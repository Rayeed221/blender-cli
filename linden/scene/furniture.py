"""Furniture & dressing. Positions in plan metres (X east, Y north), placed from the
furniture symbols on the drawing; styling from the design photos."""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

import arch
from arch import box, coll, link
from mats import M

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "models", "_lib"))
import modelkit as mk  # noqa: E402

C = None  # current collection


def X(px):
    return (px - 37) / 63.62


def Y(py):
    return (852 - py) / 63.62


def put(o):
    link(o, C)
    return o


def rbox(name, lo, hi, mat, r=0.02, seg=2):
    o = box(name, lo, hi, mat, C)
    if r > 0:
        m = o.modifiers.new("Bevel", "BEVEL")
        m.width = r
        m.segments = seg
        m.limit_method = "ANGLE"
    return o


def cyl(name, x, y, z0, z1, r, mat, seg=32, r_top=None):
    o = mk.cylinder(name, radius=r, depth=z1 - z0, segments=seg, location=(x, y, (z0 + z1) / 2),
                    mat=mat, radius_top=r_top)
    return put(o)


def rot_group(objs, pivot, deg):
    """Rotate already-placed objects about a vertical axis through pivot."""
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    for o in objs:
        p = o.location - Vector((pivot[0], pivot[1], 0))
        o.location = Vector((pivot[0] + p.x * ca - p.y * sa, pivot[1] + p.x * sa + p.y * ca, o.location.z))
        o.rotation_euler.z += a


def track(fn):
    """Collect objects created inside fn so they can be rotated as a group."""
    before = set(bpy.data.objects)
    fn()
    return [o for o in bpy.data.objects if o not in before]


# ---------------------------------------------------------------- generic pieces
def curtain(name, a, b, z0, z1, mat, folds=None, amp=0.05, offset=0.0):
    """Pleated curtain hanging from a->b (plan coords) between z0 and z1."""
    a, b = Vector((*a, 0)), Vector((*b, 0))
    u = (b - a)
    L = u.length
    u.normalize()
    n = Vector((-u.y, u.x, 0))
    folds = folds or max(2, int(L / 0.12))
    nu = folds * 8
    verts, faces = [], []
    for i in range(nu + 1):
        s = L * i / nu
        d = amp * math.sin(2 * math.pi * folds * i / nu) + offset
        for z in (z0, z1):
            p = a + u * s + n * d
            verts.append((p.x, p.y, z))
    for i in range(nu):
        faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, me)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    m = o.modifiers.new("Solidify", "SOLIDIFY")
    m.thickness = 0.006
    return put(o)


def plant(name, x, y, h=1.4, pot_r=0.22, kind="ficus", seed=0):
    rnd = random.Random(seed)
    cyl(name + " pot", x, y, 0, pot_r * 1.6, pot_r, M["terracotta"] if kind != "palm" else M["panel_cream"], 24, pot_r * 1.2)
    cyl(name + " soil", x, y, pot_r * 1.5, pot_r * 1.55, pot_r * 1.1, M["soil"], 16)
    if kind == "palm":
        for i in range(9):
            ang = rnd.uniform(0, 2 * math.pi)
            tilt = rnd.uniform(25, 60)
            ln = rnd.uniform(0.5, 0.85) * h
            leaf = mk.sphere(f"{name} frond{i}", radius=1, segments=10, rings=6, mat=M["plant"])
            leaf.scale = (ln / 2, 0.08, 0.012)
            r = math.radians(tilt)
            leaf.rotation_euler = (0, -math.pi / 2 + r, ang)
            leaf.location = (x + math.cos(ang) * math.sin(r) * ln / 2,
                             y + math.sin(ang) * math.sin(r) * ln / 2,
                             pot_r * 1.6 + h * 0.35 + math.cos(r) * ln / 2)
            put(leaf)
        cyl(name + " stem", x, y, pot_r * 1.5, pot_r * 1.6 + h * 0.4, 0.025, M["wood_light"], 8)
    else:
        cyl(name + " stem", x, y, pot_r * 1.5, h * 0.7, 0.015, M["wood_light"], 6)
        bush(name, x, y, pot_r * 1.6 + (h - pot_r * 1.6) * 0.62, h * 0.28, seed, int(90 + 60 * h))


