"""
Tests for Agent Management, Studio Organization, and Multi-Agent Orchestration.
"""

import pytest
import os
from core.provider_manager import ProviderManager
from core.agent_runtime import AgentManager, AgentDefinition
from core.orchestration import (
    MultiAgentOrchestrationEngine,
    TaskNode,
    TaskStatus,
)
from core.security import PermissionManager, FileLockManager


@pytest.fixture
def studio_setup():
    pm = ProviderManager()
    am = AgentManager(pm)
    upstream_agents = os.path.join(os.path.dirname(__file__), "..", "upstream", ".claude", "agents")
    loaded = am.load_all_upstream_agents(upstream_agents)
    orch = MultiAgentOrchestrationEngine(am)
    return pm, am, orch, loaded


def test_load_all_upstream_agents(studio_setup):
    _, am, _, loaded = studio_setup
    assert loaded == 49, f"Expected 49 agents loaded from upstream, got {loaded}"

    # Verify key agents exist across all tiers
    cd = am.get_agent("creative-director")
    assert cd is not None
    assert cd.tier == 1
    assert cd.assigned_provider == "claude"

    td = am.get_agent("technical-director")
    assert td is not None
    assert td.assigned_provider == "openai"

    lp = am.get_agent("lead-programmer")
    assert lp is not None
    assert lp.tier == 2
    assert lp.assigned_provider == "deepseek"

    gd = am.get_agent("game-designer")
    assert gd is not None
    assert gd.assigned_provider == "gemini"

    # Verify AI Operations Director was registered
    ai_ops = am.get_agent("ai-operations-director")
    assert ai_ops is not None
    assert ai_ops.tier == 1


def test_agent_model_reassignment(studio_setup):
    _, am, _, _ = studio_setup
    # Reassign Lead Programmer from DeepSeek to OpenAI GPT-4o
    assert am.update_agent_model("lead-programmer", "openai", "gpt-4o", backup_model="deepseek-chat")
    agent = am.get_agent("lead-programmer")
    assert agent.assigned_provider == "openai"
    assert agent.assigned_model == "gpt-4o"
    assert agent.backup_model == "deepseek-chat"


def test_agent_clone_and_crud(studio_setup):
    _, am, _, _ = studio_setup
    cloned = am.clone_agent("gameplay-programmer", "custom-combat-coder", "Custom Combat Coder")
    assert cloned is not None
    assert cloned.agent_id == "custom-combat-coder"
    assert am.get_agent("custom-combat-coder") is not None

    # Test YAML export / import
    yaml_str = am.export_agent_yaml("custom-combat-coder")
    assert "Custom Combat Coder" in yaml_str
    assert am.delete_agent("custom-combat-coder")
    assert am.get_agent("custom-combat-coder") is None


@pytest.mark.asyncio
async def test_dag_cycle_detection(studio_setup):
    _, _, orch, _ = studio_setup

    # Cycle: task1 -> task2 -> task1
    task1 = TaskNode(task_id="t1", title="Task 1", assigned_agent_id="creative-director", instruction="Do 1", dependencies=["t2"])
    task2 = TaskNode(task_id="t2", title="Task 2", assigned_agent_id="game-designer", instruction="Do 2", dependencies=["t1"])

    assert not orch.validate_dag([task1, task2]), "Orchestrator should detect cycle"


@pytest.mark.asyncio
async def test_parallel_dag_execution(studio_setup):
    _, _, orch, _ = studio_setup

    tasks = [
        TaskNode(task_id="spec_gameplay", title="Gameplay Spec", assigned_agent_id="gameplay-programmer", instruction="Write jump mechanics"),
        TaskNode(task_id="spec_audio", title="Audio Spec", assigned_agent_id="sound-designer", instruction="List jump sounds"),
        TaskNode(task_id="integrate", title="Integration", assigned_agent_id="lead-programmer", instruction="Review jump and audio", dependencies=["spec_gameplay", "spec_audio"]),
    ]

    results = await orch.execute_task_graph(tasks, enable_cross_model_review=True, reviewer_agent_ids=["qa-lead"])

    assert results["spec_gameplay"].status == TaskStatus.COMPLETED
    assert results["spec_audio"].status == TaskStatus.COMPLETED
    assert results["integrate"].status == TaskStatus.COMPLETED
    assert results["integrate"].review_summary is not None
    assert "consensus" in results["integrate"].review_summary


@pytest.mark.asyncio
async def test_hierarchical_delegation(studio_setup):
    _, _, orch, _ = studio_setup

    result = await orch.execute_hierarchical_delegation(
        project_goal="Implement 2.5D Real-time Action Combat",
        director_agent_id="creative-director",
        lead_agent_id="game-designer",
        specialist_agent_id="systems-designer",
    )

    assert result["director_output"] is not None
    assert result["lead_output"] is not None
    assert result["specialist_output"] is not None
    assert result["review"] is not None
