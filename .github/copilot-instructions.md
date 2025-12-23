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
- **Stage 3** ✅ **COMPLETE**: Next.js frontend on Vercel (separate repo) - [Live Demo](https://medical-extraction.vercel.app)
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
- CORS restricted to Vercel domains (`https://medical-extraction.vercel.app`, `https://*.vercel.app`)
  - Currently allows all methods and headers (hardening planned post-Stage 3)

## Stage 3 Completion Status
✅ **COMPLETE** - Next.js frontend successfully deployed on Vercel

**Live Application**: [https://medical-extraction.vercel.app](https://medical-extraction.vercel.app)

**Repository**: Separate frontend repo
**Deployment**: Vercel (auto-deploy from main branch)
**Backend Integration**: FastAPI gateway at EC2:8080 (proxied via Next.js API routes)

### Overview
User-friendly web interface for medical information extraction, deployed on Vercel as a separate repository. The frontend consumes the FastAPI gateway API deployed in Stage 2.

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

**Technical Stack** (Implemented):
- Next.js 16 (App Router)
- React 18+
- TypeScript (strict mode)
- TailwindCSS v4
- ShadcnUI (Radix primitives)
- Vercel deployment with auto-deploy

**API Integration** (Implemented):
- Server-side API proxy routes (`/api/extract`, `/api/health`)
- Backend IP hidden from browser (server-only `BACKEND_API_URL`)
- Full TypeScript types matching Stage 2 API
- Proper error handling and loading states

**Environment Variables** (Vercel):
```env
BACKEND_API_URL=http://<ec2-ip>:8080  # Server-only, no NEXT_PUBLIC_ prefix
```

### Implemented Features

1. ✅ **Next.js 16 project** with TypeScript strict mode and TailwindCSS v4
2. ✅ **UI components** with ShadcnUI:
   - Clinical text input form with validation
   - Structured results display grid (7 fields)
   - Loading states and error boundaries
3. ✅ **API proxy routes** for secure backend communication
4. ✅ **Example clinical texts** for user testing
5. ✅ **Vercel deployment** with auto-deploy from main branch
6. ✅ **End-to-end workflow** tested and validated

### Stage 3 Success Criteria
- ✅ Next.js 16 app deployed on Vercel with auto-deploy
- ✅ Medical text input form functional with validation
- ✅ Extraction results displayed in structured format (7 fields)
- ✅ Error handling for API failures
- ✅ Responsive design working on mobile/desktop
- ✅ Example clinical texts available
- ✅ CORS properly configured between Vercel and EC2
- ✅ Backend API proxied via Next.js API routes (EC2 IP hidden)
- ✅ TypeScript strict mode with full type coverage
- ✅ TailwindCSS v4 + ShadcnUI components

### Stage 3 Implementation Notes

**CORS Configuration** (Completed):
- ✅ Backend `config/deployment.yml` updated with Vercel domains
- ✅ CORS origins: `https://medical-extraction.vercel.app`, `https://*.vercel.app`
- ✅ OPTIONS preflight requests working correctly

**Performance** (Implemented):
- ✅ Loading states for ~2-3 second extraction time
- ✅ Token usage displayed in results
- ✅ Responsive UI with immediate feedback

**Security** (Implemented):
- ✅ EC2 IP hidden via server-side Next.js API routes
- ✅ Input validation on both frontend and backend
- ⚠️ Rate limiting not yet implemented (future enhancement)

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

**Known Backend Limitations**:
- Non-medical text may produce hallucinated content in `raw_output`
  - Structured fields correctly return null
  - Frontend handles all-null responses gracefully
- CORS restricted to Vercel domains (production + previews)
  - Currently allows all methods/headers (hardening planned)
- Response time: ~2-3 seconds for typical clinical text
  - Frontend shows loading indicator during processing

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
