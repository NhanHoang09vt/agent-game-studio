"""
Studio Dashboard REST API Server for AI Game Development Studio.
Exposes endpoints for studio overview, multi-provider health, agent model assignments,
task DAG orchestration, cross-model reviews, and multi-project management.
"""

import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.provider_manager import ProviderManager
from core.agent_runtime import AgentManager, AgentDefinition
from core.orchestration import MultiAgentOrchestrationEngine, TaskNode, TaskStatus
from core.workflow_engine import WorkflowEngine
from core.project_manager import ProjectManager, GameGenre, EngineType
from core.memory import TieredMemoryManager
from core.asset_pipeline import AssetPipeline
from core.security import PermissionManager, RollbackCheckpointManager
from core.art_direction import ArtDirectionManager, ArtBible
from core.character_studio import CharacterStudio, CharacterIdentityProfile
from core.monster_studio import MonsterStudio, MonsterProfile
from core.playable_pipeline import PlayablePipeline
from core.asset_consistency import AssetConsistencyEngine


app = FastAPI(
    title="AI Game Development Studio — Multi-Agent Edition API",
    version="2.0.0",
    description="Multi-Provider AI Agent Orchestration Platform for Professional Game Development",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global studio singleton dependencies
pm = ProviderManager()
am = AgentManager(pm)
orch = MultiAgentOrchestrationEngine(am)
wf_engine = WorkflowEngine(am, orch)
proj_mgr = ProjectManager()
mem_mgr = TieredMemoryManager()
asset_pipe = AssetPipeline()
perm_mgr = PermissionManager()
rollback_mgr = RollbackCheckpointManager()

# Art Studio singletons
art_mgr = ArtDirectionManager()
char_studio = CharacterStudio()
monster_studio = MonsterStudio()
playable_pipe = PlayablePipeline(output_root=os.path.join(os.path.dirname(__file__), "static", "playable"))

# Pre-generate standard playable game asset bundle on startup
playable_bundle = playable_pipe.generate_complete_game_bundle(
    project_id="neon_chronicles",
    game_title="Neon Chronicles: 2.5D Cyberpunk RPG",
)

# Load upstream assets on startup
upstream_agents_dir = os.path.join(os.path.dirname(__file__), "..", "upstream", ".claude", "agents")
upstream_skills_dir = os.path.join(os.path.dirname(__file__), "..", "upstream", ".claude", "skills")
am.load_all_upstream_agents(upstream_agents_dir)
wf_engine.load_all_upstream_skills(upstream_skills_dir)

# Seed a default sample project if none exists
if not proj_mgr.list_projects():
    proj_mgr.create_project(
        project_id="neon_chronicles",
        name="Neon Chronicles: 2.5D Cyberpunk RPG",
        genre=GameGenre.MMORPG_25D,
        engine=EngineType.GODOT_4,
    )


# -----------------------------------------------------------------------------
# 1. OVERVIEW & TELEMETRY
# -----------------------------------------------------------------------------
@app.get("/api/overview")
def get_studio_overview() -> Dict[str, Any]:
    statuses = pm.get_all_statuses()
    agents = am.list_agents()
    projects = proj_mgr.list_projects()
    active_agents = [a for a in agents if am.get_instance(a.agent_id) and am.get_instance(a.agent_id).status.value != "idle"]

    total_tokens = sum(s.total_tokens_used for s in statuses)
    total_cost = sum(s.total_cost_usd for s in statuses)
    total_reqs = sum(s.total_requests for s in statuses)
    failed_reqs = sum(s.failed_requests for s in statuses)

    return {
        "studio_name": "AI Game Development Studio — Multi-Agent Edition",
        "total_projects": len(projects),
        "total_agents": len(agents),
        "active_agents": len(active_agents),
        "total_providers": len(statuses),
        "connected_providers": len([s for s in statuses if s.is_configured]),
        "total_skills": len(wf_engine.list_skills()),
        "total_workflows": len(wf_engine.list_workflows()),
        "total_tokens_used": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "total_requests": total_reqs,
        "failed_requests": failed_reqs,
    }


# -----------------------------------------------------------------------------
# 2. PROVIDER MANAGEMENT
# -----------------------------------------------------------------------------
@app.get("/api/providers")
def list_providers():
    return pm.get_all_statuses()


@app.get("/api/providers/{provider_id}")
def get_provider_detail(provider_id: str):
    status = pm.get_status(provider_id)
    if not status:
        raise HTTPException(status_code=404, detail="Provider not found")
    models = pm.model_registry.list_by_provider(provider_id)
    return {
        "status": status,
        "models": models,
    }


class ProviderUpdateRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    fallback_model: Optional[str] = None
    is_enabled: Optional[bool] = None


@app.post("/api/providers/{provider_id}/update")
def update_provider(provider_id: str, req: ProviderUpdateRequest):
    if req.is_enabled is not None:
        pm.set_provider_enabled(provider_id, req.is_enabled)
    pm.update_provider_config(
        provider_id,
        api_key=req.api_key,
        base_url=req.base_url,
        default_model=req.default_model,
        fallback_model=req.fallback_model,
    )
    return {"success": True, "status": pm.get_status(provider_id)}


@app.post("/api/providers/{provider_id}/test")
async def test_provider_connection(provider_id: str):
    res = await pm.test_connection(provider_id)
    return res


# -----------------------------------------------------------------------------
# 3. AGENT MANAGEMENT
# -----------------------------------------------------------------------------
@app.get("/api/agents")
def list_agents(department: Optional[str] = None, tier: Optional[int] = None):
    agents = am.list_agents(department=department, tier=tier)
    output = []
    for a in agents:
        inst = am.get_instance(a.agent_id)
        output.append({
            "definition": a,
            "runtime_status": inst.status.value if inst else "idle",
            "tokens_consumed": inst.total_tokens_consumed if inst else 0,
            "cost_consumed": round(inst.total_cost_consumed, 4) if inst else 0.0,
        })
    return output


@app.get("/api/agents/{agent_id}")
def get_agent_detail(agent_id: str):
    agent = am.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    inst = am.get_instance(agent_id)
    return {
        "definition": agent,
        "runtime_status": inst.status.value if inst else "idle",
        "history": [h.model_dump() for h in (inst.history if inst else [])],
    }


class AgentModelAssignmentRequest(BaseModel):
    provider_id: str
    model_id: str
    backup_model: Optional[str] = None


@app.post("/api/agents/{agent_id}/assign-model")
def assign_agent_model(agent_id: str, req: AgentModelAssignmentRequest):
    success = am.update_agent_model(agent_id, req.provider_id, req.model_id, req.backup_model)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "agent": am.get_agent(agent_id)}


