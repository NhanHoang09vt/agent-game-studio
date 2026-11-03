"""
AI Provider Manager for AI Game Development Studio — Multi-Agent Edition.
Orchestrates all AI providers, health checks, credentials, fallback routing,
latency tracking, token usage, and cost analytics.
"""

import os
import time
from typing import Any, Dict, List, Optional
from core.types import (
    CanonicalMessage,
    ModelMetadata,
    ProviderCompletionResponse,
    ProviderStatus,
    TokenUsage,
)
from core.provider_interface import AIProviderInterface
from core.model_registry import ModelRegistry
from providers.openai_adapter import OpenAIAdapter
from providers.claude_adapter import ClaudeAdapter
from providers.gemini_adapter import GeminiAdapter
from providers.deepseek_adapter import DeepSeekAdapter
from providers.muse_adapter import MuseAdapter
from providers.dogxiai_adapter import DogxiaiAdapter
from providers.custom_adapter import CustomAdapter


class ProviderManager:
    """
    Central manager for AI Providers.
    Supports dynamic registration, fallback execution, health probing, and cost tracking.
    """

    def __init__(self, model_registry: Optional[ModelRegistry] = None):
        self.model_registry = model_registry or ModelRegistry()
        self._adapters: Dict[str, AIProviderInterface] = {}
        self._statuses: Dict[str, ProviderStatus] = {}
        self._fallback_map: Dict[str, str] = {
            "deepseek": "openai",
            "muse": "claude",
            "dogxiai": "deepseek",
            "custom": "openai",
            "gemini": "claude",
            "openai": "claude",
            "claude": "gemini",
        }
        self._initialize_from_environment()

    def _initialize_from_environment(self) -> None:
        """Read API keys securely from environment variables"""
        env = os.environ

        configs = [
            ("openai", "OpenAI", OpenAIAdapter, env.get("OPENAI_API_KEY"), env.get("OPENAI_BASE_URL", "https://api.openai.com/v1"), "gpt-4o", "gpt-4o-mini"),
            ("claude", "Anthropic Claude", ClaudeAdapter, env.get("ANTHROPIC_API_KEY"), env.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"), "claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022"),
            ("gemini", "Google Gemini", GeminiAdapter, env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY"), env.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"), "gemini-3.8-flash", "gemini-3.8-pro"),
            ("deepseek", "DeepSeek", DeepSeekAdapter, env.get("DEEPSEEK_API_KEY"), env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"), "deepseek-chat", "deepseek-reasoner"),
            ("muse", "Muse AI", MuseAdapter, env.get("MUSE_API_KEY"), env.get("MUSE_BASE_URL", "https://api.museai.com/v1"), "muse-story-pro", "muse-audio-engine"),
            ("dogxiai", "Dogxiai Gaming", DogxiaiAdapter, env.get("DOGXIAI_API_KEY"), env.get("DOGXIAI_BASE_URL", "https://api.dogxiai.com/v1"), "dogxiai-game-master", "dogxiai-balance-bot"),
            ("custom", "Custom / Local", CustomAdapter, env.get("CUSTOM_API_KEY", "local"), env.get("CUSTOM_BASE_URL", "http://localhost:11434/v1"), "local-model", None),
        ]

        for pid, name, adapter_cls, key, base_url, default_mod, fallback_mod in configs:
            adapter = adapter_cls(api_key=key, base_url=base_url)
            self._adapters[pid] = adapter

            is_configured = bool(key and key.strip())
            models = [m.model_id for m in self.model_registry.list_by_provider(pid)]

            self._statuses[pid] = ProviderStatus(
                provider_id=pid,
                name=name,
                is_enabled=True,
                is_configured=is_configured,
                base_url=base_url,
                default_model=default_mod,
                fallback_model=fallback_mod,
                available_models=models,
            )

    def register_provider(
        self,
        provider_id: str,
        adapter: AIProviderInterface,
        name: str,
        default_model: str,
        fallback_model: Optional[str] = None,
    ) -> None:
        self._adapters[provider_id] = adapter
        models = [m.model_id for m in self.model_registry.list_by_provider(provider_id)]
        self._statuses[provider_id] = ProviderStatus(
            provider_id=provider_id,
            name=name,
            is_enabled=True,
            is_configured=bool(adapter.api_key),
            base_url=adapter.base_url,
            default_model=default_model,
            fallback_model=fallback_model,
            available_models=models,
        )

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> bool:
        if provider_id in self._statuses:
            self._statuses[provider_id].is_enabled = enabled
            if provider_id in self._adapters:
                self._adapters[provider_id].is_enabled = enabled
            return True
        return False

    def update_provider_config(
        self,
        provider_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> bool:
        if provider_id not in self._adapters:
            return False

        adapter = self._adapters[provider_id]
        status = self._statuses[provider_id]

        if api_key is not None:
            adapter.api_key = api_key
            status.is_configured = bool(api_key.strip())
        if base_url is not None:
            adapter.base_url = base_url.rstrip("/")
            status.base_url = adapter.base_url
        if default_model is not None:
            status.default_model = default_model
        if fallback_model is not None:
            status.fallback_model = fallback_model
        if timeout_seconds is not None:
            adapter.timeout_seconds = timeout_seconds

        return True

    def get_adapter(self, provider_id: str) -> Optional[AIProviderInterface]:
        return self._adapters.get(provider_id)

    def get_status(self, provider_id: str) -> Optional[ProviderStatus]:
        return self._statuses.get(provider_id)

    def get_all_statuses(self) -> List[ProviderStatus]:
        return list(self._statuses.values())

    async def test_connection(self, provider_id: str) -> Dict[str, Any]:
        """Verify API key, connectivity, and latency for a provider"""
        adapter = self.get_adapter(provider_id)
        status = self.get_status(provider_id)
        if not adapter or not status:
            return {"success": False, "latency_ms": 0.0, "error": f"Provider '{provider_id}' not found."}

        res = await adapter.validate_credentials()
        status.last_check_timestamp = time.time()
        status.latency_ms = res.get("latency_ms", 0.0)

        if res.get("success"):
            status.last_error = None
        else:
            status.last_error = res.get("error")

        return res

    async def execute_chat_with_fallback(
        self,
        provider_id: str,
        model_id: str,
        messages: List[CanonicalMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ProviderCompletionResponse:
        """
        Execute chat completion with automatic failover to fallback provider/model
        if primary provider encounters an error or rate limit.
        """
        adapter = self.get_adapter(provider_id)
        status = self.get_status(provider_id)

        if not adapter or not status or not status.is_enabled:
            # Route immediately to fallback
            fallback_pid = self._fallback_map.get(provider_id, "openai")
            fb_adapter = self.get_adapter(fallback_pid)
            fb_status = self.get_status(fallback_pid)
            if fb_adapter and fb_status:
                fb_model = fb_status.default_model
                return await fb_adapter.chat_completion(
                    model_id=fb_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                )
            raise RuntimeError(f"Provider '{provider_id}' is disabled and no fallback available.")

        try:
            status.total_requests += 1
            response = await adapter.chat_completion(
                model_id=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
            )
            # Record telemetry
            status.total_tokens_used += response.usage.total_tokens
            status.total_cost_usd += response.usage.estimated_cost_usd
            status.latency_ms = response.latency_ms
            return response

        except Exception as e:
            status.failed_requests += 1
            status.last_error = str(e)

            # Try fallback provider
            fallback_pid = self._fallback_map.get(provider_id, "openai")
            fb_adapter = self.get_adapter(fallback_pid)
            fb_status = self.get_status(fallback_pid)
            if fb_adapter and fb_status and fb_status.is_enabled:
                fb_model = fb_status.default_model
                fb_status.total_requests += 1
                fb_resp = await fb_adapter.chat_completion(
                    model_id=fb_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                )
                fb_status.total_tokens_used += fb_resp.usage.total_tokens
                fb_status.total_cost_usd += fb_resp.usage.estimated_cost_usd
                return fb_resp

            raise e
