from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .glb import inspect_glb
from .media import png_dimensions, probe_video


def _poster_difference(left: Path, right: Path) -> dict[str, Any]:
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:
        return {"status": "NOT_MEASURED", "reason": "install the visual-regression extra for Pillow"}
    with Image.open(left).convert("RGB") as a, Image.open(right).convert("RGB") as b:
        if a.size != b.size:
            return {"status": "SIZE_MISMATCH", "historical": a.size, "generated": b.size}
        difference = ImageChops.difference(a, b)
        mean = sum(ImageStat.Stat(difference).mean) / 3.0
        return {"status": "MEASURED", "mean_absolute_channel_difference": mean, "identical": mean == 0}


def compare_outputs(historical: str | Path, generated: str | Path) -> dict[str, Any]:
    old, new = Path(historical).resolve(), Path(generated).resolve()
    old_glb = inspect_glb(old / "Odd-Shift-Duo.glb")
    new_glb = inspect_glb(new / "Odd-Shift-Duo.glb")
    keys = ("meshes", "materials", "skins", "joints", "animations", "animation_channels")
    structure = {
        key: {"historical": old_glb["metrics"][key], "generated": new_glb["metrics"][key]}
        for key in keys
    }
    structural_equivalent = all(row["historical"] == row["generated"] for row in structure.values())
    old_poster, new_poster = old / "Odd-Shift-Duo-Poster.png", new / "Odd-Shift-Duo-Poster.png"
    old_video, new_video = old / "Odd-Shift-Duo-Preview.mp4", new / "Odd-Shift-Duo-Preview.mp4"
    video = {"status": "NOT_COMPARED"}
    if old_video.is_file() and new_video.is_file():
        video = {
            "status": "COMPARED",
            "historical": probe_video(old_video),
            "generated": probe_video(new_video),
        }
    return {
        "schema": "axm.avatar.regression/v1",
        "historical": str(old),
        "generated": str(new),
        "structure": structure,
        "structural_equivalent": structural_equivalent,
        "historical_glb_sha256": old_glb["sha256"],
        "generated_glb_sha256": new_glb["sha256"],
        "poster_dimensions": {
            "historical": png_dimensions(old_poster),
            "generated": png_dimensions(new_poster),
        },
        "poster_difference": _poster_difference(old_poster, new_poster),
        "video": video,
        "status": "PASS" if structural_equivalent else "REGRESSION",
        "truth": "Structural equivalence and pixel measurements are separate from human visual acceptance.",
    }


def write_comparison(historical: str | Path, generated: str | Path, destination: str | Path) -> dict[str, Any]:
    result = compare_outputs(historical, generated)
    Path(destination).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
