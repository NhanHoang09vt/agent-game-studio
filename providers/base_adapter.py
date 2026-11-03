"""
Base Provider Adapter Implementation for AI Game Development Studio.
Provides shared HTTP client session handling, retry logic with exponential backoff,
error classification, and canonical format transformation.
"""

import asyncio
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
import httpx
from core.provider_interface import AIProviderInterface
from core.types import (
    CanonicalMessage,
    CanonicalToolCall,
    MessageRole,
    ModelMetadata,
    ProviderCompletionResponse,
    TokenUsage,
)


class BaseAIAdapter(AIProviderInterface):
    """
    Base implementation with robust connection handling and telemetry.
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
        super().__init__(
            provider_id=provider_id,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            extra_config=extra_config,
        )
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _convert_canonical_to_openai_messages(
        self, messages: List[CanonicalMessage]
    ) -> List[Dict[str, Any]]:
        """Standard transformation used by OpenAI, DeepSeek, Custom, and Dogxiai"""
        openai_msgs = []
        for msg in messages:
            item: Dict[str, Any] = {"role": msg.role.value}

            if isinstance(msg.content, str):
                item["content"] = msg.content
            elif isinstance(msg.content, list):
                parts = []
                for part in msg.content:
                    if part.type == "text":
                        parts.append({"type": "text", "text": part.text or ""})
                    elif part.type == "image_url" and part.media_url:
                        parts.append({"type": "image_url", "image_url": {"url": part.media_url}})
                    elif part.type == "image_data" and part.media_base64:
                        mime = part.mime_type or "image/png"
                        parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{part.media_base64}"}
                        })
                item["content"] = parts

            if msg.name:
                item["name"] = msg.name
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]

            openai_msgs.append(item)
        return openai_msgs

    def _parse_openai_tool_calls(
        self, raw_tool_calls: Optional[List[Dict[str, Any]]]
    ) -> Optional[List[CanonicalToolCall]]:
        if not raw_tool_calls:
            return None
        parsed = []
        for tc in raw_tool_calls:
            func = tc.get("function", {})
            args = {}
            raw_args = func.get("arguments", "{}")
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except Exception:
                    args = {"raw": raw_args}
            elif isinstance(raw_args, dict):
                args = raw_args

            parsed.append(
                CanonicalToolCall(
                    id=tc.get("id", f"call_{int(time.time()*1000)}"),
                    name=func.get("name", "unknown_function"),
                    arguments=args,
                )
            )
        return parsed

    async def _execute_with_retry(self, func, *args, **kwargs) -> Any:
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                backoff = (2 ** attempt) * 0.5
                await asyncio.sleep(backoff)
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    last_exception = e
                    backoff = (2 ** attempt) * 1.0
                    await asyncio.sleep(backoff)
                else:
                    raise e
        raise last_exception or RuntimeError("Max retries exceeded")
