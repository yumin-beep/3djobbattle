import bpy
import math
import os
from mathutils import Matrix, Vector


SOURCE_BLEND = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_round_xy_v12.blend"
OUT_BLEND = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_rigged.blend"
OUT_FBX = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_rigged.fbx"
OUT_PREVIEW = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Animations/char_baker_cat_rig_preview.png"
COLLECTION_NAME = "BakerCat_Rebuild_v3"
RIG_NAME = "BakerCat_Rig"
TARGET_HEIGHT = 1.6
FPS = 30


BODY_PART_EXCLUSIONS = {
    "BC3_Arm_L_UpperSupport",
    "BC3_Arm_R_LowerWrap",
    "BC3_Baguette",
    "BC3_Leg_L", "BC3_Foot_L",
    "BC3_Leg_R", "BC3_Foot_R",
}


def character_objects():
    collection = bpy.data.collections[COLLECTION_NAME]
    return [
        obj for obj in collection.all_objects
        if obj.type in {"MESH", "CURVE"} and obj.name != "BC3_Ground"
    ]


def clean_legacy_scene_data():
    """Keep only the BC3 character generation in the rigged deliverable."""
    warm_white = bpy.data.materials.get("BC3_Mat_Warm_White")
    hat_puff = bpy.data.objects.get("BC3_Hat_Puff")
    if warm_white is None or hat_puff is None:
        raise RuntimeError("BC3_Hat_Puff or BC3_Mat_Warm_White is missing")

    hat_puff.data.materials.clear()
    hat_puff.data.materials.append(warm_white)

    legacy_material = bpy.data.materials.get("MAT_char_baker_cat_palette")
    remove_objects = []
    for obj in bpy.data.objects:
        uses_legacy_palette = any(
            slot.material == legacy_material for slot in obj.material_slots
        )
        is_ground = "ground" in obj.name.lower()
        if uses_legacy_palette or is_ground:
            remove_objects.append(obj)

    for obj in remove_objects:
        bpy.data.objects.remove(obj, do_unlink=True)

    legacy_root = bpy.data.objects.get("ROOT_char_baker_cat")
    if legacy_root is not None and not legacy_root.children:
        bpy.data.objects.remove(legacy_root, do_unlink=True)

    legacy_collection = bpy.data.collections.get("CHARACTER_char_baker_cat")
    if legacy_collection is not None and not legacy_collection.objects:
        bpy.data.collections.remove(legacy_collection)

    removable_material_names = {"MAT_char_baker_cat_palette", "BC3_Mat_Ground"}
    for mesh in list(bpy.data.meshes):
        if mesh.users != 0:
            continue
        mesh_material_names = {mat.name for mat in mesh.materials if mat is not None}
        if mesh_material_names & removable_material_names:
            bpy.data.meshes.remove(mesh)

    for material_name in ("MAT_char_baker_cat_palette", "BC3_Mat_Ground"):
        material = bpy.data.materials.get(material_name)
        if material is not None and material.users == 0:
            bpy.data.materials.remove(material)

    return [obj.name for obj in remove_objects]


