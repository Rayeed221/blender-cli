"""modelkit: small, dependency-free helpers for building 3D models with bpy.

Every model in models/<name>/build.py imports this module. The helpers wrap
the verbose parts of bpy (materials, modifiers, procedural meshes, camera
framing) so a build script reads like a description of the object.

Conventions
-----------
* Units are metres, +Z is up, models sit on the ground plane (z = 0) and are
  centred on the origin in X/Y unless there is a reason not to.
* Colours are "#rrggbb" hex strings (sRGB) or (r, g, b[, a]) tuples in linear
  space.
* Everything a build creates for the model goes into the "Model" collection;
  camera, lights and floor go into "Studio" so they can be left out of
  exports (see finalize()).
"""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

__all__ = [
    "reset", "seed", "rgba", "material", "assign",
    "cube", "cylinder", "cone", "sphere", "icosphere", "torus", "plane",
    "mesh_from_data", "lathe", "extrude_polygon", "tube_along", "text",
    "bevel", "subsurf", "solidify", "mirror", "array", "boolean",
    "displace_noise", "apply_modifiers", "clean_material_slots", "uv_unwrap", "shade_smooth", "shade_flat",
    "join", "parent", "apply_transforms", "origin_to_bottom", "drop_to_floor",
    "bounds", "studio", "finalize", "report",
]

MODEL_COLLECTION = "Model"
STUDIO_COLLECTION = "Studio"


# --------------------------------------------------------------------------
# Scene
# --------------------------------------------------------------------------

def reset(engine="CYCLES", fps=24):
    """Empty the open file: objects, meshes, materials, curves, lights, cameras."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.curves,
                 bpy.data.lights, bpy.data.cameras, bpy.data.textures,
                 bpy.data.node_groups, bpy.data.images):
        for block in list(coll):
            if block.users == 0 or coll is not bpy.data.images:
                try:
                    coll.remove(block)
                except (RuntimeError, ReferenceError):
                    pass
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.render.fps = fps
    if engine:
        sc.render.engine = engine
    _collection(MODEL_COLLECTION)
    return sc


def seed(value=0):
    """Seed Python's RNG so procedural models are reproducible."""
    random.seed(value)


def _collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def _link(obj, collection=MODEL_COLLECTION):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    _collection(collection).objects.link(obj)
    return obj


# --------------------------------------------------------------------------
# Colour & materials
# --------------------------------------------------------------------------

def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgba(color, alpha=1.0):
    """'#rrggbb' | '#rrggbbaa' | (r,g,b[,a]) -> linear (r,g,b,a)."""
    if isinstance(color, str):
        h = color.lstrip("#")
        if len(h) not in (6, 8):
            raise ValueError("hex colour must be #rrggbb or #rrggbbaa: " + color)
        vals = [int(h[i:i + 2], 16) / 255 for i in range(0, len(h), 2)]
        rgb = [_srgb_to_linear(v) for v in vals[:3]]
        a = vals[3] if len(vals) == 4 else alpha
        return (*rgb, a)
    c = tuple(color)
    return c if len(c) == 4 else (*c, alpha)


def _set_input(bsdf, names, value):
    for n in names:
        sock = bsdf.inputs.get(n)
        if sock is not None:
            sock.default_value = value
            return True
    return False


