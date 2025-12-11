"""
Response parsing utilities.

Implements robust parsing for vLLM model outputs:
- extract_first_json: Extract first valid JSON object from text
- parse_key_value_format: Fallback parser for key:value format
- parse_medical_output: Main parser with multi-layer fallback strategy
"""

import json
import re
from typing import Dict, Optional

from loguru import logger


def extract_first_json(text: str) -> Optional[Dict]:
    """
    Extract first valid JSON object from text with proper brace matching.

    Handles nested braces and malformed trailing content. This is the primary
    parsing method for structured model outputs.

    Args:
        text: Raw text that may contain JSON object

    Returns:
        Parsed JSON dict if found, None otherwise

    Example:
        >>> text = '{"cancer_type": "lung cancer"}extra text'
        >>> extract_first_json(text)
        {'cancer_type': 'lung cancer'}
    """
    brace_count = 0
    start_idx = text.find("{")

    if start_idx == -1:
        return None

    for i in range(start_idx, len(text)):
        if text[i] == "{":
            brace_count += 1
        elif text[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                # Found complete JSON object
                json_str = text[start_idx : i + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error: {e}")
                    return None

    logger.warning("No complete JSON object found")
    return None


def parse_key_value_format(text: str) -> Dict[str, str]:
    """
    Fallback parser for key:value format when JSON parsing fails.

    Parses text in format:
        cancer_type: breast cancer
        stage: 3
        biomarker: HER2 positive

    Args:
        text: Text with key:value pairs (one per line)

    Returns:
        Dict of extracted key-value pairs

    Example:
        >>> text = "cancer_type: lung cancer\\nstage: IV"
        >>> parse_key_value_format(text)
        {'cancer_type': 'lung cancer', 'stage': 'IV'}
    """
    fields = {}
    valid_keys = {
        "cancer_type",
        "stage",
        "gene_mutation",
        "biomarker",
        "treatment",
        "response",
        "metastasis_site",
    }

    for line in text.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            if key in valid_keys:
                fields[key] = value.strip()

    return fields


def parse_medical_output(text: str) -> Dict[str, Optional[str]]:
    """
    Main parser for medical entity extraction with multi-layer fallback.

    Parsing strategy:
    1. Try extracting first JSON object (primary method)
    2. Fall back to key:value parsing if JSON fails
    3. Return empty dict with all None values if both fail

    Args:
        text: Raw model output

    Returns:
        Dict with medical entity fields (all optional)

    Example:
        >>> output = '{"cancer_type": "breast cancer", "stage": "3"}'
        >>> parse_medical_output(output)
        {'cancer_type': 'breast cancer', 'stage': '3', ...}
    """
    # Initialize result with all fields as None
    result: Dict[str, Optional[str]] = {
        "cancer_type": None,
        "stage": None,
        "gene_mutation": None,
        "biomarker": None,
        "treatment": None,
        "response": None,
        "metastasis_site": None,
    }

    # Layer 1: Try JSON extraction
    json_obj = extract_first_json(text)
    if json_obj:
        logger.debug("Successfully parsed JSON output")
        # Only update fields that exist in the JSON
        for key in result:
            if key in json_obj:
                result[key] = json_obj[key]
        return result

    # Layer 2: Try key:value parsing
    logger.debug("JSON parsing failed, trying key:value format")
    kv_fields = parse_key_value_format(text)
    if kv_fields:
        logger.debug(f"Parsed {len(kv_fields)} fields from key:value format")
        result.update(kv_fields)
        return result

    # Layer 3: Return empty result
    logger.warning("All parsing methods failed, returning empty result")
    return result


def clean_json_string(text: str) -> str:
    """
    Clean text before JSON parsing by removing common issues.

    Handles:
    - Leading/trailing whitespace
    - Markdown code blocks (with or without language specifier)
    - Extra newlines

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text ready for parsing

    Example:
        >>> clean_json_string('```json\\n{"key": "value"}\\n```')
        '{"key": "value"}'
    """
    # Remove markdown code blocks (with or without language specifier)
    text = re.sub(r"```(?:json)?\s*\n?", "", text)
    text = re.sub(r"```\s*$", "", text)

    # Remove extra whitespace
    text = text.strip()

    return text
