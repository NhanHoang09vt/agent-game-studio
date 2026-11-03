"""
Google Gemini Provider Adapter (Gemini 3.8 Flash, Gemini 3.8 Pro, 2.5 Pro, Flash Thinking).
Supports native Gemini REST API, 2M+ Token Context, Multimodal (Image, Audio, Video, Docs),
Function Declarations, Thinking Blocks, Structured JSON Schemas, and SSE Streaming.
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


class GeminiAdapter(BaseAIAdapter):
    """Adapter for Google Gemini Generative Language API (Gemini 3.8 & 2.5)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        extra_config: Optional[Dict[str, Any]] = None,
    ):
        base = base_url or "https://generativelanguage.googleapis.com/v1beta"
        super().__init__(
            provider_id="gemini",
            api_key=api_key,
            base_url=base,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            extra_config=extra_config,
        )

    def get_supported_models(self) -> List[ModelMetadata]:
        return ModelRegistry().list_by_provider("gemini")

    async def validate_credentials(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "latency_ms": 0.0, "error": "No API Key provided for Google Gemini."}
        start = time.perf_counter()
        try:
            client = await self.get_client()
            resp = await client.get(f"{self.base_url}/models?key={self.api_key}")
            resp.raise_for_status()
            latency = (time.perf_counter() - start) * 1000.0
            return {"success": True, "latency_ms": round(latency, 2), "error": None}
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            return {"success": False, "latency_ms": round(latency, 2), "error": str(e)}

    def _convert_to_gemini_contents(
        self, messages: List[CanonicalMessage]
    ) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        system_instruction: Optional[Dict[str, Any]] = None
        contents: List[Dict[str, Any]] = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_instruction = {"parts": [{"text": msg.get_text_content()}]}
                continue

            role = "model" if msg.role == MessageRole.ASSISTANT else "user"
            parts: List[Dict[str, Any]] = []

            if isinstance(msg.content, str):
                if msg.content:
                    parts.append({"text": msg.content})
            elif isinstance(msg.content, list):
                for p in msg.content:
                    if p.type == "text" and p.text:
                        parts.append({"text": p.text})
                    elif p.type in ("image_data", "file_data") and p.media_base64:
                        parts.append({
                            "inline_data": {
                                "mime_type": p.mime_type or "image/png",
                                "data": p.media_base64,
                            }
                        })

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    parts.append({
                        "function_call": {
                            "name": tc.name,
                            "args": tc.arguments,
                        }
                    })

            if msg.role == MessageRole.TOOL:
                parts.append({
                    "function_response": {
                        "name": msg.name or "unknown_func",
                        "response": {"output": msg.get_text_content()},
                    }
                })

            if parts:
                contents.append({"role": role, "parts": parts})

        return system_instruction, contents

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
                content=f"[Gemini 3.8 Offline Mock - {model_id}]: High-speed multimodal game systems analysis generated.",
                role=MessageRole.ASSISTANT,
                usage=TokenUsage(prompt_tokens=45, completion_tokens=30, total_tokens=75, estimated_cost_usd=0.00005),
                latency_ms=12.0,
            )

        system_instruction, contents = self._convert_to_gemini_contents(messages)
        gen_config: Dict[str, Any] = {
            "temperature": temperature,
        }
        if max_tokens:
            gen_config["maxOutputTokens"] = max_tokens

        # Support structured JSON output
        if response_format:
            if response_format.get("type") in ["json_object", "json"]:
                gen_config["responseMimeType"] = "application/json"
            if "schema" in response_format:
                gen_config["responseSchema"] = response_format["schema"]

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": gen_config,
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction

        if tools:
            decls = []
            for t in tools:
                if "function" in t:
                    func = t["function"]
                    decls.append({
                        "name": func.get("name"),
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters"),
                    })
                elif "name" in t:
                    decls.append(t)
            if decls:
                payload["tools"] = [{"function_declarations": decls}]

            # Tool choice / calling mode
            if tool_choice:
                mode = "AUTO"
                if isinstance(tool_choice, str):
                    mode = "ANY" if tool_choice == "required" else "NONE" if tool_choice == "none" else "AUTO"
                payload["toolConfig"] = {
                    "functionCallingConfig": {"mode": mode}
                }

        async def _call():
            client = await self.get_client()
            url = f"{self.base_url}/models/{model_id}:generateContent?key={self.api_key}"
            res = await client.post(url, json=payload)
            res.raise_for_status()
            return res.json()

        data = await self._execute_with_retry(_call)
        latency = (time.perf_counter() - start_time) * 1000.0

        candidates = data.get("candidates", [])
        content_text = ""
        thought_text = ""
        tool_calls: List[CanonicalToolCall] = []

        if candidates:
            cand = candidates[0]
            cand_content = cand.get("content", {})
            parts = cand_content.get("parts", [])
            for p in parts:
                if "thought" in p and p.get("thought"):
                    thought_text += p.get("text", "")
                elif "text" in p:
                    content_text += p["text"]
                elif "functionCall" in p:
                    fc = p["functionCall"]
                    tool_calls.append(
                        CanonicalToolCall(
                            id=f"gemini_call_{int(time.time()*1000)}",
                            name=fc.get("name"),
                            arguments=fc.get("args", {}),
                        )
                    )

        if thought_text:
            content_text = f"<!-- Gemini Thinking:\n{thought_text}\n-->\n\n{content_text}"

        usage_meta = data.get("usageMetadata", {})
        prompt_tokens = usage_meta.get("promptTokenCount", 0)
        completion_tokens = usage_meta.get("candidatesTokenCount", 0)
        cost = self.calculate_cost(model_id, prompt_tokens, completion_tokens)

        return ProviderCompletionResponse(
            content=content_text,
            role=MessageRole.ASSISTANT,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=candidates[0].get("finishReason") if candidates else None,
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
            yield f"[Gemini 3.8 Streaming Mock - {model_id}]: Streaming content..."
            return

        system_instruction, contents = self._convert_to_gemini_contents(messages)
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_instruction:
            payload["system_instruction"] = system_instruction

        client = await self.get_client()
        url = f"{self.base_url}/models/{model_id}:streamGenerateContent?alt=sse&key={self.api_key}"

        async with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                raw_chunk = line[6:].strip()
                try:
                    event = json.loads(raw_chunk)
                    cands = event.get("candidates", [])
                    if cands:
                        parts = cands[0].get("content", {}).get("parts", [])
                        for p in parts:
                            if "text" in p:
                                yield p["text"]
                except Exception:
                    continue
