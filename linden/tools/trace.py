"""Trace of ref/floorplan.jpg -> plan.json (metres) + orange overlay for checking.

All geometry is entered in drawing pixels (x right, y down), read off the wall/glazing
masks with tools/probe.py. The pixel->metre scale is fitted by least squares to the room
dimensions printed on the sheet (clear inside-face distances).

Plan frame: +X east, +Y north, origin at the outer south-west corner of the master wing.
"""
import json, math, os, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def ft(f, i=0):
    return (f * 12 + i) * 0.0254

# ---------------------------------------------------------------- scale fit
# (label, printed metres, measured clear pixels, how measured)
DIMS = [
    ("C. Bed 1 E-W 11'-8\"",   ft(11, 8),  276 - 49,  "x 49..276"),
    ("C. Bed 1 N-S 15'-10\"",  ft(15, 10), 327 - 14,  "y 14..327"),
    ("Kitchen E-W 14'-7\"",    ft(14, 7),  324 - 42,  "x 42..324"),
    ("Kitchen N-S 7'-11\"",    ft(7, 11),  488 - 340, "y 340..488"),
    ("Master E-W 13'-4\"",     ft(13, 4),  308 - 49,  "x 49..308"),
    ("Master N-S 12'-1\"",     ft(12, 1),  833 - 598, "y 598..833"),
    ("C. Bed 2 N-S 13'-4\"",   ft(13, 4),  842 - 583, "y 583..842"),
    ("C. Bed 2 E-W 12'-1\"",   ft(12, 1),  629 - 402, "x 402..629"),
    ("Living E-W 12'-1\"",     ft(12, 1),  612 - 378, "x 378..612"),
    ("Dining E-W 14'-2\"",     ft(14, 2),  612 - 337, "x 337..612"),
    ("Toilet 1 E-W 4'-2\"",    ft(4, 2),   365 - 288, "x 288..365"),
    ("Toilet 1 N-S 6'-8\"",    ft(6, 8),   143 - 14,  "y 14..143"),
    ("C.Bed2 Ver 6'-0\"",      ft(6, 0),   601 - 478, "x 478..601"),
    ("Master Ver 5'-10\"",     ft(5, 10),  268 - 155, "x 155..268"),
]
S = sum(px * m for _, m, px, _ in DIMS) / sum(m * m for _, m, px, _ in DIMS)  # px per metre
X0, Y0 = 37, 852  # outer SW corner (px)

def P(x, y):
    return [round((x - X0) / S, 4), round((Y0 - y) / S, 4)]

# ---------------------------------------------------------------- heights (m)
WALL_H = 3.0
DOOR_H = 2.1
TYPES = {
    "window":       dict(sill=0.9, head=2.1),
    "high_window":  dict(sill=1.5, head=2.1),   # toilets
    "sliding_door": dict(sill=0.0, head=2.1),   # glazed doors to verandas
    "door":         dict(sill=0.0, head=DOOR_H),
    "entry_door":   dict(sill=0.0, head=2.2),
    "opening":      dict(sill=0.0, head=2.2),   # doorless archway
}

# ---------------------------------------------------------------- walls (px centre lines)
EXT, INT, THIN = 13, 12, 9
W = []          # (id, x0, y0, x1, y1, thickness_px, exterior)
def wall(i, a, b, t=INT, ext=False):
    W.append((i, a[0], a[1], b[0], b[1], t, ext))

# north edge
wall("N1_bed1_top",      (37, 8),    (302, 8),    10, True)
wall("N2_toilet_top",    (302, 8),   (378, 8),    10, True)
wall("N3_living_top",    (365, 82),  (632, 82),   EXT, True)
# C. Bed 1 / toilet / living west
wall("V1_bed1_west",     (43, 8),    (43, 229),   EXT, True)
wall("H1_bed1_ver",      (37, 222),  (126, 222),  EXT, True)
wall("V2_ver1_east",     (120, 222), (120, 333),  INT, True)
wall("V3_bed1_east",     (282, 8),   (282, 333),  EXT)
wall("H2_toilet_basin",  (282, 149), (365, 149),  INT)
wall("H3_basin_south",   (282, 252), (365, 252),  EXT)
wall("V4_tv_wall",       (371.5, 8), (371.5, 258), EXT)
# living east / entry / prayer
wall("V5_living_east",   (622, 76),  (622, 410),  20, True)
wall("H4_prayer_top",    (632, 370), (788, 370),  9, True)
wall("V6_prayer_east",   (784.5, 366), (784.5, 583), 10, True)
# kitchen
wall("H5_kitchen_top",   (37, 333),  (337, 333),  EXT)
wall("V7_kitchen_west",  (37, 327),  (37, 498),   EXT, True)
wall("V8_kitchen_east",  (331, 333), (331, 500),  EXT)
wall("H6_kitchen_south", (37, 494.5), (337, 494.5), EXT)
# master toilet / utility
wall("V9_mtoilet_west",  (121, 494), (121, 592),  EXT)
wall("H7_master_top",    (37, 592),  (318, 592),  INT)
wall("V10_master_east",  (312, 494), (312, 846),  EXT, True)
# master bed
wall("V11_master_west",  (43, 586),  (43, 846),   EXT, True)
wall("H8_master_south",  (37, 840),  (318, 840),  EXT, True)
# hall south / C. Bed 2
wall("H9_hall_south",    (390, 578.5), (788, 578.5), 10)
wall("V12_bed2_west",    (395.5, 573), (395.5, 851), 11, True)
wall("H10_bed2_south",   (390, 846), (641, 846),  EXT, True)
wall("V13_bed2_east",    (635, 573), (635, 851),  EXT, True)
wall("V14_toilet2_east", (741.5, 573), (741.5, 748), EXT, True)
wall("H11_toilet2_south",(629, 741), (748, 741),  EXT, True)

