"""Denoise baked atlas PNGs in place with OIDN (Blender compositor).
   blender -b -P tools/denoise_png.py -- bake/living.png [more.png ...]
Originals are kept in bake/raw/."""
import os, shutil, sys
import bpy
paths = sys.argv[sys.argv.index("--") + 1:]
sc = bpy.context.scene
sc.render.engine = "CYCLES"
for o in list(sc.objects):
    bpy.data.objects.remove(o)
tree = bpy.data.node_groups.new("dn", "CompositorNodeTree")
sc.compositing_node_group = tree
img_node = tree.nodes.new("CompositorNodeImage")
dn = tree.nodes.new("CompositorNodeDenoise")
for k, v in (("prefilter", "ACCURATE"), ("quality", "HIGH")):
    try: setattr(dn, k, v)
    except Exception: pass
out = tree.nodes.new("NodeGroupOutput")
tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
tree.links.new(img_node.outputs[0], dn.inputs[0])
tree.links.new(dn.outputs[0], out.inputs[0])
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
s = sc.render.image_settings
s.file_format = "PNG"; s.color_mode = "RGB"; s.color_depth = "8"
for p in paths:
    p = os.path.abspath(p)
    raw = os.path.join(os.path.dirname(p), "raw", os.path.basename(p))
    if not os.path.exists(raw):
        shutil.copy(p, raw)
    img = bpy.data.images.load(raw)
    img_node.image = img
    sc.render.resolution_x, sc.render.resolution_y = img.size
    sc.render.resolution_percentage = 100
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    print("DENOISED", p, flush=True)
