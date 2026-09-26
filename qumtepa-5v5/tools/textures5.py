"""Qumtepa 5v5 — 4-bosqich teksturalari (protsedural, 512 px, choksiz takrorlanadi).

Qumtepa v2 teksturalari (qumtepa-v2/tools/textures.py) ustiga hudud uslublari uchun yangilari:
koshin (ko'k va firuza), g'isht, tosh yo'lak (bozor), soyabon matolari, gilam, gumbaz koshini,
to'q qumtosh (qal'a), oq suvoq (madrasa, masjid), och yog'och (balkonlar).
"""
import math, os, sys
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


# ------------------------------------------------------------------ 5-bosqich: milliy teksturalar
def girih(seed=400):
    """Girih: o'n qirrali yulduzlar va beshburchaklar to'ri (Registon, Shohi Zinda koshinlari ruhida)."""
    s = 256
    im = Image.new("RGB", (N, N), (238, 232, 214))
    d = ImageDraw.Draw(im)
    blue, turq, gold, line = (28, 70, 150), (40, 150, 160), (214, 170, 70), (250, 248, 236)
    for ty in range(-s, N + s, s):
        for tx in range(-s, N + s, s):
            for (ox, oy, big) in ((0, 0, True), (s / 2, s / 2, False)):
                cx, cy = tx + ox, ty + oy
                r1 = s * (0.38 if big else 0.2)
                r2 = r1 * 0.62
                pts = []
                for k in range(20):
                    r = r1 if k % 2 == 0 else r2
                    a = math.pi / 10 * k
                    pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
                d.polygon(pts, fill=blue if big else turq, outline=line)
                inner = [(cx + r2 * 0.6 * math.cos(math.pi / 5 * k), cy + r2 * 0.6 * math.sin(math.pi / 5 * k)) for k in range(10)]
                d.polygon(inner, fill=gold, outline=line)
                if big:
                    for k in range(10):
                        a = math.pi / 5 * k
                        x0, y0 = cx + r1 * math.cos(a), cy + r1 * math.sin(a)
                        x1, y1 = cx + s * 0.55 * math.cos(a), cy + s * 0.55 * math.sin(a)
                        d.line([(x0, y0), (x1, y1)], fill=line, width=5)
    a = np.asarray(im).astype(float) / 255
    a *= (0.92 + 0.14 * fbm(seed, 4))[..., None]
    h = ndimage.gaussian_filter((a.mean(-1) > 0.9).astype(float), 1.5, mode="wrap")
    return to_img(a), normal_from_height(h, 2)


def majolica(seed=410):
    """Xiva majolikasi: oq fonda ko'k-yashil o'simliksimon naqsh (islimiy)."""
    im = Image.new("RGB", (N, N), (240, 238, 228))
    d = ImageDraw.Draw(im)
    blue, dark, green = (40, 90, 170), (20, 40, 90), (60, 140, 110)
    s = 128
    for ty in range(0, N, s):
        for tx in range(0, N, s):
            cx, cy = tx + s / 2, ty + s / 2
            for k in range(4):
                a = math.pi / 2 * k + math.pi / 4
                px_, py_ = cx + 34 * math.cos(a), cy + 34 * math.sin(a)
                d.ellipse([px_ - 16, py_ - 26, px_ + 16, py_ + 26], fill=blue, outline=dark, width=3)
            d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=green, outline=dark, width=3)
            for k in range(8):
                a = math.pi / 4 * k
                d.arc([cx - 58, cy - 58, cx + 58, cy + 58], math.degrees(a), math.degrees(a) + 25, fill=dark, width=4)
            d.rectangle([tx, ty, tx + s, ty + s], outline=(200, 196, 186), width=2)
    a = np.asarray(im).astype(float) / 255
    a *= (0.93 + 0.12 * fbm(seed, 4))[..., None]
    return to_img(a), normal_from_height(np.zeros((N, N)), 1)


