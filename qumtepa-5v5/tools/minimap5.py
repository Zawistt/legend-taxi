"""Qumtepa 5v5 — 7-bosqich: minimap (radar) rasmi, tepadan uslublashtirilgan xarita.

godot/ui/minimap.png (1024×1024, 110 m): binolar to'q, yuriladigan joy hudud rangida, yopiq yo'laklar to'qroq,
bomba zonalari va harflar, spawn'lar, asosiy callout nomlari. Shimol (T) — tepada.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont
import layout5 as L

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "godot", "ui", "minimap.png")
S = 1024
K = S / (L.G * L.CELL)          # px / m
an = json.load(open(os.path.join(HERE, "..", "docs", "analysis_stage1.json")))

TINT = {"qala": (196, 170, 132), "bozor": (214, 190, 146), "madrasa": (222, 214, 196), "karvon": (206, 162, 132), "masjid": (200, 214, 208)}
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
P = lambda x, z: ((x - L.ORIGIN) * K, (z - L.ORIGIN) * K)
for r in range(L.G):
    for c in range(L.G):
        x0, y0 = P(L.ORIGIN + c * L.CELL, L.ORIGIN + r * L.CELL)
        x1, y1 = x0 + L.CELL * K, y0 + L.CELL * K
        t = L.grid[r][c]
        if t == "#":
            col = (58, 46, 38, 235)
        else:
            base = TINT[L.DISTRICT[r][c]]
            f = 0.78 if t in L.COVER else 1.0
            col = tuple(int(v * f) for v in base) + (235,)
        d.rectangle([x0, y0, x1, y1], fill=col)
for p in L.PROPS:
    if p[0] == "wall":
        d.rectangle([*P(p[1], p[2]), *P(p[3], p[4])], fill=(58, 46, 38, 235))
    elif p[0] == "platform":
        d.rectangle([*P(p[1], p[2]), *P(p[3], p[4])], fill=(150, 110, 70, 235))
    elif p[0] == "stack":
        x, z = p[1], p[2]
        d.rectangle([*P(x - 0.7, z - 0.7), *P(x + 0.7, z + 0.7)], fill=(120, 84, 52, 235))
for s, rect in L.BOMB_ZONES.items():
    d.rectangle([*P(rect[0], rect[1]), *P(rect[2], rect[3])], outline=(200, 40, 40, 255), width=5)
try:
    F = lambda n: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", n)
    F(10)
except OSError:
    F = lambda n: ImageFont.load_default()
for s, p in (("A", L.A_PLANT), ("B", L.B_PLANT)):
    x, y = P(*p)
    d.text((x, y), s, fill=(210, 40, 40, 255), font=F(90), anchor="mm", stroke_width=4, stroke_fill=(255, 255, 255, 255))
for team, rect, col in (("T", L.BUY_ZONES["T"], (220, 120, 40, 255)), ("CT", L.BUY_ZONES["CT"], (50, 100, 200, 255))):
    x, y = P((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)
    d.text((x, y), team, fill=col, font=F(56), anchor="mm", stroke_width=3, stroke_fill=(255, 255, 255, 255))
LABELS = {"Long": (-44, -8), "Outside long": (-31, -38), "Catwalk": (-22, -19), "Top mid": (0, -24), "Mid": (0, -9),
          "Upper tunnels": (31, -38), "Lower tunnels": (44, -8), "B window": (22, -12), "CT mid": (8, 21), "A ramp": (-25, 38),
          "B ramp": (25, 38), "A CT": (-14, 15), "B doors": (14, 15), "Long pit": (-32, -8), "Mid doors": (0, 5)}
for n, p in LABELS.items():
    x, y = P(*p)
    d.text((x, y), n, fill=(255, 255, 255, 255), font=F(22), anchor="mm", stroke_width=3, stroke_fill=(40, 30, 20, 255))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT)
print("minimap:", OUT)
