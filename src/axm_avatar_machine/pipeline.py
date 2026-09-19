from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any
import zipfile

from .benchmark import write_comparison
from .glb import inspect_glb, sha256
from .media import png_dimensions, probe_video
from .paths import machine_root
from .profile import PROFILE_ID, load_profile, profile_directory
from .runtime import resolve_authoring_runtime


OUTPUT_MODES = {"visual", "clip", "3d", "animated-3d"}


class ReferenceInterpretationHold(RuntimeError):
    pass


def load_request(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("request must be a JSON object")
    if value.get("profile") != PROFILE_ID:
        raise ValueError(f"request.profile must be {PROFILE_ID!r}")
    modes = value.get("modes")
    if not isinstance(modes, list) or not modes or any(mode not in OUTPUT_MODES for mode in modes):
        raise ValueError(f"request.modes must be a non-empty list drawn from {sorted(OUTPUT_MODES)}")
    references = value.get("reference_images", [])
    if not isinstance(references, list) or any(not isinstance(item, str) or not item for item in references):
        raise TypeError("reference_images must be a list of paths")
    if references:
        raise ReferenceInterpretationHold(
            "Doll Profile v1 can regenerate the authored Odd Shift design, but no local image-to-design interpreter "
            "was present in the proven source. Arbitrary reference images are HOLD_PLATFORM_MODEL_ASSISTED."
        )
    return {**value, "modes": list(dict.fromkeys(modes)), "reference_images": references}


def _run(command: list[str], stdout_path: Path, stderr_path: Path, timeout: int) -> None:
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.run(command, stdout=stdout, stderr=stderr, check=False, timeout=timeout)
    if completed.returncode:
        raise RuntimeError(f"command failed with exit {completed.returncode}; inspect {stderr_path}")


def _standalone_inspection(output: Path) -> dict[str, Any]:
    glb = inspect_glb(output / "Odd-Shift-Duo.glb")
    poster = output / "Odd-Shift-Duo-Poster.png"
    preview = output / "Odd-Shift-Duo-Preview.mp4"
    result: dict[str, Any] = {
        "schema": "axm.avatar.output-inspection/v1",
        "glb": glb,
        "poster": {
            "path": str(poster),
            "sha256": sha256(poster),
            "dimensions": png_dimensions(poster),
        },
        "blend": {
            "path": str(output / "Odd-Shift-Duo.blend"),
            "sha256": sha256(output / "Odd-Shift-Duo.blend"),
        },
    }
    if preview.is_file():
        result["preview"] = {"path": str(preview), "sha256": sha256(preview), "probe": probe_video(preview)}
    result["status"] = "PASS" if glb["status"] == "PASS" else "FAIL"
    return result


def _write_creator_parts_index(output: Path) -> dict[str, Any]:
    parts = output / "creator-parts"
    state = json.loads((parts / "creation-state.json").read_text(encoding="utf-8"))
    retained = []
    for path in sorted(item for item in parts.rglob("*") if item.is_file() and item.name != "index.json"):
        retained.append({
            "path": str(path.relative_to(output)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    result = {
        "schema": "axm.avatar.creator-parts-index/v1",
        "profile": PROFILE_ID,
        "source_authority": True,
        "realizations_are_secondary": True,
        "retained": retained,
        "counts": {
            "scene_objects": len(state["objects"]),
            "materials": len(state["materials"]),
            "bones": len(state["rig"]["bones"]),
            "animation_channels": len(state["animation"]["channels"]),
            "geometry_atoms": len(state["atom_library"]["geometry_atoms"]),
            "deduplicated_geometry_instances": state["atom_library"]["deduplicated_geometry_instances"],
            "material_family_atoms": len(state["atom_library"]["material_family_atoms"]),
            "source_files": sum(item["path"].startswith("creator-parts/source/") for item in retained),
        },
        "reuse": (
            "Humans and optional AI may edit or replace the retained intent, source parts, materials, "
            "hierarchy and motion. The copied builder remains the deterministic executable authority."
        ),
    }
    (parts / "index.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _package(output: Path, modes: list[str]) -> Path:
    archive = output / "Avatar-Machine-Doll-v1.zip"
    names = {
        "profile.json", "avatar-blueprint.json", "creator-parts.json", "animation_manifest.json", "VISUAL_CONTRACT.md",
        "run-receipt.json", "standalone-inspection.json", "verification.json",
        "verification_report.txt", "build_stats.json", "regression-comparison.json",
    }
    if "visual" in modes:
        names.add("Odd-Shift-Duo-Poster.png")
    if "clip" in modes:
        names.add("Odd-Shift-Duo-Preview.mp4")
    if "3d" in modes or "animated-3d" in modes:
        names.update(("Odd-Shift-Duo.blend", "Odd-Shift-Duo.glb"))
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name in sorted(names):
            path = output / name
            if path.is_file():
                bundle.write(path, name)
        proof = output / "proof"
        if proof.is_dir() and "visual" in modes:
            for path in sorted(proof.glob("*.png")):
                bundle.write(path, f"proof/{path.name}")
        creator_parts = output / "creator-parts"
        for path in sorted(item for item in creator_parts.rglob("*") if item.is_file()):
            bundle.write(path, str(path.relative_to(output)))
    return archive


def run_pipeline(
    request_path: str | Path,
    output_path: str | Path,
    *,
    blender: str | Path | None = None,
    bpy_python: str | Path | None = None,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    request = load_request(request_path)
    root = machine_root()
    output = Path(output_path).resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    logs = output / "logs"
    logs.mkdir()
    runtime = resolve_authoring_runtime(blender, bpy_python)
    profile = load_profile()
    profile_dir = profile_directory()
    shutil.copyfile(profile_dir / "profile.json", output / "profile.json")
    shutil.copyfile(profile_dir / "avatar-blueprint.json", output / "avatar-blueprint.json")
    shutil.copyfile(profile_dir / "creator-parts.json", output / "creator-parts.json")
    shutil.copyfile(profile_dir / "animation_manifest.json", output / "animation_manifest.json")
    shutil.copyfile(profile_dir / "VISUAL_CONTRACT.md", output / "VISUAL_CONTRACT.md")

    executable = runtime["executable"]
    builder = root / profile["scripts"]["build"]
    renderer = root / profile["scripts"]["render"]
    verifier = root / profile["scripts"]["verify"]
    parts = output / "creator-parts"
    source_parts = parts / "source"
    profile_parts = parts / "profile"
    source_parts.mkdir(parents=True)
    profile_parts.mkdir()
    for path in (builder, renderer, verifier):
        shutil.copyfile(path, source_parts / path.name)
    for path in sorted(profile_dir.iterdir()):
        if path.is_file():
            shutil.copyfile(path, profile_parts / path.name)
    shutil.copyfile(Path(request_path).resolve(), parts / "request.json")
    started = time.time()
    if runtime["kind"] == "blender-cli":
        build_command = [
            executable, "--background", "--factory-startup", "--python-exit-code", "1",
            "--python", str(builder), "--", "--output", str(output), "--poster-frame", "92",
        ]
    else:
        build_command = [executable, str(builder), "--output", str(output), "--poster-frame", "92"]
    _run(build_command, logs / "build.stdout.txt", logs / "build.stderr.txt", timeout_seconds)
    creator_parts = _write_creator_parts_index(output)

    proof = output / "proof"
    proof.mkdir()
    if runtime["kind"] == "blender-cli":
        frame_command = [
            executable, "--background", str(output / "Odd-Shift-Duo.blend"), "--python-exit-code", "1",
            "--python", str(renderer), "--", "--output", str(proof), "--frames", "17,53,92,124",
            "--width", "640", "--height", "640", "--samples", "16",
        ]
    else:
        frame_command = [
            executable, str(renderer), "--blend", str(output / "Odd-Shift-Duo.blend"),
            "--output", str(proof), "--frames", "17,53,92,124",
            "--width", "640", "--height", "640", "--samples", "16",
        ]
    _run(frame_command, logs / "frames.stdout.txt", logs / "frames.stderr.txt", timeout_seconds)

    if "clip" in request["modes"]:
        if runtime["kind"] == "blender-cli":
            clip_command = [
                executable, "--background", str(output / "Odd-Shift-Duo.blend"), "--python-exit-code", "1",
                "--python", str(renderer), "--", "--output", str(output), "--animation",
                "--width", "640", "--height", "640", "--samples", "16", "--step", "2",
            ]
        else:
            clip_command = [
                executable, str(renderer), "--blend", str(output / "Odd-Shift-Duo.blend"),
                "--output", str(output), "--animation", "--width", "640", "--height", "640",
                "--samples", "16", "--step", "2",
            ]
        _run(clip_command, logs / "clip.stdout.txt", logs / "clip.stderr.txt", timeout_seconds)
        if runtime["kind"] == "blender-cli":
            verify_command = [
                executable, "--background", str(output / "Odd-Shift-Duo.blend"), "--python-exit-code", "1",
                "--python", str(verifier), "--", "--output", str(output),
            ]
        else:
            verify_command = [
                executable, str(verifier), "--blend", str(output / "Odd-Shift-Duo.blend"),
                "--output", str(output),
            ]
        _run(verify_command, logs / "verify.stdout.txt", logs / "verify.stderr.txt", timeout_seconds)

    inspection = _standalone_inspection(output)
    (output / "standalone-inspection.json").write_text(
        json.dumps(inspection, indent=2) + "\n", encoding="utf-8"
    )
    historical = root / "fixtures" / "odd-shift-duo" / "historical"
    regression = None
    if historical.is_dir() and (output / "Odd-Shift-Duo-Preview.mp4").is_file():
        regression = write_comparison(historical, output, output / "regression-comparison.json")

    receipt = {
        "schema": "axm.avatar.run-receipt/v1",
        "profile": PROFILE_ID,
        "modes": request["modes"],
        "reference_interpretation": "PREAUTHORED_PROFILE; arbitrary reference interpretation held",
        "runtime": runtime,
        "scripts": {
            name: {"path": str(path.relative_to(root)), "sha256": sha256(path)}
            for name, path in {"build": builder, "render": renderer, "verify": verifier}.items()
        },
        "inspection_status": inspection["status"],
        "creator_parts": creator_parts["counts"],
        "regression_status": regression["status"] if regression else "NOT_RUN",
        "elapsed_seconds": round(time.time() - started, 3),
        "uc_runtime_dependency": False,
        "status": "PASS"
        if inspection["status"] == "PASS" and (not regression or regression["status"] == "PASS")
        else "FAIL",
    }
    (output / "run-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    archive = _package(output, request["modes"])
    receipt["package"] = {"path": str(archive), "sha256": sha256(archive)}
    (output / "run-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt
