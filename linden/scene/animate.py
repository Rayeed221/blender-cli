"""7-second fly-in rig: flat plan -> walls rise -> glide in through the back (patio) doors.

  blender -b scene/linden.blend -P scene/animate.py      -> scene/linden_anim.blend
"""
import json
import math
import os

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(bpy.data.filepath))
ROOT = os.path.dirname(HERE)
plan = json.load(open(os.path.join(ROOT, "plan.json")))
sc = bpy.context.scene
FPS = 24
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, 7 * FPS
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920


def f(t):
    return 1 + round(t * FPS)


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- the drawing on the floor
S = plan["scale"]["px_per_m"]
ox, oy = plan["scale"]["origin_px"]
img = bpy.data.images.load(os.path.join(ROOT, "ref", "floorplan.jpg"))
W, H = img.size
x0, x1 = (0 - ox) / S, (W - ox) / S
y0, y1 = (oy - H) / S, (oy - 0) / S
me = bpy.data.meshes.new("Plan drawing")
me.from_pydata([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], [], [(0, 1, 2, 3)])
uv = me.uv_layers.new()
for li, (u, v) in zip(range(4), [(0, 0), (1, 0), (1, 1), (0, 1)]):
    uv.data[li].uv = (u, v)
drawing = bpy.data.objects.new("Plan drawing", me)
sc.collection.objects.link(drawing)
drawing.location.z = 0.012
mat = bpy.data.materials.new("Plan drawing")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial")
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = img
em = nt.nodes.new("ShaderNodeEmission")
em.inputs["Strength"].default_value = 2.6
tr = nt.nodes.new("ShaderNodeBsdfTransparent")
mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(tex.outputs["Color"], em.inputs["Color"])
nt.links.new(em.outputs[0], mix.inputs[1])
nt.links.new(tr.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], out.inputs["Surface"])
me.materials.append(mat)
drawing.visible_shadow = False
# paper backing under the drawing so the top view reads as a sheet
fade = mix.inputs[0]
for t, v in ((0.0, 0.0), (1.1, 0.0), (2.3, 1.0)):
    fade.default_value = v
    fade.keyframe_insert("default_value", frame=f(t))
for t in (2.31,):
    drawing.hide_render = False
drawing.hide_render = True
drawing.keyframe_insert("hide_render", frame=f(2.4))
drawing.hide_render = False
drawing.keyframe_insert("hide_render", frame=1)


# ---------------------------------------------------------------- rise / lid rigs
def rig(name):
    e = bpy.data.objects.new(name, None)
    sc.collection.objects.link(e)
    return e


rise_arch = rig("RIG rise architecture")
rise_furn = rig("RIG rise furniture")
lid = rig("RIG lid")


def parent_all(objs, p):
    for o in objs:
        if o.parent is None and o.type != "CAMERA":
            mw = o.matrix_world.copy()
            o.parent = p
            o.matrix_parent_inverse = p.matrix_world.inverted()
            o.matrix_world = mw


A = bpy.data.collections["Architecture"]
arch_objs = [o for c in ("Walls",) for o in [bpy.data.objects["Walls"]]]
for cname in ("Windows", "Glass", "Doors", "Railings", "Planters"):
    arch_objs += list(bpy.data.collections[cname].all_objects)
parent_all(arch_objs, rise_arch)
lid_objs = list(bpy.data.collections["Ceilings"].all_objects) + list(bpy.data.collections["Roof"].all_objects)
furn = list(bpy.data.collections["Furniture"].all_objects)
ceiling_lights = [o for o in furn if o.type == "LIGHT" and o.location.z > 2.5]
parent_all(lid_objs + ceiling_lights, lid)
parent_all([o for o in furn if o not in ceiling_lights], rise_furn)

EPS = 0.002
for t, s in ((0.0, EPS), (1.0, EPS), (2.9, 1.0)):
    rise_arch.scale = (1, 1, s)
    rise_arch.keyframe_insert("scale", index=2, frame=f(t))
for t, s in ((0.0, EPS), (1.7, EPS), (3.3, 1.0)):
    rise_furn.scale = (1, 1, s)
    rise_furn.keyframe_insert("scale", index=2, frame=f(t))
for t, z in ((0.0, 40.0), (3.55, 40.0), (4.25, 0.0)):
    lid.location = (0, 0, z)
    lid.keyframe_insert("location", index=2, frame=f(t))

