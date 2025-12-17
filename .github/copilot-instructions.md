# Copilot Instructions for slm-ft-serving

## Repository Context
**This is the BACKEND/SERVER repository** containing:
- vLLM inference server (Llama 3.1 8B + medical-ie LoRA adapter)
- FastAPI gateway with medical extraction API
- Docker Compose orchestration
- AWS deployment scripts (EC2, ECR, SSM)

**Separate Frontend Repository**: Stage 3 frontend (React/Next.js on Vercel) is in a different repo but consumes this backend's API.

**Cross-Repository Work**: 
- Frontend changes may require backend API updates (new endpoints, response formats)
- Backend API changes should be communicated to frontend repo
- Both repos carry their own implementations and deployment logic

## Project Overview
This project serves a fine-tuned Llama 3.1 8B model (qLoRA 4-bit quantization) specialized for medical cancer information extraction. The model uses a base model (`meta-llama/Llama-3.1-8B`) with custom adapters (`loghoag/llama-3.1-8b-medical-ie`) for structured entity extraction from clinical text.

## Architecture Philosophy
**Staged Development**: This project follows a strict stage-by-stage build approach. Each stage must be complete and tested before moving forward.

### Current Stage Progression
- **Stage 1** ✅ **COMPLETE**: vLLM server with LoRA adapter on EC2 g6.2xlarge (us-east-1)
- **Stage 2** ✅ **COMPLETE**: FastAPI gateway layer orchestrated via Docker Compose on same EC2 instance
- **Stage 3** 🚧 **IN PROGRESS**: React/Next.js frontend on Vercel (separate repo)
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
- Chat template added for `/v1/chat/completions` support

## Stage 2 Completion Status
✅ **COMPLETE** - FastAPI gateway successfully deployed and operational
- FastAPI gateway running on port 8080 (external API)
- vLLM server running on port 8000 (internal inference engine)
- Docker Compose orchestration with health check dependencies
- Medical extraction endpoint (`/api/v1/extract`) returning structured JSON
- Input validation with Pydantic models
- Proper error handling and HTTP status codes
- Interactive API documentation at `/docs`
- Deployment automation via `scripts/deploy.py`
- GitHub Actions CI/CD for dual image builds (vLLM + gateway)

### Stage 2 Architecture
```
Client → FastAPI Gateway (port 8080) → vLLM Server (port 8000)
         └─ Same EC2 instance (g6.2xlarge)
         └─ Docker Compose orchestration
         └─ Named volumes for model persistence
```

### Stage 2 Known Limitations
- Non-medical text input may trigger LLM hallucinations in `raw_output` field
  - Parsed structured fields correctly return null (low impact)
  - Fix planned for post-Stage 3 hardening
- CORS configured with wildcard (`*`) - should be restricted in production

## Stage 3: React/Next.js Frontend

### Overview
Build a user-friendly web interface for medical information extraction, deployed on Vercel as a separate repository. The frontend will consume the FastAPI gateway API deployed in Stage 2.

**Repository**: New repo (this file will be copied there as `.github/copilot-instructions.md`)
**Deployment**: Vercel (serverless Next.js)
**Backend API**: Stage 2 FastAPI gateway at `http://<ec2-ip>:8080`

**Important**: 
- Frontend repo has its own codebase, deployment, and documentation
- This backend repo may need updates based on frontend requirements (e.g., new API endpoints, CORS config, response format changes)
- When working on frontend integration, check both repos for cross-repository dependencies

### Architecture
```
User Browser → Next.js Frontend (Vercel) → FastAPI Gateway (EC2:8080) → vLLM (EC2:8000)
               └─ Static generation + API routes
               └─ Responsive React components
```

### Key Requirements

**Frontend Features**:
- Medical text input form with validation
- Real-time extraction results display
- Structured JSON output visualization
- Example clinical texts for demo
- Loading states and error handling
- Responsive design (mobile + desktop)
- Optional: History of past extractions (client-side storage)

**Technical Stack**:
- Next.js 14+ (App Router)
- React 18+
- TypeScript
- TailwindCSS for styling
- ShadcnUI or similar component library
- Vercel deployment

**API Integration**:
- HTTP client (fetch or axios) to call `/api/v1/extract`
- Proper CORS handling
- Request/response type definitions matching Stage 2 API
- Error boundary for API failures

**Environment Variables** (Vercel):
```env
NEXT_PUBLIC_API_BASE_URL=http://<ec2-ip>:8080
```

### Implementation Priorities

1. **Create Next.js project** with TypeScript and TailwindCSS
2. **Design UI components**:
   - Input form for clinical text
   - Results display with structured fields
   - Loading spinner and error states
3. **Implement API client** to call extraction endpoint
4. **Add example texts** for user testing
5. **Deploy to Vercel** with environment variables
6. **Test end-to-end** workflow

### Stage 3 Success Criteria
- ⏳ Next.js app deployed on Vercel
- ⏳ Medical text input form functional
- ⏳ Extraction results displayed in structured format
- ⏳ Error handling for API failures
- ⏳ Responsive design working on mobile/desktop
- ⏳ Example clinical texts available
- ⏳ CORS properly configured between Vercel and EC2

