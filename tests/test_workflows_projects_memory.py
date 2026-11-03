"""
Tests for Skills, Workflow Engine, Project Management, Memory, and Asset Pipeline.
"""

import pytest
import os
from core.provider_manager import ProviderManager
from core.agent_runtime import AgentManager
from core.orchestration import MultiAgentOrchestrationEngine
from core.workflow_engine import WorkflowEngine
from core.project_manager import ProjectManager, GameGenre, EngineType
from core.memory import TieredMemoryManager, MemoryTier
from core.asset_pipeline import AssetPipeline, GameAsset, AssetCategory, AssetApprovalStatus


@pytest.fixture
def workflow_setup():
    pm = ProviderManager()
    am = AgentManager(pm)
    upstream_agents = os.path.join(os.path.dirname(__file__), "..", "upstream", ".claude", "agents")
    am.load_all_upstream_agents(upstream_agents)
    orch = MultiAgentOrchestrationEngine(am)
    wf_engine = WorkflowEngine(am, orch)
    upstream_skills = os.path.join(os.path.dirname(__file__), "..", "upstream", ".claude", "skills")
    skills_loaded = wf_engine.load_all_upstream_skills(upstream_skills)
    return am, orch, wf_engine, skills_loaded


def test_load_all_upstream_skills(workflow_setup):
    _, _, wf_engine, loaded = workflow_setup
    assert loaded == 74, f"Expected 74 skills loaded from upstream, got {loaded}"

    # Verify key skills
    assert wf_engine.get_skill("start") is not None
    assert wf_engine.get_skill("brainstorm") is not None
    assert wf_engine.get_skill("dev-story") is not None
    assert wf_engine.get_skill("code-review") is not None
    assert wf_engine.get_skill("team-combat") is not None


@pytest.mark.asyncio
async def test_execute_skill(workflow_setup):
    _, _, wf_engine, _ = workflow_setup
    res = await wf_engine.execute_skill(
        skill_id="brainstorm",
        assigned_agent_id="creative-director",
        user_arguments="2.5D Cyberpunk Action RPG",
    )
    assert res is not None
    assert len(res.content) > 0


def test_multi_project_management():
    pm = ProjectManager("./tests_data/projects")
    proj = pm.create_project(
        project_id="neon_strike",
        name="Neon Strike: 2.5D Cyberpunk",
        genre=GameGenre.MMORPG_25D,
        engine=EngineType.GODOT_4,
    )
    assert proj.project_id == "neon_strike"
    assert proj.engine == EngineType.GODOT_4
    assert os.path.exists(proj.entities_db_path)

    profile = pm.get_engine_profile(EngineType.GODOT_4)
    assert profile.specialist_agent_id == "godot-specialist"
    assert ".gd" in profile.file_extensions


def test_tiered_memory_isolation():
    mem = TieredMemoryManager("./tests_data/memory")

    # Store in Project A
    mem.store_entry(
        tier=MemoryTier.PROJECT,
        project_id="project_alpha",
        title="Combat Damage Multipliers",
        content="Crit multiplier is fixed at 1.75x.",
        tags=["combat", "formula"],
    )

    # Store in Project B
    mem.store_entry(
        tier=MemoryTier.PROJECT,
        project_id="project_beta",
        title="Stealth Mechanics",
        content="Invisibility lasts for 5 seconds.",
        tags=["stealth"],
    )

    # Retrieve for Agent in Project Alpha
    alpha_ctx = mem.retrieve_context_for_agent(
        agent_id="combat-designer",
        project_id="project_alpha",
        query="combat multiplier",
    )
    assert any("Crit multiplier" in e.content for e in alpha_ctx)
    # Ensure Project Beta data did NOT leak
    assert not any("Invisibility" in e.content for e in alpha_ctx)


def test_asset_pipeline_and_validation():
    pipeline = AssetPipeline("./tests_data/assets_manifest.json")

    asset = GameAsset(
        asset_id="sword_01",
        project_id="neon_strike",
        name="Plasma Katana",
        category=AssetCategory.MODEL_3D,
        file_path="assets/weapons/plasma_katana.glb",
        file_format=".glb",
        polycount=12000,
        created_by_agent_id="technical-artist",
    )

    valid, errors = pipeline.validate_asset_spec(asset)
    assert valid, f"Asset spec should be valid: {errors}"

    pipeline.register_asset(asset)
    assert pipeline.review_asset("sword_01", approved=True, notes="Excellent LOD topology.")
    updated = pipeline.get_asset("sword_01")
    assert updated.approval_status == AssetApprovalStatus.APPROVED