def ganch(seed=420):
    """Ganch o'ymakorligi: oq gips ustida chuqur o'yilgan geometrik-o'simliksimon naqsh."""
    y, x = np.mgrid[0:N, 0:N] / N * 2 * math.pi
    p = (np.sin(4 * x) * np.cos(4 * y) + 0.6 * np.sin(8 * (x + y)) * np.sin(8 * (x - y)))
    rel = (p > 0.35).astype(float) + 0.5 * (np.abs(p) < 0.08)
    h = ndimage.gaussian_filter(rel, 1.2, mode="wrap")
    base = np.array([0.93, 0.90, 0.84])
    shade = 0.62 + 0.38 * h + 0.06 * (fbm(seed, 6) - 0.5)
    return to_img(base[None, None] * shade[..., None]), normal_from_height(h, 6)


def carved_wood(seed=430):
    """Xiva o'ymakor eshigi: to'q yog'och, to'rtburchak panellar, ichida girih-rozetkalar."""
    img, nrm = V2.wood(seed, (0.34, 0.21, 0.12), 3)
    a = np.asarray(img).astype(float) / 255
    y, x = np.mgrid[0:N, 0:N]
    h = np.zeros((N, N))
    for py0 in (20, 180, 340):
        for px0 in (30, 270):
            box_ = (x >= px0) & (x < px0 + 212) & (y >= py0) & (y < py0 + 150)
            edge = box_ & ((np.abs(x - px0) < 10) | (np.abs(x - px0 - 211) < 10) | (np.abs(y - py0) < 10) | (np.abs(y - py0 - 149) < 10))
            cx, cy = px0 + 106, py0 + 75
            r = np.hypot(x - cx, y - cy)
            ang = np.arctan2(y - cy, x - cx)
            rose = box_ & (r < 55 + 12 * np.cos(8 * ang))
            a[edge] *= 0.6
            a[rose] *= 1.25
            h += edge * 0.8 + rose * (0.5 + 0.5 * np.cos(8 * ang)) * 0.6
    return to_img(a), normal_from_height(ndimage.gaussian_filter(h, 1.5, mode="wrap"), 3)


def atlas(colors, seed):
    """Atlas / adras (ikat): vertikal to'lqinli naqsh, chegaralari "suvga oqqan" kabi xira."""
    y, x = np.mgrid[0:N, 0:N].astype(float)
    band = (x / N * 6 + 0.6 * np.sin(y / N * 2 * math.pi * 4) + 0.15 * fbm(seed, 12, 3, aniso=(0.2, 4))) % 1.0
    idx = (band * len(colors)).astype(int) % len(colors)
    pal = np.array(colors, float) / 255
    rgb = pal[idx]
    blur = ndimage.gaussian_filter(rgb, (0, 3, 0))
    thread = 0.92 + 0.08 * (np.sin(y * 1.2) > 0)
    return to_img(blur * thread[..., None]), normal_from_height(thread * 0.2, 1)


def suzani(seed=440):
    """So'zana: oq-krem mato ustida yirik qizil-to'q sariq aylana gullar (medalyonlar)."""
    im = Image.new("RGB", (N, N), (236, 224, 196))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    for cx, cy, r in ((128, 128, 92), (384, 384, 92), (384, 128, 60), (128, 384, 60), (256, 256, 40)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(170, 30, 36))
        d.ellipse([cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7], fill=(220, 120, 40))
        d.ellipse([cx - r * 0.4, cy - r * 0.4, cx + r * 0.4, cy + r * 0.4], fill=(120, 20, 40))
        for k in range(12):
            a = math.pi / 6 * k
            px_, py_ = cx + r * 1.12 * math.cos(a), cy + r * 1.12 * math.sin(a)
            d.ellipse([px_ - 9, py_ - 9, px_ + 9, py_ + 9], fill=(60, 110, 70))
    for _ in range(40):
        px_, py_ = rng.integers(0, N, 2)
        d.line([(px_, py_), (px_ + rng.integers(-40, 40), py_ + rng.integers(-40, 40))], fill=(60, 110, 70), width=4)
    a = np.asarray(im).astype(float) / 255
    a *= (0.9 + 0.15 * fbm(seed, 64, 3))[..., None]
    return to_img(a), normal_from_height(fbm(seed + 1, 96, 2) * 0.3, 1)