### Stage 3 Considerations

**CORS Configuration**:
- Update Stage 2 `config/deployment.yml` to whitelist Vercel domain
- Change from `cors_origins: "*"` to specific Vercel URL
- Test OPTIONS preflight requests

**Performance**:
- Consider adding loading states (extraction takes ~2-3 seconds)
- Implement debouncing for input changes
- Show token usage and response time metrics

**Security**:
- Never expose EC2 IP directly in frontend (consider API route proxy)
- Validate inputs on both frontend and backend
- Rate limit considerations for public-facing app

### Post-Stage 3 Enhancements
- User authentication (if needed)
- Extraction history with persistent storage
- Batch processing for multiple texts
- Download results as JSON/CSV
- Confidence scores for extractions

## Future Stages

**Stage 4 Preview** (Observability & Monitoring):
- CloudWatch dashboard for GPU metrics
- Container logs aggregation
- API request/response monitoring
- Cost tracking and alerts
- Performance metrics (latency, throughput)
- Error rate monitoring

**Stage 4 Tools**:
- CloudWatch Logs for centralized logging
- CloudWatch Metrics for GPU utilization
- CloudWatch Alarms for anomaly detection
- Optional: Grafana for advanced dashboarding
- Optional: Sentry for frontend error tracking

## Backend API Reference (for Stage 3 Frontend)

The Stage 2 backend provides the following endpoints:

### Health Check
```bash
GET /health
Response: {"status":"healthy","vllm_available":true,"version":"0.1.0"}
```

### Medical Extraction
```bash
POST /api/v1/extract
Content-Type: application/json

Request Body:
{
  "text": "Patient diagnosed with stage 3 breast cancer with HER2 positive marker.",
  "temperature": 0.3,  // Optional: 0.0-2.0, default 0.3
  "max_tokens": 512    // Optional: 1-8192, default 512
}

Response (200 OK):
{
  "cancer_type": "breast cancer",
  "stage": "3",
  "gene_mutation": null,
  "biomarker": "HER2 positive",
  "treatment": null,
  "response": null,
  "metastasis_site": null,
  "raw_output": "{...}",  // Raw model JSON output
  "tokens_used": 116
}

Error Response (422 Unprocessable Entity):
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "text"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {"min_length": 1}
    }
  ]
}
```

### API Documentation
```bash
GET /docs  # Interactive Swagger UI
GET /redoc  # ReDoc documentation
```

## Project Context for Stage 3

**What's Already Working**:
- ✅ vLLM server serving Llama 3.1 8B + medical-ie LoRA adapter
- ✅ FastAPI gateway with structured extraction endpoint
- ✅ Docker Compose orchestration on EC2
- ✅ Health checks and error handling
- ✅ Input validation (empty text, parameter ranges)
- ✅ Structured JSON output for 7 medical fields

**Known Backend Limitations** (to be aware of in frontend):
- Non-medical text may produce hallucinated content in `raw_output`
  - Structured fields will correctly return null
  - Frontend should handle all-null responses gracefully
- CORS currently set to wildcard (`*`)
  - Will be restricted to Vercel domain once deployed
- Response time: ~2-3 seconds for typical clinical text
  - Frontend should show loading indicator

**EC2 Instance Details**:
- Instance Type: g6.2xlarge (1x L4 GPU)
- Region: us-east-1
- OS: Amazon Linux 2023
- Access: SSM only (no SSH)
- Ports: 8000 (vLLM), 8080 (Gateway)

**Cost Considerations**:
- EC2 instance: ~$1.00/hour when running
- Instance can be stopped when not in use
- Vercel: Free tier for personal projects
- Consider implementing auto-stop after inactivity

## Development Workflow (All Stages)

### Local Development
1. Make changes to code
2. Test locally if possible
3. Commit and push to trigger GitHub Actions

### Deployment (Stage 1-2 Backend)
1. GitHub Actions builds Docker images
2. Images pushed to ECR
3. Run `poetry run python scripts/deploy.py` to deploy to EC2
4. Validate with health checks and API tests

### Deployment (Stage 3 Frontend)
1. Push to GitHub (main branch)
2. Vercel auto-deploys from GitHub
3. Test production URL
4. Monitor Vercel logs for errors

## Troubleshooting

### Backend (Stage 1-2)
- Check CloudWatch logs: `/aws/ssm/slm-ft-serving/commands`
- SSH alternative: Use SSM Session Manager
- Container logs: `docker logs vllm-server` or `docker logs fastapi-gateway`
- Health checks: `curl http://<ec2-ip>:8080/health`

### Frontend (Stage 3)
- Check Vercel deployment logs
- Verify CORS configuration if seeing network errors
- Check browser console for JavaScript errors
- Verify API endpoint is accessible from browser

### Common Issues
1. **CORS errors**: Update Stage 2 CORS config with Vercel domain
2. **Slow responses**: Normal for LLM inference (2-3s)
3. **Connection timeout**: Check EC2 security group allows port 8080
4. **Empty results**: Non-medical text returns null fields (expected)
