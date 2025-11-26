# Stage 1: vLLM Server for Fine-tuned Llama 3.1 8B Medical IE
# Base image: vLLM official image with CUDA support
FROM vllm/vllm-openai:latest

# Set working directory
WORKDIR /app

# Environment variables (will be injected via AWS Secrets Manager -> SSM)
ENV HF_TOKEN=""
ENV MODEL_NAME="meta-llama/Llama-3.1-8B"
ENV ADAPTER_NAME="loghoag/llama-3.1-8b-medical-ie"

# Install additional dependencies if needed
# RUN pip install --no-cache-dir <package>

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose vLLM API port
EXPOSE 8000

# Start vLLM server with base model + adapter
# TODO: Add actual vLLM launch command with:
# - Load base model: meta-llama/Llama-3.1-8B
# - Load adapter: loghoag/llama-3.1-8b-medical-ie
# - Configure tensor parallelism for g6.2xlarge GPU
# - Set quantization parameters (4-bit)
CMD ["echo", "vLLM launch command placeholder - implement in next phase"]
