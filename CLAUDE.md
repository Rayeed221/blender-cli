# CLAUDE.md

This repo is two things:

1. **`blender-cli`** — a zero-dependency Node CLI (`./blender-cli`, `foundation.js`) that drives
   Blender headless: JSON in, `bpy` runs, JSON out. Tests: `npm test -- --blender "$(command -v blender)"`.
2. **A 3D-model workspace** — `models/<name>/build.py` scripts built by `scripts/model.mjs`
   into `build/<name>/` (blend, preview, render, exports, report). See `models/README.md`.

## Setup (once per machine/container)

```bash
npm run setup:blender            # official Blender 5.2.0 LTS, checksum-verified, into /opt; links blender + blender-cli
blender-cli doctor -H            # expect headless_ok: true, support: "tested (5.2)"
```

Needs network access to `download.blender.org`. Other version: `bash scripts/install-blender.sh 4.3.2`.

## Building a model (the loop)

1. `npm run model -- new <name>` then write `models/<name>/build.py` with `modelkit` (`mk.*`).
   Real-world metres, +Z up, sitting on z = 0, meaningful object names.
2. `npm run model -- build <name>` — fails fast with the Python trace if the script errors.
3. **Look at `build/<name>/preview.png`** (Read the image) and check `report.json`
   (`model_facts.dimensions_m`, triangle count, `verify_summary`). Iterate until it looks right.
4. `--render` for a Cycles beauty shot (`render.png`), `--formats glb,fbx,obj,stl,usd` for deliverables.

Rules of thumb:
- Prefer modelkit helpers (`lathe`, `extrude_polygon`, `tube_along`, `boolean`, `bevel`, ...)
  and fall back to raw `bpy`/`bmesh` in the same file for anything else.
- Keep studio objects (camera/lights/floor) out of the "Model" collection — `mk.studio()` does
  this — so `export --selected` ships only the model.
- `verify` warnings for `overlap` between intentionally intersecting parts and `open_mesh`
  on open shapes (vase lip, floor) are expected; errors are not.
- Blender 5.x API: EEVEE engine id is `BLENDER_EEVEE`; `use_auto_smooth` is gone (use
  `mk.shade_smooth(obj, angle=30)`); check unfamiliar code with `blender-cli exec '<code>' --check`.
- No GPU here: render with Cycles on CPU (the pipeline does), keep samples modest (32–128).

## Don'ts

- Don't commit `build/` or `*.blend` (git-ignored).
- Don't change `blender-cli` behaviour without running the full test suite.
