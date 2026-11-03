"""
Abstract Provider Interface for AI Game Development Studio — Multi-Agent Edition.
Every provider adapter (OpenAI, Gemini, Claude, DeepSeek, Muse, Dogxiai, Custom)
must implement this contract.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional, Any, Union
from core.types import (
    CanonicalMessage,
    ModelMetadata,
    ProviderCompletionResponse,
    TokenUsage
)


class AIProviderInterface(ABC):
    """
    Unified abstract interface for AI model providers.
    Supports chat completion, streaming, model capability checking,
    credential verification, and token usage / cost tracking.
    """

    def __init__(
        self,
        provider_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        extra_config: Optional[Dict[str, Any]] = None,
    ):
        self.provider_id = provider_id
        self.api_key = api_key or ""
        self.base_url = (base_url or "").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.extra_config = extra_config or {}
        self.is_enabled = True

    @abstractmethod
    async def validate_credentials(self) -> Dict[str, Any]:
        """
        Validate API Key, ping endpoint, and test connectivity.
        Returns a dict with {"success": bool, "latency_ms": float, "error": Optional[str]}.
        """
        pass

    @abstractmethod
    def get_supported_models(self) -> List[ModelMetadata]:
        """
        Return the catalog of supported models with metadata, pricing,
        and capability flags.
        """
        pass

    @abstractmethod
    async def chat_completion(
        self,
        model_id: str,
        messages: List[CanonicalMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> ProviderCompletionResponse:
        """
        Execute a standard chat completion call.
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        model_id: str,
        messages: List[CanonicalMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Execute a streaming chat completion call, yielding token chunks.
        """
        pass

    def calculate_cost(self, model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate total cost in USD for a given completion based on model pricing.
        """
        for m in self.get_supported_models():
            if m.model_id == model_id:
                cost_in = (prompt_tokens / 1_000_000.0) * m.cost_per_million_input
                cost_out = (completion_tokens / 1_000_000.0) * m.cost_per_million_output
                return round(cost_in + cost_out, 6)
        return 0.0

    def get_model_metadata(self, model_id: str) -> Optional[ModelMetadata]:
        for m in self.get_supported_models():
            if m.model_id == model_id:
                return m
        return None
