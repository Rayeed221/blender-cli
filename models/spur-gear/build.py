# Spur gear, 24 teeth, 10 cm across, 2 cm thick, with a bore and keyway.
# Technique: parametric 2D outline -> extrude, boolean cuts, bevel.
import math, os, sys
sys.path.insert(0, os.environ["MODELKIT_PATH"])
import modelkit as mk

TEETH = 24
R_ROOT, R_TIP, THICK, BORE = 0.044, 0.05, 0.02, 0.012

mk.reset()
steel = mk.material("Steel", "#9aa3ad", roughness=0.35, metallic=1.0)

# trapezoidal teeth: root -> flank -> tip -> flank, counter-clockwise
pts = []
for i in range(TEETH):
    a0 = 2 * math.pi * i / TEETH
    step = 2 * math.pi / TEETH
    for frac, r in [(0.0, R_ROOT), (0.15, R_ROOT), (0.3, R_TIP), (0.55, R_TIP), (0.7, R_ROOT)]:
        a = a0 + frac * step
        pts.append((r * math.cos(a), r * math.sin(a)))

gear = mk.extrude_polygon("Gear", pts, depth=THICK, mat=steel)

bore = mk.cylinder("BoreCutter", radius=BORE, depth=THICK * 3, segments=48,
                   location=(0, 0, THICK / 2))
mk.boolean(gear, bore)
key = mk.cube("KeyCutter", size=(0.006, 0.008, THICK * 3), location=(0, BORE, THICK / 2))
mk.boolean(gear, key)
mk.bevel(gear, width=0.0008, segments=2)

mk.studio(view=(0.6, -1.0, 1.1))
mk.finalize()
result.update(mk.report())
