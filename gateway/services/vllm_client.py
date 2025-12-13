"""
vLLM HTTP client wrapper for making requests to vLLM server.
"""

import os
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


class VLLMClient:
    """
    HTTP client for communicating with vLLM server.

    Provides methods for:
    - Health checks
    - Completions API (/v1/completions)
    - Chat completions API (/v1/chat/completions)

    Attributes:
        base_url: Base URL of vLLM server (from VLLM_BASE_URL env var)
        timeout: Request timeout in seconds (default: 60.0)
        client: Async HTTP client instance
    """

    def __init__(self, base_url: str | None = None, timeout: float = 60.0):
        """
        Initialize vLLM client.

        Args:
            base_url: Base URL of vLLM server (defaults to VLLM_BASE_URL env var,
                      falls back to http://localhost:8000 for local development)
            timeout: Request timeout in seconds
        """
        # Priority: explicit arg > env var > localhost fallback
        if base_url is None:
            base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
        
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        logger.info(f"Initialized VLLMClient with base_url={self.base_url}, timeout={timeout}s")

    async def close(self):
        """Close the HTTP client connection."""
        await self.client.aclose()
        logger.debug("VLLMClient connection closed")

    async def health_check(self) -> bool:
        """
        Check if vLLM server is healthy and responsive.

        Returns:
            True if server is healthy, False otherwise

        Example:
            >>> client = VLLMClient()
            >>> is_healthy = await client.health_check()
            >>> print(is_healthy)
            True
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            is_healthy = response.status_code == 200
            if is_healthy:
                logger.info("vLLM health check passed")
            else:
                logger.warning(f"vLLM health check failed with status {response.status_code}")
            return is_healthy
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.error(f"vLLM health check failed: {e}")
            return False

    async def completions(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.3,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call vLLM completions API.

        Args:
            model: Model name (e.g., "medical-ie" for LoRA adapter)
            prompt: Input prompt text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 2.0)
            top_p: Nucleus sampling parameter
            stop: List of stop sequences
            **kwargs: Additional parameters for vLLM API

        Returns:
            API response as dictionary with 'choices', 'usage', etc.

        Raises:
            httpx.HTTPStatusError: If API returns error status

        Example:
            >>> client = VLLMClient()
            >>> result = await client.completions(
            ...     model="medical-ie",
            ...     prompt="Extract cancer info from...",
            ...     max_tokens=256
            ... )
            >>> print(result["choices"][0]["text"])
        """
        request_data = {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            **kwargs
        }

        if stop:
            request_data["stop"] = stop

        logger.debug(
            f"Calling completions API: model={model}, "
            f"max_tokens={max_tokens}, temp={temperature}"
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/v1/completions",
                json=request_data
            )
            response.raise_for_status()
            result = response.json()

            tokens_used = result.get("usage", {}).get("total_tokens", 0)
            logger.info(f"Completions API success: {tokens_used} tokens used")

            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Completions API HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.HTTPError as e:
            logger.error(f"Completions API failed: {e}")
            raise

    async def chat_completions(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.3,
        top_p: float = 1.0,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call vLLM chat completions API.

        Args:
            model: Model name (e.g., "medical-ie")
            messages: List of message dicts with 'role' and 'content' keys
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 2.0)
            top_p: Nucleus sampling parameter
            stop: List of stop sequences
            **kwargs: Additional parameters for vLLM API

        Returns:
            API response with 'choices', 'usage', etc.

        Raises:
            httpx.HTTPStatusError: If API returns error status

        Example:
            >>> client = VLLMClient()
            >>> messages = [
            ...     {"role": "system", "content": "You are a medical assistant."},
            ...     {"role": "user", "content": "Extract cancer info..."}
            ... ]
            >>> result = await client.chat_completions(
            ...     model="medical-ie",
            ...     messages=messages
            ... )
        """
        request_data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            **kwargs
        }

        if stop:
            request_data["stop"] = stop

        logger.debug(
            f"Calling chat completions API: model={model}, "
            f"messages={len(messages)}, max_tokens={max_tokens}"
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data
            )
            response.raise_for_status()
            result = response.json()

            tokens_used = result.get("usage", {}).get("total_tokens", 0)
            logger.info(f"Chat completions API success: {tokens_used} tokens used")

            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Chat completions API HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.HTTPError as e:
            logger.error(f"Chat completions API failed: {e}")
            raise
