# models/

Each 3D model is a single Python file, `models/<name>/build.py`, that builds the model from
scratch with `bpy` + the shared [`modelkit`](./_lib/modelkit/__init__.py) helpers. The
pipeline in [`scripts/model.mjs`](../scripts/model.mjs) runs it headless with `blender-cli`
and writes everything to `build/<name>/` (git-ignored).

```bash
npm run model -- new office-chair                 # scaffold models/office-chair/build.py
npm run model -- build office-chair               # build + verify + preview + glb
npm run model -- build office-chair --render      # + Cycles beauty render
npm run model -- build office-chair --formats glb,fbx,obj,stl,usd
npm run models:build                              # rebuild every model
```

| Output | What |
|---|---|
| `build/<name>/<name>.blend` | The built scene (model + studio camera, lights, floor). Open it in Blender. |
| `build/<name>/preview.png` | 4-view workbench contact sheet (front, right, top, perspective). Look at it after every build. |
| `build/<name>/render.png` | Cycles render from the studio camera (`--render`). |
| `build/<name>/<name>.<fmt>` | Exports of the model only (studio excluded), read back for fidelity. |
| `build/<name>/report.json` | Vertex/triangle counts, dimensions, materials, lint findings, and every step's JSON. |

## Writing a build.py

```python
import os, sys
sys.path.insert(0, os.environ["MODELKIT_PATH"])
import modelkit as mk

mk.reset()                      # empty scene; everything goes in the "Model" collection
mk.seed(1)                      # reproducible randomness
wood = mk.material("Wood", "#8b5a2b", roughness=0.7)
top = mk.cube("Top", size=(1.2, 0.7, 0.04), location=(0, 0, 0.74), mat=wood)
mk.bevel(top, width=0.005)
for x in (-0.55, 0.55):
    for y in (-0.3, 0.3):
        mk.cylinder("Leg", radius=0.025, depth=0.72, location=(x, y, 0.36), mat=wood)
mk.studio()                     # camera framed to the model, 3 area lights, floor
mk.finalize()                   # UV unwrap, select model for export, render defaults
result.update(mk.report())      # facts returned as JSON
```

Conventions: metres, +Z up, model on the ground (`z = 0`) and centred in X/Y, real-world
scale, hex sRGB colours. Name objects meaningfully — names survive into exports.

## modelkit cheatsheet

| Need | Helper |
|---|---|
| Boxes, cylinders, cones, spheres, tori, planes | `cube` `cylinder` (`radius_top=` for tapers) `cone` `sphere` `icosphere` `torus` `plane` |
| Anything rotationally symmetric (vase, bottle, lamp, wheel, chess piece) | `lathe(name, [(radius, z), ...])` |
| Flat outlines with thickness (gear, logo, bracket, sign, floor plan) | `extrude_polygon(name, [(x, y), ...], depth)` |
| Pipes, cables, handles, wire frames | `tube_along(name, [(x, y, z), ...], radius)` |
| 3D text | `text(name, "Hello", size, depth)` |
| Arbitrary mesh | `mesh_from_data(name, verts, faces)` (or raw `bmesh`) |
| Holes, cut-outs, merges | `boolean(obj, cutter, "DIFFERENCE"\|"UNION"\|"INTERSECT")` |
| Rounded edges / smoothness / thickness | `bevel` `subsurf` `solidify` `shade_smooth(obj, angle)` `shade_flat` |
| Symmetry / repetition | `mirror(obj, "X")` `array(obj, count, offset)` |
| Organic lumpiness (rocks, terrain, foliage) | `displace_noise(obj, strength, scale)` |
| Materials | `material(name, "#hex", roughness, metallic, alpha, emission, transmission)` `assign` |
| Structure | `parent` `join` `apply_modifiers` `apply_transforms` `origin_to_bottom` `drop_to_floor` |
| Inspect | `bounds()` `report()` |

Anything modelkit doesn't cover: write plain `bpy` / `bmesh` / geometry nodes in the same
file. Discover node names with `blender-cli nodes find --kind geometry --search <term>`.

## Examples

| Model | Technique |
|---|---|
| [`low-poly-tree`](./low-poly-tree/build.py) | primitives, noise displacement, flat shading, parenting |
| [`ceramic-vase`](./ceramic-vase/build.py) | lathe profile, solidify, subdivision, metal trim |
| [`spur-gear`](./spur-gear/build.py) | parametric outline, extrusion, boolean bore + keyway, bevel |

## Other ways to get geometry

- `blender-cli import model.glb|fbx|obj|stl|usd ...` — bring in existing assets.
- `blender-cli import polyhaven:<id>` — CC0 models, textures, HDRIs (needs `polyhaven.com`/`dl.polyhaven.org` network access).
- `blender-cli generate "a red armchair" --out chair.glb` — text/image-to-3D via Meshy (`MESHY_API_KEY`).
