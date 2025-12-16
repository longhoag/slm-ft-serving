#!/usr/bin/env python3
"""
Stage 2 Deployment Script - Docker Compose Orchestration via SSM

This script orchestrates multi-container deployment (vLLM + FastAPI gateway):
1. Start EC2 instance
2. Wait for instance to be ready (status checks passed)
3. Send SSM run command to:
   - Copy docker-compose.yml to EC2
   - Pull images from ECR (vllm + gateway)
   - Run docker-compose up with health check dependencies
4. Monitor deployment status and validate both containers

Stage 2 Changes:
- Uses docker-compose instead of docker run
- Deploys both vLLM server (port 8000) and FastAPI gateway (port 8080)
- Gateway waits for vLLM health check before starting
- Single orchestration command for entire stack

Prerequisites:
- AWS credentials configured (via AWS CLI or environment variables)
- EC2 instance with SSM agent, Docker, and Docker Compose installed
- ECR repositories with pushed images (vllm + gateway)
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
    level="INFO",
    colorize=True
)

# Custom level colors
logger.level("INFO", color="<blue>")


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
    def ecr_vllm_repository(self) -> str:
        """Get vLLM ECR repository name"""
        return self.config['ecr']['vllm_repository']
    
    @property
    def ecr_gateway_repository(self) -> str:
        """Get gateway ECR repository name"""
        return self.config['ecr']['gateway_repository']


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


def deploy_compose_stack_via_ssm(
    config: DeploymentConfig,
    image_tag: str = "latest",
    force_redeploy: bool = True
) -> Optional[str]:
    """
    Send SSM run command to deploy Docker Compose stack:
    1. Create Docker volume (if doesn't exist)
    2. Stop and remove existing stack (if force_redeploy=True)
    3. Login to ECR
    4. Pull both Docker images (vllm + gateway)
    5. Copy docker-compose.yml to EC2
    6. Run docker-compose up with environment variables
    
    Returns:
        Command ID if successful, None otherwise
    """
    logger.info(f"Deploying Docker Compose stack to {config.instance_id} via SSM")
    
    ssm_client = boto3.client('ssm', region_name=config.region)
    
    # Read docker-compose.yml from project root
    script_dir = Path(__file__).parent
    compose_file = script_dir.parent / 'docker-compose.yml'
    
    if not compose_file.exists():
        logger.error(f"docker-compose.yml not found at {compose_file}")
        return None
    
    with open(compose_file, 'r', encoding='utf-8') as f:
        compose_content = f.read()
    
    # No escaping needed - we'll use quoted heredoc delimiter 'COMPOSE_EOF'
    # which treats content literally (no variable substitution)
    
    volume_name = config.config['docker']['volume_name']
    
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
            "echo '=== Cleaning Up Existing Containers ==='",
            "cd ~",  # Use ~ instead of hardcoded path
            "",
            "# Stop and remove docker-compose stack (Stage 2 containers)",
            "docker compose down 2>/dev/null || echo 'No existing compose stack'",
            "",
            "# Remove any standalone containers from Stage 1 deployment",
            "# (prevents container name conflicts)",
            "echo 'Checking for Stage 1 containers...'",
            "docker stop vllm-server 2>/dev/null || echo 'No Stage 1 vllm-server running'",
            "docker rm vllm-server 2>/dev/null || echo 'No Stage 1 vllm-server to remove'",
            "",
        ])
    
    commands.extend([
        "echo '=== ECR Login ==='",
        f"aws ecr get-login-password --region {config.region} | "
        f"docker login --username AWS --password-stdin {config.ecr_registry} 2>&1 | grep -v 'WARNING'",
        "",
        "echo '=== Pulling Docker Images ==='",
        f"docker pull {config.ecr_registry}/{config.ecr_vllm_repository}:{image_tag}",
        f"docker pull {config.ecr_registry}/{config.ecr_gateway_repository}:{image_tag}",
        "",
        "echo '=== Writing docker-compose.yml ==='",
        "cd ~",  # Use ~ to work with any user
        "cat > docker-compose.yml << 'COMPOSE_EOF'",
        compose_content,
        "COMPOSE_EOF",
        "",
        "echo '=== Retrieving Secrets ==='",
        f"HF_TOKEN=$(aws secretsmanager get-secret-value "
        f"--secret-id {config.hf_token_secret_name} "
        f"--query SecretString --output text --region {config.region})",
        "",
        "echo '=== Setting Environment Variables ==='",
        f"export ECR_REGISTRY={config.ecr_registry}",
        "export HF_TOKEN=\"$HF_TOKEN\"",
        f"export CORS_ORIGINS=\"{config.config['gateway']['cors_origins']}\"",
        "echo 'Environment configured for Stage 2 deployment'",
        "",
        "echo 'Current directory:' && pwd",
        "echo 'docker-compose.yml exists:' && ls -la docker-compose.yml",
        "echo 'Environment variables:'",
        "echo \"ECR_REGISTRY=$ECR_REGISTRY\"",
        "echo \"HF_TOKEN=${HF_TOKEN:0:20}...\"",
        "echo \"CORS_ORIGINS=$CORS_ORIGINS\"",
        "",
        "echo '=== Starting Docker Compose Stack ==='",
        "docker compose up -d 2>&1",
        "",
        "echo '=== Verifying Stack Status ===",
        "sleep 5",  # Brief wait for containers to initialize
        "docker compose ps",
        "",
        "echo '=== Deployment Complete ==='",
        "echo 'vLLM server: http://localhost:8000'",
        "echo 'Gateway API: http://localhost:8080'",
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
        retry_delay = config.config['deployment']['retry_delay_seconds']
        timeout = config.config['deployment']['ssm_command_timeout_seconds']
        max_attempts = timeout // retry_delay  # Calculate attempts based on timeout
        
        for attempt in range(max_attempts):
            time.sleep(retry_delay)
            
            cmd_response = ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=config.instance_id
            )
            
            status = cmd_response['Status']
            
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
                if (attempt + 1) % 6 == 0:  # Log every minute (6 * 10 seconds)
                    logger.info(f"Still running... ({(attempt + 1) * retry_delay}s elapsed)")
                continue
        
        logger.error("Command execution timed out")
        return None
        
    except ClientError as e:
        logger.error(f"Failed to send SSM command: {e}")
        return None


def validate_deployment(config: DeploymentConfig) -> bool:
    """Verify both containers are running and healthy via health check endpoints"""
    logger.info("Validating deployment...")
    
    ssm_client = boto3.client('ssm', region_name=config.region)
    vllm_port = config.config['vllm']['api_port']
    gateway_port = config.config['gateway']['api_port']
    timeout = config.config['deployment']['health_check_timeout_seconds']
    interval = config.config['deployment']['health_check_interval_seconds']
    
    # Check both containers via SSM
    health_check_cmd = f"""
    #!/bin/bash
    
    echo "=== Checking Docker Compose Stack ==="
    cd ~
    docker compose ps
    
    # Check if both containers are running
    VLLM_RUNNING=$(docker ps --filter name=vllm-server --format '{{{{.Names}}}}')
    GATEWAY_RUNNING=$(docker ps --filter name=fastapi-gateway --format '{{{{.Names}}}}')
    
    if [ "$VLLM_RUNNING" != "vllm-server" ]; then
        echo "ERROR: vLLM container is not running"
        docker ps -a --filter name=vllm-server
        echo "=== vLLM logs ==="
        docker logs vllm-server --tail 100
        exit 1
    fi
    
    if [ "$GATEWAY_RUNNING" != "fastapi-gateway" ]; then
        echo "ERROR: Gateway container is not running"
        docker ps -a --filter name=fastapi-gateway
        echo "=== Gateway logs ==="
        docker logs fastapi-gateway --tail 100
        exit 1
    fi
    
    echo "Both containers running, checking health endpoints..."
    
    # Check vLLM health endpoint (may take 4-5 mins for model loading)
    echo "Checking vLLM health (model loading may take 4-5 minutes)..."
    max_attempts={timeout // interval}
    for i in $(seq 1 $max_attempts); do
        if curl -f http://localhost:{vllm_port}/health 2>/dev/null; then
            echo "✅ vLLM server is healthy"
            break
        fi
        echo "Attempt $i/$max_attempts: vLLM not ready, waiting..."
        sleep {interval}
    done
    
    # Check gateway health endpoint
    echo "Checking FastAPI gateway health..."
    for i in $(seq 1 10); do
        if curl -f http://localhost:{gateway_port}/health 2>/dev/null; then
            echo "✅ Gateway is healthy"
            
            # Get detailed health status
            echo "=== Gateway Health Details ==="
            curl -s http://localhost:{gateway_port}/health | python3 -m json.tool
            
            echo ""
            echo "SUCCESS: Full stack is healthy"
            echo "- vLLM: http://localhost:{vllm_port}"
            echo "- Gateway: http://localhost:{gateway_port}"
            echo "- API Docs: http://localhost:{gateway_port}/docs"
            exit 0
        fi
        echo "Gateway attempt $i/10: waiting..."
        sleep 3
    done
    
    echo "ERROR: Health checks failed"
    echo "=== Stack Status ==="
    docker compose ps
    echo "=== vLLM Logs (last 200 lines) ==="
    docker logs vllm-server --tail 200
    echo "=== Gateway Logs (last 200 lines) ==="
    docker logs fastapi-gateway --tail 200
    echo "=== GPU Status ==="
    nvidia-smi
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
        logger.info("=== Stage 2 Deployment Starting ===")
        logger.info("Deploying Docker Compose stack: vLLM + FastAPI Gateway")
        
        # Load configuration
        config = DeploymentConfig(config_path)
        
        # Step 1: Start EC2 instance
        if not args.skip_start:
            if not start_ec2_instance(config):
                logger.error("Failed to start EC2 instance")
                sys.exit(1)
        else:
            logger.info("Skipping EC2 instance start")
        
        # Step 2: Deploy Docker Compose stack
        if args.quick_restart:
            logger.info("Quick restart: restarting existing stack...")
            command_id = deploy_compose_stack_via_ssm(
                config,
                image_tag=args.image_tag,
                force_redeploy=False
            )
        else:
            command_id = deploy_compose_stack_via_ssm(
                config,
                image_tag=args.image_tag,
                force_redeploy=True
            )
        
        if not command_id:
            logger.error("Deployment failed")
            sys.exit(1)
        
        # Step 3: Validate deployment (both containers)
        if not args.skip_validation:
            if not validate_deployment(config):
                logger.error("Deployment validation failed")
                sys.exit(1)
        else:
            logger.info("Skipping validation")
        
        logger.success("=== Deployment Complete ===")
        vllm_port = config.config['vllm']['api_port']
        logger.info(f"✅ vLLM server: http://<instance-ip>:{vllm_port}")
        logger.info(f"✅ Gateway API: http://<instance-ip>:8080")
        logger.info(f"✅ API Documentation: http://<instance-ip>:8080/docs")
        logger.info("Models cached on EBS volume for future deployments")
        
    except KeyboardInterrupt:
        logger.warning("Deployment interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unexpected error during deployment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
