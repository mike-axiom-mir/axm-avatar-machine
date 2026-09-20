from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .blueprint import BLUEPRINT_SCHEMA, compile_blueprint, validate_blueprint

REFERENCE_PACKET_SCHEMA = "axm.avatar.reference-packet/v1"
INTERPRETATION_RESPONSE_SCHEMA = "axm.avatar.interpretation-response/v1"
INTERPRETATION_RECEIPT_SCHEMA = "axm.avatar.interpretation-receipt/v1"
INTERPRETATION_METHODS = {"HUMAN_AUTHORED", "EXTERNAL_MODEL", "LOCAL_VISION_MODEL"}


class InterpretationHold(RuntimeError):
    pass


class InterpretationError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_reference_packet(image_paths: list[str | Path]) -> dict[str, Any]:
    if not image_paths:
        raise InterpretationError("at least one reference image path is required")
    references = []
    for raw in image_paths:
        path = Path(raw).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        references.append({
            "name": path.name,
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
            "suffix": path.suffix.lower(),
        })
    return {
        "schema": REFERENCE_PACKET_SCHEMA,
        "references": references,
        "requested_output_schema": BLUEPRINT_SCHEMA,
        "required_decisions": [
            "style.material_finish",
            "character proportions",
            "palette",
            "bounded hair/facial-hair/eyes/mouth choices",
            "bounded wardrobe choices",
            "character placement",
            "animation beats",
        ],
        "truth": (
            "Avatar Machine hashes and packages the references but does not infer likeness or design semantics here. "
            "A human or explicitly configured replaceable interpreter must author the blueprint fields."
        ),
    }


def write_reference_packet(image_paths: list[str | Path], output_dir: str | Path) -> dict[str, Any]:
    packet = create_reference_packet(image_paths)
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    references_dir = output / "references"
    references_dir.mkdir(parents=True)
    for index, (raw, record) in enumerate(zip(image_paths, packet["references"], strict=True)):
        source = Path(raw).resolve()
        safe_name = f"{index:03d}-{source.name}"
        target = references_dir / safe_name
        shutil.copyfile(source, target)
        record["path"] = f"references/{safe_name}"
    packet["portable_reference_bytes"] = True
    (output / "reference-packet.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return packet


def load_reference_packet(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != REFERENCE_PACKET_SCHEMA:
        raise InterpretationError(f"reference packet schema must be {REFERENCE_PACKET_SCHEMA!r}")
    refs = value.get("references")
    if not isinstance(refs, list) or not refs:
        raise InterpretationError("reference packet must contain references")
    return value


def _validate_response(packet: dict[str, Any], value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, dict) or value.get("schema") != INTERPRETATION_RESPONSE_SCHEMA:
        raise InterpretationError(f"response.schema must be {INTERPRETATION_RESPONSE_SCHEMA!r}")
    method = value.get("method")
    if method not in INTERPRETATION_METHODS:
        raise InterpretationError(f"response.method must be one of {sorted(INTERPRETATION_METHODS)}")
    provider = value.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        raise InterpretationError("response.provider must name the human or interpreter that authored the decisions")
    expected = [item["sha256"] for item in packet["references"]]
    supplied = value.get("reference_sha256")
    if supplied != expected:
        raise InterpretationError("interpretation response reference_sha256 does not match the packet")
    blueprint = validate_blueprint(value.get("blueprint"))
    receipt = {
        "schema": INTERPRETATION_RECEIPT_SCHEMA,
        "method": method,
        "provider": provider.strip(),
        "reference_sha256": expected,
        "automatic_local_photo_interpretation": False,
        "replaceable_interpreter": method != "HUMAN_AUTHORED",
        "blueprint_plan_sha256": compile_blueprint(blueprint)["plan_sha256"],
        "truth": (
            "The blueprint decisions came from the named provider. Avatar Machine validated the explicit fields; "
            "it did not independently infer likeness from the reference pixels."
        ),
    }
    return blueprint, receipt


def _run_adapter(packet_path: Path, adapter: str | Path, timeout_seconds: int) -> dict[str, Any]:
    adapter_path = Path(adapter).resolve()
    if not adapter_path.is_file():
        raise FileNotFoundError(adapter_path)
    with tempfile.TemporaryDirectory(prefix="axm-avatar-interpreter-") as directory:
        response_path = Path(directory) / "response.json"
        command = [str(adapter_path), "--packet", str(packet_path.resolve()), "--output", str(response_path)]
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout_seconds)
        if completed.returncode:
            raise RuntimeError(
                f"interpreter adapter exited {completed.returncode}: {completed.stderr.strip() or completed.stdout.strip()}"
            )
        if not response_path.is_file():
            raise RuntimeError("interpreter adapter did not create the required response file")
        return json.loads(response_path.read_text(encoding="utf-8"))


def resolve_interpretation(
    packet_path: str | Path,
    output_dir: str | Path,
    *,
    response_path: str | Path | None = None,
    adapter: str | Path | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    if (response_path is None) == (adapter is None):
        if response_path is None:
            raise InterpretationHold(
                "Reference images are present, but no human interpretation response or optional interpreter adapter "
                "was supplied. Automatic local photo-to-avatar interpretation is not implemented."
            )
        raise InterpretationError("choose exactly one of response_path or adapter")
    packet_path = Path(packet_path)
    packet = load_reference_packet(packet_path)
    if response_path is not None:
        response = json.loads(Path(response_path).read_text(encoding="utf-8"))
    else:
        response = _run_adapter(packet_path, adapter, timeout_seconds)

    blueprint, receipt = _validate_response(packet, response)
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    (output / "reference-packet.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    (output / "avatar-blueprint.json").write_text(json.dumps(blueprint, indent=2) + "\n", encoding="utf-8")
    (output / "interpretation-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt
