"""
LLM Factory & Manager for BhashaKheti.
Provides access to configured LLM (Cohere) with deterministic fallback.
"""

from typing import Optional
from app.services.llm.provider import BaseLLMProvider
from app.services.llm.cohere_provider import CohereLLMProvider

_cohere_instance: Optional[CohereLLMProvider] = None


def get_llm_provider() -> BaseLLMProvider:
    """Returns active LLM provider instance."""
    global _cohere_instance
    if _cohere_instance is None:
        _cohere_instance = CohereLLMProvider()
    return _cohere_instance
