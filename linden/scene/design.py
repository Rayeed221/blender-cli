"""Room designs from the Interior Studio deck (ref/design.pdf), layered on top of the base
furnishing in furniture.py. Coordinates are drawing pixels via X()/Y() (see furniture.py)."""
import math
import random

import bpy
from mathutils import Vector

import furniture as F
from arch import box, coll
from furniture import X, Y, rbox, cyl, art, curtain, plant, track, rot_group, area_light
from mats import M

H = 3.0


GROUP = {"Lobby": "F Living", "Living design": "F Living", "Dining design": "F Dining", "Prayer": "F Dining",
         "Kitchen design": "F Kitchen", "Basin": "F Rooms", "Master": "F Rooms", "C. Bed 1 design": "F Rooms",
         "C. Bed 2 design": "F Rooms", "Baths": "F Rooms"}


def use(name):
    # design pieces join the existing furniture groups so they are baked + exported with them
    F.C = bpy.data.collections[GROUP[name]]


def remove(prefixes, collection=None):
    pool = bpy.data.collections[collection].all_objects if collection else bpy.data.objects
    for o in list(pool):
        if any(o.name.startswith(p) for p in prefixes):
            bpy.data.objects.remove(o)


# ------------------------------------------------------------------ shared fixtures
def ceiling_fan(name, x, y, drop=0.45, top=H):
    z = top - drop
    cyl(name + " rod", x, y, z, top, 0.012, M["white_gloss"], 8)
    cyl(name + " motor", x, y, z - 0.08, z + 0.02, 0.11, M["white_gloss"], 24, 0.09)
    for i in range(3):
        a = 2 * math.pi * i / 3 + 0.3
        bl = F.rbox(f"{name} blade {i}", (x + 0.12, y - 0.055, z - 0.05), (x + 0.68, y + 0.055, z - 0.038), M["white_gloss"], 0.02)
        rot_group([bl], (x, y), math.degrees(a))


def ac_unit(name, center, normal, z=2.42):
    n = Vector((*normal, 0)).normalized()
    u = Vector((n.y, -n.x, 0))
    c = Vector((*center, 0))
    p = [c - u * 0.45, c + u * 0.45, c - u * 0.45 + n * 0.22, c + u * 0.45 + n * 0.22]
    rbox(name, (min(q.x for q in p), min(q.y for q in p), z), (max(q.x for q in p), max(q.y for q in p), z + 0.3), M["white_plastic"], 0.03, 3)
    q = [c - u * 0.4 + n * 0.222, c + u * 0.4 + n * 0.225]
    box(name + " vent", (min(v.x for v in q) - 0.002, min(v.y for v in q) - 0.002, z + 0.04),
        (max(v.x for v in q) + 0.002, max(v.y for v in q) + 0.002, z + 0.07), M["steel"], F.C)


def fluted(name, x0, y0, x1, y1, z0, z1, along_x, pitch=0.045, depth=0.02, mat=None):
    """Vertical fluted panel: a backer plus rounded vertical ribs."""
    mat = mat or M["panel_beige"]
    box(name + " backer", (x0, y0, z0), (x1, y1, z1), mat, F.C)
    L = (x1 - x0) if along_x else (y1 - y0)
    n = max(1, int(L / pitch))
    for i in range(n):
        a = i * L / n
        b = a + L / n * 0.7
        if along_x:
            F.rbox(f"{name} rib", (x0 + a, y0 - depth, z0), (x0 + b, y0, z1), mat, 0.008, 2)
        else:
            F.rbox(f"{name} rib", (x1, y0 + a, z0), (x1 + depth, y0 + b, z1), mat, 0.008, 2)


def round_mirror(name, center, normal, r, z):
    """Back-lit round mirror on a wall (normal points into the room)."""
    n = Vector((*normal, 0)).normalized()
    c = Vector((*center, 0)) + n * 0.03
    disc = F.cyl(name, 0, 0, -0.012, 0.012, r, M["mirror"], 48)
    halo = F.cyl(name + " halo", 0, 0, -0.02, -0.005, r + 0.02, M["led"], 48)
    for o in (disc, halo):
        o.rotation_euler = (math.pi / 2, 0, math.atan2(n.y, n.x) - math.pi / 2)
        o.location = (c.x, c.y, z)


