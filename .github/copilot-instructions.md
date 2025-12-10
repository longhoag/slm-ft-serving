# Copilot Instructions for slm-ft-serving

## Project Overview
This project serves a fine-tuned Llama 3.1 8B model (qLoRA 4-bit quantization) specialized for medical cancer information extraction. The model uses a base model (`meta-llama/Llama-3.1-8B`) with custom adapters (`loghoag/llama-3.1-8b-medical-ie`) for structured entity extraction from clinical text.

## Architecture Philosophy
**Staged Development**: This project follows a strict stage-by-stage build approach. Do NOT create files or infrastructure for future stages (2-4) when working on Stage 1. Each stage must be complete and tested before moving forward.

### Current Stage Progression
- **Stage 1** ✅ **COMPLETE**: vLLM server on EC2 g6.2xlarge (us-east-1)
- **Stage 2** 🚧 **IN PROGRESS**: FastAPI gateway layer on same EC2 instance
- **Stage 3** (Future): React/Next.js frontend on Vercel (separate repo)  
- **Stage 4** (Future): CloudWatch monitoring and observability

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

## Stage 2: FastAPI Gateway Layer

### Overview
Build a FastAPI gateway that runs on the same EC2 instance as vLLM, providing:
- Request validation and structured input/output
- Medical entity extraction with proper prompt formatting
- Rate limiting and error handling
- Health checks and monitoring
- Chat template support for vLLM

### Architecture
```
Client → FastAPI Gateway (port 8080) → vLLM Server (port 8000)
         └─ Same EC2 instance
         └─ Docker Compose orchestration
```

### Implementation Steps

#### Step 1: Add Chat Template to vLLM (Enable /v1/chat/completions)

**1.1 Create `chat_template.jinja`** in project root:
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

**1.2 Update Dockerfile** - Add after `WORKDIR /app`:
```dockerfile
# Copy chat template for Llama 3.1 (required for chat completions API)
COPY chat_template.jinja /app/chat_template.jinja
```

**1.3 Update Dockerfile CMD** - Add `--chat-template` flag:
```dockerfile
CMD ["sh", "-c", "vllm serve $MODEL_NAME --enable-lora --lora-modules medical-ie=$ADAPTER_NAME --tensor-parallel-size $TENSOR_PARALLEL_SIZE --host $HOST --port $PORT --trust-remote-code --disable-log-requests --max-model-len 8192 --max-num-seqs 32 --gpu-memory-utilization 0.90 --chat-template /app/chat_template.jinja"]
```

**1.4 Rebuild and deploy vLLM:**
```bash
git add chat_template.jinja Dockerfile
git commit -m "Add Llama 3.1 chat template for vLLM"
git push
# Wait for GitHub Actions to build
poetry run python scripts/deploy.py --skip-start
```

#### Step 2: Create FastAPI Gateway Application

**2.1 Project structure:**
```
gateway/
├── __init__.py
├── main.py              # FastAPI app entry point
├── models.py            # Pydantic models for request/response
├── services/
│   ├── __init__.py
│   └── vllm_client.py   # vLLM HTTP client wrapper
├── routers/
│   ├── __init__.py
│   ├── health.py        # Health check endpoints
│   └── extraction.py    # Medical IE endpoints
└── utils/
    ├── __init__.py
    ├── prompts.py       # Prompt templates for medical IE
    └── parsers.py       # Response parsing logic
```

**2.2 Core dependencies (add to pyproject.toml):**
```toml
[tool.poetry.dependencies]
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
pydantic = "^2.9.0"
httpx = "^0.27.0"
python-multipart = "^0.0.12"
pydantic-settings = "^2.6.0"
```

**2.3 Key files to implement:**

**gateway/models.py** - Request/response schemas:
```python
from pydantic import BaseModel, Field
from typing import Optional, List

class MedicalExtractionRequest(BaseModel):
    text: str = Field(..., description="Clinical text to extract information from")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=8192)

class MedicalExtractionResponse(BaseModel):
    cancer_type: Optional[str] = None
    stage: Optional[str] = None
    gene_mutation: Optional[str] = None
    biomarker: Optional[str] = None
    treatment: Optional[str] = None
    response: Optional[str] = None
    metastasis_site: Optional[str] = None
    raw_output: str = Field(..., description="Raw model output")
    tokens_used: int
```

