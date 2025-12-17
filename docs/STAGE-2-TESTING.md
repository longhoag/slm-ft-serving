# Stage 2 Testing Guide - FastAPI Gateway + vLLM Stack

This guide walks you through testing the complete Stage 2 deployment: vLLM server + FastAPI gateway orchestrated via Docker Compose.

## Prerequisites

- ✅ GitHub Actions successfully built and pushed both images to ECR
- ✅ EC2 instance exists (i-0245530819e118c37) with Docker + Docker Compose
- ✅ AWS credentials configured locally (`slm-ft-serving-deployer`)
- ✅ Poetry environment set up

## Stage 2 Architecture

```
EC2 Instance (g6.2xlarge)
├── vLLM Server (port 8000)
│   └── Model: Llama 3.1 8B + medical-ie adapter
├── FastAPI Gateway (port 8080)
│   ├── /health (gateway health)
│   ├── /health/vllm (backend health)
│   ├── /api/v1/extract (medical extraction)
│   └── /docs (Swagger UI)
└── Docker Network: slm-network
```

---

## Step 1: Deploy the Stack

### 1.1 Start EC2 and Deploy

```bash
# From project root
cd /Volumes/deuxSSD/Developer/slm-ft-serving

# Deploy with EC2 auto-start
poetry run python scripts/deploy.py

# OR if EC2 is already running
poetry run python scripts/deploy.py --skip-start
```

**Expected output:**
```
=== Stage 2 Deployment Starting ===
Deploying Docker Compose stack: vLLM + FastAPI Gateway
Loading configuration from config/deployment.yml
Resolving SSM parameters...
Instance ID: i-0245530819e118c37
...
✅ vLLM server: http://<instance-ip>:8000
✅ Gateway API: http://<instance-ip>:8080
✅ API Documentation: http://<instance-ip>:8080/docs
```

### 1.2 Get EC2 Instance IP

```bash
# Get public IP address
aws ec2 describe-instances \
  --instance-ids i-0245530819e118c37 \
  --region us-east-1 \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text
```

Save this IP for testing (referred to as `<EC2-IP>` below).

---

## Step 2: Health Check Tests

### 2.1 Gateway Health Check

```bash
# Test gateway is running
curl http://<EC2-IP>:8080/health

# Expected response:
# {"status":"healthy","service":"Medical IE Gateway","version":"0.1.0"}
```

### 2.2 vLLM Backend Health Check

```bash
# Test gateway → vLLM communication
curl http://<EC2-IP>:8080/health/vllm

# Expected response:
# {"status":"healthy","vllm_backend":"available"}
```

### 2.3 Direct vLLM Health Check

```bash
# Test vLLM server directly
curl -v http://<EC2-IP>:8000/health

# Expected response: (empty body with HTTP 200)
```

**⚠️ Troubleshooting:**
- If vLLM health fails: Model may still be loading (takes 4-5 minutes on first start)
- Check logs: `ssh via SSM → docker logs vllm-server`

---

## Step 3: Medical Extraction Tests

### 3.1 Simple Test Case

```bash
# Test medical information extraction
curl -X POST http://<EC2-IP>:8080/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient diagnosed with stage 3 breast cancer with HER2 positive marker. Started on Herceptin treatment."
  }'
```

**Expected response:**
```json
{
  "cancer_type": "breast cancer",
  "stage": "stage 3",
  "gene_mutation": null,
  "biomarker": "HER2 positive",
  "treatment": "Herceptin",
  "response": null,
  "metastasis_site": null,
  "raw_output": "...",
  "tokens_used": 45
}
```

### 3.2 Complex Test Case

```bash
curl -X POST http://<EC2-IP>:8080/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "65-year-old male with lung adenocarcinoma, EGFR L858R mutation detected. Initiated on Osimertinib 80mg daily. CT scan after 3 months shows partial response with 40% tumor reduction. No metastasis observed.",
    "temperature": 0.1,
    "max_tokens": 256
  }'
```