# ------------------------------------------------------------------ rooms
def lobby():
    """Shoe cabinet by the entry (p4-p5): cream tall unit, lit niche, fluted grey panel, bench."""
    use("Lobby")
    xw = X(612)            # inside face of the east wall south of the entry door
    y0, y1 = Y(410) + 0.05, Y(342) - 0.02
    d = 0.4
    rbox("Shoe cabinet lower", (xw - d, y0 + 0.4, 0.42), (xw, y1, 1.25), M["cabinet_cream"], 0.004)
    rbox("Shoe cabinet upper", (xw - d, y0 + 0.4, 1.6), (xw, y1, 2.95), M["cabinet_cream"], 0.004)
    box("Shoe niche back", (xw - 0.02, y0 + 0.4, 1.25), (xw, y1, 1.6), M["panel_beige"], F.C)
    box("Shoe niche light", (xw - d + 0.05, y0 + 0.42, 1.585), (xw - 0.05, y1 - 0.02, 1.595), M["led"], F.C)
    F.plant("Niche plant", xw - 0.2, y1 - 0.15, 0.25, 0.05, "ficus", 31)
    for o in [o for o in bpy.data.objects if o.name.startswith("Niche plant")]:
        o.location.z += 1.25
    box("Shoe plinth shelf", (xw - d, y0, 0.0), (xw, y1, 0.08), M["greige"], F.C)
    box("Shoe shelf light", (xw - d + 0.03, y0 + 0.02, 0.34), (xw - 0.03, y0 + 0.38, 0.35), M["led"], F.C)
    rbox("Shoe bench", (xw - d, y0, 0.36), (xw, y0 + 0.4, 0.46), M["greige"], 0.01)
    rbox("Bench cushion", (xw - d + 0.02, y0 + 0.02, 0.46), (xw - 0.02, y0 + 0.38, 0.52), M["grey_fabric"], 0.02, 3)
    fluted("Lobby fluted", xw - 0.025, y0, xw, y0 + 0.4, 0.52, 2.95, False, mat=M["fluted_grey"])
    rnd = random.Random(4)
    for i in range(6):
        yy = y0 + 0.4 + (i + 0.5) * (y1 - y0 - 0.4) / 6
        F.rbox("Shoe", (xw - 0.3, yy - 0.05, 0.08), (xw - 0.06, yy + 0.05, 0.17),
               M["cushion_rust"] if i % 2 else M["dark_wood"], 0.03, 2)


def living():
    use("Living design")
    remove(["TV wall beige flank", "TV wall LED reveal"], "F Living")
    wx = X(378)
    # fluted beige flanks either side of the cream TV panel, with LED reveals (p7, p11)
    fluted("TV flute S", wx + 0.04, Y(250), wx + 0.06, Y(222), 0, 2.72, False)
    fluted("TV flute N", wx + 0.04, Y(124), wx + 0.06, Y(96), 0, 2.72, False)
    for yy in (Y(222) - 0.012, Y(124) + 0.002):
        box("TV LED reveal", (wx + 0.041, yy, 0.05), (wx + 0.052, yy + 0.012, 2.7), M["led"], F.C)
    # feature wall behind the sofa (p9-p10): beige panels, sculpted wave, fluted strips, LED lines
    ex = X(612)
    ya, yb = Y(262), Y(92)
    seg = (yb - ya)
    box("Feature panel", (ex - 0.03, ya, 0.0), (ex, yb, 2.72), M["panel_beige"], F.C)
    box("Feature wave", (ex - 0.045, ya + seg * 0.38, 0.95), (ex - 0.03, ya + seg * 0.62, 2.6), M["wave_relief"], F.C)
    for k in (0.32, 0.68):
        yy = ya + seg * k
        fluted(f"Feature flute {k}", ex - 0.05, yy - 0.12, ex - 0.03, yy + 0.12, 0.88, 2.72, False)
        box("Feature LED", (ex - 0.055, yy + 0.125, 0.88), (ex - 0.045, yy + 0.135, 2.7), M["led"], F.C)
    ceiling_fan("Living fan", (X(378) + X(616)) / 2, (Y(88) + Y(340)) / 2 + 0.25)
    ac_unit("Living AC", ((X(422) + X(569)) / 2, Y(88)), (0, -1))
    # decor: floor vase with branches, bicycle sculpture on the console
    cyl("Floor vase", X(600) - 0.25, Y(262) - 0.85, 0, 0.55, 0.13, M["ceramic"], 24, 0.08)
    for i in range(5):
        b = F.cyl(f"Branch {i}", 0, 0, 0, 0.8, 0.006, M["dark_wood"], 6)
        b.location = (X(600) - 0.25, Y(262) - 0.85, 0.5)
        b.rotation_euler = (math.radians(12 + i * 4), 0, math.radians(i * 72))


