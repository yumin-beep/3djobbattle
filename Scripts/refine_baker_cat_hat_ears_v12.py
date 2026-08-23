import bpy


BASE_BLEND = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_round_xy_v11.blend"
OUT_BLEND = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_round_xy_v12.blend"
OUT_RENDER = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_round_xy_v12_preview.png"
OUT_GLB = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_round_xy_v12.glb"
COLLECTION_NAME = "BakerCat_Rebuild_v3"


def scale_mesh_xy_to(obj, target_xy):
    factor_x = target_xy / obj.dimensions.x
    factor_y = target_xy / obj.dimensions.y
    for vert in obj.data.vertices:
        vert.co.x *= factor_x
        vert.co.y *= factor_y
    obj.data.update()


def fit_ears():
    left = bpy.data.objects["BC3_EarInner_L"]
    right = bpy.data.objects["BC3_EarInner_R"]

    # Preserve the user's mesh, scale and +/-13 degree rotations. Translation only.
    left.location.x -= 0.05
    right.location.x += 0.05
    left.location.y = -0.42
    right.location.y = -0.42

    for obj in (left, right):
        obj["v12_fit"] = "translation only for circular body; user rotation and mesh preserved"
        obj["user_shape_preserved"] = True


def fit_hat():
    band = bpy.data.objects["BC3_Hat_Band"]
    puff = bpy.data.objects["BC3_Hat_Puff"]

    # Center the hat on the new circular body instead of the old rear offset.
    band.location.y = 0.0
    puff.location.y = 0.0

    # Slightly widen the two masses; keep all Z proportions and low-poly topology.
    scale_mesh_xy_to(band, 1.46)
    scale_mesh_xy_to(puff, 2.05)
    puff.location.z += 0.03

    band["v12_fit"] = "centered on round body; XY diameter 1.46"
    puff["v12_fit"] = "centered on round body; XY diameter 2.05; raised 0.03"


def save_render_export():
    scene = bpy.context.scene
    scene.render.filepath = OUT_RENDER
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.render.render(write_still=True)

    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    collection = bpy.data.collections[COLLECTION_NAME]
    for obj in collection.objects:
        if obj.type in {"MESH", "CURVE", "EMPTY"} and obj.name != "BC3_Ground":
            obj.hide_set(False)
            obj.select_set(True)
    root = bpy.data.objects.get("BC3_ROOT_BakerCat")
    if root:
        bpy.context.view_layer.objects.active = root
        root["style_revision"] = "v12 round XY body with refitted ears and chef hat"
    bpy.ops.export_scene.gltf(
        filepath=OUT_GLB,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
    )
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)


def main():
    if bpy.data.filepath != BASE_BLEND:
        raise RuntimeError("Open v11 before running this script")
    fit_ears()
    fit_hat()
    bpy.context.view_layer.update()
    save_render_export()
    print({
        "done": True,
        "ear_changes": "translation only",
        "hat_band_xy": (1.46, 1.46),
        "hat_puff_xy": (2.05, 2.05),
        "blend": OUT_BLEND,
        "render": OUT_RENDER,
        "glb": OUT_GLB,
    })


main()
