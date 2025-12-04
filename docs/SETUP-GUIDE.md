# Complete AWS & External Services Setup Guide

This guide walks through setting up all required AWS services and external accounts via web UI consoles for the slm-ft-serving project.

---

## Table of Contents
1. [HuggingFace Account Setup](#1-huggingface-account-setup)
2. [AWS Account Prerequisites](#2-aws-account-prerequisites)
3. [AWS IAM Setup](#3-aws-iam-setup)
4. [Amazon ECR Setup](#4-amazon-ecr-setup)
5. [AWS Secrets Manager Setup](#5-aws-secrets-manager-setup)
6. [AWS Systems Manager Parameter Store](#6-aws-systems-manager-parameter-store)
7. [EC2 Instance Setup](#7-ec2-instance-setup)
8. [CloudWatch Logs Setup](#8-cloudwatch-logs-setup)
9. [GitHub Secrets Configuration](#9-github-secrets-configuration)
10. [Verification Checklist](#10-verification-checklist)

---

## 1. HuggingFace Account Setup

### 1.1 Create HuggingFace Account (if needed)
1. Go to https://huggingface.co/join
2. Sign up with your email or GitHub account
3. Verify your email address

### 1.2 Generate Access Token
1. Log in to HuggingFace
2. Click your profile picture (top right) → **Settings**
3. Navigate to **Access Tokens** in the left sidebar
4. Click **New token**
5. Configure token:
   - **Name**: `slm-ft-serving-production`
   - **Role**: Select **Read** (sufficient for model download)
6. Click **Generate token**
7. **IMPORTANT**: Copy the token immediately (starts with `hf_...`)
8. Store it securely - you'll add it to AWS Secrets Manager later

### 1.3 Request Access to Llama 3.1 Model
1. Go to https://huggingface.co/meta-llama/Llama-3.1-8B
2. Click **Agree and access repository**
3. Fill out Meta's access form if prompted
4. Wait for approval (usually takes a few hours to 1 day)
5. Once approved, your token will have access to download the model

---

## 2. AWS Account Prerequisites

### 2.1 AWS Account Setup
- Ensure you have an AWS account at https://aws.amazon.com
- Have billing enabled (g6.2xlarge instances incur charges)
- Note your AWS Account ID (found in top right → Account dropdown)

### 2.2 Set Default Region
1. In AWS Console, click region dropdown (top right)
2. Select **US East (N. Virginia) us-east-1**
3. All subsequent services should be created in this region

---

## 3. AWS IAM Setup

### 3.1 Create IAM Role for EC2 Instance

**Step 1: Create the Role**
1. Go to **IAM Console**: https://console.aws.amazon.com/iam/
2. Click **Roles** in left sidebar
3. Click **Create role** button
4. Configure role:
   - **Trusted entity type**: AWS service
   - **Use case**: EC2
   - Click **Next**

**Step 2: Attach AWS Managed Policies**
1. Search and select these AWS managed policies:
   - ✅ `AmazonSSMManagedInstanceCore` (for SSM Session Manager)
   - ✅ `AmazonEC2ContainerRegistryReadOnly` (for pulling images from ECR)
2. Click **Next**

**Step 3: Name and Create**
1. **Role name**: `slm-ft-serving-ec2-role`
2. **Description**: `IAM role for slm-ft-serving EC2 instance with SSM, ECR, Secrets Manager access`
3. Click **Create role**

**Step 4: Add Custom Inline Policies**

Go back to **IAM → Roles → slm-ft-serving-ec2-role**

**Why custom policies instead of AWS managed policies?**
- `SecretsManagerReadWrite` gives access to ALL secrets in your account (security risk)
- `CloudWatchLogsFullAccess` allows creating/deleting any log group (too permissive)
- Custom policies scope access only to your project's specific resources

**Policy 1: Secrets Manager & Parameter Store Access**
1. Click **Add permissions** → **Create inline policy**
2. Click **JSON** tab
3. Paste this policy (replace `ACCOUNT_ID` with your AWS account ID):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:slm-ft-serving/*"
    },
    {
      "Sid": "ParameterStoreAccess",
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": "arn:aws:ssm:us-east-1:ACCOUNT_ID:parameter/slm-ft-serving/*"
    }
  ]
}
```
4. Click **Next**
5. **Policy name**: `SecretsAndParameterStorePolicy`
6. Click **Create policy**

**Policy 2: CloudWatch Logs Access**
1. Click **Add permissions** → **Create inline policy**
2. Click **JSON** tab
3. Paste this policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:us-east-1:*:log-group:/aws/ssm/slm-ft-serving/*"
    }
  ]
}
```
4. Click **Next**
5. **Policy name**: `CloudWatchLogsPolicy`
6. Click **Create policy**

**Summary of EC2 Role Policies:**
- ✅ 2 AWS Managed Policies (SSM, ECR ReadOnly)
- ✅ 2 Custom Inline Policies (Secrets/Parameters + CloudWatch Logs - scoped to your resources)

### 3.2 Create IAM User for Local Deployment Script

**Step 1: Create User**
1. Go to **IAM → Users**
2. Click **Create user**
3. **User name**: `slm-ft-serving-deployer`
4. Click **Next**

**Step 2: Set Permissions**
1. Select **Attach policies directly**
2. Search and attach these **AWS Managed Policies**:
   - ✅ `AmazonEC2ReadOnlyAccess` (for describing instances)
   - ✅ `AmazonSSMReadOnlyAccess` (base SSM permissions)
3. Now create a **custom policy** for write operations:
   - Click **Create policy** (opens new tab)
   - Click **JSON** tab
   - Paste this policy (replace `ACCOUNT_ID` and `INSTANCE_ID`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EC2StartStopAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:StartInstances",
        "ec2:StopInstances"
      ],
      "Resource": "arn:aws:ec2:us-east-1:ACCOUNT_ID:instance/INSTANCE_ID"
    },
    {
      "Sid": "SSMCommandAccess",
      "Effect": "Allow",
      "Action": [
        "ssm:SendCommand",
        "ssm:GetCommandInvocation",
        "ssm:ListCommandInvocations"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ParameterStoreReadAccess",
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": "arn:aws:ssm:us-east-1:ACCOUNT_ID:parameter/slm-ft-serving/*"
    },
    {
      "Sid": "SecretsManagerReadAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:slm-ft-serving/*"
    },
    {
      "Sid": "CloudWatchLogsReadAccess",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource": [
        "arn:aws:logs:us-east-1:ACCOUNT_ID:log-group:/aws/ssm/slm-ft-serving/*",
        "arn:aws:logs:us-east-1:ACCOUNT_ID:log-group:/aws/deployment/slm-ft-serving/*"
      ]
    }
  ]
}
```
4. Click **Next**
5. **Policy name**: `slm-ft-serving-deployer-policy`
6. Click **Create policy**
7. Go back to user creation tab, refresh policies
8. Search and attach:
   - ✅ `AmazonEC2ReadOnlyAccess` (if not already selected)
   - ✅ `AmazonSSMReadOnlyAccess` (if not already selected)
   - ✅ `slm-ft-serving-deployer-policy` (your custom policy)
9. Click **Next** → **Create user**

**Summary of Deployer User Policies:**
- ✅ 2 AWS Managed Policies (EC2 ReadOnly, SSM ReadOnly)
- ✅ 1 Custom Policy (EC2 start/stop, SSM commands, secrets access, CloudWatch Logs read)

**Step 3: Create Access Keys**
1. Go to **IAM → Users → slm-ft-serving-deployer**
2. Click **Security credentials** tab
3. Scroll to **Access keys** section
4. Click **Create access key**
5. Select **Command Line Interface (CLI)**
6. Check the confirmation checkbox
7. Click **Next**
8. **Description tag**: `Local deployment script access`
9. Click **Create access key**
10. **CRITICAL**: Copy both:
    - **Access key ID** (starts with `AKIA...`)
    - **Secret access key** (only shown once)
11. Store these securely for GitHub Secrets setup

### 3.3 Create IAM User for GitHub Actions

**Option A: Reuse Same User** (Simpler)
- Use the same `slm-ft-serving-deployer` user created above
- Create a second access key pair for GitHub Actions
- Follow Step 3 above again to create another access key

**Option B: Create Separate User** (Better isolation)
1. Follow same steps as 3.2 but name it `slm-ft-serving-github-actions`
2. Attach **AWS Managed Policy**:
   - ✅ `AmazonEC2ContainerRegistryPowerUser` (for pushing images to ECR)
3. No custom policy needed for GitHub Actions!
4. Create access key as described above

**Summary of GitHub Actions User:**
- ✅ 1 AWS Managed Policy (ECR PowerUser - includes push/pull permissions)

---

## 4. Amazon ECR Setup

### 4.1 Create ECR Repository
1. Go to **ECR Console**: https://console.aws.amazon.com/ecr/
2. Ensure region is **us-east-1** (top right)
3. Click **Get Started** or **Create repository**
4. Configure repository:
   - **Visibility settings**: Private
   - **Repository name**: `slm-ft-serving-vllm`
   - **Tag immutability**: Disabled (allow tag overwrites)
   - **Image scanning**: Enable **Scan on push**
   - **Encryption**: AES-256 (default)
5. Click **Create repository**

### 4.2 Set Lifecycle Policy
1. Click on the repository name `slm-ft-serving-vllm`
2. Click **Lifecycle Policy** tab
3. Click **Create rule**
4. Configure rule:
   - **Rule priority**: 1
   - **Rule description**: `Keep last 2 images`
   - **Image status**: Any
   - **Match criteria**: Image count more than
   - **Image count**: 2
   - **Image count before action**: Specify maximum images to not perform action on
   - **Rule action**: Expire (deletes the image)
5. Click **Save**

### 4.3 Note Repository URI
1. In the repository page, copy the **URI** (format: `ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/slm-ft-serving-vllm`)
2. Save this for reference (used in deployment scripts)

---

## 5. AWS Secrets Manager Setup

### 5.1 Create HuggingFace Token Secret
1. Go to **Secrets Manager Console**: https://console.aws.amazon.com/secretsmanager/
2. Click **Store a new secret**
3. Configure secret:
   - **Secret type**: Other type of secret
   - **Key/value pairs**: Click **Plaintext** tab
4. Paste your HuggingFace token directly (the `hf_...` string from step 1.2)
5. Click **Next**
6. Configure secret name:
   - **Secret name**: `slm-ft-serving/hf-token`
   - **Description**: `HuggingFace access token for Llama 3.1 8B model download`
7. Click **Next**
8. **Automatic rotation**: Disable (not needed for HF tokens)
9. Click **Next**
10. Review and click **Store**

### 5.2 Verify Secret
1. Click on the secret name `slm-ft-serving/hf-token`
2. Click **Retrieve secret value** to verify it's correct
3. Copy the **Secret ARN** for reference

---

## 6. AWS Systems Manager Parameter Store

### 6.1 Automated Setup (Recommended)

Use the setup script provided in `docs/ssm-parameters.md`:

1. Ensure AWS CLI is configured with your credentials
2. Run the setup script:
```bash
chmod +x scripts/setup-ssm-parameters.sh
./scripts/setup-ssm-parameters.sh
```
3. Enter EC2 Instance ID when prompted (you'll get this after step 7)
4. Enter HuggingFace token when prompted

### 6.2 Manual Setup via Console

If you prefer using the AWS Console:

1. Go to **Systems Manager Console**: https://console.aws.amazon.com/systems-manager/
2. Click **Parameter Store** in left sidebar
3. For each parameter below, click **Create parameter**:

**Parameter 1: AWS Region**
- **Name**: `/slm-ft-serving/aws/region`
- **Type**: String
- **Value**: `us-east-1`
- Click **Create parameter**

**Parameter 2: EC2 Instance ID** (create after step 7.7)
- **Name**: `/slm-ft-serving/ec2/instance-id`
- **Type**: String
- **Value**: `i-XXXXXXXXXXXXX` (your actual instance ID)

**Parameter 3: EC2 Instance Type**
- **Name**: `/slm-ft-serving/ec2/instance-type`
- **Type**: String
- **Value**: `g6.2xlarge`

**Parameter 4: ECR Repository Name**
- **Name**: `/slm-ft-serving/ecr/repository-name`
- **Type**: String
- **Value**: `slm-ft-serving-vllm`

**Parameter 5: HF Token Reference**
- **Name**: `/slm-ft-serving/secrets/hf-token`
- **Type**: String
- **Value**: `{{resolve:secretsmanager:slm-ft-serving/hf-token}}`
- This creates a reference to the Secrets Manager secret

**Parameter 6: Base Model**
- **Name**: `/slm-ft-serving/model/base-model`
- **Type**: String
- **Value**: `meta-llama/Llama-3.1-8B`

**Parameter 7: Adapter Model**
- **Name**: `/slm-ft-serving/model/adapter-model`
- **Type**: String
- **Value**: `loghoag/llama-3.1-8b-medical-ie`

**Parameter 8: vLLM API Port**
- **Name**: `/slm-ft-serving/vllm/api-port`
- **Type**: String
- **Value**: `8000`

**Parameter 9: Tensor Parallel Size**
- **Name**: `/slm-ft-serving/vllm/tensor-parallel-size`
- **Type**: String
- **Value**: `1`

**Parameter 10: CloudWatch SSM Log Group**
- **Name**: `/slm-ft-serving/cloudwatch/log-group-ssm`
- **Type**: String
- **Value**: `/aws/ssm/slm-ft-serving/commands`

**Parameter 11: CloudWatch Deployment Log Group**
- **Name**: `/slm-ft-serving/cloudwatch/log-group-deployment`
- **Type**: String
- **Value**: `/aws/deployment/slm-ft-serving`

**Parameter 12: Max Retries**
- **Name**: `/slm-ft-serving/deployment/max-retries`
- **Type**: String
- **Value**: `3`

**Parameter 13: Retry Delay**
- **Name**: `/slm-ft-serving/deployment/retry-delay-seconds`
- **Type**: String
- **Value**: `10`

**Parameter 14: EC2 Start Timeout**
- **Name**: `/slm-ft-serving/deployment/ec2-start-timeout`
- **Type**: String
- **Value**: `300`

**Parameter 15: SSM Command Timeout**
- **Name**: `/slm-ft-serving/deployment/ssm-command-timeout`
- **Type**: String
- **Value**: `600`

**Parameter 16: Health Check Timeout**
- **Name**: `/slm-ft-serving/deployment/health-check-timeout`
- **Type**: String
- **Value**: `120`

**Parameter 17: Health Check Interval**
- **Name**: `/slm-ft-serving/deployment/health-check-interval`
- **Type**: String
- **Value**: `10`

---

## 7. EC2 Instance Setup

### 7.1 Launch EC2 Instance
1. Go to **EC2 Console**: https://console.aws.amazon.com/ec2/
2. Click **Launch instances** button

### 7.2 Configure Instance Details

**Name and tags**
- **Name**: `slm-ft-serving-vllm`
- Add tags:
  - `Environment`: `production`
  - `Project`: `slm-ft-serving`
  - `Stage`: `1`

**Application and OS Images (AMI)**
1. Click **Browse more AMIs**
2. Click **AWS Marketplace AMIs** tab
3. Search for: `Deep Learning AMI GPU PyTorch`
4. Select: **Deep Learning AMI GPU PyTorch 2.x (Ubuntu 22.04)**
5. Click **Select** and accept terms

**Instance type**
- Click **Compare instance types**
- Filter by: `g6.2xlarge`
- Select: **g6.2xlarge** (8 vCPU, 32 GiB RAM, 1x NVIDIA L4 GPU)

**Key pair (login)**
- Select: **Proceed without a key pair**
- We use SSM Session Manager, no SSH keys needed

**Network settings**
- Click **Edit**
- **VPC**: Default VPC is fine
- **Subnet**: No preference (any subnet with internet access)
- **Auto-assign public IP**: Enable
- **Firewall (security groups)**: Create new security group
  - **Security group name**: `slm-ft-serving-sg`
  - **Description**: `Security group for slm-ft-serving vLLM server`

**Security group rules:**
1. Remove the default SSH rule (we use SSM)
2. Click **Add security group rule**:
   - **Type**: Custom TCP
   - **Port range**: 8000
   - **Source type**: My IP (for now) or Custom with your VPC CIDR
   - **Description**: vLLM API endpoint
3. Outbound rules: Leave as default (all traffic allowed)

**Configure storage**
- **Root volume**:
  - **Size**: 80 GiB
  - **Volume type**: gp3
  - **IOPS**: 3000 (default)
  - **Throughput**: 125 MB/s (default)
  - **Encrypted**: Yes (use default AWS managed key)
  - **Delete on termination**: Yes

**Advanced details**
- **IAM instance profile**: Select `slm-ft-serving-ec2-role`
- **Enable termination protection**: Optional (recommended for production)
- **Stop - Hibernate behavior**: Stop
- **User data**: Leave empty (we'll deploy via SSM)

### 7.3 Launch Instance
1. Review all settings in **Summary** panel
2. Click **Launch instance**
3. Wait for instance state to show **Running**
4. **IMPORTANT**: Copy the **Instance ID** (format: `i-XXXXXXXXXXXXX`)

### 7.4 Verify SSM Access
1. In EC2 console, select your instance
2. Click **Connect** button at top
3. Click **Session Manager** tab
4. If it says "Connect", SSM is working ✅
5. If it says "Waiting for instance...", wait 2-3 minutes for SSM agent to register
6. Do NOT connect yet - just verify it's available

### 7.5 Update Parameter Store with Instance ID
1. Go back to **Systems Manager → Parameter Store**
2. Find parameter `/slm-ft-serving/ec2/instance-id`
3. Click on it → **Edit**
4. Update **Value** with your instance ID from step 7.3
5. Click **Save changes**

### 7.6 Update Deployer Policy with Instance ID
1. Go to **IAM → Users → slm-ft-serving-deployer**
2. Click **Permissions** tab
3. Find and click on `slm-ft-serving-deployer-policy`
4. Click **Edit policy** → **JSON** tab
5. Replace `INSTANCE_ID` placeholder with actual instance ID in the EC2 resource ARN
6. Click **Next** → **Save changes**

### 7.7 Configure EC2 Instance (One-time Setup)
This step is optional but recommended to reduce cold start times:

1. Connect to instance via Session Manager (EC2 Console → Connect → Session Manager)
2. Run these commands:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker if not present
sudo apt install -y docker.io
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu

# Install AWS CLI v2 (if not present)
sudo apt install -y awscli

# Verify installations
docker --version
aws --version
nvidia-smi  # Should show NVIDIA L4 GPU

# Pre-pull vLLM base image (optional, saves time on first deploy)
docker pull vllm/vllm-openai:latest
```
3. Exit the session

---

## 8. CloudWatch Logs Setup

### 8.1 Create Log Groups
1. Go to **CloudWatch Console**: https://console.aws.amazon.com/cloudwatch/
2. Click **Log groups** in left sidebar

**Log Group 1: SSM Commands**
1. Click **Create log group**
2. **Log group name**: `/aws/ssm/slm-ft-serving/commands`
3. **Retention setting**: 7 days (adjust as needed)
4. Click **Create**

**Log Group 2: Deployment Logs**
1. Click **Create log group**
2. **Log group name**: `/aws/deployment/slm-ft-serving`
3. **Retention setting**: 7 days
4. Click **Create**

### 8.2 Configure SSM to Use CloudWatch Logs
1. Go to **Systems Manager → Session Manager**
2. Click **Preferences** tab
3. Click **Edit**
4. Scroll to **CloudWatch logs**:
   - **Enable**: ✅ Enable CloudWatch logging
   - **Log group name**: `/aws/ssm/slm-ft-serving/commands`
5. Click **Save**

---

## 9. GitHub Secrets Configuration

### 9.1 Add Secrets to GitHub Repository
1. Go to your GitHub repository: https://github.com/longhoag/slm-ft-serving
2. Click **Settings** tab
3. Click **Secrets and variables** → **Actions** in left sidebar
4. Click **New repository secret** for each:

**Secret 1: AWS Access Key ID**
- **Name**: `AWS_ACCESS_KEY_ID`
- **Value**: The access key ID from step 3.3 (starts with `AKIA...`)
- Click **Add secret**

**Secret 2: AWS Secret Access Key**
- **Name**: `AWS_SECRET_ACCESS_KEY`
- **Value**: The secret access key from step 3.3
- Click **Add secret**

### 9.2 Verify GitHub Actions Permissions
1. In repository **Settings → Actions → General**
2. Scroll to **Workflow permissions**
3. Ensure **Read and write permissions** is selected
4. Click **Save**

---

## 10. Verification Checklist

Before running your first deployment, verify all services are set up:

### AWS IAM
- [ ] EC2 IAM role `slm-ft-serving-ec2-role` created with:
  - [ ] 2 AWS managed policies (SSM, ECR ReadOnly)
  - [ ] 2 custom inline policies (Secrets/Parameters + CloudWatch Logs)
- [ ] IAM user `slm-ft-serving-deployer` created with:
  - [ ] 2 AWS managed policies (EC2 ReadOnly, SSM ReadOnly)
  - [ ] 1 custom policy (EC2 start/stop, SSM commands)
- [ ] IAM user `slm-ft-serving-github-actions` (optional) with:
  - [ ] 1 AWS managed policy (ECR PowerUser)
- [ ] Access keys generated and stored securely
- [ ] Deployer policy updated with actual instance ID

### Amazon ECR
- [ ] Repository `slm-ft-serving-vllm` created in us-east-1
- [ ] Lifecycle policy set (keep last 10 images)
- [ ] Repository URI noted

### AWS Secrets Manager
- [ ] Secret `slm-ft-serving/hf-token` created with HF token
- [ ] Secret value verified

### AWS Parameter Store
- [ ] All 17 parameters created under `/slm-ft-serving/` namespace
- [ ] Instance ID parameter updated with actual value
- [ ] HF token reference parameter points to Secrets Manager

### EC2
- [ ] g6.2xlarge instance launched in us-east-1
- [ ] Instance has IAM role attached
- [ ] Security group allows port 8000
- [ ] 80 GiB gp3 root volume configured
- [ ] SSM Session Manager connectivity verified
- [ ] Instance ID recorded

### CloudWatch Logs
- [ ] Log group `/aws/ssm/slm-ft-serving/commands` created
- [ ] Log group `/aws/deployment/slm-ft-serving` created
- [ ] SSM preferences configured for CloudWatch logging

### GitHub
- [ ] Repository secrets configured (AWS credentials)
- [ ] Workflow permissions set to read/write

### HuggingFace
- [ ] Account created and verified
- [ ] Access token generated
- [ ] Llama 3.1 8B access approved

### Local Development
- [ ] AWS CLI installed and configured with deployer credentials
- [ ] Poetry installed
- [ ] Project dependencies installed (`poetry install`)

---

## Testing Your Setup

### Test 1: AWS CLI Access
```bash
aws sts get-caller-identity
# Should return your AWS account details
```

### Test 2: SSM Parameter Retrieval
```bash
aws ssm get-parameter --name "/slm-ft-serving/aws/region"
# Should return us-east-1
```

### Test 3: Secrets Manager Access
```bash
aws secretsmanager get-secret-value --secret-id "slm-ft-serving/hf-token"
# Should return your HF token (check it starts with hf_)
```

### Test 4: ECR Authentication
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com
# Should return "Login Succeeded"
```

### Test 5: SSM Instance Connectivity
```bash
aws ssm describe-instance-information --filters "Key=tag:Name,Values=slm-ft-serving-vllm"
# Should return instance details showing "PingStatus": "Online"
```

---

## Cost Optimization Tips

1. **Stop EC2 when not in use**:
   - g6.2xlarge costs ~$0.75/hour
   - Use deployment script to start/stop automatically
   
2. **Monitor ECR storage**:
   - Lifecycle policy automatically cleans old images
   - Current usage visible in ECR console

3. **Set billing alerts**:
   - Go to **Billing Dashboard → Budgets**
   - Create a budget for EC2 and ECR costs

4. **Use Spot Instances (optional)**:
   - For non-production: Consider g6.2xlarge Spot for ~70% savings
   - Modify EC2 launch settings to use Spot purchasing option

---

## Troubleshooting

### Issue: SSM Session Manager not working
**Solution**: 
- Ensure IAM role has `AmazonSSMManagedInstanceCore` policy
- Wait 2-3 minutes after instance launch for agent to register
- Check instance has outbound internet access for SSM endpoints

### Issue: ECR authentication fails
**Solution**:
- Verify IAM user has ECR permissions
- Check region matches (us-east-1)
- Re-authenticate: `aws ecr get-login-password...`

### Issue: Secrets Manager access denied
**Solution**:
- Verify secret name exactly matches: `slm-ft-serving/hf-token`
- Check IAM policies include correct secret ARN
- Ensure region is us-east-1

### Issue: HuggingFace model access denied
**Solution**:
- Verify you've been approved for Llama 3.1 access
- Check token has read permissions
- Test token manually: `curl -H "Authorization: Bearer hf_..." https://huggingface.co/api/whoami`

---

## Next Steps

After completing this setup:
1. Commit and push your code to trigger GitHub Actions
2. Run the local deployment script to deploy the container
3. Monitor CloudWatch Logs for deployment progress
4. Test vLLM API endpoint once deployment completes

Refer to `docs/infrastructure.md` for detailed infrastructure architecture and deployment workflow.