def dining():
    use("Dining design")
    remove(["Dinner wagon", "Wagon top", "Crockery", "Bowl", "Chandelier", "Chair", "Dining leg"], "F Dining")
    # crockery wall (p14): white base + dark top, diamond mirror splash, lit glass row, tall cabinets
    wy = Y(573)
    xa, xb = X(395), X(575)
    rbox("Crockery base", (xa, wy, 0.1), (xb, wy + 0.5, 0.86), M["white_gloss"], 0.004)
    box("Crockery kick", (xa, wy, 0), (xb, wy + 0.45, 0.1), M["black_metal"], F.C)
    rbox("Crockery top", (xa, wy, 0.86), (xb, wy + 0.52, 0.9), M["granite"], 0.004)
    box("Crockery mirror", (xa, wy, 0.9), (xb, wy + 0.012, 1.45), M["mirror"], F.C)
    n = 8
    for i in range(n + 1):  # diamond grid lines on the mirror
        for s in (-1, 1):
            o = F.box(f"Mirror line {i}", (0, -0.002, -0.4), (0.008, 0.002, 0.4), M["brass"], F.C)
            o.location = (xa + (xb - xa) * i / n, wy + 0.014, 1.175)
            o.rotation_euler = (0, s * math.radians(28), 0)
    for i in range(n):
        a, b = xa + (xb - xa) * i / n, xa + (xb - xa) * (i + 1) / n
        if i % 2 == 0:
            F.cyl("Display bowl", (a + b) / 2, wy + 0.25, 0.9, 0.98, 0.09, M["ceramic"], 16, 0.12)
    for i in range(5):
        a, b = xa + (xb - xa) * i / 5, xa + (xb - xa) * (i + 1) / 5
        box("Display back", (a, wy, 1.45), (b, wy + 0.02, 2.2), M["panel_beige"], F.C)
        box("Display glass", (a + 0.03, wy + 0.37, 1.48), (b - 0.03, wy + 0.376, 2.17), M["glass"], F.C)
        for xx in (a, b - 0.025):
            box("Display frame", (xx, wy, 1.45), (xx + 0.025, wy + 0.38, 2.2), M["black_metal"], F.C)
        box("Display top", (a, wy, 2.18), (b, wy + 0.38, 2.2), M["black_metal"], F.C)
        box("Display bottom", (a, wy, 1.45), (b, wy + 0.38, 1.47), M["black_metal"], F.C)
        box("Display light", (a + 0.04, wy + 0.05, 2.165), (b - 0.04, wy + 0.33, 2.175), M["led"], F.C)
        box("Display shelf", (a + 0.025, wy + 0.02, 1.82), (b - 0.025, wy + 0.36, 1.832), M["glass"], F.C)
        for k in range(3):
            F.cyl("Display cup", a + (b - a) * (k + 1) / 4, wy + 0.18, 1.832, 1.92, 0.04, M["ceramic"], 12, 0.05)
        rbox("Tall cabinet", (a + 0.003, wy, 2.22), (b - 0.003, wy + 0.4, 2.98), M["white_gloss"], 0.003)
    # chandelier: black ring with crystal drops (p14-p15)
    tx, ty = X(482), Y(435)
    F.put(F.mk.torus("Chandelier ring", major_radius=0.42, minor_radius=0.03, location=(tx, ty, 2.28), mat=M["black_metal"]))
    F.put(F.mk.torus("Chandelier glow", major_radius=0.42, minor_radius=0.012, location=(tx, ty, 2.245), mat=M["lamp_glow"]))
    for i in range(36):
        a = 2 * math.pi * i / 36
        r = 0.42 if i % 2 else 0.36
        ln = 0.18 if i % 2 else 0.26
        F.cyl(f"Crystal {i}", tx + r * math.cos(a), ty + r * math.sin(a), 2.25 - ln, 2.25, 0.01, M["glass"], 6)
    for i in range(3):
        a = 2 * math.pi * i / 3
        o = F.cyl("Chandelier cable", 0, 0, 0, 0.75, 0.003, M["black_metal"], 4)
        o.location = (tx + 0.4 * math.cos(a), ty + 0.4 * math.sin(a), 2.28)
        o.rotation_euler = (0, math.radians(-25), a)
    F.cyl("Chandelier rose", tx, ty, 2.97, 3.0, 0.08, M["black_metal"], 16)
    # pedestal table base in white (p15)
    remove(["Dining leg"], "F Dining")
    rbox("Dining pedestal", (tx - 0.6, ty - 0.18, 0), (tx + 0.6, ty + 0.18, 0.74), M["white_gloss"], 0.02)
    # barrel-back chairs: ribbed rose leather backs, grey seats, black legs
    seats = [(-0.45, -1, 0), (0.45, -1, 0), (-0.45, 1, 180), (0.45, 1, 180), (-1.12, 0, -90), (1.12, 0, 90)]
    for dx, side, rot in seats:
        cx = tx + dx
        cy = ty + side * 0.74 if side else ty
        objs = track(lambda: barrel_chair(cx, cy))
        rot_group(objs, (cx, cy), rot)
    ceiling_fan("Dining fan", tx + 1.35, ty - 0.2)
    art("Dining art", (X(337) + 0.02, Y(400)), (1, 0), 0.6, 0.8, 1.6, M["art"])


def barrel_chair(x, y):
    """Barrel chair facing +Y before rotation (the table is at +Y)."""
    rbox("Chair seat", (x - 0.24, y - 0.22, 0.42), (x + 0.24, y + 0.24, 0.5), M["grey_fabric"], 0.04, 3)
    r = 0.27
    for i in range(9):
        a = math.radians(-160 + i * 140 / 8)
        px, py = x + r * math.cos(a), y + 0.02 + r * math.sin(a)
        rib = F.rbox("Chair rib", (px - 0.044, py - 0.03, 0.48), (px + 0.044, py + 0.03, 0.8), M["leather_rose"], 0.028, 3)
        rot_group([rib], (px, py), math.degrees(a) + 90)
    for sx, sy in ((-0.2, -0.18), (0.2, -0.18), (-0.18, 0.2), (0.18, 0.2)):
        F.cyl("Chair leg", x + sx, y + sy, 0, 0.42, 0.011, M["black_metal"], 8)