def paxta(seed=450):
    """Paxta toyi: oq-kulrang qanor mato, arqon bog'ichlar."""
    y, x = np.mgrid[0:N, 0:N]
    weave = 0.5 + 0.25 * np.sin(x * 0.9) + 0.25 * np.sin(y * 0.9)
    n = fbm(seed, 6)
    base = np.array([0.86, 0.84, 0.78])
    rgb = base[None, None] * (0.85 + 0.1 * weave + 0.15 * (n - 0.5))[..., None]
    rope = (np.abs((y % 170) - 85) < 7)
    rgb[rope] = np.array([0.55, 0.42, 0.26])
    h = weave * 0.2 + rope * 0.8
    return to_img(rgb), normal_from_height(h, 2)


def vassa(seed=460):
    """Vassa-bolor shift: zich terilgan yumaloq yog'och xodalar."""
    y, x = np.mgrid[0:N, 0:N]
    k = x % 32
    round_ = np.sqrt(np.clip(1 - ((k - 16) / 16.0) ** 2, 0, 1))
    g = fbm(seed, 6, 4, aniso=(6, 0.4))
    rng = np.random.default_rng(seed)
    tint = rng.normal(0, 1, N // 32 + 1)[x // 32]
    rgb = np.array([0.50, 0.34, 0.19])[None, None] * (0.55 + 0.45 * round_ + 0.06 * tint + 0.15 * (g - 0.5))[..., None]
    return to_img(rgb), normal_from_height(round_, 3)


def lagan(seed=470):
    """Rishton lagani: ko'k-firuza sirli sopol, markazdan tarqalgan naqsh (disk uchun, alfa bilan)."""
    s = N
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = s / 2
    d.ellipse([4, 4, s - 4, s - 4], fill=(236, 240, 238, 255), outline=(20, 60, 120, 255), width=18)
    for k in range(16):
        a = math.pi / 8 * k
        d.polygon([(c, c), (c + c * 0.9 * math.cos(a - 0.12), c + c * 0.9 * math.sin(a - 0.12)),
                   (c + c * 0.9 * math.cos(a + 0.12), c + c * 0.9 * math.sin(a + 0.12))],
                  fill=(30, 110, 170, 255) if k % 2 else (40, 160, 160, 255))
    d.ellipse([c - 60, c - 60, c + 60, c + 60], fill=(236, 240, 238, 255), outline=(20, 60, 120, 255), width=8)
    d.ellipse([c - 26, c - 26, c + 26, c + 26], fill=(30, 110, 170, 255))
    return im


def leaves(seed=480):
    """Chinor barglari (alfa kartochka): yirik besh bo'lakli barglar to'dasi."""
    s = N
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    for _ in range(320):
        cx, cy = rng.normal(s / 2, s * 0.2, 2)
        if math.hypot(cx - s / 2, cy - s / 2) > s * 0.46:
            continue
        r = rng.uniform(14, 26)
        g = int(rng.uniform(90, 150))
        col = (int(g * 0.45), g, int(g * 0.3), 255)
        for k in range(5):
            a = rng.uniform(0, 0.4) + k * 2 * math.pi / 5
            d.ellipse([cx + r * 0.6 * math.cos(a) - r * 0.45, cy + r * 0.6 * math.sin(a) - r * 0.45,
                       cx + r * 0.6 * math.cos(a) + r * 0.45, cy + r * 0.6 * math.sin(a) + r * 0.45], fill=col)
    return im


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
        # 5-bosqich: milliy
        "girih": girih(), "majolica": majolica(), "ganch": ganch(), "carved_wood": carved_wood(),
        "atlas_1": atlas([(200, 30, 60), (250, 200, 40), (30, 60, 160), (250, 250, 240), (40, 140, 90)], 490),
        "atlas_2": atlas([(120, 20, 90), (240, 120, 30), (250, 230, 200), (20, 110, 170)], 500),
        "suzani": suzani(), "paxta": paxta(), "vassa": vassa(),
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
    lagan().save(os.path.join(out, "lagan.png")); leaves().save(os.path.join(out, "leaves.png"))
    print(len(tex), "ta tekstura:", ", ".join(tex))
