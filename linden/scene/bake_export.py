"""Bake Cycles lighting into texture atlases and export a compressed glb + colliders.

  blender -b scene/linden.blend -P scene/bake_export.py -- [--scale 0.25] [--samples 16] [--no-denoise]

Writes viewer/linden.glb, viewer/colliders.json and bake/*.png (the lightmaps).
"""
import json
import math
import os
import sys
import time

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(bpy.data.filepath))
ROOT = os.path.dirname(HERE)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SCALE = float(argv[argv.index("--scale") + 1]) if "--scale" in argv else 1.0
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 64
DENOISE = "--no-denoise" not in argv
ONLY = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
BAKE_DIR = os.path.join(ROOT, "bake")
VIEW_DIR = os.path.join(ROOT, "viewer")
os.makedirs(BAKE_DIR, exist_ok=True)
sc = bpy.context.scene
plan = json.load(open(os.path.join(ROOT, "plan.json")))

GLASS_MATS = {"Glass", "Frosted glass"}

# atlas name -> (collections, base size)
GROUPS = {
    "shell": (["Architecture/Walls"], 4096),
    "floors": (["Floors"], 2048),
    "ceilings": (["Ceilings", "Roof"], 2048),
    "openings": (["Windows", "Doors", "Railings", "Planters"], 2048),
    "living": (["F Living"], 2048),
    "dining": (["F Dining"], 2048),
    "kitchen": (["F Kitchen"], 2048),
    "patio": (["F Patio"], 2048),
    "rooms": (["F Rooms", "F Lights"], 4096),
    "ground": (["@Ground"], 1024),
}


def log(*a):
    print("[bake]", *a, flush=True)


def objects_for(spec):
    out = []
    for name in spec:
        if name.startswith("@"):
            out.append(bpy.data.objects[name[1:]])
        elif name == "Architecture/Walls":
            out.append(bpy.data.objects["Walls"])
        else:
            out += [o for o in bpy.data.collections[name].all_objects]
    return [o for o in out if o.type in ("MESH", "CURVE", "FONT")]


def is_glass(o):
    return bool(o.data.materials) and all(m and m.name in GLASS_MATS for m in o.data.materials)


def realize(objs):
    """Apply modifiers + parenting into plain world-space meshes."""
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
        me.transform(o.matrix_world)
        n = bpy.data.objects.new(o.name + "_r", me)
        sc.collection.objects.link(n)
        out.append(n)
    return out


def join(objs, name):
    bm = bmesh.new()
    mats = []
    for o in objs:
        remap = {}
        for i, m in enumerate(o.data.materials):
            if m not in mats:
                mats.append(m)
            remap[i] = mats.index(m)
        me = o.data
        for p in me.polygons:
            p.material_index = remap.get(p.material_index, 0)
        bm.from_mesh(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    for o in objs:
        d = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(d)
    return ob


def lightmap_uv(ob):
    me = ob.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name="Lightmap")
    for o in sc.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, area_weight=0.0,
                             scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    uv = me.uv_layers[0].data
    us = [d.uv.x for d in uv]
    vs = [d.uv.y for d in uv]
    log(f"{ob.name}: {len(me.polygons)} faces, uv x {min(us):.3f}..{max(us):.3f} y {min(vs):.3f}..{max(vs):.3f}")