**gateway/services/vllm_client.py** - vLLM client:
```python
import httpx
from loguru import logger

class VLLMClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def health_check(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"vLLM health check failed: {e}")
            return False
    
    async def completions(self, model: str, prompt: str, max_tokens: int, temperature: float):
        response = await self.client.post(
            f"{self.base_url}/v1/completions",
            json={
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        )
        response.raise_for_status()
        return response.json()
```

**gateway/utils/prompts.py** - Prompt templates:
```python
def medical_extraction_prompt(text: str) -> str:
    return f"""Extract structured cancer information (cancer_type, stage, gene_mutation, biomarker, treatment, response, metastasis_site) from this text:

{text}

Structured Data:"""
```

**gateway/routers/extraction.py** - Extraction endpoint:
```python
from fastapi import APIRouter, HTTPException
from gateway.models import MedicalExtractionRequest, MedicalExtractionResponse
from gateway.services.vllm_client import VLLMClient
from gateway.utils.prompts import medical_extraction_prompt
from gateway.utils.parsers import parse_medical_output

router = APIRouter(prefix="/api/v1", tags=["extraction"])
vllm_client = VLLMClient()

@router.post("/extract", response_model=MedicalExtractionResponse)
async def extract_medical_info(request: MedicalExtractionRequest):
    prompt = medical_extraction_prompt(request.text)
    
    result = await vllm_client.completions(
        model="medical-ie",
        prompt=prompt,
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )
    
    raw_text = result["choices"][0]["text"]
    parsed = parse_medical_output(raw_text)
    
    return MedicalExtractionResponse(
        **parsed,
        raw_output=raw_text,
        tokens_used=result["usage"]["total_tokens"]
    )
```

#### Step 3: Dockerize FastAPI Gateway

**3.1 Create `gateway/Dockerfile`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev dependencies in production)
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY gateway/ ./gateway/

# Expose gateway port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### Step 4: Docker Compose Orchestration

**4.1 Create `docker-compose.yml`:**
```yaml
version: '3.8'

services:
  vllm:
    image: ${ECR_REGISTRY}/slm-ft-serving-vllm:latest
    container_name: vllm-server
    ports:
      - "8000:8000"
    volumes:
      - huggingface-cache:/root/.cache/huggingface
    environment:
      - HF_TOKEN=${HF_TOKEN}
      - MODEL_NAME=meta-llama/Llama-3.1-8B
      - ADAPTER_NAME=loghoag/llama-3.1-8b-medical-ie
      - PORT=8000
      - HOST=0.0.0.0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s

  gateway:
    image: ${ECR_REGISTRY}/slm-ft-serving-gateway:latest
    container_name: fastapi-gateway
    ports:
      - "8080:8080"
    environment:
      - VLLM_BASE_URL=http://vllm:8000
    depends_on:
      vllm:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  huggingface-cache:
    external: true
```

#### Step 5: Update Deployment Scripts

**5.1 Update `scripts/deploy.py`:**
- Add logic to deploy docker-compose stack
- Pull both vLLM and gateway images
- Use `docker-compose up -d` instead of `docker run`
- Wait for both services to be healthy

**5.2 Update GitHub Actions:**
- Add second build job for gateway image
- Push both images to ECR with same tag
- Trigger on changes to gateway/ directory

#### Step 6: Testing and Validation

**6.1 Local testing:**
```bash
# Test gateway health
curl http://<ec2-ip>:8080/health

# Test extraction endpoint
curl http://<ec2-ip>:8080/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient diagnosed with stage 3 breast cancer with HER2 positive marker."
  }'
```

**6.2 Create `scripts/test_gateway.py`:**
- Automated tests for gateway endpoints
- Validate structured output parsing
- Test error handling and rate limiting

#### Step 7: Documentation

**7.1 Create `docs/STAGE-2-GATEWAY.md`:**
- Gateway API documentation
- Request/response examples
- Deployment instructions
- Troubleshooting guide

### Stage 2 Success Criteria
- ✅ Chat template added to vLLM (chat completions working)
- ✅ FastAPI gateway running on port 8080
- ✅ Medical extraction endpoint returns structured JSON
- ✅ Docker Compose orchestrates both services
- ✅ Health checks passing for both containers
- ✅ Gateway waits for vLLM readiness
- ✅ Deployment script updated for compose stack
- ✅ Tests passing for gateway endpoints

## Future Stages

**Stage 3 Preview** (Frontend):
- React/Next.js on Vercel (separate repo)
- Route53 DNS → ALB → EC2

**Stage 4 Preview** (Observability):
- CloudWatch GPU metrics
- vLLM container logs
- Dashboarding
