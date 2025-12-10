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

# Override entrypoint and command to properly use vllm serve
# The base image's ENTRYPOINT interferes with our command
# Memory constraints for L4 GPU (23GB):
# - max_model_len 8192: Reduce context length to fit KV cache
# - max_num_seqs 32: Limit concurrent sequences (default 256 is too high)
# - gpu_memory_utilization 0.90: Leave headroom for sampling operations
ENTRYPOINT []
CMD ["sh", "-c", "vllm serve $MODEL_NAME --enable-lora --lora-modules medical-ie=$ADAPTER_NAME --tensor-parallel-size $TENSOR_PARALLEL_SIZE --host $HOST --port $PORT --trust-remote-code --disable-log-requests --max-model-len 8192 --max-num-seqs 32 --gpu-memory-utilization 0.90"]
