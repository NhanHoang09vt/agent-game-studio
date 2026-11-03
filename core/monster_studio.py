"""
Monster Design Studio for AI Game Development Studio.
Manages monster tiers, anatomy, evolution trees, combat roles, and sprite references.
"""

import os
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MonsterTier(str, Enum):
    NORMAL = "normal"
    ELITE = "elite"
    RARE = "rare"
    MINI_BOSS = "mini_boss"
    WORLD_BOSS = "world_boss"
    EVOLUTION = "evolution"


class MonsterProfile(BaseModel):
    monster_id: str
    name: str
    species: str
    tier: MonsterTier = MonsterTier.NORMAL
    evolution_stage: int = 1
    evolution_line_id: Optional[str] = None
    size: str = "medium"  # tiny, small, medium, large, colossal
    silhouette_traits: List[str]
    color_palette: List[str]  # Hex codes
    anatomy_notes: str
    material_types: List[str]  # e.g. ["carapace", "glow_core", "slime"]
    combat_role: str  # melee_swarmer, ranged_caster, tank, assassin, raid_boss
    animation_requirements: List[str] = Field(default_factory=lambda: ["idle", "move", "attack", "hit", "die"])
    created_at: float = Field(default_factory=time.time)


class MonsterStudio:
    """Manages monster catalogs, evolution chains, and visual specifications"""

    def __init__(self, storage_dir: str = "./data/monsters"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._monsters: Dict[str, MonsterProfile] = {}

    def register_monster(self, monster: MonsterProfile) -> MonsterProfile:
        self._monsters[monster.monster_id] = monster
        fpath = os.path.join(self.storage_dir, f"{monster.monster_id}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(monster.model_dump_json(indent=2))
        return monster

    def get_monster(self, monster_id: str) -> Optional[MonsterProfile]:
        if monster_id in self._monsters:
            return self._monsters[monster_id]
        fpath = os.path.join(self.storage_dir, f"{monster_id}.json")
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                monster = MonsterProfile(**data)
                self._monsters[monster_id] = monster
                return monster
        return None

    def list_monsters(self, tier: Optional[MonsterTier] = None) -> List[MonsterProfile]:
        for fname in os.listdir(self.storage_dir):
            if fname.endswith(".json"):
                mid = fname.replace(".json", "")
                self.get_monster(mid)
        res = list(self._monsters.values())
        if tier:
            res = [m for m in res if m.tier == tier]
        return res

    def get_evolution_chain(self, line_id: str) -> List[MonsterProfile]:
        chain = [m for m in self.list_monsters() if m.evolution_line_id == line_id]
        chain.sort(key=lambda m: m.evolution_stage)
        return chain
