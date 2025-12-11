"""
Pydantic models for request/response validation.

Defines schemas for:
- MedicalExtractionRequest: Input for medical entity extraction
- MedicalExtractionResponse: Structured output with extracted entities
"""

from typing import Optional

from pydantic import BaseModel, Field


class MedicalExtractionRequest(BaseModel):
    """
    Request schema for medical information extraction.

    Attributes:
        text: Clinical text to extract cancer information from
        temperature: Sampling temperature (0.0-2.0). Lower = more deterministic
        max_tokens: Maximum tokens to generate (1-8192)
        model: Model to use for extraction (default: medical-ie)
    """

    text: str = Field(
        ...,
        description="Clinical text to extract cancer information from",
        min_length=1,
        max_length=8000,
    )
    temperature: float = Field(
        default=0.3, description="Sampling temperature for generation", ge=0.0, le=2.0
    )
    max_tokens: int = Field(
        default=100, description="Maximum tokens to generate", ge=1, le=8192
    )
    model: str = Field(default="medical-ie", description="Model to use for extraction")

    class Config:
        """Pydantic model configuration with example."""

        json_schema_extra = {
            "example": {
                "text": "Patient diagnosed with stage 3 breast cancer with HER2 positive marker.",
                "temperature": 0.3,
                "max_tokens": 100,
                "model": "medical-ie",
            }
        }


class MedicalExtractionResponse(BaseModel):
    """
    Response schema for medical information extraction.

    Returns structured cancer information with optional fields.
    All fields default to None if not found in the text.

    Attributes:
        cancer_type: Type of cancer (e.g., breast cancer, lung cancer)
        stage: Cancer stage (e.g., I, II, III, IV, or specific staging)
        gene_mutation: Genetic mutations (e.g., BRCA1, EGFR, KRAS)
        biomarker: Biomarkers (e.g., HER2+, PD-L1, MSI-high)
        treatment: Treatment regimen (e.g., chemotherapy, targeted therapy)
        response: Treatment response (e.g., complete response, partial response)
        metastasis_site: Sites of metastasis (e.g., liver, lung, bone)
        raw_output: Raw model output before parsing
        tokens_used: Total tokens used (prompt + completion)
    """

    cancer_type: Optional[str] = Field(None, description="Type of cancer identified")
    stage: Optional[str] = Field(None, description="Cancer stage")
    gene_mutation: Optional[str] = Field(None, description="Genetic mutations identified")
    biomarker: Optional[str] = Field(None, description="Biomarkers identified")
    treatment: Optional[str] = Field(None, description="Treatment regimen")
    response: Optional[str] = Field(None, description="Treatment response")
    metastasis_site: Optional[str] = Field(None, description="Sites of metastasis")
    raw_output: str = Field(..., description="Raw model output before parsing")
    tokens_used: int = Field(
        ..., description="Total tokens used for this request", ge=0
    )

    class Config:
        """Pydantic model configuration with example."""

        json_schema_extra = {
            "example": {
                "cancer_type": "breast cancer",
                "stage": "3",
                "gene_mutation": None,
                "biomarker": "HER2 positive",
                "treatment": None,
                "response": None,
                "metastasis_site": None,
                "raw_output": (
                    '{"cancer_type": "breast cancer", "stage": "3", '
                    '"biomarker": "HER2 positive"}'
                ),
                "tokens_used": 85,
            }
        }


class HealthCheckResponse(BaseModel):
    """
    Health check response schema.

    Attributes:
        status: Health status (healthy/unhealthy)
        vllm_available: Whether vLLM backend is accessible
        version: Gateway version
    """

    status: str = Field(..., description="Overall health status")
    vllm_available: bool = Field(..., description="vLLM backend availability")
    version: str = Field(..., description="Gateway version")

    class Config:
        """Pydantic model configuration with example."""

        json_schema_extra = {
            "example": {"status": "healthy", "vllm_available": True, "version": "0.1.0"}
        }
