# Testing Guide - Stage 1 vLLM Server

This guide shows how to test the deployed vLLM server with the fine-tuned Llama 3.1 8B medical IE model.

## Prerequisites

- Stage 1 deployment completed successfully
- EC2 instance running with vLLM container
- Security group allows inbound traffic on port 8000

## Get EC2 Public IP

```bash
aws ec2 describe-instances \
  --instance-ids i-0245530819e118c37 \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text \
  --region us-east-1
```

Replace `<public-ip>` in the examples below with your actual public IP.

## Test 1: Health Check

Verify the vLLM server is running and healthy.

```bash
curl http://<public-ip>:8000/health
```

**Expected Response:**
```json
{"status":"ok"}
```

or similar health status indicator.

## Test 2: List Available Models

Check which models are loaded, including the LoRA adapter.

```bash
curl http://<public-ip>:8000/v1/models
```

**Expected Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "meta-llama/Llama-3.1-8B",
      "object": "model",
      "created": 1234567890,
      "owned_by": "vllm"
    }
  ]
}
```

## Test 3: Completions API (Simple Prompt)

Test basic inference with the completions endpoint.

```bash
curl http://<public-ip>:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B",
    "prompt": "Extract cancer information from this text: Patient diagnosed with stage 3 breast cancer with HER2 positive marker.",
    "max_tokens": 256,
    "temperature": 0.7
  }'
```

**Expected Response:**
```json
{
  "id": "cmpl-...",
  "object": "text_completion",
  "created": 1234567890,
  "model": "meta-llama/Llama-3.1-8B",
  "choices": [
    {
      "text": "...",
      "index": 0,
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 50,
    "total_tokens": 75
  }
}
```

## Test 4: Chat Completions API (Conversational)

Test with the chat completions endpoint for more structured interactions.

```bash
curl http://<public-ip>:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B",
    "messages": [
      {
        "role": "system",
        "content": "You are a medical information extraction assistant."
      },
      {
        "role": "user",
        "content": "Extract cancer type, stage, and biomarkers from: Patient has stage 2 lung adenocarcinoma with EGFR mutation."
      }
    ],
    "max_tokens": 256,
    "temperature": 0.7
  }'
```

**Expected Response:**
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "meta-llama/Llama-3.1-8B",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 45,
    "completion_tokens": 80,
    "total_tokens": 125
  }
}
```

## Test 5: LoRA Adapter Verification

The LoRA adapter (`loghoag/llama-3.1-8b-medical-ie`) is automatically loaded with the module name `medical-ie`.

To verify it's active, you can:

1. **Check model info** (may show adapter details):
   ```bash
   curl http://<public-ip>:8000/v1/models | jq
   ```

2. **Compare outputs** with and without medical context to see if the adapter improves medical entity extraction.

## Test 6: Medical Information Extraction Example

Test with a realistic clinical note:

```bash
curl http://<public-ip>:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B",
    "messages": [
      {
        "role": "system",
        "content": "Extract structured cancer information: cancer_type, stage, gene_mutation, biomarker, treatment, response, metastasis_site."
      },
      {
        "role": "user",
        "content": "A 62-year-old female patient presents with metastatic colorectal cancer, stage IV, with liver metastases. KRAS wild-type, MSI-high. Started on FOLFOX plus bevacizumab. Partial response after 3 cycles."
      }
    ],
    "max_tokens": 512,
    "temperature": 0.3
  }' | jq
```

**Expected Structured Output:**
The model should extract:
- `cancer_type`: colorectal cancer
- `stage`: IV / stage 4
- `gene_mutation`: KRAS wild-type
- `biomarker`: MSI-high
- `treatment`: FOLFOX plus bevacizumab
- `response`: partial response
- `metastasis_site`: liver

## Performance Testing

### Throughput Test

Test concurrent requests (requires `parallel` or similar tool):

```bash
seq 10 | parallel -j 5 "curl -s http://<public-ip>:8000/v1/completions \
  -H 'Content-Type: application/json' \
  -d '{\"model\":\"meta-llama/Llama-3.1-8B\",\"prompt\":\"Test {}\",\"max_tokens\":50}'"
```

### Latency Test

Measure response time:

```bash
time curl http://<public-ip>:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B",
    "prompt": "Extract cancer info: Patient with lung cancer.",
    "max_tokens": 100
  }'
```

## Monitoring

### Check Container Logs

Via SSM:

```bash
aws ssm send-command \
  --instance-ids i-0245530819e118c37 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["docker logs vllm-server --tail 100"]' \
  --region us-east-1
```

### Check GPU Usage

```bash
aws ssm send-command \
  --instance-ids i-0245530819e118c37 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["nvidia-smi"]' \
  --region us-east-1
```

### Check Container Status

```bash
aws ssm send-command \
  --instance-ids i-0245530819e118c37 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["docker ps --filter name=vllm-server"]' \
  --region us-east-1
```

## Troubleshooting

### Connection Refused

**Symptoms:** `curl: (7) Failed to connect`

**Fixes:**
1. Check security group allows port 8000 from your IP
2. Verify container is running: `docker ps`
3. Check instance public IP hasn't changed

### Timeout / Slow Responses

**Symptoms:** Request takes >30 seconds

**Causes:**
- First inference after startup (model warmup)
- Long prompt (>4k tokens)
- High concurrent requests (>32)

**Fixes:**
- Allow 30-60s for first request
- Reduce `max_tokens` parameter
- Implement request queuing

### Container Crashed

**Symptoms:** Health check fails, no response

**Diagnosis:**
```bash
docker logs vllm-server --tail 200
docker ps -a --filter name=vllm-server
```

**Common causes:**
- Out of memory (reduce `max_num_seqs` or `max_model_len`)
- Model download failed (check HF token)
- GPU not available (verify `nvidia-smi` works)

## API Parameters Reference

### Common Parameters

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| `max_tokens` | Maximum tokens to generate | 16 | 1-8192 |
| `temperature` | Sampling randomness | 1.0 | 0.0-2.0 |
| `top_p` | Nucleus sampling threshold | 1.0 | 0.0-1.0 |
| `frequency_penalty` | Penalize repeated tokens | 0.0 | -2.0-2.0 |
| `presence_penalty` | Penalize new topics | 0.0 | -2.0-2.0 |
| `stop` | Stop sequences | null | array of strings |

### Model Constraints (Current Configuration)

- **Max context length:** 8,192 tokens (~6,000 words)
- **Max concurrent requests:** 32
- **GPU memory utilization:** 90%
- **Tensor parallelism:** 1 (single GPU)

## Cost Considerations

### EC2 Instance Costs

- **Running:** $0.864/hour (g6.2xlarge)
- **Stopped:** $0.10/GB/month for EBS (80GB = $8/month)

### Cost Optimization Tips

1. **Stop instance when not in use:**
   ```bash
   aws ec2 stop-instances --instance-ids i-0245530819e118c37 --region us-east-1
   ```

2. **Models persist on EBS** - No re-download on restart

3. **Use CloudWatch metrics** to track usage patterns

## Next Steps

- **Stage 2:** FastAPI gateway layer for request validation and structured parsing
- **Stage 3:** React/Next.js frontend for user interface
- **Stage 4:** CloudWatch monitoring and observability dashboards

---

**Questions?** Check DEPLOYMENT.md for deployment details or INFRASTRUCTURE.md for architecture overview.
