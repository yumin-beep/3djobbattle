import bpy
import math


PREFIX = "BC3_"
COLLECTION = "BakerCat_Rebuild_v3"
OLD_CENTER_Z = 3.12
NEW_CENTER_Z = 2.82
Z_FACTOR = 0.86


def remap_z(value):
    return NEW_CENTER_Z + (value - OLD_CENTER_Z) * Z_FACTOR


def replace_profile_mesh(obj, profile, segments, xy_scale, mesh_name):
    old = obj.data
    sx, sy = xy_scale
    verts, faces = [], []
    for z, radius in profile:
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            verts.append((sx * radius * math.cos(angle), sy * radius * math.sin(angle), z))
    for ring in range(len(profile) - 1):
        a0 = ring * segments
        b0 = (ring + 1) * segments
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((a0 + i, a0 + j, b0 + j, b0 + i))
    faces.append(tuple(reversed(range(segments))))
    faces.append(tuple((len(profile) - 1) * segments + i for i in range(segments)))
    mesh = bpy.data.meshes.new(mesh_name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for mat in old.materials:
        mesh.materials.append(mat)
    obj.data = mesh
    if old.users == 0:
        bpy.data.meshes.remove(old)


def remap_mesh_vertices(obj, scale_x=1.0, scale_y=1.0):
    for vert in obj.data.vertices:
        vert.co.x *= scale_x
        vert.co.y *= scale_y
        vert.co.z = remap_z(vert.co.z)
    obj.data.update()


def remap_object_z(obj, old_z=None):
    obj.location.z = remap_z(obj.location.z if old_z is None else old_z)


def apply_stout_proportions():
    body = bpy.data.objects["BC3_Body_Capsule"]
    profile = [
        (-1.88, .78), (-1.79, .95), (-1.62, 1.0), (-1.35, 1.0),
        (1.32, 1.0), (1.55, .98), (1.73, .90), (1.88, .70),
    ]
    replace_profile_mesh(
        body, profile, 16, (1.43, 1.00),
        "BC3_Body_Capsule_Mesh_Stout_v9",
    )
    body.location.z = NEW_CENTER_Z
    body["shape_revision"] = "v9 stout rounded cylinder inspired by compact action-game proportions"
    body["dimensions_target"] = "2.86 x 2.00 x 3.76"

    apron = bpy.data.objects["BC3_Apron_Front"]
    if apron.get("stout_revision") != "v9":
        remap_mesh_vertices(apron, 1.065, 1.11)
        apron["stout_revision"] = "v9"
    band = bpy.data.objects["BC3_Apron_Waistband"]
    if band.get("stout_revision") != "v9":
        remap_mesh_vertices(band, 1.05, 1.08)
        band["stout_revision"] = "v9"
        band["design_rule"] = "continuous waistband fitted to stout body; rear bow only"

    pocket = bpy.data.objects.get("BC3_Apron_Pocket")
    if pocket:
        pocket.location.y = -1.08
        pocket.location.z = remap_z(1.82)
        pocket.scale.x = 1.14
        pocket.scale.z = .95

    for name, old_y, new_y, old_z in (
        ("BC3_Bow_Knot", .99, 1.10, 2.96),
        ("BC3_Bow_L", .99, 1.10, 2.96),
        ("BC3_Bow_R", .99, 1.10, 2.96),
        ("BC3_Ribbon_L", 1.01, 1.12, 2.55),
        ("BC3_Ribbon_R", 1.01, 1.12, 2.55),
    ):
        obj = bpy.data.objects.get(name)
        if obj:
            obj.location.y = new_y
            obj.location.z = remap_z(old_z)
            obj.scale.z = .90

    for name, old_z, new_y in (
        ("BC3_Eye_L", 4.10, -1.00),
        ("BC3_Eye_R", 4.10, -1.00),
        ("BC3_Nose", 3.77, -1.05),
    ):
        obj = bpy.data.objects.get(name)
        if obj:
            obj.location.z = remap_z(old_z)
            obj.location.y = new_y
    for obj in bpy.data.objects:
        if obj.name.startswith("BC3_Mouth_") or obj.name.startswith("BC3_Whisker_"):
            if obj.get("stout_revision") != "v9":
                for spline in obj.data.splines:
                    for bp in spline.bezier_points:
                        bp.co.z = remap_z(bp.co.z)
                        bp.co.y -= .09
                obj.location.y = 0.0
                obj["stout_revision"] = "v9"

    # Preserve the user's ear shapes and rotations; only follow the lowered body/hat assembly.
    for obj in bpy.data.objects:
        if obj.name.startswith("BC3_") and "Ear" in obj.name:
            obj.location.x *= 1.03
            obj.location.z -= .62
            obj["user_shape_preserved"] = True
            obj["v9_change"] = "translation only; rotation and scale preserved"

    hat_band = bpy.data.objects.get("BC3_Hat_Band")
    hat_puff = bpy.data.objects.get("BC3_Hat_Puff")
    if hat_band:
        hat_band.location.z -= .62
        hat_band.scale.x = 1.06
        hat_band.scale.y = 1.06
    if hat_puff:
        hat_puff.location.z -= .62
        hat_puff.scale.x = 1.08
        hat_puff.scale.y = 1.08
        hat_puff.scale.z = .92

    for side in ("L", "R"):
        leg = bpy.data.objects.get("BC3_Leg_" + side)
        foot = bpy.data.objects.get("BC3_Foot_" + side)
        if leg:
            leg.scale.x = 1.12
            leg.scale.y = 1.12
            leg.scale.z = .75
            leg.location.z = .70
        if foot:
            foot.scale.x = 1.08
            foot.scale.y = 1.08
            foot.scale.z = .92

    arm_points = {
        "BC3_Arm_L_UpperSupport": [
            (-1.28, -.16, remap_z(3.00)), (-1.52, -.72, remap_z(2.92)),
            (-1.18, -1.42, remap_z(3.18)), (-.68, -1.52, remap_z(3.55)),
        ],
        "BC3_Arm_R_LowerWrap": [
            (1.28, -.14, remap_z(3.28)), (1.54, -.72, remap_z(3.05)),
            (1.16, -1.44, remap_z(2.72)), (.58, -1.52, remap_z(2.48)),
        ],
    }
    for name, points in arm_points.items():
        obj = bpy.data.objects.get(name)
        if obj and obj.type == "CURVE":
            obj.data.bevel_depth = .105
            for bp, co in zip(obj.data.splines[0].bezier_points, points):
                bp.co = co

    baguette = bpy.data.objects.get("BC3_Baguette")
    if baguette:
        baguette.location.z = remap_z(3.10)
        baguette.scale = (.92, .92, .92)

    image = bpy.data.images.get("BC3_Baguette_Score_Texture")
    if image and not image.packed_file:
        image.pack()

    root = bpy.data.objects.get("BC3_ROOT_BakerCat")
    if root:
        root["style_revision"] = "v9 stout compact silhouette"


def save_render_export():
    scene = bpy.context.scene
    blend_path = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_stout_v9.blend"
    render_path = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_stout_v9_preview.png"
    glb_path = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_stout_v9.glb"
    scene.render.filepath = render_path
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    bpy.ops.render.render(write_still=True)
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    collection = bpy.data.collections[COLLECTION]
    for obj in collection.objects:
        if obj.type in {"MESH", "CURVE", "EMPTY"} and obj.name != "BC3_Ground":
            obj.hide_set(False)
            obj.select_set(True)
    root = bpy.data.objects.get("BC3_ROOT_BakerCat")
    if root:
        bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
    )
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    return {"blend": blend_path, "render": render_path, "glb": glb_path}

