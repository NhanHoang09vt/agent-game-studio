"""
Automated Asset Processing Pipeline for AI Game Development Studio.
Validates dimensions, verifies alpha transparency, crops borders,
generates thumbnails, packs texture atlases, and performs integrity checks.
"""

import os
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image


class AssetProcessor:
    """Automates post-processing of generated 2D/UI game assets"""

    @staticmethod
    def inspect_image(image_path: str) -> Dict[str, Any]:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File '{image_path}' does not exist.")

        with Image.open(image_path) as img:
            has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
            width, height = img.size
            fmt = img.format or os.path.splitext(image_path)[1].replace(".", "").upper()

            # Hash for deduplication
            with open(image_path, "rb") as f:
                fhash = hashlib.md5(f.read()).hexdigest()

            return {
                "file_path": image_path,
                "width": width,
                "height": height,
                "format": fmt,
                "mode": img.mode,
                "has_transparency": has_alpha,
                "aspect_ratio": round(width / max(1, height), 2),
                "md5_hash": fhash,
                "size_bytes": os.path.getsize(image_path),
            }

    @staticmethod
    def generate_thumbnail(image_path: str, thumb_path: str, size: Tuple[int, int] = (128, 128)) -> str:
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        with Image.open(image_path) as img:
            img.thumbnail(size)
            img.save(thumb_path, "PNG")
        return thumb_path

    @staticmethod
    def ensure_transparent_background(image_path: str, output_path: str, threshold: int = 15) -> str:
        """Converts near-black background to transparent alpha"""
        with Image.open(image_path).convert("RGBA") as img:
            datas = img.getdata()
            new_data = []
            for item in datas:
                # If pixel is near-black, make it transparent
                if item[0] <= threshold and item[1] <= threshold and item[2] <= threshold:
                    new_data.append((0, 0, 0, 0))
                else:
                    new_data.append(item)
            img.putdata(new_data)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path, "PNG")
        return output_path