**Expected response:**
```json
{
  "cancer_type": "lung adenocarcinoma",
  "stage": null,
  "gene_mutation": "EGFR L858R",
  "biomarker": null,
  "treatment": "Osimertinib 80mg daily",
  "response": "partial response",
  "metastasis_site": "no metastasis",
  "raw_output": "...",
  "tokens_used": 78
}
```

### 3.3 Empty/Invalid Input

```bash
# Test error handling
curl -X POST http://<EC2-IP>:8080/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": ""
  }'

# Expected: HTTP 422 Validation Error
```

---

## Step 4: Interactive API Testing

### 4.1 Swagger UI

Open in browser:
```
http://<EC2-IP>:8080/docs
```

**Features to test:**
- ✅ View all endpoints
- ✅ Try `/health` endpoints
- ✅ Test `/api/v1/extract` with interactive form
- ✅ See request/response schemas
- ✅ Check validation errors

### 4.2 ReDoc (Alternative API Docs)

```
http://<EC2-IP>:8080/redoc
```

---

## Step 5: Container Status Verification

### 5.1 Check Container Status via SSM

```bash
# Send SSM command to check containers
aws ssm send-command \
  --instance-ids i-0245530819e118c37 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["cd /home/ec2-user && docker-compose ps"]' \
  --region us-east-1
```

**Expected output:**
```
NAME                IMAGE                                                          STATUS
vllm-server        855386719590.dkr.ecr.us-east-1.amazonaws.com/slm-ft-serving-vllm:latest      Up 10 minutes (healthy)
fastapi-gateway    855386719590.dkr.ecr.us-east-1.amazonaws.com/slm-ft-serving-gateway:latest   Up 10 minutes (healthy)
```

### 5.2 Check Logs

**Gateway logs:**
```bash
# Via SSM
aws ssm send-command \
  --instance-ids i-0245530819e118c37 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["docker logs fastapi-gateway --tail 50"]' \
  --region us-east-1
```

**vLLM logs:**
```bash
# Via SSM
aws ssm send-command \
  --instance-ids i-0245530819e118c37 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["docker logs vllm-server --tail 50"]' \
  --region us-east-1
```

---

## Step 6: Performance & Load Testing

### 6.1 Response Time Test

```bash
# Measure response time
time curl -X POST http://<EC2-IP>:8080/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient with metastatic melanoma, BRAF V600E mutation. Started on combination therapy with Dabrafenib and Trametinib."
  }'
```

**Expected:** 
- First request: 2-5 seconds (model warm-up)
- Subsequent requests: 0.5-2 seconds

### 6.2 Concurrent Requests

```bash
# Test with 5 concurrent requests
for i in {1..5}; do
  curl -X POST http://<EC2-IP>:8080/api/v1/extract \
    -H "Content-Type: application/json" \
    -d '{"text":"Patient diagnosed with pancreatic cancer."}' &
done
wait

echo "All requests completed"
```

### 6.3 CORS Test (if needed)

```bash
# Test CORS headers
curl -X OPTIONS http://<EC2-IP>:8080/api/v1/extract \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

**Expected headers:**
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: *
```

---

## Step 7: Validation Checklist

### ✅ Deployment Success Criteria

- [ ] EC2 instance started successfully
- [ ] Both Docker images pulled from ECR
- [ ] Both containers running (`docker-compose ps` shows "Up")
- [ ] Gateway health check returns `{"status":"healthy"}`
- [ ] vLLM health check returns 200 OK
- [ ] Medical extraction returns structured JSON
- [ ] Swagger UI loads at `/docs`
- [ ] Response time < 5 seconds
- [ ] No errors in container logs
- [ ] CORS headers present (if testing from browser)

### ✅ Stage 2 Components Verified