def material(name, color="#cccccc", roughness=0.5, metallic=0.0, alpha=1.0,
             emission=None, emission_strength=1.0, transmission=0.0, ior=1.45):
    """Get or create a Principled BSDF material. Reuses an existing one by name."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    col = rgba(color, alpha)
    mat.diffuse_color = col  # viewport / workbench colour
    if bsdf is not None:
        _set_input(bsdf, ["Base Color"], col)
        _set_input(bsdf, ["Roughness"], roughness)
        _set_input(bsdf, ["Metallic"], metallic)
        _set_input(bsdf, ["Alpha"], alpha)
        _set_input(bsdf, ["IOR"], ior)
        _set_input(bsdf, ["Transmission Weight", "Transmission"], transmission)
        if emission is not None:
            _set_input(bsdf, ["Emission Color", "Emission"], rgba(emission))
            _set_input(bsdf, ["Emission Strength"], emission_strength)
    if alpha < 1.0 and hasattr(mat, "blend_method"):
        try:
            mat.blend_method = "BLEND"
        except (TypeError, AttributeError):
            pass
    mat.roughness = roughness
    mat.metallic = metallic
    return mat


def assign(obj, mat, slot=None):
    """Assign a material (object or name) to obj; append a slot unless slot given."""
    if isinstance(mat, str):
        mat = bpy.data.materials.get(mat) or material(mat)
    if obj.data is None or not hasattr(obj.data, "materials"):
        return obj
    if slot is None:
        if mat.name not in [m.name for m in obj.data.materials if m]:
            obj.data.materials.append(mat)
    else:
        while len(obj.data.materials) <= slot:
            obj.data.materials.append(None)
        obj.data.materials[slot] = mat
    return obj


# --------------------------------------------------------------------------
# Primitives (built from bmesh, no operators: deterministic and context-free)
# --------------------------------------------------------------------------

def _finish(bm, name, location, rotation, scale, mat, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    _link(obj)
    obj.location = location
    obj.rotation_euler = [math.radians(a) for a in rotation]
    obj.scale = scale if hasattr(scale, "__len__") else (scale, scale, scale)
    if mat is not None:
        assign(obj, mat)
    if smooth:
        shade_smooth(obj)
    return obj


def cube(name="Cube", size=(1, 1, 1), location=(0, 0, 0), rotation=(0, 0, 0),
         scale=1, mat=None):
    """Box with full dimensions `size` (x, y, z), centred on `location`."""
    sx, sy, sz = size if hasattr(size, "__len__") else (size, size, size)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    return _finish(bm, name, location, rotation, scale, mat)


def cylinder(name="Cylinder", radius=0.5, depth=1.0, segments=32, location=(0, 0, 0),
             rotation=(0, 0, 0), scale=1, mat=None, cap=True, radius_top=None, smooth=True):
    """Cylinder (or truncated cone with radius_top) along Z, centred on location."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius if radius_top is None else radius_top,
                          depth=depth)
    obj = _finish(bm, name, location, rotation, scale, mat, smooth)
    return obj


def cone(name="Cone", radius=0.5, depth=1.0, segments=32, **kw):
    return cylinder(name, radius=radius, depth=depth, segments=segments, radius_top=0.0, **kw)


def sphere(name="Sphere", radius=0.5, segments=32, rings=16, location=(0, 0, 0),
           rotation=(0, 0, 0), scale=1, mat=None, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    return _finish(bm, name, location, rotation, scale, mat, smooth)


def icosphere(name="Icosphere", radius=0.5, subdivisions=2, location=(0, 0, 0),
              rotation=(0, 0, 0), scale=1, mat=None, smooth=False):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, radius=radius)
    return _finish(bm, name, location, rotation, scale, mat, smooth)


def torus(name="Torus", major_radius=0.5, minor_radius=0.15, major_segments=48,
          minor_segments=16, location=(0, 0, 0), rotation=(0, 0, 0), scale=1, mat=None,
          smooth=True):
    verts, faces = [], []
    for i in range(major_segments):
        u = 2 * math.pi * i / major_segments
        for j in range(minor_segments):
            v = 2 * math.pi * j / minor_segments
            r = major_radius + minor_radius * math.cos(v)
            verts.append((r * math.cos(u), r * math.sin(u), minor_radius * math.sin(v)))
    for i in range(major_segments):
        for j in range(minor_segments):
            a = i * minor_segments + j
            b = ((i + 1) % major_segments) * minor_segments + j
            c = ((i + 1) % major_segments) * minor_segments + (j + 1) % minor_segments
            d = i * minor_segments + (j + 1) % minor_segments
            faces.append((a, b, c, d))
    return mesh_from_data(name, verts, faces, location=location, rotation=rotation,
                          scale=scale, mat=mat, smooth=smooth)


def plane(name="Plane", size=(2, 2), location=(0, 0, 0), rotation=(0, 0, 0), scale=1,
          mat=None, subdivisions=0):
    sx, sy = size if hasattr(size, "__len__") else (size, size)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=subdivisions + 1, y_segments=subdivisions + 1,
                          size=0.5)
    bmesh.ops.scale(bm, vec=(sx, sy, 1), verts=bm.verts)
    return _finish(bm, name, location, rotation, scale, mat)