def prayer():
    use("Prayer")
    remove(["Window seat", "Prayer mat"], "F Rooms")
    # window seat: white drawers + wood top (p18-p20)
    x0, x1 = X(745), X(779)
    ya, yb = Y(573) + 0.02, Y(400)
    rbox("Window seat", (x0, ya, 0.06), (x1, yb, 0.42), M["white_gloss"], 0.005)
    for k in range(1, 4):
        yy = ya + (yb - ya) * k / 4
        box("Seat drawer gap", (x0 - 0.002, yy - 0.003, 0.08), (x0 + 0.001, yy + 0.003, 0.4), M["black_metal"], F.C)
    rbox("Window seat top", (x0 - 0.02, ya, 0.42), (x1, yb, 0.48), M["dark_wood"], 0.01)
    curtain("Prayer sheer", (x1 - 0.12, Y(570)), (x1 - 0.12, Y(479)), 0.02, 2.75, M["sheer"], amp=0.03)
    curtain("Prayer drape", (x1 - 0.2, Y(479) - 0.05), (x1 - 0.2, Y(479) + 0.35), 0.02, 2.75, M["drape"], 4, 0.05)
    # tall white cabinet with black open bookshelf niche on the north wall (drawing "SHELF")
    ny = Y(375)
    ca, cb = X(648), X(722)
    rbox("Prayer cabinet low", (ca, ny - 0.4, 0), (cb, ny, 0.85), M["white_gloss"], 0.004)
    rbox("Prayer cabinet high", (ca, ny - 0.4, 2.1), (cb, ny, 2.98), M["white_gloss"], 0.004)
    box("Bookshelf back", (ca, ny - 0.02, 0.85), (cb, ny, 2.1), M["black_metal"], F.C)
    for xx in (ca, (ca + cb) / 2 - 0.01, cb - 0.02):
        box("Bookshelf side", (xx, ny - 0.38, 0.85), (xx + 0.02, ny, 2.1), M["black_metal"], F.C)
    rnd = random.Random(9)
    for z in (0.85, 1.25, 1.65):
        box("Bookshelf shelf", (ca, ny - 0.38, z), (cb, ny, z + 0.02), M["black_metal"], F.C)
        for k in range(5):
            xx = ca + 0.08 + k * (cb - ca - 0.16) / 5
            h = rnd.uniform(0.18, 0.3)
            box("Book", (xx, ny - 0.3, z + 0.02), (xx + 0.05, ny - 0.06, z + 0.02 + h),
                [M["cushion_rust"], M["drape"], M["dark_wood"], M["cushion_cream"]][k % 4], F.C)
    art("Kaaba art", ((X(640) + X(745)) / 2, Y(573) + 0.02), (0, 1), 0.6, 0.85, 1.55, M["art_kaaba"])
    # prayer rugs (navy with ivory border)
    for i in range(3):
        yy = Y(560) + i * 0.75
        rbox(f"Prayer rug {i}", (X(650), yy, 0), (X(735), yy + 0.65, 0.01), M["cushion_cream"], 0.003)
        rbox(f"Prayer rug field {i}", (X(650) + 0.06, yy + 0.06, 0.01), (X(735) - 0.06, yy + 0.59, 0.014), M["navy"], 0.002)
        rbox(f"Prayer rug arch {i}", (X(650) + 0.45, yy + 0.18, 0.014), (X(735) - 0.2, yy + 0.47, 0.016), M["cushion_cream"], 0.06, 3)
    # black-framed sliding frosted doors between dining and prayer (p15, p19)
    gx = X(636)
    y0, y1 = Y(573), Y(410)
    for k in range(4):
        yy = y0 + (y1 - y0) * k / 3 - (0.02 if k == 3 else 0)
        box("Slider mullion", (gx - 0.025, yy, 0), (gx + 0.025, yy + 0.04, 2.4), M["black_metal"], F.C)
    box("Slider head", (gx - 0.03, y0, 2.38), (gx + 0.03, y1, 2.45), M["black_metal"], F.C)
    box("Slider bulkhead", (gx - 0.06, y0, 2.45), (gx + 0.06, y1, 3.0), M["wall"], F.C)
    ceiling_fan("Prayer fan", (X(640) + X(745)) / 2, (Y(375) + Y(573)) / 2)


def basin_area():
    """Basin area (p22): fluted grey panel, round back-lit mirror, floating vanity, pendants."""
    use("Basin")
    remove(["Basin area"], "F Rooms")
    wx = X(288)
    ya, yb = Y(246), Y(155)
    yc = (ya + yb) / 2
    fluted("Basin fluted", wx, ya, wx + 0.02, ya + 0.18, 0, 2.95, False, mat=M["fluted_grey"])
    rbox("Basin vanity", (wx, yc - 0.42, 0.45), (wx + 0.46, yc + 0.42, 0.78), M["white_gloss"], 0.008)
    box("Basin vanity glow", (wx + 0.05, yc - 0.4, 0.44), (wx + 0.42, yc + 0.4, 0.45), M["led"], F.C)
    rbox("Basin top", (wx, yc - 0.44, 0.78), (wx + 0.48, yc + 0.44, 0.8), M["granite"], 0.004)
    rbox("Basin bowl", (wx + 0.1, yc - 0.25, 0.8), (wx + 0.42, yc + 0.25, 0.92), M["ceramic"], 0.04, 3)
    F.cyl("Basin tap", wx + 0.05, yc, 0.8, 1.05, 0.012, M["black_metal"], 8)
    round_mirror("Basin mirror", (wx, yc), (1, 0), 0.33, 1.55)
    for k in (-1, 1):
        F.cyl("Pendant cord", wx + 0.3, yc + k * 0.55, 1.6, 3.0, 0.003, M["black_metal"], 4)
        F.cyl("Pendant", wx + 0.3, yc + k * 0.55, 1.45, 1.6, 0.04, M["lamp_glow"], 12, 0.012)


