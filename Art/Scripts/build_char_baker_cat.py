import bpy
import math
import os
from mathutils import Vector


ROOT_DIR = "/Users/kang-yumin/Documents/GitHub/new 3d"
OUTPUT_DIR = os.path.join(ROOT_DIR, "Art", "Models")
BLEND_PATH = os.path.join(OUTPUT_DIR, "char_baker_cat.blend")
FBX_PATH = os.path.join(OUTPUT_DIR, "char_baker_cat.fbx")
PALETTE_PATH = os.path.join(OUTPUT_DIR, "char_baker_cat_palette.png")
PREVIEW_PATH = os.path.join(OUTPUT_DIR, "char_baker_cat_preview.png")
PREVIEW_PATHS = {
    "front": os.path.join(OUTPUT_DIR, "char_baker_cat_preview_front.png"),
    "left": os.path.join(OUTPUT_DIR, "char_baker_cat_preview_left.png"),
    "back": os.path.join(OUTPUT_DIR, "char_baker_cat_preview_back.png"),
    "quarter": os.path.join(OUTPUT_DIR, "char_baker_cat_preview_quarter.png"),
}

PALETTE = {
    "body": "F0A92F",
    "body_shadow": "D58D24",
    "white": "F0E8DC",
    "white_shadow": "CBBBA6",
    "ink": "17130F",
    "brown": "4B2814",
    "bread": "C97718",
    "bread_light": "F2C56A",
    "ear": "D97B67",
    "ground": "FFFFFF",
}


def srgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)


def clear_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            datablocks.remove(block)
    for image in list(bpy.data.images):
        if image.name not in {"Render Result", "Viewer Node"}:
            bpy.data.images.remove(image)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def create_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, collection):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def create_palette_material():
    keys = list(PALETTE.keys())
    width = height = 128
    image = bpy.data.images.new("char_baker_cat_palette", width=width, height=height, alpha=True)
    pixels = list(srgb(PALETTE["body"])) * (width * height)
    stripe = width / len(keys)
    # The lower 32 px hold the flat palette. The remaining area is the body/face atlas.
    for y in range(32):
        for x in range(width):
            index = min(int(x / stripe), len(keys) - 1)
            rgba = srgb(PALETTE[keys[index]])
            offset = (y * width + x) * 4
            pixels[offset:offset + 4] = rgba

    ink = srgb(PALETTE["ink"])

    def dot(x, y, radius=1, color=ink):
        for py in range(max(0, y - radius), min(height, y + radius + 1)):
            for px in range(max(0, x - radius), min(width, x + radius + 1)):
                if (px - x) ** 2 + (py - y) ** 2 <= radius ** 2 + 0.5:
                    offset = (py * width + px) * 4
                    pixels[offset:offset + 4] = color

    def line(x0, y0, x1, y1, radius=1):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for step in range(steps + 1):
            t = step / steps
            dot(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), radius)

    # Face atlas: point eyes, small nose, omega mouth, and three whiskers per side.
    dot(40, 89, 4)
    dot(88, 89, 4)
    for x, y in ((62, 72), (63, 71), (64, 70), (65, 71), (66, 72)):
        dot(x, y, 2)
    line(64, 69, 64, 62, 1)
    line(64, 62, 60, 58, 1)
    line(60, 58, 55, 59, 1)
    line(64, 62, 68, 58, 1)
    line(68, 58, 73, 59, 1)
    for y0, y1 in ((72, 75), (67, 67), (62, 59)):
        line(22, y0, 42, y1, 1)
        line(86, y1, 106, y0, 1)

    image.pixels.foreach_set(pixels)
    image.filepath_raw = PALETTE_PATH
    image.file_format = "PNG"
    image.save()

    material = bpy.data.materials.new("MAT_char_baker_cat_palette")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Closest"
    bsdf.inputs["Roughness"].default_value = 0.92
    bsdf.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.18
    links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    uv_points = {key: ((i + 0.5) / len(keys), 16 / height) for i, key in enumerate(keys)}
    return material, uv_points


