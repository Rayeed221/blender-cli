"""Swap a glb's embedded images for bake/<name>.png (re-encoded as JPEG) without re-exporting.

  python3 tools/glb_retexture.py viewer/linden.glb [quality]
"""
import io
import json
import os
import struct
import sys

from PIL import Image

path = sys.argv[1]
quality = int(sys.argv[2]) if len(sys.argv) > 2 else 92
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = open(path, "rb").read()
jlen = struct.unpack("<I", data[12:16])[0]
gltf = json.loads(data[20:20 + jlen])
bin_off = 20 + jlen + 8
blen = struct.unpack("<I", data[20 + jlen:24 + jlen])[0]
binary = data[bin_off:bin_off + blen]

replace = {}
for img in gltf["images"]:
    src = os.path.join(root, "bake", img["name"] + ".png")
    if os.path.exists(src):
        buf = io.BytesIO()
        Image.open(src).convert("RGB").save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        replace[img["bufferView"]] = buf.getvalue()

out = bytearray()
for i, bv in enumerate(gltf["bufferViews"]):
    chunk = replace.get(i, binary[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]])
    while len(out) % 4:
        out.append(0)
    bv["byteOffset"] = len(out)
    bv["byteLength"] = len(chunk)
    out += chunk
while len(out) % 4:
    out.append(0)
gltf["buffers"][0]["byteLength"] = len(out)
js = json.dumps(gltf, separators=(",", ":")).encode()
js += b" " * ((4 - len(js) % 4) % 4)
total = 12 + 8 + len(js) + 8 + len(out)
with open(path, "wb") as f:
    f.write(struct.pack("<4sII", b"glTF", 2, total))
    f.write(struct.pack("<I4s", len(js), b"JSON") + js)
    f.write(struct.pack("<I4s", len(out), b"BIN\x00") + bytes(out))
print(f"retextured {len(replace)} images -> {path} ({total / 1e6:.1f} MB)")
