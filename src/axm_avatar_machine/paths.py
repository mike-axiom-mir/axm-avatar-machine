from __future__ import annotations

import os
from pathlib import Path
import sys


def machine_root() -> Path:
    """Resolve this repository or its installed share directory without UC."""
    configured = os.environ.get("AXM_AVATAR_MACHINE_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
        if (root / "profiles").is_dir() and (root / "blender").is_dir():
            return root
        raise FileNotFoundError(f"AXM_AVATAR_MACHINE_ROOT is not an Avatar Machine root: {root}")

    source_root = Path(__file__).resolve().parents[2]
    candidates = (
        source_root,
        Path.cwd().resolve(),
        Path(sys.prefix).resolve() / "share" / "axm-avatar-machine",
    )
    for root in candidates:
        if (root / "profiles").is_dir() and (root / "blender").is_dir():
            return root
    raise FileNotFoundError(
        "Avatar Machine profiles/scripts were not found. Run from the clone or set AXM_AVATAR_MACHINE_ROOT."
    )

