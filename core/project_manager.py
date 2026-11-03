"""
Multi-Project Management & Game Engine Support Engine.
Enables running multiple independent game projects simultaneously,
with isolated databases (GDD, ADR, entities, items, quests), sprint states,
and game engine profile bindings (Godot, Unity, Unreal, Phaser, Three.js, Babylon.js).
"""

import os
import json
import yaml
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GameGenre(str, Enum):
    MMORPG = "mmorpg"
    MMORPG_25D = "mmorpg_2.5d"
    IDLE_RPG = "idle_rpg"
    AFK_RPG = "afk_rpg"
    RACING = "racing"
    SIMULATION = "simulation"
    STRATEGY = "strategy"
    SURVIVAL = "survival"
    TOWER_DEFENSE = "tower_defense"
    BROWSER_GAME = "browser_game"
    ACTION_RPG = "action_rpg"


class EngineType(str, Enum):
    GODOT_4 = "godot_4"
    UNITY = "unity"
    UNREAL_5 = "unreal_5"
    THREE_JS = "three_js"
    BABYLON_JS = "babylon_js"
    PHASER = "phaser"
    HTML5_CANVAS = "html5_canvas"


class EngineProfile(BaseModel):
    engine_type: EngineType
    version: str
    primary_language: str
    specialist_agent_id: str
    code_root_dir: str
    asset_root_dir: str
    file_extensions: List[str]


class GameProject(BaseModel):
    project_id: str
    name: str
    genre: GameGenre
    engine: EngineType
    target_platforms: List[str] = Field(default_factory=lambda: ["PC", "Web"])
    created_at: float = Field(default_factory=time.time)
    stage: str = "Concept"  # Concept, Systems, Architecture, Pre-Production, Production, Polish, Release
    gdd_path: str
    adr_path: str
    entities_db_path: str
    workspace_dir: str
    active_sprint: str = "Sprint 1"
    active_sprint_goal: str = "MVP Prototype"


class ProjectManager:
    """
    Manages multi-project workspaces, entity registries, and engine integration.
    """

    def __init__(self, base_projects_dir: str = "./data/projects"):
        self.base_projects_dir = base_projects_dir
        os.makedirs(self.base_projects_dir, exist_ok=True)
        self._projects: Dict[str, GameProject] = {}
        self._engine_profiles: Dict[EngineType, EngineProfile] = self._init_engine_profiles()

    def _init_engine_profiles(self) -> Dict[EngineType, EngineProfile]:
        return {
            EngineType.GODOT_4: EngineProfile(
                engine_type=EngineType.GODOT_4,
                version="4.3-stable",
                primary_language="GDScript",
                specialist_agent_id="godot-specialist",
                code_root_dir="src",
                asset_root_dir="assets",
                file_extensions=[".gd", ".tscn", ".tres", ".gdshader"],
            ),
            EngineType.UNITY: EngineProfile(
                engine_type=EngineType.UNITY,
                version="6000.0.x (Unity 6)",
                primary_language="C#",
                specialist_agent_id="unity-specialist",
                code_root_dir="Assets/Scripts",
                asset_root_dir="Assets",
                file_extensions=[".cs", ".prefab", ".shader", ".asset"],
            ),
            EngineType.UNREAL_5: EngineProfile(
                engine_type=EngineType.UNREAL_5,
                version="5.5",
                primary_language="C++ / Blueprints",
                specialist_agent_id="unreal-specialist",
                code_root_dir="Source",
                asset_root_dir="Content",
                file_extensions=[".cpp", ".h", ".uasset", ".umap"],
            ),
            EngineType.THREE_JS: EngineProfile(
                engine_type=EngineType.THREE_JS,
                version="r170",
                primary_language="TypeScript / JavaScript",
                specialist_agent_id="engine-programmer",
                code_root_dir="src",
                asset_root_dir="public/assets",
                file_extensions=[".ts", ".js", ".glsl", ".json"],
            ),
            EngineType.PHASER: EngineProfile(
                engine_type=EngineType.PHASER,
                version="3.85.0",
                primary_language="TypeScript / JavaScript",
                specialist_agent_id="gameplay-programmer",
                code_root_dir="src",
                asset_root_dir="public/assets",
                file_extensions=[".ts", ".js", ".png", ".json"],
            ),
        }

    def create_project(
        self,
        project_id: str,
        name: str,
        genre: GameGenre,
        engine: EngineType = EngineType.GODOT_4,
        target_platforms: Optional[List[str]] = None,
    ) -> GameProject:
        project_dir = os.path.join(self.base_projects_dir, project_id)
        os.makedirs(os.path.join(project_dir, "design", "gdd"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "design", "registry"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "docs", "architecture"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "production", "epics"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)

        # Initialize base entities.yaml
        entities_path = os.path.join(project_dir, "design", "registry", "entities.yaml")
        if not os.path.exists(entities_path):
            with open(entities_path, "w", encoding="utf-8") as f:
                yaml.dump({
                    "project_id": project_id,
                    "schema_version": 1,
                    "entities": {},
                    "items": {},
                    "skills": {},
                    "quests": {},
                }, f)

        # Initialize project.yaml config
        config_path = os.path.join(project_dir, "project.yaml")
        if not os.path.exists(config_path):
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump({
                    "schema_version": 2,
                    "project": {
                        "id": project_id,
                        "name": name,
                        "genre": genre.value,
                        "engine": engine.value,
                        "stage": "Concept",
                    },
                    "modes": {
                        "rigor": "standard",
                        "automation": "collaborative",
                    },
                }, f)

        project = GameProject(
            project_id=project_id,
            name=name,
            genre=genre,
            engine=engine,
            target_platforms=target_platforms or ["PC"],
            gdd_path=os.path.join(project_dir, "design", "gdd"),
            adr_path=os.path.join(project_dir, "docs", "architecture"),
            entities_db_path=entities_path,
            workspace_dir=project_dir,
        )

        self._projects[project_id] = project
        return project

    def get_project(self, project_id: str) -> Optional[GameProject]:
        return self._projects.get(project_id)

    def list_projects(self) -> List[GameProject]:
        return list(self._projects.values())

    def get_engine_profile(self, engine: EngineType) -> Optional[EngineProfile]:
        return self._engine_profiles.get(engine)