# ---------------------------------------------------------------- columns (px rects)
COLS = [(38, 2, 80, 25), (243, 2, 298, 25), (612, 76, 632, 268), (30, 321, 136, 347),
        (268, 321, 337, 345), (28, 425, 41, 490), (612, 340, 645, 410), (36, 783, 60, 852),
        (298, 783, 320, 852), (613, 800, 641, 852)]

# ---------------------------------------------------------------- openings (wall, a, b along wall, type, name)
O = [
    ("N1_bed1_top", 117, 207, "window", "C. Bed 1 north window"),
    ("N2_toilet_top", 305, 340, "high_window", "Toilet 1 window"),
    ("V1_bed1_west", 80, 172, "window", "C. Bed 1 west window"),
    ("H1_bed1_ver", 50, 116, "sliding_door", "C. Bed 1 veranda door"),
    ("V3_bed1_east", 262, 320, "door", "C. Bed 1 door"),
    ("H2_toilet_basin", 322, 363, "door", "Toilet 1 door"),
    ("H3_basin_south", 322, 365, "opening", "Basin area arch"),
    ("N3_living_top", 422, 569, "window", "Living window"),
    ("V5_living_east", 270, 340, "entry_door", "Entry door"),
    ("V6_prayer_east", 479, 572, "window", "Prayer window"),
    ("V8_kitchen_east", 446, 488, "door", "Kitchen door"),
    ("H6_kitchen_south", 44, 114, "sliding_door", "Kitchen utility door"),
    ("V9_mtoilet_west", 525, 557, "high_window", "Master toilet window"),
    ("H7_master_top", 188, 230, "door", "Master toilet door"),
    ("V10_master_east", 600, 658, "door", "Master door"),
    ("V11_master_west", 668, 767, "window", "Master west window"),
    ("H8_master_south", 130, 258, "sliding_door", "Master veranda door"),
    ("V12_bed2_west", 585, 643, "door", "C. Bed 2 door"),
    ("V12_bed2_west", 852, 852, None, None),  # placeholder removed below
    ("H10_bed2_south", 475, 588, "sliding_door", "C. Bed 2 veranda door (back doors)"),
    ("V13_bed2_east", 642, 684, "door", "Toilet 2 door"),
    ("V13_bed2_east", 765, 797, "window", "C. Bed 2 east window"),
    ("V14_toilet2_east", 600, 627, "high_window", "Toilet 2 window"),
]
O = [o for o in O if o[3]]

# door leaves, read from the swing arcs: hinge end (px y or x along the wall) and the
# plan direction the open leaf points (+x east, +y north)
SWING = {
    "Entry door": (340, (-1, 0)),
    "C. Bed 1 door": (262, (-1, 0)),
    "Toilet 1 door": (363, (0, 1)),
    "Kitchen door": (488, (-1, 0)),
    "Master toilet door": (188, (0, 1)),
    "Master door": (658, (-1, 0)),
    "C. Bed 2 door": (643, (1, 0)),
    "Toilet 2 door": (642, (1, 0)),
}

# hall south window sits in the gap between master and bed2 wings: model as a short wall
wall("H12_hall_window",  (318, 666), (390, 666), 10, True)
O.append(("H12_hall_window", 322, 389, "window", "Hall south window"))

# glass partitions (px centre lines)
GLASS = [("Prayer screen", (636, 410), (636, 573), 1.0, 2.4),
         ("Master shower glass", (237, 501), (237, 587), 0.0, 2.1),
         ("Toilet 2 shower glass", (641, 688), (736, 688), 0.0, 2.1)]

