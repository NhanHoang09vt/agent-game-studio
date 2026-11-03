"""
UI & Icon Asset Studio for AI Game Development Studio.
Produces consistent HUD panels, skill icons, inventory frames, health bars,
and transparent PNG icons with uniform bevels and lighting.
"""

import os
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UIIconType(str, Enum):
    SKILL = "skill"
    ITEM = "item"
    EQUIPMENT = "equipment"
    STATUS_EFFECT = "status_effect"
    CURRENCY = "currency"


class UIIconSpec(BaseModel):
    icon_id: str
    name: str
    icon_type: UIIconType
    dimensions: int = 32  # 16, 32, 64
    border_style: str = "golden_metallic_bevel"
    background_color: str = "#0f172a"
    has_transparent_bg: bool = True
    file_path: str
    created_at: float = Field(default_factory=time.time)


class UIThemeSpec(BaseModel):
    theme_id: str
    name: str
    hud_panel_corner_radius: int = 8
    border_thickness_px: int = 2
    primary_frame_color: str = "#1e293b"
    accent_frame_color: str = "#38bdf8"
    hp_bar_fill: str = "#ef4444"
    mana_bar_fill: str = "#3b82f6"
    stamina_bar_fill: str = "#10b981"
    exp_bar_fill: str = "#eab308"


class UIStudio:
    """Manages UI themes, HUD layouts, and game icon libraries"""

    def __init__(self, storage_dir: str = "./data/ui"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._icons: Dict[str, UIIconSpec] = {}
        self._themes: Dict[str, UIThemeSpec] = {}

    def register_icon(self, icon: UIIconSpec) -> UIIconSpec:
        self._icons[icon.icon_id] = icon
        return icon

    def get_icon(self, icon_id: str) -> Optional[UIIconSpec]:
        return self._icons.get(icon_id)

    def list_icons(self) -> List[UIIconSpec]:
        return list(self._icons.values())
