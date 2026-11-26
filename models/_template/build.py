# __NAME__ — describe the model here: what it is, real-world size, style.
#
# Build:  npm run model -- __NAME__
# Runs headless inside Blender via `blender-cli run`. Everything put on the
# `result` dict comes back in build/__NAME__/report.json.
import os, sys
sys.path.insert(0, os.environ["MODELKIT_PATH"])
import modelkit as mk

mk.reset()
mk.seed(1)

# --- materials -------------------------------------------------------------
body = mk.material("Body", "#4a7bd0", roughness=0.4)
accent = mk.material("Accent", "#f0b429", roughness=0.3, metallic=0.6)

# --- geometry (metres, +Z up, sitting on z = 0) ----------------------------
base = mk.cube("Base", size=(1.0, 1.0, 0.2), location=(0, 0, 0.1), mat=body)
mk.bevel(base, width=0.03)
knob = mk.sphere("Knob", radius=0.2, location=(0, 0, 0.4), mat=accent)

# --- studio + report -------------------------------------------------------
mk.studio()
mk.finalize()
result.update(mk.report())