def apply_constant_uv(obj, color_key):
    if obj.type != "MESH":
        return
    mesh = obj.data
    if len(mesh.uv_layers) == 0:
        layer = mesh.uv_layers.new(name="PaletteUV")
    else:
        layer = mesh.uv_layers[0]
        layer.name = "PaletteUV"
    point = UV_POINTS[color_key]
    for loop in layer.data:
        loop.uv = point


def apply_body_face_uv(obj):
    """Planar-map only the visible facial polygons into the upper texture atlas."""
    mesh = obj.data
    layer = mesh.uv_layers.get("PaletteUV") or mesh.uv_layers.new(name="PaletteUV")
    uniform = UV_POINTS["body"]
    for polygon in mesh.polygons:
        center_z = polygon.center.z + obj.location.z
        is_face = polygon.center.y < -0.18 and 0.76 <= center_z <= 1.24
        for loop_index in polygon.loop_indices:
            if not is_face:
                layer.data[loop_index].uv = uniform
                continue
            vertex = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            world_z = vertex.z + obj.location.z
            u = 0.06 + ((vertex.x + 0.34) / 0.68) * 0.88
            v = 0.27 + ((world_z - 0.76) / 0.48) * 0.69
            layer.data[loop_index].uv = (max(0.02, min(0.98, u)), max(0.27, min(0.98, v)))


def finalize(obj, color_key, parent=True, collection=None, flat=True):
    if obj.type == "CURVE":
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.convert(target="MESH")
        obj = bpy.context.object
    if obj.type == "MESH":
        if not obj.data.materials:
            obj.data.materials.append(MATERIAL)
        for poly in obj.data.polygons:
            poly.use_smooth = not flat
        apply_constant_uv(obj, color_key)
    if parent:
        obj.parent = ROOT
    move_to_collection(obj, collection or CHARACTER)
    obj["palette_swatch"] = color_key
    return obj


def apply_transform(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)


