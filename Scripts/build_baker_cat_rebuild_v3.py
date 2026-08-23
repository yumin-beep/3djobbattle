import bpy
import math
import os
from mathutils import Vector


COLL_NAME = "BakerCat_Rebuild_v3"
PREFIX = "BC3_"
ROOT = None
COLL = None
MATS = {}


def _move_to_collection(obj):
    global COLL
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    COLL.objects.link(obj)
    return obj


def _parent(obj):
    if ROOT is not None:
        obj.parent = ROOT
    return obj


def _mat(name, color, roughness=0.72, metallic=0.0):
    mat = bpy.data.materials.get(PREFIX + name) or bpy.data.materials.new(PREFIX + name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = next((node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        if bsdf.inputs.get("Base Color"):
            bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        if bsdf.inputs.get("Roughness"):
            bsdf.inputs["Roughness"].default_value = roughness
        if bsdf.inputs.get("Metallic"):
            bsdf.inputs["Metallic"].default_value = metallic
    return mat


def _assign(obj, mat):
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj


def _bevel(obj, width=0.04, segments=1):
    mod = obj.modifiers.new("Controlled_Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    return obj


def _cube(name, loc, scale, mat, rotation=(0.0, 0.0, 0.0), bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = PREFIX + name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    _move_to_collection(obj)
    _parent(obj)
    _assign(obj, mat)
    if bevel:
        _bevel(obj, bevel, 1)
    return obj


def _cylinder(name, loc, radius, depth, mat, vertices=12, rotation=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = PREFIX + name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    _move_to_collection(obj)
    _parent(obj)
    _assign(obj, mat)
    return obj


def _uv_sphere(name, loc, scale, mat, segments=12, rings=6):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    obj = bpy.context.object
    obj.name = PREFIX + name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    _move_to_collection(obj)
    _parent(obj)
    _assign(obj, mat)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


def _profile_mesh(name, loc, z_radii, segments, xy_scale, mat):
    verts = []
    faces = []
    sx, sy = xy_scale
    for z, radius in z_radii:
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            verts.append((sx * radius * math.cos(angle), sy * radius * math.sin(angle), z))
    rings = len(z_radii)
    for ring in range(rings - 1):
        a = ring * segments
        b = (ring + 1) * segments
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((a + i, a + j, b + j, b + i))
    faces.append(tuple(reversed(tuple(range(segments)))))
    top = tuple((rings - 1) * segments + i for i in range(segments))
    faces.append(top)
    mesh = bpy.data.meshes.new(PREFIX + name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(PREFIX + name, mesh)
    obj.location = loc
    COLL.objects.link(obj)
    _parent(obj)
    _assign(obj, mat)
    return obj


def _tri_prism(name, loc, width, height, depth, mat, rotation=(0.0, 0.0, 0.0)):
    x = width * 0.5
    y = depth * 0.5
    z0 = -height * 0.5
    z1 = height * 0.5
    verts = [(-x, -y, z0), (x, -y, z0), (0, -y, z1), (-x, y, z0), (x, y, z0), (0, y, z1)]
    faces = [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
    mesh = bpy.data.meshes.new(PREFIX + name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(PREFIX + name, mesh)
    obj.location = loc
    obj.rotation_euler = rotation
    COLL.objects.link(obj)
    _parent(obj)
    _assign(obj, mat)
    return obj


def _diamond_prism(name, width, height, depth, mat):
    x = width * 0.5
    y = depth * 0.5
    z = height * 0.5
    verts = [(-x, -y, 0), (0, -y, z), (x, -y, 0), (0, -y, -z),
             (-x, y, 0), (0, y, z), (x, y, 0), (0, y, -z)]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    mesh = bpy.data.meshes.new(PREFIX + name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(PREFIX + name, mesh)
    COLL.objects.link(obj)
    _parent(obj)
    _assign(obj, mat)
    return obj


def _curve(name, points, radius, mat, cyclic=False):
    curve = bpy.data.curves.new(PREFIX + name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 0
    curve.resolution_u = 1
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, co in zip(spline.bezier_points, points):
        bp.co = co
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(PREFIX + name, curve)
    COLL.objects.link(obj)
    _parent(obj)
    _assign(obj, mat)
    return obj


def _curved_panel(name, z_bottom, z_top, half_width, rx, ry, y_offset, mat, cols=8, rows=3):
    verts = []
    faces = []
    for row in range(rows + 1):
        z = z_bottom + (z_top - z_bottom) * row / rows
        for col in range(cols + 1):
            x = -half_width + 2.0 * half_width * col / cols
            norm = min(0.999, (x / rx) ** 2)
            y = -ry * math.sqrt(1.0 - norm) - y_offset
            verts.append((x, y, z))
    stride = cols + 1
    for row in range(rows):
        for col in range(cols):
            a = row * stride + col
            faces.append((a, a + 1, a + 1 + stride, a + stride))
    mesh = bpy.data.meshes.new(PREFIX + name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(PREFIX + name, mesh)
    COLL.objects.link(obj)
    _parent(obj)
    _assign(obj, mat)
    solid = obj.modifiers.new("Apron_Thickness", "SOLIDIFY")
    solid.thickness = 0.055
    _bevel(obj, 0.025, 1)
    return obj


def _ellipse_band(name, z0, z1, rx, ry, offset, mat, segments=16):
    verts = []
    faces = []
    for z in (z0, z1):
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            verts.append((rx * math.cos(a), ry * math.sin(a), z))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, segments + j, segments + i))
    mesh = bpy.data.meshes.new(PREFIX + name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(PREFIX + name, mesh)
    COLL.objects.link(obj)
    _parent(obj)
    _assign(obj, mat)
    solid = obj.modifiers.new("Band_Thickness", "SOLIDIFY")
    solid.thickness = offset
    return obj


def _look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _make_baguette_score_texture(filepath, width=256, height=1024):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    image = bpy.data.images.get("BC3_Baguette_Score_Texture")
    if image is None or image.size[0] != width or image.size[1] != height:
        if image is not None:
            bpy.data.images.remove(image)
        image = bpy.data.images.new("BC3_Baguette_Score_Texture", width=width, height=height, alpha=False)
    crust = (0.74, 0.30, 0.055)
    cut = (1.0, 0.72, 0.30)
    centers = (.18, .34, .50, .66, .82)
    angle = math.radians(8.0)
    ca, sa = math.cos(angle), math.sin(angle)
    pixels = [0.0] * (width * height * 4)
    for py in range(height):
        v = py / max(1, height - 1)
        for px in range(width):
            u = px / max(1, width - 1)
            mask = 0.0
            for center in centers:
                du = u - .75
                dv = v - center
                qx = ca * du + sa * dv
                qy = -sa * du + ca * dv
                diamond = abs(qx) / .105 + abs(qy) / .022
                if diamond < 1.0:
                    mask = max(mask, min(1.0, (1.0 - diamond) * 10.0))
            color = tuple(crust[i] * (1.0 - mask) + cut[i] * mask for i in range(3))
            offset = (py * width + px) * 4
            pixels[offset:offset + 4] = (*color, 1.0)
    image.pixels.foreach_set(pixels)
    image.filepath_raw = filepath
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image


def _apply_baguette_uv_texture(obj, filepath):
    mesh = obj.data
    segments = 12
    rings = len(mesh.vertices) // segments
    uv = mesh.uv_layers.get("Baguette_UV") or mesh.uv_layers.new(name="Baguette_UV")
    side_count = (rings - 1) * segments
    z_values = [vert.co.z for vert in mesh.vertices]
    z_min, z_max = min(z_values), max(z_values)
    z_span = max(.0001, z_max - z_min)
    for poly in mesh.polygons:
        if poly.index < side_count:
            ring = poly.index // segments
            seg = poly.index % segments
            u0 = seg / segments
            u1 = (seg + 1) / segments
            v0 = (mesh.vertices[ring * segments].co.z - z_min) / z_span
            v1 = (mesh.vertices[(ring + 1) * segments].co.z - z_min) / z_span
            coords = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
        else:
            coords = tuple((.5, .5) for _ in poly.loop_indices)
        for loop_index, coord in zip(poly.loop_indices, coords):
            uv.data[loop_index].uv = coord
    image = _make_baguette_score_texture(filepath)
    mat = MATS["bread"]
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    tex = nodes.get("BC3_Baguette_Texture") or nodes.new("ShaderNodeTexImage")
    tex.name = "BC3_Baguette_Texture"
    tex.label = "Five baked score cuts — UV texture, no geometry"
    tex.image = image
    bsdf = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf and bsdf.inputs.get("Base Color"):
        for link in list(bsdf.inputs["Base Color"].links):
            links.remove(link)
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    obj["score_method"] = "UV image texture"
    obj["score_count"] = 5
    obj["texture_path"] = filepath
    return filepath


def setup_scene():
    global COLL, ROOT, MATS
    old = bpy.data.collections.get(COLL_NAME)
    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)
    for obj in bpy.context.scene.objects:
        obj.hide_render = True
        obj.hide_set(True)
    COLL = bpy.data.collections.new(COLL_NAME)
    bpy.context.scene.collection.children.link(COLL)
    ROOT = bpy.data.objects.new(PREFIX + "ROOT_BakerCat", None)
    COLL.objects.link(ROOT)
    ROOT["construction"] = "primitive assembly; independent body, ears, hat, apron, baguette"
    ROOT["body_height_reference"] = 4.4
    MATS = {
        "yellow": _mat("Mat_Body_Yellow", (1.0, 0.58, 0.115), 0.78),
        "yellow_light": _mat("Mat_InnerEar_Gold", (1.0, 0.70, 0.20), 0.75),
        "coral": _mat("Mat_InnerEar_Coral", (0.95, 0.30, 0.20), 0.76),
        "white": _mat("Mat_Warm_White", (0.94, 0.91, 0.84), 0.82),
        "dark": _mat("Mat_Dark_Chocolate", (0.12, 0.045, 0.018), 0.68),
        "black": _mat("Mat_Face_Black", (0.012, 0.009, 0.006), 0.42),
        "bread": _mat("Mat_Baguette_Crust", (0.88, 0.31, 0.035), 0.80),
        "score": _mat("Mat_Baguette_Score", (1.0, 0.66, 0.20), 0.86),
        "ground": _mat("Mat_Ground", (0.52, 0.39, 0.27), 0.92),
    }
    return "setup complete"


def build_body_hat_ears():
    body = _profile_mesh(
        "Body_Capsule", (0, 0, 3.12),
        [(-2.18, .78), (-2.08, .94), (-1.90, 1.0), (-1.62, 1.0), (1.60, 1.0), (1.90, .98), (2.08, .90), (2.18, .70)],
        16, (1.34, .90), MATS["yellow"]
    )
    body["base_primitive"] = "16-segment capped cylinder profile"
    body["topology"] = "quad sides, two n-gon caps"
    for side, sign in (("L", -1), ("R", 1)):
        x = sign * 1.02
        ear_rot = (0, sign * math.radians(2.0), 0)
        ear = _tri_prism("Ear_" + side, (x, -.38, 5.16), .58, 1.02, .26, MATS["yellow_light"], rotation=ear_rot)
        ear["separate_mesh"] = True
        inner = _tri_prism("EarInner_" + side, (x, -.525, 5.17), .32, .58, .035, MATS["coral"], rotation=ear_rot)
        inner["separate_mesh"] = True
    band = _cylinder("Hat_Band", (0, .14, 5.55), .68, .72, MATS["white"], vertices=16, scale=(1.0, .80, 1.0))
    band["separate_mesh"] = True
    crown = _profile_mesh(
        "Hat_Puff", (0, .14, 6.15),
        [(-.55, .62), (-.38, .94), (-.08, 1.12), (.22, 1.02), (.44, .70), (.56, .38)],
        12, (.88, .67), MATS["white"]
    )
    crown["separate_mesh"] = True
    crown["ear_clearance_rule"] = "hat centered between and behind ears; no merge"
    return "body, ears, inner ears, hat band, and hat puff built"


def build_outfit_legs_face():
    _curved_panel("Apron_Front", 1.08, 3.02, 1.18, 1.34, .90, .055, MATS["white"])
    waistband = _ellipse_band("Apron_Waistband", 2.85, 3.12, 1.385, .925, .055, MATS["white"], 16)
    waistband["design_rule"] = "one continuous white waistband; visible on both sides; rear bow only"
    _cube("Apron_Pocket", (0, -.975, 1.82), (.52, .055, .36), MATS["white"], bevel=.035)
    _cube("Bow_Knot", (0, .99, 2.96), (.18, .10, .15), MATS["white"], rotation=(math.radians(90), 0, 0), bevel=.035)
    _cube("Bow_L", (-.32, .99, 2.96), (.30, .085, .18), MATS["white"], rotation=(0, math.radians(-15), math.radians(-18)), bevel=.05)
    _cube("Bow_R", (.32, .99, 2.96), (.30, .085, .18), MATS["white"], rotation=(0, math.radians(15), math.radians(18)), bevel=.05)
    _cube("Ribbon_L", (-.20, 1.01, 2.55), (.12, .065, .38), MATS["white"], rotation=(math.radians(8), 0, math.radians(10)), bevel=.025)
    _cube("Ribbon_R", (.20, 1.01, 2.55), (.12, .065, .38), MATS["white"], rotation=(math.radians(-8), 0, math.radians(-10)), bevel=.025)
    for side, x in (("L", -.55), ("R", .55)):
        _cylinder("Leg_" + side, (x, 0, .70), .095, .78, MATS["dark"], vertices=8)
        _uv_sphere("Foot_" + side, (x, -.08, .25), (.36, .47, .21), MATS["yellow_light"], 12, 6)
    for side, x in (("L", -.40), ("R", .40)):
        _uv_sphere("Eye_" + side, (x, -.895, 4.10), (.105, .065, .14), MATS["black"], 12, 6)
    _tri_prism("Nose", (0, -.945, 3.77), .20, .16, .055, MATS["black"], rotation=(math.pi, 0, 0))
    _curve("Mouth_Center", [(0, -.955, 3.70), (0, -.965, 3.56)], .026, MATS["black"])
    _curve("Mouth_L", [(0, -.965, 3.56), (-.08, -.97, 3.48), (-.20, -.965, 3.53)], .026, MATS["black"])
    _curve("Mouth_R", [(0, -.965, 3.56), (.08, -.97, 3.48), (.20, -.965, 3.53)], .026, MATS["black"])
    for side, sign in (("L", -1), ("R", 1)):
        for idx, dz in enumerate((.13, 0, -.13), 1):
            x0 = sign * .62
            x1 = sign * 1.00
            _curve("Whisker_%s_%d" % (side, idx), [(x0, -.94, 3.76 + dz), (x1, -.91, 3.80 + dz * 1.18)], .018, MATS["black"])
    return "apron assembly, bow, legs, feet, and face built"


def build_baguette_and_arms():
    baguette = _profile_mesh(
        "Baguette", (0, -1.20, 3.10),
        [(-2.40, .44), (-2.25, .58), (-1.95, .66), (1.95, .66), (2.25, .58), (2.40, .44)],
        12, (.54, .33), MATS["bread"]
    )
    baguette.rotation_euler.y = math.radians(-42)
    baguette["separate_mesh"] = True
    baguette["pose_angle_degrees"] = 42.0
    baguette["front_offset"] = 1.20
    texture_path = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Textures/baker_cat_baguette_scores_v4.png"
    _apply_baguette_uv_texture(baguette, texture_path)
    _curve("Arm_L_UpperSupport", [(-1.18, -.12, 3.00), (-1.42, -.66, 2.92), (-1.14, -1.42, 3.18), (-.68, -1.52, 3.55)], .085, MATS["dark"])
    _curve("Arm_R_LowerWrap", [(1.18, -.10, 3.28), (1.44, -.66, 3.05), (1.12, -1.44, 2.72), (.58, -1.52, 2.48)], .085, MATS["dark"])
    return "diagonal baguette with five UV-textured scores and two supporting arms built"


def build_studio_and_render():
    global ROOT
    for obj in list(COLL.objects):
        if obj.name == PREFIX + "Ground" or obj.name == PREFIX + "Camera_Hero" or obj.name.startswith(PREFIX + "Light_"):
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    ground = bpy.context.object
    ground.name = PREFIX + "Ground"
    _move_to_collection(ground)
    _assign(ground, MATS["ground"])
    ground.parent = ROOT
    bpy.ops.object.camera_add(location=(4.2, -14.0, 5.5))
    cam = bpy.context.object
    cam.name = PREFIX + "Camera_Hero"
    _move_to_collection(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 8.05
    _look_at(cam, (0, 0, 3.1))
    bpy.context.scene.camera = cam
    for name, loc, energy, size, color in (
        ("Key", (-4.5, -6.0, 10.0), 620, 5.0, (1.0, .79, .58)),
        ("Fill", (5.5, -3.0, 6.5), 360, 4.0, (.65, .78, 1.0)),
        ("Rim", (2.0, 5.0, 8.5), 460, 3.5, (1.0, .48, .20)),
    ):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = PREFIX + "Light_" + name
        _move_to_collection(light)
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = color
        _look_at(light, (0, 0, 3.0))
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        pass
    scene.render.resolution_x = 800
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0.15
    scene.world.color = (0.035, 0.025, 0.02)
    if scene.world.use_nodes:
        bg = scene.world.node_tree.nodes.get("Background")
        if bg is None:
            bg = next((node for node in scene.world.node_tree.nodes if node.type == "BACKGROUND"), None)
        if bg is not None:
            if bg.inputs.get("Color"):
                bg.inputs["Color"].default_value = (0.035, 0.025, 0.02, 1.0)
            if bg.inputs.get("Strength"):
                bg.inputs["Strength"].default_value = .32
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.shading.type = "MATERIAL"
    blend_path = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_rebuild_v8.blend"
    render_path = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_rebuild_v8_preview.png"
    scene.render.filepath = render_path
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    bpy.ops.render.render(write_still=True)
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    for obj in COLL.objects:
        if obj.type in {"MESH", "CURVE", "EMPTY"} and not obj.name.endswith("Ground"):
            obj.hide_set(False)
            obj.select_set(True)
    bpy.context.view_layer.objects.active = ROOT
    glb_path = "/Users/kang-yumin/Documents/GitHub/new 3d/Art/Models/char_baker_cat_rebuild_v8.glb"
    try:
        bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB", use_selection=True, export_apply=True)
        glb_result = glb_path
    except Exception as exc:
        glb_result = "GLB export skipped: " + str(exc)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    return {"blend": blend_path, "render": render_path, "glb": glb_result, "objects": len(COLL.objects)}


def summarize():
    meshes = [o for o in COLL.objects if o.type == "MESH" and not o.name.endswith("Ground")]
    curves = [o for o in COLL.objects if o.type == "CURVE"]
    return {
        "collection": COLL.name,
        "mesh_count": len(meshes),
        "curve_count": len(curves),
        "independent_parts": sorted(o.name for o in meshes),
    }
