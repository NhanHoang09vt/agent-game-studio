"""
Character Design Studio for AI Game Development Studio.
Manages Character Identity Profiles, Turnaround sheets (Front, Side, Back, 3/4),
Color palettes, and equipment references.
"""

import os
import json
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from core.art_direction import ArtStyle, CameraPerspective


class CharacterView(str):
    FRONT = "front"
    SIDE = "side"
    BACK = "back"
    THREE_QUARTER = "three_quarter"


class CharacterIdentityProfile(BaseModel):
    character_id: str
    name: str
    race: str = "Human"
    gender: Optional[str] = "Neutral"
    relative_height: float = 1.0  # Multiplier against baseline 48px
    role: str = "Warrior"
    outfit_description: str
    key_visual_traits: List[str]
    color_scheme: Dict[str, str]  # e.g. {"hair": "#e11d48", "armor": "#334155", "cape": "#0284c7"}
    art_style: ArtStyle = ArtStyle.PIXEL_ART_32BIT
    turnaround_views: Dict[str, Optional[str]] = Field(default_factory=lambda: {
        "front": None,
        "side": None,
        "back": None,
        "three_quarter": None,
    })
    equipment_slots: Dict[str, str] = Field(default_factory=lambda: {
        "main_hand": "Plasma Katana",
        "off_hand": "Energy Shield",
        "armor": "Reinforced Nanoweave Coat",
    })
    created_at: float = Field(default_factory=time.time)
    version: int = 1


class CharacterStudio:
    """Manages character profiles, turnaround generation, and character identity consistency"""

    def __init__(self, storage_dir: str = "./data/characters"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._profiles: Dict[str, CharacterIdentityProfile] = {}

    def register_character(self, profile: CharacterIdentityProfile) -> CharacterIdentityProfile:
        self._profiles[profile.character_id] = profile
        fpath = os.path.join(self.storage_dir, f"{profile.character_id}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(profile.model_dump_json(indent=2))
        return profile

    def get_character(self, character_id: str) -> Optional[CharacterIdentityProfile]:
        if character_id in self._profiles:
            return self._profiles[character_id]
        fpath = os.path.join(self.storage_dir, f"{character_id}.json")
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                profile = CharacterIdentityProfile(**data)
                self._profiles[character_id] = profile
                return profile
        return None

    def list_characters(self) -> List[CharacterIdentityProfile]:
        # Scan folder for any saved characters
        for fname in os.listdir(self.storage_dir):
            if fname.endswith(".json"):
                cid = fname.replace(".json", "")
                self.get_character(cid)
        return list(self._profiles.values())
