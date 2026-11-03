"""
Dogxiai Provider Adapter.
Specialized provider for game mechanics, combat simulation, economy balancing,
and game design mathematics.
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


class DogxiaiAdapter(BaseAIAdapter):
    """Adapter for Dogxiai Gaming AI services"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        extra_config: Optional[Dict[str, Any]] = None,
    ):
        base = base_url or "https://api.dogxiai.com/v1"
        super().__init__(
            provider_id="dogxiai",
            api_key=api_key,
            base_url=base,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            extra_config=extra_config,
        )

    def get_supported_models(self) -> List[ModelMetadata]:
        return ModelRegistry().list_by_provider("dogxiai")

    async def validate_credentials(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "latency_ms": 0.0, "error": "No API Key provided for Dogxiai."}
        start = time.perf_counter()
        try:
            client = await self.get_client()
            resp = await client.get(
                f"{self.base_url}/status",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            latency = (time.perf_counter() - start) * 1000.0
            return {"success": True, "latency_ms": round(latency, 2), "error": None}
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            return {"success": False, "latency_ms": round(latency, 2), "error": str(e)}

    async def chat_completion(
        self,
        model_id: str,
        messages: List[CanonicalMessage],
        temperature: float = 0.5,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> ProviderCompletionResponse:
        start_time = time.perf_counter()

        if not self.api_key:
            return ProviderCompletionResponse(
                content=f"[Dogxiai Game Master Mock - {model_id}]: Combat balance curve and loot formulas validated.",
                role=MessageRole.ASSISTANT,
                usage=TokenUsage(prompt_tokens=40, completion_tokens=35, total_tokens=75, estimated_cost_usd=0.00004),
                latency_ms=10.0,
            )

        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": self._convert_canonical_to_openai_messages(messages),
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async def _call():
            client = await self.get_client()
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            res = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            res.raise_for_status()
            return res.json()

        data = await self._execute_with_retry(_call)
        latency = (time.perf_counter() - start_time) * 1000.0

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        usage_data = data.get("usage", {})
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        cost = self.calculate_cost(model_id, prompt_tokens, completion_tokens)

        return ProviderCompletionResponse(
            content=msg.get("content") or "",
            role=MessageRole.ASSISTANT,
            tool_calls=self._parse_openai_tool_calls(msg.get("tool_calls")),
            finish_reason=choice.get("finish_reason"),
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=cost,
            ),
            latency_ms=round(latency, 2),
            raw_response=data,
        )

    async def chat_stream(
        self,
        model_id: str,
        messages: List[CanonicalMessage],
        temperature: float = 0.5,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield f"[Dogxiai Streaming Mock - {model_id}]: Streaming game mechanics..."
            return

        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": self._convert_canonical_to_openai_messages(messages),
            "temperature": temperature,
            "stream": True,
        }

        client = await self.get_client()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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
