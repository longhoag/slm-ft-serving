# SSM Parameter Store Setup Guide

This document describes the AWS SSM Parameter Store parameters that need to be created for the deployment configuration.

## Creating Parameters

Use the AWS CLI to create these parameters:

```bash
# AWS Configuration
aws ssm put-parameter --name "/slm-ft-serving/aws/region" --value "us-east-1" --type "String"

# EC2 Configuration
aws ssm put-parameter --name "/slm-ft-serving/ec2/instance-id" --value "i-XXXXXXXXXXXXX" --type "String"  # Replace with actual instance ID
aws ssm put-parameter --name "/slm-ft-serving/ec2/instance-type" --value "g6.2xlarge" --type "String"

# ECR Configuration
aws ssm put-parameter --name "/slm-ft-serving/ecr/repository-name" --value "slm-ft-serving-vllm" --type "String"

# Secrets (HuggingFace Token)
# First create the secret in Secrets Manager, then reference it via SSM parameter
aws secretsmanager create-secret --name "slm-ft-serving/hf-token" --secret-string "hf_YOUR_TOKEN_HERE"
aws ssm put-parameter --name "/slm-ft-serving/secrets/hf-token" --value "{{resolve:secretsmanager:slm-ft-serving/hf-token}}" --type "String"

# Model Configuration
aws ssm put-parameter --name "/slm-ft-serving/model/base-model" --value "meta-llama/Llama-3.1-8B" --type "String"
aws ssm put-parameter --name "/slm-ft-serving/model/adapter-model" --value "loghoag/llama-3.1-8b-medical-ie" --type "String"

# vLLM Configuration
aws ssm put-parameter --name "/slm-ft-serving/vllm/api-port" --value "8000" --type "String"
aws ssm put-parameter --name "/slm-ft-serving/vllm/tensor-parallel-size" --value "1" --type "String"

# CloudWatch Configuration
aws ssm put-parameter --name "/slm-ft-serving/cloudwatch/log-group-ssm" --value "/aws/ssm/slm-ft-serving/commands" --type "String"
aws ssm put-parameter --name "/slm-ft-serving/cloudwatch/log-group-deployment" --value "/aws/deployment/slm-ft-serving" --type "String"

# Deployment Configuration
aws ssm put-parameter --name "/slm-ft-serving/deployment/max-retries" --value "3" --type "String"
aws ssm put-parameter --name "/slm-ft-serving/deployment/retry-delay-seconds" --value "10" --type "String"
aws ssm put-parameter --name "/slm-ft-serving/deployment/ec2-start-timeout" --value "300" --type "String"
aws ssm put-parameter --name "/slm-ft-serving/deployment/ssm-command-timeout" --value "600" --type "String"
aws ssm put-parameter --name "/slm-ft-serving/deployment/health-check-timeout" --value "120" --type "String"
aws ssm put-parameter --name "/slm-ft-serving/deployment/health-check-interval" --value "10" --type "String"
```

## Bulk Create Script

Save this as `scripts/setup-ssm-parameters.sh`:

```bash
#!/bin/bash
set -e

echo "Setting up SSM Parameter Store parameters..."

# Prompt for required values
read -p "Enter EC2 Instance ID: " INSTANCE_ID
read -p "Enter HuggingFace Token: " HF_TOKEN

# AWS Configuration
aws ssm put-parameter --name "/slm-ft-serving/aws/region" --value "us-east-1" --type "String" --overwrite

# EC2 Configuration
aws ssm put-parameter --name "/slm-ft-serving/ec2/instance-id" --value "$INSTANCE_ID" --type "String" --overwrite
aws ssm put-parameter --name "/slm-ft-serving/ec2/instance-type" --value "g6.2xlarge" --type "String" --overwrite

# ECR Configuration
aws ssm put-parameter --name "/slm-ft-serving/ecr/repository-name" --value "slm-ft-serving-vllm" --type "String" --overwrite

# Secrets
aws secretsmanager create-secret --name "slm-ft-serving/hf-token" --secret-string "$HF_TOKEN" 2>/dev/null || \
aws secretsmanager update-secret --secret-id "slm-ft-serving/hf-token" --secret-string "$HF_TOKEN"
aws ssm put-parameter --name "/slm-ft-serving/secrets/hf-token" --value "{{resolve:secretsmanager:slm-ft-serving/hf-token}}" --type "String" --overwrite

# Model Configuration
aws ssm put-parameter --name "/slm-ft-serving/model/base-model" --value "meta-llama/Llama-3.1-8B" --type "String" --overwrite
aws ssm put-parameter --name "/slm-ft-serving/model/adapter-model" --value "loghoag/llama-3.1-8b-medical-ie" --type "String" --overwrite

# vLLM Configuration
aws ssm put-parameter --name "/slm-ft-serving/vllm/api-port" --value "8000" --type "String" --overwrite
aws ssm put-parameter --name "/slm-ft-serving/vllm/tensor-parallel-size" --value "1" --type "String" --overwrite

# CloudWatch Configuration
aws ssm put-parameter --name "/slm-ft-serving/cloudwatch/log-group-ssm" --value "/aws/ssm/slm-ft-serving/commands" --type "String" --overwrite
aws ssm put-parameter --name "/slm-ft-serving/cloudwatch/log-group-deployment" --value "/aws/deployment/slm-ft-serving" --type "String" --overwrite

# Deployment Configuration
aws ssm put-parameter --name "/slm-ft-serving/deployment/max-retries" --value "3" --type "String" --overwrite
aws ssm put-parameter --name "/slm-ft-serving/deployment/retry-delay-seconds" --value "10" --type "String" --overwrite
aws ssm put-parameter --name "/slm-ft-serving/deployment/ec2-start-timeout" --value "300" --type "String" --overwrite
aws ssm put-parameter --name "/slm-ft-serving/deployment/ssm-command-timeout" --value "600" --type "String" --overwrite
aws ssm put-parameter --name "/slm-ft-serving/deployment/health-check-timeout" --value "120" --type "String" --overwrite
aws ssm put-parameter --name "/slm-ft-serving/deployment/health-check-interval" --value "10" --type "String" --overwrite

echo "✓ All SSM parameters created successfully!"
```

Make it executable:
```bash
chmod +x scripts/setup-ssm-parameters.sh
```

## Retrieving Parameters in Python

The deployment script will use boto3 to retrieve these values:

```python
import boto3

ssm = boto3.client('ssm', region_name='us-east-1')

def get_parameter(param_path: str) -> str:
    """Retrieve parameter value from SSM Parameter Store"""
    response = ssm.get_parameter(Name=param_path, WithDecryption=True)
    return response['Parameter']['Value']

# Example usage
instance_id = get_parameter('/slm-ft-serving/ec2/instance-id')
hf_token = get_parameter('/slm-ft-serving/secrets/hf-token')
```

## Updating Parameters

To update a parameter value:
```bash
aws ssm put-parameter --name "/slm-ft-serving/ec2/instance-id" --value "i-NEW_INSTANCE_ID" --type "String" --overwrite
```

## Listing All Parameters

```bash
aws ssm get-parameters-by-path --path "/slm-ft-serving" --recursive
```
