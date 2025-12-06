#!/usr/bin/env python3
"""
Stage 1 Deployment Script - EC2 vLLM Server Deployment via SSM

This script orchestrates deployment from local terminal to EC2 via AWS SSM:
1. Start EC2 instance
2. Wait for instance to be ready (status checks passed)
3. Send SSM run command to pull and run Docker container from ECR
4. Monitor deployment status and validate container health

Prerequisites:
- AWS credentials configured (via AWS CLI or environment variables)
- EC2 instance with SSM agent installed and IAM role attached
- ECR repository with pushed image
- CloudWatch log group configured for SSM output
- Configuration file: config/deployment.yml
"""

import sys
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

import boto3
import yaml
from loguru import logger
from botocore.exceptions import ClientError, WaiterError

# Configure loguru
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


class DeploymentConfig:
    """Load and manage deployment configuration"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self._load_config()
        self.ssm_client = boto3.client('ssm', region_name=self._get_region())
        self._resolve_ssm_parameters()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load deployment configuration from YAML file"""
        logger.info(f"Loading configuration from {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_region(self) -> str:
        """Get AWS region from SSM parameter"""
        try:
            # Try to get from SSM first
            region_param = self.config['aws']['region']
            temp_client = boto3.client('ssm', region_name='us-east-1')  # Default region for bootstrap
            response = temp_client.get_parameter(Name=region_param)
            return response['Parameter']['Value']
        except Exception as e:
            logger.warning(f"Could not retrieve region from SSM: {e}")
            logger.info("Falling back to us-east-1")
            return 'us-east-1'
    
    def _resolve_ssm_parameters(self):
        """Resolve SSM parameter references to actual values"""
        logger.info("Resolving SSM parameters...")
        
        # Resolve instance_id
        instance_id_param = self.config['ec2']['instance_id']
        response = self.ssm_client.get_parameter(Name=instance_id_param)
        self.instance_id = response['Parameter']['Value']
        logger.info(f"Instance ID: {self.instance_id}")
        
        # Resolve hf_token reference (Secrets Manager name)
        hf_token_param = self.config['secrets']['hf_token']
        response = self.ssm_client.get_parameter(Name=hf_token_param)
        self.hf_token_secret_name = response['Parameter']['Value']
        logger.info(f"HF Token Secret: {self.hf_token_secret_name}")
        
        # Get AWS account ID for ECR registry
        sts_client = boto3.client('sts', region_name=self.region)
        self.account_id = sts_client.get_caller_identity()['Account']
        logger.info(f"AWS Account ID: {self.account_id}")
    
    @property
    def region(self) -> str:
        """Get AWS region"""
        return self.ssm_client.meta.region_name
    
    @property
    def ecr_registry(self) -> str:
        """Construct ECR registry URL"""
        return f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com"
    
    @property
    def ecr_repository(self) -> str:
        """Get ECR repository name"""
        return self.config['ecr']['repository_name']


def start_ec2_instance(config: DeploymentConfig) -> bool:
    """Start EC2 instance and wait for status OK"""
    logger.info(f"Starting EC2 instance: {config.instance_id}")
    
    ec2_client = boto3.client('ec2', region_name=config.region)
    timeout = config.config['deployment']['ec2_start_timeout_seconds']
    
    try:
        # Check current instance state
        response = ec2_client.describe_instances(InstanceIds=[config.instance_id])
        state = response['Reservations'][0]['Instances'][0]['State']['Name']
        logger.info(f"Current instance state: {state}")
        
        if state == 'running':
            logger.info("Instance already running")
        elif state == 'stopped':
            logger.info("Starting instance...")
            ec2_client.start_instances(InstanceIds=[config.instance_id])
        else:
            logger.warning(f"Instance in unexpected state: {state}")
            return False
        
        # Wait for instance to be running
        logger.info("Waiting for instance to reach 'running' state...")
        waiter = ec2_client.get_waiter('instance_running')
        waiter.wait(
            InstanceIds=[config.instance_id],
            WaiterConfig={'Delay': 15, 'MaxAttempts': timeout // 15}
        )
        logger.success("Instance is running")
        
        # Wait for status checks to pass
        logger.info("Waiting for status checks to pass...")
        waiter = ec2_client.get_waiter('instance_status_ok')
        waiter.wait(
            InstanceIds=[config.instance_id],
            WaiterConfig={'Delay': 15, 'MaxAttempts': timeout // 15}
        )
        logger.success("Instance status checks passed")
        
        return True
        
    except WaiterError as e:
        logger.error(f"Timeout waiting for instance to be ready: {e}")
        return False
    except ClientError as e:
        logger.error(f"Failed to start instance: {e}")
        return False


def deploy_container_via_ssm(
    config: DeploymentConfig,
    image_tag: str = "latest",
    force_redeploy: bool = True
) -> Optional[str]:
    """
    Send SSM run command to:
    1. Create Docker volume (if doesn't exist)
    2. Stop and remove existing container (if force_redeploy=True)
    3. Login to ECR
    4. Pull Docker image
    5. Run new container with volume mount and environment variables
    
    Returns:
        Command ID if successful, None otherwise
    """
    logger.info(f"Deploying container to {config.instance_id} via SSM")
    
    ssm_client = boto3.client('ssm', region_name=config.region)
    image_uri = f"{config.ecr_registry}/{config.ecr_repository}:{image_tag}"
    
    # Build deployment command
    container_name = config.config['docker']['container_name']
    volume_name = config.config['docker']['volume_name']
    cache_mount_path = config.config['docker']['cache_mount_path']
    model_name = config.config['model']['base_model']
    adapter_name = config.config['model']['adapter_model']
    api_port = config.config['vllm']['api_port']
    
    commands = [
        "#!/bin/bash",
        "set -e",  # Exit on error
        "",
        "echo '=== Docker Volume Setup ==='",
        f"docker volume create {volume_name} || true",
        f"echo 'Volume {volume_name} ready'",
        "",
    ]
    
    if force_redeploy:
        commands.extend([
            "echo '=== Stopping Existing Container ==='",
            f"docker stop {container_name} 2>/dev/null || echo 'No running container'",
            f"docker rm {container_name} 2>/dev/null || echo 'No container to remove'",
            "",
        ])
    
    commands.extend([
        "echo '=== ECR Login ==='",
        f"aws ecr get-login-password --region {config.region} | "
        f"docker login --username AWS --password-stdin {config.ecr_registry}",
        "",
        "echo '=== Pulling Docker Image ==='",
        f"docker pull {image_uri}",
        "",
        "echo '=== Retrieving HuggingFace Token ==='",
        f"HF_TOKEN=$(aws secretsmanager get-secret-value "
        f"--secret-id {config.hf_token_secret_name} "
        f"--query SecretString --output text --region {config.region})",
        "",
        "echo '=== Running vLLM Container ==='",
        "docker run -d \\",
        f"  --name {container_name} \\",
        "  --gpus all \\",
        f"  -p {api_port}:{api_port} \\",
        f"  -e HF_TOKEN=\"$HF_TOKEN\" \\",
        f"  -e MODEL_NAME=\"{model_name}\" \\",
        f"  -e ADAPTER_NAME=\"{adapter_name}\" \\",
        f"  -e PORT={api_port} \\",
        f"  -v {volume_name}:{cache_mount_path} \\",
        f"  {image_uri}",
        "",
        "echo '=== Verifying Container Status ==='",
        f"docker ps --filter name={container_name}",
        "",
        "echo '=== Deployment Complete ==='",
    ])
    
    command_string = "\n".join(commands)
    log_group = config.config['cloudwatch']['log_group_ssm']
    timeout = config.config['deployment']['ssm_command_timeout_seconds']
    
    try:
        logger.info("Sending SSM command...")
        response = ssm_client.send_command(
            InstanceIds=[config.instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [command_string]},
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': log_group,
                'CloudWatchOutputEnabled': True
            },
            TimeoutSeconds=timeout
        )
        
        command_id = response['Command']['CommandId']
        logger.info(f"SSM Command ID: {command_id}")
        logger.info(f"CloudWatch Logs: {log_group}")
        
        # Wait for command to complete
        logger.info("Waiting for command execution...")
        max_retries = config.config['deployment']['max_retries']
        retry_delay = config.config['deployment']['retry_delay_seconds']
        
        for attempt in range(max_retries):
            time.sleep(retry_delay)
            
            cmd_response = ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=config.instance_id
            )
            
            status = cmd_response['Status']
            logger.info(f"Command status: {status}")
            
            if status == 'Success':
                logger.success("Deployment command executed successfully")
                logger.info("Output:")
                print(cmd_response.get('StandardOutputContent', ''))
                return command_id
            elif status in ['Failed', 'Cancelled', 'TimedOut']:
                logger.error(f"Deployment failed with status: {status}")
                logger.error("Error output:")
                print(cmd_response.get('StandardErrorContent', ''))
                return None
            elif status in ['InProgress', 'Pending']:
                logger.info(f"Still running... (attempt {attempt + 1}/{max_retries})")
                continue
        
        logger.error("Command execution timed out")
        return None
        
    except ClientError as e:
        logger.error(f"Failed to send SSM command: {e}")
        return None


def validate_deployment(config: DeploymentConfig) -> bool:
    """Verify container is running and healthy via health check endpoint"""
    logger.info("Validating deployment...")
    
    ssm_client = boto3.client('ssm', region_name=config.region)
    container_name = config.config['docker']['container_name']
    api_port = config.config['vllm']['api_port']
    timeout = config.config['deployment']['health_check_timeout_seconds']
    interval = config.config['deployment']['health_check_interval_seconds']
    
    # Check container status via SSM
    health_check_cmd = f"""
    #!/bin/bash
    
    # Check if container is running
    RUNNING=$(docker ps --filter name={container_name} --format '{{{{.Names}}}}')
    if [ "$RUNNING" != "{container_name}" ]; then
        echo "ERROR: Container {container_name} is not running"
        exit 1
    fi
    
    echo "Container is running, checking health endpoint..."
    
    # Check vLLM health endpoint
    max_attempts={timeout // interval}
    for i in $(seq 1 $max_attempts); do
        if curl -f http://localhost:{api_port}/health 2>/dev/null; then
            echo "SUCCESS: vLLM server is healthy"
            exit 0
        fi
        echo "Attempt $i/$max_attempts: Health check not ready, waiting..."
        sleep {interval}
    done
    
    echo "ERROR: Health check timed out after {timeout} seconds"
    docker logs {container_name} --tail 50
    exit 1
    """
    
    try:
        logger.info("Running health check via SSM...")
        response = ssm_client.send_command(
            InstanceIds=[config.instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [health_check_cmd]},
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': config.config['cloudwatch']['log_group_ssm'],
                'CloudWatchOutputEnabled': True
            }
        )
        
        command_id = response['Command']['CommandId']
        
        # Wait for health check to complete
        time.sleep(5)  # Initial wait
        
        for _ in range(timeout // 5):
            cmd_response = ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=config.instance_id
            )
            
            status = cmd_response['Status']
            
            if status == 'Success':
                logger.success("Health check passed!")
                logger.info(cmd_response.get('StandardOutputContent', ''))
                return True
            elif status in ['Failed', 'Cancelled', 'TimedOut']:
                logger.error("Health check failed")
                logger.error(cmd_response.get('StandardErrorContent', ''))
                return False
            elif status in ['InProgress', 'Pending']:
                time.sleep(5)
                continue
        
        logger.error("Health check timed out")
        return False
        
    except ClientError as e:
        logger.error(f"Failed to run health check: {e}")
        return False


