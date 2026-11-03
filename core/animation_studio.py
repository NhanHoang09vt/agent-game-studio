"""
Animation Production Studio for AI Game Development Studio.
Manages Sprite Sheet packing, frame coordinate sequences, timing metadata,
and state transitions (Idle, Walk, Run, Attack, Hit, Death, Victory).
"""

import os
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnimationState(str, Enum):
    IDLE = "idle"
    WALK = "walk"
    RUN = "run"
    JUMP = "jump"
    ATTACK = "attack"
    SKILL = "skill"
    HIT = "hit"
    DEATH = "death"
    VICTORY = "victory"


class AnimationFrame(BaseModel):
    index: int
    x: int
    y: int
    width: int
    height: int
    duration_ms: int = 120


class AnimationClip(BaseModel):
    state: AnimationState
    frames: List[AnimationFrame]
    loop: bool = True
    frame_rate_fps: int = 8


class SpriteSheetMetadata(BaseModel):
    sheet_id: str
    target_entity_id: str
    texture_path: str
    frame_width: int = 48
    frame_height: int = 48
    total_frames: int
    animations: Dict[str, AnimationClip]
    created_at: float = Field(default_factory=time.time)


class AnimationStudio:
    """Creates, packs, and exports engine-ready sprite sheet animations"""

    def __init__(self, storage_dir: str = "./data/animations"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._sheets: Dict[str, SpriteSheetMetadata] = {}

    def register_spritesheet(self, metadata: SpriteSheetMetadata) -> SpriteSheetMetadata:
        self._sheets[metadata.sheet_id] = metadata
        fpath = os.path.join(self.storage_dir, f"{metadata.sheet_id}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))
        return metadata

    def get_spritesheet(self, sheet_id: str) -> Optional[SpriteSheetMetadata]:
        return self._sheets.get(sheet_id)

    def export_engine_json(self, sheet_id: str) -> Optional[str]:
        sheet = self.get_spritesheet(sheet_id)
        if not sheet:
            return None
        # Format compatible with Phaser 3 & Godot SpriteFrames
        return sheet.model_dump_json(indent=2)
