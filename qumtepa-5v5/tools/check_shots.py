"""Qumtepa 5v5 — 6-bosqich: ko'rinish tekshiruvi (skrinshotlardan).

O'yinchi dushmanni ko'ra olishi uchun sahna na juda qorong'i, na oqarib ketgan bo'lmasligi kerak.
Har bir skrinshotning markaziy qismi (o'yinchi qaraydigan joy) uchun o'rtacha yorqinlik o'lchanadi.
Ishga tushirish: skrinshotlardan keyin (godot/tools/screenshots.gd), `python3 check_shots.py`.
"""
import glob, json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "..", "docs", "shots")
LO, HI = 0.22, 0.85          # o'rtacha yorqinlik chegaralari (0 — qora, 1 — oq)
res, fails = {}, 0
for f in sorted(glob.glob(os.path.join(SHOTS, "[0-9][0-9]_*.png"))):
    name = os.path.basename(f)[:-4]
    if name.startswith("01_"):
        continue                       # tepadan ko'rinish — o'yinchi ko'rmaydi
    a = np.asarray(Image.open(f).convert("RGB")).astype(float) / 255
    h, w, _ = a.shape
    c = a[int(h * 0.3):int(h * 0.8), int(w * 0.25):int(w * 0.75)]
    lum = float((0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]).mean())
    dark = float(((0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]) < 0.08).mean())
    ok = LO <= lum <= HI and dark < 0.15
    fails += not ok
    res[name] = {"lum": round(lum, 3), "dark_frac": round(dark, 3), "ok": ok}
    print(("  [OK]   " if ok else "  [XATO] ") + f"{name:26s} yorqinlik {lum:.2f} (≥{LO}, ≤{HI}), juda qorong'i piksel {dark * 100:.0f}% (<15%)")
print(f"\nNATIJA: {len(res) - fails} / {len(res)} skrinshot ko'rinish talabiga javob beradi")
json.dump(res, open(os.path.join(SHOTS, "..", "visibility_stage6.json"), "w"), indent=1)
sys.exit(1 if fails else 0)
