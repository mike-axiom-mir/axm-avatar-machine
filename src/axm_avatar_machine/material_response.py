"""Surface-response intent for Avatar Machine.

The user-supplied response pack is explicit material intent. The generic Blender
builder currently projects base scalar values only; organ behavior stays HOLD
until that host earns its own render receipts.
"""
from __future__ import annotations

import copy
import json
from typing import Any

from .paths import machine_root

EVIDENCE = "declared_contract_match_not_tested"
SOURCE_ARCHIVE_SHA256 = "9b263ddd536c7f9aa1b6640ad7672283c0e30e7c2b818a7ee23076aafdd1a363"
SOURCE_PACK_SHA256 = "cc101f7f975e4334570b89d3dacede28e537f6ae09fd11af49d9864a2d064cf5"

BASE_KEYS = {"base_color", "roughness", "metallic", "specular", "ior", "note"}
ORGAN_BY_KEY = {
    "subsurface": "surface.subsurface",
    "sheen": "surface.sheen",
    "anisotropy": "surface.anisotropy",
    "clearcoat": "surface.coat",
    "breakup": "surface.breakup",
    "transmission": "surface.transmission",
    "transmission_tint": "surface.transmission",
    "absorption": "surface.transmission",
    "dispersion": "surface.transmission",
    "iridescence": "surface.iridescence",
    "layers": "surface.wear_layer",
    "flake": "surface.coat",
}


class MaterialResponseHold(ValueError):
    pass


def _load(name: str) -> Any:
    return json.loads((machine_root() / "material-response" / name).read_text(encoding="utf-8"))


def _pack() -> dict[str, Any]:
    value = _load("pack.json")
    if not isinstance(value, dict) or value.get("format") != "axm-material-response-pack":
        raise MaterialResponseHold("invalid material-response pack")
    return value


def _organs() -> dict[str, dict[str, Any]]:
    values = _load("organs.json")
    if not isinstance(values, list):
        raise MaterialResponseHold("material-response organ data must be a list")
    result = {}
    for value in values:
        organ_id = value.get("id") if isinstance(value, dict) else None
        if not isinstance(organ_id, str) or organ_id in result:
            raise MaterialResponseHold("invalid or duplicate material-response organ id")
        result[organ_id] = value
    return result


def _active(value: Any, key: str, response: dict[str, Any]) -> bool:
    if key == "transmission":
        weight = value.get("weight", 0) if isinstance(value, dict) else value
        return isinstance(weight, (int, float)) and not isinstance(weight, bool) and abs(float(weight)) > 1e-12
    if key in {"transmission_tint", "absorption", "dispersion"}:
        return _active(response.get("transmission", 0), "transmission", response)
    if key == "layers":
        return isinstance(value, list) and any(
            isinstance(layer, dict) and float(layer.get("weight", 1) or 0) > 1e-12 for layer in value
        )
    if key == "anisotropy":
        return isinstance(value, dict) and abs(float(value.get("strength", 0) or 0)) > 1e-12
    if key == "breakup":
        if not isinstance(value, dict):
            return False
        return any(
            isinstance(v, (int, float)) and not isinstance(v, bool) and abs(float(v)) > 1e-12
            for k, v in value.items() if k not in {"scale_mm", "octaves"}
        )
    if key in {"subsurface", "sheen", "clearcoat", "iridescence", "flake"}:
        return isinstance(value, dict) and float(value.get("weight", 0) or 0) > 1e-12
    return value is not None


def active_organs(response: dict[str, Any]) -> list[str]:
    records = _organs()
    active = set()
    for key, value in response.items():
        if key in BASE_KEYS:
            continue
        organ_id = ORGAN_BY_KEY.get(key)
        if organ_id is None:
            raise MaterialResponseHold(f"unknown material-response key: {key}")
        if organ_id not in records:
            raise MaterialResponseHold(f"missing material-response organ record: {organ_id}")
        if _active(value, key, response):
            active.add(organ_id)
    return sorted(active)