# ease curves (Blender 5 may store fcurves on layered actions; set via the generic helper)
def ease_all(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    fcs = []
    if hasattr(ad.action, "fcurves") and ad.action.fcurves:
        fcs = list(ad.action.fcurves)
    else:
        for layer in getattr(ad.action, "layers", []):
            for strip in layer.strips:
                for cb in strip.channelbags:
                    fcs += list(cb.fcurves)
    for fc in fcs:
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER"
            k.easing = "AUTO"
            k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"


for o in (rise_arch, rise_furn, lid):
    ease_all(o)

# ---------------------------------------------------------------- camera
cam_data = bpy.data.cameras.new("CAM_flyin")
cam_data.sensor_width = 36
cam_data.sensor_fit = "AUTO"
cam_data.clip_start = 0.05
cam_data.clip_end = 400
cam = bpy.data.objects.new("CAM_flyin", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam

cx, cy = (x0 + x1) / 2 + 0.3, (y0 + y1) / 2 + 0.3
# (time s, position, look-at, lens mm)
KEYS = [
    (0.0, (cx, cy, 32.0), (cx, cy, 0.0), 50),
    (1.0, (cx, cy, 30.5), (cx, cy, 0.0), 50),
    (2.5, (cx - 1.0, cy - 15.0, 25.0), (cx + 0.3, cy - 0.5, 0.8), 32),
    (3.7, (8.9, -7.2, 4.6), (7.9, 0.6, 1.3), 22),
    (4.7, (8.05, -2.35, 1.55), (8.05, 2.2, 1.3), 17),
    (5.5, (8.2, 0.15, 1.5), (7.6, 3.6, 1.25), 16),
    (7.0, (7.95, 2.95, 1.45), (5.8, 1.75, 1.0), 16),
]


def catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def sample(t):
    ts = [k[0] for k in KEYS]
    i = max(0, min(len(KEYS) - 2, max(j for j in range(len(KEYS)) if ts[j] <= t)))
    k0, k1 = KEYS[i], KEYS[i + 1]
    u = (t - k0[0]) / (k1[0] - k0[0])
    u = smooth(u) if i in (0, len(KEYS) - 2) else u  # ease out of the hold, ease into the end
    km = KEYS[max(0, i - 1)]
    kp = KEYS[min(len(KEYS) - 1, i + 2)]
    P = [Vector(k[1]) for k in (km, k0, k1, kp)]
    T = [Vector(k[2]) for k in (km, k0, k1, kp)]
    pos = catmull(*P, u)
    tgt = catmull(*T, u)
    lens = k0[3] + (k1[3] - k0[3]) * smooth(u)
    return pos, tgt, lens


def look(pos, tgt, t):
    fwd = (tgt - pos).normalized()
    # up hint: +Y while looking straight down (plan reads upright), world Z afterwards
    a = smooth((t - 1.0) / 1.6)
    hint = (Vector((0, 1, 0)) * (1 - a) + Vector((0, 0, 1)) * a).normalized()
    right = fwd.cross(hint)
    if right.length < 1e-4:
        right = Vector((1, 0, 0))
    right.normalize()
    up = right.cross(fwd)
    m = Matrix((right, up, -fwd)).transposed()
    return m.to_quaternion()


cam.rotation_mode = "QUATERNION"
prev = None
for fr in range(sc.frame_start, sc.frame_end + 1):
    t = (fr - 1) / FPS
    pos, tgt, lens = sample(t)
    q = look(pos, tgt, t)
    if prev is not None and prev.dot(q) < 0:
        q.negate()
    prev = q
    cam.location = pos
    cam.rotation_quaternion = q
    cam_data.lens = lens
    cam.keyframe_insert("location", frame=fr)
    cam.keyframe_insert("rotation_quaternion", frame=fr)
    cam_data.keyframe_insert("lens", frame=fr)

# motion blur for the glide
sc.render.use_motion_blur = False  # measured: costs ~20% for a barely visible 0.2 shutter
sc.render.motion_blur_shutter = 0.2
# path guiding: big win for rooms lit through door/window openings
sc.cycles.use_guiding = True
sc.cycles.use_surface_guiding = True
sc.cycles.use_volume_guiding = False
sc.cycles.sample_clamp_indirect = 4.0
sc.cycles.adaptive_threshold = 0.015
sc.cycles.max_bounces = 6
sc.cycles.diffuse_bounces = 3
sc.cycles.glossy_bounces = 2

out = os.path.join(HERE, "linden_anim.blend")
bpy.ops.wm.save_as_mainfile(filepath=out)
print("SAVED", out)
