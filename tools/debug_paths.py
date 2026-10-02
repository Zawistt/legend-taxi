#!/usr/bin/env python3
"""Debug render: hillshaded terrain + roads + blockers -> PNG (usage: debug_paths.py out.png)"""
import json, os, sys
import numpy as np
from scipy.ndimage import sobel
from PIL import Image, ImageDraw
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "godot", "terrain_data")
m = json.load(open(f"{D}/terrain_meta.json")); P = json.load(open(f"{D}/paths.json")); B = json.load(open(f"{D}/blockers.json"))
G, C, SZ = m["grid"], m["cell_m"], m["size_m"]
h = np.fromfile(f"{D}/heightmap.bin", "<f4").reshape(G, G)
gx = sobel(h, axis=1) / (8 * C); gz = sobel(h, axis=0) / (8 * C)
sh = np.clip(0.62 + (-gx * 0.6 - gz * 0.5) * 1.6, 0, 1); t = np.clip(h / 16, 0, 1)
col = np.stack([0.30 + 0.5 * t, 0.46 + 0.32 * t, 0.22 + 0.4 * t], -1) * sh[..., None]
W = 1370
img = Image.fromarray((col * 255).astype(np.uint8)).resize((W, W), Image.BICUBIC).convert("RGBA")
ov = Image.new("RGBA", (W, W), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
S = W / SZ
px = lambda x, z: ((x + SZ / 2) * S, (z + SZ / 2) * S)
for b in B["blockers"]:
    d.polygon([px(*p) for p in b["polygon"]], fill=(20, 90, 30, 190) if b["kind"] == "forest" else (110, 105, 100, 220))
colors = {"center": (255, 215, 60), "left": (70, 170, 255), "right": (255, 90, 90), "link": (255, 255, 255), "ramp": (255, 150, 30), "work": (200, 120, 255)}
for e in P["edges"]:
    if e["width"] == 0: continue
    pts = [px(p[0], p[2]) for p in e["points"]]
    d.line(pts, fill=colors[e["lane"]] + (230,), width=max(2, int(e["width"] * S)))
for k, p in P["nodes"].items():
    x, y = px(p[0], p[2]); d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(0, 0, 0, 255)); d.text((x + 5, y - 5), k, fill=(0, 0, 0, 255))
for c in P["chokes"]:
    x, y = px(*c["pos"]); d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=(255, 0, 255, 255), width=3)
x0, y0 = px(-180, -180); x1, y1 = px(180, 180); d.rectangle([x0, y0, x1, y1], outline=(255, 255, 0, 255))
out = Image.alpha_composite(img, ov).convert("RGB"); out.save(sys.argv[1] if len(sys.argv) > 1 else "/tmp/x/paths_debug.png")
