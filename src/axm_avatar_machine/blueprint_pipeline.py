from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any

from .blueprint import compile_blueprint, load_blueprint
from .glb import inspect_glb, sha256
from .paths import machine_root
from .runtime import resolve_authoring_runtime


def _run(command: list[str], stdout_path: Path, stderr_path: Path, timeout: int) -> None:
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.run(command, stdout=stdout, stderr=stderr, check=False, timeout=timeout)
    if completed.returncode:
        raise RuntimeError(f"command failed with exit {completed.returncode}; inspect {stderr_path}")


def build_blueprint(
    blueprint_path: str | Path,
    output_path: str | Path,
    *,
    blender: str | Path | None = None,
    bpy_python: str | Path | None = None,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    blueprint_path = Path(blueprint_path).resolve()
    blueprint = load_blueprint(blueprint_path)
    plan = compile_blueprint(blueprint)
    output = Path(output_path).resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    logs = output / "logs"
    logs.mkdir()

    (output / "avatar-blueprint.json").write_text(json.dumps(blueprint, indent=2) + "\n", encoding="utf-8")
    (output / "scene-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    root = machine_root()
    builder = root / "blender" / "build_blueprint_v1.py"
    runtime = resolve_authoring_runtime(blender, bpy_python)
    executable = runtime["executable"]

    parts = output / "creator-parts"
    source = parts / "source"
    source.mkdir(parents=True)
    shutil.copyfile(blueprint_path, parts / "request-blueprint.json")
    shutil.copyfile(builder, source / builder.name)
    shutil.copyfile(root / "src" / "axm_avatar_machine" / "blueprint.py", source / "blueprint_compiler.py")
    shutil.copyfile(output / "scene-plan.json", parts / "scene-plan.json")

    if runtime["kind"] == "blender-cli":
        command = [
            executable, "--background", "--factory-startup", "--python-exit-code", "1",
            "--python", str(builder), "--", "--plan", str(output / "scene-plan.json"), "--output", str(output),
        ]
    else:
        command = [
            executable, str(builder), "--plan", str(output / "scene-plan.json"), "--output", str(output),
        ]

    started = time.time()
    _run(command, logs / "build.stdout.txt", logs / "build.stderr.txt", timeout_seconds)
    inspection = inspect_glb(output / "Blueprint-Avatar.glb")
    (output / "structural-inspection.json").write_text(
        json.dumps(inspection, indent=2) + "\n", encoding="utf-8"
    )
    builder_receipt = json.loads((output / "build-receipt.json").read_text(encoding="utf-8"))
    material_response = builder_receipt.get(
        "material_response", {"status": "PASS_NO_ACTIVE_ORGANS", "active_organs": []}
    )
    receipt = {
        "schema": "axm.avatar.blueprint-run-receipt/v1",
        "blueprint_schema": blueprint["schema"],
        "blueprint_id": blueprint["id"],
        "plan_sha256": plan["plan_sha256"],
        "geometry_signature": plan["geometry_signature"],
        "behavior_signature": plan["behavior_signature"],
        "appearance_signature": plan["appearance_signature"],
        "runtime": runtime,
        "builder": {"path": "blender/build_blueprint_v1.py", "sha256": sha256(builder)},
        "structural_status": inspection["status"],
        "deformation": inspection["deformation"],
        "creator_parts_retained": True,
        "reference_interpretation_dependency": False,
        "aesthetic_acceptance": "NOT_PERFORMED",
        "material_response": material_response,
        "elapsed_seconds": round(time.time() - started, 3),
        "status": (
            "FAIL" if inspection["status"] != "PASS"
            else "HOLD" if material_response.get("status", "").startswith("HOLD_")
            else "PASS"
        ),
        "truth": (
            "PASS means the bounded blueprint compiled and the exported GLB decoded structurally. "
            "HOLD means structural output exists but requested material-response organ behavior is not yet "
            "bound/verified in the generic Blender host. Neither state is automatic aesthetic or likeness acceptance."
        ),
        "builder_receipt": builder_receipt,
    }
    (output / "blueprint-run-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt
