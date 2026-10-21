"""
Abstract base interface for LLM providers in BhashaKheti.
Ensures provider independence (Cohere, OpenAI, Local, etc.) and safe fallbacks.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseLLMProvider(ABC):
    """Abstract protocol for all LLM providers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is properly configured with credentials."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns human-readable name of the provider."""
        pass

    @abstractmethod
    async def generate_grounded_response(
        self,
        prompt: str,
        system_instruction: str,
        context_documents: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 800
    ) -> Dict[str, Any]:
        """
        Generates an evidence-grounded response.
        Returns dict with keys:
          - text: str
          - provider: str
          - model: str
          - is_fallback: bool
          - tokens_used: Optional[int]
        """
        pass
