---
name: model-builder
description: Build any 3D model in this repo (props, furniture, mechanical parts, characters' blockouts, buildings, low-poly game assets) as a procedural models/<name>/build.py, then verify, preview, render and export it to glb/fbx/obj/stl/usd. Use when asked to make, model, create or design a 3D object or asset.
---

# Model builder

1. Make sure Blender is installed: `blender-cli doctor` → `headless_ok: true`. If not, `npm run setup:blender`.
2. Plan the model: real-world size in metres, its parts, which modelkit helper fits each part
   (see `models/README.md` cheatsheet), materials as hex colours.
3. `npm run model -- new <kebab-name>` and write `models/<name>/build.py`.
   Look at the examples in `models/*/build.py` for idioms.
4. `npm run model -- build <name>`. On failure read the Python trace in the output, fix, rebuild.
5. Read `build/<name>/preview.png` (front/right/top/persp) with the Read tool and compare it to the
   intent: proportions, parts in the right place, nothing floating or missing. Check
   `build/<name>/report.json` → `model_facts` (dimensions, triangles) and `verify_summary`.
   Iterate on build.py until it is right — expect 2–4 rounds for anything non-trivial.
6. Finish with `npm run model -- build <name> --render --formats glb,...` and show the user
   `render.png`. Commit only `models/<name>/build.py` (outputs in `build/` are git-ignored).
