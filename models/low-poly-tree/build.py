# Low-poly tree: tapered trunk, three stacked lumpy foliage blobs. ~2.4 m tall.
# Technique: primitives, noise displacement, flat shading, parenting.
import os, sys
sys.path.insert(0, os.environ["MODELKIT_PATH"])
import modelkit as mk

mk.reset()
mk.seed(7)

bark = mk.material("Bark", "#6b4423", roughness=0.9)
leaf = mk.material("Leaves", "#4f9a3a", roughness=0.7)

trunk = mk.cylinder("Trunk", radius=0.12, radius_top=0.08, depth=1.2, segments=8,
                    location=(0, 0, 0.6), mat=bark, smooth=False)

blobs = []
for i, (z, r) in enumerate([(1.35, 0.6), (1.8, 0.45), (2.15, 0.28)]):
    b = mk.icosphere(f"Foliage_{i}", radius=r, subdivisions=2, location=(0, 0, z), mat=leaf)
    b.scale.z = 0.85
    mk.apply_transforms(b)  # bake the squash so normals and export stay clean
    mk.displace_noise(b, strength=r * 0.35, scale=r * 0.8)
    mk.apply_modifiers(b)
    mk.shade_flat(b)
    mk.parent(b, trunk)
    blobs.append(b)

mk.studio(view=(1.0, -1.2, 0.45))
mk.finalize()
result.update(mk.report())