def kitchen():
    """Kitchen (p24-p27): two-tier uppers to the ceiling, slim hood, black fridge, utility."""
    use("Kitchen design")
    remove(["Hood chimney", "Hood"], "F Kitchen")
    x0 = X(43)
    yN = Y(340)
    # top tier of solid taupe cabinets above the existing uppers, up to the ceiling
    for i in range(7):
        a = x0 + (X(262) - x0) * i / 7
        b = x0 + (X(262) - x0) * (i + 1) / 7
        rbox(f"Upper top {i}", (a + 0.004, yN - 0.35, 2.47), (b - 0.004, yN, 2.97), M["cabinet_taupe"], 0.004)
    for i in range(3):
        a = Y(470) + (yN - Y(470)) * i / 3
        b = Y(470) + (yN - Y(470)) * (i + 1) / 3
        rbox(f"Upper top west {i}", (x0, a + 0.004, 2.47), (x0 + 0.35, b - 0.004, 2.97), M["cabinet_taupe"], 0.004)
    hx = (X(172) + X(222)) / 2
    rbox("Slim hood", (hx - 0.42, yN - 0.36, 1.48), (hx + 0.42, yN, 1.55), M["steel"], 0.006)
    box("Hood light", (hx - 0.3, yN - 0.3, 1.475), (hx + 0.3, yN - 0.25, 1.48), M["led_panel"], F.C)
    rbox("Hood cabinet", (hx - 0.42, yN - 0.35, 1.55), (hx + 0.42, yN, 2.45), M["cabinet_taupe"], 0.004)
    # fridge in black steel with water dispenser (p26)
    for o in bpy.data.collections["F Kitchen"].all_objects:
        if o.name.startswith("Fridge") and o.data and o.data.materials and o.data.materials[0] == M["steel"]:
            o.data.materials[0] = M["black_steel"]
    # utility: washing machine with cabinet + open shelf above (p27)
    ux = X(115) - 0.02
    uy = (Y(501) + Y(586)) / 2
    rbox("Washing machine", (ux - 0.6, uy - 0.3, 0), (ux, uy + 0.3, 0.85), M["white_plastic"], 0.03, 3)
    door = F.cyl("Washer door", 0, 0, -0.02, 0.02, 0.2, M["black_glass"], 32)
    door.rotation_euler = (0, math.pi / 2, 0)
    door.location = (ux - 0.61, uy, 0.45)
    ring = F.cyl("Washer ring", 0, 0, -0.012, 0.012, 0.24, M["chrome"], 32)
    ring.rotation_euler = (0, math.pi / 2, 0)
    ring.location = (ux - 0.605, uy, 0.45)
    box("Utility shelf", (ux - 0.4, uy - 0.35, 1.2), (ux, uy + 0.35, 1.22), M["cabinet_cream"], F.C)
    rbox("Utility cabinet", (ux - 0.4, uy - 0.35, 1.55), (ux, uy + 0.35, 2.4), M["cabinet_cream"], 0.004)
    F.rbox("Towels", (ux - 0.3, uy - 0.2, 1.22), (ux - 0.05, uy + 0.05, 1.36), M["grey_fabric"], 0.02, 2)


def master():
    use("Master")
    remove(["Master wardrobe", "Master bed"], "F Rooms")
    # bed: tan upholstered with tall headboard, terracotta + cream cushions (p29-p33)
    F.bed("Master bed", (X(65) + X(167)) / 2, Y(833), 1.8, 2.1, (0, 1))
    for o in bpy.data.objects:
        if o.name.startswith("Master bed headboard") or o.name.startswith("Master bed base"):
            o.data.materials[0] = M["tan_leather"]
        if o.name.startswith("Master bed pillow"):
            o.data.materials[0] = M["cushion_rust"]
    art("Master leaf art", ((X(65) + X(167)) / 2 - 0.25, Y(833) + 0.03), (0, 1), 0.65, 0.85, 1.75, M["art_leaf"])
    # full-wall wardrobe: white doors over a greige band, long bar handles (p30)
    ex = X(305)
    ya, yb = Y(785), Y(615)
    d = 0.6
    n = 5
    for i in range(n):
        a, b = ya + (yb - ya) * i / n, ya + (yb - ya) * (i + 1) / n
        rbox(f"Wardrobe door {i}", (ex - d, a + 0.003, 0.65), (ex, b - 0.003, 2.98), M["white_gloss"], 0.003)
        rbox(f"Wardrobe base {i}", (ex - d, a + 0.003, 0.05), (ex, b - 0.003, 0.65), M["greige"], 0.003)
        hy = b - 0.06 if i % 2 == 0 else a + 0.06
        F.cyl("Wardrobe handle", ex - d - 0.02, hy, 0.95, 1.55, 0.008, M["steel"], 8)
    box("Wardrobe plinth", (ex - d + 0.04, ya, 0), (ex, yb, 0.05), M["black_metal"], F.C)
    # dressing table with mirror and stool (p32), against the north wall by the drawing's dressing units
    dy = Y(598)
    dx0, dx1 = X(95), X(175)
    rbox("Dressing table", (dx0, dy - 0.45, 0.72), (dx1, dy, 0.76), M["white_gloss"], 0.004)
    rbox("Dressing drawer", (dx0, dy - 0.45, 0.6), (dx1, dy, 0.72), M["white_gloss"], 0.004)
    for xx in (dx0 + 0.02, dx1 - 0.06):
        box("Dressing leg", (xx, dy - 0.43, 0), (xx + 0.04, dy - 0.39, 0.6), M["white_gloss"], F.C)
    box("Dressing mirror", (dx0 + 0.15, dy - 0.02, 0.85), (dx1 - 0.15, dy, 2.2), M["mirror"], F.C)
    for xx in (dx0 + 0.12, dx1 - 0.15):
        box("Dressing mirror LED", (xx, dy - 0.025, 0.85), (xx + 0.02, dy - 0.02, 2.2), M["led"], F.C)
    F.cyl("Dressing stool", (dx0 + dx1) / 2, dy - 0.7, 0, 0.45, 0.2, M["cushion_cream"], 24)
    F.cyl("Dressing stool base", (dx0 + dx1) / 2, dy - 0.7, 0, 0.3, 0.19, M["wood_light"], 24)
    for k in range(5):
        F.cyl("Cosmetic", dx0 + 0.25 + k * 0.08, dy - 0.15, 0.76, 0.76 + 0.06 + 0.03 * (k % 3), 0.02, [M["cushion_rust"], M["ceramic"], M["brass"]][k % 3], 8)
    # curtains: sheers + taupe drapes on the west window and the veranda door
    curtain("Master sheer W", (X(49) + 0.15, Y(767)), (X(49) + 0.15, Y(668)), 0.02, 2.7, M["sheer"], amp=0.03)
    curtain("Master drape W1", (X(49) + 0.22, Y(668)), (X(49) + 0.22, Y(668) + 0.35), 0.02, 2.7, M["drape"], 4, 0.05)
    curtain("Master drape W2", (X(49) + 0.22, Y(767) - 0.35), (X(49) + 0.22, Y(767)), 0.02, 2.7, M["drape"], 4, 0.05)
    curtain("Master sheer S", (X(200), Y(833) + 0.15), (X(258), Y(833) + 0.15), 0.02, 2.7, M["sheer"], amp=0.03)
    curtain("Master drape S", (X(258), Y(833) + 0.22), (X(282), Y(833) + 0.22), 0.02, 2.7, M["drape"], 4, 0.05)
    rbox("Master rug", (X(70), Y(820) + 1.4, 0), (X(200), Y(820) + 2.6, 0.015), M["rug_pattern"], 0.01)
    ac_unit("Master AC", ((X(49) + X(305)) / 2 + 0.6, Y(598)), (0, -1))
    ceiling_fan("Master fan", (X(49) + X(305)) / 2, (Y(598) + Y(833)) / 2)