def mesh_from_data(name, verts, faces, edges=(), location=(0, 0, 0), rotation=(0, 0, 0),
                   scale=1, mat=None, smooth=False):
    """Mesh from raw vertex/face lists: the escape hatch for any shape."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], list(edges), [tuple(f) for f in faces])
    me.validate()
    me.update()
    obj = bpy.data.objects.new(name, me)
    _link(obj)
    obj.location = location
    obj.rotation_euler = [math.radians(a) for a in rotation]
    obj.scale = scale if hasattr(scale, "__len__") else (scale, scale, scale)
    if mat is not None:
        assign(obj, mat)
    if smooth:
        shade_smooth(obj)
    return obj


def lathe(name, profile, segments=48, location=(0, 0, 0), mat=None, smooth=True,
          close_bottom=True, close_top=False):
    """Revolve a 2D profile [(radius, z), ...] around Z. Vases, bottles, lamps, wheels.

    The profile is ordered bottom to top. A point with radius 0 sits on the axis.
    """
    ring = len(profile)
    verts, faces = [], []
    for s in range(segments):
        a = 2 * math.pi * s / segments
        ca, sa = math.cos(a), math.sin(a)
        for r, z in profile:
            verts.append((r * ca, r * sa, z))
    for s in range(segments):
        n = (s + 1) % segments
        for i in range(ring - 1):
            faces.append((s * ring + i, n * ring + i, n * ring + i + 1, s * ring + i + 1))
    if close_bottom and profile[0][0] > 0:
        faces.append(tuple(s * ring for s in reversed(range(segments))))
    if close_top and profile[-1][0] > 0:
        faces.append(tuple(s * ring + ring - 1 for s in range(segments)))
    obj = mesh_from_data(name, verts, faces, location=location, mat=mat, smooth=smooth)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def extrude_polygon(name, points, depth=0.1, location=(0, 0, 0), rotation=(0, 0, 0),
                    mat=None, holes=()):
    """Extrude a closed 2D outline [(x, y), ...] (counter-clockwise) along +Z by depth.

    Gears, logos, brackets, signs, floor plans. Holes are not cut here: use boolean().
    """
    n = len(points)
    verts = [(x, y, 0.0) for x, y in points] + [(x, y, depth) for x, y in points]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    obj = mesh_from_data(name, verts, faces, location=location, rotation=rotation, mat=mat)
    return obj


def tube_along(name, points, radius=0.05, resolution=8, mat=None, cyclic=False,
               to_mesh=True):
    """A round tube following a polyline [(x, y, z), ...]: pipes, cables, handles, frames."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = max(1, resolution // 4)
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, co in zip(sp.points, points):
        p.co = (*co, 1.0)
    sp.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, cu)
    _link(obj)
    if mat is not None:
        assign(obj, mat)
    if to_mesh:
        obj = _curve_to_mesh(obj)
    return obj


def text(name, body, size=0.5, depth=0.05, location=(0, 0, 0), rotation=(90, 0, 0),
         mat=None, align="CENTER", to_mesh=True):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = depth
    cu.align_x = align
    obj = bpy.data.objects.new(name, cu)
    _link(obj)
    obj.location = location
    obj.rotation_euler = [math.radians(a) for a in rotation]
    if mat is not None:
        assign(obj, mat)
    if to_mesh:
        obj = _curve_to_mesh(obj)
    return obj


def _curve_to_mesh(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, depsgraph=dg)
    new = bpy.data.objects.new(obj.name, me)
    new.matrix_world = obj.matrix_world.copy()
    name = obj.name
    curve = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.curves.remove(curve)
    new.name = name
    _link(new)
    return new


# --------------------------------------------------------------------------
# Modifiers
# --------------------------------------------------------------------------

def bevel(obj, width=0.02, segments=3, angle=30, harden=True):
    m = obj.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle)
    if hasattr(m, "harden_normals"):
        m.harden_normals = harden
    return m


