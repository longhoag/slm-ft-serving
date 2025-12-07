# Deployment Guide - Stage 1

This guide explains how to deploy the vLLM server to EC2 using the `deploy.py` script.

## Prerequisites

- AWS credentials configured (`aws configure` or environment variables)
- ECR image pushed (via GitHub Actions workflow)
- EC2 instance set up with IAM role and SSM agent
- All AWS infrastructure configured (see SETUP-GUIDE.md)
- Poetry installed and dependencies installed: `poetry install`

## Quick Start

### Full Deployment (First Time)

```bash
cd /path/to/slm-ft-serving
poetry run python scripts/deploy.py
```

This will:
1. Start EC2 instance (if stopped)
2. Wait for instance to be ready (~3-5 minutes)
3. Create Docker volume `huggingface-cache` on EBS
4. Pull latest Docker image from ECR
5. Retrieve HuggingFace token from Secrets Manager
6. Run vLLM container with volume mount
7. Validate deployment via health check

**First deployment:** ~25-35 minutes (includes model download: 32 GB)  
**Subsequent deployments:** ~5-10 minutes (models cached on EBS)

### Deploy Specific Image Tag

```bash
poetry run python scripts/deploy.py --image-tag abc123def
```

Uses image tagged with specific git SHA from ECR.

### Quick Restart (No New Image)

```bash
poetry run python scripts/deploy.py --quick-restart
```

Just restarts the existing container without pulling a new image or recreating the container. Fastest option when no code changes.

### Skip Instance Start (If Already Running)

```bash
poetry run python scripts/deploy.py --skip-start
```

Useful if you manually started the instance or it's already running.

### Skip Health Check Validation

```bash
poetry run python scripts/deploy.py --skip-validation
```

Deploys without waiting for health check to pass. Not recommended for production.

## What Happens During Deployment

### 1. Configuration Loading
- Reads `config/deployment.yml`
- Retrieves SSM parameters:
  - `/slm-ft-serving/aws/region` → AWS region
  - `/slm-ft-serving/ec2/instance-id` → EC2 instance ID
  - `/slm-ft-serving/secrets/hf-token` → Secrets Manager reference

### 2. EC2 Instance Start
- Checks instance state
- Starts if stopped
- Waits for `running` state
- Waits for status checks to pass
- Timeout: 300 seconds (5 minutes)

### 3. Container Deployment via SSM

Sends SSM run command that executes:

```bash
# Create Docker volume (persists models on EBS)
docker volume create huggingface-cache

# Stop and remove old container (if exists)
docker stop vllm-server
docker rm vllm-server

# Login to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <ecr-registry>

# Pull latest image
docker pull <ecr-registry>/slm-ft-serving-vllm:latest

# Retrieve HF token from Secrets Manager
HF_TOKEN=$(aws secretsmanager get-secret-value --secret-id slm-ft-serving/hf-token ...)

# Run container with volume mount
docker run -d \
  --name vllm-server \
  --gpus all \
  -p 8000:8000 \
  -e HF_TOKEN="$HF_TOKEN" \
  -e MODEL_NAME="meta-llama/Llama-3.1-8B" \
  -e ADAPTER_NAME="loghoag/llama-3.1-8b-medical-ie" \
  -v huggingface-cache:/root/.cache/huggingface \
  <ecr-image>
```

### 4. Health Check Validation

Polls `http://localhost:8000/health` endpoint:
- Interval: 10 seconds
- Timeout: 120 seconds
- Returns success when vLLM server responds

## Model Persistence on EBS

Models are stored in Docker volume `huggingface-cache` which maps to:
- **Host (EBS root volume):** `/var/lib/docker/volumes/huggingface-cache/_data/`
- **Container:** `/root/.cache/huggingface/`

**Storage:**
- Base model: `meta-llama/Llama-3.1-8B` (~32 GB)
- LoRA adapter: `loghoag/llama-3.1-8b-medical-ie` (~72 MB)

**Persistence:**
- ✅ Persists across container recreations (`docker rm`)
- ✅ Persists across EC2 instance stop/start
- ✅ Survives deployments (no re-download)
- ❌ Only deleted if you explicitly `docker volume rm huggingface-cache`

## Monitoring Deployment

### CloudWatch Logs

SSM command output is logged to:
```
/aws/ssm/slm-ft-serving/commands
```

View in AWS Console or via CLI:
```bash
aws logs tail /aws/ssm/slm-ft-serving/commands --follow --region us-east-1
```

### Check Container Status

Via SSM Session Manager:
```bash
aws ssm start-session --target <instance-id> --region us-east-1

# On EC2 instance:
docker ps
docker logs vllm-server
docker exec vllm-server nvidia-smi  # Check GPU usage
```

### Health Check

Once deployed, test the API:
```bash
curl http://<instance-public-ip>:8000/health
curl http://<instance-public-ip>:8000/v1/models
```

## Troubleshooting

### Deployment Fails at Model Download

**Error:** Timeout during first deployment

**Solution:** First deployment takes 25-35 minutes for model download. Increase timeout:
```yaml
# config/deployment.yml
deployment:
  ssm_command_timeout_seconds: 1800  # 30 minutes
  health_check_timeout_seconds: 300  # 5 minutes
```

### Container Exits Immediately

**Check logs:**
```bash
python3 scripts/deploy.py --skip-validation
# Then manually check:
aws ssm send-command --instance-ids <id> --document-name "AWS-RunShellScript" \
  --parameters 'commands=["docker logs vllm-server --tail 100"]'
```

**Common causes:**
- Invalid HuggingFace token
- Out of GPU memory (g6.2xlarge has 23GB, model needs ~20GB)
- Model download failed

### Health Check Times Out

**Symptoms:** Container running but health check fails

**Check vLLM logs:**
```bash
docker logs vllm-server
```

**Common causes:**
- Model still loading (can take 2-5 minutes on first run)
- Port 8000 not accessible
- vLLM crashed during startup

### Volume Not Mounting

**Verify volume exists:**
```bash
docker volume ls | grep huggingface-cache
docker volume inspect huggingface-cache
```

**Check mount in container:**
```bash
docker exec vllm-server ls -lah /root/.cache/huggingface/
```

## Cost Optimization

### Stop Instance When Not in Use

```bash
aws ec2 stop-instances --instance-ids <id> --region us-east-1
```

**Costs while stopped:**
- ✅ EBS storage: $0.10/GB/month (80GB = $8/month)
- ❌ No EC2 compute charges
- ❌ No data transfer charges

**Models persist on EBS.** Next deployment will be fast (no re-download).

### Start Instance for Deployment

```bash
poetry run python scripts/deploy.py  # Automatically starts instance
```

## Advanced Usage

### Deployment Script Help

```bash
poetry run python scripts/deploy.py --help
```

### Custom Configuration

Edit `config/deployment.yml` to adjust:
- Timeouts
- Retry attempts
- Port numbers
- Model names
- Volume paths

### Rollback to Previous Image

```bash
# Find previous image SHA in ECR
aws ecr describe-images --repository-name slm-ft-serving-vllm --region us-east-1

# Deploy specific SHA
poetry run python scripts/deploy.py --image-tag <previous-sha>
```

## Next Steps

- **Stage 2:** FastAPI gateway layer (planned)
- **Stage 3:** React/Next.js frontend (planned)
- **Stage 4:** CloudWatch monitoring and dashboards (planned)

---

**Questions?** Check INFRASTRUCTURE.md for architecture details or SETUP-GUIDE.md for initial setup.