def bed1():
    """C. Bed 1 (p35-p40): dark mocha walls, star ceiling, dark bed, desk + shelves, lit wardrobe."""
    use("C. Bed 1 design")
    remove(["C. Bed 1"], "F Rooms")
    F.bed("C. Bed 1 bed", (X(60) + X(160)) / 2, Y(14), 1.6, 2.05, (0, -1))
    for o in bpy.data.objects:
        if o.name.startswith("C. Bed 1 bed") and o.type == "MESH":
            nm = o.name
            if "headboard" in nm or "base" in nm:
                o.data.materials[0] = M["dark_fabric"]
            elif "throw" in nm or "mattress" in nm:
                o.data.materials[0] = M["grey_fabric"] if "mattress" in nm else M["dark_fabric"]
            elif "nightstand" in nm:
                o.data.materials[0] = M["dark_wood"]
    # desk with open shelving above along the north wall (east of the bed)
    ny = Y(14)
    rbox("C. Bed 1 desk", (X(178), ny - 0.55, 0.72), (X(272), ny, 0.76), M["dark_wood"], 0.004)
    rbox("C. Bed 1 drawers", (X(250), ny - 0.55, 0), (X(272), ny, 0.72), M["dark_wood"], 0.004)
    box("C. Bed 1 desk panel", (X(178), ny - 0.02, 0.76), (X(272), ny, 1.5), M["granite"], F.C)
    for z in (1.6, 1.95, 2.3):
        box("C. Bed 1 shelf", (X(225), ny - 0.3, z), (X(272), ny, z + 0.025), M["dark_wood"], F.C)
        box("C. Bed 1 shelf light", (X(226), ny - 0.28, z - 0.006), (X(271), ny - 0.24, z), M["led"], F.C)
    F.rbox("C. Bed 1 laptop", (X(200), ny - 0.4, 0.76), (X(215), ny - 0.15, 0.775), M["steel"], 0.003)
    objs = track(lambda: F.dining_chair((X(200) + X(215)) / 2, ny - 0.8))
    rot_group(objs, ((X(200) + X(215)) / 2, ny - 0.8), 180)
    for o in objs:
        if o.type == "MESH" and ("seat" in o.name or "back" in o.name):
            o.data.materials[0] = M["dark_fabric"]
    # dark wardrobe with bronze-glass lit doors along the south (drawing wardrobe)
    sy = Y(326)
    for i in range(4):
        a, b = X(128) + (X(240) - X(128)) * i / 4, X(128) + (X(240) - X(128)) * (i + 1) / 4
        box("C. Bed 1 wardrobe back", (a, sy, 0.05), (b, sy + 0.04, 2.6), M["dark_wood"], F.C)
        box("C. Bed 1 wardrobe glass", (a + 0.03, sy + 0.555, 0.1), (b - 0.03, sy + 0.56, 2.55), M["bronze_glass"], F.C)
        for xx in (a, b - 0.025):
            box("C. Bed 1 wardrobe frame", (xx, sy, 0.05), (xx + 0.025, sy + 0.57, 2.6), M["black_metal"], F.C)
        box("C. Bed 1 wardrobe light", (a + 0.04, sy + 0.05, 2.55), (b - 0.04, sy + 0.5, 2.56), M["led"], F.C)
        F.cyl("Hanging clothes", (a + b) / 2, sy + 0.3, 1.2, 2.0, 0.09, [M["grey_fabric"], M["drape"], M["cushion_cream"]][i % 3], 10)
    box("C. Bed 1 wardrobe top", (X(128), sy, 2.6), (X(240), sy + 0.57, 2.98), M["dark_wood"], F.C)
    # charcoal drapes + sheers at the windows
    curtain("C. Bed 1 sheer N", (X(117), ny - 0.15), (X(160), ny - 0.15), 0.02, 2.7, M["sheer"], amp=0.03)
    curtain("C. Bed 1 drape N", (X(160), ny - 0.22), (X(190), ny - 0.22), 0.02, 2.7, M["dark_fabric"], 4, 0.05)
    curtain("C. Bed 1 drape W", (X(49) + 0.22, Y(172)), (X(49) + 0.22, Y(130)), 0.02, 2.7, M["dark_fabric"], 4, 0.05)
    rbox("C. Bed 1 rug", (X(70), Y(250), 0), (X(230), Y(160), 0.015), M["rug"], 0.01)
    ac_unit("C. Bed 1 AC", (X(49), Y(230) + 0.6), (1, 0))
    # warm LED cove around the star ceiling (p35, p39)
    xa, xb, ya_, yb_ = X(49), X(276), Y(228), Y(14)
    for nm, lo, hi in [("N", (xa, yb_ - 0.12, 2.82), (xb, yb_, 2.85)), ("E", (xb - 0.12, Y(327), 2.82), (xb, yb_, 2.85)),
                       ("W", (xa, ya_, 2.82), (xa + 0.12, yb_, 2.85))]:
        box(f"C. Bed 1 cove {nm}", lo, hi, M["dark_wall"], F.C)
        box(f"C. Bed 1 cove LED {nm}", (lo[0], lo[1], 2.85), (hi[0], hi[1], 2.86), M["led"], F.C)
    area_light("C. Bed 1 cove light", ((xa + xb) / 2, (ya_ + yb_) / 2 + 0.5, 2.6), 2.2, 90)
    ceiling_fan("C. Bed 1 fan", (X(49) + X(276)) / 2, (Y(14) + Y(228)) / 2)