def subsurf(obj, levels=2, render_levels=None):
    m = obj.modifiers.new("Subdivision", "SUBSURF")
    m.levels = levels
    m.render_levels = levels if render_levels is None else render_levels
    return m


def solidify(obj, thickness=0.02, offset=-1.0):
    m = obj.modifiers.new("Solidify", "SOLIDIFY")
    m.thickness = thickness
    m.offset = offset
    return m


def mirror(obj, axes="X", mirror_object=None):
    m = obj.modifiers.new("Mirror", "MIRROR")
    m.use_axis = ["X" in axes, "Y" in axes, "Z" in axes]
    m.use_clip = True
    if mirror_object is not None:
        m.mirror_object = mirror_object
    return m


def array(obj, count=3, offset=(1.1, 0, 0), relative=True):
    m = obj.modifiers.new("Array", "ARRAY")
    m.count = count
    m.use_relative_offset = relative
    m.use_constant_offset = not relative
    if relative:
        m.relative_offset_displace = offset
    else:
        m.constant_offset_displace = offset
    return m


def boolean(obj, cutter, operation="DIFFERENCE", apply=True, delete_cutter=True):
    """Boolean obj with cutter (DIFFERENCE | UNION | INTERSECT)."""
    m = obj.modifiers.new("Boolean", "BOOLEAN")
    m.operation = operation
    m.object = cutter
    if hasattr(m, "solver"):
        m.solver = "EXACT"
    cutter.hide_render = True
    cutter.display_type = "WIRE"
    if apply:
        apply_modifiers(obj, only=[m.name])
        clean_material_slots(obj)
        if delete_cutter:
            me = cutter.data
            bpy.data.objects.remove(cutter, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    return obj


def displace_noise(obj, strength=0.1, scale=0.5, seed_value=0):
    """Organic lumpiness (rocks, terrain, foliage) via a Clouds texture displace."""
    tex = bpy.data.textures.new(obj.name + "_noise", "CLOUDS")
    tex.noise_scale = scale
    m = obj.modifiers.new("Displace", "DISPLACE")
    m.texture = tex
    m.strength = strength
    m.texture_coords = "OBJECT" if seed_value == 0 else "GLOBAL"
    return m


def clean_material_slots(obj):
    """Drop empty or duplicate material slots (booleans add them) and remap faces."""
    me = obj.data
    if not hasattr(me, "materials"):
        return obj
    old = list(me.materials)
    keep = []
    for m in old:
        if m is not None and m not in keep:
            keep.append(m)
    if len(keep) == len(old):
        return obj
    remap = [keep.index(m) if m in keep else 0 for m in old]
    idx = [remap[p.material_index] if p.material_index < len(remap) else 0 for p in me.polygons]
    me.materials.clear()
    for m in keep:
        me.materials.append(m)
    for p, i in zip(me.polygons, idx):
        p.material_index = i
    return obj


def uv_unwrap(obj, angle=66.0, margin=0.02):
    """Smart-project UVs so the mesh can take image textures (and exports carry UVs)."""
    if obj.type != "MESH" or not obj.data.polygons:
        return obj
    view_layer = bpy.context.view_layer
    prev = view_layer.objects.active
    for o in view_layer.objects:
        o.select_set(o == obj)
    view_layer.objects.active = obj
    try:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin)
    finally:
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        view_layer.objects.active = prev
    return obj


def apply_modifiers(obj, only=None):
    """Bake modifiers into the mesh data (all of them, or the names in `only`)."""
    dg = bpy.context.evaluated_depsgraph_get()
    keep = [] if only is None else [m for m in obj.modifiers if m.name not in only]
    saved = [(m, m.show_viewport) for m in keep]
    for m, _ in saved:
        m.show_viewport = False
    dg.update()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, depsgraph=dg)
    old = obj.data
    obj.data = me
    for m in list(obj.modifiers):
        if only is None or m.name in only:
            obj.modifiers.remove(m)
    for m, vis in saved:
        m.show_viewport = vis
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return obj


# --------------------------------------------------------------------------
# Shading, hierarchy, transforms
# --------------------------------------------------------------------------

