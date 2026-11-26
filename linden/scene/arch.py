"""Architecture from plan.json: wall shell with real openings, floors, ceilings, roof,
windows, doors, railings and planters. Imported by build_scene.py (runs inside Blender)."""
import math
import bmesh
import bpy
from mathutils import Vector

from mats import M

SLAB = 0.15
PARAPET = 0.9


def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def link(obj, c):
    for u in list(obj.users_collection):
        u.objects.unlink(obj)
    c.objects.link(obj)
    return obj


def box(name, lo, hi, mat=None, c=None):
    """Axis-aligned box from corner lo to hi (world). Origin at the box's bottom centre."""
    lo, hi = Vector(lo), Vector(hi)
    size = hi - lo
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, size.z / 2), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)
    if mat:
        me.materials.append(mat)
    link(o, c or bpy.context.scene.collection)
    return o


def prism(name, poly, z0, z1, mat=None, c=None, top_only=False):
    """Extrude a 2D polygon from z0 to z1 (polygon made CCW automatically)."""
    pts = [tuple(p) for p in poly]
    area = sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts)))
    if area < 0:
        pts.reverse()
    n = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces = [tuple(range(n, 2 * n))]
    if not top_only:
        faces.append(tuple(reversed(range(n))))
        faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    if mat:
        me.materials.append(mat)
    link(o, c or bpy.context.scene.collection)
    return o


def apply_mods(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
    old = o.data
    o.modifiers.clear()
    o.data = me
    bpy.data.meshes.remove(old)


def wall_frame(w):
    a, b = Vector((*w["a"], 0)), Vector((*w["b"], 0))
    d = (b - a)
    L = d.length
    u = d / L
    n = Vector((-u.y, u.x, 0))
    return a, u, n, L


# ---------------------------------------------------------------------- shell
def build_shell(plan, root):
    H = plan["storey"]["floor_to_ceiling"]
    top_int = H + SLAB
    top_ext = top_int + PARAPET
    parts = coll("_shell_parts", root)
    cut = coll("_cutters", root)
    pieces = []
    for w in plan["walls"]:
        a, u, n, L = wall_frame(w)
        t = w["thickness"]
        top = top_ext if w["exterior"] else top_int
        lo = a - n * t / 2
        hi = a + u * L + n * t / 2
        pieces.append(box("p_" + w["id"], (min(lo.x, hi.x), min(lo.y, hi.y), -SLAB),
                          (max(lo.x, hi.x), max(lo.y, hi.y), top), c=parts))
    for i, c in enumerate(plan["columns"] + plan["fins"]):
        pieces.append(box(f"p_col{i}", (*c["min"], -SLAB), (*c["max"], top_ext), c=parts))

    shell = pieces[0]
    shell.name = "Walls"
    link(shell, root)
    m = shell.modifiers.new("union", "BOOLEAN")
    m.operation = "UNION"
    m.operand_type = "COLLECTION"
    m.collection = parts
    m.solver = "EXACT"
    parts.objects.unlink(shell) if shell.name in parts.objects else None

    for o in plan["openings"]:
        w = next(x for x in plan["walls"] if x["id"] == o["wall"])
        a, b = Vector((*o["a"], 0)), Vector((*o["b"], 0))
        t = w["thickness"] + 0.6
        horiz = abs(b.x - a.x) > abs(b.y - a.y)
        z0, z1 = o["sill"], o["sill"] + o["height"]
        if horiz:
            lo = (min(a.x, b.x), a.y - t / 2, z0 if z0 > 0 else -0.02)
            hi = (max(a.x, b.x), a.y + t / 2, z1)
        else:
            lo = (a.x - t / 2, min(a.y, b.y), z0 if z0 > 0 else -0.02)
            hi = (a.x + t / 2, max(a.y, b.y), z1)
        box("cut_" + o["name"], lo, hi, c=cut)
    m2 = shell.modifiers.new("openings", "BOOLEAN")
    m2.operation = "DIFFERENCE"
    m2.operand_type = "COLLECTION"
    m2.collection = cut
    m2.solver = "EXACT"
    apply_mods(shell)
    for c_ in (parts, cut):
        for o in list(c_.objects):
            me = o.data
            bpy.data.objects.remove(o)
            bpy.data.meshes.remove(me)
        bpy.data.collections.remove(c_)
    # cleanup + materials: exterior faces get render, interior faces paint
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts, edges=bm.edges)
    bm.to_mesh(shell.data)
    bm.free()
    shell.data.materials.clear()
    for mat in (M["wall"], M["exterior"], M["wall_top"]):
        shell.data.materials.append(mat)
    return shell