def bake(ob, name, size):
    img = bpy.data.images.new("LM_" + name, size, size, alpha=False, float_buffer=True)
    nodes = []
    for m in ob.data.materials:
        if not m or not m.use_nodes:
            continue
        n = m.node_tree.nodes.new("ShaderNodeTexImage")
        n.image = img
        m.node_tree.nodes.active = n
        nodes.append((m, n))
    for o in sc.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    b = sc.render.bake
    b.use_pass_direct = b.use_pass_indirect = True
    b.use_pass_diffuse = b.use_pass_emit = True
    b.use_pass_glossy = b.use_pass_transmission = False
    b.margin = max(4, size // 256)
    b.margin_type = "EXTEND"
    t = time.time()
    bpy.ops.object.bake(type="COMBINED")
    log(f"{name}: {size}px baked in {time.time() - t:.0f}s")
    for m, n in nodes:
        m.node_tree.nodes.remove(n)
    return img


def denoise(img, size):
    """OIDN through the compositor (bake has no built-in denoiser)."""
    sc.use_nodes = True if hasattr(sc, "use_nodes") else None
    tree = sc.compositing_node_group if hasattr(sc, "compositing_node_group") else sc.node_tree
    if tree is None:
        tree = bpy.data.node_groups.new("Denoise", "CompositorNodeTree")
        sc.compositing_node_group = tree
    tree.nodes.clear()
    i = tree.nodes.new("CompositorNodeImage")
    i.image = img
    d = tree.nodes.new("CompositorNodeDenoise")
    for k, v in (("prefilter", "ACCURATE"), ("quality", "HIGH")):
        if hasattr(d, k):
            try:
                setattr(d, k, v)
            except TypeError:
                pass
    try:
        o = tree.nodes.new("NodeGroupOutput")
        tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        tree.links.new(d.outputs[0], o.inputs[0])
    except Exception:
        o = tree.nodes.new("CompositorNodeComposite")
        tree.links.new(d.outputs[0], o.inputs[0])
    tree.links.new(i.outputs[0], d.inputs[0])
    r = sc.render
    keep = (r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath)
    r.resolution_x = r.resolution_y = size
    r.resolution_percentage = 100
    r.filepath = os.path.join(BAKE_DIR, "_dn.png")
    sc.render.image_settings.file_format = "PNG"
    # render the compositor only: no scene objects visible
    hidden = [o for o in sc.objects if not o.hide_render]
    for o in hidden:
        o.hide_render = True
    world = sc.world
    sc.world = None
    sc.cycles.samples = 1
    bpy.ops.render.render(write_still=True)
    for o in hidden:
        o.hide_render = False
    sc.world = world
    r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath = keep
    out = bpy.data.images.load(os.path.join(BAKE_DIR, "_dn.png"))
    return out


def to_display(img, name):
    """Write the baked radiance through the scene's view transform (AgX) as the final texture."""
    path = os.path.join(BAKE_DIR, name + ".png")
    s = sc.render.image_settings
    s.file_format = "PNG"
    s.color_mode = "RGB"
    s.color_depth = "8"
    img.save_render(path, scene=sc)
    return path


def viewer_material(name, tex_path):
    m = bpy.data.materials.new("Baked " + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(tex_path)
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 1.0
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


def colliders(furn_objs):
    """2D blockers for the walkthrough: wall pieces (doors cut out), columns, rails, furniture."""
    rects = []
    for w in plan["walls"]:
        a, b = Vector(w["a"]), Vector(w["b"])
        horiz = abs(b.x - a.x) > abs(b.y - a.y)
        lo_s, hi_s = (min(a.x, b.x), max(a.x, b.x)) if horiz else (min(a.y, b.y), max(a.y, b.y))
        gaps = []
        for o in plan["openings"]:
            if o["wall"] != w["id"] or o["sill"] > 0.3 or o["type"] == "entry_door":
                continue
            oa, ob = Vector(o["a"]), Vector(o["b"])
            g = (min(oa.x, ob.x), max(oa.x, ob.x)) if horiz else (min(oa.y, ob.y), max(oa.y, ob.y))
            if o["type"] == "sliding_door":   # only the open half is passable
                g = (g[0] + (g[1] - g[0]) / 2, g[1])
            gaps.append(g)
        gaps.sort()
        cur = lo_s
        t = w["thickness"] / 2
        for g0, g1 in gaps + [(hi_s, hi_s)]:
            if g0 - cur > 0.01:
                if horiz:
                    rects.append([cur, a.y - t, g0, a.y + t])
                else:
                    rects.append([a.x - t, cur, a.x + t, g0])
            cur = max(cur, g1)
    for c in plan["columns"] + plan["fins"]:
        rects.append([c["min"][0], c["min"][1], c["max"][0], c["max"][1]])
    for p in plan["planters"]:
        rects.append([p["min"][0], p["min"][1], p["max"][0], p["max"][1]])
    for r in plan["railings"]:
        pts = r["points"]
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            rects.append([min(x0, x1) - 0.03, min(y0, y1) - 0.03, max(x0, x1) + 0.03, max(y0, y1) + 0.03])
    for o in plan["glass_partitions"]:
        (x0, y0), (x1, y1) = o["a"], o["b"]
        rects.append([min(x0, x1) - 0.02, min(y0, y1) - 0.02, max(x0, x1) + 0.02, max(y0, y1) + 0.02])
    dg = bpy.context.evaluated_depsgraph_get()
    for o in furn_objs:
        if o.type != "MESH":
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        z0, z1 = min(p.z for p in bb), max(p.z for p in bb)
        if z0 > 1.2 or z1 < 0.25:      # rugs, wall-hung items, ceiling fittings: walkable
            continue
        xs, ys = [p.x for p in bb], [p.y for p in bb]
        if (max(xs) - min(xs)) * (max(ys) - min(ys)) < 0.004:
            continue
        rects.append([min(xs), min(ys), max(xs), max(ys)])
    return [[round(v, 3) for v in r] for r in rects]


def main():
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 4
    sc.cycles.glossy_bounces = 1
    sc.cycles.use_guiding = True
    sc.render.bake.target = "IMAGE_TEXTURES"
    # crop the ground to the neighbourhood before baking
    g = bpy.data.objects["Ground"]
    g.dimensions = (36, 36, g.dimensions.z)
    g.location.x, g.location.y = 6.0, 5.5

    furn_src = list(bpy.data.collections["Furniture"].all_objects)
    coll = colliders(furn_src)
    spawn = [7.0, 8.2, 0.0]
    with open(os.path.join(VIEW_DIR, "colliders.json"), "w") as f:
        json.dump({"rects": coll, "spawn": spawn, "eye": 1.6, "radius": 0.22,
                   "rooms": [{"name": r["name"], "polygon": r["polygon"]} for r in plan["rooms"]],
                   "walls": [{"a": w["a"], "b": w["b"], "t": w["thickness"]} for w in plan["walls"]],
                   "openings": [{"a": o["a"], "b": o["b"], "type": o["type"]} for o in plan["openings"]]}, f)
    log(f"colliders: {len(coll)} rects")

    # phase 1: realize + join every atlas group (and the glass) BEFORE baking, then hide the
    # originals: a copy baked while its original still occupies the same surface is self-shadowed
    built = []
    glass_src = []
    originals = []
    for name, (spec, base) in GROUPS.items():
        src = objects_for(spec)
        originals += src
        glass_src += [o for o in src if is_glass(o)]
        src = [o for o in src if not is_glass(o)]
        if src:
            built.append((join(realize(src), "LM_" + name), name, base))
    gl = join(realize(glass_src), "Glass")
    for o in originals:
        o.hide_render = True
    # phase 2: lightmap UVs + bake each group against the realized scene
    export = []
    for ob, name, base in built:
        if ONLY and name not in ONLY:
            continue
        lightmap_uv(ob)
        size = max(128, int(base * SCALE))
        # furniture atlases are full of tiny islands: the denoiser would smear colour between
        # unrelated neighbours, so they get more samples instead
        big_islands = name in ("shell", "floors", "ceilings", "ground")
        sc.cycles.samples = SAMPLES if big_islands else (SAMPLES * 2 if name == "rooms" else SAMPLES * 3)
        img = bake(ob, name, size)
        if DENOISE and big_islands:
            img = denoise(img, size)
        path = to_display(img, name)
        export.append((ob, name, path))
    # glass: one mesh, plain material (viewer makes it transparent)
    gm = bpy.data.materials.new("Glass_viewer")
    gl.data.materials.clear()
    gl.data.materials.append(gm)

    # swap in baked materials and export only the baked meshes + glass
    for ob, name, path in export:
        ob.data.materials.clear()
        ob.data.materials.append(viewer_material(name, path))
    keep = {ob for ob, _, _ in export} | {gl}
    for o in list(sc.objects):
        if o not in keep:
            bpy.data.objects.remove(o)
    for o in sc.objects:
        o.select_set(True)
    out = os.path.join(VIEW_DIR, "linden.glb")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True,
                              export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=6,
                              export_draco_position_quantization=14,
                              export_draco_texcoord_quantization=12,
                              export_image_format="JPEG", export_jpeg_quality=92,
                              export_materials="EXPORT", export_normals=False,
                              export_yup=True, export_apply=True, export_lights=False, export_cameras=False)
    log("exported", out, f"{os.path.getsize(out) / 1e6:.1f} MB")


main()
