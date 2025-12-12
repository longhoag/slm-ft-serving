# Gateway Dockerfile for FastAPI medical information extraction service
# Multi-stage build with Poetry for clean dependency installation

FROM python:3.11-slim AS builder

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.0

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (gateway + main groups only, no dev/deploy)
# --no-root: Don't install the project itself (no setup.py)
# --no-directory: Pure dependency installation
RUN poetry config virtualenvs.create false \
    && poetry install --only main,gateway --no-root --no-directory --no-interaction --no-ansi

# Final stage: Runtime image
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy gateway application code
COPY gateway/ ./gateway/

# Create logs directory for loguru
RUN mkdir -p logs

# Expose gateway port
EXPOSE 8080

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health', timeout=5.0)" || exit 1

# Run FastAPI with uvicorn
# --host 0.0.0.0: Listen on all interfaces (required for Docker)
# --port 8080: Gateway port
# --log-level info: Standard logging
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
