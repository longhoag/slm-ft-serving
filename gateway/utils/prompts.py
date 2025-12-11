"""
Prompt templates for medical information extraction.
"""

from typing import Optional


def medical_extraction_prompt(text: str, format_hint: bool = True) -> str:
    """
    Create a prompt for medical information extraction from clinical text.

    Args:
        text: Clinical text to extract information from
        format_hint: Whether to include JSON format hint in the prompt

    Returns:
        Formatted prompt string for the model

    Example:
        >>> prompt = medical_extraction_prompt("Patient has stage 3 breast cancer")
        >>> print(prompt)
        Extract structured cancer information from this clinical text...
    """
    base_prompt = f"""Extract structured cancer information from this clinical text. Identify the following fields if present:

- cancer_type: The type of cancer (e.g., breast cancer, lung cancer, prostate cancer)
- stage: Cancer stage (e.g., 1, 2, 3, 4, or descriptive like "early-stage")
- gene_mutation: Specific genetic mutations (e.g., BRCA1, EGFR, KRAS)
- biomarker: Biomarkers or molecular markers (e.g., HER2 positive, PD-L1)
- treatment: Treatment approaches (e.g., chemotherapy, radiation, immunotherapy)
- response: Treatment response or outcome (e.g., complete response, partial response)
- metastasis_site: Sites of metastasis if mentioned (e.g., bone, liver, brain)

Clinical Text:
{text}

Structured Data:"""

    if format_hint:
        base_prompt += '\n{"cancer_type": "", "stage": "", "gene_mutation": "", "biomarker": "", "treatment": "", "response": "", "metastasis_site": ""}'

    return base_prompt


def chat_extraction_prompt(text: str) -> list[dict[str, str]]:
    """
    Create a chat-style prompt for medical extraction using the chat completions API.

    Args:
        text: Clinical text to extract information from

    Returns:
        List of message dicts with 'role' and 'content' keys

    Example:
        >>> messages = chat_extraction_prompt("Patient diagnosed with lung cancer")
        >>> print(messages[0]['role'])
        system
    """
    system_message = """You are a medical information extraction assistant. Your task is to extract structured cancer-related information from clinical text.

Extract these fields when present:
- cancer_type: Type of cancer
- stage: Cancer stage
- gene_mutation: Genetic mutations
- biomarker: Biomarkers/molecular markers
- treatment: Treatment approaches
- response: Treatment response
- metastasis_site: Metastasis sites

Return results as a JSON object. If a field is not mentioned, omit it or use null."""

    user_message = f"""Extract structured cancer information from this text:

{text}"""

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]


def validation_prompt(extracted_data: dict[str, Optional[str]], original_text: str) -> str:
    """
    Create a validation prompt to verify extracted information against original text.

    Args:
        extracted_data: Dictionary of extracted medical fields
        original_text: Original clinical text

    Returns:
        Formatted validation prompt

    Example:
        >>> data = {"cancer_type": "breast cancer", "stage": "3"}
        >>> prompt = validation_prompt(data, "Patient has stage 3 breast cancer")
    """
    fields_str = "\n".join([f"- {k}: {v}" for k, v in extracted_data.items() if v])

    return f"""Verify that the following extracted information is accurate based on the original text.

Original Text:
{original_text}

Extracted Data:
{fields_str}

Is this extraction accurate? Respond with "yes" or "no" and explain any discrepancies."""
