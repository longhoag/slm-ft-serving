# Stage 1: vLLM Server for Fine-tuned Llama 3.1 8B Medical IE
# Base image: vLLM official image with CUDA support
FROM vllm/vllm-openai:latest

# Set working directory
WORKDIR /app

# Environment variables (will be injected at runtime via docker run -e)
ENV HF_TOKEN=""
ENV MODEL_NAME="meta-llama/Llama-3.1-8B"
ENV ADAPTER_NAME="loghoag/llama-3.1-8b-medical-ie"
ENV PORT=8000
ENV HOST=0.0.0.0
ENV TENSOR_PARALLEL_SIZE=1

# Health check endpoint (vLLM OpenAI-compatible server exposes /health)
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose vLLM API port
EXPOSE ${PORT}

# Start vLLM server with base model + LoRA adapter
# vLLM OpenAI-compatible server with:
# - Base model: meta-llama/Llama-3.1-8B (auto-downloads from HuggingFace)
# - LoRA adapter: loghoag/llama-3.1-8b-medical-ie
# - Tensor parallelism: 1 GPU (g6.2xlarge has single L4)
# - Trust remote code for model loading
# - Disable log requests for cleaner CloudWatch logs
CMD python3 -m vllm.entrypoints.openai.api_server \
    --model ${MODEL_NAME} \
    --enable-lora \
    --lora-modules medical-ie=${ADAPTER_NAME} \
    --tensor-parallel-size ${TENSOR_PARALLEL_SIZE} \
    --host ${HOST} \
    --port ${PORT} \
    --trust-remote-code \
    --disable-log-requests
