"""
Integration Tests for Studio Dashboard REST API Server.
"""

import pytest
from fastapi.testclient import TestClient
from dashboard.api_server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_overview(client):
    res = client.get("/api/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["total_agents"] >= 49
    assert data["total_providers"] >= 7
    assert data["total_skills"] >= 74


def test_api_providers_list(client):
    res = client.get("/api/providers")
    assert res.status_code == 200
    providers = res.json()
    p_ids = [p["provider_id"] for p in providers]
    for expected in ["openai", "claude", "gemini", "deepseek", "muse", "dogxiai", "custom"]:
        assert expected in p_ids


def test_api_agents_list(client):
    res = client.get("/api/agents")
    assert res.status_code == 200
    agents = res.json()
    assert len(agents) >= 49

    # Filter by tier
    res_tier1 = client.get("/api/agents?tier=1")
    assert res_tier1.status_code == 200
    assert all(a["definition"]["tier"] == 1 for a in res_tier1.json())


def test_api_agent_assign_model(client):
    res = client.post(
        "/api/agents/game-designer/assign-model",
        json={"provider_id": "openai", "model_id": "gpt-4o", "backup_model": "deepseek-chat"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["agent"]["assigned_provider"] == "openai"
    assert data["agent"]["assigned_model"] == "gpt-4o"


def test_api_execute_task(client):
    res = client.post(
        "/api/tasks/execute",
        json={
            "task_id": "test_api_task",
            "title": "Test Combat Damage",
            "assigned_agent_id": "systems-designer",
            "instruction": "Output combat damage formula",
            "enable_peer_review": True,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["task_id"] == "test_api_task"
    assert data["status"] == "completed"
    assert len(data["result_content"]) > 0
    assert data["review_summary"] is not None


def test_api_hierarchical_delegation(client):
    res = client.post(
        "/api/tasks/hierarchical-delegation",
        json={"goal": "Design a 2.5D Real-time Action Combat System"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "director_output" in data
    assert "lead_output" in data
    assert "specialist_output" in data
    assert "review" in data
