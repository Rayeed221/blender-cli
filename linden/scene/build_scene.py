"""Build The Linden in Blender from plan.json.

  blender -b -P scene/build_scene.py -- [--no-furniture] [--out scene/linden.blend]
"""
import json
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import mats  # noqa: E402
import arch  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(HERE, "linden.blend")
FURNISH = "--no-furniture" not in argv

# golden hour: low sun from the west-north-west (plan +Y is north)
SUN_ELEV = 9.0     # degrees above horizon
SUN_AZ = 305.0
SKY_STRENGTH = 0.3     # compass bearing the sun shines FROM (0 = north, 90 = east)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    return sc


def setup_render(sc):
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = 128
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.use_denoising = True
    cy.max_bounces = 8
    cy.diffuse_bounces = 4
    cy.glossy_bounces = 3
    cy.transmission_bounces = 6
    cy.transparent_max_bounces = 12
    cy.sample_clamp_indirect = 8.0
    cy.blur_glossy = 1.0
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast" if "AgX - Medium High Contrast" in \
        [i.identifier for i in sc.view_settings.bl_rna.properties["look"].enum_items_static] else "None"
    sc.view_settings.exposure = 0.0
    sc.render.fps = 24


def sun_vector():
    az, el = math.radians(SUN_AZ), math.radians(SUN_ELEV)
    # direction TOWARD the sun in plan coords (+X east, +Y north)
    return Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))


def setup_light(sc):
    w = bpy.data.worlds.new("Golden hour")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = True
    sky.sun_size = math.radians(0.8)
    sky.sun_intensity = 1.0
    sky.sun_elevation = math.radians(SUN_ELEV)
    # sky sun_rotation is a compass bearing: 0 = +Y (north), 90 deg = +X (east); measured
    sky.sun_rotation = math.radians(SUN_AZ)
    sky.altitude = 20
    sky.air_density = 1.2
    sky.aerosol_density = 2.5
    bg.inputs["Strength"].default_value = SKY_STRENGTH
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])

    sun = bpy.data.lights.new("Sun", "SUN")   # reference only: the sky's sun disc lights the scene
    sun.energy = 0.0
    sun.angle = math.radians(0.6)
    sun.color = (1.0, 0.66, 0.40)
    o = bpy.data.objects.new("Sun", sun)
    sc.collection.objects.link(o)
    d = sun_vector()
    o.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    o.location = Vector((6, 6, 10)) + d * 5

    # ground around the building
    g = arch.box("Ground", (-40, -40, -0.30), (50, 50, -0.16), mats.tiles("Ground paving", "#a8a296", "#8a8478", 0.8, 0.9))
    return o


def add_camera(name, loc, target, lens=18, c=None):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = 36
    cam.clip_start = 0.05
    cam.clip_end = 300
    o = bpy.data.objects.new(name, cam)
    (c or bpy.context.scene.collection).objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def cameras(plan):
    c = arch.coll("Cameras")
    # centre of the plan
    xs = [p[0] for r in plan["rooms"] for p in r["polygon"]]
    ys = [p[1] for r in plan["rooms"] for p in r["polygon"]]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    top = add_camera("CAM_plan_top", (cx, cy, 34), (cx, cy, 0), lens=50, c=c)
    top.data.type = "ORTHO"
    top.data.ortho_scale = 19.5
    add_camera("CAM_aerial", (cx - 9, cy - 13, 15), (cx, cy, 1), lens=24, c=c)
    # rooms (eye height 1.5 m), portrait framing
    add_camera("CAM_living", (5.9, 7.45, 1.45), (8.2, 11.2, 1.1), lens=16, c=c)
    add_camera("CAM_kitchen", (4.05, 6.05, 1.6), (0.4, 7.6, 1.05), lens=15, c=c)
    add_camera("CAM_patio", (9.7, -2.5, 2.0), (7.6, -0.45, 0.65), lens=20, c=c)
    add_camera("CAM_bed2", (8.4, 0.5, 1.5), (5.9, 2.6, 1.0), lens=15, c=c)
    add_camera("CAM_master", (3.35, 3.85, 1.6), (0.9, 0.9, 1.0), lens=15, c=c)
    add_camera("CAM_bed1", (3.2, 9.7, 1.6), (0.8, 12.6, 0.9), lens=15, c=c)
    add_camera("CAM_prayer", (9.75, 4.75, 1.5), (11.3, 7.2, 0.9), lens=15, c=c)
    add_camera("CAM_basin", (4.95, 9.15, 1.55), (3.95, 10.3, 1.3), lens=16, c=c)
    add_camera("CAM_mbath", (4.05, 4.35, 1.6), (1.6, 5.35, 1.0), lens=14, c=c)
    add_camera("CAM_lobby", (7.4, 6.0, 1.5), (9.0, 7.45, 1.15), lens=18, c=c)
    add_camera("CAM_dining", (8.7, 5.6, 1.55), (6.0, 7.4, 1.0), lens=16, c=c)


def main():
    sc = reset()
    plan = json.load(open(os.path.join(ROOT, "plan.json")))
    setup_render(sc)
    mats.make()
    root = arch.coll("Architecture")
    shell = arch.build_shell(plan, root)
    arch.classify_shell_faces(shell, plan)
    arch.build_floors(plan, root)
    arch.build_roof(plan, root)
    arch.build_windows(plan, root)
    arch.build_doors(plan, root)
    arch.build_rails_planters(plan, root)
    setup_light(sc)
    if FURNISH:
        import furniture
        furniture.furnish(plan)
    cameras(plan)
    sc.camera = bpy.data.objects["CAM_living"]
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("SAVED", OUT, len(bpy.data.objects), "objects")


main()