def shade_smooth(obj, angle=None):
    """Smooth shading. With `angle` (deg), faces sharper than it stay flat (4.1+ aware)."""
    me = obj.data
    if not hasattr(me, "polygons"):
        return obj
    if hasattr(me, "shade_smooth"):
        me.shade_smooth()
    else:
        for p in me.polygons:
            p.use_smooth = True
    if angle is not None:
        if hasattr(me, "set_sharp_from_angle"):
            me.set_sharp_from_angle(angle=math.radians(angle))
        elif hasattr(me, "use_auto_smooth"):
            me.use_auto_smooth = True
            me.auto_smooth_angle = math.radians(angle)
    return obj


def shade_flat(obj):
    me = obj.data
    if hasattr(me, "shade_flat"):
        me.shade_flat()
    else:
        for p in me.polygons:
            p.use_smooth = False
    return obj


def join(objs, name=None):
    """Join mesh objects into the first one (modifiers are applied first)."""
    objs = [o for o in objs if o is not None]
    target = objs[0]
    bm = bmesh.new()
    inv = target.matrix_world.inverted()
    mats = []
    for o in objs:
        if o.modifiers:
            apply_modifiers(o)
        if o.type != "MESH":
            continue
        local = {}
        for i, m in enumerate(o.data.materials):
            if m is not None and m.name not in mats:
                mats.append(m.name)
            local[i] = mats.index(m.name) if m is not None else 0
        tmp = o.data.copy()
        tmp.transform(inv @ o.matrix_world)
        for p in tmp.polygons:
            p.material_index = local.get(p.material_index, 0)
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    me = bpy.data.meshes.new(name or target.name)
    bm.to_mesh(me)
    bm.free()
    for mname in mats:
        me.materials.append(bpy.data.materials[mname])
    old = target.data
    target.data = me
    for o in objs[1:]:
        d = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if d is not None and getattr(d, "users", 1) == 0 and isinstance(d, bpy.types.Mesh):
            bpy.data.meshes.remove(d)
    if old.users == 0:
        bpy.data.meshes.remove(old)
    if name:
        target.name = name
    return target


def parent(child, parent_obj, keep_transform=True):
    mw = child.matrix_world.copy()
    child.parent = parent_obj
    if keep_transform:
        child.matrix_parent_inverse = parent_obj.matrix_world.inverted()
        child.matrix_world = mw
    return child


def apply_transforms(obj, location=False, rotation=True, scale=True):
    """Bake rotation/scale (and optionally location) into mesh data."""
    loc, rot, sca = obj.matrix_basis.decompose()
    m = Matrix.Identity(4)
    if location:
        m = m @ Matrix.Translation(loc)
    if rotation:
        m = m @ rot.to_matrix().to_4x4()
    if scale:
        m = m @ Matrix.Diagonal((*sca, 1.0))
    if hasattr(obj.data, "transform"):
        obj.data.transform(m)
    obj.location = (0, 0, 0) if location else loc
    obj.rotation_euler = (0, 0, 0) if rotation else rot.to_euler()
    obj.scale = (1, 1, 1) if scale else sca
    return obj


def origin_to_bottom(obj):
    """Move the origin to the bottom-centre of the mesh, keeping it in place."""
    me = obj.data
    if not me.vertices:
        return obj
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    off = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    me.transform(Matrix.Translation(-off))
    obj.location = obj.matrix_world @ off
    return obj


def drop_to_floor(objs=None, z=0.0):
    """Translate the model so its lowest point sits on z."""
    objs = objs or _model_objects()
    lo, _ = bounds(objs)
    dz = z - lo.z
    for o in objs:
        if o.parent is None:
            o.location.z += dz
    return dz


def bounds(objs=None):
    """World-space (min, max) Vectors of the evaluated geometry of objs."""
    objs = objs or _model_objects()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for o in objs:
        ev = o.evaluated_get(dg)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    if lo.x == math.inf:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    return lo, hi


def _model_objects():
    coll = bpy.data.collections.get(MODEL_COLLECTION)
    objs = list(coll.all_objects) if coll else list(bpy.context.scene.objects)
    return [o for o in objs if o.type in {"MESH", "CURVE", "FONT", "SURFACE", "META"}]