def main():
    """Main deployment orchestration"""
    parser = argparse.ArgumentParser(
        description='Deploy vLLM server to EC2 via SSM'
    )
    parser.add_argument(
        '--image-tag',
        default='latest',
        help='Docker image tag to deploy (default: latest)'
    )
    parser.add_argument(
        '--skip-start',
        action='store_true',
        help='Skip EC2 instance start (if already running)'
    )
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip health check validation'
    )
    parser.add_argument(
        '--quick-restart',
        action='store_true',
        help='Quick restart: just restart existing container without pulling new image'
    )
    
    args = parser.parse_args()
    
    # Resolve config path
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / 'config' / 'deployment.yml'
    
    try:
        logger.info("=== Stage 1 Deployment Starting ===")
        
        # Load configuration
        config = DeploymentConfig(config_path)
        
        # Step 1: Start EC2 instance
        if not args.skip_start:
            if not start_ec2_instance(config):
                logger.error("Failed to start EC2 instance")
                sys.exit(1)
        else:
            logger.info("Skipping EC2 instance start")
        
        # Step 2: Deploy container
        if args.quick_restart:
            logger.info("Quick restart: restarting existing container...")
            command_id = deploy_container_via_ssm(
                config,
                image_tag=args.image_tag,
                force_redeploy=False
            )
        else:
            command_id = deploy_container_via_ssm(
                config,
                image_tag=args.image_tag,
                force_redeploy=True
            )
        
        if not command_id:
            logger.error("Deployment failed")
            sys.exit(1)
        
        # Step 3: Validate deployment
        if not args.skip_validation:
            if not validate_deployment(config):
                logger.error("Deployment validation failed")
                sys.exit(1)
        else:
            logger.info("Skipping validation")
        
        logger.success("=== Deployment Complete ===")
        api_port = config.config['vllm']['api_port']
        logger.info(f"vLLM server running at http://<instance-ip>:{api_port}")
        logger.info("Models cached on EBS volume for future deployments")
        
    except KeyboardInterrupt:
        logger.warning("Deployment interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unexpected error during deployment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
