from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


def resolve_blender(explicit: str | Path | None = None) -> dict[str, str]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    configured = os.environ.get("AXM_AVATAR_BLENDER")
    if configured:
        candidates.append(Path(configured))
    discovered = shutil.which("blender")
    if discovered:
        candidates.append(Path(discovered))

    for candidate in candidates:
        resolved = Path(os.path.abspath(os.fspath(candidate.expanduser())))
        if not resolved.is_file():
            continue
        checked = subprocess.run(
            [str(resolved), "--version"], capture_output=True, text=True, check=False, timeout=30
        )
        if checked.returncode == 0:
            first = (checked.stdout or checked.stderr).splitlines()[0].strip()
            return {"executable": str(resolved), "version": first, "kind": "blender-cli", "status": "FOUND"}
    raise FileNotFoundError(
        "Blender was not found. Install Blender 4.x, pass --blender, or set AXM_AVATAR_BLENDER."
    )


def resolve_bpy_python(explicit: str | Path | None = None) -> dict[str, str]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    configured = os.environ.get("AXM_AVATAR_BPY_PYTHON")
    if configured:
        candidates.append(Path(configured))
    candidates.append(Path(sys.executable))
    for candidate in candidates:
        # Keep a virtual-environment launcher path intact. Resolving its symlink
        # would bypass the environment's site-packages, including bpy.
        resolved = Path(os.path.abspath(os.fspath(candidate.expanduser())))
        if not resolved.is_file():
            continue
        checked = subprocess.run(
            [str(resolved), "-c", "import bpy; print(bpy.app.version_string)"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if checked.returncode == 0:
            version = checked.stdout.strip().splitlines()[-1]
            return {
                "executable": str(resolved),
                "version": f"bpy {version}",
                "kind": "bpy-python",
                "status": "FOUND",
            }
    raise FileNotFoundError(
        "A Python runtime with bpy was not found. Pass --bpy-python or set AXM_AVATAR_BPY_PYTHON."
    )


def resolve_authoring_runtime(
    blender: str | Path | None = None,
    bpy_python: str | Path | None = None,
) -> dict[str, str]:
    if blender and bpy_python:
        raise ValueError("select either --blender or --bpy-python, not both")
    if blender:
        return resolve_blender(blender)
    if bpy_python:
        return resolve_bpy_python(bpy_python)
    try:
        return resolve_blender()
    except FileNotFoundError:
        return resolve_bpy_python()