def world_bbox(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    mins = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    maxs = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return mins, maxs


def unparent_keep_world(obj):
    world = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world


def scale_character_to_meters(objects):
    before_min, before_max = world_bbox(objects)
    source_height = before_max.z - before_min.z
    factor = TARGET_HEIGHT / source_height
    transform = Matrix.Translation((0.0, 0.0, -before_min.z * factor)) @ Matrix.Scale(factor, 4)

    for obj in objects:
        unparent_keep_world(obj)
        obj.matrix_world = transform @ obj.matrix_world

    # Bake the uniform scale into each part while preserving rotation and shape.
    for obj in objects:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.select_all(action="DESELECT")

    after_min, after_max = world_bbox(objects)
    return factor, before_min, before_max, after_min, after_max


def curve_endpoint_world(obj, index):
    spline = obj.data.splines[0]
    if spline.type == "BEZIER":
        co = spline.bezier_points[index].co
    else:
        co = spline.points[index].co.xyz
    return obj.matrix_world @ co


def object_top_center(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return Vector((
        sum(p.x for p in points) / len(points),
        sum(p.y for p in points) / len(points),
        max(p.z for p in points),
    ))


def convert_curves_to_mesh(objects):
    converted = []
    for obj in list(objects):
        if obj.type != "CURVE":
            converted.append(obj)
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
        converted.append(bpy.context.view_layer.objects.active)
    bpy.ops.object.select_all(action="DESELECT")
    return converted


def create_rig(body_bottom, arm_l_head, arm_r_head, leg_l_head, leg_r_head, prop_head):
    arm_data = bpy.data.armatures.new(RIG_NAME + "_Data")
    arm_obj = bpy.data.objects.new(RIG_NAME, arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    arm_obj.show_in_front = True
    arm_obj.data.display_type = "OCTAHEDRAL"
    arm_obj["source_spec"] = "발주-char_baker_cat-rev3-리깅애니메이션.md"
    arm_obj["bone_count_note"] = "Specification says 8, but exact named hierarchy contains 7 bones; named hierarchy followed"
    arm_obj["frozen_ear_state"] = "L/R x +/-1.05, y -0.60, z 5.56, rotY +/-23deg, scale 1.5/1.5/1.0 before uniform meter conversion"

    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    def add_bone(name, head, length=0.16, parent=None, deform=True):
        bone = arm_data.edit_bones.new(name)
        bone.head = head
        bone.tail = Vector(head) + Vector((0.0, length, 0.0))
        bone.parent = parent
        bone.use_connect = False
        bone.use_deform = deform
        return bone

    root = add_bone("root", (0.0, 0.0, 0.0), length=0.12, deform=False)
    body = add_bone("body", body_bottom, length=0.24, parent=root)
    arm_l = add_bone("arm.L", arm_l_head, length=0.14, parent=body)
    arm_r = add_bone("arm.R", arm_r_head, length=0.14, parent=body)
    add_bone("prop", prop_head, length=0.12, parent=arm_r)
    add_bone("leg.L", leg_l_head, length=0.12, parent=body)
    add_bone("leg.R", leg_r_head, length=0.12, parent=body)

    bpy.ops.object.mode_set(mode="POSE")
    for pose_bone in arm_obj.pose.bones:
        pose_bone.rotation_mode = "XYZ"
    bpy.ops.object.mode_set(mode="OBJECT")
    arm_obj.select_set(False)
    return arm_obj


def assigned_bone_for_object(obj):
    if obj.name == "BC3_Arm_L_UpperSupport":
        return "arm.L"
    if obj.name == "BC3_Arm_R_LowerWrap":
        return "arm.R"
    if obj.name == "BC3_Baguette":
        return "prop"
    if obj.name in {"BC3_Leg_L", "BC3_Foot_L"}:
        return "leg.L"
    if obj.name in {"BC3_Leg_R", "BC3_Foot_R"}:
        return "leg.R"
    return "body"


def rigid_bind(objects, arm_obj):
    assignments = {}
    for obj in objects:
        if obj.type != "MESH":
            continue
        bone_name = assigned_bone_for_object(obj)
        obj.parent = None
        for modifier in list(obj.modifiers):
            if modifier.type == "ARMATURE":
                obj.modifiers.remove(modifier)
        obj.vertex_groups.clear()
        group = obj.vertex_groups.new(name=bone_name)
        group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
        modifier = obj.modifiers.new(name="Rigid_Armature", type="ARMATURE")
        modifier.object = arm_obj
        modifier.use_vertex_groups = True
        modifier.use_bone_envelopes = False
        obj["rigid_bone"] = bone_name
        obj["rigid_weight"] = 1.0
        assignments[obj.name] = bone_name
    return assignments


def reset_pose(arm_obj):
    for pb in arm_obj.pose.bones:
        pb.location = (0.0, 0.0, 0.0)
        pb.rotation_euler = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)


def key_pose(pb, frame, location=None, rotation=None):
    if location is not None:
        pb.location = location
        pb.keyframe_insert(data_path="location", frame=frame, group=pb.name)
    if rotation is not None:
        pb.rotation_euler = rotation
        pb.keyframe_insert(data_path="rotation_euler", frame=frame, group=pb.name)


def key_static_bones(arm_obj, bone_names, frames):
    for bone_name in bone_names:
        pb = arm_obj.pose.bones[bone_name]
        for frame in frames:
            key_pose(pb, frame, location=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0))


def action_fcurves(action):
    # Blender 5.x stores F-curves in layered Action channel bags.
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in strip.channelbags:
                for fcurve in channelbag.fcurves:
                    yield fcurve


def set_interpolation(action, interpolation):
    for fcurve in action_fcurves(action):
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = interpolation


def begin_action(arm_obj, name):
    reset_pose(arm_obj)
    action = bpy.data.actions.get(name) or bpy.data.actions.new(name=name)
    arm_obj.animation_data_create()
    arm_obj.animation_data.action = action
    return action


def finish_action(arm_obj, action, frame_end, loop=False):
    action.frame_start = 1
    action.frame_end = frame_end
    set_interpolation(action, "BEZIER")
    if loop:
        for fcurve in action_fcurves(action):
            modifier = fcurve.modifiers.new(type="CYCLES")
            modifier.mode_before = "REPEAT"
            modifier.mode_after = "REPEAT"
    arm_obj.animation_data.action = None


def build_idle(arm_obj):
    action = begin_action(arm_obj, "Idle")
    body = arm_obj.pose.bones["body"]
    arm_l = arm_obj.pose.bones["arm.L"]
    arm_r = arm_obj.pose.bones["arm.R"]
    frames = (1, 12, 23, 34, 45)
    z_values = (0.0, 0.02, 0.0, -0.02, 0.0)
    roll = (0.0, math.radians(1.5), 0.0, math.radians(-1.5), 0.0)
    swing = (0.0, math.radians(3.0), 0.0, math.radians(-3.0), 0.0)
    for frame, z, ry, arm_x in zip(frames, z_values, roll, swing):
        key_pose(body, frame, location=(0.0, 0.0, z), rotation=(0.0, ry, 0.0))
        key_pose(arm_l, frame, rotation=(arm_x, 0.0, 0.0))
        key_pose(arm_r, frame, rotation=(-arm_x * 0.7, 0.0, 0.0))
    key_static_bones(arm_obj, ("leg.L", "leg.R", "prop"), (1, 45))
    finish_action(arm_obj, action, 45, loop=True)
    return action


def build_run(arm_obj):
    action = begin_action(arm_obj, "Run")
    body = arm_obj.pose.bones["body"]
    arm_l = arm_obj.pose.bones["arm.L"]
    arm_r = arm_obj.pose.bones["arm.R"]
    leg_l = arm_obj.pose.bones["leg.L"]
    leg_r = arm_obj.pose.bones["leg.R"]
    frames = (1, 5, 9, 14, 18)
    phase = (1.0, 0.0, -1.0, 0.0, 1.0)
    bounce = (-0.04, 0.04, -0.04, 0.04, -0.04)
    for frame, p, z in zip(frames, phase, bounce):
        key_pose(body, frame, location=(0.0, 0.0, z), rotation=(math.radians(8.0), math.radians(3.0 * p), 0.0))
        key_pose(leg_l, frame, rotation=(math.radians(35.0 * p), 0.0, 0.0))
        key_pose(leg_r, frame, rotation=(math.radians(-35.0 * p), 0.0, 0.0))
        key_pose(arm_l, frame, rotation=(math.radians(-25.0 * p), 0.0, 0.0))
        key_pose(arm_r, frame, rotation=(math.radians(15.0 * p), 0.0, 0.0))
    key_static_bones(arm_obj, ("prop",), (1, 18))
    finish_action(arm_obj, action, 18, loop=True)
    return action


def build_defend(arm_obj):
    # Preserve the previous front-facing baguette motion as a defensive block.
    action = begin_action(arm_obj, "Defend")
    body = arm_obj.pose.bones["body"]
    arm_r = arm_obj.pose.bones["arm.R"]
    prop = arm_obj.pose.bones["prop"]
    poses = {
        1:  (0.0, 0.0, 0.0),
        4:  (50.0, 10.0, -5.0),
        5:  (50.0, 10.0, -5.0),
        7:  (0.0, 0.0, 5.0),
        8:  (-50.0, -10.0, 10.0),
        12: (0.0, 0.0, 0.0),
    }
    for frame, (arm_deg, prop_deg, yaw_deg) in poses.items():
        # Rotate around the character's front axis (Y), keeping the baguette's
        # 120-degree attack arc clearly readable in the front plane.
        key_pose(arm_r, frame, rotation=(0.0, math.radians(arm_deg), 0.0))
        key_pose(prop, frame, rotation=(0.0, math.radians(prop_deg), 0.0))
        key_pose(body, frame, location=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, math.radians(yaw_deg)))
    key_static_bones(arm_obj, ("arm.L", "leg.L", "leg.R"), (1, 12))
    finish_action(arm_obj, action, 12, loop=False)
    return action


