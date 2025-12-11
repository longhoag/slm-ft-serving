"""
Health check endpoints for the FastAPI gateway.

Provides health status for the gateway itself and the vLLM backend server.
"""
from fastapi import APIRouter
from loguru import logger

from gateway.models import HealthCheckResponse
from gateway.services.vllm_client import VLLMClient

router = APIRouter(tags=["health"])

# Initialize vLLM client (shared across health check requests)
vllm_client = VLLMClient()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Check the health status of the gateway and vLLM backend.
    
    Returns:
        HealthCheckResponse with gateway status and vLLM availability
    """
    logger.debug("Health check requested")
    
    # Check vLLM backend availability
    vllm_available = await vllm_client.health_check()
    
    response = HealthCheckResponse(
        status="healthy",
        vllm_available=vllm_available,
        version="0.1.0"
    )
    
    logger.info(f"Health check complete: gateway=healthy, vllm={vllm_available}")
    return response


@router.get("/health/vllm")
async def vllm_health_check() -> dict:
    """
    Direct vLLM backend health check endpoint.
    
    Returns:
        Dict with vLLM availability status
    """
    logger.debug("vLLM health check requested")
    
    available = await vllm_client.health_check()
    
    return {
        "vllm_available": available,
        "backend_url": vllm_client.base_url
    }
