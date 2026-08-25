import bpy
import json
import os


ALLOWED_FILES = {
    "char_baker_cat_round_xy_v12.blend",
    "char_baker_cat_rigged.blend",
}


def main():
    basename = os.path.basename(bpy.data.filepath)
    if basename not in ALLOWED_FILES:
        raise RuntimeError(f"Refusing to clean unexpected file: {bpy.data.filepath}")

    warm_white = bpy.data.materials.get("BC3_Mat_Warm_White")
    hat_puff = bpy.data.objects.get("BC3_Hat_Puff")
    if warm_white is None or hat_puff is None:
        raise RuntimeError("BC3_Hat_Puff or BC3_Mat_Warm_White is missing")

    hat_puff.data.materials.clear()
    hat_puff.data.materials.append(warm_white)

    legacy_material = bpy.data.materials.get("MAT_char_baker_cat_palette")
    removed_objects = []
    for obj in list(bpy.data.objects):
        uses_legacy_palette = any(
            slot.material == legacy_material for slot in obj.material_slots
        )
        if uses_legacy_palette or "ground" in obj.name.lower():
            removed_objects.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)

    legacy_root = bpy.data.objects.get("ROOT_char_baker_cat")
    if legacy_root is not None and not legacy_root.children:
        bpy.data.objects.remove(legacy_root, do_unlink=True)

    legacy_collection = bpy.data.collections.get("CHARACTER_char_baker_cat")
    if legacy_collection is not None and not legacy_collection.objects:
        bpy.data.collections.remove(legacy_collection)

    removable_material_names = {"MAT_char_baker_cat_palette", "BC3_Mat_Ground"}
    removed_meshes = []
    for mesh in list(bpy.data.meshes):
        mesh_material_names = {mat.name for mat in mesh.materials if mat is not None}
        if mesh.users == 0 and mesh_material_names & removable_material_names:
            removed_meshes.append(mesh.name)
            bpy.data.meshes.remove(mesh)

    removed_materials = []
    for material_name in removable_material_names:
        material = bpy.data.materials.get(material_name)
        if material is not None and material.users == 0:
            removed_materials.append(material_name)
            bpy.data.materials.remove(material)

    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print("BAKER_CAT_CLEANUP_JSON=" + json.dumps({
        "file": bpy.data.filepath,
        "hat_materials": [mat.name for mat in hat_puff.data.materials],
        "removed_objects": removed_objects,
        "removed_meshes": removed_meshes,
        "removed_materials": removed_materials,
    }, ensure_ascii=False))


main()