# ---------------------------------------------------------------- rooms (px polygons, inside faces)
R = [
    ("C. Bed 1", "bedroom", [(49, 14), (276, 14), (276, 327), (126, 327), (126, 228), (49, 228)]),
    ("Toilet 1", "bath", [(288, 14), (365, 14), (365, 143), (288, 143)]),
    ("Basin Area", "bath", [(288, 155), (365, 155), (365, 246), (288, 246)]),
    ("Living", "living", [(378, 88), (616, 88), (616, 340), (378, 340)]),
    ("Lobby", "living", [(288, 258), (378, 258), (378, 340), (337, 340), (337, 327), (288, 327)]),
    ("Dining", "dining", [(337, 340), (616, 340), (616, 410), (632, 410), (632, 573), (337, 573)]),
    ("Corridor", "dining", [(318, 573), (390, 573), (390, 661), (318, 661)]),
    ("Prayer Space", "prayer", [(640, 375), (779, 375), (779, 573), (640, 573)]),
    ("Kitchen", "kitchen", [(43, 340), (324, 340), (324, 488), (43, 488)]),
    ("Utility", "outdoor", [(40, 501), (115, 501), (115, 586), (40, 586)]),
    ("Master Toilet", "bath", [(128, 501), (305, 501), (305, 586), (128, 586)]),
    ("Master Bed", "bedroom", [(49, 598), (305, 598), (305, 833), (49, 833)]),
    ("C. Bed 2", "bedroom", [(402, 584), (628, 584), (628, 839), (402, 839)]),
    ("Toilet 2", "bath", [(642, 584), (735, 584), (735, 734), (642, 734)]),
    ("C. Bed 1 Veranda", "patio", [(40, 229), (114, 229), (114, 321), (40, 321)]),
    ("Master Veranda", "patio", [(155, 847), (268, 847), (268, 917), (155, 917)]),
    ("Patio (C. Bed 2 Veranda)", "patio", [(478, 853), (601, 853), (601, 929), (478, 929)]),
]
# full-height wall fins / returns drawn outside the main walls (px rects)
FINS = [(12, 3, 38, 14), (12, 323, 38, 345), (37, 852, 60, 880), (298, 852, 320, 880), (641, 842, 690, 853)]
# 1.0 m balustrades on verandas and the utility balcony (px polylines)
RAILS = [("Utility rail", [(37, 498), (37, 588)]),
         ("C. Bed 1 veranda rail", [(37, 229), (37, 322)]),
         ("Master veranda rail", [(155, 846), (155, 917), (268, 917), (268, 846)]),
         ("Patio rail", [(478, 853), (478, 929), (601, 929), (601, 853)])]
PLANTERS = [(60, 846, 152, 890), (396, 853, 478, 929), (641, 748, 690, 846), (742, 578, 786, 612)]

# ---------------------------------------------------------------- build plan.json
def wall_len(w):
    return math.hypot(w[3] - w[1], w[4] - w[2])