# -----------------------------------------------------------------------------
# 4. ORCHESTRATION & TASK EXECUTION
# -----------------------------------------------------------------------------
class ExecuteTaskRequest(BaseModel):
    task_id: str
    title: str
    assigned_agent_id: str
    instruction: str
    enable_peer_review: bool = True
    reviewer_agent_ids: Optional[List[str]] = None


@app.post("/api/tasks/execute")
async def execute_studio_task(req: ExecuteTaskRequest):
    task = TaskNode(
        task_id=req.task_id,
        title=req.title,
        assigned_agent_id=req.assigned_agent_id,
        instruction=req.instruction,
    )
    results = await orch.execute_task_graph(
        [task],
        enable_cross_model_review=req.enable_peer_review,
        reviewer_agent_ids=req.reviewer_agent_ids or ["technical-director", "qa-lead"],
    )
    completed_task = results[req.task_id]
    return {
        "task_id": completed_task.task_id,
        "status": completed_task.status.value,
        "result_content": completed_task.result_content,
        "review_summary": completed_task.review_summary,
        "error_message": completed_task.error_message,
    }


class DelegationRequest(BaseModel):
    goal: str
    director_id: str = "creative-director"
    lead_id: str = "game-designer"
    specialist_id: str = "systems-designer"


@app.post("/api/tasks/hierarchical-delegation")
async def execute_delegation(req: DelegationRequest):
    res = await orch.execute_hierarchical_delegation(
        project_goal=req.goal,
        director_agent_id=req.director_id,
        lead_agent_id=req.lead_id,
        specialist_agent_id=req.specialist_id,
    )
    return res


# -----------------------------------------------------------------------------
# 5. PROJECTS & SKILLS
# -----------------------------------------------------------------------------
@app.get("/api/projects")
def list_projects():
    return proj_mgr.list_projects()


@app.get("/api/skills")
def list_skills():
    return wf_engine.list_skills()


@app.get("/api/workflows")
def list_workflows():
    return wf_engine.list_workflows()


# -----------------------------------------------------------------------------
# 6. ART STUDIO & ASSET PRODUCTION
# -----------------------------------------------------------------------------
@app.get("/api/art/bible")
def get_art_bible(project_id: str = "neon_chronicles"):
    return art_mgr.get_bible(project_id)


@app.post("/api/art/generate-bundle")
def generate_playable_bundle(project_id: str = "neon_chronicles", title: str = "Neon Chronicles"):
    pkg = playable_pipe.generate_complete_game_bundle(project_id, title)
    return {"success": True, "package": pkg}


@app.get("/api/art/characters")
def list_art_characters():
    return char_studio.list_characters()


@app.get("/api/art/monsters")
def list_art_monsters():
    return monster_studio.list_monsters()


@app.get("/api/art/bundle-status")
def get_bundle_status(project_id: str = "neon_chronicles"):
    bpath = os.path.join(playable_pipe.output_root, project_id, "game_manifest.json")
    exists = os.path.exists(bpath)
    return {
        "project_id": project_id,
        "is_generated": exists,
        "manifest_path": bpath if exists else None,
        "playable_url": "/game",
    }


# -----------------------------------------------------------------------------
# STATIC FILES & SPA SERVING
# -----------------------------------------------------------------------------
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>AI Game Development Studio Dashboard</h1><p>Visit /docs for OpenAPI specs.</p>"


@app.get("/game", response_class=HTMLResponse)
def serve_game():
    game_file = os.path.join(static_dir, "game.html")
    if os.path.exists(game_file):
        with open(game_file, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="Game file not found")
