# Medical Information Extraction - Backend Server

> **Backend infrastructure for AI-powered medical cancer information extraction using fine-tuned Llama 3.1 8B**

[![Live Demo](https://img.shields.io/badge/Demo-Live-brightgreen)](https://medical-extraction.vercel.app)
[![GitHub Actions](https://img.shields.io/badge/CI/CD-GitHub%20Actions-2088FF?logo=github-actions&logoColor=white)](https://github.com/longhoag/slm-ft-serving/actions)
[![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20ECR%20%7C%20SSM-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![Docker](https://img.shields.io/badge/Docker-vLLM%20%7C%20FastAPI-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

---

## 🎯 Overview

This repository contains the **backend infrastructure** for a medical information extraction system that uses a **fine-tuned Llama 3.1 8B model** (qLoRA 4-bit quantization) to extract structured cancer-related entities from clinical text.

The system serves as an AI-powered medical assistant that can parse unstructured clinical notes and return structured data including cancer type, stage, gene mutations, biomarkers, treatments, responses, and metastasis sites.

**🌐 Live Application**: [https://medical-extraction.vercel.app](https://medical-extraction.vercel.app)

**📱 Frontend Repository**: [slm-ft-serving-frontend](https://github.com/longhoag/slm-ft-serving-frontend)

---

## 🏗️ Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        User Browser                           │
│                (medical-extraction.vercel.app)                │
└───────────────────────────┬───────────────────────────────────┘
                            │ HTTPS
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                  Next.js Frontend (Vercel)                    │
│  • React UI components                                        │
│  • Server-side API routes (proxy to backend)                  │
│  • Input validation & error handling                          │
└───────────────────────────┬───────────────────────────────────┘
                            │ HTTP (proxied)
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                  EC2 g6.2xlarge (us-east-1)                   │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  FastAPI Gateway (Port 8080)                            │  │
│  │  • REST API endpoints                                   │  │
│  │  • Request validation (Pydantic)                        │  │
│  │  • CORS configuration                                   │  │
│  └────────────────────────┬────────────────────────────────┘  │
│                           │ HTTP                              │
│                           ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  vLLM Server (Port 8000)                                │  │
│  │  • Llama 3.1 8B base model                              │  │
│  │  • LoRA adapter: medical-ie                             │  │
│  │  • GPU inference (L4 GPU)                               │  │
│  │  • Model caching on EBS                                 │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

> ⚠️ **Note**: This is an experimental project. The EC2 backend server may not be running at all times to save costs (~$1/hour for GPU instance). If the demo is unavailable, the server is likely stopped.

### Component Details

| Component | Technology | Port | Description |
|-----------|-----------|------|-------------|
| **Frontend** | Next.js 16 + React | N/A | User interface on Vercel (separate repo) |
| **Gateway** | FastAPI + Pydantic | 8080 | REST API layer with validation |
| **Inference** | vLLM + Llama 3.1 8B | 8000 | LLM serving with LoRA adapter |
| **Infrastructure** | EC2 + Docker Compose | N/A | Container orchestration |
| **CI/CD** | GitHub Actions + ECR | N/A | Automated builds and deployments |

---

## 🚀 Project Stages

This project follows a **staged development approach** - each stage must be complete before moving to the next:

| Stage | Status | Description | Documentation |
|-------|--------|-------------|---------------|
| **1** | ✅ Complete | vLLM server with LoRA adapter on EC2 | [Stage 1 Details](#stage-1-vllm-inference-server) |
| **2** | ✅ Complete | FastAPI gateway with Docker Compose | [Stage 2 Details](#stage-2-fastapi-gateway) |
| **3** | ✅ Complete | Next.js frontend on Vercel | [Stage 3 Details](#stage-3-nextjs-frontend) |
| **4** | 🔮 Planned | CloudWatch monitoring & observability | [Stage 4 Preview](#stage-4-future-monitoring) |

---

## 🧬 The Model

### Fine-tuning Details

The model was fine-tuned on synthetic cancer clinical data using **qLoRA (4-bit quantization)** technique for parameter-efficient training.

**Base Model**: [`meta-llama/Llama-3.1-8B`](https://huggingface.co/meta-llama/Llama-3.1-8B)  
**Fine-tuned Adapter**: [`loghoag/llama-3.1-8b-medical-ie`](https://huggingface.co/loghoag/llama-3.1-8b-medical-ie)

### Training Data Format

```json
{
  "instruction": "Extract all cancer-related entities from the text.",
  "input": "70-year-old man with widely metastatic cutaneous melanoma. PD-L1 was 5% on IHC and NGS reported TMB-high. Given multiple symptomatic brain metastases he received combination immunotherapy with nivolumab plus ipilimumab and stereotactic radiosurgery to dominant intracranial lesions. Imaging after two cycles demonstrated some shrinking of index lesions but appearance of a new small lesion — overall assessment called a mixed response.",
  "output": {
    "cancer_type": "melanoma (cutaneous)",
    "stage": "IV",
    "gene_mutation": null,
    "biomarker": "PD-L1 5%; TMB-high",
    "treatment": "nivolumab and ipilimumab; stereotactic radiosurgery",
    "response": "mixed response",
    "metastasis_site": "brain"
  }
}
```

### Extraction Fields

The model extracts **7 structured fields**:

| Field | Description | Example |
|-------|-------------|---------|
| `cancer_type` | Type of cancer | melanoma, breast cancer, NSCLC |
| `stage` | Cancer stage | III, IV, metastatic |
| `gene_mutation` | Genetic mutations | EGFR exon 19, KRAS G12D, BRCA1 |
| `biomarker` | Biomarker status | HER2+, PD-L1 5%, TMB-high |
| `treatment` | Treatments given | nivolumab, chemotherapy, surgery |
| `response` | Treatment response | complete response, stable disease |
| `metastasis_site` | Metastasis locations | brain, liver, bone |

---

## 🛠️ Tech Stack

### Backend (This Repository)

| Category | Technology |
|----------|------------|
| **Inference Engine** | [vLLM](https://github.com/vllm-project/vllm) (optimized LLM serving) |
| **API Framework** | [FastAPI](https://fastapi.tiangolo.com/) + [Pydantic](https://docs.pydantic.dev/) |
| **Language** | Python 3.11+ |
| **Dependency Management** | Poetry |
| **Containerization** | Docker + Docker Compose |
| **Cloud Infrastructure** | AWS EC2 (g6.2xlarge, L4 GPU) |
| **Container Registry** | AWS ECR |
| **Remote Execution** | AWS Systems Manager (SSM) |
| **Secrets Management** | AWS Secrets Manager + SSM Parameter Store |
| **CI/CD** | GitHub Actions |
| **Logging** | Loguru + CloudWatch Logs |

### Frontend ([Separate Repository](https://github.com/longhoag/slm-ft-serving-frontend))

| Category | Technology |
|----------|------------|
| **Framework** | Next.js 16 (App Router) |
| **Language** | TypeScript (strict mode) |
| **Styling** | TailwindCSS v4 |
| **UI Components** | ShadcnUI (Radix primitives) |
| **Deployment** | Vercel (serverless) |
| **State Management** | React Hooks |

---

## �� Stage Details

### Stage 1: vLLM Inference Server

**Status**: ✅ Complete

**Deliverables**:
- Docker image with vLLM + Llama 3.1 8B + medical-ie LoRA adapter
- EC2 g6.2xlarge deployment (L4 GPU, 80 GiB EBS)
- Model persistence via Docker named volumes
- Health checks and inference validation
- Remote deployment via SSM (no SSH)

**Infrastructure**:
- Instance: EC2 g6.2xlarge (us-east-1)
- Storage: 80 GiB EBS root volume
- GPU: 1x NVIDIA L4 (24GB VRAM)
- Access: SSM only (no \`.pem\` keys)

### Stage 2: FastAPI Gateway

**Status**: ✅ Complete

**Deliverables**:
- FastAPI gateway with REST API endpoints
- Docker Compose orchestration (vLLM + Gateway)
- Medical extraction endpoint (\`/api/v1/extract\`)
- Input validation with Pydantic models
- CORS configuration for Vercel domains
- Interactive API documentation (\`/docs\`)
- Dual GitHub Actions workflow (parallel builds)

**API Endpoints**:

\`\`\`bash
# Health check
GET /health
Response: {"status": "healthy", "vllm_available": true, "version": "0.1.0"}

# Medical extraction
POST /api/v1/extract
Content-Type: application/json
Body: {
  "text": "Patient diagnosed with stage 3 breast cancer...",
  "temperature": 0.3,  // optional: 0.0-2.0
  "max_tokens": 512    // optional: 1-8192
}
\`\`\`

### Stage 3: Next.js Frontend

**Status**: ✅ Complete

**Live Application**: [https://medical-extraction.vercel.app](https://medical-extraction.vercel.app)

**Repository**: [slm-ft-serving-frontend](https://github.com/longhoag/slm-ft-serving-frontend)

**Features**:
- Medical text input form with validation
- Real-time extraction results (2-3 second response)
- Structured display of 7 extracted fields
- Example clinical texts for testing
- Responsive design (mobile + desktop)
- Server-side API proxy (EC2 IP hidden from browser)
- Loading states and error handling
- TypeScript strict mode with full type coverage

**Frontend Architecture**:
\`\`\`
src/
├── app/
│   ├── api/
│   │   ├── extract/route.ts   # Proxy to backend
│   │   └── health/route.ts    # Health check proxy
│   ├── layout.tsx             # Root layout
│   └── page.tsx               # Main extraction form
├── components/
│   ├── ui/                    # ShadcnUI components
│   ├── extraction-form.tsx    # Input form
│   └── extraction-results.tsx # Results display
└── types/
    └── api.ts                 # TypeScript interfaces
\`\`\`

### Stage 4: Future Monitoring

**Status**: 🔮 Planned

**Planned Features**:
- CloudWatch dashboards for GPU metrics
- Container log aggregation and analysis
- API request/response monitoring
- Cost tracking and alerts
- Performance metrics (latency, throughput)
- Error rate monitoring and alerting

---

## 🚀 Getting Started

### Prerequisites

- AWS account with EC2, ECR, SSM, Secrets Manager access
- GitHub account with Actions enabled
- Poetry installed locally (\`brew install poetry\`)
- AWS CLI configured with credentials
- HuggingFace account with Llama 3.1 access

### Required Secrets

Store these in **AWS Secrets Manager**:

| Secret | Purpose | Location |
|--------|---------|----------|
| \`HF_TOKEN\` | HuggingFace access token | Secrets Manager |
| \`AWS_ACCESS_KEY_ID\` | AWS credentials | GitHub Secrets |
| \`AWS_SECRET_ACCESS_KEY\` | AWS credentials | GitHub Secrets |

Reference secrets via **SSM Parameter Store** (no \`.env\` files).

### Deployment

#### 1. Initial Setup

\`\`\`bash
# Clone repository
git clone https://github.com/longhoag/slm-ft-serving.git
cd slm-ft-serving

# Install dependencies
poetry install

# Configure AWS credentials
aws configure
\`\`\`

#### 2. Deploy to EC2

\`\`\`bash
# Start EC2 instance and deploy containers
poetry run python scripts/deploy.py

# Deploy without starting EC2 (if already running)
poetry run python scripts/deploy.py --skip-start
\`\`\`

#### 3. Verify Deployment

\`\`\`bash
# Check health
curl http://<ec2-public-ip>:8080/health

# Test extraction
curl -X POST http://<ec2-public-ip>:8080/api/v1/extract \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Patient diagnosed with stage 3 breast cancer with HER2 positive marker."
  }'
\`\`\`

### CI/CD Workflow

The GitHub Actions workflow automatically:

1. **Triggers on push** to \`main\` branch (when backend files change)
2. **Builds Docker images** (vLLM + Gateway in parallel)
3. **Pushes to ECR** with cache optimization
4. **Tracks deployment** in GitHub sidebar

**Manual deployment** to EC2:
\`\`\`bash
poetry run python scripts/deploy.py --skip-start
\`\`\`

---

## 📊 Features & Capabilities

### Backend Features

✅ **High-Performance Inference** - vLLM optimizations for fast LLM serving  
✅ **GPU Acceleration** - NVIDIA L4 GPU for efficient inference  
✅ **LoRA Adapter Support** - Load fine-tuned adapters without full model retraining  
✅ **Model Caching** - Persistent storage on EBS (survives container restarts)  
✅ **Health Checks** - Automated container health monitoring  
✅ **Input Validation** - Pydantic models for request/response validation  
✅ **CORS Security** - Restricted to Vercel domains  
✅ **API Documentation** - Interactive Swagger UI at \`/docs\`  
✅ **Structured Output** - 7 medical fields in JSON format  
✅ **Error Handling** - Proper HTTP status codes and error messages

### Frontend Features ([View Frontend Repo](https://github.com/longhoag/slm-ft-serving-frontend))

✨ **Real-time Extraction** - Extract medical entities in 2-3 seconds  
🔒 **Secure Architecture** - EC2 backend IP hidden via server-side proxy  
📱 **Responsive Design** - Works seamlessly on mobile and desktop  
🎯 **Type-safe** - Full TypeScript coverage with strict mode  
⚡ **Fast & Modern** - Built with Next.js 16 and TailwindCSS v4  
🔄 **Auto-deploy** - Push to main → live on Vercel instantly

---

## 📖 Documentation

- **[STAGE-3.md](docs/STAGE-3.md)** - Stage 3 backend changes and CORS configuration
- **[Copilot Instructions](.github/copilot-instructions.md)** - AI assistant context and guidelines
- **[Frontend Repository](https://github.com/longhoag/slm-ft-serving-frontend)** - Frontend codebase and documentation

---

## 🔧 Development Notes

### Design Principles

- **SSM-only access**: No SSH, no \`.pem\` keys for EC2 access
- **Secrets Manager**: All secrets stored securely, never in \`.env\` files
- **Poetry for Python**: No raw \`pip install\` commands
- **Loguru for logging**: No \`print()\` statements in production code
- **Staged development**: Complete each stage before moving forward
- **Fail-safe execution**: Commands execute with error handling and retries

### Project Structure

\`\`\`
slm-ft-serving/
├── .github/
│   ├── workflows/
│   │   └── deploy.yml              # CI/CD pipeline
│   └── copilot-instructions.md     # AI assistant context
├── config/
│   └── deployment.yml              # Deployment configuration
├── docs/
│   └── STAGE-3.md                  # Stage 3 documentation
├── gateway/
│   ├── routers/
│   │   └── extraction.py           # Extraction endpoint
│   ├── main.py                     # FastAPI app
│   └── Dockerfile                  # Gateway Docker image
├── scripts/
│   └── deploy.py                   # SSM deployment script
├── Dockerfile                      # vLLM Docker image
├── docker-compose.yml              # Container orchestration
├── pyproject.toml                  # Poetry dependencies
└── README.md                       # This file
\`\`\`

---

## 🌐 Related Links

- **Live Application**: [https://medical-extraction.vercel.app](https://medical-extraction.vercel.app)
- **Frontend Repository**: [slm-ft-serving-frontend](https://github.com/longhoag/slm-ft-serving-frontend)
- **Base Model**: [meta-llama/Llama-3.1-8B](https://huggingface.co/meta-llama/Llama-3.1-8B)
- **Fine-tuned Adapter**: [loghoag/llama-3.1-8b-medical-ie](https://huggingface.co/loghoag/llama-3.1-8b-medical-ie)

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **vLLM Team** - High-performance LLM inference engine
- **Meta AI** - Llama 3.1 base model
- **HuggingFace** - Model hosting and fine-tuning infrastructure
- **FastAPI** - Modern Python web framework
- **Vercel** - Frontend hosting platform
