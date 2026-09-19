from __future__ import annotations

import json
from pathlib import Path
import shutil
import struct
import subprocess
from typing import Any


def png_dimensions(path: str | Path) -> tuple[int, int]:
    raw = Path(path).read_bytes()[:24]
    if len(raw) != 24 or raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
        raise ValueError("not a PNG with an IHDR header")
    return struct.unpack(">II", raw[16:24])


def probe_video(path: str | Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise FileNotFoundError("ffprobe is required for video verification")
    completed = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames",
            "-of", "json",
            str(Path(path).resolve()),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(completed.stdout)
