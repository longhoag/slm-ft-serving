# Infrastructure Setup - Stage 1

## Overview
This document details the AWS infrastructure setup required for Stage 1: vLLM server deployment on EC2.

## EC2 Instance Configuration

### Instance Specifications
- **Instance Type**: g6.2xlarge
- **Region**: us-east-1
- **GPU**: NVIDIA L4 (1x GPU, 24GB VRAM)
- **vCPUs**: 8
- **Memory**: 32 GiB
- **Storage**: 80 GiB EBS root volume (gp3 recommended)
- **AMI**: Deep Learning AMI with Docker and NVIDIA drivers pre-installed

### Instance Tags
```
Name: slm-ft-serving-vllm
Environment: production
Project: slm-ft-serving
Stage: 1
```

## IAM Configuration

### EC2 Instance IAM Role
Create IAM role: `slm-ft-serving-ec2-role`

**Required Policies:**
1. **SSM Managed Policy**: `AmazonSSMManagedInstanceCore` (for SSM access)
2. **ECR Pull Access** (custom inline policy):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
```

3. **Secrets Manager Access** (custom inline policy):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:slm-ft-serving/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:us-east-1:*:parameter/slm-ft-serving/*"
    }
  ]
}
```

4. **CloudWatch Logs** (custom inline policy):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:*:log-group:/aws/ssm/slm-ft-serving/*"
    }
  ]
}
```

### Local Deployment IAM User/Role
For running `scripts/deploy.py` locally:

**Required Permissions:**
- EC2: `StartInstances`, `DescribeInstances`, `DescribeInstanceStatus`
- SSM: `SendCommand`, `GetCommandInvocation`, `DescribeInstanceInformation`
- Secrets Manager: Read access to secrets
- CloudWatch Logs: Read access for monitoring

## Security Group Configuration

Create Security Group: `slm-ft-serving-sg`

**Inbound Rules:**
- Port 8000 (vLLM API): Source depends on Stage 2 architecture (initially: your IP or VPC CIDR)
- No SSH port needed (using SSM)

**Outbound Rules:**
- Allow all outbound traffic (for HuggingFace model download, ECR pull, etc.)

## AWS Secrets Manager Setup

### Required Secrets
1. **HuggingFace Token**
   - Secret Name: `slm-ft-serving/hf-token`
   - Key: `HF_TOKEN`
   - Description: HuggingFace access token for Llama model download

2. **AWS Credentials for GitHub Actions**
   - Store in GitHub Secrets (not AWS Secrets Manager):
     - `AWS_ACCESS_KEY_ID`
     - `AWS_SECRET_ACCESS_KEY`

### SSM Parameter Store (Alternative/Complementary)
```bash
# Create parameter that references Secrets Manager
aws ssm put-parameter \
  --name "/slm-ft-serving/hf-token" \
  --value "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:slm-ft-serving/hf-token" \
  --type "String"
```

## CloudWatch Configuration

### Log Groups
1. **SSM Command Output**: `/aws/ssm/slm-ft-serving/commands`
2. **EC2 Instance Logs**: `/aws/ec2/slm-ft-serving/vllm`
3. **Deployment Script Logs**: `/aws/deployment/slm-ft-serving`

### Retention Policy
- Set retention to 7 days (adjust based on needs)

## ECR Repository

### Repository Configuration
- **Repository Name**: `slm-ft-serving-vllm`
- **Region**: us-east-1
- **Image Scanning**: Enable on push
- **Encryption**: AES-256

### Lifecycle Policy
```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

## SSM Configuration

### Prerequisites
- SSM Agent installed on EC2 instance (comes pre-installed on most AMIs)
- Instance IAM role attached with SSM permissions
- Instance in a subnet with internet access (for SSM endpoint communication)

### SSM Document (Optional Custom Command)
For standardized deployment commands, create custom SSM document:
- Document Name: `slm-ft-serving-deploy`
- Document Type: Command
- Content: Shell script for pulling and running container

## Setup Checklist

- [ ] Create ECR repository
- [ ] Create IAM role for EC2 instance
- [ ] Create Security Group
- [ ] Store HF_TOKEN in AWS Secrets Manager
- [ ] Create CloudWatch log groups
- [ ] Launch EC2 g6.2xlarge instance with:
  - [ ] IAM role attached
  - [ ] Security Group attached
  - [ ] 80 GiB root volume
  - [ ] SSM agent enabled
- [ ] Configure GitHub Secrets:
  - [ ] AWS_ACCESS_KEY_ID
  - [ ] AWS_SECRET_ACCESS_KEY
- [ ] Test SSM connectivity: `aws ssm start-session --target <instance-id>`
- [ ] Install Poetry locally: `curl -sSL https://install.python-poetry.org | python3 -`
- [ ] Run `poetry install` in project root

## Cost Estimates (Approximate)
- EC2 g6.2xlarge: ~$0.75/hour (on-demand)
- EBS 80 GiB gp3: ~$6.40/month
- ECR storage: ~$0.10/GB/month
- Data transfer and other services: Variable

**Note**: Use EC2 instance stop/start in deployment script to minimize costs when not in use.
