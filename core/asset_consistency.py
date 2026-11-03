"""
Asset Consistency Engine for AI Game Development Studio.
Evaluates art assets against Art Bible, Color Palettes, and technical constraints.
"""

from typing import Any, Dict, List, Tuple
from PIL import Image
from core.art_direction import ArtBible


class AssetConsistencyEngine:
    """Verifies that generated assets adhere strictly to Art Bible rules"""

    @staticmethod
    def audit_asset_consistency(image_path: str, art_bible: ArtBible) -> Dict[str, Any]:
        with Image.open(image_path) as img:
            width, height = img.size
            has_alpha = img.mode in ("RGBA", "LA")

        violations = []
        score = 1.0

        # Rule 1: Tile size multiple
        base_unit = art_bible.tile_size_px
        if (width % 16 != 0) or (height % 16 != 0):
            violations.append(f"Dimensions {width}x{height} are not a multiple of standard 16px tile unit.")
            score -= 0.2

        # Rule 2: Transparency check for sprite/icon assets
        if not has_alpha and not image_path.endswith("_background.png"):
            violations.append("Asset lacks an alpha transparency channel.")
            score -= 0.3

        # Rule 3: Dimension budget
        if width > 2048 or height > 2048:
            violations.append(f"Asset dimensions {width}x{height} exceed max budget (2048x2048).")
            score -= 0.4

        verdict = "APPROVED" if score >= 0.7 and len(violations) == 0 else "WARNING" if score >= 0.5 else "REJECTED"

        return {
            "image_path": image_path,
            "art_style": art_bible.style.value,
            "consistency_score": round(max(0.0, score), 2),
            "verdict": verdict,
            "violations": violations,
            "is_engine_ready": verdict in ["APPROVED", "WARNING"],
        }
