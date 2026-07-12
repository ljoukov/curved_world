"""Generate Professor Bent as a rigged, animated Blender and GLB asset.

Run with:
    blender --background --python scripts/generate_professor_bent.py

The character is constructed entirely from Blender primitives and generated
meshes so the source remains reproducible and easy to art-direct.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "assets" / "professor-bent"
BLEND_PATH = OUTPUT_DIR / "professor-bent.blend"
GLB_PATH = OUTPUT_DIR / "professor-bent.glb"
PREVIEW_PATH = OUTPUT_DIR / "professor-bent-preview.png"


COLORS = {
    "teal": (0.09, 0.53, 0.56, 1.0),
    "teal_dark": (0.035, 0.24, 0.27, 1.0),
    "teal_light": (0.22, 0.70, 0.69, 1.0),
    "burgundy": (0.28, 0.035, 0.075, 1.0),
    "burgundy_light": (0.45, 0.07, 0.12, 1.0),
    "cream": (0.88, 0.79, 0.61, 1.0),
    "mint": (0.32, 0.67, 0.55, 1.0),
    "gold": (0.83, 0.46, 0.08, 1.0),
    "hair": (0.75, 0.80, 0.80, 1.0),
    "hair_highlight": (0.94, 0.94, 0.88, 1.0),
    "eye": (0.96, 0.90, 0.74, 1.0),
    "iris": (0.70, 0.30, 0.025, 1.0),
    "pupil": (0.025, 0.018, 0.012, 1.0),
    "mouth": (0.045, 0.012, 0.015, 1.0),
    "navy": (0.008, 0.025, 0.055, 1.0),
}


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights, bpy.data.armatures):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def material(name: str, color, *, metallic=0.0, roughness=0.5, coat=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
    return mat


def apply_material(obj, mat) -> None:
    if hasattr(obj.data, "materials"):
        obj.data.materials.append(mat)


def smooth(obj) -> None:
    if obj.type == "MESH":
        for polygon in obj.data.polygons:
            polygon.use_smooth = True


def ellipsoid(name, location, scale, mat, *, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, location=location
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth(obj)
    apply_material(obj, mat)
    return obj


def rounded_box(name, location, scale, mat, *, rotation=(0, 0, 0), bevel=0.12):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    modifier = obj.modifiers.new("Soft edges", "BEVEL")
    modifier.width = bevel
    modifier.segments = 3
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    smooth(obj)
    apply_material(obj, mat)
    return obj


def cylinder_between(name, start, end, radius, mat, *, vertices=24):
    start = Vector(start)
    end = Vector(end)
    delta = end - start
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=delta.length,
        location=(start + end) * 0.5,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth(obj)
    apply_material(obj, mat)
    return obj


def torus(name, location, major_radius, minor_radius, mat, *, rotation=(math.pi / 2, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=48,
        minor_segments=10,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    smooth(obj)
    apply_material(obj, mat)
    return obj


def curve_tube(name, points, radius, mat, *, cyclic=False):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 3
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    curve.resolution_u = 12
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coords in zip(spline.bezier_points, points):
        point.co = coords
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    apply_material(obj, mat)
    return obj


def crescent_horn(name, mat):
    """Create the distinctive tapered crescent as a swept cubic Bezier mesh."""
    p0 = Vector((-0.30, 0.12, 3.92))
    p1 = Vector((-1.45, 0.12, 5.45))
    p2 = Vector((0.20, 0.12, 6.55))
    p3 = Vector((1.62, 0.12, 5.30))
    rings = 34
    sides = 16
    vertices = []
    faces = []
    for i in range(rings):
        t = i / (rings - 1)
        omt = 1.0 - t
        point = omt**3 * p0 + 3 * omt**2 * t * p1 + 3 * omt * t**2 * p2 + t**3 * p3
        tangent = (
            3 * omt**2 * (p1 - p0)
            + 6 * omt * t * (p2 - p1)
            + 3 * t**2 * (p3 - p2)
        ).normalized()
        depth_axis = Vector((0, 1, 0))
        profile_axis = tangent.cross(depth_axis).normalized()
        # A soft, head-sized base tapers dramatically into the hooked tip.
        radius = 0.83 * (1.0 - t) ** 0.72 + 0.045
        depth_radius = radius * 0.76
        for side in range(sides):
            angle = 2 * math.pi * side / sides
            offset = depth_axis * (math.cos(angle) * depth_radius)
            offset += profile_axis * (math.sin(angle) * radius)
            vertices.append(tuple(point + offset))
    for ring in range(rings - 1):
        for side in range(sides):
            nxt = (side + 1) % sides
            a = ring * sides + side
            b = ring * sides + nxt
            c = (ring + 1) * sides + nxt
            d = (ring + 1) * sides + side
            faces.append((a, b, c, d))
    faces.append(tuple(range(sides - 1, -1, -1)))
    final_ring = (rings - 1) * sides
    faces.append(tuple(final_ring + i for i in range(sides)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    smooth(obj)
    apply_material(obj, mat)
    bevel = obj.modifiers.new("Crescent polish", "BEVEL")
    bevel.width = 0.025
    bevel.segments = 2
    return obj


def parent_to_bone(obj, rig, bone_name):
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world


def build_rig():
    armature = bpy.data.armatures.new("ProfessorBent_Rig")
    rig = bpy.data.objects.new("ProfessorBent_Rig", armature)
    bpy.context.collection.objects.link(rig)
    rig.show_in_front = True
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    specs = {
        "root": ((0, 0, 0.1), (0, 0, 0.8), None),
        "spine": ((0, 0, 0.75), (0, 0, 2.35), "root"),
        "neck": ((0, 0, 2.25), (0, 0, 2.80), "spine"),
        "head": ((0, 0, 2.72), (0, 0, 4.25), "neck"),
        "jaw": ((0, -0.67, 3.02), (0, -0.75, 2.72), "head"),
        "eye.L": ((-0.42, -0.76, 3.60), (-0.42, -0.84, 3.84), "head"),
        "eye.R": ((0.42, -0.76, 3.60), (0.42, -0.84, 3.84), "head"),
        "upper_arm.L": ((-0.85, 0, 2.15), (-1.55, -0.02, 1.90), "spine"),
        "forearm.L": ((-1.55, -0.02, 1.90), (-1.92, -0.18, 2.55), "upper_arm.L"),
        "hand.L": ((-1.92, -0.18, 2.55), (-1.98, -0.21, 3.08), "forearm.L"),
        "upper_arm.R": ((0.85, 0, 2.15), (1.48, -0.07, 1.78), "spine"),
        "forearm.R": ((1.48, -0.07, 1.78), (1.12, -0.38, 1.22), "upper_arm.R"),
        "hand.R": ((1.12, -0.38, 1.22), (0.68, -0.64, 1.35), "forearm.R"),
    }
    edit_bones = {}
    for name, (head, tail, parent) in specs.items():
        bone = armature.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        if parent:
            bone.parent = edit_bones[parent]
        edit_bones[name] = bone
    bpy.ops.object.mode_set(mode="POSE")
    for pose_bone in rig.pose.bones:
        pose_bone.rotation_mode = "XYZ"
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def build_character(rig):
    mats = {
        key: material(
            f"PB_{key}",
            color,
            metallic=0.72 if key == "gold" else 0.0,
            roughness=0.24 if key == "gold" else (0.31 if key == "teal" else 0.48),
            coat=0.25 if key == "teal" else 0.0,
        )
        for key, color in COLORS.items()
    }
    parts = {}

    # Academic coat and shirt.
    parts["Torso"] = ellipsoid("Torso", (0, 0.08, 1.35), (1.42, 0.70, 1.48), mats["burgundy"])
    parts["Shirt"] = ellipsoid("Shirt", (0, -0.66, 1.50), (0.55, 0.12, 0.92), mats["cream"])
    parts["Waistcoat"] = ellipsoid("Waistcoat", (0, -0.78, 1.13), (0.60, 0.10, 0.58), mats["teal_dark"])
    parts["Lapel.L"] = rounded_box("Lapel.L", (-0.53, -0.78, 1.72), (0.24, 0.08, 0.77), mats["burgundy_light"], rotation=(0.0, -0.35, -0.08), bevel=0.08)
    parts["Lapel.R"] = rounded_box("Lapel.R", (0.53, -0.78, 1.72), (0.24, 0.08, 0.77), mats["burgundy_light"], rotation=(0.0, 0.35, 0.08), bevel=0.08)
    parts["GoldTrim.L"] = curve_tube("GoldTrim.L", [(-0.82, -0.88, 2.38), (-0.63, -0.91, 1.73), (-0.23, -0.90, 1.08)], 0.025, mats["gold"])
    parts["GoldTrim.R"] = curve_tube("GoldTrim.R", [(0.82, -0.88, 2.38), (0.63, -0.91, 1.73), (0.23, -0.90, 1.08)], 0.025, mats["gold"])
    parts["Bow.L"] = ellipsoid("Bow.L", (-0.30, -0.98, 2.30), (0.38, 0.13, 0.25), mats["mint"])
    parts["Bow.R"] = ellipsoid("Bow.R", (0.30, -0.98, 2.30), (0.38, 0.13, 0.25), mats["mint"])
    parts["Bow.Knot"] = ellipsoid("Bow.Knot", (0, -1.04, 2.30), (0.18, 0.15, 0.19), mats["mint"])

    # Face, crescent silhouette, ears, and facial features.
    parts["Head"] = ellipsoid("Head", (0, 0, 3.45), (0.91, 0.72, 1.08), mats["teal"])
    parts["Crescent"] = crescent_horn("Crescent", mats["teal"])
    parts["Ear.L"] = ellipsoid("Ear.L", (-0.94, 0.00, 3.28), (0.26, 0.17, 0.39), mats["teal"])
    parts["Ear.R"] = ellipsoid("Ear.R", (0.94, 0.00, 3.28), (0.26, 0.17, 0.39), mats["teal"])
    parts["Nose"] = ellipsoid("Nose", (0, -0.80, 3.22), (0.25, 0.25, 0.37), mats["teal_light"])
    parts["Mouth"] = ellipsoid("Mouth", (0, -0.745, 2.84), (0.42, 0.09, 0.17), mats["mouth"])
    parts["LowerLip"] = curve_tube("LowerLip", [(-0.29, -0.83, 2.80), (0, -0.88, 2.72), (0.29, -0.83, 2.80)], 0.035, mats["teal_light"])

    for side, x in (("L", -0.42), ("R", 0.42)):
        eye_bone = f"eye.{side}"
        parts[f"EyeWhite.{side}"] = ellipsoid(f"EyeWhite.{side}", (x, -0.70, 3.58), (0.35, 0.13, 0.42), mats["eye"])
        parts[f"Iris.{side}"] = ellipsoid(f"Iris.{side}", (x, -0.835, 3.57), (0.15, 0.045, 0.18), mats["iris"], segments=24, rings=16)
        parts[f"Pupil.{side}"] = ellipsoid(f"Pupil.{side}", (x, -0.882, 3.57), (0.066, 0.025, 0.10), mats["pupil"], segments=20, rings=12)
        for key in (f"EyeWhite.{side}", f"Iris.{side}", f"Pupil.{side}"):
            parent_to_bone(parts[key], rig, eye_bone)
        parts[f"Glasses.{side}"] = torus(f"Glasses.{side}", (x, -0.90, 3.58), 0.48, 0.035, mats["gold"])

    parts["GlassesBridge"] = curve_tube("GlassesBridge", [(-0.08, -0.91, 3.62), (0, -0.97, 3.69), (0.08, -0.91, 3.62)], 0.028, mats["gold"])
    parts["GlassesArm.L"] = cylinder_between("GlassesArm.L", (-0.87, -0.89, 3.63), (-1.02, -0.18, 3.54), 0.026, mats["gold"], vertices=12)
    parts["GlassesArm.R"] = cylinder_between("GlassesArm.R", (0.87, -0.89, 3.63), (1.02, -0.18, 3.54), 0.026, mats["gold"], vertices=12)
    parts["Brow.L"] = curve_tube("Brow.L", [(-0.75, -0.76, 4.02), (-0.46, -0.88, 4.15), (-0.17, -0.77, 4.04)], 0.065, mats["hair_highlight"])
    parts["Brow.R"] = curve_tube("Brow.R", [(0.17, -0.77, 4.04), (0.46, -0.88, 4.15), (0.75, -0.76, 4.02)], 0.065, mats["hair_highlight"])

    # A readable mass of swept silver hair, with individual highlight strands.
    hair_paths = [
        [(-0.75, 0.05, 4.12), (-1.25, -0.05, 4.08), (-1.50, 0.02, 3.77)],
        [(-0.82, 0.12, 4.02), (-1.35, 0.08, 3.90), (-1.54, 0.18, 3.48)],
        [(0.64, 0.12, 4.23), (1.30, 0.02, 4.18), (1.66, 0.10, 3.93)],
        [(0.72, 0.19, 4.11), (1.42, 0.12, 3.97), (1.77, 0.25, 3.62)],
        [(0.75, 0.25, 3.98), (1.43, 0.27, 3.72), (1.63, 0.38, 3.33)],
        [(0.69, 0.30, 3.85), (1.28, 0.37, 3.47), (1.42, 0.41, 3.12)],
        [(0.55, 0.23, 4.32), (1.05, 0.11, 4.48), (1.49, 0.16, 4.33)],
    ]
    for index, path in enumerate(hair_paths):
        parts[f"Hair.{index:02d}"] = curve_tube(
            f"Hair.{index:02d}", path, 0.10 if index in (1, 3, 4) else 0.075,
            mats["hair"] if index % 2 else mats["hair_highlight"]
        )

    # Arms and readable gesturing hands. Left index points upward.
    limb_specs = {
        "UpperArm.L": ((-0.78, 0.02, 2.10), (-1.48, -0.05, 1.88), 0.28, "burgundy", "upper_arm.L"),
        "Forearm.L": ((-1.48, -0.05, 1.88), (-1.88, -0.20, 2.50), 0.24, "burgundy", "forearm.L"),
        "UpperArm.R": ((0.78, 0.02, 2.10), (1.44, -0.08, 1.76), 0.28, "burgundy", "upper_arm.R"),
        "Forearm.R": ((1.44, -0.08, 1.76), (1.08, -0.41, 1.24), 0.24, "burgundy", "forearm.R"),
    }
    for name, (start, end, radius, mat_name, bone) in limb_specs.items():
        parts[name] = cylinder_between(name, start, end, radius, mats[mat_name])
        parent_to_bone(parts[name], rig, bone)
    parts["Hand.L"] = ellipsoid("Hand.L", (-1.96, -0.24, 2.58), (0.27, 0.18, 0.34), mats["teal"])
    parts["Index.L"] = cylinder_between("Index.L", (-2.02, -0.25, 2.72), (-2.04, -0.25, 3.43), 0.085, mats["teal"], vertices=18)
    parts["IndexTip.L"] = ellipsoid("IndexTip.L", (-2.04, -0.25, 3.45), (0.085, 0.085, 0.11), mats["teal"], segments=20, rings=12)
    parts["Hand.R"] = ellipsoid("Hand.R", (0.86, -0.58, 1.33), (0.34, 0.18, 0.24), mats["teal"])
    finger_ends = [(0.52, -0.72, 1.43), (0.49, -0.72, 1.32), (0.54, -0.70, 1.22)]
    for index, end in enumerate(finger_ends):
        parts[f"Finger.R.{index}"] = cylinder_between(
            f"Finger.R.{index}", (0.82, -0.60, 1.35 - index * 0.04), end, 0.055, mats["teal"], vertices=14
        )
    for key in ("Hand.L", "Index.L", "IndexTip.L"):
        parent_to_bone(parts[key], rig, "hand.L")
    for key in ("Hand.R", "Finger.R.0", "Finger.R.1", "Finger.R.2"):
        parent_to_bone(parts[key], rig, "hand.R")

    # Parent all head and torso parts that were not assigned to specialist bones.
    head_prefixes = ("Head", "Crescent", "Ear", "Nose", "Glasses", "Brow", "Hair")
    for key, obj in parts.items():
        if obj.parent:
            continue
        if key == "Mouth" or key == "LowerLip":
            parent_to_bone(obj, rig, "jaw")
        elif key.startswith(head_prefixes):
            parent_to_bone(obj, rig, "head")
        else:
            parent_to_bone(obj, rig, "spine")

    return mats, parts


def reset_pose(rig):
    for bone in rig.pose.bones:
        bone.rotation_euler = (0, 0, 0)
        bone.location = (0, 0, 0)
        bone.scale = (1, 1, 1)


def key_bone(rig, bone_name, frame, *, rotation=None, location=None, scale=None):
    bone = rig.pose.bones[bone_name]
    if rotation is not None:
        bone.rotation_euler = rotation
        bone.keyframe_insert("rotation_euler", frame=frame, group=bone_name)
    if location is not None:
        bone.location = location
        bone.keyframe_insert("location", frame=frame, group=bone_name)
    if scale is not None:
        bone.scale = scale
        bone.keyframe_insert("scale", frame=frame, group=bone_name)


def create_action(rig, name, frame_end, keys):
    reset_pose(rig)
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    for key in keys:
        key_bone(rig, **key)
    # Blender 5's layered Actions no longer expose ``action.fcurves`` directly.
    # Keyframe insertion still creates the correct Action slots for export.
    if hasattr(action, "fcurves"):
        for fcurve in action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "BEZIER"
    if hasattr(action, "use_frame_range"):
        action.use_frame_range = True
        action.frame_start = 1
        action.frame_end = frame_end
    return action


def build_animations(rig):
    blink = [
        {"bone_name": side, "frame": frame, "scale": scale}
        for side in ("eye.L", "eye.R")
        for frame, scale in ((1, (1, 1, 1)), (18, (1, 1, 1)), (20, (1, 1, 0.08)), (22, (1, 1, 1)), (48, (1, 1, 1)))
    ]
    idle = create_action(rig, "Idle", 48, [
        {"bone_name": "spine", "frame": 1, "rotation": (0, 0, -0.025)},
        {"bone_name": "spine", "frame": 24, "rotation": (0.02, 0, 0.025)},
        {"bone_name": "spine", "frame": 48, "rotation": (0, 0, -0.025)},
        {"bone_name": "head", "frame": 1, "rotation": (0.0, -0.025, 0.03)},
        {"bone_name": "head", "frame": 24, "rotation": (-0.025, 0.03, -0.025)},
        {"bone_name": "head", "frame": 48, "rotation": (0.0, -0.025, 0.03)},
    ] + blink)

    talk_keys = []
    for frame, amount in ((1, 0.0), (5, 0.18), (9, 0.04), (13, 0.23), (17, 0.02), (21, 0.16), (25, 0.0)):
        talk_keys.append({"bone_name": "jaw", "frame": frame, "rotation": (amount, 0, 0)})
    talk_keys += [
        {"bone_name": "head", "frame": 1, "rotation": (0, 0, -0.04)},
        {"bone_name": "head", "frame": 13, "rotation": (-0.04, 0, 0.05)},
        {"bone_name": "head", "frame": 25, "rotation": (0, 0, -0.04)},
        {"bone_name": "hand.R", "frame": 1, "rotation": (0, 0.0, -0.05)},
        {"bone_name": "hand.R", "frame": 13, "rotation": (0.12, 0.04, 0.18)},
        {"bone_name": "hand.R", "frame": 25, "rotation": (0, 0.0, -0.05)},
    ]
    talk = create_action(rig, "Talk", 25, talk_keys)

    point = create_action(rig, "Point", 32, [
        {"bone_name": "head", "frame": 1, "rotation": (0, 0, 0)},
        {"bone_name": "head", "frame": 12, "rotation": (-0.05, -0.03, 0.12)},
        {"bone_name": "head", "frame": 32, "rotation": (0, 0, 0)},
        {"bone_name": "upper_arm.L", "frame": 1, "rotation": (0, 0, -0.12)},
        {"bone_name": "upper_arm.L", "frame": 12, "rotation": (0.0, -0.12, -0.34)},
        {"bone_name": "upper_arm.L", "frame": 32, "rotation": (0, 0, -0.12)},
        {"bone_name": "forearm.L", "frame": 1, "rotation": (0, 0, 0)},
        {"bone_name": "forearm.L", "frame": 12, "rotation": (0.05, 0.04, -0.10)},
        {"bone_name": "forearm.L", "frame": 32, "rotation": (0, 0, 0)},
        {"bone_name": "hand.L", "frame": 1, "rotation": (0, 0, 0)},
        {"bone_name": "hand.L", "frame": 12, "rotation": (0, -0.08, 0.09)},
        {"bone_name": "hand.L", "frame": 32, "rotation": (0, 0, 0)},
    ])

    think = create_action(rig, "Think", 40, [
        {"bone_name": "head", "frame": 1, "rotation": (0, 0, 0)},
        {"bone_name": "head", "frame": 18, "rotation": (-0.13, 0.12, -0.16)},
        {"bone_name": "head", "frame": 30, "rotation": (-0.10, 0.09, -0.13)},
        {"bone_name": "head", "frame": 40, "rotation": (0, 0, 0)},
        {"bone_name": "upper_arm.R", "frame": 1, "rotation": (0, 0, 0)},
        {"bone_name": "upper_arm.R", "frame": 18, "rotation": (0.18, -0.06, 0.26)},
        {"bone_name": "upper_arm.R", "frame": 40, "rotation": (0, 0, 0)},
        {"bone_name": "forearm.R", "frame": 1, "rotation": (0, 0, 0)},
        {"bone_name": "forearm.R", "frame": 18, "rotation": (-0.28, 0.10, 0.12)},
        {"bone_name": "forearm.R", "frame": 40, "rotation": (0, 0, 0)},
        {"bone_name": "eye.L", "frame": 16, "scale": (1, 1, 1)},
        {"bone_name": "eye.L", "frame": 18, "scale": (1, 1, 0.10)},
        {"bone_name": "eye.L", "frame": 20, "scale": (1, 1, 1)},
        {"bone_name": "eye.R", "frame": 16, "scale": (1, 1, 1)},
        {"bone_name": "eye.R", "frame": 18, "scale": (1, 1, 0.10)},
        {"bone_name": "eye.R", "frame": 20, "scale": (1, 1, 1)},
    ])
    rig.animation_data.action = point
    return {action.name: action for action in (idle, talk, point, think)}


def aim_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_stage(mats):
    # Render-only studio elements are excluded from the GLB via a dedicated collection.
    stage = bpy.data.collections.new("Preview_Stage")
    bpy.context.scene.collection.children.link(stage)

    def move_to_stage(obj):
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        stage.objects.link(obj)
        obj.hide_viewport = False

    floor = rounded_box("PreviewFloor", (0, 0.65, -0.12), (4.6, 3.2, 0.12), mats["teal_dark"], bevel=0.18)
    move_to_stage(floor)
    backdrop = rounded_box("PreviewBackdrop", (0, 2.25, 3.1), (4.6, 0.12, 3.3), mats["navy"], bevel=0.18)
    move_to_stage(backdrop)

    bpy.ops.object.camera_add(location=(0, -13.3, 3.75))
    camera = bpy.context.object
    camera.name = "PreviewCamera"
    camera.data.lens = 58
    aim_at(camera, (0, 0, 3.0))
    move_to_stage(camera)
    bpy.context.scene.camera = camera

    lights = [
        ("Key", "AREA", (-4.0, -5.0, 7.0), (0.40, 0.82, 1.0), 1100, 4.0),
        ("Fill", "AREA", (4.0, -3.0, 4.5), (1.0, 0.48, 0.30), 850, 3.0),
        ("Rim", "AREA", (1.8, 2.2, 6.0), (0.25, 1.0, 0.78), 1250, 2.5),
    ]
    for name, light_type, location, color, energy, size in lights:
        data = bpy.data.lights.new(name, light_type)
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        stage.objects.link(obj)
        obj.location = location
        aim_at(obj, (0, 0, 2.8))
    return stage


def configure_scene():
    scene = bpy.context.scene
    # Blender 5 exposes Eevee under the original engine identifier again.
    available_engines = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in available_engines else "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 700
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(PREVIEW_PATH)
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 48
    scene.world.color = COLORS["navy"][:3]
    scene.view_settings.look = "AgX - Medium High Contrast"


def export_glb(stage):
    # Select only the character. This keeps the camera, studio lights, floor, and
    # backdrop out of the web asset regardless of exporter visibility defaults.
    bpy.ops.object.select_all(action="DESELECT")
    stage_objects = set(stage.objects)
    for obj in bpy.context.scene.objects:
        if obj not in stage_objects:
            obj.select_set(True)
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    options = {
        "filepath": str(GLB_PATH),
        "export_format": "GLB",
        "use_selection": True,
        "export_animations": True,
        "export_cameras": False,
        "export_lights": False,
    }
    if "export_animation_mode" in props:
        options["export_animation_mode"] = "ACTIONS"
    elif "export_nla_strips" in props:
        options["export_nla_strips"] = False
        options["export_all_actions"] = True
    bpy.ops.export_scene.gltf(**options)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clear_scene()
    configure_scene()
    rig = build_rig()
    mats, _parts = build_character(rig)
    actions = build_animations(rig)
    stage = build_stage(mats)

    # Use the strongest silhouette from the pointing clip for the preview.
    rig.animation_data.action = actions["Point"]
    bpy.context.scene.frame_set(12)
    bpy.context.scene.render.filepath = str(PREVIEW_PATH)
    bpy.ops.render.render(write_still=True)

    export_glb(stage)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(f"Generated {BLEND_PATH}")
    print(f"Generated {GLB_PATH}")
    print(f"Rendered {PREVIEW_PATH}")


if __name__ == "__main__":
    main()
