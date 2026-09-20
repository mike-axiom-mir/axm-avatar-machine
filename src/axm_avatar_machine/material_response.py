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
CHEAP_FOUR = {"surface.breakup", "surface.sheen", "surface.coat", "surface.anisotropy"}
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


def compile_blender_response_binding(
    response: dict[str, Any],
    *,
    renderer: str = "BLENDER_EEVEE_NEXT",
) -> dict[str, Any]:
    """Compile explicit Blender host bindings without transferring donor evidence."""
    if not isinstance(response, dict):
        raise MaterialResponseHold("material response must be an object")
    requested = active_organs(response)
    sockets: dict[str, float] = {}
    colors: dict[str, list[float]] = {}
    vectors: dict[str, list[float]] = {}
    shader_properties: dict[str, str] = {}
    nodes: list[dict[str, Any]] = []
    bound: list[str] = []
    held: list[dict[str, str]] = []
    partial_bindings: list[dict[str, Any]] = []
    fallbacks: list[dict[str, Any]] = []
    approximations: list[str] = []

    if "surface.subsurface" in requested:
        value = response.get("subsurface", {})
        radius_mm = value.get("radius_mm", [1.0, 1.0, 1.0])
        if (
            not isinstance(radius_mm, list)
            or len(radius_mm) != 3
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or float(v) <= 0 for v in radius_mm)
        ):
            raise MaterialResponseHold("subsurface.radius_mm must contain three positive numbers")
        radius_mm = [float(v) for v in radius_mm]
        max_radius_mm = max(radius_mm)
        sockets["Subsurface Weight"] = max(0.0, min(1.0, float(value.get("weight", 0))))
        sockets["Subsurface Scale"] = max_radius_mm / 1000.0
        vectors["Subsurface Radius"] = [round(v / max_radius_mm, 8) for v in radius_mm]
        shader_properties["subsurface_method"] = "BURLEY"

        held_fields = []
        if value.get("tint") is not None:
            held_fields.append("tint")
            held.append({
                "organ": "surface.subsurface",
                "reason": "HOLD_SUBSURFACE_TINT_UNMAPPED_IN_PRINCIPLED_EEVEE",
            })
        partial_bindings.append({
            "organ": "surface.subsurface",
            "bound_fields": ["weight", "radius_mm"],
            "held_fields": held_fields,
            "renderer_method": "BURLEY",
            "scale_m": sockets["Subsurface Scale"],
            "radius_ratio": vectors["Subsurface Radius"],
        })
        if not held_fields:
            bound.append("surface.subsurface")
        approximations.append(
            "EEVEE uses Christensen-Burley subsurface scattering here. Blender documents Random Walk, "
            "subsurface IOR, and subsurface anisotropy as Cycles-only."
        )

    if "surface.sheen" in requested:
        value = response.get("sheen", {})
        sockets["Sheen Weight"] = float(value.get("weight", 0))
        sockets["Sheen Roughness"] = float(value.get("roughness", 0.3))
        if isinstance(value.get("tint"), list) and len(value["tint"]) == 3:
            colors["Sheen Tint"] = [float(v) for v in value["tint"]]
        bound.append("surface.sheen")
        if renderer == "BLENDER_EEVEE_NEXT":
            approximations.append(
                "Blender documents the EEVEE Principled sheen layer as an approximation; "
                "Avatar Machine still requires host pixel evidence."
            )

    if "surface.coat" in requested:
        value = response.get("clearcoat", {})
        sockets["Coat Weight"] = float(value.get("weight", 0))
        sockets["Coat Roughness"] = float(value.get("roughness", 0.05))
        sockets["Coat IOR"] = float(value.get("ior", 1.5))
        if isinstance(value.get("tint"), list) and len(value["tint"]) == 3:
            colors["Coat Tint"] = [float(v) for v in value["tint"]]
        bound.append("surface.coat")

    if "surface.breakup" in requested:
        value = response.get("breakup", {})
        scale_mm = max(0.05, float(value.get("scale_mm", 2)))
        octaves = max(1, min(4, int(value.get("octaves", 2))))
        seed = int(value.get("seed", 7))
        nodes.append({
            "kind": "object-space-noise-breakup",
            "coordinate_space": "OBJECT",
            "noise_dimensions": "4D",
            "scale": round(1000.0 / scale_mm, 8),
            "detail": float(octaves - 1),
            "seed_w": round(((seed % 100000) * 0.61803398875) % 1000.0, 8),
            "roughness_variation": float(value.get("roughness_variation", 0)),
            "color_variation": float(value.get("color_variation", 0)),
            "scale_mm": scale_mm,
        })
        bound.append("surface.breakup")

    if "surface.anisotropy" in requested:
        value = response.get("anisotropy", {})
        direction = value.get("direction", "tangent_u")
        if renderer == "BLENDER_EEVEE_NEXT":
            held.append({
                "organ": "surface.anisotropy",
                "reason": "HOLD_EEVEE_ANISOTROPY_UNSUPPORTED",
            })
            fallbacks.append({
                "organ": "surface.anisotropy",
                "fallback": "directional_roughness",
                "evidence": "declared_contract_match_not_tested",
            })
            nodes.append({
                "kind": "directional-roughness-fallback",
                "direction": direction,
                "rotation": float(value.get("rotation", 0)) % 1.0,
                "strength": abs(float(value.get("strength", 0))),
                "scale": 7.0,
                "stretch": 8.0,
                "roughness_variation": min(0.22, 0.08 + abs(float(value.get("strength", 0))) * 0.12),
            })
            approximations.append(
                "EEVEE 4.3 does not support Principled anisotropy. Avatar Machine uses the donor pack's "
                "declared no-anisotropy fallback: directional roughness variation. The true organ remains HOLD."
            )
        elif direction not in {"tangent_u", "tangent_v"}:
            held.append({
                "organ": "surface.anisotropy",
                "reason": "HOLD_DIRECTION_FIELD_NOT_OWNED",
            })
        else:
            strength = float(value.get("strength", 0))
            rotation = float(value.get("rotation", 0)) % 1.0
            if strength < 0:
                rotation = (rotation + 0.25) % 1.0
            if direction == "tangent_v":
                rotation = (rotation + 0.25) % 1.0
            sockets["Anisotropic IOR Level"] = abs(strength)
            sockets["Anisotropic Rotation"] = rotation
            nodes.append({
                "kind": "radial-object-tangent",
                "direction_type": "RADIAL",
                "axis": "Z",
                "source_direction": direction,
            })
            bound.append("surface.anisotropy")

    for organ in requested:
        if organ in CHEAP_FOUR or organ == "surface.subsurface":
            continue
        held.append({"organ": organ, "reason": "HOLD_ORGAN_NOT_BOUND_IN_BLUEPRINT_BLENDER_V1"})

    status = "PASS_NO_ACTIVE_ORGANS"
    if bound or fallbacks:
        status = "HOLD_RENDER_VERIFICATION_REQUIRED"
    if held:
        status = "HOLD_PARTIAL_BINDING_AND_RENDER_VERIFICATION_REQUIRED"

    return {
        "schema": "axm.avatar.blender-material-response-binding/v0.2",
        "renderer": renderer,
        "requested_organs": requested,
        "bound_organs": sorted(set(bound)),
        "held_organs": held,
        "fallbacks": fallbacks,
        "partial_bindings": partial_bindings,
        "principled_sockets": sockets,
        "principled_colors": colors,
        "principled_vectors": vectors,
        "shader_properties": shader_properties,
        "node_plans": nodes,
        "approximations": approximations,
        "evidence": EVIDENCE,
        "render_verified_organs": [],
        "render_verified_partial_organs": [],
        "render_verified_fallbacks": [],
        "status": status,
        "truth": (
            "Bound means the requested behavior has an explicit renderer construction. "
            "Fallback means the requested organ is still held and a declared approximation is used. "
            "Neither is render evidence until its host probe passes."
        ),
    }
