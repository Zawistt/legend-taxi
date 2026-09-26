"""Qumtepa 5v5 — 4-bosqich teksturalari (protsedural, 512 px, choksiz takrorlanadi).

Qumtepa v2 teksturalari (qumtepa-v2/tools/textures.py) ustiga hudud uslublari uchun yangilari:
koshin (ko'k va firuza), g'isht, tosh yo'lak (bozor), soyabon matolari, gilam, gumbaz koshini,
to'q qumtosh (qal'a), oq suvoq (madrasa, masjid), och yog'och (balkonlar).
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "qumtepa-v2", "tools"))
import textures as V2   # noqa: E402

N = V2.N
fbm, to_img, normal_from_height, block_pattern = V2.fbm, V2.to_img, V2.normal_from_height, V2.block_pattern


def sandstone_dark():
    img, nrm = V2.sandstone()
    a = np.asarray(img).astype(float) / 255
    a *= np.array([0.86, 0.80, 0.74])[None, None]
    return to_img(a), nrm


def plaster_white():
    n1 = fbm(210, 3)
    n2 = fbm(220, 24, 5)
    stain = np.clip((fbm(230, 2, 4) - 0.58) * 3, 0, 1)
    base = np.array([0.93, 0.89, 0.80])
    shade = 1 + 0.10 * (n1 - 0.5) + 0.08 * (n2 - 0.5) - 0.22 * stain
    rgb = base[None, None] * shade[..., None]
    rgb[..., 2] -= 0.05 * stain
    return to_img(rgb), normal_from_height(n2 * 0.5, 2)


def brick():
    t, e, m = block_pattern(64, 24, 2, 240)
    n1 = fbm(250, 6)
    n2 = fbm(260, 40, 3)
    base = np.array([0.66, 0.40, 0.27])
    shade = (1 + 0.12 * t + 0.25 * (n1 - 0.5) + 0.15 * (n2 - 0.5)) * (0.86 + 0.14 * np.clip(e / 5.0, 0, 1))
    rgb = base[None, None] * shade[..., None]
    rgb[m] = np.array([0.72, 0.66, 0.56]) * (0.9 + 0.2 * n2[m])[..., None]
    h = np.clip(e / 5.0, 0, 1) * 0.7 + n2 * 0.3
    h[m] = 0
    return to_img(rgb), normal_from_height(ndimage.gaussian_filter(h, 1, mode="wrap"), 3)


def cobble():
    rng = np.random.default_rng(270)
    pts = rng.random((180, 2)) * N
    y, x = np.mgrid[0:N, 0:N]
    d1 = np.full((N, N), 1e9)
    d2 = np.full((N, N), 1e9)
    idx = np.zeros((N, N), int)
    for i, (px, py) in enumerate(pts):
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                d = np.hypot(x - px - ox, y - py - oy)
                closer = d < d1
                d2 = np.where(closer, d1, np.minimum(d2, d))
                idx = np.where(closer, i, idx)
                d1 = np.where(closer, d, d1)
    edge = d2 - d1
    tint = rng.normal(0, 1, len(pts))[idx]
    n = fbm(280, 20, 4)
    base = np.array([0.70, 0.62, 0.50])
    shade = (1 + 0.10 * tint + 0.2 * (n - 0.5)) * (0.55 + 0.45 * np.clip(edge / 7.0, 0, 1))
    rgb = base[None, None] * shade[..., None]
    h = np.clip(edge / 9.0, 0, 1) ** 0.6
    return to_img(rgb), normal_from_height(h, 4)


def tile(palette, seed):
    """Koshin: sakkiz qirrali yulduzlar va xochlar panjarasi, har bir plitka 128 px."""
    s = 128
    im = Image.new("RGB", (N, N), palette[0])
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    for ty in range(0, N, s):
        for tx in range(0, N, s):
            cx, cy = tx + s / 2, ty + s / 2
            star = []
            for k in range(16):
                r = s * (0.46 if k % 2 == 0 else 0.30)
                a = np.pi / 8 * k + np.pi / 16
                star.append((cx + r * np.cos(a), cy + r * np.sin(a)))
            d.polygon(star, fill=palette[1], outline=palette[3])
            inner = [(cx + s * 0.18 * np.cos(np.pi / 4 * k), cy + s * 0.18 * np.sin(np.pi / 4 * k)) for k in range(8)]
            d.polygon(inner, fill=palette[2])
            for ox, oy in ((0, 0), (s, 0), (0, s), (s, s)):
                x0, y0 = tx + ox, ty + oy
                d.polygon([(x0, y0 - 18), (x0 + 18, y0), (x0, y0 + 18), (x0 - 18, y0)], fill=palette[2])
            d.line([(tx, ty), (tx + s, ty)], fill=palette[3], width=3)
            d.line([(tx, ty), (tx, ty + s)], fill=palette[3], width=3)
    a = np.asarray(im).astype(float) / 255
    gl = fbm(seed, 4)
    a *= (0.9 + 0.2 * gl)[..., None]
    y, x = np.mgrid[0:N, 0:N]
    grout = ((x % s) < 3) | ((y % s) < 3)
    h = np.where(grout, 0.0, 0.6)
    return to_img(a), normal_from_height(ndimage.gaussian_filter(h, 1.5, mode="wrap"), 2)


def tile_blue():
    return tile([(236, 232, 220), (32, 78, 150), (230, 190, 70), (20, 40, 80)], 290)


def tile_turq():
    return tile([(240, 236, 224), (40, 150, 160), (30, 70, 140), (20, 60, 70)], 300)


def dome_turq():
    n = fbm(310, 30, 4)
    y, x = np.mgrid[0:N, 0:N]
    rows = ((y // 32) % 2 == 0)
    xo = (x + np.where(rows, 0, 16)) % 32
    brickline = (xo < 2) | ((y % 32) < 2)
    base = np.array([0.18, 0.62, 0.66])
    shade = 1 + 0.15 * (n - 0.5)
    rgb = base[None, None] * shade[..., None]
    rgb[brickline] *= 0.7
    return to_img(rgb), normal_from_height(np.where(brickline, 0, 0.5).astype(float), 2)


def awning(c1, c2, seed):
    y, x = np.mgrid[0:N, 0:N]
    stripe = ((x // 64) % 2 == 0)
    n = fbm(seed, 8, 4, aniso=(0.3, 3))
    rgb = np.where(stripe[..., None], np.array(c1)[None, None], np.array(c2)[None, None]).astype(float)
    rgb *= (0.85 + 0.25 * n)[..., None]
    fold = 0.5 + 0.5 * np.sin(x / N * np.pi * 16)
    rgb *= (0.88 + 0.12 * fold)[..., None]
    return to_img(rgb), normal_from_height(fold * 0.5, 2)


def carpet(seed=330):
    im = Image.new("RGB", (N, N), (120, 28, 30))
    d = ImageDraw.Draw(im)
    d.rectangle([24, 24, N - 24, N - 24], outline=(210, 170, 90), width=18)
    d.rectangle([64, 64, N - 64, N - 64], outline=(30, 40, 90), width=10)
    c = N // 2
    for r, col in ((150, (200, 150, 70)), (110, (30, 40, 90)), (70, (160, 40, 40)), (35, (220, 200, 150))):
        d.polygon([(c, c - r), (c + r, c), (c, c + r), (c - r, c)], fill=col)
    for k in range(8):
        for j in range(8):
            if (k + j) % 3 == 0:
                x0, y0 = 90 + k * 42, 90 + j * 42
                d.rectangle([x0, y0, x0 + 6, y0 + 6], fill=(220, 200, 150))
    a = np.asarray(im).astype(float) / 255
    a *= (0.85 + 0.25 * fbm(seed, 64, 3))[..., None]
    return to_img(a), normal_from_height(fbm(seed + 1, 96, 2) * 0.3, 1)


def wood_light():
    return V2.wood(340, (0.56, 0.40, 0.24), 4)


def all_textures():
    t = V2.all_textures()
    t.update({
        "sandstone_dk": sandstone_dark(), "plaster_w": plaster_white(), "brick": brick(), "cobble": cobble(),
        "tile_blue": tile_blue(), "tile_turq": tile_turq(), "dome": dome_turq(), "wood_light": wood_light(),
        "awning_r": awning((0.72, 0.16, 0.14), (0.90, 0.84, 0.70), 350),
        "awning_b": awning((0.16, 0.30, 0.62), (0.90, 0.88, 0.80), 360),
        "awning_g": awning((0.20, 0.46, 0.26), (0.88, 0.76, 0.34), 370),
        "carpet": carpet(),
    })
    return t


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "textures")
    os.makedirs(out, exist_ok=True)
    tex = all_textures()
    sheet = Image.new("RGB", (256 * 6, 256 * ((len(tex) + 5) // 6)))
    for i, (k, (img, _n)) in enumerate(tex.items()):
        sheet.paste(img.resize((256, 256)), ((i % 6) * 256, (i // 6) * 256))
    sheet.save(os.path.join(out, "sheet.png"))
    print(len(tex), "ta tekstura:", ", ".join(tex))
