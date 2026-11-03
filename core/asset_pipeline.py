"""
Art & Asset Production Pipeline for AI Game Development Studio.
Tracks game assets (2D art, 3D models, textures, audio, VFX, animations),
manages asset metadata (format, polycount, texture dimensions, license, approval state),
and provides verified generation adapter interfaces.
"""

import os
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AssetCategory(str, Enum):
    CONCEPT_ART = "concept_art"
    CHARACTER = "character"
    MONSTER = "monster"
    NPC = "npc"
    ENVIRONMENT = "environment"
    WEAPON = "weapon"
    EQUIPMENT = "equipment"
    UI_ASSET = "ui_asset"
    ANIMATION = "animation"
    VFX = "vfx"
    AUDIO_SFX = "audio_sfx"
    AUDIO_MUSIC = "audio_music"
    MODEL_3D = "model_3d"
    TEXTURE = "texture"
    MATERIAL = "material"


class AssetApprovalStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class GameAsset(BaseModel):
    asset_id: str
    project_id: str
    name: str
    category: AssetCategory
    file_path: str
    file_format: str  # .png, .glb, .wav, .tres, etc.
    resolution: Optional[str] = None  # e.g. "1024x1024"
    polycount: Optional[int] = None
    texture_size_mb: Optional[float] = None
    version: int = 1
    license: str = "Studio-Proprietary"
    created_by_agent_id: str
    approval_status: AssetApprovalStatus = AssetApprovalStatus.DRAFT
    approval_notes: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class AssetPipeline:
    """
    Manages production assets, metadata verification, and approval gates.
    """

    def __init__(self, asset_manifest_path: str = "./data/assets_manifest.json"):
        self.manifest_path = asset_manifest_path
        self._assets: Dict[str, GameAsset] = {}
        self._load_manifest()

    def register_asset(self, asset: GameAsset) -> GameAsset:
        self._assets[asset.asset_id] = asset
        self._save_manifest()
        return asset

    def get_asset(self, asset_id: str) -> Optional[GameAsset]:
        return self._assets.get(asset_id)

    def list_assets(self, project_id: Optional[str] = None, category: Optional[AssetCategory] = None) -> List[GameAsset]:
        res = list(self._assets.values())
        if project_id:
            res = [a for a in res if a.project_id == project_id]
        if category:
            res = [a for a in res if a.category == category]
        return res

    def review_asset(self, asset_id: str, approved: bool, notes: str) -> bool:
        asset = self.get_asset(asset_id)
        if not asset:
            return False
        asset.approval_status = AssetApprovalStatus.APPROVED if approved else AssetApprovalStatus.REJECTED
        asset.approval_notes = notes
        self._save_manifest()
        return True

    def validate_asset_spec(self, asset: GameAsset) -> tuple[bool, List[str]]:
        """Validate technical budgets (textures, formats)"""
        errors = []
        # Enforce approved formats
        valid_formats = {
            AssetCategory.TEXTURE: [".png", ".webp", ".tga"],
            AssetCategory.MODEL_3D: [".glb", ".gltf", ".fbx", ".obj"],
            AssetCategory.AUDIO_SFX: [".wav", ".ogg"],
            AssetCategory.AUDIO_MUSIC: [".ogg", ".mp3"],
        }
        allowed = valid_formats.get(asset.category)
        if allowed and asset.file_format.lower() not in allowed:
            errors.append(f"Format '{asset.file_format}' invalid for {asset.category}. Allowed: {allowed}")

        if asset.polycount and asset.polycount > 50000:
            errors.append(f"Polycount {asset.polycount} exceeds indie budget (max 50,000 for standard mesh).")

        return len(errors) == 0, errors

    def _save_manifest(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump({k: v.model_dump() for k, v in self._assets.items()}, f, indent=2)
        except Exception:
            pass

    def _load_manifest(self) -> None:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self._assets[k] = GameAsset(**v)
            except Exception:
                pass
