# Copilot Instructions for slm-ft-serving

## Project Overview
This project serves a fine-tuned Llama 3.1 8B model (qLoRA 4-bit quantization) specialized for medical cancer information extraction. The model uses a base model (`meta-llama/Llama-3.1-8B`) with custom adapters (`loghoag/llama-3.1-8b-medical-ie`) for structured entity extraction from clinical text.

## Architecture Philosophy
**Staged Development**: This project follows a strict stage-by-stage build approach. Do NOT create files or infrastructure for future stages (2-4) when working on Stage 1. Each stage must be complete and tested before moving forward.

### Current Stage Progression
- **Stage 1** (Planning → Implementation): vLLM server on EC2 g6.2xlarge (us-east-1)
- **Stage 2** (Future): FastAPI gateway layer on same EC2 instance
- **Stage 3** (Future): React/Next.js frontend on Vercel (separate repo)  
- **Stage 4** (Future): CloudWatch monitoring and observability

> **Note**: Stages 2-4 details intentionally omitted from instructions. Update this file when entering each new stage.

## Critical Model Serving Details
When implementing vLLM serving code, always:
- Load base model: `meta-llama/Llama-3.1-8B`
- Load adapter: `loghoag/llama-3.1-8b-medical-ie`
- Model expects structured input: `{"instruction": "...", "input": "...", "output": {...}}`
- Output schema: `cancer_type`, `stage`, `gene_mutation`, `biomarker`, `treatment`, `response`, `metastasis_site`

## Infrastructure & Deployment Patterns

### Remote Execution via SSM (No SSH)
All deployment commands execute from local terminal → AWS SSM → EC2 instance. Never create SSH-based deployment scripts or `.pem` key references.

**Deployment Flow:**
1. GitHub Actions: Build Docker image → Push to ECR
2. Local script: Start EC2 instance → Wait for status OK
3. Local script: Send SSM run command to deploy

### Secrets Management Pattern
**Never use `.env` files**. All secrets flow through:
```
AWS Secrets Manager → SSM Parameter Store → EC2 instance
```

Required secrets/keys:
- `HF_TOKEN`: HuggingFace access token (for Llama model download)
- AWS credentials (access key + secret) - used for ECR authentication and SSM

### CloudWatch Integration
- Log all SSM command outputs and sessions to CloudWatch
- Configure CloudWatch log groups for deployment scripts

## Development Standards

### Python Dependency Management
Use **Poetry** for all Python dependencies. Never use `pip install` directly in scripts or Dockerfiles without Poetry context.

### Logging Standard
Use **loguru** for all logging. Do not use `print()` statements in Python scripts. Example:
```python
from loguru import logger
logger.info("Starting deployment...")
logger.error(f"Failed to connect: {error}")
```

### Error Handling Philosophy
Commands must be "execute with precaution to errors" - implement failsafe measures:
- Check EC2 instance status before proceeding
- Verify SSM command execution success
- Validate container health before marking deployment complete
- Implement rollback logic for failed deployments

## CI/CD Architecture (Stage 1)
- **GitHub Actions**: Fully automated Docker build + ECR push
- **Local Deployment Scripts**: SSM-based deployment orchestration (not in CI/CD)
  - Use **boto3** (AWS SDK) or **AWS CLI** depending on context complexity
  - Prefer boto3 for programmatic control with retry logic and status checks
  - Use AWS CLI for simple, scriptable SSM commands
- **Storage**: 80 GiB EBS root volume
  - Model: 32.1 GB (base Llama 3.1 8B) + 71.8 MB (adapters)
  - Docker layers: ~15-20 GB (vLLM image + dependencies)
  - OS + overhead: ~10 GB
  - Buffer for logs/cache: ~20 GB

## Key Project Constraints
1. **No premature architecture**: Don't create Stage 2/3/4 structure during Stage 1
2. **SSM-only remote execution**: No SSH, no `.pem` keys
3. **Secrets Manager only**: No `.env` files or hardcoded credentials
4. **Poetry for Python**: No raw pip commands
5. **Loguru for logging**: No print statements

## Stage 1 Completion Status
✅ **COMPLETE** - vLLM server successfully deployed and validated
- Docker image with vLLM + Llama 3.1 8B + LoRA adapter (medical-ie)
- EC2 g6.2xlarge deployment via SSM (no SSH)
- Model persistence on EBS via Docker named volumes
- Health checks passing, inference validated
- Structured medical entity extraction working correctly

### Stage 1 Known Limitation
- `/v1/chat/completions` endpoint not available (requires chat template)
- Currently using `/v1/completions` endpoint with raw prompts
- **Fix deferred to Stage 2** (when implementing FastAPI gateway)

## Future Stages
Instructions for Stages 2-4 will be added to this file as the project progresses. Do not implement or create infrastructure for future stages prematurely.

**Stage 2 Preview** (FastAPI gateway):
- API gateway layer on same EC2 instance
- Health checks + linting + API tests
- Gateway waits for vLLM readiness
- **Add chat template support** for `/v1/chat/completions` endpoint

### Stage 2: Chat Template Implementation (TODO)
When implementing Stage 2, add Llama 3.1 chat template to enable `/v1/chat/completions`:

1. **Create `chat_template.jinja`** in project root:
```jinja
{{- bos_token }}
{%- if messages[0]['role'] == 'system' %}
    {%- set system_message = messages[0]['content'] %}
    {%- set loop_messages = messages[1:] %}
{%- else %}
    {%- set loop_messages = messages %}
{%- endif %}
{%- if system_message is defined %}
    {{- '<|start_header_id|>system<|end_header_id|>\n\n' + system_message + '<|eot_id|>' }}
{%- endif %}
{%- for message in loop_messages %}
    {%- if message['role'] == 'user' %}
        {{- '<|start_header_id|>user<|end_header_id|>\n\n' + message['content'] + '<|eot_id|>' }}
    {%- elif message['role'] == 'assistant' %}
        {{- '<|start_header_id|>assistant<|end_header_id|>\n\n' + message['content'] + '<|eot_id|>' }}
    {%- endif %}
{%- endfor %}
{%- if add_generation_prompt %}
    {{- '<|start_header_id|>assistant<|end_header_id|>\n\n' }}
{%- endif %}
```

2. **Update Dockerfile** - Add after `WORKDIR /app`:
```dockerfile
# Copy chat template for Llama 3.1 (required for chat completions API)
COPY chat_template.jinja /app/chat_template.jinja
```

3. **Update Dockerfile CMD** - Add `--chat-template` flag:
```dockerfile
CMD ["sh", "-c", "vllm serve $MODEL_NAME --enable-lora --lora-modules medical-ie=$ADAPTER_NAME --tensor-parallel-size $TENSOR_PARALLEL_SIZE --host $HOST --port $PORT --trust-remote-code --disable-log-requests --max-model-len 8192 --max-num-seqs 32 --gpu-memory-utilization 0.90 --chat-template /app/chat_template.jinja"]
```

**Stage 3 Preview** (Frontend):
- React/Next.js on Vercel (separate repo)
- Route53 DNS → ALB → EC2

**Stage 4 Preview** (Observability):
- CloudWatch GPU metrics
- vLLM container logs
- Dashboarding
