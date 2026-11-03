"""
Unit and integration tests for Multi-Provider AI Architecture.
Verifies adapter instantiation, canonical conversion, fallback mechanisms,
cost estimation, and model registry capabilities.
"""

import pytest
import asyncio
from core.types import (
    CanonicalMessage,
    MessageRole,
    Modality,
    ModelCapabilities,
    ModelMetadata,
)
from core.model_registry import ModelRegistry
from core.provider_manager import ProviderManager
from providers.openai_adapter import OpenAIAdapter
from providers.claude_adapter import ClaudeAdapter
from providers.gemini_adapter import GeminiAdapter
from providers.deepseek_adapter import DeepSeekAdapter
from providers.muse_adapter import MuseAdapter
from providers.dogxiai_adapter import DogxiaiAdapter
from providers.custom_adapter import CustomAdapter


def test_model_registry_builtins():
    registry = ModelRegistry()
    all_models = registry.list_all_models()
    assert len(all_models) >= 14, "Model registry should contain at least 14 built-in models"

    # Test provider query
    gemini_models = registry.list_by_provider("gemini")
    assert any(m.model_id == "gemini-2.5-pro" for m in gemini_models)
    assert any(m.capabilities.vision for m in gemini_models)

    deepseek_models = registry.list_by_provider("deepseek")
    assert any(m.model_id == "deepseek-chat" for m in deepseek_models)
    assert any(m.model_id == "deepseek-reasoner" for m in deepseek_models)

    # Test capability search
    vision_models = registry.find_capable_models(vision_required=True)
    assert all(m.capabilities.vision for m in vision_models)
    assert any(m.provider_id == "gemini" for m in vision_models)
    assert any(m.provider_id == "openai" for m in vision_models)


def test_cost_calculation():
    adapter = DeepSeekAdapter()
    # DeepSeek-V3: 0.14 input, 0.28 output per million
    cost = adapter.calculate_cost("deepseek-chat", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost == pytest.approx(0.42, 0.001)


@pytest.mark.asyncio
async def test_provider_manager_initialization():
    pm = ProviderManager()
    statuses = pm.get_all_statuses()
    provider_ids = [s.provider_id for s in statuses]

    for expected in ["openai", "claude", "gemini", "deepseek", "muse", "dogxiai", "custom"]:
        assert expected in provider_ids

    # Test enable / disable toggle
    assert pm.set_provider_enabled("dogxiai", False)
    assert not pm.get_status("dogxiai").is_enabled
    assert pm.set_provider_enabled("dogxiai", True)
    assert pm.get_status("dogxiai").is_enabled


@pytest.mark.asyncio
async def test_offline_mock_completion():
    """Verify that adapters can run offline / dry-run safely without throwing crashes"""
    messages = [
        CanonicalMessage(role=MessageRole.SYSTEM, content="You are a senior game systems designer."),
        CanonicalMessage(role=MessageRole.USER, content="Design a durability formula for swords."),
    ]

    adapters = [
        ("openai", "gpt-4o"),
        ("claude", "claude-3-7-sonnet-20250219"),
        ("gemini", "gemini-2.5-pro"),
        ("deepseek", "deepseek-chat"),
        ("muse", "muse-story-pro"),
        ("dogxiai", "dogxiai-game-master"),
        ("custom", "local-model"),
    ]

    pm = ProviderManager()

    for pid, model in adapters:
        resp = await pm.execute_chat_with_fallback(
            provider_id=pid,
            model_id=model,
            messages=messages,
        )
        assert resp is not None
        assert len(resp.content) > 0
        assert resp.usage.total_tokens > 0
