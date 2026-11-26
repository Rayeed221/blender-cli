#!/usr/bin/env bash
# Full-quality outputs for The Linden. Each stage can be run on its own:
#   ./render_final.sh stills      5 furnished-room stills, 1080x1920, Cycles 128 spp
#   ./render_final.sh bake        lightmaps (64/128 spp) -> viewer/linden.glb
#   ./render_final.sh anim A B    fly-in frames A..B (1080x1920, 24 spp + path guiding)
#   ./render_final.sh encode      frames -> out/linden_flyin.mp4
set -euo pipefail
cd "$(dirname "$0")"
export LD_LIBRARY_PATH=/opt/blender-5.2.0-linux-x64/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
BLENDER=${BLENDER:-blender}

case "${1:-}" in
  stills)
    $BLENDER -b scene/linden.blend -P scene/test_render.py -- \
      CAM_living,CAM_kitchen,CAM_dining,CAM_patio,CAM_bed2 1080 1920 128 out/stills ;;
  bake)
    $BLENDER -b scene/linden.blend -P scene/bake_export.py -- --scale 1 --samples 64 ;;
  anim)
    frames=$(seq -s, "$2" "$3")
    $BLENDER -b scene/linden_anim.blend -P scene/render_frames.py -- "$frames" 1080 1920 24 out/frames --skip-existing ;;
  encode)
    ffmpeg -y -framerate 24 -i out/frames/f%04d.png -c:v libx264 -preset slow -crf 16 \
      -pix_fmt yuv420p -movflags +faststart out/linden_flyin.mp4 ;;
  *) sed -n '2,7p' "$0"; exit 2 ;;
esac
