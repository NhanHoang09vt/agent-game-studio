"""
Environment & Map Studio for AI Game Development Studio.
Manages biomes, tilesets, modular props, terrain, and collision specifications.
"""

import os
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BiomeType(str, Enum):
    VILLAGE = "village"
    CITY_CYBERPUNK = "city_cyberpunk"
    DUNGEON_CRYPT = "dungeon_crypt"
    FOREST_ANCIENT = "forest_ancient"
    DESERT_WASTELAND = "desert_wasteland"
    VOLCANIC_CAVE = "volcanic_cave"
    CASTLE_CITADEL = "castle_citadel"


class TileLayer(str, Enum):
    TERRAIN_BASE = "terrain_base"
    TERRAIN_OVERLAY = "terrain_overlay"
    WALLS_COLLISION = "walls_collision"
    PROPS_DECORATION = "props_decoration"
    INTERACTIVE = "interactive"


class TilesetSpec(BaseModel):
    tileset_id: str
    biome: BiomeType
    tile_size_px: int = 32
    columns: int = 8
    rows: int = 8
    texture_path: str
    tile_definitions: Dict[str, Dict[str, Any]] = Field(default_factory=lambda: {
        "floor_01": {"x": 0, "y": 0, "walkable": True},
        "floor_02": {"x": 1, "y": 0, "walkable": True},
        "wall_top": {"x": 2, "y": 0, "walkable": False, "blocks_vision": True},
        "wall_mid": {"x": 3, "y": 0, "walkable": False, "blocks_vision": True},
        "chest": {"x": 0, "y": 1, "walkable": False, "interactive": True},
        "door_closed": {"x": 1, "y": 1, "walkable": False, "interactive": True},
        "door_open": {"x": 2, "y": 1, "walkable": True, "interactive": True},
        "spikes": {"x": 3, "y": 1, "walkable": True, "hazard": True},
    })


class EnvironmentStudio:
    """Manages game biomes, tilesets, and collision layers"""

    def __init__(self, storage_dir: str = "./data/environments"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._tilesets: Dict[str, TilesetSpec] = {}

    def register_tileset(self, spec: TilesetSpec) -> TilesetSpec:
        self._tilesets[spec.tileset_id] = spec
        fpath = os.path.join(self.storage_dir, f"{spec.tileset_id}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(spec.model_dump_json(indent=2))
        return spec

    def get_tileset(self, tileset_id: str) -> Optional[TilesetSpec]:
        if tileset_id in self._tilesets:
            return self._tilesets[tileset_id]
        fpath = os.path.join(self.storage_dir, f"{tileset_id}.json")
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                ts = TilesetSpec(**data)
                self._tilesets[tileset_id] = ts
                return ts
        return None
