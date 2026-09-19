from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from typing import Any


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_glb_document(path: str | Path) -> tuple[bytes, dict[str, Any]]:
    target = Path(path)
    raw = target.read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB is shorter than its header and JSON chunk")
    magic, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(raw):
        raise ValueError("not a complete GLB v2 container")
    json_length, json_type = struct.unpack_from("<I4s", raw, 12)
    if json_type != b"JSON" or 20 + json_length > len(raw):
        raise ValueError("GLB does not contain a valid leading JSON chunk")
    document = json.loads(raw[20:20 + json_length].decode("utf-8").rstrip(" \t\r\n\0"))
    return raw, document


def inspect_glb(path: str | Path) -> dict[str, Any]:
    target = Path(path).resolve()
    raw, doc = read_glb_document(target)
    nodes = doc.get("nodes", [])
    meshes = doc.get("meshes", [])
    materials = doc.get("materials", [])
    skins = doc.get("skins", [])
    animations = doc.get("animations", [])
    primitives = [primitive for mesh in meshes for primitive in mesh.get("primitives", [])]
    mesh_nodes = [node for node in nodes if isinstance(node.get("mesh"), int)]
    skin_bindings = [node for node in nodes if isinstance(node.get("skin"), int)]
    joint_indices = [joint for skin in skins for joint in skin.get("joints", [])]
    channels = [channel for animation in animations for channel in animation.get("channels", [])]

    checks = {
        "node_mesh_indices_valid": all(node["mesh"] < len(meshes) for node in mesh_nodes),
        "node_skin_indices_valid": all(node["skin"] < len(skins) for node in skin_bindings),
        "joint_indices_valid": all(isinstance(index, int) and index < len(nodes) for index in joint_indices),
        "animation_targets_valid": all(
            isinstance(channel.get("target", {}).get("node"), int)
            and channel["target"]["node"] < len(nodes)
            for channel in channels
        ),
        "animation_samplers_valid": all(
            isinstance(channel.get("sampler"), int)
            and channel["sampler"] < len(animation.get("samplers", []))
            for animation in animations
            for channel in animation.get("channels", [])
        ),
        "primitive_material_indices_valid": all(
            "material" not in primitive or primitive["material"] < len(materials)
            for primitive in primitives
        ),
    }
    return {
        "schema": "axm.avatar.glb-inspection/v1",
        "path": str(target),
        "sha256": sha256(target),
        "bytes": len(raw),
        "asset": doc.get("asset", {}),
        "metrics": {
            "nodes": len(nodes),
            "meshes": len(meshes),
            "mesh_nodes": len(mesh_nodes),
            "primitives": len(primitives),
            "materials": len(materials),
            "skins": len(skins),
            "joints": len(joint_indices),
            "skin_bindings": len(skin_bindings),
            "animations": len(animations),
            "animation_channels": len(channels),
        },
        "animation_names": [animation.get("name") for animation in animations],
        "deformation": {
            "model": "SKINNED_MESH" if skin_bindings else "RIGID_BONE_PARENTING",
            "skinned_mesh_deformation": bool(skin_bindings),
            "note": (
                "Mesh nodes reference a glTF skin."
                if skin_bindings
                else "No mesh node references the retained skin; meshes animate as rigid children of joints."
            ),
        },
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "truth": "Decoded structure does not prove rendered appearance, deformation quality, or engine integration.",
    }
