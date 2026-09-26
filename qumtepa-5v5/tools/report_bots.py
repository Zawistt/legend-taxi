"""Qumtepa 5v5 — 3-bosqich: bot o'yinlari natijasini rasmga chiqaradi.

docs/bots_stage3.json (tests/run_bots.gd natijasi) dan docs/bots_stage3.png:
chapda — xaritada o'limlar (T — to'q sariq, CT — ko'k) va birinchi o'limlar chiziqlari,
o'ngda — T taktikasi va CT joylashuvi bo'yicha T g'alaba foizi.

Ishga tushirish: cd qumtepa-5v5/tools && python3 report_bots.py
"""
import json, os
from PIL import Image, ImageDraw, ImageFont
import layout5 as L

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs")
data = json.load(open(os.path.join(DOCS, "bots_stage3.json")))
S = data["summary"]
try:
    F = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", s)
    FB = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", s)
    F(10)
except OSError:
    F = FB = lambda s: ImageFont.load_default()

C = 13
PAD = 40
W = PAD * 2 + L.G * C
PANEL = 640
img = Image.new("RGB", (W + PANEL, W), (234, 224, 200))
dr = ImageDraw.Draw(img, "RGBA")
COL = {"#": (92, 72, 56), ".": (228, 208, 164), ",": (198, 172, 130), "m": (188, 160, 118),
       "T": (214, 160, 92), "C": (122, 160, 186), "A": (232, 184, 156), "B": (232, 184, 156)}
for r in range(L.G):
    for c in range(L.G):
        dr.rectangle([PAD + c * C, PAD + r * C, PAD + c * C + C - 1, PAD + r * C + C - 1], fill=COL[L.grid[r][c]])
P = lambda x, z: (PAD + (x - L.ORIGIN) / L.CELL * C, PAD + (z - L.ORIGIN) / L.CELL * C)
TC, CC = (214, 96, 20), (30, 80, 190)
for rd in data["rounds"]:
    if rd["kills"]:
        k = rd["kills"][0]
        dr.line([P(*k["kp"]), P(*k["vp"])], fill=(20, 20, 20, 60), width=1)
for rd in data["rounds"]:
    for k in rd["kills"]:
        x, y = P(*k["vp"])
        col = TC if k["victim"] == "T" else CC
        dr.ellipse([x - 3, y - 3, x + 3, y + 3], fill=col + (150,))
for s, p in (("A", L.A_PLANT), ("B", L.B_PLANT)):
    x, y = P(*p)
    dr.text((x - 9, y - 16), s, fill=(170, 30, 30), font=FB(28))
dr.text((PAD, 12), "O'limlar: • T  • CT   (kulrang chiziq — raunddagi birinchi o'lim: otuvchi → o'lgan)", fill=(60, 50, 40), font=F(13))
dr.ellipse([PAD + 88, 17, PAD + 96, 25], fill=TC)
dr.ellipse([PAD + 118, 17, PAD + 126, 25], fill=CC)

X, y = W + 10, PAD
dr.text((X, y), "Qumtepa 5v5 — 5v5 bot o'yinlari", fill=(40, 30, 20), font=FB(22)); y += 32
dr.text((X, y), f"{S['rounds']} raund · T yutdi {S['t_win_pct']}% · bomba o'rnatildi {S['plant_pct']}% · "
                f"qaytarib olish {S['retake_pct']}%", fill=(90, 70, 50), font=F(14)); y += 30


def bars(title, d, y, order=None):
    dr.text((X, y), title, fill=(40, 30, 20), font=FB(16)); y += 24
    keys = order or list(d)
    for k in keys:
        v = d[k]
        pct = v["t_win_pct"]
        dr.text((X, y), k, fill=(50, 40, 30), font=F(12))
        bx = X + 250
        dr.rectangle([bx, y + 2, bx + 300, y + 14], fill=(210, 200, 180))
        dr.rectangle([bx, y + 2, bx + 3 * pct, y + 14], fill=TC if pct >= 50 else CC)
        dr.line([bx + 150, y, bx + 150, y + 16], fill=(40, 30, 20), width=1)
        dr.text((bx + 306, y), f"{pct:.0f}%", fill=(40, 30, 20), font=F(12))
        y += 19
    return y + 12


y = bars("T taktikasi (T g'alaba %)", S["by_strategy"], y, [s[0] for s in L.T_STRATS])
y = bars("CT joylashuvi", S["by_setup"], y, [s[0] for s in L.CT_SETUPS])
y = bars("Site", S["by_site"], y, ["A", "B"])
dr.text((X, y), "Chiziq o'rtasi — 50%. To'q sariq — T ustun, ko'k — CT ustun.", fill=(90, 70, 50), font=F(12))
img.save(os.path.join(DOCS, "bots_stage3.png"))
print("saqlandi: docs/bots_stage3.png")