def bush(name, x, y, z, r, seed=0, leaves=120):
    """Leafy bush: many small leaves (flattened ellipsoids) scattered on a sphere shell,
    joined into one mesh so it stays cheap to render and export."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    for i in range(leaves):
        u, v = rnd.uniform(-1, 1), rnd.uniform(0, 2 * math.pi)
        rr = r * rnd.uniform(0.55, 1.0)
        s_ = math.sqrt(1 - u * u)
        p = Vector((x + rr * s_ * math.cos(v), y + rr * s_ * math.sin(v), z + rr * u * 0.85))
        geom = bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=3, radius=1.0)
        vs = geom["verts"]
        ln = rnd.uniform(0.05, 0.09)
        bmesh.ops.scale(bm, vec=(ln, ln * 0.42, ln * 0.06), verts=vs)
        from mathutils import Euler
        rot = Euler((rnd.uniform(-1.2, 1.2), rnd.uniform(-0.6, 0.6), rnd.uniform(0, 2 * math.pi))).to_matrix()
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=rot, verts=vs)
        bmesh.ops.translate(bm, vec=p, verts=vs)
        for f in {f for v_ in vs for f in v_.link_faces}:
            f.material_index = i % 2
            f.smooth = True
    me = bpy.data.meshes.new(name + " leaves")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M["plant"])
    me.materials.append(M["plant_dark"])
    o = bpy.data.objects.new(name + " leaves", me)
    return put(o)


def art(name, center, normal, w, h, z, mat=None):
    """Framed artwork on a wall; normal points into the room."""
    n = Vector((*normal, 0)).normalized()
    u = Vector((n.y, -n.x, 0))
    c = Vector((*center, 0))
    p0, p1 = c - u * w / 2, c + u * w / 2
    xs = [p0.x, p1.x, p0.x + n.x * 0.04, p1.x + n.x * 0.04]
    ys = [p0.y, p1.y, p0.y + n.y * 0.04, p1.y + n.y * 0.04]
    box(name + " frame", (min(xs), min(ys), z - h / 2), (max(xs), max(ys), z + h / 2), M["black_metal"], C)
    q0, q1 = c - u * (w / 2 - 0.05), c + u * (w / 2 - 0.05)
    xs = [q0.x, q1.x, q0.x + n.x * 0.045, q1.x + n.x * 0.045]
    ys = [q0.y, q1.y, q0.y + n.y * 0.045, q1.y + n.y * 0.045]
    box(name + " print", (min(xs), min(ys), z - h / 2 + 0.05), (max(xs), max(ys), z + h / 2 - 0.05), mat or M["art"], C)


def pendant_ring(name, x, y, z, r, mat_glow):
    t = mk.torus(name, major_radius=r, minor_radius=0.025, location=(x, y, z), mat=M["brass"])
    put(t)
    g = mk.torus(name + " glow", major_radius=r, minor_radius=0.012, location=(x, y, z - 0.03), mat=mat_glow)
    put(g)
    for i in range(14):
        a = 2 * math.pi * i / 14
        cyl(f"{name} crystal{i}", x + r * math.cos(a), y + r * math.sin(a), z - 0.28, z - 0.04, 0.012, M["glass"], 6)
    cyl(name + " rod", x, y, z, 3.0, 0.006, M["brass"], 6)


# ---------------------------------------------------------------- rooms
def living():
    # TV wall: cream lacquer panelling with beige flanks and LED reveals (photos p7-p8)
    wx = X(378)                     # inside face of the TV wall
    y0, y1 = Y(258), Y(88)
    rbox("TV wall panel", (wx, Y(250), 0), (wx + 0.04, Y(96), 2.72), M["panel_cream"], 0.004)
    for k, (a, b) in enumerate(((Y(250), Y(232)), (Y(106), Y(96)))):
        rbox(f"TV wall beige flank {k}", (wx + 0.04, a, 0), (wx + 0.06, b, 2.72), M["panel_beige"], 0.003)
    for yy in (Y(214), Y(124)):
        box("TV wall LED reveal", (wx + 0.041, yy - 0.01, 0.05), (wx + 0.05, yy + 0.01, 2.7), M["led"], C)
    yc = (Y(250) + Y(96)) / 2
    rbox("TV console", (wx + 0.04, yc - 1.0, 0.22), (wx + 0.46, yc + 1.0, 0.52), M["cabinet_taupe"], 0.01)
    box("Console LED", (wx + 0.3, yc - 0.98, 0.215), (wx + 0.42, yc + 0.98, 0.22), M["led"], C)
    rbox("TV", (wx + 0.06, yc - 0.72, 1.0), (wx + 0.1, yc + 0.72, 1.82), M["black_glass"], 0.005)
    rbox("TV bezel", (wx + 0.055, yc - 0.73, 0.99), (wx + 0.062, yc + 0.73, 1.83), M["black_metal"], 0.002)
    # decor on console
    cyl("Vase", wx + 0.25, yc - 0.7, 0.52, 0.8, 0.07, M["ceramic"], 16, 0.04)
    rbox("Books", (wx + 0.12, yc + 0.5, 0.52), (wx + 0.35, yc + 0.78, 0.6), M["drape"], 0.005)

    # L sectional along the east column and the north window (drawing x 501-606, y 92-265)
    ex = X(612)          # inside face of the east column
    ny = Y(88)           # inside face of north wall
    d = 0.95             # seat depth
    sy0 = Y(262)
    parts = []
    rbox("Sofa base long", (ex - d, sy0, 0.06), (ex, ny - d, 0.44), M["sofa"], 0.04, 3)
    rbox("Sofa base corner", (ex - d, ny - d, 0.06), (ex, ny, 0.44), M["sofa"], 0.04, 3)
    rbox("Sofa base short", (X(500), ny - d, 0.06), (ex - d, ny, 0.44), M["sofa"], 0.04, 3)
    for o_ in ("Sofa plinth long", ):
        box(o_, (ex - d + 0.05, sy0 + 0.05, 0), (ex - 0.05, ny - 0.05, 0.06), M["black_metal"], C)
    box("Sofa plinth short", (X(500) + 0.05, ny - d + 0.05, 0), (ex - d, ny - 0.05, 0.06), M["black_metal"], C)
    # seat cushions
    n_long = 3
    span = (ny - d) - sy0
    for i in range(n_long):
        a = sy0 + 0.02 + i * span / n_long
        rbox(f"Seat cushion long {i}", (ex - d + 0.02, a, 0.44), (ex - 0.2, a + span / n_long - 0.02, 0.58), M["sofa"], 0.05, 3)
    rbox("Seat cushion corner", (ex - d + 0.02, ny - d + 0.02, 0.44), (ex - 0.2, ny - 0.2, 0.58), M["sofa"], 0.05, 3)
    span2 = (ex - d) - X(500)
    for i in range(2):
        a = X(500) + 0.02 + i * span2 / 2
        rbox(f"Seat cushion short {i}", (a, ny - d + 0.02, 0.44), (a + span2 / 2 - 0.02, ny - 0.2, 0.58), M["sofa"], 0.05, 3)
    # channel-tufted backs (vertical channels like the photos)
    def channels(prefix, lo, hi, along_x, n):
        for i in range(n):
            if along_x:
                a = lo[0] + (hi[0] - lo[0]) * i / n
                b = lo[0] + (hi[0] - lo[0]) * (i + 1) / n
                rbox(f"{prefix} {i}", (a + 0.005, lo[1], lo[2]), (b - 0.005, hi[1], hi[2]), M["sofa"], 0.045, 3)
            else:
                a = lo[1] + (hi[1] - lo[1]) * i / n
                b = lo[1] + (hi[1] - lo[1]) * (i + 1) / n
                rbox(f"{prefix} {i}", (lo[0], a + 0.005, lo[2]), (hi[0], b - 0.005, hi[2]), M["sofa"], 0.045, 3)
    channels("Back channel long", (ex - 0.22, sy0, 0.44), (ex, ny - 0.22, 0.88), False, 11)
    channels("Back channel short", (X(500), ny - 0.22, 0.44), (ex, ny, 0.88), True, 9)
    rbox("Sofa arm", (ex - d, sy0 - 0.0, 0.06), (ex, sy0 + 0.2, 0.66), M["sofa"], 0.05, 3)
    rbox("Sofa arm short", (X(500), ny - d, 0.06), (X(500) + 0.2, ny, 0.66), M["sofa"], 0.05, 3)
    # throw cushions
    rnd = random.Random(3)
    for i, (px, py, mat) in enumerate([(ex - 0.33, sy0 + 0.45, M["cushion_rust"]), (ex - 0.33, sy0 + 0.95, M["cushion_cream"]),
                                       (ex - 0.35, ny - 0.4, M["cushion_cream"]), (X(500) + 0.45, ny - 0.33, M["cushion_rust"]),
                                       (X(500) + 0.95, ny - 0.33, M["cushion_cream"])]):
        c = mk.cube(f"Throw cushion {i}", size=(0.16, 0.45, 0.42) if i < 3 else (0.45, 0.16, 0.42), location=(px, py, 0.8), mat=mat)
        c.rotation_euler = (math.radians(rnd.uniform(-8, 8)), 0, math.radians(rnd.uniform(-10, 10)))
        mk.subsurf(c, 2)
        put(c)
    rbox("Sofa throw", (ex - 0.9, sy0 + 1.4, 0.585), (ex - 0.25, sy0 + 1.95, 0.6), M["throw"], 0.01)

    # rug + nested round tables (photos: white marble + black, round)
    rbox("Living rug", (X(410), Y(250), 0.0), (ex - 0.85, ny - 0.75, 0.018), M["rug"], 0.01)
    tx, ty = (X(410) + ex - 0.85) / 2 + 0.2, (Y(250) + ny - 0.75) / 2
    cyl("Coffee table top", tx, ty, 0.36, 0.40, 0.45, M["white_marble_top"], 48)
    cyl("Coffee table base", tx, ty, 0.0, 0.36, 0.3, M["black_metal"], 32)
    cyl("Side table top", tx - 0.45, ty - 0.45, 0.30, 0.33, 0.28, M["black_metal"], 32)
    cyl("Side table base", tx - 0.45, ty - 0.45, 0.0, 0.30, 0.16, M["black_metal"], 24)
    cyl("Tray vase", tx + 0.1, ty, 0.40, 0.62, 0.06, M["ceramic"], 16, 0.035)
    rbox("Coffee book", (tx - 0.25, ty - 0.18, 0.40), (tx + 0.02, ty + 0.12, 0.45), M["cushion_rust"], 0.005)
    # tufted armchair by the window (drawing x 422-481, y 95-140), angled toward the TV
    objs = track(lambda: armchair(X(451), Y(118)))
    rot_group(objs, (X(451), Y(118)), -35)
    # floor lamp + plant + art
    lamp_x, lamp_y = X(396), Y(110)
    cyl("Floor lamp base", lamp_x, lamp_y, 0, 0.03, 0.16, M["black_metal"], 24)
    cyl("Floor lamp pole", lamp_x, lamp_y, 0.03, 1.55, 0.012, M["black_metal"], 8)
    cyl("Floor lamp shade", lamp_x, lamp_y, 1.38, 1.65, 0.2, M["sheer"], 32, 0.16)
    cyl("Floor lamp bulb", lamp_x, lamp_y, 1.45, 1.55, 0.05, M["lamp_glow"], 12)
    plant("Living plant", X(600) - 0.25, Y(262) - 0.35, 1.5, 0.2, "palm", 4)
    # window: sheers drawn across, taupe drapes stacked at the sides (photos)
    wy = Y(82) - 0.12
    curtain("Living sheer", (X(415), wy), (X(470), wy), 0.02, 2.7, M["sheer"], amp=0.035)
    curtain("Living drape L", (X(398), wy - 0.06), (X(426), wy - 0.06), 0.02, 2.7, M["drape"], 4, 0.05)
    curtain("Living drape R", (X(566), wy - 0.06), (X(596), wy - 0.06), 0.02, 2.7, M["drape"], 4, 0.05)
    art("Living art", (X(612) - 0.03, Y(300)), (-1, 0), 0.7, 0.95, 1.55)


def armchair(x, y):
    rbox("Armchair seat", (x - 0.4, y - 0.38, 0.12), (x + 0.4, y + 0.38, 0.45), M["sofa"], 0.05, 3)
    for i in range(7):
        a = x - 0.4 + 0.8 * i / 7
        rbox(f"Armchair back {i}", (a + 0.004, y + 0.2, 0.42), (a + 0.8 / 7 - 0.004, y + 0.38, 0.85), M["sofa"], 0.04, 3)
    for s in (-1, 1):
        rbox("Armchair arm", (x + s * 0.4 - (0.14 if s > 0 else 0), y - 0.38, 0.12),
             (x + s * 0.4 + (0.0 if s > 0 else 0.14), y + 0.38, 0.65), M["sofa"], 0.04, 3)
    for sx in (-0.33, 0.33):
        for sy in (-0.3, 0.3):
            cyl("Armchair leg", x + sx, y + sy, 0, 0.12, 0.018, M["brass"], 8)


def dining():
    tx, ty = X(482), Y(435)
    L, W = 1.8, 0.95
    rbox("Dining top", (tx - L / 2, ty - W / 2, 0.74), (tx + L / 2, ty + W / 2, 0.77), M["white_marble_top"], 0.006)
    for s in (-1, 1):
        box("Dining leg", (tx + s * 0.55 - 0.04, ty - 0.3, 0), (tx + s * 0.55 + 0.04, ty + 0.3, 0.74), M["black_metal"], C)
    seats = [(-0.45, -1, 0), (0.45, -1, 0), (-0.45, 1, 180), (0.45, 1, 180), (-1.1, 0, -90), (1.1, 0, 90)]
    for i, (dx, side, rot) in enumerate(seats):
        cx = tx + dx
        cy = ty + side * 0.72 if side else ty
        objs = track(lambda: dining_chair(cx, cy))
        rot_group(objs, (cx, cy), rot)
    pendant_ring("Chandelier", tx, ty, 2.25, 0.4, M["lamp_glow"])
    # dinner wagon + crockery unit with lit glass shelves along the hall south wall
    wy = Y(573)
    rbox("Dinner wagon", (X(395), wy, 0.0), (X(575), wy + 0.5, 0.85), M["cabinet_cream"], 0.01)
    rbox("Wagon top", (X(395), wy, 0.85), (X(575), wy + 0.52, 0.88), M["white_marble_top"], 0.004)
    rbox("Crockery unit", (X(430), wy, 1.45), (X(540), wy + 0.38, 2.75), M["cabinet_cream"], 0.005)
    for i in range(4):
        a = X(430) + (X(540) - X(430)) * i / 4
        b = X(430) + (X(540) - X(430)) * (i + 1) / 4
        box("Crockery glass", (a + 0.03, wy + 0.385, 1.5), (b - 0.03, wy + 0.39, 2.7), M["glass"], C)
        box("Crockery frame", (a, wy + 0.38, 1.45), (a + 0.03, wy + 0.4, 2.75), M["black_metal"], C)
        box("Crockery light", (a + 0.03, wy + 0.02, 2.66), (b - 0.03, wy + 0.36, 2.68), M["led"], C)
        for z in (1.85, 2.25):
            box("Crockery shelf", (a + 0.03, wy + 0.02, z), (b - 0.03, wy + 0.36, z + 0.015), M["glass"], C)
            for k in range(3):
                cyl("Bowl", a + 0.08 + k * 0.1, wy + 0.18, z + 0.015, z + 0.09, 0.045, M["ceramic"], 12, 0.06)
    rbox("Dining fridge", (X(577), wy, 0), (X(627), wy + 0.7, 1.85), M["steel"], 0.02)
    plant("Dining plant", X(392) + 0.35, Y(573) + 0.35, 1.2, 0.18, "ficus", 9)


def dining_chair(x, y):
    """Chair at (x, y) facing +Y (toward the table) before rotation."""
    rbox("Chair seat", (x - 0.23, y - 0.22, 0.44), (x + 0.23, y + 0.22, 0.5), M["leather_rose"], 0.03, 2)
    back = rbox("Chair back", (x - 0.24, y - 0.28, 0.5), (x + 0.24, y - 0.22, 0.9), M["leather_rose"], 0.03, 2)
    for sx in (-0.2, 0.2):
        for sy in (-0.19, 0.19):
            cyl("Chair leg", x + sx, y + sy, 0, 0.44, 0.012, M["black_metal"], 8)


def point_light(name, loc, watts, radius=0.05, color=(1.0, 0.75, 0.5)):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = watts
    ld.shadow_soft_size = radius
    ld.color = color
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    C.objects.link(o)
    return o


def spot_light(name, loc, watts, angle=100, color=(1.0, 0.75, 0.5)):
    ld = bpy.data.lights.new(name, "SPOT")
    ld.energy = watts
    ld.spot_size = math.radians(angle)
    ld.spot_blend = 0.6
    ld.shadow_soft_size = 0.04
    ld.color = color
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    C.objects.link(o)
    return o


def kitchen():
    # room interior: x 43..324 px, y 340..488 px
    x0, x1 = X(43), X(324)
    yN, yS = Y(340), Y(488)
    dp = 0.6
    ws = X(43)
    # base run along the north wall (hob) and along the west wall (sink, dishwasher)
    rbox("Base run north", (x0 + dp, yN - dp, 0.1), (X(262), yN, 0.86), M["cabinet_taupe"], 0.004)
    rbox("Base run west", (x0, Y(470), 0.1), (x0 + dp, yN, 0.86), M["cabinet_taupe"], 0.004)
    box("Kick north", (x0 + dp, yN - dp + 0.06, 0), (X(262), yN, 0.1), M["black_metal"], C)
    box("Kick west", (x0, Y(470), 0), (x0 + dp - 0.06, yN, 0.1), M["black_metal"], C)
    box("Kick LED", (x0 + dp, yN - dp + 0.05, 0.005), (X(262), yN - dp + 0.07, 0.015), M["led"], C)
    rbox("Worktop north", (x0 + dp, yN - dp - 0.02, 0.86), (X(262) + 0.02, yN, 0.9), M["granite"], 0.004)
    rbox("Worktop west", (x0, Y(470) - 0.02, 0.86), (x0 + dp + 0.02, yN, 0.9), M["granite"], 0.004)
    # door/drawer grooves
    for i in range(1, 6):
        xx = x0 + dp + (X(262) - x0 - dp) * i / 6
        box("Base door gap", (xx - 0.003, yN - dp - 0.001, 0.12), (xx + 0.003, yN - dp + 0.002, 0.84), M["black_metal"], C)
    for i in range(1, 4):
        yy = Y(470) + (yN - dp - Y(470)) * i / 4
        box("Base door gap", (x0 + dp - 0.002, yy - 0.003, 0.12), (x0 + dp + 0.001, yy + 0.003, 0.84), M["black_metal"], C)
    # backsplash
    box("Backsplash north", (x0, yN - 0.02, 0.9), (X(262), yN, 1.5), M["backsplash"], C)
    box("Backsplash west", (x0, Y(470), 0.9), (x0 + 0.02, yN, 1.5), M["backsplash"], C)
    # hob + hood (drawing x 172-222)
    hx = (X(172) + X(222)) / 2
    box("Hob", (hx - 0.38, yN - 0.52, 0.9), (hx + 0.38, yN - 0.06, 0.91), M["black_glass"], C)
    for dx, dy in ((-0.2, -0.17), (0.2, -0.17), (-0.2, -0.38), (0.2, -0.38)):
        put(mk.torus("Burner", major_radius=0.07, minor_radius=0.008, location=(hx + dx, yN + dy, 0.915), mat=M["steel"]))
    rbox("Hood", (hx - 0.45, yN - 0.5, 1.6), (hx + 0.45, yN, 1.75), M["steel"], 0.01)
    rbox("Hood chimney", (hx - 0.15, yN - 0.3, 1.75), (hx + 0.15, yN, 2.75), M["steel"], 0.005)
    # sink on the west run (drawing y 370-420) with mixer
    sy = (Y(370) + Y(420)) / 2
    box("Sink basin", (x0 + 0.12, sy - 0.38, 0.75), (x0 + 0.5, sy + 0.38, 0.905), M["steel"], C)
    cyl("Mixer", x0 + 0.08, sy, 0.9, 1.2, 0.018, M["black_metal"], 12)
    box("Mixer spout", (x0 + 0.08, sy - 0.012, 1.17), (x0 + 0.3, sy + 0.012, 1.2), M["black_metal"], C)
    # upper cabinets: cream with lit glass-front shelves on the north wall (photos p24-p26)
    up0, up1 = 1.55, 2.45
    n = 7
    for i in range(n):
        a = x0 + (X(262) - x0) * i / n
        b = x0 + (X(262) - x0) * (i + 1) / n
        glazed = i in (1, 2, 5, 6) and not (hx - 0.5 < (a + b) / 2 < hx + 0.5)
        if hx - 0.5 < (a + b) / 2 < hx + 0.5:
            continue
        if not glazed:
            rbox(f"Upper {i}", (a + 0.004, yN - 0.35, up0), (b - 0.004, yN, up1), M["cabinet_cream"], 0.004)
            continue
        # hollow carcass: back, sides, top, bottom; black-framed glass door; warm strip light
        box(f"Upper back {i}", (a, yN - 0.02, up0), (b, yN, up1), M["panel_beige"], C)
        for xa, xb in ((a + 0.004, a + 0.022), (b - 0.022, b - 0.004)):
            box(f"Upper side {i}", (xa, yN - 0.35, up0), (xb, yN, up1), M["cabinet_cream"], C)
        box(f"Upper top {i}", (a + 0.004, yN - 0.35, up1 - 0.02), (b - 0.004, yN, up1), M["cabinet_cream"], C)
        box(f"Upper bottom {i}", (a + 0.004, yN - 0.35, up0), (b - 0.004, yN, up0 + 0.02), M["cabinet_cream"], C)
        box(f"Upper glass {i}", (a + 0.03, yN - 0.35, up0 + 0.03), (b - 0.03, yN - 0.344, up1 - 0.03), M["glass"], C)
        for xa, xb in ((a + 0.022, a + 0.032), (b - 0.032, b - 0.022)):
            box(f"Upper door frame {i}", (xa, yN - 0.352, up0 + 0.02), (xb, yN - 0.342, up1 - 0.02), M["black_metal"], C)
        box(f"Upper light {i}", (a + 0.04, yN - 0.25, up1 - 0.03), (b - 0.04, yN - 0.06, up1 - 0.02), M["led"], C)
        for z in (up0 + 0.3, up0 + 0.6):
            box("Shelf", (a + 0.022, yN - 0.33, z), (b - 0.022, yN - 0.02, z + 0.012), M["glass"], C)
            for k in range(2):
                cyl("Jar", a + (b - a) * (k + 1) / 3, yN - 0.17, z + 0.012, z + 0.18, 0.045, M["ceramic"], 12, 0.04)
    box("Under-cabinet LED", (x0, yN - 0.33, up0 - 0.01), (X(262), yN - 0.3, up0), M["led"], C)
    for i in range(3):
        a = Y(470) + (yN - Y(470)) * i / 3
        b = Y(470) + (yN - Y(470)) * (i + 1) / 3
        rbox(f"Upper west {i}", (x0, a + 0.004, up0), (x0 + 0.35, b - 0.004, up1), M["cabinet_cream"], 0.004)
    box("Under-cabinet LED west", (x0 + 0.3, Y(470), up0 - 0.01), (x0 + 0.33, yN, up0), M["led"], C)
    # tall fridge + pantry against the east wall (drawing x 268-315, y 375-430)
    fx1 = x1
    rbox("Fridge", (fx1 - 0.72, Y(434), 0), (fx1, Y(374), 1.9), M["steel"], 0.02)
    box("Fridge split", (fx1 - 0.725, (Y(434) + Y(374)) / 2 - 0.004, 0.05), (fx1 - 0.72, (Y(434) + Y(374)) / 2 + 0.004, 1.85), M["black_metal"], C)
    for s in (-1, 1):
        box("Fridge handle", (fx1 - 0.76, (Y(434) + Y(374)) / 2 + s * 0.04 - 0.01, 0.8), (fx1 - 0.74, (Y(434) + Y(374)) / 2 + s * 0.04 + 0.01, 1.5), M["black_metal"], C)
    rbox("Pantry", (fx1 - 0.62, Y(374), 0), (fx1, yN, 2.45), M["cabinet_taupe"], 0.004)
    rbox("Upper over fridge", (fx1 - 0.62, Y(434), 1.95), (fx1, Y(374), 2.45), M["cabinet_taupe"], 0.004)
    # props
    cyl("Kettle", X(120), yN - 0.25, 0.9, 1.12, 0.09, M["steel"], 24, 0.07)
    cyl("Pot", hx + 0.2, yN - 0.17, 0.915, 1.05, 0.12, M["steel"], 24)
    rbox("Chopping board", (X(240) - 0.2, yN - 0.45, 0.9), (X(240) + 0.15, yN - 0.15, 0.92), M["wood_light"], 0.005)
    plant("Kitchen herb", x0 + 0.3, Y(395), 0.35, 0.07, "ficus", 2)
    bpy.data.objects["Kitchen herb pot"].location.z += 0.9
    for o in [o for o in bpy.data.objects if o.name.startswith("Kitchen herb")]:
        if o.name != "Kitchen herb pot":
            o.location.z += 0.9
    # ceiling downlights
    for xx in (X(110), X(200), X(290)):
        cyl("Downlight", xx, (yN + yS) / 2, 2.985, 3.0, 0.05, M["led_panel"], 16)
        spot_light("Kitchen downlight", (xx, (yN + yS) / 2, 2.97), 45)


def patio():
    # C. Bed 2 veranda (drawing x 478-601, y 853-929); planter to the west
    x0, x1, y0, y1 = X(478), X(601), Y(929), Y(853)
    rbox("Outdoor rug", (x0 + 0.15, y0 + 0.12, 0), (x1 - 0.15, y1 - 0.12, 0.012), M["rug"], 0.005)
    for i, (cx, cy, rot) in enumerate([(x0 + 0.55, y0 + 0.55, 35), (x1 - 0.55, y0 + 0.55, -35)]):
        objs = track(lambda: lounge_chair(cx, cy))
        rot_group(objs, (cx, cy), rot)
    cx, cy = (x0 + x1) / 2, y0 + 0.5
    cyl("Patio table top", cx, cy, 0.42, 0.45, 0.28, M["deck"], 32)
    cyl("Patio table leg", cx, cy, 0, 0.42, 0.05, M["black_metal"], 12)
    cyl("Patio cup", cx + 0.08, cy, 0.45, 0.53, 0.035, M["ceramic"], 12)
    # lantern
    lx, ly = x1 - 0.2, y1 - 0.25
    box("Lantern frame", (lx - 0.1, ly - 0.1, 0), (lx + 0.1, ly + 0.1, 0.02), M["black_metal"], C)
    box("Lantern glass", (lx - 0.09, ly - 0.09, 0.02), (lx + 0.09, ly + 0.09, 0.4), M["glass"], C)
    cyl("Lantern candle", lx, ly, 0.02, 0.14, 0.035, M["lamp_glow"], 12)
    point_light("Lantern light", (lx, ly, 0.2), 4, 0.03, (1.0, 0.6, 0.3))
    box("Lantern top", (lx - 0.1, ly - 0.1, 0.4), (lx + 0.1, ly + 0.1, 0.43), M["black_metal"], C)
    plant("Patio palm", x0 + 0.25, y1 - 0.3, 1.5, 0.2, "palm", 11)
    plant("Patio olive", x1 - 0.22, y1 - 0.75, 1.1, 0.16, "ficus", 12)
    # planter boxes get greenery
    for i, p in enumerate(_plan["planters"]):
        lo, hi = p["min"], p["max"]
        rnd = random.Random(i)
        nb = max(2, int((hi[0] - lo[0]) * (hi[1] - lo[1]) * 9))
        for k in range(nb):
            x = rnd.uniform(lo[0] + 0.18, hi[0] - 0.18)
            y = rnd.uniform(lo[1] + 0.18, hi[1] - 0.18)
            r = rnd.uniform(0.18, 0.28)
            bush(f"Planter shrub {i}.{k}", x, y, 0.45 + r * 0.7, r, i * 31 + k, 110)


def lounge_chair(x, y):
    """Rattan lounge chair facing +Y before rotation."""
    rbox("Lounge base", (x - 0.33, y - 0.33, 0.12), (x + 0.33, y + 0.33, 0.36), M["rattan"], 0.04, 2)
    rbox("Lounge cushion", (x - 0.3, y - 0.3, 0.36), (x + 0.3, y + 0.3, 0.44), M["cushion_cream"], 0.04, 3)
    b = rbox("Lounge back", (x - 0.33, y - 0.36, 0.36), (x + 0.33, y - 0.26, 0.85), M["rattan"], 0.04, 2)
    rbox("Lounge back cushion", (x - 0.28, y - 0.27, 0.44), (x + 0.28, y - 0.18, 0.8), M["cushion_cream"], 0.04, 3)
    for sx in (-0.28, 0.28):
        for sy in (-0.28, 0.28):
            cyl("Lounge leg", x + sx, y + sy, 0, 0.12, 0.015, M["black_metal"], 8)


def bed(name, hx, hy, w, L, facing, linen=None):
    """Bed with its headboard centred at (hx, hy) on a wall, extending along `facing`."""
    f = Vector((*facing, 0)).normalized()
    s = Vector((f.y, -f.x, 0))
    c = Vector((hx, hy, 0))

    def rect(a0, a1, b0, b1):
        pts = [c + s * a + f * b for a in (a0, a1) for b in (b0, b1)]
        return min(p.x for p in pts), min(p.y for p in pts), max(p.x for p in pts), max(p.y for p in pts)
    x0, y0, x1, y1 = rect(-w / 2, w / 2, 0.06, L)
    rbox(name + " base", (x0, y0, 0.08), (x1, y1, 0.38), M["drape"], 0.03)
    rbox(name + " mattress", (x0 + 0.02, y0 + 0.02, 0.38), (x1 - 0.02, y1 - 0.02, 0.58), linen or M["bed_linen"], 0.06, 3)
    x0, y0, x1, y1 = rect(-w / 2 - 0.15, w / 2 + 0.15, 0, 0.08)
    rbox(name + " headboard", (x0, y0, 0), (x1, y1, 1.15), M["sofa"], 0.03, 2)
    x0, y0, x1, y1 = rect(-w / 2, w / 2, L * 0.62, L * 0.92)
    rbox(name + " throw", (x0 - 0.02, y0, 0.58), (x1 + 0.02, y1, 0.6), M["throw"], 0.01)
    for k in (-1, 1):
        x0, y0, x1, y1 = rect(k * w / 4 - 0.3, k * w / 4 + 0.3, 0.12, 0.42)
        p = rbox(name + " pillow", (x0, y0, 0.58), (x1, y1, 0.74), M["cushion_cream"], 0.06, 3)
        x0, y0, x1, y1 = rect(k * (w / 2 + 0.45) - 0.25, k * (w / 2 + 0.45) + 0.25, 0.02, 0.45)
        rbox(name + " nightstand", (x0, y0, 0), (x1, y1, 0.5), M["cabinet_cream"], 0.01)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        cyl(name + " lamp", cx, cy, 0.5, 0.8, 0.09, M["sheer"], 16, 0.07)


def bedrooms_baths():
    # beds placed from the drawing symbols (pillow end = headboard wall)
    bed("C. Bed 2 bed", X(402) + 0.09, (Y(697) + Y(800)) / 2, 1.6, 2.05, (1, 0))
    bpy.data.objects["C. Bed 2 bed throw"].data.materials[0] = M["teal_fabric"]
    # teal feature wall with brass trims and framed art behind the bed (photos p42-p48)
    fy = (Y(697) + Y(800)) / 2
    rbox("C. Bed 2 feature panel", (X(402), fy - 1.35, 0), (X(402) + 0.03, fy + 1.35, 2.75), M["teal"], 0.003)
    for k in (-1.35, 1.35):
        box("C. Bed 2 brass trim", (X(402) + 0.03, fy + k - 0.01, 0), (X(402) + 0.04, fy + k + 0.01, 2.75), M["brass"], C)
    rbox("C. Bed 2 upholstered head", (X(402) + 0.03, fy - 0.95, 0.4), (X(402) + 0.09, fy + 0.95, 1.35), M["cushion_cream"], 0.02)
    art("C. Bed 2 art", (X(402) + 0.04, fy), (1, 0), 1.1, 0.75, 1.85, M["art_abstract"])
    for k in (-1, 1):
        cyl("C. Bed 2 sconce", X(402) + 0.08, fy + k * 1.15, 1.45, 1.6, 0.05, M["lamp_glow"], 12)
    rbox("C. Bed 2 rug", (X(430), Y(820), 0), (X(560), Y(690), 0.015), M["rug"], 0.01)
    rbox("C. Bed 2 desk", (X(592), Y(800), 0.72), (X(626), Y(740), 0.75), M["cabinet_cream"], 0.005)
    rbox("C. Bed 2 desk side", (X(592), Y(800), 0.0), (X(626), Y(796), 0.72), M["cabinet_cream"], 0.003)
    objs = track(lambda: dining_chair(X(584) - 0.05, (Y(800) + Y(740)) / 2))
    rot_group(objs, (X(584) - 0.05, (Y(800) + Y(740)) / 2), 90)
    for o in objs:
        if "seat" in o.name or "back" in o.name:
            o.data.materials[0] = M["teal_fabric"]
    rbox("Laptop", (X(600), Y(785), 0.75), (X(620), Y(760), 0.77), M["steel"], 0.003)
    plant("C. Bed 2 plant", X(615), Y(690), 1.3, 0.17, "palm", 21)
    rbox("C. Bed 2 wardrobe", (X(470), Y(612), 0), (X(545), Y(586), 2.4), M["cabinet_cream"], 0.005)
    curtain("C. Bed 2 sheer", (X(452), Y(846) + 0.15), (X(500), Y(846) + 0.15), 0.02, 2.7, M["sheer"], amp=0.05)
    bed("Master bed", (X(65) + X(167)) / 2, Y(833), 1.8, 2.1, (0, 1))
    rbox("Master wardrobe", (X(270), Y(780), 0), (X(305), Y(600), 2.5), M["cabinet_taupe"], 0.005)
    bed("C. Bed 1 bed", (X(60) + X(160)) / 2, Y(14), 1.6, 2.05, (0, -1))
    rbox("C. Bed 1 desk", (X(164), Y(70), 0.72), (X(275), Y(20), 0.75), M["wood_light"], 0.005)
    rbox("C. Bed 1 wardrobe", (X(128), Y(326), 0), (X(240), Y(290), 2.4), M["cabinet_cream"], 0.005)
    # prayer space: window seat + mats
    rbox("Window seat", (X(745), Y(573), 0), (X(779), Y(400), 0.45), M["cabinet_cream"], 0.01)
    rbox("Window seat cushion", (X(745), Y(573), 0.45), (X(779), Y(400), 0.52), M["wood_light"], 0.02)
    for i in range(4):
        y0 = Y(560) + i * 0.68
        rbox(f"Prayer mat {i}", (X(660), y0, 0), (X(735), y0 + 0.6, 0.01), M["cushion_rust"] if i % 2 else M["throw"], 0.003)
    # bathrooms: WC + vanity
    def bath(nm, wc, vanity, wc_face):
        cx, cy = wc
        cyl(nm + " WC", cx, cy, 0, 0.4, 0.19, M["ceramic"], 24, 0.17)
        f = Vector((*wc_face, 0))
        t = Vector((cx, cy, 0)) - f * 0.3
        rbox(nm + " cistern", (t.x - 0.18, t.y - 0.18, 0.0), (t.x + 0.18, t.y + 0.18, 0.75), M["ceramic"], 0.03)
        vx, vy, vw, vd, along_x = vanity
        lo = (vx - vw / 2, vy - vd / 2, 0.5) if along_x else (vx - vd / 2, vy - vw / 2, 0.5)
        hi = (vx + vw / 2, vy + vd / 2, 0.85) if along_x else (vx + vd / 2, vy + vw / 2, 0.85)
        rbox(nm + " vanity", lo, hi, M["cabinet_taupe"], 0.01)
        cyl(nm + " basin", vx, vy, 0.85, 0.97, 0.2, M["ceramic"], 24, 0.22)
    bath("Toilet 1", (X(326), Y(40)), (X(300), Y(100), 0.5, 0.4, False), (0, -1))
    bath("Master toilet", (X(150), Y(560)), (X(205), Y(520), 0.6, 0.42, True), (0, -1))
    bath("Toilet 2", (X(668), Y(625)), (X(722), Y(620), 0.5, 0.4, False), (1, 0))
    rbox("Basin area vanity", (X(288), Y(220), 0.5), (X(288) + 0.4, Y(180), 0.85), M["cabinet_taupe"], 0.01)
    cyl("Basin area basin", X(288) + 0.2, (Y(220) + Y(180)) / 2, 0.85, 0.97, 0.2, M["ceramic"], 24, 0.22)
    box("Basin area mirror", (X(288), Y(215), 1.1), (X(288) + 0.01, Y(185), 1.9), M["chrome"], C)

def area_light(name, loc, size, watts, color=(1.0, 0.72, 0.45)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = watts
    ld.size = size
    ld.color = color
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    C.objects.link(o)
    return o


ROOM_LIGHT = {"bedroom": 70, "bath": 30, "prayer": 35}


def room_lights():
    """Warm ceiling lights (with a visible flush fitting) in rooms without coves."""
    for r in _plan["rooms"]:
        w = ROOM_LIGHT.get(r["use"])
        if r["name"] in ("Lobby", "Corridor"):
            w = 25
        if not w:
            continue
        xs = [p[0] for p in r["polygon"]]
        ys = [p[1] for p in r["polygon"]]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        cyl(r["name"] + " ceiling fitting", cx, cy, 2.97, 3.0, 0.18, M["led_panel"], 32)
        area_light(r["name"] + " ceiling light", (cx, cy, 2.95), 0.35, w)
    # bedside lamps glow
    for o in [o for o in bpy.data.objects if o.name.endswith(" lamp") and "bed" in o.name.lower()]:
        area_light(o.name + " light", (o.location.x, o.location.y, 0.95), 0.12, 6)
    # patio wall sconces beside the back doors
    for k, xx in enumerate((X(470), X(596))):
        box(f"Patio sconce {k}", (xx - 0.05, Y(846) - 0.12, 1.85), (xx + 0.05, Y(846) - 0.1, 2.05), M["lamp_glow"], C)
        area_light(f"Patio sconce light {k}", (xx, Y(846) - 0.2, 1.95), 0.1, 10, (1.0, 0.62, 0.35))


_plan = None


def furnish(plan):
    global C, _plan
    _plan = plan
    root = coll("Furniture")
    for name, fn in (("Living", living), ("Dining", dining), ("Kitchen", kitchen), ("Patio", patio),
                     ("Rooms", bedrooms_baths), ("Lights", room_lights)):
        C = coll("F " + name, root)
        before = set(bpy.data.objects)
        fn()
        # anything created via modelkit lands in "Model": move it here
        for o in bpy.data.objects:
            if o not in before and C not in o.users_collection:
                link(o, C)
    m = bpy.data.collections.get("Model")
    if m and not m.objects:
        bpy.data.collections.remove(m)