def build():
    walls = []
    wmap = {w[0]: w for w in W}
    for i, x0, y0, x1, y1, t, ext in W:
        walls.append({"id": i, "a": P(x0, y0), "b": P(x1, y1), "thickness": round(t / S, 3),
                      "height": WALL_H, "exterior": ext})
    openings = []
    for wid, a, b, typ, name in O:
        w = wmap[wid]
        horiz = abs(w[4] - w[2]) < abs(w[3] - w[1])
        if horiz:
            pa, pb = P(a, w[2]), P(b, w[2])
            s0 = (min(a, b) - min(w[1], w[3])) / S
        else:
            pa, pb = P(w[1], a), P(w[1], b)
            s0 = (min(a, b) - min(w[2], w[4])) / S
        # offset measured from the wall's start point "a"
        start_px = (w[1], w[2])
        d_a = math.hypot(pa[0] - P(*start_px)[0], pa[1] - P(*start_px)[1])
        d_b = math.hypot(pb[0] - P(*start_px)[0], pb[1] - P(*start_px)[1])
        h = TYPES[typ]
        extra = {}
        if name in SWING:
            hp, sw = SWING[name]
            extra = {"hinge": P(hp, w[2]) if horiz else P(w[1], hp), "swing": list(sw)}
        openings.append({**extra, "wall": wid, "type": typ, "name": name,
                         "a": pa, "b": pb,
                         "offset": round(min(d_a, d_b), 3), "width": round(abs(d_b - d_a), 3),
                         "sill": h["sill"], "height": round(h["head"] - h["sill"], 3)})
    plan = {
        "name": "Fennrow Homes - The Linden",
        "units": "metres",
        "frame": "+X east, +Y north, origin at outer SW corner; heights from finished floor",
        "source": "ref/floorplan.jpg",
        "scale": {"px_per_m": round(S, 3), "origin_px": [X0, Y0],
                  "fit": [{"dim": l, "printed_m": round(m, 3), "traced_m": round(px / S, 3),
                           "error_cm": round((px / S - m) * 100, 1)} for l, m, px, _ in DIMS]},
        "storey": {"floor_to_ceiling": WALL_H, "slab": 0.15},
        "walls": walls,
        "openings": openings,
        "glass_partitions": [{"name": n, "a": P(*a), "b": P(*b), "sill": s, "height": h} for n, a, b, s, h in GLASS],
        "columns": [{"min": P(x0, y1), "max": P(x1, y0)} for x0, y0, x1, y1 in COLS],
        "rooms": [{"name": n, "use": u, "polygon": [P(x, y) for x, y in poly],
                   "area_m2": round(abs(sum(P(*poly[i])[0] * P(*poly[i - 1])[1] - P(*poly[i - 1])[0] * P(*poly[i])[1]
                                             for i in range(len(poly)))) / 2, 2)} for n, u, poly in R],
        "fins": [{"min": P(x0, y1), "max": P(x1, y0)} for x0, y0, x1, y1 in FINS],
        "railings": [{"name": n, "points": [P(*q) for q in pts], "height": 1.0} for n, pts in RAILS],
        "planters": [{"min": P(x0, y1), "max": P(x1, y0)} for x0, y0, x1, y1 in PLANTERS],
    }
    return plan

def overlay(plan, out, scale=2):
    im = Image.open(os.path.join(ROOT, "ref/floorplan.jpg")).convert("RGB")
    im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
    im = Image.blend(im, Image.new("RGB", im.size, "white"), 0.35)
    d = ImageDraw.Draw(im, "RGBA")
    def px(p):
        return ((p[0] * S + X0) * scale, (Y0 - p[1] * S) * scale)
    for r in plan["rooms"]:
        d.polygon([px(p) for p in r["polygon"]], fill=(255, 140, 0, 28), outline=(255, 140, 0, 160))
    for c in plan["columns"]:
        a, b = px(c["min"]), px(c["max"])
        d.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], outline=(200, 60, 0, 255), width=2)
    for w in plan["walls"]:
        a, b = px(w["a"]), px(w["b"])
        t = w["thickness"] * S * scale
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy); nx, ny = -dy / L * t / 2, dx / L * t / 2
        d.polygon([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)],
                  fill=(255, 120, 0, 110), outline=(255, 100, 0, 255))
        d.line([a, b], fill=(255, 100, 0, 255), width=1)
    for c in plan["fins"]:
        a, b = px(c["min"]), px(c["max"])
        d.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], fill=(255, 120, 0, 110), outline=(255, 100, 0, 255))
    for c in plan["planters"]:
        a, b = px(c["min"]), px(c["max"])
        d.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], outline=(255, 140, 0, 255), width=2)
    for r in plan["railings"]:
        d.line([px(q) for q in r["points"]], fill=(255, 140, 0, 255), width=3)
    for o in plan["openings"]:
        a, b = px(o["a"]), px(o["b"])
        col = {"window": (0, 120, 255), "high_window": (0, 200, 255), "sliding_door": (0, 170, 90)}.get(o["type"], (200, 0, 160))
        d.line([a, b], fill=col + (255,), width=6)
    for g in plan["glass_partitions"]:
        d.line([px(g["a"]), px(g["b"])], fill=(0, 200, 255, 255), width=3)
    for r in plan["rooms"]:
        xs = [px(p)[0] for p in r["polygon"]]; ys = [px(p)[1] for p in r["polygon"]]
        d.text((sum(xs) / len(xs) - 20, sum(ys) / len(ys) + 18), f'{r["name"]}\n{r["area_m2"]} m2', fill=(160, 60, 0, 255))
    im.save(out)

if __name__ == "__main__":
    plan = build()
    with open(os.path.join(ROOT, "plan.json"), "w") as f:
        json.dump(plan, f, indent=1)
    overlay(plan, sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out/trace_overlay.png"))
    print(f"scale {S:.2f} px/m; walls {len(plan['walls'])}, openings {len(plan['openings'])}, rooms {len(plan['rooms'])}")
    for f_ in plan["scale"]["fit"]:
        print(f"  {f_['dim']:<24} printed {f_['printed_m']:.3f}  traced {f_['traced_m']:.3f}  {f_['error_cm']:+.1f} cm")
