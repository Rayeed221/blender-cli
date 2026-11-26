# Ceramic vase with a gold rim, ~32 cm tall.
# Technique: lathe (revolve a 2D profile), solidify for wall thickness, smooth shading.
import os, sys
sys.path.insert(0, os.environ["MODELKIT_PATH"])
import modelkit as mk

mk.reset()

glaze = mk.material("Glaze", "#2e6f8e", roughness=0.15)
gold = mk.material("Gold", "#d4a73a", roughness=0.25, metallic=1.0)

# (radius, z) from the foot up to the lip, in metres
profile = [(0.0, 0.0), (0.055, 0.0), (0.06, 0.01), (0.085, 0.06), (0.11, 0.13),
           (0.105, 0.19), (0.075, 0.25), (0.05, 0.29), (0.055, 0.31), (0.065, 0.32)]
vase = mk.lathe("Vase", profile, segments=64, mat=glaze)
mk.solidify(vase, thickness=0.006)
mk.subsurf(vase, levels=1)

rim = mk.torus("Rim", major_radius=0.062, minor_radius=0.004, location=(0, 0, 0.32), mat=gold)

mk.studio(view=(1.0, -1.3, 0.6))
mk.finalize()
result.update(mk.report())