def build_attack(arm_obj):
    action = begin_action(arm_obj, "Attack")
    body = arm_obj.pose.bones["body"]
    arm_l = arm_obj.pose.bones["arm.L"]
    arm_r = arm_obj.pose.bones["arm.R"]
    prop = arm_obj.pose.bones["prop"]

    # A bat/sword-like diagonal slash: load the baguette over the right shoulder,
    # cut through the opposite diagonal quickly, then follow through and recover.
    poses = {
        # frame: armY, propY, leanX, rollY, yawZ, forwardY, downZ, counterArmY
        1:  (0.0,   0.0,  0.0,  0.0,   0.0,  0.00,  0.00,  0.0),
        3:  (35.0, 10.0, -2.0, -2.0,  -6.0,  0.01,  0.00, -8.0),
        4:  (45.0, 15.0, -4.0, -4.0, -12.0,  0.02,  0.01, -12.0),
        5:  (45.0, 15.0, -4.0, -4.0, -12.0,  0.02,  0.01, -12.0),
        6:  (10.0,  0.0,  2.0,  0.0,   0.0, -0.01,  0.00,  0.0),
        7:  (-40.0,-10.0, 7.0,  4.0,  12.0, -0.03, -0.01, 10.0),
        8:  (-75.0,-15.0, 8.0,  5.0,  16.0, -0.04, -0.02, 14.0),
        9:  (-80.0,-15.0, 6.0,  3.0,  12.0, -0.03, -0.01,  8.0),
        10: (-40.0,-10.0, 3.0,  1.5,   6.0, -0.01,  0.00,  3.0),
        12: (0.0,   0.0,  0.0,  0.0,   0.0,  0.00,  0.00,  0.0),
    }
    for frame, values in poses.items():
        arm_y, prop_y, lean_x, roll_y, yaw_z, move_y, move_z, counter_y = values
        key_pose(arm_r, frame, rotation=(0.0, math.radians(arm_y), 0.0))
        key_pose(prop, frame, rotation=(0.0, math.radians(prop_y), 0.0))
        key_pose(arm_l, frame, rotation=(0.0, math.radians(counter_y), 0.0))
        key_pose(
            body,
            frame,
            location=(0.0, move_y, move_z),
            rotation=(math.radians(lean_x), math.radians(roll_y), math.radians(yaw_z)),
        )
    key_static_bones(arm_obj, ("leg.L", "leg.R"), (1, 12))
    finish_action(arm_obj, action, 12, loop=False)
    return action


