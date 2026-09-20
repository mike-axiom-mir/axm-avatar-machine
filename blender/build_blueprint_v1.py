#!/usr/bin/env python3
"""Compile an AXM Doll Blueprint v1 scene plan into editable Blender/GLB outputs.

This is a new generic bounded doll builder. It does not replace or modify the
recovered Odd Shift Duo builder, which remains the regression baseline.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(tail)


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.armatures, bpy.data.materials, bpy.data.meshes, bpy.data.curves,
                       bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def rgba(hex_color):
    raw = hex_color.lstrip("#")
    return tuple(int(raw[i:i+2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)


def make_material(spec):
    material = bpy.data.materials.new(spec["id"])
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba(spec["color"])
    bsdf.inputs["Metallic"].default_value = float(spec["metallic"])
    bsdf.inputs["Roughness"].default_value = float(spec["roughness"])
    if "specular" in spec and bsdf.inputs.get("Specular IOR Level") is not None:
        bsdf.inputs["Specular IOR Level"].default_value = float(spec["specular"])
    if spec.get("response_family"):
        material["axm_response_family"] = spec["response_family"]
        material["axm_response_renderer_binding"] = spec.get(
            "response_renderer_binding", "HOLD_BLUEPRINT_BLENDER_ORGANS_NOT_BOUND"
        )
        material["axm_active_organs"] = json.dumps(spec.get("active_organs", []), sort_keys=True)
    return material


def make_rig(bones):
    data = bpy.data.armatures.new("AXM_Doll_Blueprint_RigData")
    rig = bpy.data.objects.new("AXM_Doll_Blueprint_Rig", data)
    bpy.context.collection.objects.link(rig)
    rig["axm_deformation"] = "RIGID_BONE_PARENTING"
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for spec in bones:
        bone = data.edit_bones.new(spec["name"])
        bone.head = spec["head"]
        bone.tail = spec["tail"]
        if spec.get("parent"):
            bone.parent = data.edit_bones.get(spec["parent"])
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)
    return rig


def assign(obj, material):
    if material and hasattr(obj.data, "materials"):
        obj.data.materials.append(material)


def bone_parent(obj, rig, bone_name):
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world


def smooth(obj):
    if hasattr(obj.data, "polygons"):
        for polygon in obj.data.polygons:
            polygon.use_smooth = True


def cylinder_between(start, end, radius):
    start_v, end_v = Vector(start), Vector(end)
    direction = end_v - start_v
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=direction.length,
                                       location=(start_v + end_v) * 0.5)
    obj = bpy.context.object
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


def create_object(spec, materials, rig):
    primitive = spec["primitive"]
    if primitive == "ellipsoid":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=16, location=spec["location"])
        obj = bpy.context.object
        obj.scale = spec["scale"]
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        smooth(obj)
    elif primitive == "box":
        bpy.ops.mesh.primitive_cube_add(location=spec["location"], rotation=spec.get("rotation", [0,0,0]))
        obj = bpy.context.object
        obj.dimensions = spec["dimensions"]
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bevel = obj.modifiers.new("crafted edge", "BEVEL")
        bevel.width = min(spec["dimensions"]) * 0.08
        bevel.segments = 2
    elif primitive == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=spec["radius"], depth=spec["depth"],
                                           location=spec["location"], rotation=spec.get("rotation", [0,0,0]))
        obj = bpy.context.object
        smooth(obj)
    elif primitive == "cylinder_between":
        obj = cylinder_between(spec["start"], spec["end"], spec["radius"])
        smooth(obj)
    elif primitive == "torus":
        bpy.ops.mesh.primitive_torus_add(major_radius=spec["major_radius"], minor_radius=spec["minor_radius"],
                                        major_segments=32, minor_segments=12, location=spec["location"],
                                        rotation=spec.get("rotation", [0,0,0]))
        obj = bpy.context.object
        obj.scale = spec.get("scale", [1,1,1])
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        smooth(obj)
    else:
        raise ValueError(f"unsupported primitive {primitive!r}")
    obj.name = spec["id"]
    obj["axm_blueprint_part"] = True
    obj["axm_part_id"] = spec["id"]
    assign(obj, materials[spec["material"]])
    bone_parent(obj, rig, spec["bone"])
    return obj


def animate(rig, keys):
    if not keys:
        return
    action = bpy.data.actions.new("AXM_Blueprint_Action")
    rig.animation_data_create()
    rig.animation_data.action = action
    for spec in keys:
        pose_bone = rig.pose.bones.get(spec["bone"])
        if pose_bone is None:
            raise ValueError(f"missing animation bone {spec['bone']}")
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = spec["rotation_euler"]
        pose_bone.keyframe_insert(data_path="rotation_euler", frame=spec["frame"], group=spec["bone"])


def stage(scene, plan):
    world = bpy.data.worlds.new("AXM Blueprint World") if bpy.data.worlds.get("AXM Blueprint World") is None else bpy.data.worlds["AXM Blueprint World"]
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = rgba(plan["scene"]["background"])
    bg.inputs["Strength"].default_value = 0.42

    bpy.ops.object.camera_add(location=plan["scene"]["camera"]["location"])
    camera = bpy.context.object
    camera.name = "AXM_Blueprint_Camera"
    camera.data.lens = plan["scene"]["camera"]["lens"]
    target = Vector((0, 0, 1.55))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera

    for loc, energy, size in [((-4,-4,7), 1100, 4.0), ((4,-2,5), 800, 3.0), ((0,4,4), 600, 3.0)]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.rotation_euler = (Vector((0,0,1.5)) - light.location).to_track_quat("-Z", "Y").to_euler()

    bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,0))
    floor = bpy.context.object
    floor.name = "AXM_Blueprint_Floor"
    mat = bpy.data.materials.new("AXM_Floor")
    mat.diffuse_color = (0.12,0.13,0.15,1)
    floor.data.materials.append(mat)


def main():
    cfg = parse_args()
    plan = json.loads(Path(cfg.plan).read_text(encoding="utf-8"))
    if plan.get("schema") != "axm.avatar.scene-plan/v1":
        raise ValueError("unsupported scene plan schema")
    out = Path(cfg.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    reset_scene()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(out / "Blueprint-Avatar-Poster.png")
    scene.render.fps = plan["scene"]["fps"]
    scene.frame_start = plan["scene"]["frame_start"]
    scene.frame_end = plan["scene"]["frame_end"]
    scene["axm_blueprint_plan_sha256"] = plan["plan_sha256"]
    scene["axm_deformation"] = "RIGID_BONE_PARENTING"

    materials = {spec["id"]: make_material(spec) for spec in plan["materials"]}
    rig = make_rig(plan["bones"])
    for spec in plan["objects"]:
        create_object(spec, materials, rig)
    animate(rig, plan["animation"])
    stage(scene, plan)

    scene.frame_set(scene.frame_start)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "Blueprint-Avatar.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    for obj in bpy.data.objects:
        if obj.get("axm_blueprint_part"):
            obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(
        filepath=str(out / "Blueprint-Avatar.glb"),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
    )
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.render.render(write_still=True)
    response_materials = [spec for spec in plan["materials"] if spec.get("response_family")]
    active_response_organs = sorted({
        organ for spec in response_materials for organ in spec.get("active_organs", [])
    })
    material_response_status = (
        "HOLD_BLUEPRINT_BLENDER_ORGANS_NOT_BOUND" if active_response_organs
        else "PASS_NO_ACTIVE_ORGANS"
    )
    receipt = {
        "schema": "axm.avatar.blueprint-build-receipt/v1",
        "plan_sha256": plan["plan_sha256"],
        "deformation": "RIGID_BONE_PARENTING",
        "objects": len(plan["objects"]),
        "bones": len(plan["bones"]),
        "materials": len(plan["materials"]),
        "animation_keys": len(plan["animation"]),
        "outputs": ["Blueprint-Avatar.blend", "Blueprint-Avatar.glb", "Blueprint-Avatar-Poster.png"],
        "material_response": {
            "selected_materials": len(response_materials),
            "active_organs": active_response_organs,
            "base_scalar_projection": True,
            "organ_behavior_bound": False,
            "status": material_response_status,
        },
        "status": (
            "BUILT_WITH_MATERIAL_RESPONSE_HOLD_NOT_AESTHETICALLY_ACCEPTED"
            if active_response_organs else "BUILT_NOT_AESTHETICALLY_ACCEPTED"
        ),
    }
    (out / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
