"""
Core Type Definitions for AI Game Development Studio — Multi-Agent Edition.
Defines canonical messages, tool specifications, provider capabilities, model metadata,
and execution results.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import time


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"


class AgentLifecycleStatus(str, Enum):
    IDLE = "idle"
    ASSIGNED = "assigned"
    WORKING = "working"
    WAITING = "waiting"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    CONSULTATION = "consultation"
    REVIEW = "review"
    APPROVAL = "approval"
    ESCALATION = "escalation"
    CONFLICT_RESOLUTION = "conflict_resolution"


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class CanonicalToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class CanonicalToolResult(BaseModel):
    tool_call_id: str
    output: Any
    is_error: bool = False


class ContentPart(BaseModel):
    type: str  # text, image_url, image_data, file_data
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_base64: Optional[str] = None
    mime_type: Optional[str] = None


class CanonicalMessage(BaseModel):
    role: MessageRole
    content: Union[str, List[ContentPart]]
    name: Optional[str] = None
    tool_calls: Optional[List[CanonicalToolCall]] = None
    tool_call_id: Optional[str] = None

    def get_text_content(self) -> str:
        if isinstance(self.content, str):
            return self.content
        texts = [p.text for p in self.content if p.text]
        return "\n".join(texts)


class ModelCapabilities(BaseModel):
    streaming: bool = True
    tool_calling: bool = True
    structured_output: bool = True
    vision: bool = False
    audio_input: bool = False
    audio_output: bool = False
    system_instruction: bool = True
    json_mode: bool = True


class ModelMetadata(BaseModel):
    provider_id: str
    model_id: str
    display_name: str
    context_window: int = 128000
    max_output_tokens: int = 4096
    input_modalities: List[Modality] = Field(default_factory=lambda: [Modality.TEXT])
    output_modalities: List[Modality] = Field(default_factory=lambda: [Modality.TEXT])
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    cost_per_million_input: float = 0.0
    cost_per_million_output: float = 0.0
    is_available: bool = True
    is_default: bool = False


class ProviderStatus(BaseModel):
    provider_id: str
    name: str
    is_enabled: bool = True
    is_configured: bool = False
    base_url: str
    default_model: str
    fallback_model: Optional[str] = None
    available_models: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    last_error: Optional[str] = None
    last_check_timestamp: float = Field(default_factory=time.time)


class ProviderCompletionResponse(BaseModel):
    content: str
    role: MessageRole = MessageRole.ASSISTANT
    tool_calls: Optional[List[CanonicalToolCall]] = None
    finish_reason: Optional[str] = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    raw_response: Optional[Dict[str, Any]] = None