def stash_actions(arm_obj, actions):
    arm_obj.animation_data_create()
    for track in list(arm_obj.animation_data.nla_tracks):
        arm_obj.animation_data.nla_tracks.remove(track)
    for action in actions:
        track = arm_obj.animation_data.nla_tracks.new()
        track.name = action.name
        strip = track.strips.new(action.name, 1, action)
        strip.action_frame_start = 1
        strip.action_frame_end = action.frame_end
        track.mute = True
    arm_obj.animation_data.action = None


def configure_scene_and_camera(character):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.fps = FPS
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.frame_start = 1
    scene.frame_end = 45

    camera = scene.camera
    camera.location = (1.00, -3.35, 1.34)
    target = Vector((0.0, 0.0, 0.78))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.05
    camera.data.lens = 52

    for name, location, energy, size in (
        ("Key_Light", (2.4, -3.0, 3.2), 650.0, 3.0),
        ("Fill_Light", (-2.4, -1.8, 2.2), 420.0, 2.5),
    ):
        light = bpy.data.objects.get(name)
        if light and light.type == "LIGHT":
            light.location = location
            light.data.energy = energy
            if hasattr(light.data, "shape"):
                light.data.shape = "DISK"
            if hasattr(light.data, "size"):
                light.data.size = size

    world = scene.world
    if world:
        world.color = (0.04, 0.04, 0.04)


def select_for_export(objects, arm_obj):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        if obj.type == "MESH":
            obj.hide_set(False)
            obj.hide_render = False
            obj.select_set(True)
    arm_obj.hide_set(False)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj


def export_fbx(objects, arm_obj):
    arm_obj.animation_data.action = None
    for track in arm_obj.animation_data.nla_tracks:
        track.mute = False
    select_for_export(objects, arm_obj)
    bpy.ops.export_scene.fbx(
        filepath=OUT_FBX,
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        axis_forward="-Z",
        axis_up="Y",
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        use_space_transform=True,
        add_leaf_bones=False,
        primary_bone_axis="Y",
        secondary_bone_axis="X",
        use_armature_deform_only=True,
        bake_anim=True,
        bake_anim_use_all_bones=False,
        bake_anim_use_nla_strips=True,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=False,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
        path_mode="COPY",
        embed_textures=True,
    )
    for track in arm_obj.animation_data.nla_tracks:
        track.mute = True


def render_preview(scene, arm_obj, action):
    os.makedirs(os.path.dirname(OUT_PREVIEW), exist_ok=True)
    for track in arm_obj.animation_data.nla_tracks:
        track.mute = True
    arm_obj.animation_data.action = action
    scene.frame_set(1)
    scene.render.filepath = OUT_PREVIEW
    bpy.ops.render.render(write_still=True)
    arm_obj.animation_data.action = None


