import bpy


BODY_NAME = "BC3_Body_Capsule"
COLLECTION_NAME = "BakerCat_Rebuild_v3"
BASE_BLEND = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_rebuild_v8.blend"
OUT_BLEND = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_plump_v10.blend"
OUT_RENDER = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_plump_v10_preview.png"
OUT_GLB = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_plump_v10.glb"


# Local-Z profile: keep the original bean height and rounded ends, while adding
# most of the weight around the lower torso. X is the visible width; Y receives
# only a small increase so the face and apron keep their v8 placement.
PROFILE = [
    (-2.18, 1.04, 1.005),
    (-2.08, 1.08, 1.010),
    (-1.90, 1.11, 1.018),
    (-1.62, 1.12, 1.025),
    (1.60, 1.09, 1.020),
    (1.90, 1.06, 1.015),
    (2.08, 1.03, 1.008),
    (2.18, 1.00, 1.000),
]


def interpolate_profile(z):
    if z <= PROFILE[0][0]:
        return PROFILE[0][1], PROFILE[0][2]
    if z >= PROFILE[-1][0]:
        return PROFILE[-1][1], PROFILE[-1][2]
    for left, right in zip(PROFILE, PROFILE[1:]):
        z0, x0, y0 = left
        z1, x1, y1 = right
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
    return 1.0, 1.0


def add_plump_shape_key():
    body = bpy.data.objects[BODY_NAME]
    if body.data.shape_keys is None:
        body.shape_key_add(name="Basis", from_mix=False)
    old = body.data.shape_keys.key_blocks.get("Plump_Bean")
    if old:
        body.shape_key_remove(old)
    key = body.shape_key_add(name="Plump_Bean", from_mix=False)
    basis = body.data.shape_keys.key_blocks["Basis"]
    for src, dst in zip(basis.data, key.data):
        fx, fy = interpolate_profile(src.co.z)
        dst.co.x = src.co.x * fx
        dst.co.y = src.co.y * fy
        dst.co.z = src.co.z
    key.value = 1.0
    key.slider_min = 0.0
    key.slider_max = 1.35
    body["shape_revision"] = "v10 plump bean derived strictly from v8"
    body["plump_control"] = "Shape Keys > Plump_Bean (0.0 original v8, 1.0 final)"
    body["topology_preserved"] = True
    return body


def fit_waistband_only():
    # The body grows wider at waist level. Expand only the existing continuous
    # band in X so it remains outside the body; its design and depth stay v8.
    band = bpy.data.objects.get("BC3_Apron_Waistband")
    if not band:
        return
    band.scale.x = 1.11
    band["v10_fit_only"] = "X width adjusted to follow plump body"


def pack_baguette_texture():
    image = bpy.data.images.get("BC3_Baguette_Score_Texture")
    if image and not image.packed_file:
        image.pack()


def save_render_export():
    scene = bpy.context.scene
    scene.render.filepath = OUT_RENDER
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.render.render(write_still=True)

    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    collection = bpy.data.collections[COLLECTION_NAME]
    for obj in collection.objects:
        if obj.type in {"MESH", "CURVE", "EMPTY"} and obj.name != "BC3_Ground":
            obj.hide_set(False)
            obj.select_set(True)
    root = bpy.data.objects.get("BC3_ROOT_BakerCat")
    if root:
        bpy.context.view_layer.objects.active = root
        root["style_revision"] = "v10 v8 silhouette with adjustable plump bean body"
    bpy.ops.export_scene.gltf(
        filepath=OUT_GLB,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
    )
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)


def main():
    if bpy.data.filepath != BASE_BLEND:
        bpy.ops.wm.open_mainfile(filepath=BASE_BLEND)
    body = add_plump_shape_key()
    fit_waistband_only()
    pack_baguette_texture()
    bpy.context.view_layer.update()
    dimensions = tuple(round(float(v), 4) for v in body.dimensions)
    save_render_export()
    print({
        "done": True,
        "body_dimensions": dimensions,
        "plump_shape_key": body.data.shape_keys.key_blocks["Plump_Bean"].value,
        "topology_vertices": len(body.data.vertices),
        "blend": OUT_BLEND,
        "render": OUT_RENDER,
        "glb": OUT_GLB,
    })


main()
