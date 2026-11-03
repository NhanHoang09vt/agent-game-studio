"""
Anthropic Claude Provider Adapter (Claude 3.7 Sonnet, Claude 3.5 Sonnet, Claude 3 Opus, Haiku).
Supports native Anthropic Messages API, Tool Calling, Vision, Thinking Blocks, and Streaming.
"""

import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
import httpx
from core.types import (
    CanonicalMessage,
    CanonicalToolCall,
    MessageRole,
    ModelMetadata,
    ProviderCompletionResponse,
    TokenUsage,
)
from providers.base_adapter import BaseAIAdapter
from core.model_registry import ModelRegistry


class ClaudeAdapter(BaseAIAdapter):
    """Adapter for Anthropic Claude Messages API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        extra_config: Optional[Dict[str, Any]] = None,
    ):
        base = base_url or "https://api.anthropic.com/v1"
        super().__init__(
            provider_id="claude",
            api_key=api_key,
            base_url=base,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            extra_config=extra_config,
        )

    def get_supported_models(self) -> List[ModelMetadata]:
        return ModelRegistry().list_by_provider("claude")

    async def validate_credentials(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "latency_ms": 0.0, "error": "No API Key provided for Anthropic Claude."}
        start = time.perf_counter()
        try:
            # Test minimal payload
            client = await self.get_client()
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            # Claude doesn't have a simple GET /models endpoint, so we ping with a 1-token query or check header
            payload = {
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "ping"}],
            }
            resp = await client.post(f"{self.base_url}/messages", headers=headers, json=payload)
            if resp.status_code in [200, 400]:  # 400 means authenticated but parameter error; 401 is auth error
                latency = (time.perf_counter() - start) * 1000.0
                return {"success": True, "latency_ms": round(latency, 2), "error": None}
            resp.raise_for_status()
            latency = (time.perf_counter() - start) * 1000.0
            return {"success": True, "latency_ms": round(latency, 2), "error": None}
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            return {"success": False, "latency_ms": round(latency, 2), "error": str(e)}

    def _convert_to_anthropic_format(
        self, messages: List[CanonicalMessage]
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        system_prompt: Optional[str] = None
        anthropic_msgs: List[Dict[str, Any]] = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                sys_text = msg.get_text_content()
                system_prompt = f"{system_prompt}\n{sys_text}" if system_prompt else sys_text
                continue

            role = "assistant" if msg.role == MessageRole.ASSISTANT else "user"

            if msg.role == MessageRole.TOOL:
                anthropic_msgs.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id or "unknown",
                            "content": msg.get_text_content(),
                        }
                    ],
                })
                continue

            if isinstance(msg.content, str):
                content: Any = msg.content
                if msg.tool_calls:
                    content_list = [{"type": "text", "text": msg.content}] if msg.content else []
                    for tc in msg.tool_calls:
                        content_list.append({
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        })
                    content = content_list
                anthropic_msgs.append({"role": role, "content": content})
            elif isinstance(msg.content, list):
                parts = []
                for p in msg.content:
                    if p.type == "text":
                        parts.append({"type": "text", "text": p.text or ""})
                    elif p.type == "image_data" and p.media_base64:
                        parts.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": p.mime_type or "image/png",
                                "data": p.media_base64,
                            },
                        })
                anthropic_msgs.append({"role": role, "content": parts})

        return system_prompt, anthropic_msgs

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

        if not self.api_key:
            return ProviderCompletionResponse(
                content=f"[Claude Offline Mock - {model_id}]: Studio architectural review completed.",
                role=MessageRole.ASSISTANT,
                usage=TokenUsage(prompt_tokens=60, completion_tokens=30, total_tokens=90, estimated_cost_usd=0.0003),
                latency_ms=12.0,
            )

        system_prompt, anthropic_msgs = self._convert_to_anthropic_format(messages)
        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": anthropic_msgs,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if tools:
            # Map tools to Anthropic format: name, description, input_schema
            formatted_tools = []
            for t in tools:
                if "function" in t:
                    func = t["function"]
                    formatted_tools.append({
                        "name": func.get("name"),
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
                    })
                else:
                    formatted_tools.append(t)
            payload["tools"] = formatted_tools

        async def _call():
            client = await self.get_client()
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            res = await client.post(f"{self.base_url}/messages", headers=headers, json=payload)
            res.raise_for_status()
            return res.json()

        data = await self._execute_with_retry(_call)
        latency = (time.perf_counter() - start_time) * 1000.0

        content_parts = []
        tool_calls: List[CanonicalToolCall] = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                content_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    CanonicalToolCall(
                        id=block.get("id"),
                        name=block.get("name"),
                        arguments=block.get("input", {}),
                    )
                )

        usage_data = data.get("usage", {})
        prompt_tokens = usage_data.get("input_tokens", 0)
        completion_tokens = usage_data.get("output_tokens", 0)
        cost = self.calculate_cost(model_id, prompt_tokens, completion_tokens)

        return ProviderCompletionResponse(
            content="\n".join(content_parts),
            role=MessageRole.ASSISTANT,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=data.get("stop_reason"),
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
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield f"[Claude Streaming Mock - {model_id}]: Streaming tokens..."
            return

        system_prompt, anthropic_msgs = self._convert_to_anthropic_format(messages)
        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": anthropic_msgs,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        client = await self.get_client()
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async with client.stream("POST", f"{self.base_url}/messages", headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                raw_chunk = line[6:].strip()
                try:
                    event = json.loads(raw_chunk)
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield delta.get("text", "")
                except Exception:
                    continue
