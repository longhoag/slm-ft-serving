"""
FastAPI gateway for vLLM medical information extraction.

This gateway provides a REST API for extracting structured cancer information
from clinical text using a fine-tuned Llama 3.1 8B model served by vLLM.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from gateway.routers import health, extraction

# Configure loguru for gateway logging
logger.add(
    "logs/gateway_{time}.log",
    rotation="100 MB",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Initialize FastAPI application
app = FastAPI(
    title="Medical Information Extraction Gateway",
    description="REST API for extracting structured cancer information from clinical text",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include routers
app.include_router(health.router)
app.include_router(extraction.router)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Log gateway startup."""
    logger.info("🚀 Medical IE Gateway starting up...")
    logger.info(f"   Version: 0.1.0")
    logger.info(f"   Docs: http://localhost:8080/docs")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Log gateway shutdown."""
    logger.info("👋 Medical IE Gateway shutting down...")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Medical Information Extraction Gateway",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "extraction": "/api/v1/extract"
    }