def classify_shell_faces(shell, plan):
    """Face material: 0 interior paint, 1 exterior render, 2 tops/undersides."""
    from mathutils.geometry import intersect_point_line  # noqa
    indoor = [r for r in plan["rooms"] if r["use"] not in ("patio", "outdoor")]

    def inside(pt, poly):
        x, y = pt
        c = False
        for i in range(len(poly)):
            x1, y1 = poly[i - 1]
            x2, y2 = poly[i]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
        return c

    me = shell.data
    for f in me.polygons:
        nz = f.normal.z
        if abs(nz) > 0.5:
            f.material_index = 2
            continue
        c = f.center + f.normal * 0.12
        in_room = any(inside((c.x, c.y), r["polygon"]) for r in indoor)
        f.material_index = 0 if (in_room and c.z < 3.02) else 1


# ---------------------------------------------------------------------- floors, ceilings, roof
FLOOR_MAT = {"bedroom": "marble", "living": "marble", "dining": "marble", "kitchen": "marble",
             "prayer": "marble", "bath": "bath_tile", "patio": "deck", "outdoor": "utility_tile"}


def build_floors(plan, root):
    H = plan["storey"]["floor_to_ceiling"]
    c = coll("Floors", root)
    cc = coll("Ceilings", root)
    for r in plan["rooms"]:
        prism("Floor " + r["name"], r["polygon"], -SLAB, 0.0, M[FLOOR_MAT[r["use"]]], c)
        if r["use"] in ("patio", "outdoor"):
            continue
        if r["name"] in ("Living", "Dining"):
            tray_ceiling(r, H, cc)
        else:
            prism("Ceiling " + r["name"], r["polygon"], H, H + SLAB, M["ceiling"], cc)
    # thresholds under door / opening cuts
    for o in plan["openings"]:
        if o["sill"] > 0:
            continue
        w = next(x for x in plan["walls"] if x["id"] == o["wall"])
        a, b = Vector((*o["a"], 0)), Vector((*o["b"], 0))
        t = w["thickness"] / 2 + 0.01
        if abs(b.x - a.x) > abs(b.y - a.y):
            lo, hi = (min(a.x, b.x), a.y - t, -SLAB), (max(a.x, b.x), a.y + t, 0.0)
        else:
            lo, hi = (a.x - t, min(a.y, b.y), -SLAB), (a.x + t, max(a.y, b.y), 0.0)
        box("Threshold " + o["name"], lo, hi, M["marble"], c)


