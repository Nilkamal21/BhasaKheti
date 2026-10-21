"""
Cohere LLM Provider Implementation for BhashaKheti.
Uses standard HTTP REST API via httpx (CPU & lightweight friendly, no bloated dependencies).
Handles rate limits, timeouts, and grounds output in verified documents.
"""

from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.services.llm.provider import BaseLLMProvider

COHERE_V2_CHAT_URL = "https://api.cohere.com/v2/chat"


class CohereLLMProvider(BaseLLMProvider):
    """Integrates Cohere's Command-R series via official REST API."""

    def __init__(self):
        self.api_key = settings.COHERE_API_KEY
        self.model = settings.COHERE_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def get_provider_name(self) -> str:
        return "Cohere"

    async def generate_grounded_response(
        self,
        prompt: str,
        system_instruction: str,
        context_documents: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 800
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Cohere API key is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BhasaKheti-CropIntelligence/1.0"
        }

        # Build message payload for Cohere v2 Chat API
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # If grounded context documents are supplied, attach them
        if context_documents:
            doc_snippets = []
            for d in context_documents:
                doc_snippets.append({
                    "data": {
                        "title": d.get("title_bn") or d.get("title_en", "Agricultural Record"),
                        "text": d.get("content_bn") or d.get("content_en", ""),
                        "source": d.get("source_org", "Verified Source")
                    }
                })
            payload["documents"] = doc_snippets

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(COHERE_V2_CHAT_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                # Extract generated text from Cohere v2 format
                generated_text = ""
                if "message" in data and "content" in data["message"]:
                    for block in data["message"]["content"]:
                        if block.get("type") == "text":
                            generated_text += block.get("text", "")

                tokens_used = None
                if "usage" in data and "tokens" in data["usage"]:
                    tokens_used = data["usage"]["tokens"].get("total_tokens")

                return {
                    "text": generated_text.strip(),
                    "provider": "cohere",
                    "model": self.model,
                    "is_fallback": False,
                    "tokens_used": tokens_used
                }

        except httpx.TimeoutException as exc:
            logger.warning(f"Cohere API call timed out after {self.timeout}s: {exc}")
            raise TimeoutError(f"Cohere API response timed out ({self.timeout}s).") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_body = exc.response.text
            logger.error(f"Cohere API HTTP error {status_code}: {error_body}")
            if status_code == 429:
                raise RuntimeError("Cohere API rate limit reached.") from exc
            if status_code == 401:
                raise RuntimeError("Invalid or unauthorized Cohere API key.") from exc
            raise RuntimeError(f"Cohere API HTTP {status_code}: {error_body}") from exc
        except Exception as exc:
            logger.error(f"Cohere API general error: {exc}")
            raise RuntimeError(f"Cohere API call failed: {str(exc)}") from exc
