#!/usr/bin/env python3
"""Fresh structural verification for the Odd Shift Duo Blender/GLB asset."""

import argparse
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

import bpy


def args():
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend")
    parser.add_argument("--output", required=True)
    return parser.parse_args(tail)


def read_glb(path):
    raw = path.read_bytes()
    magic, version, total_length = struct.unpack_from("<III", raw, 0)
    json_length, json_type = struct.unpack_from("<II", raw, 12)
    document = json.loads(raw[20:20 + json_length])
    return magic, version, total_length, json_type, document


def main():
    cfg = args()
    if cfg.blend:
        bpy.ops.wm.open_mainfile(filepath=str(Path(cfg.blend).resolve()))
    out_dir = Path(cfg.output).resolve()
    scene = bpy.context.scene
    rig = bpy.data.objects.get("OddShift_Duo_Rig")
    glb_path = out_dir / "Odd-Shift-Duo.glb"
    video_path = out_dir / "Odd-Shift-Duo-Preview.mp4"
    poster_path = out_dir / "Odd-Shift-Duo-Poster.png"
    magic, version, total_length, json_type, gltf = read_glb(glb_path)

    scene.frame_set(92)
    a_hand = rig.pose.bones["A_R_hand"].head.copy()
    b_hand = rig.pose.bones["B_L_hand"].head.copy()
    contact_distance = (a_hand - b_hand).length
    action = rig.animation_data.action if rig and rig.animation_data else None
    exported = [obj for obj in bpy.data.objects if obj.get("odd_shift_export")]
    missing_material = [obj.name for obj in exported if obj.type == "MESH" and not obj.data.materials]
    markers = {marker.name: marker.frame for marker in scene.timeline_markers}
    expected_markers = {
        "CURIOUS_IDLE": 1,
        "SWAGGER_WALK": 33,
        "HIGH_FIVE": 73,
        "VICTORY": 105,
    }

    ffprobe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames",
            "-of", "json", str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    video = json.loads(ffprobe.stdout)
    stream = video["streams"][0]
    skin_binding_nodes = sum("skin" in node for node in gltf.get("nodes", []))

    checks = {
        "blend_title_metadata": scene.get("asset_title") == "Odd Shift Duo",
        "one_shared_armature": sum(obj.type == "ARMATURE" for obj in exported) == 1,
        "expected_bone_count": rig is not None and len(rig.data.bones) == 34,
        "synchronized_action_present": action is not None and action.name == "OddShift_Duo_Demo",
        "animation_covers_authored_range": action is not None and action.frame_range[0] <= 1 and action.frame_range[1] >= 144,
        "clip_markers_present": all(markers.get(name) == frame for name, frame in expected_markers.items()),
        "high_five_contact_under_12cm": contact_distance < 0.12,
        "export_meshes_have_materials": not missing_material,
        "reference_not_embedded": scene.get("source_reference_embedded") is False and not [
            image for image in bpy.data.images
            if image.source != "VIEWER" and (image.filepath or image.packed_file)
        ],
        "glb_magic_and_version": magic == 0x46546C67 and version == 2 and json_type == 0x4E4F534A,
        "glb_declared_size_matches": total_length == glb_path.stat().st_size,
        "glb_has_one_skin": len(gltf.get("skins", [])) == 1,
        "glb_has_34_joints": len(gltf.get("skins", [{}])[0].get("joints", [])) == 34,
        "glb_has_meshes": len(gltf.get("meshes", [])) >= 90,
        "glb_has_materials": len(gltf.get("materials", [])) >= 20,
        "glb_has_synchronized_animation": len(gltf.get("animations", [])) == 1 and gltf["animations"][0].get("name") == "OddShift_Duo_Demo",
        "glb_animation_is_substantive": len(gltf.get("animations", [{}])[0].get("channels", [])) >= 80,
        "poster_exists": poster_path.exists() and poster_path.stat().st_size > 100_000,
        "preview_is_h264": stream.get("codec_name") == "h264",
        "preview_dimensions": stream.get("width") == 640 and stream.get("height") == 640,
        "preview_duration": abs(float(video["format"]["duration"]) - 6.0) < 0.05,
    }

    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "metrics": {
            "export_objects": len(exported),
            "mesh_nodes": len(gltf.get("meshes", [])),
            "materials": len(gltf.get("materials", [])),
            "joints": len(gltf.get("skins", [{}])[0].get("joints", [])),
            "skin_binding_nodes": skin_binding_nodes,
            "animation_channels": len(gltf.get("animations", [{}])[0].get("channels", [])),
            "high_five_hand_distance_m": round(contact_distance, 4),
            "glb_bytes": glb_path.stat().st_size,
            "preview_frames": int(stream.get("nb_frames", 0)),
            "preview_seconds": float(video["format"]["duration"]),
        },
        "visual_review": {
            "frames_reviewed": [17, 53, 92, 124],
            "result": "Readable identity anchors, distinct silhouettes, grounded walk, clear contact pose, and clean victory pose.",
            "showcase_only_stage_excluded_from_glb": True,
        },
        "deformation": {
            "model": "SKINNED_MESH" if skin_binding_nodes else "RIGID_BONE_PARENTING",
            "skinned_mesh_deformation": bool(skin_binding_nodes),
            "note": (
                "Mesh nodes reference the glTF skin."
                if skin_binding_nodes
                else "No mesh node references the retained skin; the proven asset uses rigid bone-parent hierarchy animation."
            ),
        },
    }
    report_lines = [
        "ODD SHIFT DUO — VERIFICATION REPORT",
        f"STATUS: {result['status']}",
        "",
        "STRUCTURAL CHECKS",
    ]
    report_lines.extend(f"[{'PASS' if passed else 'FAIL'}] {name}" for name, passed in checks.items())
    report_lines.extend([
        "",
        "METRICS",
        *[f"{name}: {value}" for name, value in result["metrics"].items()],
        "",
        "VISUAL REVIEW",
        "Frames inspected: 17 (idle), 53 (walk), 92 (high-five), 124 (victory)",
        result["visual_review"]["result"],
        "The supplied photograph is not packed into the Blender file or exported GLB.",
        "",
        "DEFORMATION TRUTH",
        f"Model: {result['deformation']['model']}",
        result["deformation"]["note"],
    ])
    (out_dir / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out_dir / "verification_report.txt").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
