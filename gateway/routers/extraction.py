"""
Medical information extraction endpoints.

Provides API for extracting structured cancer information from clinical text.
"""
from fastapi import APIRouter, HTTPException
from loguru import logger

from gateway.models import MedicalExtractionRequest, MedicalExtractionResponse
from gateway.services.vllm_client import VLLMClient
from gateway.utils.prompts import medical_extraction_prompt
from gateway.utils.parsers import parse_medical_output

router = APIRouter(prefix="/api/v1", tags=["extraction"])

# Initialize vLLM client (shared across extraction requests)
vllm_client = VLLMClient()


@router.post("/extract", response_model=MedicalExtractionResponse)
async def extract_medical_info(request: MedicalExtractionRequest) -> MedicalExtractionResponse:
    """
    Extract structured medical information from clinical text.
    
    Args:
        request: MedicalExtractionRequest with clinical text and generation params
        
    Returns:
        MedicalExtractionResponse with extracted cancer information
        
    Raises:
        HTTPException 503: vLLM backend unavailable
        HTTPException 500: Extraction or parsing failed
    """
    logger.info(f"Extraction requested for {len(request.text)} chars of text")
    
    # Check vLLM availability first
    if not await vllm_client.health_check():
        logger.error("vLLM backend unavailable")
        raise HTTPException(
            status_code=503,
            detail="vLLM backend is unavailable. Please try again later."
        )
    
    # Generate prompt with proper formatting
    prompt = medical_extraction_prompt(request.text)
    logger.debug(f"Generated prompt ({len(prompt)} chars)")
    
    # Call vLLM completions endpoint
    try:
        result = await vllm_client.completions(
            model=request.model,
            prompt=prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            # Stop sequences to prevent redundant output
            stop=["\n\n\n", "Instruction:", "Input:", "Output:", "###"],
            top_p=0.95
        )
        logger.debug(f"vLLM returned {result['usage']['total_tokens']} tokens")
    except Exception as e:
        logger.error(f"vLLM completion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Model inference failed: {str(e)}"
        ) from e
    
    # Extract raw model output
    raw_text = result["choices"][0]["text"].strip()
    tokens_used = result["usage"]["total_tokens"]
    
    logger.debug(f"Raw output ({len(raw_text)} chars): {raw_text[:200]}...")
    
    # Parse structured medical information
    try:
        parsed = parse_medical_output(raw_text)
        logger.info(f"Successfully extracted medical info: {list(parsed.keys())}")
    except Exception as e:
        logger.error(f"Parsing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse model output: {str(e)}"
        ) from e
    
    # Build response with parsed data + metadata
    response = MedicalExtractionResponse(
        **parsed,
        raw_output=raw_text,
        tokens_used=tokens_used
    )
    
    fields_extracted = sum(1 for v in parsed.values() if v)
    logger.info(f"Extraction complete: {tokens_used} tokens, {fields_extracted} fields")
    return response