- [ ] vLLM server serves on port 8000
- [ ] FastAPI gateway serves on port 8080
- [ ] Docker Compose orchestration working
- [ ] Health check dependencies working (gateway waits for vLLM)
- [ ] Docker network communication (gateway → vLLM via `http://vllm:8000`)
- [ ] Model persistence on EBS volume
- [ ] Chat template working (Llama 3.1 format)

---

## Step 8: Cleanup & Cost Management

### 8.1 Stop EC2 Instance (Save Costs)

```bash
# Stop instance when not testing
aws ec2 stop-instances \
  --instance-ids i-0245530819e118c37 \
  --region us-east-1

# Verify stopped
aws ec2 describe-instances \
  --instance-ids i-0245530819e118c37 \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text
```

**Expected:** `stopping` → `stopped`

### 8.2 Monitor Costs

**Current Stage 2 costs:**
- EC2 g6.2xlarge: ~$0.75/hour (only when running)
- EBS 80GB: ~$8/month (always)
- ECR storage: ~$1.80/month (with lifecycle policy)
- Data transfer: Minimal (within AWS)

**Total monthly (if running 8 hours/day):** ~$190/month

---

## Troubleshooting

### Issue: Gateway can't reach vLLM

**Symptoms:** `/health/vllm` returns `{"status":"unhealthy","vllm_backend":"unavailable"}`

**Diagnosis:**
```bash
# Check Docker network
aws ssm send-command \
  --instance-ids i-0245530819e118c37 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["docker network inspect slm-network"]' \
  --region us-east-1

# Check VLLM_BASE_URL in gateway
aws ssm send-command \
  --instance-ids i-0245530819e118c37 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["docker exec fastapi-gateway env | grep VLLM"]' \
  --region us-east-1
```

**Solution:** Should show `VLLM_BASE_URL=http://vllm:8000`

### Issue: Model loading too slow

**Symptoms:** vLLM health check times out (>6 minutes)

**Diagnosis:**
```bash
# Check model download progress
docker logs vllm-server --tail 100
```

**Solution:** 
- First deployment: Wait 4-5 minutes for model download (32 GB)
- Subsequent deployments: Model cached on EBS (loads in 1-2 minutes)

### Issue: Out of memory errors

**Symptoms:** vLLM crashes with CUDA OOM

**Diagnosis:**
```bash
# Check GPU memory
aws ssm send-command \
  --instance-ids i-0245530819e118c37 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["nvidia-smi"]' \
  --region us-east-1
```

**Solution:** Reduce `--max-num-seqs` or `--gpu-memory-utilization` in Dockerfile

---

## Next Steps

After Stage 2 testing is complete:

1. **Document test results** - Record response times, error rates
2. **Plan Stage 3** - Frontend deployment on Vercel
3. **Set up monitoring** - CloudWatch metrics for Stage 4
4. **Security hardening** - Restrict CORS origins for production

---

## Quick Reference

**Key URLs:**
- Gateway API: `http://<EC2-IP>:8080`
- Gateway Health: `http://<EC2-IP>:8080/health`
- vLLM Health: `http://<EC2-IP>:8000/health`
- API Docs: `http://<EC2-IP>:8080/docs`
- Extraction: `POST http://<EC2-IP>:8080/api/v1/extract`

**Key Commands:**
```bash
# Deploy
poetry run python scripts/deploy.py

# Get IP
aws ec2 describe-instances --instance-ids i-0245530819e118c37 --query 'Reservations[0].Instances[0].PublicIpAddress' --output text

# Test health
curl http://<EC2-IP>:8080/health

# Test extraction
curl -X POST http://<EC2-IP>:8080/api/v1/extract -H "Content-Type: application/json" -d '{"text":"Patient with lung cancer."}'

# Stop EC2
aws ec2 stop-instances --instance-ids i-0245530819e118c37 --region us-east-1
```

---

**Stage 2 Testing Complete!** 🎉

If all tests pass, you're ready to move to Stage 3 (Frontend) or Stage 4 (Monitoring).
