# Fennrow Homes • The Linden

A 3-bed apartment traced from `ref/floorplan.jpg`, built in Blender with Python, rendered in
Cycles at golden hour, and baked into a phone walkthrough.

## Open the walkthrough

The viewer is a static page (`viewer/`) that loads `linden.glb` with `fetch`, so it needs to be
served over HTTP; opening `index.html` straight from disk won't load the model.

```bash
cd linden/viewer && python3 -m http.server 8000
```

Then open `http://localhost:8000` on this computer, or `http://<this-computer's-LAN-IP>:8000` on a
phone on the same Wi-Fi. Everything (three.js, Draco decoder) is vendored, so it works offline.

Controls: joystick (bottom left) to walk, drag anywhere else to look, WASD/arrows on desktop.
Walls, furniture, railings and glass stop you; doors and the open half of sliding doors let you through.

## Layout

| Path | What |
|---|---|
| `plan.json` | The trace in metres: wall centre lines + thickness, openings (width, sill, height, door hinge/swing), rooms, columns, fins, railings, planters, and the scale fit against the printed dimensions. |
| `tools/trace.py` | Source of the trace (pixel coordinates read off the drawing) → `plan.json` + `out/trace_overlay.png`. |
| `tools/probe.py` | Measures wall bands in the drawing (used to read the coordinates). |
| `scene/build_scene.py` | Builds `scene/linden.blend` from `plan.json`: `arch.py` (shell with boolean-cut openings, floors, tray ceilings, roof, windows, doors, rails), `mats.py` (finishes), `furniture.py` (furnishing + lights). |
| `scene/animate.py` | 7 s fly-in rig → `scene/linden_anim.blend`. |
| `scene/bake_export.py` | Lightmap bake → `bake/*.png`, `viewer/linden.glb`, `viewer/colliders.json`. |
| `render_final.sh` | Full-quality stills, bake, animation frames, MP4 encode. |
| `out/` | Renders: `stills/`, `linden_flyin.mp4`, `trace_overlay.png`, test renders. |

## Rebuild

```bash
blender -b -P scene/build_scene.py                 # scene/linden.blend
blender -b scene/linden.blend -P scene/animate.py  # scene/linden_anim.blend
./render_final.sh stills
./render_final.sh bake
./render_final.sh anim 1 168 && ./render_final.sh encode
```

## Notes and assumptions

- **Scale:** 63.62 px/m, least-squares fit to 14 printed dimensions; 9 agree within ~1 cm, the others
  differ by 6–12 cm where the drawing itself is inconsistent with its labels (walls traced as drawn).
- **Heights** are not on the drawing: 3.0 m floor-to-ceiling, 0.15 m slab, 0.9 m parapet, doors 2.1 m,
  windows 0.9–2.1 m, toilet windows 1.5–2.1 m.
- **Orientation** is not on the drawing: plan-up is taken as north, and the golden-hour sun sits at
  bearing 305°, 9° up (a summer-evening sun for Dhaka), so it shines through the living-room window.
- **"Patio"** is the largest veranda (C. Bed 2, 6'-0"×4'-0"); its sliding doors are the "back doors"
  the fly-in glides through. The other two verandas are planted but not furnished.
- Finishes follow the design deck: cream/beige walls, white marble, walnut slatted doors, black
  slim frames, taupe + black-granite kitchen, beige channel-tufted sofa, warm 2700 K coves.
