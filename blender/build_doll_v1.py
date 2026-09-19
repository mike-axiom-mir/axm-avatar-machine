#!/usr/bin/env python3
"""Build the original Odd Shift Duo rigged game asset in Blender 4.x."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

FPS = 24
END = 144
EXPORT_OBJECTS = []
RIG = None


def parse_args():
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--poster-frame", type=int, default=92)
    return parser.parse_args(tail)


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.armatures,
        bpy.data.materials,
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def mat(name, color, metallic=0.0, roughness=0.5, emission=None, strength=0.0,
        subsurface=0.0, noise=False):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = subsurface
        if "Subsurface Radius" in bsdf.inputs:
            bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.25)
    if emission is not None:
        key = "Emission Color" if "Emission Color" in bsdf.inputs else "Emission"
        bsdf.inputs[key].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    if noise:
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 95.0
        tex.inputs["Detail"].default_value = 2.8
        tex.inputs["Roughness"].default_value = 0.72
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.11
        bump.inputs["Distance"].default_value = 0.025
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return material


def assign(obj, material):
    if material is not None and hasattr(obj.data, "materials"):
        obj.data.materials.append(material)
    return obj


def smooth(obj):
    if hasattr(obj.data, "polygons"):
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    return obj


def bevel(obj, width=0.035, segments=2):
    modifier = obj.modifiers.new("crafted edge", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    return obj


def mark_export(obj, role="character"):
    obj["odd_shift_export"] = True
    obj["asset_role"] = role
    EXPORT_OBJECTS.append(obj)
    return obj


def box(name, loc, dims, material=None, rotation=(0, 0, 0), edge=0.035, export=False):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, material)
    if edge:
        bevel(obj, edge, 3)
    if export:
        mark_export(obj)
    return obj


def ellipsoid(name, loc, scale, material=None, segments=32, export=False):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=max(12, segments // 2), location=loc
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, material)
    smooth(obj)
    if export:
        mark_export(obj)
    return obj


def cylinder(name, loc, radius, depth, material=None, rotation=(0, 0, 0), vertices=24,
             export=False, edge=0.015):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    assign(obj, material)
    if edge:
        bevel(obj, edge, 2)
    smooth(obj)
    if export:
        mark_export(obj)
    return obj


def cone(name, loc, radius1, radius2, depth, material=None, rotation=(0, 0, 0),
         vertices=24, export=False):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices, radius1=radius1, radius2=radius2, depth=depth,
        location=loc, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    assign(obj, material)
    bevel(obj, 0.018, 2)
    smooth(obj)
    if export:
        mark_export(obj)
    return obj


def torus(name, loc, major, minor, material=None, rotation=(0, 0, 0), scale=(1, 1, 1),
          export=False):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major, minor_radius=minor, major_segments=32, minor_segments=12,
        location=loc, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, material)
    smooth(obj)
    if export:
        mark_export(obj)
    return obj


def curve_tube(name, points, radius, material=None, export=False, cyclic=False):
    curve_data = bpy.data.curves.new(name + " curve", "CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 2
    curve_data.bevel_depth = radius
    curve_data.bevel_resolution = 3
    spline = curve_data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, point in zip(spline.bezier_points, points):
        bp.co = point
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(obj)
    assign(obj, material)
    if export:
        mark_export(obj)
    return obj


def cylinder_between(name, start, end, radius, material=None, export=False):
    start_v, end_v = Vector(start), Vector(end)
    direction = end_v - start_v
    obj = cylinder(name, (start_v + end_v) * 0.5, radius, direction.length, material,
                   vertices=24, export=export)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


def add_text(name, body, loc, rotation, size, material, extrude=0.025):
    data = bpy.data.curves.new(name + " data", "FONT")
    data.body = body
    data.align_x = "CENTER"
    data.align_y = "CENTER"
    data.size = size
    data.extrude = extrude
    data.bevel_depth = 0.004
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rotation
    assign(obj, material)
    return obj


def bone_parent(obj, bone_name):
    world = obj.matrix_world.copy()
    obj.parent = RIG
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world
    return obj


def create_rig():
    global RIG
    data = bpy.data.armatures.new("OddShift_Duo_RigData")
    RIG = bpy.data.objects.new("OddShift_Duo_Rig", data)
    bpy.context.collection.objects.link(RIG)
    mark_export(RIG, "shared_armature")
    RIG.show_in_front = True
    bpy.context.view_layer.objects.active = RIG
    RIG.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    specs = {}

    def add(name, head, tail, parent=None):
        bone = data.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        if parent:
            bone.parent = data.edit_bones.get(parent)
        specs[name] = (head, tail)

    # Compact Chaos rig on the left.
    ax = -1.05
    add("A_root", (ax, 0, 0.02), (ax, 0, 0.28))
    add("A_pelvis", (ax, 0, 1.02), (ax, 0, 1.36), "A_root")
    add("A_spine", (ax, 0, 1.36), (ax, 0, 2.16), "A_pelvis")
    add("A_neck", (ax, 0, 2.16), (ax, 0, 2.48), "A_spine")
    add("A_head", (ax, 0, 2.48), (ax, 0, 3.18), "A_neck")
    for side, sx in (("L", -1), ("R", 1)):
        lx = ax + sx * 0.22
        add(f"A_{side}_thigh", (lx, 0, 1.15), (lx, 0, 0.66), "A_pelvis")
        add(f"A_{side}_shin", (lx, 0, 0.66), (lx, 0, 0.25), f"A_{side}_thigh")
        add(f"A_{side}_foot", (lx, 0, 0.25), (lx, -0.30, 0.15), f"A_{side}_shin")
        sx2 = ax + sx * 0.51
        add(f"A_{side}_upperarm", (sx2, 0, 2.08), (sx2, 0, 1.53), "A_spine")
        add(f"A_{side}_forearm", (sx2, 0, 1.53), (sx2, 0, 1.07), f"A_{side}_upperarm")
        add(f"A_{side}_hand", (sx2, 0, 1.07), (sx2, 0, 0.88), f"A_{side}_forearm")

    # Lanky Deadpan rig on the right.
    bx = 1.08
    add("B_root", (bx, 0, 0.02), (bx, 0, 0.28))
    add("B_pelvis", (bx, 0, 1.12), (bx, 0, 1.51), "B_root")
    add("B_spine", (bx, 0, 1.51), (bx, 0, 2.43), "B_pelvis")
    add("B_neck", (bx, 0, 2.43), (bx, 0, 2.71), "B_spine")
    add("B_head", (bx, 0, 2.71), (bx, 0, 3.42), "B_neck")
    for side, sx in (("L", -1), ("R", 1)):
        lx = bx + sx * 0.19
        add(f"B_{side}_thigh", (lx, 0, 1.30), (lx, 0, 0.72), "B_pelvis")
        add(f"B_{side}_shin", (lx, 0, 0.72), (lx, 0, 0.25), f"B_{side}_thigh")
        add(f"B_{side}_foot", (lx, 0, 0.25), (lx, -0.32, 0.15), f"B_{side}_shin")
        sx2 = bx + sx * 0.43
        add(f"B_{side}_upperarm", (sx2, 0, 2.34), (sx2, 0, 1.69), "B_spine")
        add(f"B_{side}_forearm", (sx2, 0, 1.69), (sx2, 0, 1.15), f"B_{side}_upperarm")
        add(f"B_{side}_hand", (sx2, 0, 1.15), (sx2, 0, 0.92), f"B_{side}_forearm")

    bpy.ops.object.mode_set(mode="OBJECT")
    RIG.select_set(False)
    return specs


def add_joint(name, loc, radius, material, bone):
    return bone_parent(ellipsoid(name, loc, (radius, radius, radius), material, 20, True), bone)


def make_chaos(m):
    x = -1.05
    # Shoes and jeans.
    for side, sx in (("L", -1), ("R", 1)):
        lx = x + sx * 0.22
        foot = ellipsoid(f"Chaos {side} sneaker", (lx, -0.12, 0.16), (0.22, 0.34, 0.15), m["shoe"], 24, True)
        bone_parent(foot, f"A_{side}_foot")
        sole = box(f"Chaos {side} white sole", (lx, -0.15, 0.085), (0.43, 0.62, 0.08), m["sole"], edge=0.035, export=True)
        bone_parent(sole, f"A_{side}_foot")
        shin = cylinder_between(f"Chaos {side} jean shin", (lx, 0, 0.27), (lx, 0, 0.67), 0.18, m["denim"], True)
        bone_parent(shin, f"A_{side}_shin")
        thigh = cylinder_between(f"Chaos {side} jean thigh", (lx, 0, 0.65), (lx, 0, 1.18), 0.205, m["denim"], True)
        bone_parent(thigh, f"A_{side}_thigh")
        add_joint(f"Chaos {side} knee", (lx, 0, 0.66), 0.19, m["denim"], f"A_{side}_shin")

    hips = ellipsoid("Chaos jeans waist", (x, 0, 1.24), (0.48, 0.31, 0.30), m["denim"], 28, True)
    bone_parent(hips, "A_pelvis")
    torso = ellipsoid("Chaos blue hoodie", (x, 0, 1.77), (0.55, 0.34, 0.62), m["hoodie"], 32, True)
    bone_parent(torso, "A_spine")
    hem = torus("Chaos hoodie hem", (x, 0, 1.34), 0.43, 0.035, m["hoodie_dark"], scale=(1.1, 0.72, 1), export=True)
    bone_parent(hem, "A_spine")
    # Jacket side panels reveal the blue hoodie in the middle.
    for sx in (-1, 1):
        panel = box(
            f"Chaos jacket panel {sx}", (x + sx * 0.37, -0.035, 1.77),
            (0.28, 0.66, 1.12), m["jacket"], rotation=(0, sx * math.radians(8), 0),
            edge=0.08, export=True,
        )
        bone_parent(panel, "A_spine")
        lapel = box(
            f"Chaos lapel {sx}", (x + sx * 0.20, -0.34, 2.01),
            (0.15, 0.07, 0.56), m["jacket_hi"], rotation=(0, sx * math.radians(20), 0),
            edge=0.025, export=True,
        )
        bone_parent(lapel, "A_spine")
    zipper = box("Chaos zipper", (x, -0.354, 1.69), (0.025, 0.025, 0.76), m["zipper"], edge=0.006, export=True)
    bone_parent(zipper, "A_spine")
    for sx in (-1, 1):
        pocket = box(f"Chaos pocket {sx}", (x + sx * 0.34, -0.36, 1.48), (0.25, 0.035, 0.05), m["zipper"],
                     rotation=(0, sx * math.radians(14), 0), edge=0.01, export=True)
        bone_parent(pocket, "A_spine")

    # Sleeves, hands, and small jacket cuffs.
    for side, sx in (("L", -1), ("R", 1)):
        ax = x + sx * 0.51
        upper = cylinder_between(f"Chaos {side} jacket upperarm", (ax, 0, 2.05), (ax, 0, 1.54), 0.18, m["jacket"], True)
        bone_parent(upper, f"A_{side}_upperarm")
        elbow = add_joint(f"Chaos {side} elbow", (ax, 0, 1.53), 0.18, m["jacket"], f"A_{side}_forearm")
        fore = cylinder_between(f"Chaos {side} jacket forearm", (ax, 0, 1.49), (ax, 0, 1.08), 0.16, m["jacket"], True)
        bone_parent(fore, f"A_{side}_forearm")
        cuff = cylinder(f"Chaos {side} cuff", (ax, 0, 1.10), 0.17, 0.10, m["hoodie_dark"], vertices=24, export=True)
        bone_parent(cuff, f"A_{side}_forearm")
        hand = ellipsoid(f"Chaos {side} hand", (ax, -0.01, 0.96), (0.18, 0.14, 0.21), m["skin_a"], 28, True)
        bone_parent(hand, f"A_{side}_hand")

    # Neck, sculpted bald head, ears, stubble, and comic face.
    neck = cylinder("Chaos neck", (x, 0, 2.38), 0.19, 0.34, m["skin_a"], vertices=28, export=True)
    bone_parent(neck, "A_neck")
    head = ellipsoid("Chaos bald head", (x, 0, 2.84), (0.46, 0.405, 0.50), m["skin_a"], 40, True)
    bone_parent(head, "A_head")
    for sx in (-1, 1):
        ear = ellipsoid(f"Chaos ear {sx}", (x + sx * 0.45, -0.01, 2.84), (0.09, 0.055, 0.15), m["skin_a"], 20, True)
        bone_parent(ear, "A_head")
    beard = ellipsoid("Chaos dark stubble", (x, -0.045, 2.67), (0.385, 0.385, 0.29), m["stubble"], 36, True)
    bone_parent(beard, "A_head")
    face_patch = ellipsoid("Chaos clean upper face", (x, -0.175, 2.93), (0.40, 0.235, 0.32), m["skin_a"], 36, True)
    bone_parent(face_patch, "A_head")
    nose = ellipsoid("Chaos nose", (x, -0.421, 2.85), (0.095, 0.13, 0.14), m["skin_a_hi"], 28, True)
    bone_parent(nose, "A_head")
    # Deliberately uneven eyes echo the photo's comic expression.
    for sx, z, scale in ((-1, 2.965, (0.13, 0.055, 0.095)), (1, 3.005, (0.15, 0.06, 0.13))):
        eye = ellipsoid(f"Chaos eye {sx}", (x + sx * 0.18, -0.395, z), scale, m["eye"], 28, True)
        bone_parent(eye, "A_head")
        pupil = ellipsoid(f"Chaos pupil {sx}", (x + sx * 0.18, -0.454, z), (0.046, 0.025, 0.057), m["pupil"], 20, True)
        bone_parent(pupil, "A_head")
    for sx, ang, z in ((-1, math.radians(-7), 3.13), (1, math.radians(10), 3.17)):
        brow = box(f"Chaos brow {sx}", (x + sx * 0.18, -0.445, z), (0.24, 0.035, 0.047), m["stubble"],
                   rotation=(0, ang, 0), edge=0.016, export=True)
        bone_parent(brow, "A_head")
    # Puckered lips: two soft lobes plus a dark opening.
    mouth = ellipsoid("Chaos mouth opening", (x, -0.443, 2.665), (0.09, 0.025, 0.075), m["mouth"], 24, True)
    bone_parent(mouth, "A_head")
    for sx in (-1, 1):
        lip = ellipsoid(f"Chaos pucker lip {sx}", (x + sx * 0.055, -0.466, 2.69), (0.075, 0.032, 0.055), m["lip"], 24, True)
        bone_parent(lip, "A_head")

    # Headphones: full neck band, metal hinge details, padded cups.
    band = torus("Chaos headphone band", (x, 0.01, 2.39), 0.39, 0.052, m["headphone"],
                 rotation=(math.radians(90), 0, 0), scale=(1.0, 1.0, 0.72), export=True)
    bone_parent(band, "A_neck")
    for sx in (-1, 1):
        cup = cylinder(f"Chaos headphone cup {sx}", (x + sx * 0.39, -0.04, 2.34), 0.17, 0.12, m["headphone"],
                       rotation=(math.radians(90), 0, 0), vertices=32, export=True)
        bone_parent(cup, "A_neck")
        inset = cylinder(f"Chaos headphone inset {sx}", (x + sx * 0.39, -0.105, 2.34), 0.11, 0.018, m["headphone_hi"],
                         rotation=(math.radians(90), 0, 0), vertices=28, export=True)
        bone_parent(inset, "A_neck")
        hinge = box(f"Chaos headphone hinge {sx}", (x + sx * 0.40, 0.0, 2.53), (0.10, 0.10, 0.16), m["zipper"], edge=0.025, export=True)
        bone_parent(hinge, "A_neck")


def make_deadpan(m):
    x = 1.08
    # Shoes and dark trousers.
    for side, sx in (("L", -1), ("R", 1)):
        lx = x + sx * 0.19
        foot = ellipsoid(f"Deadpan {side} sneaker", (lx, -0.13, 0.16), (0.20, 0.34, 0.14), m["shoe_b"], 24, True)
        bone_parent(foot, f"B_{side}_foot")
        sole = box(f"Deadpan {side} sole", (lx, -0.15, 0.082), (0.38, 0.62, 0.07), m["sole"], edge=0.03, export=True)
        bone_parent(sole, f"B_{side}_foot")
        shin = cylinder_between(f"Deadpan {side} trouser shin", (lx, 0, 0.26), (lx, 0, 0.73), 0.15, m["trouser"], True)
        bone_parent(shin, f"B_{side}_shin")
        thigh = cylinder_between(f"Deadpan {side} trouser thigh", (lx, 0, 0.71), (lx, 0, 1.32), 0.17, m["trouser"], True)
        bone_parent(thigh, f"B_{side}_thigh")
        add_joint(f"Deadpan {side} knee", (lx, 0, 0.72), 0.158, m["trouser"], f"B_{side}_shin")
    hips = ellipsoid("Deadpan trouser waist", (x, 0, 1.38), (0.39, 0.26, 0.29), m["trouser"], 28, True)
    bone_parent(hips, "B_pelvis")

    # Tailored white polo with seam, collar, placket and fictional gold pin.
    torso = ellipsoid("Deadpan white polo", (x, 0, 1.94), (0.45, 0.29, 0.68), m["polo"], 32, True)
    bone_parent(torso, "B_spine")
    hem = torus("Deadpan polo hem", (x, 0, 1.48), 0.34, 0.026, m["polo_shadow"], scale=(1.12, 0.72, 1), export=True)
    bone_parent(hem, "B_spine")
    for sx in (-1, 1):
        collar = box(f"Deadpan collar {sx}", (x + sx * 0.14, -0.292, 2.35), (0.25, 0.045, 0.18), m["polo_shadow"],
                     rotation=(0, sx * math.radians(24), 0), edge=0.025, export=True)
        bone_parent(collar, "B_spine")
    placket = box("Deadpan polo placket", (x, -0.298, 2.20), (0.075, 0.035, 0.34), m["polo_shadow"], edge=0.014, export=True)
    bone_parent(placket, "B_spine")
    for i in range(3):
        button = ellipsoid(f"Deadpan button {i}", (x, -0.323, 2.31 - i * 0.105), (0.027, 0.013, 0.027), m["button"], 16, True)
        bone_parent(button, "B_spine")
    # Gold crescent is fictional and deliberately not a copied logo.
    badge = torus("Deadpan gold crescent pin", (x + 0.27, -0.318, 2.13), 0.075, 0.018, m["gold"],
                  rotation=(math.radians(90), 0, 0), scale=(0.72, 1.0, 1.0), export=True)
    bone_parent(badge, "B_spine")
    badge_cut = box("Deadpan crescent slash", (x + 0.305, -0.339, 2.13), (0.075, 0.025, 0.19), m["polo"],
                    rotation=(0, math.radians(-8), 0), edge=0.01, export=True)
    bone_parent(badge_cut, "B_spine")

    for side, sx in (("L", -1), ("R", 1)):
        ax = x + sx * 0.43
        sleeve = cylinder_between(f"Deadpan {side} polo sleeve", (ax, 0, 2.31), (ax, 0, 2.02), 0.17, m["polo"], True)
        bone_parent(sleeve, f"B_{side}_upperarm")
        band = cylinder(f"Deadpan {side} sleeve band", (ax, 0, 2.02), 0.17, 0.045, m["gold"], vertices=24, export=True)
        bone_parent(band, f"B_{side}_upperarm")
        upper = cylinder_between(f"Deadpan {side} bare upperarm", (ax, 0, 1.98), (ax, 0, 1.69), 0.145, m["skin_b"], True)
        bone_parent(upper, f"B_{side}_upperarm")
        add_joint(f"Deadpan {side} elbow", (ax, 0, 1.69), 0.15, m["skin_b"], f"B_{side}_forearm")
        fore = cylinder_between(f"Deadpan {side} forearm", (ax, 0, 1.67), (ax, 0, 1.15), 0.135, m["skin_b"], True)
        bone_parent(fore, f"B_{side}_forearm")
        hand = ellipsoid(f"Deadpan {side} hand", (ax, -0.01, 1.03), (0.16, 0.125, 0.22), m["skin_b"], 28, True)
        bone_parent(hand, f"B_{side}_hand")

    neck = cylinder("Deadpan neck", (x, 0, 2.60), 0.17, 0.34, m["skin_b"], vertices=28, export=True)
    bone_parent(neck, "B_neck")
    head = ellipsoid("Deadpan head", (x, 0, 3.02), (0.40, 0.36, 0.48), m["skin_b"], 40, True)
    bone_parent(head, "B_head")
    jaw = ellipsoid("Deadpan jaw definition", (x, -0.045, 2.88), (0.34, 0.32, 0.28), m["skin_b_shadow"], 32, True)
    bone_parent(jaw, "B_head")
    face_patch = ellipsoid("Deadpan clean face", (x, -0.15, 3.04), (0.35, 0.23, 0.33), m["skin_b"], 34, True)
    bone_parent(face_patch, "B_head")
    for sx in (-1, 1):
        ear = ellipsoid(f"Deadpan ear {sx}", (x + sx * 0.39, -0.005, 3.03), (0.075, 0.052, 0.13), m["skin_b"], 20, True)
        bone_parent(ear, "B_head")
    nose = ellipsoid("Deadpan nose", (x, -0.372, 3.035), (0.075, 0.115, 0.145), m["skin_b_hi"], 26, True)
    bone_parent(nose, "B_head")
    # Eyes and highly readable raised brow.
    for sx, z in ((-1, 3.13), (1, 3.10)):
        eye = ellipsoid(f"Deadpan eye {sx}", (x + sx * 0.145, -0.346, z), (0.115, 0.05, 0.09), m["eye"], 26, True)
        bone_parent(eye, "B_head")
        pupil_x = x + sx * 0.145 - 0.018
        pupil = ellipsoid(f"Deadpan pupil {sx}", (pupil_x, -0.397, z), (0.040, 0.022, 0.050), m["pupil"], 20, True)
        bone_parent(pupil, "B_head")
    for sx, ang, z in ((-1, math.radians(18), 3.27), (1, math.radians(-4), 3.22)):
        brow = box(f"Deadpan eyebrow {sx}", (x + sx * 0.15, -0.386, z), (0.23, 0.03, 0.043), m["hair"],
                   rotation=(0, ang, 0), edge=0.014, export=True)
        bone_parent(brow, "B_head")
    # Crooked half-smile built as an asymmetric tube.
    smile = curve_tube(
        "Deadpan crooked smile",
        [(x - 0.13, -0.385, 2.89), (x - 0.02, -0.405, 2.865), (x + 0.13, -0.39, 2.92)],
        0.018, m["mouth"], True,
    )
    bone_parent(smile, "B_head")

    # Swept hair cap plus individually modeled locks, all original geometry.
    cap = ellipsoid("Deadpan swept hair cap", (x, 0.035, 3.34), (0.40, 0.35, 0.22), m["hair"], 36, True)
    bone_parent(cap, "B_head")
    locks = [
        [(-0.32, 0.00, 3.35), (-0.24, -0.15, 3.54), (-0.03, -0.17, 3.61)],
        [(-0.15, -0.01, 3.38), (-0.05, -0.18, 3.57), (0.20, -0.15, 3.58)],
        [(0.02, 0.00, 3.39), (0.15, -0.16, 3.52), (0.34, -0.11, 3.47)],
        [(0.18, 0.02, 3.35), (0.30, -0.10, 3.44), (0.39, -0.04, 3.37)],
    ]
    for i, pts in enumerate(locks):
        world_pts = [(x + px, py, pz) for px, py, pz in pts]
        lock = curve_tube(f"Deadpan swept lock {i}", world_pts, 0.055 - i * 0.006, m["hair_hi" if i % 2 else "hair"], True)
        bone_parent(lock, "B_head")


def make_materials():
    return {
        "skin_a": mat("Chaos warm skin", (0.43, 0.19, 0.115), roughness=0.52, subsurface=0.06, noise=True),
        "skin_a_hi": mat("Chaos nose highlight", (0.55, 0.255, 0.15), roughness=0.48, subsurface=0.05),
        "skin_b": mat("Deadpan warm skin", (0.66, 0.34, 0.20), roughness=0.50, subsurface=0.07, noise=True),
        "skin_b_hi": mat("Deadpan nose highlight", (0.78, 0.43, 0.26), roughness=0.47, subsurface=0.05),
        "skin_b_shadow": mat("Deadpan jaw warmth", (0.50, 0.235, 0.14), roughness=0.55, subsurface=0.04),
        "stubble": mat("Short dark stubble", (0.055, 0.035, 0.030), roughness=0.72, noise=True),
        "hair": mat("Deep brown hair", (0.055, 0.024, 0.012), roughness=0.36, noise=True),
        "hair_hi": mat("Brown hair glint", (0.14, 0.055, 0.020), roughness=0.31),
        "eye": mat("Warm eye white", (0.84, 0.87, 0.82), roughness=0.22),
        "pupil": mat("Dark hazel pupil", (0.025, 0.018, 0.012), roughness=0.16),
        "mouth": mat("Mouth dark", (0.075, 0.008, 0.006), roughness=0.42),
        "lip": mat("Natural lip", (0.34, 0.065, 0.055), roughness=0.44),
        "hoodie": mat("Electric blue hoodie", (0.025, 0.12, 0.34), roughness=0.68, noise=True),
        "hoodie_dark": mat("Blue ribbing", (0.012, 0.048, 0.14), roughness=0.71, noise=True),
        "jacket": mat("Black technical jacket", (0.012, 0.016, 0.020), roughness=0.46, noise=True),
        "jacket_hi": mat("Jacket edge", (0.035, 0.045, 0.055), roughness=0.38),
        "denim": mat("Dark blue denim", (0.018, 0.048, 0.085), roughness=0.76, noise=True),
        "polo": mat("Warm white polo", (0.72, 0.70, 0.64), roughness=0.66, noise=True),
        "polo_shadow": mat("Polo seam", (0.40, 0.39, 0.36), roughness=0.70),
        "trouser": mat("Charcoal trousers", (0.028, 0.032, 0.038), roughness=0.69, noise=True),
        "gold": mat("Fictional gold accent", (0.78, 0.42, 0.055), metallic=0.54, roughness=0.29),
        "button": mat("Pearl button", (0.93, 0.90, 0.78), roughness=0.24),
        "headphone": mat("Headphone black", (0.006, 0.008, 0.012), metallic=0.14, roughness=0.27),
        "headphone_hi": mat("Headphone gloss", (0.045, 0.055, 0.065), metallic=0.38, roughness=0.19),
        "zipper": mat("Brushed zipper", (0.24, 0.27, 0.30), metallic=0.83, roughness=0.25),
        "shoe": mat("Chaos sneakers", (0.016, 0.018, 0.022), roughness=0.47),
        "shoe_b": mat("Deadpan sneakers", (0.18, 0.15, 0.11), roughness=0.54),
        "sole": mat("Sneaker sole", (0.60, 0.59, 0.55), roughness=0.68),
    }


def key_bone(name, frame, rotation=None, location=None, scale=None):
    bone = RIG.pose.bones[name]
    bone.rotation_mode = "XYZ"
    if rotation is not None:
        bone.rotation_euler = rotation
        bone.keyframe_insert("rotation_euler", frame=frame)
    if location is not None:
        bone.location = location
        bone.keyframe_insert("location", frame=frame)
    if scale is not None:
        bone.scale = scale
        bone.keyframe_insert("scale", frame=frame)


def neutral(frame):
    animated = [
        "A_root", "A_pelvis", "A_spine", "A_neck", "A_head",
        "A_L_upperarm", "A_R_upperarm", "A_L_forearm", "A_R_forearm",
        "A_L_thigh", "A_R_thigh", "A_L_shin", "A_R_shin",
        "B_root", "B_pelvis", "B_spine", "B_neck", "B_head",
        "B_L_upperarm", "B_R_upperarm", "B_L_forearm", "B_R_forearm",
        "B_L_thigh", "B_R_thigh", "B_L_shin", "B_R_shin",
    ]
    for name in animated:
        key_bone(name, frame, (0, 0, 0), (0, 0, 0))


def animate():
    # Establish one synchronized action and hard anchors between beats.
    neutral(1)
    neutral(32)
    neutral(33)
    neutral(72)
    neutral(73)
    neutral(104)
    neutral(105)
    neutral(144)

    # Curious idle: Chaos scans eagerly; Deadpan offers economical side-eye.
    for frame, bob, tilt in ((1, 0.0, -0.06), (9, 0.055, 0.10), (17, 0.0, -0.11), (25, 0.045, 0.07), (32, 0.0, -0.06)):
        key_bone("A_root", frame, location=(0, bob, 0))
        key_bone("A_spine", frame, rotation=(0.02, 0, tilt * 0.45))
        key_bone("A_head", frame, rotation=(0.02, 0.10 * math.sin(frame * 0.3), tilt))
        key_bone("A_L_upperarm", frame, rotation=(0.05, 0, -tilt * 0.35))
        key_bone("A_R_upperarm", frame, rotation=(-0.04, 0, tilt * 0.35))
    for frame, bob, tilt in ((1, 0.0, 0.05), (12, 0.018, -0.06), (22, 0.0, 0.12), (32, 0.0, 0.05)):
        key_bone("B_root", frame, location=(0, bob, 0))
        key_bone("B_spine", frame, rotation=(-0.015, 0, -tilt * 0.22))
        key_bone("B_head", frame, rotation=(0.0, -0.08, tilt))

    # Swagger walk in place: strong Chaos swing, restrained Deadpan stride.
    for i, frame in enumerate((33, 43, 53, 63, 72)):
        phase = 1 if i % 2 == 0 else -1
        key_bone("A_root", frame, location=(0, 0.045 if i % 2 else 0.0, 0))
        key_bone("A_spine", frame, rotation=(0.05 * phase, 0, -0.07 * phase))
        key_bone("A_head", frame, rotation=(-0.03 * phase, 0, 0.06 * phase))
        key_bone("A_L_thigh", frame, rotation=(0.36 * phase, 0, 0))
        key_bone("A_R_thigh", frame, rotation=(-0.36 * phase, 0, 0))
        key_bone("A_L_shin", frame, rotation=(-0.22 * phase, 0, 0))
        key_bone("A_R_shin", frame, rotation=(0.22 * phase, 0, 0))
        key_bone("A_L_upperarm", frame, rotation=(-0.33 * phase, 0, 0.05))
        key_bone("A_R_upperarm", frame, rotation=(0.33 * phase, 0, -0.05))
        key_bone("B_root", frame, location=(0, 0.025 if i % 2 else 0.0, 0))
        key_bone("B_spine", frame, rotation=(-0.02 * phase, 0, 0.025 * phase))
        key_bone("B_head", frame, rotation=(0.02 * phase, 0, -0.025 * phase))
        key_bone("B_L_thigh", frame, rotation=(0.27 * phase, 0, 0))
        key_bone("B_R_thigh", frame, rotation=(-0.27 * phase, 0, 0))
        key_bone("B_L_upperarm", frame, rotation=(-0.24 * phase, 0, 0))
        key_bone("B_R_upperarm", frame, rotation=(0.24 * phase, 0, 0))

    # High-five: anticipation, asymmetric strike, contact, comic recoil.
    for frame in (73, 104):
        neutral(frame)
    key_bone("A_spine", 80, rotation=(0, 0, -0.16))
    key_bone("A_head", 80, rotation=(0, 0.1, 0.14))
    key_bone("B_spine", 80, rotation=(0, 0, 0.10))
    key_bone("B_head", 80, rotation=(0, -0.12, -0.08))
    # Inner arms use an asymmetric two-bone arc so the palms meet cleanly
    # above the shared center rather than crossing through the torsos.
    high_five_poses = {
        80: (-0.72, -0.18, 0.52, 0.34),
        88: (-1.72, -0.68, 1.18, 1.38),
        92: (-2.30, -1.08, 1.55, 2.07),
        96: (-1.90, -0.76, 1.30, 1.56),
        104: (0.0, 0.0, 0.0, 0.0),
    }
    for frame, (a_upper, a_fore, b_upper, b_fore) in high_five_poses.items():
        key_bone("A_R_upperarm", frame, rotation=(0.0, 0.0, a_upper))
        key_bone("A_R_forearm", frame, rotation=(0.0, 0.0, a_fore))
        key_bone("B_L_upperarm", frame, rotation=(0.0, 0.0, b_upper))
        key_bone("B_L_forearm", frame, rotation=(0.0, 0.0, b_fore))
    key_bone("A_root", 92, location=(0, 0.08, 0))
    key_bone("A_spine", 92, rotation=(0.02, 0, -0.24))
    key_bone("A_head", 92, rotation=(-0.05, 0.12, 0.18))
    key_bone("B_root", 92, location=(0, 0.025, 0))
    key_bone("B_spine", 92, rotation=(-0.01, 0, 0.16))
    key_bone("B_head", 92, rotation=(0.02, -0.1, -0.10))
    key_bone("A_root", 96, location=(0, -0.035, 0))
    key_bone("B_root", 96, location=(0, -0.018, 0))

    # Victory: Chaos over-celebrates while Deadpan performs a small shrug.
    for frame, lift, sway in ((105, 0.0, 0.0), (114, 0.08, -0.11), (124, 0.02, 0.12), (134, 0.07, -0.08), (144, 0.0, 0.0)):
        key_bone("A_root", frame, location=(0, lift, 0))
        key_bone("A_spine", frame, rotation=(-0.06, 0, sway))
        key_bone("A_head", frame, rotation=(0.02, 0, -sway * 1.3))
        key_bone("A_L_upperarm", frame, rotation=(0.0, 0.0, 2.35 + sway))
        key_bone("A_R_upperarm", frame, rotation=(0.0, 0.0, -2.35 + sway))
        key_bone("A_L_forearm", frame, rotation=(0.0, 0.0, -0.42))
        key_bone("A_R_forearm", frame, rotation=(0.0, 0.0, 0.42))
        key_bone("B_root", frame, location=(0, lift * 0.12, 0))
        key_bone("B_spine", frame, rotation=(0, 0, -sway * 0.18))
        key_bone("B_head", frame, rotation=(0.02, -0.10, 0.09 + sway * 0.15))
        key_bone("B_L_upperarm", frame, rotation=(0.0, 0.0, 0.72))
        key_bone("B_R_upperarm", frame, rotation=(0.0, 0.0, -0.72))
        key_bone("B_L_forearm", frame, rotation=(0.0, 0.0, -0.34))
        key_bone("B_R_forearm", frame, rotation=(0.0, 0.0, 0.34))

    if RIG.animation_data and RIG.animation_data.action:
        RIG.animation_data.action.name = "OddShift_Duo_Demo"
        for fcurve in RIG.animation_data.action.fcurves:
            for point in fcurve.keyframe_points:
                point.interpolation = "BEZIER"
                point.easing = "AUTO"
    for name, frame in (("CURIOUS_IDLE", 1), ("SWAGGER_WALK", 33), ("HIGH_FIVE", 73), ("VICTORY", 105)):
        marker = bpy.context.scene.timeline_markers.new(name, frame=frame)
        marker["clip_start"] = True


def make_stage():
    dark = mat("Stage midnight", (0.004, 0.007, 0.012), roughness=0.26, noise=True)
    curb = mat("Stage curb", (0.12, 0.14, 0.16), roughness=0.62, noise=True)
    cyan = mat("Stage cyan neon", (0.005, 0.25, 0.55), roughness=0.25,
               emission=(0.0, 0.35, 1.0), strength=5.5)
    amber = mat("Stage amber neon", (0.85, 0.31, 0.025), roughness=0.24,
                emission=(1.0, 0.22, 0.01), strength=5.0)
    glass = mat("Stage glass", (0.012, 0.025, 0.045), metallic=0.20, roughness=0.18)
    floor = box("Showcase wet sidewalk", (0, 0.35, -0.12), (9.0, 8.0, 0.24), dark, edge=0.08)
    floor["showcase_only"] = True
    wall = box("Showcase shop wall", (0, 2.25, 2.25), (9.0, 0.22, 4.7), glass, edge=0.08)
    wall["showcase_only"] = True
    # Window grid and curb make the poster read as a street rather than a void.
    for xx in (-3.2, -1.6, 0, 1.6, 3.2):
        box(f"Window mullion {xx}", (xx, 2.10, 2.30), (0.07, 0.10, 4.0), curb, edge=0.02)
    for zz in (0.55, 3.95):
        box(f"Window rail {zz}", (0, 2.10, zz), (7.6, 0.10, 0.07), curb, edge=0.02)
    box("Street curb", (0, -1.55, 0.04), (9.0, 0.50, 0.28), curb, edge=0.05)
    for x in (-3.25, 3.25):
        cylinder(f"Street bollard {x}", (x, -0.75, 0.52), 0.13, 1.05, curb, vertices=20)
        torus(f"Street bollard glow {x}", (x, -0.75, 0.80), 0.13, 0.025, cyan if x < 0 else amber)
    add_text("Odd Shift sign", "ODD SHIFT", (0, 2.02, 3.62), (math.radians(90), 0, 0), 0.62, cyan, 0.035)
    add_text("Duo sign", "TWO BRAINS. ONE PLAN. ZERO CHANCE.", (0, 2.01, 3.02), (math.radians(90), 0, 0), 0.16, amber, 0.012)
    # Directional sidewalk paint behind the characters.
    for i, x in enumerate((-2.6, -1.3, 0, 1.3, 2.6)):
        box(f"Sidewalk stripe {i}", (x, -1.05, 0.025), (0.74, 1.30, 0.025), mat(f"Stripe {i}", (0.24, 0.25, 0.24), roughness=0.72), edge=0.015)


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_camera_lights():
    scene = bpy.context.scene
    world = bpy.data.worlds.new("Odd Shift World") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.003, 0.006, 0.012, 1)
    bg.inputs["Strength"].default_value = 0.24

    cam_data = bpy.data.cameras.new("Odd Shift Camera")
    camera = bpy.data.objects.new("Odd Shift Camera", cam_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (4.7, -10.8, 4.15)
    cam_data.lens = 62
    look_at(camera, (0, 0, 1.70))
    scene.camera = camera

    def area(name, loc, color, energy, size, target=(0, 0, 1.8)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = loc
        look_at(obj, target)
        return obj

    area("Soft key", (-3.4, -4.5, 6.4), (1.0, 0.68, 0.48), 1100, 4.0)
    area("Cool rim", (-4.8, 1.6, 4.5), (0.04, 0.34, 1.0), 980, 3.0)
    area("Gold rim", (4.8, 0.9, 4.1), (1.0, 0.25, 0.035), 1050, 3.0)
    area("Face fill", (0.0, -5.4, 3.0), (0.62, 0.78, 1.0), 680, 3.5)
    area("Top edge", (0.0, 0.4, 7.2), (0.42, 0.55, 1.0), 850, 3.4)


def configure_scene(out_dir):
    scene = bpy.context.scene
    # Blender 4.2+ renamed the engine enum. Retain compatibility with the
    # runtime used by the historical delivery without embedding host paths.
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(out_dir / "Odd-Shift-Duo-Poster.png")
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = END
    scene.render.use_file_extension = True
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.look = "AgX - Medium High Contrast"
    if hasattr(scene, "eevee"):
        eevee = scene.eevee
        if hasattr(eevee, "taa_render_samples"):
            eevee.taa_render_samples = 48
        if hasattr(eevee, "use_gtao"):
            eevee.use_gtao = True
        if hasattr(eevee, "gtao_distance"):
            eevee.gtao_distance = 3
        if hasattr(eevee, "gtao_factor"):
            eevee.gtao_factor = 1.25
    scene["asset_title"] = "Odd Shift Duo"
    scene["asset_kind"] = "rigged animated game character duo"
    scene["source_reference_embedded"] = False
    scene["clip_manifest"] = "animation_manifest.json"


def export_glb(path):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in EXPORT_OBJECTS:
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = RIG
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
        export_materials="EXPORT",
        export_animations=True,
        export_frame_range=True,
        export_force_sampling=True,
        export_anim_slide_to_zero=True,
        export_def_bones=True,
    )


def _numbers(values):
    return [round(float(value), 8) for value in values]


def _state_digest(value):
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(body).hexdigest()


def _geometry_atom(obj):
    modifiers = []
    for modifier in obj.modifiers:
        record = {"type": modifier.type}
        for attribute in ("width", "segments", "levels", "render_levels"):
            if hasattr(modifier, attribute):
                value = getattr(modifier, attribute)
                record[attribute] = round(float(value), 8) if isinstance(value, float) else value
        modifiers.append(record)
    if obj.type == "MESH":
        payload = {
            "type": "MESH",
            "vertices": [_numbers(vertex.co) for vertex in obj.data.vertices],
            "polygons": [list(polygon.vertices) for polygon in obj.data.polygons],
            "modifiers": modifiers,
        }
    elif obj.type in {"CURVE", "FONT"}:
        splines = []
        for spline in obj.data.splines:
            if spline.type == "BEZIER":
                points = [_numbers(point.co) for point in spline.bezier_points]
            else:
                points = [_numbers(point.co) for point in spline.points]
            splines.append({"type": spline.type, "points": points, "cyclic": bool(spline.use_cyclic_u)})
        payload = {
            "type": obj.type,
            "body": obj.data.body if obj.type == "FONT" else None,
            "splines": splines,
            "bevel_depth": round(float(obj.data.bevel_depth), 8),
            "extrude": round(float(obj.data.extrude), 8),
            "modifiers": modifiers,
        }
    elif obj.type == "ARMATURE":
        payload = {
            "type": "ARMATURE",
            "bones": [{
                "head": _numbers(bone.head_local),
                "tail": _numbers(bone.tail_local),
                "parent": bone.parent.name if bone.parent else None,
            } for bone in sorted(obj.data.bones, key=lambda item: item.name)],
        }
    else:
        return None
    return _state_digest(payload)


def write_creation_state(path):
    """Preserve the editable parts and assembly state, not only realizations."""
    objects = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        objects.append({
            "name": obj.name,
            "type": obj.type,
            "role": obj.get("asset_role"),
            "exported": bool(obj.get("odd_shift_export")),
            "showcase_only": bool(obj.get("showcase_only")),
            "parent": obj.parent.name if obj.parent else None,
            "parent_type": obj.parent_type if obj.parent else None,
            "parent_bone": obj.parent_bone if obj.parent_type == "BONE" else None,
            "location": _numbers(obj.location),
            "rotation_euler": _numbers(obj.rotation_euler),
            "scale": _numbers(obj.scale),
            "dimensions": _numbers(obj.dimensions),
            "matrix_world": [round(float(value), 8) for row in obj.matrix_world for value in row],
            "materials": [slot.material.name for slot in obj.material_slots if slot.material],
            "geometry_atom": _geometry_atom(obj),
        })

    materials = []
    for material in sorted(bpy.data.materials, key=lambda item: item.name):
        bsdf = material.node_tree.nodes.get("Principled BSDF") if material.use_nodes else None
        values = {}
        if bsdf:
            for label in ("Base Color", "Metallic", "Roughness", "Subsurface Weight",
                          "Emission Color", "Emission", "Emission Strength"):
                socket = bsdf.inputs.get(label)
                if socket is None:
                    continue
                value = socket.default_value
                values[label] = _numbers(value) if hasattr(value, "__len__") else round(float(value), 8)
        node_types = sorted(node.bl_idname for node in material.node_tree.nodes) if material.use_nodes else []
        node_controls = []
        if material.use_nodes:
            for node in sorted(material.node_tree.nodes, key=lambda item: (item.bl_idname, item.name)):
                inputs = {}
                for socket in node.inputs:
                    if not hasattr(socket, "default_value"):
                        continue
                    value = socket.default_value
                    try:
                        inputs[socket.name] = (_numbers(value)
                                               if hasattr(value, "__len__") and not isinstance(value, str)
                                               else value if isinstance(value, (str, bool, int))
                                               else round(float(value), 8))
                    except (TypeError, ValueError):
                        continue
                node_controls.append({"type": node.bl_idname, "inputs": inputs})
        family_values = {key: value for key, value in values.items()
                         if key not in {"Base Color", "Emission Color", "Emission"}}
        family_nodes = [{"type": node["type"], "inputs": {
            key: value for key, value in node["inputs"].items()
            if key not in {"Base Color", "Emission Color", "Emission", "Color"}
        }} for node in node_controls]
        family_signature = _state_digest({"principled": family_values, "nodes": family_nodes})
        exact_signature = _state_digest({"principled": values, "nodes": node_controls})
        materials.append({
            "name": material.name,
            "principled": values,
            "node_types": node_types,
            "node_controls": node_controls,
            "material_family_atom": family_signature,
            "exact_appearance_variant": exact_signature,
        })

    bones = [{
        "name": bone.name,
        "parent": bone.parent.name if bone.parent else None,
        "head_local": _numbers(bone.head_local),
        "tail_local": _numbers(bone.tail_local),
        "use_deform": bool(bone.use_deform),
    } for bone in sorted(RIG.data.bones, key=lambda item: item.name)]

    action = RIG.animation_data.action if RIG.animation_data else None
    channels = []
    if action:
        for curve in action.fcurves:
            channels.append({
                "data_path": curve.data_path,
                "array_index": curve.array_index,
                "keyframes": [{
                    "frame": round(float(point.co[0]), 8),
                    "value": round(float(point.co[1]), 8),
                    "interpolation": point.interpolation,
                    "easing": point.easing,
                } for point in curve.keyframe_points],
            })

    geometry_atoms = []
    for signature in dict.fromkeys(item["geometry_atom"] for item in objects if item["geometry_atom"]):
        instances = [item["name"] for item in objects if item["geometry_atom"] == signature]
        geometry_atoms.append({
            "signature": signature,
            "canonical_object": instances[0],
            "instances": instances,
        })
    material_atoms = []
    for signature in dict.fromkeys(item["material_family_atom"] for item in materials):
        members = [item for item in materials if item["material_family_atom"] == signature]
        material_atoms.append({
            "signature": signature,
            "canonical_material": members[0]["name"],
            "materials": [item["name"] for item in members],
            "exact_variants": sorted({item["exact_appearance_variant"] for item in members}),
        })

    state = {
        "schema": "axm.avatar.creation-state/v1",
        "profile": "doll/odd-shift-duo@1",
        "authority": "EDITABLE_SOURCE_PARTS",
        "truth": (
            "This records the parts, material controls, hierarchy and authored motion used by the builder. "
            "Rendered images, movies and exported GLBs are secondary realizations."
        ),
        "construction": {
            "builder": "creator-parts/source/build_doll_v1.py",
            "primitive_symbols": ["box", "ellipsoid", "cylinder", "cone", "torus", "curve_tube", "cylinder_between", "add_text"],
            "assembly_symbols": ["create_rig", "make_chaos", "make_deadpan", "animate", "make_stage", "setup_camera_lights"],
        },
        "objects": objects,
        "materials": materials,
        "atom_library": {
            "deduplication": "GEOMETRY_AND_MATERIAL_FAMILY; COLOR_IS_OVERRIDE",
            "geometry_atoms": geometry_atoms,
            "material_family_atoms": material_atoms,
            "geometry_instances": sum(len(item["instances"]) for item in geometry_atoms),
            "deduplicated_geometry_instances": sum(len(item["instances"]) - 1 for item in geometry_atoms),
            "truth": "Names and material colors do not create new geometry atoms; exact appearances remain reproducible variants.",
        },
        "rig": {"name": RIG.name, "bones": bones, "deformation": "RIGID_BONE_PARENTING"},
        "animation": {"name": action.name if action else None, "channels": channels},
        "scene": {
            "fps": bpy.context.scene.render.fps,
            "frame_start": bpy.context.scene.frame_start,
            "frame_end": bpy.context.scene.frame_end,
            "camera": bpy.context.scene.camera.name if bpy.context.scene.camera else None,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def main():
    cfg = parse_args()
    out_dir = Path(cfg.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    reset_scene()
    configure_scene(out_dir)
    create_rig()
    materials = make_materials()
    make_chaos(materials)
    make_deadpan(materials)
    animate()
    make_stage()
    setup_camera_lights()

    scene = bpy.context.scene
    scene.frame_set(cfg.poster_frame)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "Odd-Shift-Duo.blend"))
    export_glb(out_dir / "Odd-Shift-Duo.glb")
    creation_state = write_creation_state(out_dir / "creator-parts" / "creation-state.json")
    # Restore the poster frame after export and save once more with clean selection.
    scene.frame_set(cfg.poster_frame)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "Odd-Shift-Duo.blend"))
    bpy.ops.render.render(write_still=True)

    stats = {
        "title": "Odd Shift Duo",
        "fps": FPS,
        "frame_start": 1,
        "frame_end": END,
        "export_object_count": len(EXPORT_OBJECTS),
        "mesh_count": sum(1 for obj in EXPORT_OBJECTS if obj.type == "MESH"),
        "curve_count": sum(1 for obj in EXPORT_OBJECTS if obj.type == "CURVE"),
        "armature_count": sum(1 for obj in EXPORT_OBJECTS if obj.type == "ARMATURE"),
        "bone_count": len(RIG.data.bones),
        "action": RIG.animation_data.action.name if RIG.animation_data and RIG.animation_data.action else None,
        "reference_embedded": False,
        "retained_creator_parts": {
            "objects": len(creation_state["objects"]),
            "materials": len(creation_state["materials"]),
            "bones": len(creation_state["rig"]["bones"]),
            "animation_channels": len(creation_state["animation"]["channels"]),
            "geometry_atoms": len(creation_state["atom_library"]["geometry_atoms"]),
            "material_family_atoms": len(creation_state["atom_library"]["material_family_atoms"]),
        },
    }
    (out_dir / "build_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print("ODD_SHIFT_BUILD_STATS", json.dumps(stats, sort_keys=True))


if __name__ == "__main__":
    main()
