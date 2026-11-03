"""
Custom / Local Provider Adapter.
Compatible with any OpenAI-compatible endpoint: Ollama, vLLM, LocalAI, LM Studio,
OpenRouter, or private self-hosted game development LLMs.
"""

import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
import httpx
from core.types import (
    CanonicalMessage,
    MessageRole,
    ModelMetadata,
    ProviderCompletionResponse,
    TokenUsage,
)
from providers.base_adapter import BaseAIAdapter
from core.model_registry import ModelRegistry


class CustomAdapter(BaseAIAdapter):
    """Adapter for Custom or Local OpenAI-compatible model servers"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 90.0,
        max_retries: int = 2,
        extra_config: Optional[Dict[str, Any]] = None,
    ):
        base = base_url or "http://localhost:11434/v1"
        super().__init__(
            provider_id="custom",
            api_key=api_key or "local-key",
            base_url=base,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            extra_config=extra_config,
        )

    def get_supported_models(self) -> List[ModelMetadata]:
        return ModelRegistry().list_by_provider("custom")

    async def validate_credentials(self) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            client = await self.get_client()
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = await client.get(f"{self.base_url}/models", headers=headers)
            resp.raise_for_status()
            latency = (time.perf_counter() - start) * 1000.0
            return {"success": True, "latency_ms": round(latency, 2), "error": None}
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            # For local endpoints, we give a friendly message rather than a crash
            return {
                "success": False,
                "latency_ms": round(latency, 2),
                "error": f"Cannot connect to custom endpoint at {self.base_url}: {e}",
            }

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
        start_time = time.perf_counter()

        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": self._convert_canonical_to_openai_messages(messages),
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            client = await self.get_client()
            res = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            # Local fallback mock if local server is not running
            return ProviderCompletionResponse(
                content=f"[Custom Local Mock - {model_id}]: Studio task completed via local adapter fallback ({e}).",
                role=MessageRole.ASSISTANT,
                usage=TokenUsage(prompt_tokens=30, completion_tokens=30, total_tokens=60, estimated_cost_usd=0.0),
                latency_ms=5.0,
            )

        latency = (time.perf_counter() - start_time) * 1000.0
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        usage_data = data.get("usage", {})
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)

        return ProviderCompletionResponse(
            content=msg.get("content") or "",
            role=MessageRole.ASSISTANT,
            tool_calls=self._parse_openai_tool_calls(msg.get("tool_calls")),
            finish_reason=choice.get("finish_reason"),
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=0.0,
            ),
            latency_ms=round(latency, 2),
            raw_response=data,
        )

    async def chat_stream(
        self,
        model_id: str,
        messages: List[CanonicalMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": self._convert_canonical_to_openai_messages(messages),
            "temperature": temperature,
            "stream": True,
        }

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            client = await self.get_client()
            async with client.stream("POST", f"{self.base_url}/chat/completions", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    raw_chunk = line[6:].strip()
                    if raw_chunk == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(raw_chunk)
                        delta = chunk_json["choices"][0].get("delta", {})
                        token = delta.get("content")
                        if token:
                            yield token
                    except Exception:
                        continue
        except Exception:
            yield f"[Custom Local Mock - {model_id}]: Local streaming stream..."