# --------------------------------------------------------------------------
# Studio: camera framing, lights, floor, world
# --------------------------------------------------------------------------

def studio(floor=True, floor_color="#d8d8d8", background="#f2f2f2", key_energy=None,
           view=(1.0, -1.25, 0.75), lens=50, margin=1.15, resolution=(1280, 1280)):
    """Frame the model with a camera, three area lights, a floor and a soft world."""
    sc = bpy.context.scene
    lo, hi = bounds()
    center = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 0.01)

    # world
    world = sc.world or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs[0].default_value = rgba(background)
        bg.inputs[1].default_value = 0.6

    # camera: pull back until the bounding sphere fits the narrower FOV
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = lens
    cam_data.clip_end = max(1000, radius * 100)
    cam = bpy.data.objects.new("Camera", cam_data)
    _link(cam, STUDIO_COLLECTION)
    sc.render.resolution_x, sc.render.resolution_y = resolution
    fov = cam_data.angle  # along the larger sensor dimension
    aspect = resolution[0] / resolution[1]
    # sensor_fit AUTO: `angle` spans the longer image side; fit to the shorter one
    narrow = 2 * math.atan(math.tan(fov / 2) * min(aspect, 1 / aspect))
    dist = radius * margin / math.sin(narrow / 2)
    direction = Vector(view).normalized()
    cam.location = center + direction * dist
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam

    # three-point area lights scaled to the model
    # lights sit at 4x radius, so irradiance stays constant when energy ~ radius^2
    energy = key_energy if key_energy is not None else 500 * radius ** 2
    rigs = [("Key", (1.0, -1.0, 1.4), 1.0, 2.0),
            ("Fill", (-1.4, -0.6, 0.8), 0.35, 3.0),
            ("Rim", (-0.4, 1.4, 1.2), 0.6, 1.5)]
    for name, d, mult, size in rigs:
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy * mult
        ld.size = radius * size
        lo_obj = bpy.data.objects.new(name, ld)
        _link(lo_obj, STUDIO_COLLECTION)
        lo_obj.location = center + Vector(d).normalized() * radius * 4
        lo_obj.rotation_euler = (center - lo_obj.location).to_track_quat("-Z", "Y").to_euler()

    if floor:
        fl = plane("Floor", size=(radius * 20, radius * 20), location=(center.x, center.y, lo.z),
                   mat=material("Studio_Floor", floor_color, roughness=0.8))
        _link(fl, STUDIO_COLLECTION)
        # renders, but stays out of viewport-based tools (snapshot framing, verify)
        fl.hide_viewport = True
    return cam


def finalize(render_samples=64, uv=True):
    """Unwrap meshes without UVs, select only the model (so `export --selected`
    skips the studio) and set render defaults."""
    sc = bpy.context.scene
    model = [o for o in _model_objects()]
    if uv:
        for o in model:
            if o.type == "MESH" and not o.data.uv_layers:
                uv_unwrap(o)
    for o in sc.objects:
        o.select_set(False)
    for o in model:
        o.select_set(True)
    if model:
        bpy.context.view_layer.objects.active = model[0]
    if sc.render.engine == "CYCLES":
        sc.cycles.samples = render_samples
        sc.cycles.use_denoising = True
        sc.cycles.device = "CPU"
    return model


def report():
    """Facts about the built model, for the build's JSON result."""
    objs = _model_objects()
    lo, hi = bounds(objs)
    dg = bpy.context.evaluated_depsgraph_get()
    verts = faces = tris = 0
    for o in objs:
        ev = o.evaluated_get(dg)
        try:
            me = ev.to_mesh()
        except RuntimeError:
            continue
        verts += len(me.vertices)
        faces += len(me.polygons)
        tris += sum(len(p.vertices) - 2 for p in me.polygons)
        ev.to_mesh_clear()
    return {
        "objects": [o.name for o in objs],
        "materials": sorted({m.name for o in objs for m in getattr(o.data, "materials", []) if m}),
        "vertices": verts,
        "faces": faces,
        "triangles": tris,
        "dimensions_m": [round(v, 4) for v in (hi - lo)],
        "bounds_min": [round(v, 4) for v in lo],
        "bounds_max": [round(v, 4) for v in hi],
    }