def bed2():
    """C. Bed 2 additions (p42-p49): bronze-glass wardrobe with lit shelves, drapes, fan, AC."""
    use("C. Bed 2 design")
    remove(["C. Bed 2 wardrobe"], "F Rooms")
    sy = Y(586)
    xa, xb = X(470), X(560)
    for i in range(3):
        a, b = xa + (xb - xa) * i / 3, xa + (xb - xa) * (i + 1) / 3
        box("C. Bed 2 wardrobe back", (a, sy - 0.04, 0.05), (b, sy, 2.6), M["cabinet_cream"], F.C)
        box("C. Bed 2 wardrobe glass", (a + 0.03, sy - 0.56, 0.1), (b - 0.03, sy - 0.555, 2.55), M["bronze_glass"], F.C)
        for xx in (a, b - 0.025):
            box("C. Bed 2 wardrobe frame", (xx, sy - 0.57, 0.05), (xx + 0.025, sy, 2.6), M["brass"], F.C)
        box("C. Bed 2 wardrobe light", (a + 0.04, sy - 0.5, 2.55), (b - 0.04, sy - 0.05, 2.56), M["led"], F.C)
        F.cyl("Hanging clothes", (a + b) / 2, sy - 0.3, 1.2, 2.0, 0.09, [M["teal_fabric"], M["cushion_cream"], M["drape"]][i], 10)
    box("C. Bed 2 wardrobe top", (xa, sy - 0.57, 2.6), (xb, sy, 2.98), M["cabinet_cream"], F.C)
    curtain("C. Bed 2 drape", (X(500), Y(846) + 0.22), (X(530), Y(846) + 0.22), 0.02, 2.7, M["drape"], 4, 0.05)
    ac_unit("C. Bed 2 AC", (X(628), (Y(800) + Y(840)) / 2 + 0.9), (-1, 0))
    ceiling_fan("C. Bed 2 fan", (X(402) + X(628)) / 2 + 0.3, (Y(584) + Y(839)) / 2)


