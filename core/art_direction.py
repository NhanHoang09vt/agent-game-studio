"""
Art Direction & Art Bible Management System for AI Game Development Studio.
Defines visual identity, color palettes, lighting rules, camera perspectives,
proportion bibles, and consistency validation standards.
"""

import os
import json
import yaml
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ArtStyle(str, Enum):
    PIXEL_ART_16BIT = "pixel_art_16bit"
    PIXEL_ART_32BIT = "pixel_art_32bit"
    STYLIZED_25D = "stylized_2.5d"
    HAND_DRAWN_VECTOR = "hand_drawn_vector"
    DARK_FANTASY = "dark_fantasy"
    CYBERPUNK_NEO_RETRO = "cyberpunk_neo_retro"
    ANIME_CEL_SHADED = "anime_cel_shaded"


class CameraPerspective(str, Enum):
    TOP_DOWN = "top_down"
    ISOMETRIC_25D = "isometric_2.5d"
    SIDE_SCROLLER_2D = "side_scroller_2d"
    THIRD_PERSON_3D = "third_person_3d"


class ColorPalette(BaseModel):
    name: str
    primary: str  # Hex e.g. "#1e1b4b"
    secondary: str  # Hex e.g. "#38bdf8"
    accent: str  # Hex e.g. "#f43f5e"
    background: str  # Hex e.g. "#090d16"
    surface: str  # Hex e.g. "#1e293b"
    text: str  # Hex e.g. "#f8fafc"
    neutrals: List[str] = Field(default_factory=lambda: ["#0f172a", "#334155", "#64748b", "#94a3b8"])


class ArtBible(BaseModel):
    project_id: str
    style: ArtStyle = ArtStyle.PIXEL_ART_32BIT
    camera: CameraPerspective = CameraPerspective.TOP_DOWN
    resolution_reference: str = "1920x1080"
    tile_size_px: int = 32
    character_height_px: int = 48
    palette: ColorPalette
    lighting_model: str = "High contrast dynamic lighting with saturated rim lights"
    silhouette_rule: str = "Strong, readable geometric shapes with minimum 20% contrast from background"
    outline_rule: str = "1px dark colored outline matching material shadow (never pure #000000)"
    material_standards: Dict[str, str] = Field(default_factory=lambda: {
        "metal": "High specularity, sharp 2-step highlights",
        "cloth": "Matte shading, warm ambient bounce",
        "energy": "Additive glow, bloom radius 4px",
    })
    approved_by: str = "art-director"
    version: int = 1
    updated_at: float = Field(default_factory=time.time)


class ArtDirectionManager:
    """Manages Art Bibles across game projects and verifies assets against style standards"""

    def __init__(self, storage_dir: str = "./data/art_bibles"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._bibles: Dict[str, ArtBible] = {}

    def create_or_update_bible(self, bible: ArtBible) -> ArtBible:
        self._bibles[bible.project_id] = bible
        fpath = os.path.join(self.storage_dir, f"{bible.project_id}_art_bible.json")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(bible.model_dump_json(indent=2))
        return bible

    def get_bible(self, project_id: str) -> ArtBible:
        if project_id in self._bibles:
            return self._bibles[project_id]

        fpath = os.path.join(self.storage_dir, f"{project_id}_art_bible.json")
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                bible = ArtBible(**data)
                self._bibles[project_id] = bible
                return bible

        # Default fallback Art Bible (Retro Cyberpunk Fantasy)
        default_bible = ArtBible(
            project_id=project_id,
            style=ArtStyle.PIXEL_ART_32BIT,
            camera=CameraPerspective.TOP_DOWN,
            tile_size_px=32,
            character_height_px=48,
            palette=ColorPalette(
                name="CyberNeon Fantasy",
                primary="#065f46",
                secondary="#0284c7",
                accent="#f43f5e",
                background="#090d16",
                surface="#1e293b",
                text="#f1f5f9",
            ),
        )
        self.create_or_update_bible(default_bible)
        return default_bible