def ico(name, location, scale, color, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    apply_transform(obj)
    return finalize(obj, color)


def uv_sphere(name, location, scale, color, segments=16, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    apply_transform(obj)
    return finalize(obj, color)


def cube(name, location, scale, color, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    apply_transform(obj)
    if bevel > 0:
        mod = obj.modifiers.new("LowPolyBevel", "BEVEL")
        mod.width = bevel
        mod.segments = 1
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return finalize(obj, color)


def primitive_beveled_cube(name, location, dimensions, color, bevel=0.0, segments=2):
    """Keep a six-quad cube as the editable base and use a non-destructive bevel."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    apply_transform(obj)
    finalize(obj, color)
    if bevel > 0:
        modifier = obj.modifiers.new("PrimitiveBevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = segments
        modifier.limit_method = "ANGLE"
    obj["primitive_base"] = "Cube"
    obj["base_segments"] = 4
    return obj


def primitive_beveled_cylinder(name, location, radius, depth, y_scale, color,
                                vertices=16, bevel=0.0, bevel_segments=2):
    """Keep a restricted-segment cylinder base; bevel creates the capsule silhouette."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       end_fill_type="NGON", location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale.y = y_scale
    apply_transform(obj)
    finalize(obj, color)
    if bevel > 0:
        modifier = obj.modifiers.new("PrimitiveBevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = bevel_segments
        modifier.limit_method = "ANGLE"
    obj["primitive_base"] = "Cylinder"
    obj["base_segments"] = vertices
    return obj


def cylinder(name, location, radius, depth, color, vertices=12, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       end_fill_type="NGON", location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    return finalize(obj, color)


def elliptic_cylinder(name, location, radius, depth, y_scale, color, vertices=16, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       end_fill_type="NGON", location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale.y = y_scale
    apply_transform(obj)
    if bevel > 0:
        mod = obj.modifiers.new("LowPolyBevel", "BEVEL")
        mod.width = bevel
        mod.segments = 1
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return finalize(obj, color)


def prism(name, vertices, faces, color):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    CHARACTER.objects.link(obj)
    return finalize(obj, color)


def triangular_prism(name, tri_front, tri_back, color):
    verts = tri_front + tri_back
    faces = [
        (0, 1, 2), (5, 4, 3),
        (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0),
    ]
    return prism(name, verts, faces, color)


def mirrored_triangular_prism(name, tri_front, tri_back, color):
    """Build the +X ear once and apply an X mirror for exact bilateral symmetry."""
    obj = triangular_prism(name, tri_front, tri_back, color)
    modifier = obj.modifiers.new("ExactSymmetry", "MIRROR")
    modifier.use_axis[0] = True
    modifier.merge_threshold = 0.0001
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)
    apply_constant_uv(obj, color)
    obj["construction"] = "single_right_ear_mirrored_on_X"
    return obj


def curve_mesh(name, points, bevel, color, cyclic=False):
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = bevel
    curve.bevel_resolution = 0
    curve.resolution_u = 1
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    CHARACTER.objects.link(obj)
    return finalize(obj, color)


def capsule_between(name, start, end, radius, color, vertices=12, caps=True):
    a, b = Vector(start), Vector(end)
    midpoint = (a + b) * 0.5
    direction = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length,
                                       end_fill_type="NGON", location=midpoint)
    body = bpy.context.object
    body.name = name + "_Body"
    body.rotation_mode = "QUATERNION"
    body.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    body.rotation_mode = "XYZ"
    finalize(body, color)
    result = [body]
    if caps:
        result.append(ico(name + "_Cap_A", a, (radius, radius, radius), color, 1))
        result.append(ico(name + "_Cap_B", b, (radius, radius, radius), color, 1))
    return result


def join_meshes(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    meshes = [obj for obj in objects if obj and obj.type == "MESH"]
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    joined = bpy.context.object
    joined.name = name
    joined.parent = ROOT
    move_to_collection(joined, CHARACTER)
    return joined


def apply_all_character_transforms():
    for obj in list(CHARACTER.objects):
        if obj.type != "MESH":
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        obj.select_set(False)


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def bezier_tube(name, points, bevel, color):
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = bevel
    curve.bevel_resolution = 1
    curve.use_fill_caps = True
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    CHARACTER.objects.link(obj)
    return finalize(obj, color)


def build_body():
    # Editable base: one 16-sided cylinder with a bevel modifier, not a dense sculpted mesh.
    primitive_beveled_cylinder("Body", (0, 0, 0.84), 0.44, 1.26, 0.76,
                               "body", vertices=16, bevel=0.22, bevel_segments=2)

    # Each ear remains an independent five-face triangular prism.
    outer_front = [(0.28, -0.19, 1.34), (0.43, -0.15, 1.35), (0.365, -0.10, 1.61)]
    outer_back = [(x, 0.035, z) for x, _, z in outer_front]
    triangular_prism("Ear_R", outer_front, outer_back, "body")
    triangular_prism("Ear_L", [(-x, y, z) for x, y, z in reversed(outer_front)],
                     [(-x, y, z) for x, y, z in reversed(outer_back)], "body")
    inner_front = [(0.315, -0.207, 1.38), (0.405, -0.175, 1.39), (0.365, -0.15, 1.54)]
    inner_back = [(x, -0.145, z) for x, _, z in inner_front]
    triangular_prism("EarInner_R", inner_front, inner_back, "ear")
    triangular_prism("EarInner_L", [(-x, y, z) for x, y, z in reversed(inner_front)],
                     [(-x, y, z) for x, y, z in reversed(inner_back)], "ear")

    # Short stick legs and soft low-poly paws establish the required foot-center pivot.
    for side, x in (("L", -0.18), ("R", 0.18)):
        cylinder("Leg_" + side, (x, 0.0, 0.17), 0.027, 0.25, "brown", 8)
        foot = primitive_beveled_cylinder("Foot_" + side, (x, -0.025, 0.055),
                                          0.105, 0.07, 1.25, "body_shadow",
                                          vertices=10, bevel=0.025, bevel_segments=2)


def build_face_geometry():
    y = -0.349
    for side, x in (("L", -0.145), ("R", 0.145)):
        eye = primitive_beveled_cylinder("Eye_" + side, (x, y, 1.045),
                                         0.046, 0.024, 1.0, "ink",
                                         vertices=10, bevel=0.008, bevel_segments=2)
        eye.rotation_euler.x = math.radians(90)
    nose = primitive_beveled_cylinder("Nose", (0, y - 0.012, 0.955),
                                      0.040, 0.022, 1.0, "ink",
                                      vertices=8, bevel=0.007, bevel_segments=1)
    nose.rotation_euler.x = math.radians(90)
    nose.scale.z = 0.78
    bezier_tube("Mouth_Center", [(0, y - 0.014, 0.94), (0, y - 0.017, 0.895)], 0.009, "ink")
    bezier_tube("Mouth_L", [(0, y - 0.017, 0.895), (-0.035, y - 0.019, 0.875),
                            (-0.075, y - 0.016, 0.895)], 0.009, "ink")
    bezier_tube("Mouth_R", [(0, y - 0.017, 0.895), (0.035, y - 0.019, 0.875),
                            (0.075, y - 0.016, 0.895)], 0.009, "ink")
    for side, sx in (("L", -1), ("R", 1)):
        for index, dz in enumerate((0.045, 0.0, -0.045)):
            inner = (sx * 0.245, y - 0.008, 0.945 + dz)
            outer = (sx * (0.38 + index * 0.004), y + 0.002, 0.96 + dz * 1.35)
            bezier_tube(f"Whisker_{side}_{index + 1}", [inner, outer], 0.0075, "ink")


def build_apron():
    # Independent cube panel + cylinder waistband. No wrapping boolean or triangulated shell.
    primitive_beveled_cube("Apron_Panel", (0, -0.345, 0.50),
                           (0.68, 0.055, 0.50), "white", bevel=0.035, segments=2)
    primitive_beveled_cylinder("Apron_Waist", (0, 0, 0.765), 0.455, 0.065, 0.76,
                               "white_shadow", vertices=16, bevel=0.010, bevel_segments=1)
    primitive_beveled_cube("Apron_Pocket", (0, -0.392, 0.49),
                           (0.22, 0.035, 0.15), "white_shadow", bevel=0.015, segments=1)

    # Back bow and ties make the turnaround complete even though the preview is front-facing.
    primitive_beveled_cube("Apron_Bow_L", (-0.105, 0.355, 0.72),
                           (0.18, 0.045, 0.10), "white", bevel=0.025, segments=1)
    primitive_beveled_cube("Apron_Bow_R", (0.105, 0.355, 0.72),
                           (0.18, 0.045, 0.10), "white", bevel=0.025, segments=1)
    primitive_beveled_cube("Apron_Bow_Knot", (0, 0.375, 0.72),
                           (0.07, 0.05, 0.07), "white_shadow", bevel=0.018, segments=1)
    triangular_prism("Apron_Tie_L",
                     [(-0.08, 0.36, 0.69), (-0.01, 0.36, 0.69), (-0.10, 0.36, 0.48)],
                     [(-0.08, 0.39, 0.69), (-0.01, 0.39, 0.69), (-0.10, 0.39, 0.48)], "white")
    triangular_prism("Apron_Tie_R",
                     [(0.01, 0.36, 0.69), (0.08, 0.36, 0.69), (0.10, 0.36, 0.48)],
                     [(0.01, 0.39, 0.69), (0.08, 0.39, 0.69), (0.10, 0.39, 0.48)], "white")


def build_hat():
    # Both hat parts keep low-segment cylinder bases with separate bevel modifiers.
    primitive_beveled_cylinder("ChefHat_Band", (0, 0.008, 1.54), 0.285, 0.18, 0.84,
                               "white", vertices=16, bevel=0.018, bevel_segments=2)
    primitive_beveled_cylinder("ChefHat_Crown", (0, 0.015, 1.78), 0.36, 0.30, 0.80,
                               "white", vertices=16, bevel=0.10, bevel_segments=2)


def build_arms():
    # Symmetric relaxed arms are the defining neutral-pose silhouette in the concept.
    bezier_tube("Arm_L", [(-0.405, -0.015, 0.88), (-0.535, -0.08, 0.72),
                          (-0.50, -0.10, 0.49)], 0.028, "brown")
    bezier_tube("Arm_R", [(0.405, -0.015, 0.88), (0.535, -0.08, 0.72),
                          (0.50, -0.10, 0.49)], 0.028, "brown")
    primitive_beveled_cylinder("HandTip_L", (-0.50, -0.10, 0.49), 0.032, 0.035, 1.0,
                               "brown", vertices=8, bevel=0.010, bevel_segments=1)
    primitive_beveled_cylinder("HandTip_R", (0.50, -0.10, 0.49), 0.032, 0.035, 1.0,
                               "brown", vertices=8, bevel=0.010, bevel_segments=1)


def build_preview():
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.006))
    ground = bpy.context.object
    ground.name = "Preview_Ground"
    finalize(ground, "ground", parent=False, collection=PREVIEW, flat=True)
    ground.hide_render = True

    bpy.ops.object.camera_add(location=(3.15, -6.25, 2.40))
    camera = bpy.context.object
    camera.name = "Preview_Camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.45
    look_at(camera, (0, 0, 0.96))
    move_to_collection(camera, PREVIEW)
    bpy.context.scene.camera = camera

    for name, loc, energy, size in (
        ("Key_Light", (-3.5, -4.0, 5.5), 300, 4.0),
        ("Fill_Light", (4.0, -2.0, 3.0), 120, 3.0),
        ("Rim_Light", (1.0, 3.5, 4.5), 180, 3.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        PREVIEW.objects.link(light)
        light.location = loc
        look_at(light, (0, 0, 0.9))


def configure_scene():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = PREVIEW_PATH
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_percentage = 100
    scene.world.use_nodes = True
    world_nodes = scene.world.node_tree.nodes
    world_links = scene.world.node_tree.links
    world_nodes.clear()
    world_output = world_nodes.new("ShaderNodeOutputWorld")
    light_path = world_nodes.new("ShaderNodeLightPath")
    mix_shader = world_nodes.new("ShaderNodeMixShader")
    lighting_bg = world_nodes.new("ShaderNodeBackground")
    camera_bg = world_nodes.new("ShaderNodeBackground")
    lighting_bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    lighting_bg.inputs["Strength"].default_value = 0.38
    camera_bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    camera_bg.inputs["Strength"].default_value = 1.0
    world_links.new(light_path.outputs["Is Camera Ray"], mix_shader.inputs[0])
    world_links.new(lighting_bg.outputs["Background"], mix_shader.inputs[1])
    world_links.new(camera_bg.outputs["Background"], mix_shader.inputs[2])
    world_links.new(mix_shader.outputs["Shader"], world_output.inputs["Surface"])
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = PREVIEW_PATH
    scene["asset_id"] = "char_baker_cat"
    scene["front_axis"] = "-Y"
    scene["pivot_rule"] = "foot_center_at_world_origin"
    scene["art_spec"] = "Docs/발주-char_baker_cat-rev2.md"
    scene["revision"] = "rev2"
    scene["modeling_priority"] = "concept_likeness_first"
    scene["construction_rule"] = "independent_primitive_quad_first"


def render_turnaround():
    scene = bpy.context.scene
    camera = scene.camera
    views = {
        "front": ((0.0, -6.5, 1.02), (0.0, 0.0, 1.02)),
        "left": ((-6.5, 0.0, 1.02), (0.0, 0.0, 1.02)),
        "back": ((0.0, 6.5, 1.02), (0.0, 0.0, 1.02)),
        "quarter": ((3.15, -6.25, 2.40), (0.0, 0.0, 0.96)),
    }
    for name, (location, target) in views.items():
        camera.location = location
        look_at(camera, target)
        scene.render.filepath = PREVIEW_PATHS[name]
        bpy.ops.render.render(write_still=True)
        if name == "quarter":
            bpy.data.images["Render Result"].save_render(PREVIEW_PATH, scene=scene)


def export_fbx_and_verify(expected_dimensions):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in CHARACTER.objects:
        if obj.type in {"MESH", "EMPTY"}:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = ROOT
    bpy.ops.export_scene.fbx(
        filepath=FBX_PATH,
        use_selection=True,
        object_types={"EMPTY", "MESH"},
        axis_forward="-Z",
        axis_up="Y",
        apply_scale_options="FBX_SCALE_ALL",
        use_mesh_modifiers=True,
        bake_anim=False,
        add_leaf_bones=False,
        path_mode="AUTO",
    )

    original_objects = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=FBX_PATH, axis_forward="-Z", axis_up="Y")
    imported = [obj for obj in bpy.data.objects if obj not in original_objects]
    imported_meshes = [obj for obj in imported if obj.type == "MESH"]
    assert imported_meshes, "FBX round-trip created no mesh objects"
    points = [obj.matrix_world @ Vector(corner) for obj in imported_meshes for corner in obj.bound_box]
    imported_min = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    imported_max = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    imported_dimensions = imported_max - imported_min
    delta = imported_dimensions - expected_dimensions
    assert max(abs(delta.x), abs(delta.y), abs(delta.z)) < 0.03, (
        f"FBX round-trip dimension mismatch: {tuple(imported_dimensions)} vs {tuple(expected_dimensions)}"
    )

    bpy.ops.object.select_all(action="DESELECT")
    for obj in imported:
        obj.select_set(True)
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    return tuple(round(v, 4) for v in imported_dimensions)


def validate_and_save():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    triangles = 0
    mesh_objects = []
    bbox_points = []
    body_points = []
    material_names = set()
    base_topology = {"triangles": 0, "quads": 0, "ngons": 0}
    for obj in CHARACTER.objects:
        if obj.type != "MESH":
            continue
        mesh_objects.append(obj)
        for polygon in obj.data.polygons:
            side_count = len(polygon.vertices)
            if side_count == 3:
                base_topology["triangles"] += 1
            elif side_count == 4:
                base_topology["quads"] += 1
            elif side_count > 4:
                base_topology["ngons"] += 1
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        evaluated.to_mesh_clear()
        for slot in obj.material_slots:
            if slot.material:
                material_names.add(slot.material.name)
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            bbox_points.append(point)
            if not obj.name.startswith(("ChefHat", "prop_")):
                body_points.append(point)

    bbox_min = Vector((min(p.x for p in bbox_points), min(p.y for p in bbox_points), min(p.z for p in bbox_points)))
    bbox_max = Vector((max(p.x for p in bbox_points), max(p.y for p in bbox_points), max(p.z for p in bbox_points)))
    core_min = Vector((min(p.x for p in body_points), min(p.y for p in body_points), min(p.z for p in body_points)))
    core_max = Vector((max(p.x for p in body_points), max(p.y for p in body_points), max(p.z for p in body_points)))

    ROOT["triangle_count"] = triangles
    ROOT["material_count"] = len(material_names)
    ROOT["overall_dimensions_m"] = tuple(round(v, 4) for v in (bbox_max - bbox_min))
    ROOT["core_height_m"] = round(core_max.z - core_min.z, 4)
    ROOT["body_width_m"] = 0.88

    face_mesh_names = [obj.name for obj in CHARACTER.objects
                       if obj.name.startswith(("Eye", "Nose", "Mouth", "Whisker"))]
    ear_l = CHARACTER.objects.get("Ear_L")
    ear_r = CHARACTER.objects.get("Ear_R")
    band = CHARACTER.objects.get("ChefHat_Band")
    body = CHARACTER.objects.get("Body")
    assert len(face_mesh_names) >= 10, f"Concept face geometry is incomplete: {face_mesh_names}"
    assert ear_l and ear_r and (ear_l.dimensions - ear_r.dimensions).length < 1e-5, "Ears are not symmetric"
    primary = {
        "Body": "Cylinder",
        "Apron_Panel": "Cube",
        "ChefHat_Band": "Cylinder",
        "ChefHat_Crown": "Cylinder",
    }
    for name, primitive_type in primary.items():
        obj = CHARACTER.objects.get(name)
        assert obj and obj.get("primitive_base") == primitive_type, f"{name} is not a {primitive_type} base"
        assert any(mod.type == "BEVEL" for mod in obj.modifiers), f"{name} lost its non-destructive bevel"
    assert len({CHARACTER.objects[name].data.as_pointer() for name in primary}) == len(primary), "Primary parts share mesh data"
    body_top = max((body.matrix_world @ Vector(v)).z for v in body.bound_box)
    band_bottom = min((band.matrix_world @ Vector(v)).z for v in band.bound_box)
    hat_overlap = body_top - band_bottom
    assert 0.01 <= hat_overlap <= 0.025, f"Chef hat overlap must be 1-2 cm, got {hat_overlap} m"

    bad_transforms = []
    for obj in CHARACTER.objects:
        if obj.type != "MESH":
            continue
        loc_ok = obj.location.length < 1e-5
        rot_ok = sum(abs(v) for v in obj.rotation_euler) < 1e-5
        scale_ok = all(abs(v - 1.0) < 1e-5 for v in obj.scale)
        if not (loc_ok and rot_ok and scale_ok):
            bad_transforms.append((obj.name, tuple(obj.location), tuple(obj.rotation_euler), tuple(obj.scale)))

    assert triangles < 3000, f"Triangle budget exceeded: {triangles}"
    assert base_topology["quads"] > base_topology["triangles"] * 2, f"Topology is not quad-dominant: {base_topology}"
    assert len(material_names) == 1, f"Expected one material, found {material_names}"
    assert abs(ROOT.location.z) < 1e-6, "Root pivot must remain at ground level"
    assert 1.45 <= ROOT["core_height_m"] <= 1.75, f"Unexpected core height {ROOT['core_height_m']}"
    assert not bad_transforms, f"Unapplied transforms: {bad_transforms}"

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    fbx_dimensions = export_fbx_and_verify(bbox_max - bbox_min)
    ROOT["fbx_roundtrip_dimensions_m"] = fbx_dimensions
    ROOT["fbx_axis_forward"] = "-Z"
    ROOT["fbx_axis_up"] = "Y"
    render_turnaround()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print("BAKER_CAT_REV2_BUILD_OK")
    print({
        "blend": BLEND_PATH,
        "fbx": FBX_PATH,
        "previews": PREVIEW_PATHS,
        "palette": PALETTE_PATH,
        "mesh_objects": len(mesh_objects),
        "triangles": triangles,
        "base_topology": base_topology,
        "materials": sorted(material_names),
        "face_mesh_objects": face_mesh_names,
        "pose": "concept_neutral_symmetric_arms",
        "hat_head_overlap_m": round(hat_overlap, 4),
        "overall_dimensions_m": tuple(round(v, 3) for v in (bbox_max - bbox_min)),
        "core_height_m": ROOT["core_height_m"],
        "root": tuple(ROOT.location),
        "front_axis": "-Y",
        "fbx_roundtrip_dimensions_m": fbx_dimensions,
    })


os.makedirs(OUTPUT_DIR, exist_ok=True)
clear_scene()
CHARACTER = create_collection("CHARACTER_char_baker_cat")
PREVIEW = create_collection("PREVIEW_SETUP")
MATERIAL, UV_POINTS = create_palette_material()
ROOT = bpy.data.objects.new("ROOT_char_baker_cat", None)
CHARACTER.objects.link(ROOT)
ROOT.location = (0, 0, 0)
ROOT.empty_display_type = "PLAIN_AXES"
ROOT.empty_display_size = 0.25

build_body()
build_face_geometry()
build_apron()
build_hat()
build_arms()
apply_all_character_transforms()
build_preview()
configure_scene()
validate_and_save()
