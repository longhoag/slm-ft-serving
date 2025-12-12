"""
FastAPI gateway for vLLM medical information extraction.

This gateway provides a REST API for extracting structured cancer information
from clinical text using a fine-tuned Llama 3.1 8B model served by vLLM.
"""
import os
from contextlib import asynccontextmanager

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


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown").
    
    Args:
        app_instance: FastAPI application instance (unused but required by signature)
    """
    # Startup: Runs when application starts
    logger.info("🚀 Medical IE Gateway starting up...")
    logger.info("   Version: 0.1.0")
    logger.info("   Docs: http://localhost:8080/docs")
    
    yield  # Application runs here
    
    # Shutdown: Runs when application stops
    logger.info("👋 Medical IE Gateway shutting down...")


# Initialize FastAPI application with lifespan handler
app = FastAPI(
    title="Medical Information Extraction Gateway",
    description="REST API for extracting structured cancer information from clinical text",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS middleware
# CORS_ORIGINS env var: comma-separated list of allowed origins
# Example: CORS_ORIGINS="https://medical-ie.vercel.app,https://localhost:3000"
# Default: "*" (allow all - suitable for Stage 2 testing, restrict in Stage 3+)
allowed_origins = os.getenv("CORS_ORIGINS", "*")
origins_list = [allowed_origins] if allowed_origins == "*" else allowed_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include routers
app.include_router(health.router)
app.include_router(extraction.router)


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
