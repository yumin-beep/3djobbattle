import bpy


BASE_BLEND = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_rebuild_v8.blend"
OUT_BLEND = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_round_xy_v11.blend"
OUT_RENDER = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_round_xy_v11_preview.png"
OUT_GLB = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_round_xy_v11.glb"
COLLECTION_NAME = "BakerCat_Rebuild_v3"
BODY_NAME = "BC3_Body_Capsule"


def scale_mesh_y(obj, factor):
    for vert in obj.data.vertices:
        vert.co.y *= factor
    obj.data.update()


def scale_curve_y(obj, factor):
    for spline in obj.data.splines:
        for point in spline.bezier_points:
            point.co.y *= factor
            point.handle_left.y *= factor
            point.handle_right.y *= factor
        for point in spline.points:
            point.co.y *= factor
    obj.data.update_tag()


def make_body_xy_round():
    body = bpy.data.objects[BODY_NAME]
    body.location = (0.0, 0.0, 3.12)
    factor = body.dimensions.x / body.dimensions.y
    scale_mesh_y(body, factor)
    body["shape_revision"] = "v11 v8 capsule with circular XY cross-section"
    body["dimensions_target"] = "2.68 x 2.68 x 4.36"
    body["xy_equal"] = True
    body["topology_preserved"] = True
    return body, factor


def fit_front_and_back_parts(factor):
    # These two meshes were constructed on the original elliptical body.
    # Scaling their vertex Y coordinates preserves their exact fitted curvature.
    for name in ("BC3_Apron_Front", "BC3_Apron_Waistband"):
        obj = bpy.data.objects.get(name)
        if obj:
            scale_mesh_y(obj, factor)
            obj["v11_fit"] = "Y curvature mapped from v8 ellipse to circular body"

    # Rigid front details move to the new front surface without being distorted.
    rigid_surface_parts = (
        "BC3_Apron_Pocket",
        "BC3_Eye_L", "BC3_Eye_R", "BC3_Nose",
        "BC3_Bow_Knot", "BC3_Bow_L", "BC3_Bow_R",
        "BC3_Ribbon_L", "BC3_Ribbon_R",
    )
    for name in rigid_surface_parts:
        obj = bpy.data.objects.get(name)
        if obj:
            obj.location.y *= factor

    # Facial linework and arms are curve-based, so map their control geometry.
    for obj in bpy.data.objects:
        if obj.type != "CURVE":
            continue
        if (obj.name.startswith("BC3_Mouth_") or
                obj.name.startswith("BC3_Whisker_") or
                obj.name.startswith("BC3_Arm_")):
            scale_curve_y(obj, factor)
            obj["v11_fit"] = "Y control coordinates mapped to circular body"


def fit_baguette(factor):
    baguette = bpy.data.objects.get("BC3_Baguette")
    if not baguette:
        return
    baguette.location.y *= factor
    scale_mesh_y(baguette, factor)
    baguette["v11_fit"] = "depth and placement mapped with body Y ratio"


def make_hat_round_in_top_view():
    # Keep each hat part's X and Z silhouette, only make its top-view footprint round.
    for name in ("BC3_Hat_Band", "BC3_Hat_Puff"):
        obj = bpy.data.objects.get(name)
        if not obj or obj.dimensions.y == 0:
            continue
        factor = obj.dimensions.x / obj.dimensions.y
        scale_mesh_y(obj, factor)
        obj["v11_fit"] = "top-view Y dimension matched to X"


def pack_texture():
    image = bpy.data.images.get("BC3_Baguette_Score_Texture")
    if image and not image.packed_file:
        image.pack()


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
        root["style_revision"] = "v11 v8 design fitted to circular XY body"
    bpy.ops.export_scene.gltf(
        filepath=OUT_GLB,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
    )
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)


def main():
    if bpy.data.filepath != BASE_BLEND:
        raise RuntimeError("Open the clean v8 source before running this script")
    body, factor = make_body_xy_round()
    fit_front_and_back_parts(factor)
    fit_baguette(factor)
    make_hat_round_in_top_view()
    pack_texture()
    bpy.context.view_layer.update()
    dimensions = tuple(round(float(v), 4) for v in body.dimensions)
    save_render_export()
    print({
        "done": True,
        "body_dimensions": dimensions,
        "xy_factor": round(factor, 6),
        "vertices": len(body.data.vertices),
        "blend": OUT_BLEND,
        "render": OUT_RENDER,
        "glb": OUT_GLB,
    })


main()
