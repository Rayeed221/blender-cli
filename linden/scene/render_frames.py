"""Render selected frames: blender -b scene/linden_anim.blend -P scene/render_frames.py -- 1,30,60 W H SPP OUTDIR [--no-blur]"""
import os, sys, bpy
a = sys.argv[sys.argv.index("--") + 1:]
frames = [int(x) for x in a[0].split(",")] if a[0] != "all" else None
w, h, spp, outdir = int(a[1]), int(a[2]), int(a[3]), a[4]
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
sc.cycles.samples = spp
sc.cycles.use_denoising = True
sc.render.use_persistent_data = True
if "--no-blur" in a:
    sc.render.use_motion_blur = False
os.makedirs(outdir, exist_ok=True)
for fr in frames or range(sc.frame_start, sc.frame_end + 1):
    sc.frame_set(fr + 1)
    sc.frame_set(fr)  # force a real re-evaluation even when already on this frame
    sc.render.filepath = os.path.join(outdir, f"f{fr:04d}.png")
    if os.path.exists(sc.render.filepath) and "--skip-existing" in a:
        continue
    bpy.ops.render.render(write_still=True)
    print("FRAME", fr, flush=True)
