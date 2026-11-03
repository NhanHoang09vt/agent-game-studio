"""
Model Registry for AI Game Development Studio — Multi-Agent Edition.
Maintains the centralized, up-to-date registry of AI models across all providers
with their context windows, capabilities, modalities, and pricing.
"""

from typing import Dict, List, Optional
from core.types import ModelMetadata, Modality, ModelCapabilities


class ModelRegistry:
    """
    Central repository of models from OpenAI, Gemini, Claude, DeepSeek, Muse, Dogxiai, and Custom.
    """

    def __init__(self):
        self._models: Dict[str, ModelMetadata] = {}
        self._load_built_in_models()

    def register_model(self, metadata: ModelMetadata) -> None:
        key = f"{metadata.provider_id}:{metadata.model_id}"
        self._models[key] = metadata

    def get_model(self, provider_id: str, model_id: str) -> Optional[ModelMetadata]:
        key = f"{provider_id}:{model_id}"
        return self._models.get(key)

    def list_all_models(self) -> List[ModelMetadata]:
        return list(self._models.values())

    def list_by_provider(self, provider_id: str) -> List[ModelMetadata]:
        return [m for m in self._models.values() if m.provider_id == provider_id]

    def find_capable_models(
        self,
        vision_required: bool = False,
        tools_required: bool = False,
        min_context: int = 0,
    ) -> List[ModelMetadata]:
        results = []
        for m in self._models.values():
            if not m.is_available:
                continue
            if vision_required and not m.capabilities.vision:
                continue
            if tools_required and not m.capabilities.tool_calling:
                continue
            if m.context_window < min_context:
                continue
            results.append(m)
        return results

    def _load_built_in_models(self) -> None:
        """Seed catalog with modern real-world models and pricing"""
        built_ins = [
            # Anthropic Claude
            ModelMetadata(
                provider_id="claude",
                model_id="claude-3-7-sonnet-20250219",
                display_name="Claude 3.7 Sonnet (Hybrid Reasoning)",
                context_window=200000,
                max_output_tokens=8192,
                input_modalities=[Modality.TEXT, Modality.IMAGE],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=True, tool_calling=True, structured_output=True),
                cost_per_million_input=3.0,
                cost_per_million_output=15.0,
                is_default=True,
            ),
            ModelMetadata(
                provider_id="claude",
                model_id="claude-3-5-sonnet-20241022",
                display_name="Claude 3.5 Sonnet",
                context_window=200000,
                max_output_tokens=8192,
                input_modalities=[Modality.TEXT, Modality.IMAGE],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=True, tool_calling=True, structured_output=True),
                cost_per_million_input=3.0,
                cost_per_million_output=15.0,
            ),
            ModelMetadata(
                provider_id="claude",
                model_id="claude-3-opus-20240229",
                display_name="Claude 3 Opus",
                context_window=200000,
                max_output_tokens=4096,
                input_modalities=[Modality.TEXT, Modality.IMAGE],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=True, tool_calling=True, structured_output=True),
                cost_per_million_input=15.0,
                cost_per_million_output=75.0,
            ),
            ModelMetadata(
                provider_id="claude",
                model_id="claude-3-5-haiku-20241022",
                display_name="Claude 3.5 Haiku",
                context_window=200000,
                max_output_tokens=4096,
                input_modalities=[Modality.TEXT],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=False, tool_calling=True, structured_output=True),
                cost_per_million_input=0.80,
                cost_per_million_output=4.0,
            ),

            # OpenAI
            ModelMetadata(
                provider_id="openai",
                model_id="gpt-4o",
                display_name="GPT-4o (Omni)",
                context_window=128000,
                max_output_tokens=4096,
                input_modalities=[Modality.TEXT, Modality.IMAGE],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=True, tool_calling=True, structured_output=True),
                cost_per_million_input=2.5,
                cost_per_million_output=10.0,
                is_default=True,
            ),
            ModelMetadata(
                provider_id="openai",
                model_id="gpt-4o-mini",
                display_name="GPT-4o Mini",
                context_window=128000,
                max_output_tokens=4096,
                input_modalities=[Modality.TEXT, Modality.IMAGE],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=True, tool_calling=True, structured_output=True),
                cost_per_million_input=0.15,
                cost_per_million_output=0.60,
            ),
            ModelMetadata(
                provider_id="openai",
                model_id="o3-mini",
                display_name="o3-mini (High Reasoning)",
                context_window=200000,
                max_output_tokens=65536,
                input_modalities=[Modality.TEXT],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=False, tool_calling=True, structured_output=True),
                cost_per_million_input=1.10,
                cost_per_million_output=4.40,
            ),

            # Google Gemini (Including Gemini 3.8 Next-Gen)
            ModelMetadata(
                provider_id="gemini",
                model_id="gemini-3.8-flash",
                display_name="Gemini 3.8 Flash (Fast Multimodal & Tool Use)",
                context_window=1000000,
                max_output_tokens=8192,
                input_modalities=[Modality.TEXT, Modality.IMAGE, Modality.AUDIO, Modality.VIDEO, Modality.DOCUMENT],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=True, audio_input=True, tool_calling=True, structured_output=True),
                cost_per_million_input=0.10,
                cost_per_million_output=0.40,
                is_default=True,
            ),
            ModelMetadata(
                provider_id="gemini",
                model_id="gemini-3.8-pro",
                display_name="Gemini 3.8 Pro (Advanced Reasoning & Deep Multimodal)",
                context_window=2000000,
                max_output_tokens=8192,
                input_modalities=[Modality.TEXT, Modality.IMAGE, Modality.AUDIO, Modality.VIDEO, Modality.DOCUMENT],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=True, audio_input=True, tool_calling=True, structured_output=True),
                cost_per_million_input=1.25,
                cost_per_million_output=5.00,
            ),
            ModelMetadata(
                provider_id="gemini",
                model_id="gemini-2.5-pro",
                display_name="Gemini 2.5 Pro (Multimodal & Reasoning)",
                context_window=2000000,
                max_output_tokens=8192,
                input_modalities=[Modality.TEXT, Modality.IMAGE, Modality.AUDIO, Modality.VIDEO, Modality.DOCUMENT],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=True, audio_input=True, tool_calling=True, structured_output=True),
                cost_per_million_input=1.25,
                cost_per_million_output=5.00,
            ),
            ModelMetadata(
                provider_id="gemini",
                model_id="gemini-2.5-flash",
                display_name="Gemini 2.5 Flash",
                context_window=1000000,
                max_output_tokens=8192,
                input_modalities=[Modality.TEXT, Modality.IMAGE, Modality.AUDIO, Modality.VIDEO],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=True, audio_input=True, tool_calling=True, structured_output=True),
                cost_per_million_input=0.15,
                cost_per_million_output=0.60,
            ),

            # DeepSeek
            ModelMetadata(
                provider_id="deepseek",
                model_id="deepseek-chat",
                display_name="DeepSeek-V3",
                context_window=64000,
                max_output_tokens=8192,
                input_modalities=[Modality.TEXT],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=False, tool_calling=True, structured_output=True),
                cost_per_million_input=0.14,
                cost_per_million_output=0.28,
                is_default=True,
            ),
            ModelMetadata(
                provider_id="deepseek",
                model_id="deepseek-reasoner",
                display_name="DeepSeek-R1 (Chain-of-Thought Reasoning)",
                context_window=64000,
                max_output_tokens=8192,
                input_modalities=[Modality.TEXT],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=False, tool_calling=False, structured_output=False),
                cost_per_million_input=0.55,
                cost_per_million_output=2.19,
            ),

            # Muse (Creative Narrative & Audio)
            ModelMetadata(
                provider_id="muse",
                model_id="muse-story-pro",
                display_name="Muse Story Pro (Narrative & Dialogue)",
                context_window=32000,
                max_output_tokens=4096,
                input_modalities=[Modality.TEXT],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=False, tool_calling=True, structured_output=True),
                cost_per_million_input=0.50,
                cost_per_million_output=1.50,
                is_default=True,
            ),
            ModelMetadata(
                provider_id="muse",
                model_id="muse-audio-engine",
                display_name="Muse Audio & Sound FX Director",
                context_window=16000,
                max_output_tokens=2048,
                input_modalities=[Modality.TEXT],
                output_modalities=[Modality.TEXT, Modality.AUDIO],
                capabilities=ModelCapabilities(vision=False, audio_output=True, tool_calling=True),
                cost_per_million_input=1.00,
                cost_per_million_output=3.00,
            ),

            # Dogxiai (Gaming Specialized AI)
            ModelMetadata(
                provider_id="dogxiai",
                model_id="dogxiai-game-master",
                display_name="Dogxiai Game Master 2.0",
                context_window=64000,
                max_output_tokens=4096,
                input_modalities=[Modality.TEXT],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=False, tool_calling=True, structured_output=True),
                cost_per_million_input=0.30,
                cost_per_million_output=0.90,
                is_default=True,
            ),
            ModelMetadata(
                provider_id="dogxiai",
                model_id="dogxiai-balance-bot",
                display_name="Dogxiai Combat & Balance Engine",
                context_window=32000,
                max_output_tokens=4096,
                input_modalities=[Modality.TEXT],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=False, tool_calling=True, structured_output=True),
                cost_per_million_input=0.25,
                cost_per_million_output=0.75,
            ),

            # Custom / Local Providers (Ollama, vLLM, LMStudio, LocalAI)
            ModelMetadata(
                provider_id="custom",
                model_id="local-model",
                display_name="Custom / Local OpenAI-Compatible Model",
                context_window=32000,
                max_output_tokens=4096,
                input_modalities=[Modality.TEXT],
                output_modalities=[Modality.TEXT],
                capabilities=ModelCapabilities(vision=False, tool_calling=True, structured_output=True),
                cost_per_million_input=0.0,
                cost_per_million_output=0.0,
                is_default=True,
            ),
        ]

        for meta in built_ins:
            self.register_model(meta)