def _deep_merge(base: Any, patch: Any) -> Any:
    if isinstance(base, dict) and isinstance(patch, dict):
        result = copy.deepcopy(base)
        for key, value in patch.items():
            result[key] = _deep_merge(result[key], value) if key in result else copy.deepcopy(value)
        return result
    return copy.deepcopy(patch)


def _hex_rgb(value: str) -> list[float]:
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        raise MaterialResponseHold("material color must be #RRGGBB")
    return [round(int(value[i:i+2], 16) / 255.0, 8) for i in (1, 3, 5)]


def validate_surface_selection(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        value = {"family": value}
    if not isinstance(value, dict) or set(value) - {"family", "variant", "overrides"}:
        raise MaterialResponseHold("surface selection accepts family, optional variant and overrides")
    family = value.get("family")
    if not isinstance(family, str) or not family:
        raise MaterialResponseHold("surface selection family must be a non-empty string")
    resolve_material_response(family, variant=value.get("variant"), overrides=value.get("overrides"))
    result = {"family": family}
    if value.get("variant") is not None:
        result["variant"] = value["variant"]
    if value.get("overrides") is not None:
        result["overrides"] = copy.deepcopy(value["overrides"])
    return result


def resolve_material_response(
    family: str,
    *,
    variant: str | None = None,
    overrides: dict[str, Any] | None = None,
    color_hex: str | None = None,
) -> dict[str, Any]:
    pack = _pack()
    matches = [item for item in pack.get("families", []) if item.get("id") == family]
    if len(matches) != 1:
        raise MaterialResponseHold(f"unknown material-response family: {family}")
    item = matches[0]
    response = copy.deepcopy(item["response"])
    if variant is not None:
        variants = item.get("variants", {})
        if variant not in variants:
            raise MaterialResponseHold(f"unknown {family} variant: {variant}")
        response = _deep_merge(response, variants[variant])
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise MaterialResponseHold("material-response overrides must be an object")
        response = _deep_merge(response, overrides)
    if color_hex is not None:
        response["base_color"] = _hex_rgb(color_hex)
    organs = active_organs(response)
    return {
        "schema": "axm.avatar.material-response/v0.1",
        "family": family,
        "variant": variant,
        "purpose": item.get("purpose"),
        "response": response,
        "active_organs": organs,
        "evidence": EVIDENCE,
        "renderer_binding": "HOLD_BLUEPRINT_BLENDER_ORGANS_NOT_BOUND" if organs else "PASS_NO_ACTIVE_ORGANS",
        "truth": (
            "Avatar palette/base channels remain authoritative. Response organs describe additional "
            "surface behavior; the generic Blender host has not yet earned organ render receipts."
        ),
    }


def resolve_surface_selection(selection: dict[str, Any], color_hex: str) -> dict[str, Any]:
    return resolve_material_response(
        selection["family"],
        variant=selection.get("variant"),
        overrides=selection.get("overrides"),
        color_hex=color_hex,
    )


def material_response_catalog() -> dict[str, Any]:
    pack = _pack()
    organs = _organs()
    return {
        "schema": "axm.avatar.material-response-catalog/v0.1",
        "families": [
            {"id": item["id"], "purpose": item.get("purpose"), "variants": sorted(item.get("variants", {}))}
            for item in pack.get("families", [])
        ],
        "organs": [
            {"id": item["id"], "name": item.get("name"), "evidence": item.get("evidence")}
            for item in sorted(organs.values(), key=lambda row: row["id"])
        ],
        "counts": {"families": len(pack.get("families", [])), "organs": len(organs)},
        "renderer_binding": "NOT_CLAIMED",
        "source": {
            "archive_sha256": SOURCE_ARCHIVE_SHA256,
            "declared_source_pack_sha256": SOURCE_PACK_SHA256,
        },
    }
