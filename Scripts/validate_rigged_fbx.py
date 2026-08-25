import bpy
import json
from mathutils import Vector


FBX_PATH = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_rigged.fbx"


def action_fcurves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                yield from channelbag.fcurves


bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
    for datablock in list(datablocks):
        if datablock.users == 0:
            datablocks.remove(datablock)

bpy.ops.import_scene.fbx(filepath=FBX_PATH)

armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
armature = armatures[0] if armatures else None

if armature:
    armature.data.pose_position = "REST"
    if armature.animation_data:
        armature.animation_data.action = None
        for track in armature.animation_data.nla_tracks:
            track.mute = True
bpy.context.view_layer.update()

points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
mins = [min(p[i] for p in points) for i in range(3)] if points else [0.0, 0.0, 0.0]
maxs = [max(p[i] for p in points) for i in range(3)] if points else [0.0, 0.0, 0.0]

actions = {}
root_keyframes = []
root_curve_ranges = []
for action in bpy.data.actions:
    curves = list(action_fcurves(action))
    keyframes = [point.co.x for fcurve in curves for point in fcurve.keyframe_points]
    actions[action.name] = {
        "frame_start": int(round(min(keyframes))) if keyframes else 0,
        "frame_end": int(round(max(keyframes))) if keyframes else 0,
        "fcurves": len(curves),
    }
    for fcurve in curves:
        if 'pose.bones["root"]' in fcurve.data_path:
            root_keyframes.append((action.name, fcurve.data_path))
            values = [point.co.y for point in fcurve.keyframe_points]
            root_curve_ranges.append({
                "action": action.name,
                "path": fcurve.data_path,
                "index": fcurve.array_index,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
            })

mesh_bounds = []
for obj in meshes:
    obj_points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    mesh_bounds.append({
        "name": obj.name,
        "min_z": round(min(p.z for p in obj_points), 6),
        "max_z": round(max(p.z for p in obj_points), 6),
    })

report = {
    "armature_count": len(armatures),
    "mesh_count": len(meshes),
    "height_m": round(maxs[2] - mins[2], 6),
    "bbox_min_z": round(mins[2], 6),
    "actions": actions,
    "root_keyframes": root_keyframes,
    "root_curve_ranges": root_curve_ranges,
    "lowest_meshes": sorted(mesh_bounds, key=lambda row: row["min_z"])[:5],
    "bones": [bone.name for bone in armature.data.bones] if armature else [],
    "hierarchy": {
        bone.name: bone.parent.name if bone.parent else None
        for bone in armature.data.bones
    } if armature else {},
    "hat_puff_materials": [
        slot.material.name for slot in bpy.data.objects["BC3_Hat_Puff"].material_slots
        if slot.material is not None
    ] if "BC3_Hat_Puff" in bpy.data.objects else [],
    "ground_objects": [obj.name for obj in bpy.data.objects if "ground" in obj.name.lower()],
    "legacy_palette_users": [
        obj.name for obj in bpy.data.objects
        if any(
            slot.material is not None and slot.material.name == "MAT_char_baker_cat_palette"
            for slot in obj.material_slots
        )
    ],
}

print("FBX_VALIDATION_JSON=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