def baths():
    """Bathrooms (p51-p59): floating vanities with LED glow, vessel basins, black fittings,
    mirrors with LED, wall-hung WCs, rain showers behind black-framed glass."""
    use("Baths")
    remove(["Toilet 1 ", "Master toilet ", "Toilet 2 "], "F Rooms")

    def wc(nm, x, y, face):
        f = Vector((*face, 0)).normalized()
        c = Vector((x, y, 0))
        back = c - f * 0.28
        rbox(nm + " cistern panel", (back.x - 0.22 if abs(f.y) > 0.5 else back.x - 0.06, back.y - 0.06 if abs(f.y) > 0.5 else back.y - 0.22, 0),
             (back.x + 0.22 if abs(f.y) > 0.5 else back.x + 0.06, back.y + 0.06 if abs(f.y) > 0.5 else back.y + 0.22, 1.05), M["wall_tile"], 0.004)
        bowl = F.mk.sphere(nm + " WC", radius=1, segments=24, rings=12, mat=M["ceramic"])
        bowl.scale = (0.2 if abs(f.y) > 0.5 else 0.28, 0.28 if abs(f.y) > 0.5 else 0.2, 0.2)
        bowl.location = (c.x, c.y, 0.4)
        F.put(bowl)
        F.cyl(nm + " seat", c.x, c.y, 0.4, 0.43, 0.2, M["ceramic"], 24)

    def vanity(nm, x0, y0, x1, y1, mirror_side, round_mirror_r=None):
        rbox(nm + " vanity", (x0, y0, 0.45), (x1, y1, 0.8), M["greige"], 0.006)
        box(nm + " vanity glow", (x0 + 0.03, y0 + 0.03, 0.44), (x1 - 0.03, y1 - 0.03, 0.45), M["led"], F.C)
        rbox(nm + " counter", (x0 - 0.01, y0 - 0.01, 0.8), (x1 + 0.01, y1 + 0.01, 0.83), M["granite"], 0.004)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rbox(nm + " basin", (cx - 0.22, cy - 0.16, 0.83), (cx + 0.22, cy + 0.16, 0.95), M["ceramic"], 0.04, 3)
        wall = Vector((*mirror_side, 0))
        tap = Vector((cx, cy, 0)) + wall * 0.15
        F.cyl(nm + " tap", tap.x, tap.y, 0.83, 1.08, 0.012, M["black_metal"], 8)
        mp = Vector((cx, cy, 0)) + wall * ((abs(x1 - x0) if abs(wall.x) > 0.5 else abs(y1 - y0)) / 2)
        if round_mirror_r:
            round_mirror(nm + " mirror", (mp.x, mp.y), (-wall.x, -wall.y), round_mirror_r, 1.55)
        else:
            w = 0.6
            u = Vector((wall.y, -wall.x, 0))
            p0, p1 = mp - u * w / 2 - wall * 0.12, mp + u * w / 2
            rbox(nm + " mirror cabinet", (min(p0.x, p1.x), min(p0.y, p1.y), 1.2), (max(p0.x, p1.x), max(p0.y, p1.y), 1.9), M["mirror"], 0.004)
            box(nm + " mirror LED", (min(p0.x, p1.x), min(p0.y, p1.y), 1.185), (max(p0.x, p1.x), max(p0.y, p1.y), 1.2), M["led"], F.C)

    def shower(nm, x, y, wall):
        w = Vector((*wall, 0))
        p = Vector((x, y, 0)) + w * 0.25
        F.cyl(nm + " shower arm", p.x, p.y, 2.15, 2.18, 0.012, M["black_metal"], 8)
        rbox(nm + " rain head", (p.x - 0.15, p.y - 0.15, 2.12), (p.x + 0.15, p.y + 0.15, 2.14), M["black_metal"], 0.005)
        q = Vector((x, y, 0)) + w * 0.42
        rbox(nm + " mixer", (q.x - 0.04, q.y - 0.04, 1.0), (q.x + 0.04, q.y + 0.04, 1.2), M["black_metal"], 0.01)

    # Toilet 1 (288..365, 14..143): WC on north wall, vanity on west, shower east
    wc("Toilet 1", X(326), Y(14) - 0.32, (0, -1))
    vanity("Toilet 1", X(288), Y(130), X(288) + 0.45, Y(80), (-1, 0), 0.28)
    # Master toilet (128..305, 501..586): vanity on north wall, WC on west, shower east of glass x237
    wc("Master toilet", X(128) + 0.32, Y(560), (1, 0))
    vanity("Master toilet", X(160), Y(501) - 0.45, X(225), Y(501), (0, 1))
    shower("Master toilet", (X(237) + X(305)) / 2, Y(501) - 0.2, (0, 1))
    # Toilet 2 (642..735, 584..734): vanity on east wall, WC on north, shower south of glass y688
    wc("Toilet 2", X(668), Y(584) - 0.32, (0, -1))
    vanity("Toilet 2", X(735) - 0.45, Y(660), X(735), Y(610), (1, 0), 0.26)
    shower("Toilet 2", (X(642) + X(735)) / 2, Y(734) + 0.2, (0, -1))
    # black frames on the shower screens
    for g in ("Master shower glass", "Toilet 2 shower glass"):
        o = bpy.data.objects.get(g)
        if not o:
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = Vector((min(p.x for p in bb), min(p.y for p in bb), 0))
        hi = Vector((max(p.x for p in bb), max(p.y for p in bb), 2.1))
        box(g + " frame top", (lo.x - 0.01, lo.y - 0.01, 2.08), (hi.x + 0.01, hi.y + 0.01, 2.11), M["black_metal"], F.C)
        horiz = (hi.x - lo.x) > (hi.y - lo.y)
        for end in (lo, hi):
            if horiz:
                box(g + " frame post", (end.x - 0.015, lo.y - 0.01, 0), (end.x + 0.015, hi.y + 0.01, 2.11), M["black_metal"], F.C)
            else:
                box(g + " frame post", (lo.x - 0.01, end.y - 0.015, 0), (hi.x + 0.01, end.y + 0.015, 2.11), M["black_metal"], F.C)


def apply():
    for fn in (lobby, living, dining, prayer, basin_area, kitchen, master, bed1, bed2, baths):
        before = set(bpy.data.objects)
        fn()
        # modelkit helpers drop objects into "Model": move everything new into this room's group
        for o in bpy.data.objects:
            if o not in before and F.C not in o.users_collection:
                for u in list(o.users_collection):
                    u.objects.unlink(o)
                F.C.objects.link(o)