def tray_ceiling(r, H, cc, drop=0.28, band=0.5):
    """Perimeter false-ceiling band with a warm LED cove into a recessed centre."""
    xs = [p[0] for p in r["polygon"]]
    ys = [p[1] for p in r["polygon"]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    prism("Ceiling " + r["name"], r["polygon"], H, H + SLAB, M["ceiling"], cc)
    low = H - drop
    # band = room polygon minus inner rectangle, built as 4 boxes against the bounding box
    ix0, ix1, iy0, iy1 = x0 + band, x1 - band, y0 + band, y1 - band
    for nm, lo, hi in [("N", (x0, iy1, low), (x1, y1, H)), ("S", (x0, y0, low), (x1, iy0, H)),
                       ("W", (x0, iy0, low), (ix0, iy1, H)), ("E", (ix1, iy0, low), (x1, iy1, H))]:
        box(f"Cove band {r['name']} {nm}", lo, hi, M["ceiling"], cc)
    # LED strip on the inner lip, facing up/in
    e = 0.02
    for nm, lo, hi in [("N", (ix0, iy1 - e, low), (ix1, iy1, low + 0.03)),
                       ("S", (ix0, iy0, low), (ix1, iy0 + e, low + 0.03)),
                       ("W", (ix0, iy0, low), (ix0 + e, iy1, low + 0.03)),
                       ("E", (ix1 - e, iy0, low), (ix1, iy1, low + 0.03))]:
        box(f"Cove LED {r['name']} {nm}", lo, hi, M["led"], cc)
    # linear LED profiles in the recess like the photos
    cx = (x0 + x1) / 2
    for k in (-0.6, 0.6):
        box(f"Linear light {r['name']} {k}", (cx + k - 0.015, iy0 + 0.3, H - 0.012), (cx + k + 0.015, iy1 - 0.3, H), M["led_panel"], cc)


def build_roof(plan, root):
    """Roof membrane over the slab plus a coping on the parapet (walls already rise to it)."""
    H = plan["storey"]["floor_to_ceiling"]
    c = coll("Roof", root)
    for r in plan["rooms"]:
        if r["use"] in ("patio", "outdoor"):
            continue
        prism("Roof " + r["name"], r["polygon"], H + SLAB, H + SLAB + 0.03, M["roof"], c)


# ---------------------------------------------------------------------- openings hardware
def _opening_frame(o, plan):
    w = next(x for x in plan["walls"] if x["id"] == o["wall"])
    a, b = Vector((*o["a"], 0)), Vector((*o["b"], 0))
    if (b - a).length < 1e-6:
        return None
    if a.x > b.x + 1e-6 or (abs(a.x - b.x) < 1e-6 and a.y > b.y):
        a, b = b, a
    u = (b - a).normalized()
    n = Vector((-u.y, u.x, 0))
    return a, b, u, n, w["thickness"]


def oriented_box(name, origin, u, n, s0, s1, t0, t1, z0, z1, mat, c):
    """Box in a wall's frame: along u from s0..s1, across n from t0..t1, z0..z1."""
    corners = []
    for s in (s0, s1):
        for t in (t0, t1):
            corners.append(origin + u * s + n * t)
    xs = [p.x for p in corners]
    ys = [p.y for p in corners]
    return box(name, (min(xs), min(ys), z0), (max(xs), max(ys), z1), mat, c)


def build_windows(plan, root):
    c = coll("Windows", root)
    g = coll("Glass", root)
    for o in plan["openings"]:
        if o["type"] not in ("window", "high_window", "sliding_door"):
            continue
        fr = _opening_frame(o, plan)
        if not fr:
            continue
        a, b, u, n, t = fr
        L = (b - a).length
        z0, z1 = o["sill"], o["sill"] + o["height"]
        f = 0.05
        nm = o["name"]
        # outer frame
        oriented_box(f"{nm} frame L", a, u, n, 0, f, -0.05, 0.05, z0, z1, M["frame"], c)
        oriented_box(f"{nm} frame R", a, u, n, L - f, L, -0.05, 0.05, z0, z1, M["frame"], c)
        oriented_box(f"{nm} frame B", a, u, n, 0, L, -0.05, 0.05, z0, z0 + f, M["frame"], c)
        oriented_box(f"{nm} frame T", a, u, n, 0, L, -0.05, 0.05, z1 - f, z1, M["frame"], c)
        # marble sill inside for windows
        if o["sill"] > 0:
            oriented_box(f"{nm} sill", a, u, n, -0.03, L + 0.03, -t / 2 - 0.03, t / 2 + 0.03, z0 - 0.03, z0, M["marble"], c)
        # two sliding sashes on separate tracks; sliding doors stand open (one leaf stacked)
        half = L / 2
        if o["type"] == "sliding_door":
            spans = [(f, half + 0.02, -0.025), (f + 0.0, half + 0.02, 0.025)]  # stacked: open half
        else:
            spans = [(f, half + 0.02, -0.025), (half - 0.02, L - f, 0.025)]
        for k, (s0, s1, off) in enumerate(spans):
            oriented_box(f"{nm} sash{k} L", a, u, n, s0, s0 + 0.035, off - 0.015, off + 0.015, z0 + f, z1 - f, M["frame"], c)
            oriented_box(f"{nm} sash{k} R", a, u, n, s1 - 0.035, s1, off - 0.015, off + 0.015, z0 + f, z1 - f, M["frame"], c)
            oriented_box(f"{nm} sash{k} B", a, u, n, s0, s1, off - 0.015, off + 0.015, z0 + f, z0 + f + 0.035, M["frame"], c)
            oriented_box(f"{nm} sash{k} T", a, u, n, s0, s1, off - 0.015, off + 0.015, z1 - f - 0.035, z1 - f, M["frame"], c)
            oriented_box(f"{nm} glass{k}", a, u, n, s0 + 0.03, s1 - 0.03, off - 0.003, off + 0.003, z0 + f + 0.03, z1 - f - 0.03, M["glass"], g)
    for p in plan["glass_partitions"]:
        a, b = Vector((*p["a"], 0)), Vector((*p["b"], 0))
        u = (b - a).normalized()
        n = Vector((-u.y, u.x, 0))
        L = (b - a).length
        oriented_box(p["name"], a, u, n, 0, L, -0.004, 0.004, p["sill"], p["sill"] + p["height"], M["glass_frosted"] if "Prayer" in p["name"] else M["glass"], g)
        oriented_box(p["name"] + " rail", a, u, n, 0, L, -0.02, 0.02, p["sill"] + p["height"], p["sill"] + p["height"] + 0.03, M["frame"], c)


def build_doors(plan, root):
    c = coll("Doors", root)
    for o in plan["openings"]:
        if o["type"] not in ("door", "entry_door"):
            continue
        fr = _opening_frame(o, plan)
        a, b, u, n, t = fr
        L = (b - a).length
        z1 = o["height"]
        nm = o["name"]
        jamb = 0.04
        arch = 0.07
        # jamb lining + architraves both faces
        for s0, s1 in ((0, jamb), (L - jamb, L)):
            oriented_box(f"{nm} jamb", a, u, n, s0, s1, -t / 2, t / 2, 0, z1, M["door_wood"], c)
        oriented_box(f"{nm} head", a, u, n, 0, L, -t / 2, t / 2, z1 - jamb, z1, M["door_wood"], c)
        for side in (-1, 1):
            t0, t1 = sorted((side * t / 2, side * (t / 2 + 0.015)))
            oriented_box(f"{nm} arch L", a, u, n, -arch, 0, t0, t1, 0, z1 + arch, M["door_wood"], c)
            oriented_box(f"{nm} arch R", a, u, n, L, L + arch, t0, t1, 0, z1 + arch, M["door_wood"], c)
            oriented_box(f"{nm} arch T", a, u, n, -arch, L + arch, t0, t1, z1, z1 + arch, M["door_wood"], c)
        # leaf, open 90 deg from the hinge along the swing direction
        hinge = Vector((*o["hinge"], 0))
        sw = Vector((*o["swing"], 0)).normalized()
        along = (a + b) / 2 - hinge
        along = along.normalized()
        leaf_w = L - 2 * jamb - 0.006
        thick = 0.04
        # leaf lies along sw, its thickness offset toward the opening side (along)
        h0 = hinge + along * jamb
        p0 = h0
        p1 = h0 + sw * leaf_w
        q = along * thick
        xs = [p0.x, p1.x, p0.x + q.x, p1.x + q.x]
        ys = [p0.y, p1.y, p0.y + q.y, p1.y + q.y]
        leaf = box(f"{nm} leaf", (min(xs), min(ys), 0.01), (max(xs), max(ys), z1 - jamb - 0.004), M["door_leaf"], c)
        # handle
        hp = p1 - sw * 0.07
        for side in (-1, 1):
            hq = hp + q * (0.5 + side * 0.9)
            box(f"{nm} handle", (hq.x - 0.012, hq.y - 0.012, 1.0), (hq.x + 0.012, hq.y + 0.012, 1.05), M["brass"], c)


def build_rails_planters(plan, root):
    c = coll("Railings", root)
    for r in plan["railings"]:
        pts = [Vector((*p, 0)) for p in r["points"]]
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            u = (b - a).normalized()
            n = Vector((-u.y, u.x, 0))
            L = (b - a).length
            oriented_box(f"{r['name']} handrail", a, u, n, -0.025, L + 0.025, -0.025, 0.025, r["height"] - 0.05, r["height"], M["frame"], c)
            oriented_box(f"{r['name']} glass", a, u, n, 0.03, L - 0.03, -0.005, 0.005, 0.08, r["height"] - 0.08, M["glass"], c)
            k = max(1, int(L / 0.9))
            for j in range(k + 1):
                s = L * j / k
                oriented_box(f"{r['name']} post", a, u, n, s - 0.02, s + 0.02, -0.02, 0.02, 0, r["height"], M["frame"], c)
    pc = coll("Planters", root)
    for i, p in enumerate(plan["planters"]):
        lo, hi = p["min"], p["max"]
        box(f"Planter {i}", (lo[0], lo[1], -SLAB), (hi[0], hi[1], 0.45), M["planter"], pc)
        box(f"Planter soil {i}", (lo[0] + 0.05, lo[1] + 0.05, 0.4), (hi[0] - 0.05, hi[1] - 0.05, 0.44), M["soil"], pc)
