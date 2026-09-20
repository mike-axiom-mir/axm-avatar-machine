#!/usr/bin/env python3
"""Earn Blender-host pixel evidence for the first four material-response organs.

This verifier deliberately tests the Avatar Machine Blender binding, not the
Opus/reference-host renderer. PASS is scoped to these EEVEE 4.3 probe scenes and
does not claim physical equivalence, artistic acceptance, or other-host parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from PIL import Image
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from __main__ import make_material, reset_scene
except ImportError:
    from build_blueprint_v1 import make_material, reset_scene  # type: ignore
from axm_avatar_machine.material_response import compile_blender_response_binding  # noqa: E402


ORGAN_IDS = (
    "surface.breakup",
    "surface.sheen",
    "surface.coat",
    "surface.subsurface",
    "surface.anisotropy",
)


def parse_args():
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(tail)


def _look_at(obj, target=(0.0, 0.0, 0.0)):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def _base_spec(name, color, metallic, roughness):
    return {
        "id": name,
        "color": color,
        "metallic": float(metallic),
        "roughness": float(roughness),
    }


def _response_spec(name, color, metallic, roughness, response):
    binding = compile_blender_response_binding(response)
    return {
        **_base_spec(name, color, metallic, roughness),
        "response_family": "blender-verification-probe",
        "active_organs": binding["requested_organs"],
        "blender_response_binding": binding,
        "response_renderer_binding": binding["status"],
    }


def _setup_probe_scene():
    reset_scene()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 96
    scene.render.resolution_y = 96
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True

    world = bpy.data.worlds.get("AXM Material Probe World") or bpy.data.worlds.new("AXM Material Probe World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.025, 0.028, 0.035, 1.0)
    bg.inputs["Strength"].default_value = 0.08

    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, location=(0, 0, 0))
    sphere = bpy.context.object
    sphere.name = "AXM_Material_Response_Probe"
    for polygon in sphere.data.polygons:
        polygon.use_smooth = True

    bpy.ops.object.camera_add(location=(0.0, -4.3, 0.15))
    camera = bpy.context.object
    camera.data.lens = 56
    _look_at(camera)
    scene.camera = camera

    lights = [
        ("AXM Probe Key", (-2.4, -3.2, 2.8), 900.0, 2.7),
        ("AXM Probe Fill", (2.8, -1.0, 1.1), 280.0, 2.2),
        ("AXM Probe Back", (0.0, 2.4, 2.0), 850.0, 2.0),
    ]
    for name, location, energy, size in lights:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        _look_at(light)
    bpy.context.view_layer.update()
    return scene, sphere


def _render_probe(scene, sphere, spec, output_path):
    material, bind_receipt = make_material(spec)
    sphere.data.materials.clear()
    sphere.data.materials.append(material)
    scene.render.filepath = str(output_path)
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    with Image.open(output_path) as image:
        rgba = image.convert("RGBA")
        width, height = rgba.size
        raw = list(rgba.getdata())
    pixels = tuple(channel / 255.0 for pixel in raw for channel in pixel)
    return {
        "width": width,
        "height": height,
        "pixels": pixels,
        "binding": bind_receipt,
        "png_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
    }


def _luma(pixel):
    return 0.2126 * pixel[0] + 0.7152 * pixel[1] + 0.0722 * pixel[2]


def _samples(frame):
    width, height, px = frame["width"], frame["height"], frame["pixels"]
    rows = []
    for index in range(width * height):
        off = index * 4
        if px[off + 3] <= 0.5:
            continue
        x, y = index % width, index // width
        rows.append((x, y, (px[off], px[off + 1], px[off + 2]), _luma(px[off:off + 3])))
    if not rows:
        raise RuntimeError("material probe rendered no visible sphere pixels")
    return rows


def _mean_abs_delta(a, b):
    if (a["width"], a["height"]) != (b["width"], b["height"]):
        raise ValueError("render dimensions differ")
    pa, pb = a["pixels"], b["pixels"]
    total = 0.0
    count = 0
    for index in range(a["width"] * a["height"]):
        off = index * 4
        if pa[off + 3] <= 0.5 or pb[off + 3] <= 0.5:
            continue
        total += sum(abs(pa[off + channel] - pb[off + channel]) for channel in range(3)) / 3.0
        count += 1
    return total / max(count, 1)


def _local_detail(frame):
    width, height, px = frame["width"], frame["height"], frame["pixels"]
    total = 0.0
    count = 0
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            index = y * width + x
            off = index * 4
            if px[off + 3] <= 0.5:
                continue
            center = _luma(px[off:off + 3])
            for nx, ny in ((x + 2, y), (x, y + 2)):
                if nx >= width or ny >= height:
                    continue
                noff = (ny * width + nx) * 4
                if px[noff + 3] <= 0.5:
                    continue
                total += abs(center - _luma(px[noff:noff + 3]))
                count += 1
    return total / max(count, 1)


def _rim_center_ratio(frame):
    rows = _samples(frame)
    xs = [row[0] for row in rows]
    ys = [row[1] for row in rows]
    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5
    rx = max((max(xs) - min(xs)) * 0.5, 1.0)
    ry = max((max(ys) - min(ys)) * 0.5, 1.0)
    center, rim = [], []
    for x, y, _rgb, lum in rows:
        radius = math.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
        if radius <= 0.28:
            center.append(lum)
        elif 0.76 <= radius <= 0.93:
            rim.append(lum)
    return (sum(rim) / max(len(rim), 1)) / max(sum(center) / max(len(center), 1), 1e-9)


def _rim_mean_rgb(frame):
    rows = _samples(frame)
    xs = [row[0] for row in rows]
    ys = [row[1] for row in rows]
    cx = (min(xs) + max(xs)) * 0.5
    cy = (min(ys) + max(ys)) * 0.5
    rx = max((max(xs) - min(xs)) * 0.5, 1.0)
    ry = max((max(ys) - min(ys)) * 0.5, 1.0)
    rim = []
    for x, y, rgb, _lum in rows:
        radius = math.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
        if 0.72 <= radius <= 0.94:
            rim.append(rgb)
    if not rim:
        raise RuntimeError("subsurface probe has no rim samples")
    return tuple(sum(pixel[channel] for pixel in rim) / len(rim) for channel in range(3))


def _set_probe_lighting(key, fill, back):
    for name, energy in (
        ("AXM Probe Key", key),
        ("AXM Probe Fill", fill),
        ("AXM Probe Back", back),
    ):
        obj = bpy.data.objects.get(name)
        if obj is None or not hasattr(obj.data, "energy"):
            raise RuntimeError(f"probe light missing: {name}")
        obj.data.energy = float(energy)
    bpy.context.view_layer.update()


def _percentile_luma(frame, fraction):
    values = sorted(row[3] for row in _samples(frame))
    index = min(len(values) - 1, max(0, int((len(values) - 1) * fraction)))
    return values[index]


def _render_pair(scene, sphere, output, name, base, response):
    on = _render_probe(
        scene,
        sphere,
        _response_spec(name + "-on", base["color"], base["metallic"], base["roughness"], response),
        output / (name + "-on.png"),
    )
    off = _render_probe(
        scene,
        sphere,
        _base_spec(name + "-off", base["color"], base["metallic"], base["roughness"]),
        output / (name + "-off.png"),
    )
    return on, off


def run_verification(output_path):
    output = Path(output_path).resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene, sphere = _setup_probe_scene()
    cases = {}

    # Breakup: visible local micro-variation and repeatability from deterministic object-space noise.
    breakup_response = {
        "roughness": 0.55,
        "breakup": {
            "roughness_variation": 0.36,
            "color_variation": 0.22,
            "scale_mm": 40.0,
            "octaves": 3,
            "seed": 17,
        },
    }
    breakup_base = {"color": "#777777", "metallic": 0.0, "roughness": 0.55}
    b_on, b_off = _render_pair(scene, sphere, output, "breakup", breakup_base, breakup_response)
    b_repeat = _render_probe(
        scene,
        sphere,
        _response_spec("breakup-repeat", breakup_base["color"], 0.0, 0.55, breakup_response),
        output / "breakup-repeat.png",
    )
    b_delta = _mean_abs_delta(b_on, b_off)
    b_detail_on, b_detail_off = _local_detail(b_on), _local_detail(b_off)
    b_repeat_delta = _mean_abs_delta(b_on, b_repeat)
    b_pass = b_delta > 0.002 and b_detail_on > b_detail_off * 1.02 and b_repeat_delta < 1e-6
    cases["surface.breakup"] = {
        "passed": b_pass,
        "mean_abs_rgb_delta_vs_off": b_delta,
        "local_detail_with": b_detail_on,
        "local_detail_without": b_detail_off,
        "local_detail_gain": b_detail_on / max(b_detail_off, 1e-9),
        "repeat_mean_abs_rgb_delta": b_repeat_delta,
        "render_hashes": [b_on["png_sha256"], b_off["png_sha256"], b_repeat["png_sha256"]],
        "criterion": "delta>0.002, local-detail gain>1.02, repeat delta<1e-6 at authored 40 mm probe scale",
    }

    # Sheen: grazing-angle response should increase rim/centre behavior.
    sheen_response = {
        "roughness": 0.9,
        "specular": 0.05,
        "sheen": {"weight": 1.0, "roughness": 0.28, "tint": [1.0, 0.82, 0.82]},
    }
    sheen_base = {"color": "#350914", "metallic": 0.0, "roughness": 0.9}
    s_on, s_off = _render_pair(scene, sphere, output, "sheen", sheen_base, sheen_response)
    s_delta = _mean_abs_delta(s_on, s_off)
    s_ratio_on, s_ratio_off = _rim_center_ratio(s_on), _rim_center_ratio(s_off)
    s_gain = s_ratio_on / max(s_ratio_off, 1e-9)
    s_pass = s_delta > 0.001 and s_gain > 1.01
    cases["surface.sheen"] = {
        "passed": s_pass,
        "mean_abs_rgb_delta_vs_off": s_delta,
        "rim_center_with": s_ratio_on,
        "rim_center_without": s_ratio_off,
        "rim_center_gain": s_gain,
        "render_hashes": [s_on["png_sha256"], s_off["png_sha256"]],
        "criterion": "delta>0.001 and rim/centre gain>1.01",
    }

    # Coat: the second smooth lobe should lift the brightest response over a rough base.
    coat_response = {
        "roughness": 0.48,
        "clearcoat": {"weight": 1.0, "roughness": 0.03, "ior": 1.5},
    }
    coat_base = {"color": "#244a86", "metallic": 0.0, "roughness": 0.48}
    c_on, c_off = _render_pair(scene, sphere, output, "coat", coat_base, coat_response)
    c_delta = _mean_abs_delta(c_on, c_off)
    c_hi_on, c_hi_off = _percentile_luma(c_on, 0.995), _percentile_luma(c_off, 0.995)
    c_gain = c_hi_on / max(c_hi_off, 1e-9)
    c_pass = c_delta > 0.001 and c_gain > 1.01
    cases["surface.coat"] = {
        "passed": c_pass,
        "mean_abs_rgb_delta_vs_off": c_delta,
        "p99_5_luma_with": c_hi_on,
        "p99_5_luma_without": c_hi_off,
        "highlight_gain": c_gain,
        "render_hashes": [c_on["png_sha256"], c_off["png_sha256"]],
        "criterion": "delta>0.001 and 99.5th-percentile highlight gain>1.01",
    }

    # Subsurface core: EEVEE Christensen-Burley weight/radius/scale.
    # The pack's separate tint field stays a named partial-binding HOLD.
    _set_probe_lighting(12.0, 0.0, 3200.0)
    probe_world = scene.world.node_tree.nodes.get("Background")
    previous_world_strength = float(probe_world.inputs["Strength"].default_value)
    previous_scale = tuple(float(v) for v in sphere.scale)
    previous_back_size = float(bpy.data.objects["AXM Probe Back"].data.size)
    probe_world.inputs["Strength"].default_value = 0.0
    sphere.scale = (1.0, 0.10, 1.0)
    bpy.data.objects["AXM Probe Back"].data.size = 1.0
    bpy.context.view_layer.update()

    subsurface_base = {"color": "#d5a080", "metallic": 0.0, "roughness": 0.52}
    subsurface_response = {
        "roughness": 0.52,
        "subsurface": {
            "weight": 1.0,
            "radius_mm": [180.0, 65.0, 25.0],
            "tint": [0.9, 0.3, 0.2],
        },
    }
    ss_on, ss_off = _render_pair(
        scene, sphere, output, "subsurface-core", subsurface_base, subsurface_response
    )
    ss_delta = _mean_abs_delta(ss_on, ss_off)
    ss_rim_on, ss_rim_off = _rim_mean_rgb(ss_on), _rim_mean_rgb(ss_off)
    ss_luma_on, ss_luma_off = _luma(ss_rim_on), _luma(ss_rim_off)
    ss_luma_gain = ss_luma_on / max(ss_luma_off, 1e-9)
    ss_rb_on = ss_rim_on[0] / max(ss_rim_on[2], 1e-9)
    ss_rb_off = ss_rim_off[0] / max(ss_rim_off[2], 1e-9)
    ss_rb_gain = ss_rb_on / max(ss_rb_off, 1e-9)
    ss_pass = ss_delta > 0.003 and ss_luma_gain > 1.03 and ss_rb_gain > 1.01
    cases["surface.subsurface"] = {
        "passed": False,
        "organ_status": "HOLD_SUBSURFACE_TINT_UNMAPPED_IN_PRINCIPLED_EEVEE",
        "partial": {
            "passed": ss_pass,
            "bound_fields": ["weight", "radius_mm"],
            "renderer_method": "BURLEY",
            "mean_abs_rgb_delta_vs_off": ss_delta,
            "rim_luma_gain": ss_luma_gain,
            "rim_red_blue_gain": ss_rb_gain,
            "criterion": "delta>0.003, rim luma gain>1.03, rim red/blue gain>1.01",
        },
        "render_hashes": [ss_on["png_sha256"], ss_off["png_sha256"]],
        "truth": "This verifies EEVEE Burley weight/radius/scale only; the pack's separate tint field remains unmapped.",
    }
    sphere.scale = previous_scale
    bpy.data.objects["AXM Probe Back"].data.size = previous_back_size
    probe_world.inputs["Strength"].default_value = previous_world_strength
    _set_probe_lighting(900.0, 280.0, 850.0)
    bpy.context.view_layer.update()

    # EEVEE 4.3 does not support true Principled anisotropy.
    # Verify the explicit donor-declared directional-roughness fallback separately.
    aniso_base = {"color": "#a9adb5", "metallic": 1.0, "roughness": 0.32}
    aniso_response = {
        "metallic": 1.0,
        "roughness": 0.32,
        "anisotropy": {"strength": 0.9, "direction": "tangent_u", "rotation": 0.0},
    }
    a_on, a_off = _render_pair(scene, sphere, output, "anisotropy-fallback", aniso_base, aniso_response)
    rotated = {
        **aniso_response,
        "anisotropy": {"strength": 0.9, "direction": "tangent_u", "rotation": 0.25},
    }
    a_rot = _render_probe(
        scene,
        sphere,
        _response_spec("anisotropy-fallback-rotated", aniso_base["color"], 1.0, 0.32, rotated),
        output / "anisotropy-fallback-rotated.png",
    )
    a_delta = _mean_abs_delta(a_on, a_off)
    a_rotation_delta = _mean_abs_delta(a_on, a_rot)
    a_pass = a_delta > 0.001 and a_rotation_delta > 0.001
    cases["surface.anisotropy"] = {
        "passed": False,
        "organ_status": "HOLD_EEVEE_ANISOTROPY_UNSUPPORTED",
        "fallback": {
            "name": "directional_roughness",
            "passed": a_pass,
            "mean_abs_rgb_delta_vs_plain_roughness": a_delta,
            "mean_abs_rgb_delta_after_quarter_rotation": a_rotation_delta,
            "criterion": "fallback delta>0.001 and orientation delta>0.001",
        },
        "render_hashes": [a_on["png_sha256"], a_off["png_sha256"], a_rot["png_sha256"]],
        "truth": "The fallback is visual evidence for directional roughness only, not true anisotropic reflection.",
    }

    verified = sorted(
        organ for organ, result in cases.items()
        if organ != "surface.anisotropy" and result["passed"]
    )
    verified_partial_organs = []
    if cases["surface.subsurface"]["partial"]["passed"]:
        verified_partial_organs.append({
            "organ": "surface.subsurface",
            "bound_fields": ["weight", "radius_mm"],
            "renderer_method": "BURLEY",
            "evidence": "verified_render_receipt",
        })
    verified_fallbacks = []
    if cases["surface.anisotropy"]["fallback"]["passed"]:
        verified_fallbacks.append({
            "organ": "surface.anisotropy",
            "fallback": "directional_roughness",
            "evidence": "verified_render_receipt",
        })
    expected_direct = {"surface.breakup", "surface.sheen", "surface.coat"}
    status = (
        "PASS_SUPPORTED_AND_FALLBACKS"
        if set(verified) == expected_direct and verified_partial_organs and verified_fallbacks
        else "HOLD"
    )
    receipt = {
        "schema": "axm.avatar.blender-material-response-verification/v0.1",
        "host": {
            "renderer": "BLENDER_EEVEE_NEXT",
            "bpy_version": bpy.app.version_string,
            "resolution": [96, 96],
        },
        "verified_organs": verified,
        "verified_partial_organs": verified_partial_organs,
        "verified_fallbacks": verified_fallbacks,
        "cases": cases,
        "status": status,
        "evidence": (
            "verified_render_receipt"
            if status == "PASS_SUPPORTED_AND_FALLBACKS"
            else "declared_contract_match_not_tested"
        ),
        "scope": (
            "These measurements prove direct breakup/sheen/coat pixel effects, EEVEE Burley subsurface core behavior, and the anisotropy fallback in the Avatar Machine Blender 4.3 EEVEE probe scenes only. "
            "They do not prove physical correctness, Opus/reference-host numerical equivalence, artistic quality, "
            "or parity in exported game-engine materials."
        ),
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main():
    cfg = parse_args()
    receipt = run_verification(cfg.output)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
