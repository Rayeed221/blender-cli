"""Quick test renders: blender -b scene/linden.blend -P scene/test_render.py -- CAM_a,CAM_b [w h samples outdir]"""
import os
import sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
cams = argv[0].split(",")
w = int(argv[1]) if len(argv) > 1 else 270
h = int(argv[2]) if len(argv) > 2 else 480
spp = int(argv[3]) if len(argv) > 3 else 24
outdir = argv[4] if len(argv) > 4 else os.path.join(os.path.dirname(bpy.data.filepath), "..", "out", "tests")
os.makedirs(outdir, exist_ok=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = w, h
sc.render.resolution_percentage = 100
sc.cycles.samples = spp
sc.cycles.use_adaptive_sampling = True
sc.render.threads_mode = "AUTO"
sc.cycles.use_guiding = True
sc.cycles.use_surface_guiding = True
for c in cams:
    sc.camera = bpy.data.objects[c]
    sc.render.filepath = os.path.join(outdir, c.replace("CAM_", "") + ".png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc.render.filepath)