def validate_rig(objects, arm_obj, actions, after_min, after_max, assignments):
    bones = [bone.name for bone in arm_obj.data.bones]
    hierarchy = {bone.name: bone.parent.name if bone.parent else None for bone in arm_obj.data.bones}
    weight_errors = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        bone_name = assignments[obj.name]
        group = obj.vertex_groups.get(bone_name)
        if not group:
            weight_errors.append(obj.name + ":missing_group")
            continue
        for vert in obj.data.vertices:
            weights = [g.weight for g in vert.groups if g.group == group.index]
            if len(weights) != 1 or abs(weights[0] - 1.0) > 1e-6:
                weight_errors.append(obj.name + ":bad_weight")
                break
    root_keyframes = []
    loop_checks = {}
    for action in actions:
        curves = list(action_fcurves(action))
        for fcurve in curves:
            if 'pose.bones["root"]' in fcurve.data_path:
                root_keyframes.append((action.name, fcurve.data_path))
        if action.name in {"Idle", "Run"}:
            first, last = 1, int(action.frame_end)
            diffs = []
            for fcurve in curves:
                diffs.append(abs(fcurve.evaluate(first) - fcurve.evaluate(last)))
            loop_checks[action.name] = max(diffs) if diffs else 0.0
    return {
        "bones": bones,
        "bone_count": len(bones),
        "hierarchy": hierarchy,
        "height_m": round(after_max.z - after_min.z, 6),
        "bbox_min_z": round(after_min.z, 6),
        "weight_errors": weight_errors,
        "root_keyframes": root_keyframes,
        "loop_max_difference": loop_checks,
        "actions": {a.name: [int(a.frame_start), int(a.frame_end)] for a in actions},
        "nla_tracks": [t.name for t in arm_obj.animation_data.nla_tracks],
    }


def main():
    if bpy.data.filepath != SOURCE_BLEND:
        raise RuntimeError("Open the final user-saved v12 model before running this script")

    os.makedirs(os.path.dirname(OUT_PREVIEW), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    removed_legacy_objects = clean_legacy_scene_data()
    scene = bpy.context.scene
    scene.tool_settings.use_keyframe_insert_auto = False

    objects = character_objects()
    factor, before_min, before_max, after_min, after_max = scale_character_to_meters(objects)

    # Capture pivots while the original arm curves still expose authored control points.
    arm_l_curve = bpy.data.objects["BC3_Arm_L_UpperSupport"]
    arm_r_curve = bpy.data.objects["BC3_Arm_R_LowerWrap"]
    arm_l_head = curve_endpoint_world(arm_l_curve, 0)
    arm_r_head = curve_endpoint_world(arm_r_curve, 0)
    prop_head = curve_endpoint_world(arm_r_curve, -1)
    leg_l_head = object_top_center(bpy.data.objects["BC3_Leg_L"])
    leg_r_head = object_top_center(bpy.data.objects["BC3_Leg_R"])
    body_obj = bpy.data.objects["BC3_Body_Capsule"]
    body_points = [body_obj.matrix_world @ Vector(c) for c in body_obj.bound_box]
    body_bottom = Vector((0.0, 0.0, min(p.z for p in body_points)))

    objects = convert_curves_to_mesh(objects)
    arm_obj = create_rig(body_bottom, arm_l_head, arm_r_head, leg_l_head, leg_r_head, prop_head)
    assignments = rigid_bind(objects, arm_obj)

    idle = build_idle(arm_obj)
    run = build_run(arm_obj)
    attack = build_attack(arm_obj)
    defend = build_defend(arm_obj)
    actions = [idle, run, attack, defend]
    stash_actions(arm_obj, actions)
    configure_scene_and_camera(objects)

    report = validate_rig(objects, arm_obj, actions, after_min, after_max, assignments)
    arm_obj["validation_report"] = str(report)
    arm_obj["uniform_scale_factor"] = factor
    arm_obj["source_height"] = before_max.z - before_min.z
    arm_obj["target_height"] = TARGET_HEIGHT

    render_preview(scene, arm_obj, idle)
    export_fbx(objects, arm_obj)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

    print({
        "done": True,
        "blend": OUT_BLEND,
        "fbx": OUT_FBX,
        "preview": OUT_PREVIEW,
        "removed_legacy_objects": removed_legacy_objects,
        "scale_factor": factor,
        "validation": report,
    })


main()
