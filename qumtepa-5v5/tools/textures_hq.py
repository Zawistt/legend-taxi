"""Qumtepa 5v5 — yakuniy bosqich: yuqori sifatli PBR teksturalar (1024 px, protsedural).

Har bir material uchun godot/textures/ ga:
  <nom>_albedo.jpg — rang (eskirish, dog', kir bilan)
  <nom>_normal.jpg — relyef (OpenGL normal xaritasi)
  <nom>_orm.jpg    — R: soya (AO), G: g'adir-budurlik (roughness), B: metall
  <nom>_height.jpg — chuqurlik (parallax uchun, faqat tosh/g'isht/toshloq)
Godot'da scripts/materials.gd shu fayllardan StandardMaterial3D yig'adi va GLB dagi oddiy materiallarni almashtiradi.
Istalgan faylni fotosurat asosidagi (masalan, Poly Haven, ambientCG — CC0) tekstura bilan almashtirish mumkin:
nomi va formati bir xil bo'lsa, kod o'zgarmaydi.
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "godot", "textures")
N = 1024


# ------------------------------------------------------------------ asosiy shovqinlar (choksiz)
def noise(shape, cells, seed):
    rng = np.random.default_rng(seed)
    cy, cx = cells if isinstance(cells, tuple) else (cells, cells)
    g = rng.random((cy, cx))
    g = np.pad(g, ((0, 1), (0, 1)), mode="wrap")
    return ndimage.zoom(g, ((shape[0] + shape[0] / cy) / (cy + 1), (shape[1] + shape[1] / cx) / (cx + 1)), order=3)[: shape[0], : shape[1]]


def fbm(seed, base=4, octaves=6, aniso=(1, 1), n=N):
    out = np.zeros((n, n))
    amp, tot, c = 1.0, 0.0, base
    for o in range(octaves):
        cy = max(2, min(n, int(c * aniso[0])))
        cx = max(2, min(n, int(c * aniso[1])))
        out += amp * noise((n, n), (cy, cx), seed + o * 31)
        tot += amp
        amp *= 0.55
        c *= 2
    return out / tot


def cracks(seed, count, length, n=N, width=1):
    """tasodifiy yoriqlar (tasodifiy yurish chiziqlari), 0..1 niqob"""
    rng = np.random.default_rng(seed)
    im = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(im)
    for _ in range(count):
        x, y = rng.random(2) * n
        a = rng.random() * 2 * math.pi
        pts = [(x, y)]
        for _ in range(int(length)):
            a += rng.normal(0, 0.45)
            x = (x + math.cos(a) * 6) % n
            y = (y + math.sin(a) * 6) % n
            if abs(pts[-1][0] - x) > 20 or abs(pts[-1][1] - y) > 20:
                pts = [(x, y)]
                continue
            pts.append((x, y))
            if len(pts) > 1:
                d.line(pts[-2:], fill=255, width=width)
            if rng.random() < 0.03:
                a += rng.choice([-1, 1]) * 1.2
    return np.asarray(im).astype(float) / 255


def normal_from(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nz = np.ones_like(h)
    l = np.sqrt(dx * dx + dy * dy + nz * nz)
    return np.stack([-dx / l, dy / l, nz / l], -1) * 0.5 + 0.5


def ao_from(h, radius=6, amount=1.4):
    blur = ndimage.gaussian_filter(h, radius, mode="wrap")
    return np.clip(1.0 - (blur - h) * amount, 0.35, 1.0)


def save(name, albedo, h, rough, metal=0.0, nstrength=6.0, height=False, ao_amount=1.4):
    os.makedirs(OUT, exist_ok=True)
    h = (h - h.min()) / max(1e-6, h.max() - h.min())
    ao = ao_from(h, amount=ao_amount)
    alb = np.clip(albedo * (0.55 + 0.45 * ao)[..., None], 0, 1)
    Image.fromarray((alb * 255).astype(np.uint8)).save(f"{OUT}/{name}_albedo.jpg", quality=90)
    Image.fromarray((normal_from(h, nstrength) * 255).astype(np.uint8)).save(f"{OUT}/{name}_normal.jpg", quality=92)
    rough = np.broadcast_to(np.asarray(rough, float), h.shape)
    orm = np.stack([ao, np.clip(rough, 0, 1), np.full_like(h, metal)], -1)
    Image.fromarray((orm * 255).astype(np.uint8)).save(f"{OUT}/{name}_orm.jpg", quality=90)
    if height:
        Image.fromarray((h * 255).astype(np.uint8)).save(f"{OUT}/{name}_height.jpg", quality=90)


# ------------------------------------------------------------------ toshlar (bloklar)
def blocks(seed, rows, cols_range, mortar_px, offset=True):
    """qatorlar bo'yicha har xil uzunlikdagi bloklar: id, qirragacha masofa, qorishma niqobi"""
    rng = np.random.default_rng(seed)
    rh = N // rows
    ids = np.zeros((N, N), int)
    edge = np.zeros((N, N))
    k = 0
    for r in range(rows):
        x = rng.integers(0, N // 2) if offset else 0
        start = x
        while True:
            w = int(rng.uniform(*cols_range) * N)
            x0, x1 = x, min(x + w, start + N)
            k += 1
            for xx in range(x0, x1):
                ids[r * rh:(r + 1) * rh, xx % N] = k
            x = x1
            if x >= start + N:
                break
    y, xg = np.mgrid[0:N, 0:N]
    same_r = ids == np.roll(ids, 1, 1)
    # qirragacha masofa: blok chegaralaridan distance transform
    border = (ids != np.roll(ids, 1, 1)) | (ids != np.roll(ids, 1, 0))
    edge = ndimage.distance_transform_edt(~border)
    return ids, edge, edge < mortar_px


def masonry(name, seed, base, rows, cols_range, mortar, tint_amt=0.08, chip=0.5, crack_n=14, rough=0.86, mortar_col=None, nstr=7):
    ids, edge, m = blocks(seed, rows, cols_range, mortar)
    rng = np.random.default_rng(seed)
    tint = rng.normal(0, 1, ids.max() + 2)[ids]
    hoff = rng.normal(0, 1, ids.max() + 2)[ids]
    n1, n2, n3 = fbm(seed + 1, 6), fbm(seed + 2, 48, 4), fbm(seed + 3, 160, 2)
    bevel = np.clip(edge / 14.0, 0, 1) ** 0.6
    chips = (fbm(seed + 4, 24, 3) > 0.62 - chip * 0.08) & (edge < 20)
    cr = cracks(seed + 5, crack_n, 50)
    h = 0.55 * bevel + 0.12 * hoff * bevel + 0.22 * n2 + 0.10 * n3 - 0.35 * chips * (1 - edge / 20) - 0.3 * cr
    h[m] = 0.02 + 0.05 * n3[m]
    col = np.array(base)[None, None] * (1 + tint_amt * tint + 0.22 * (n1 - 0.5) + 0.12 * (n2 - 0.5))[..., None]
    dirt = np.clip((fbm(seed + 6, 3, 4) - 0.45) * 2, 0, 1)
    col *= (1 - 0.18 * dirt)[..., None]
    mc = np.array(mortar_col or [c * 0.78 for c in base])
    col[m] = mc * (0.85 + 0.25 * n3[m])[..., None]
    col *= (1 - 0.35 * cr)[..., None]
    r = rough + 0.08 * (n2 - 0.5)
    r[m] = 0.97
    save(name, col, h, r, nstrength=nstr, height=True)


def plaster(name, seed, base, stains=0.25, crack_n=6):
    n1, n2, n3 = fbm(seed, 3), fbm(seed + 1, 24, 5), fbm(seed + 2, 128, 3)
    trowel = fbm(seed + 3, 10, 3, aniso=(0.4, 3))
    cr = cracks(seed + 4, crack_n, 70)
    # suvoq ko'chgan joylar: kichik, kam, qirrasi yumshoq; ostidagi loy-g'isht rangi suvoqdan biroz to'qroq
    patch = (fbm(seed + 5, 7, 5) > 0.74).astype(float)
    patch = ndimage.gaussian_filter(patch, 3, mode="wrap") * 0.8
    h = 0.35 * n2 + 0.15 * n3 + 0.2 * trowel - 0.4 * cr - 0.25 * patch
    stain = np.clip((fbm(seed + 6, 2, 4) - 0.5) * 3, 0, 1) * stains
    streak = np.clip((fbm(seed + 7, 6, 4, aniso=(0.12, 4)) - 0.55) * 3, 0, 1) * 0.25
    col = np.array(base)[None, None] * (1 + 0.08 * (n1 - 0.5) + 0.05 * (n2 - 0.5) - stain - streak)[..., None]
    col = col * (1 - 0.22 * ndimage.gaussian_filter(cr, 0.8))[..., None]
    under = np.array(base)[None, None] * np.array([0.82, 0.74, 0.66])[None, None] * (0.85 + 0.3 * n3)[..., None]
    col = col * (1 - patch[..., None]) + patch[..., None] * under
    save(name, col, h, 0.9 + 0.06 * (n2 - 0.5), nstrength=4)


def wood(name, seed, base, planks, rough=0.72, nails=True):
    y, x = np.mgrid[0:N, 0:N]
    g = fbm(seed, 6, 5, aniso=(10, 0.4))
    g2 = fbm(seed + 1, 20, 4, aniso=(10, 0.4))
    pw = N // planks
    pid = x // pw
    rng = np.random.default_rng(seed)
    tint = rng.normal(0, 1, planks + 1)[pid]
    gap = (x % pw) < 5
    rings = 0.5 + 0.5 * np.sin(g * 60 + pid * 3)
    knots = np.zeros((N, N))
    for _ in range(planks * 2):
        kx, ky = rng.random(2) * N
        d_ = np.hypot(x - kx, (y - ky) * 0.5)
        knots += np.exp(-(d_ / 14) ** 2)
    col = np.array(base)[None, None] * (1 + 0.12 * tint + 0.28 * (rings - 0.5) + 0.2 * (g2 - 0.5) - 0.35 * knots)[..., None]
    h = rings * 0.25 + g2 * 0.35 - knots * 0.3
    col[gap] *= 0.3
    h[gap] = 0
    if nails:
        for py in (40, N - 40):
            for p in range(planks):
                cx, cy = p * pw + pw // 2, py
                nm = (x - cx) ** 2 + (y - cy) ** 2 < 49
                col[nm] = [0.2, 0.19, 0.18]
                h[nm] = 0.9
    save(name, col, h, rough + 0.1 * (g2 - 0.5), nstrength=4)


def tile_from(name, src_png, seed, gloss=0.28):
    """mavjud koshin naqshini (textures5) olib, sir yaltirashi, choklar va mayda darzlar qo'shadi"""
    img = Image.open(src_png).convert("RGB").resize((N, N), Image.LANCZOS)
    col = np.asarray(img).astype(float) / 255
    y, x = np.mgrid[0:N, 0:N]
    s = N // 4 if "tile" in name else N // 8
    grout = ((x % s) < 5) | ((y % s) < 5)
    craz = cracks(seed, 60, 12)
    n = fbm(seed + 1, 32, 3)
    tilt = noise((N, N), (4, 4), seed + 2)
    h = 0.6 + 0.1 * tilt - 0.6 * grout - 0.05 * craz
    col *= (0.93 + 0.1 * n)[..., None]
    col[grout] = np.array([0.72, 0.68, 0.6])
    col *= (1 - 0.25 * craz)[..., None]
    r = np.full((N, N), gloss) + 0.1 * (n - 0.5)
    r[grout] = 0.95
    save(name, col, h, r, nstrength=3, ao_amount=0.8)


def cobble(name, seed):
    rng = np.random.default_rng(seed)
    pts = rng.random((420, 2)) * N
    y, x = np.mgrid[0:N, 0:N]
    d1 = np.full((N, N), 1e9); d2 = np.full((N, N), 1e9); idx = np.zeros((N, N), int)
    for i, (px, py) in enumerate(pts):
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                if abs(px + ox - N / 2) > N * 0.7 or abs(py + oy - N / 2) > N * 0.7:
                    continue
                d = np.hypot(x - px - ox, y - py - oy)
                closer = d < d1
                d2 = np.where(closer, d1, np.minimum(d2, d))
                idx = np.where(closer, i, idx)
                d1 = np.where(closer, d, d1)
    e = d2 - d1
    tint = rng.normal(0, 1, len(pts))[idx]
    n = fbm(seed + 1, 64, 3)
    dome = np.clip(e / 16.0, 0, 1) ** 0.5
    h = dome * (0.8 + 0.2 * rng.random(len(pts))[idx]) + 0.1 * n
    base = np.array([0.66, 0.6, 0.5])
    col = base[None, None] * (1 + 0.12 * tint + 0.2 * (n - 0.5))[..., None] * (0.5 + 0.5 * dome)[..., None]
    sand = e < 3
    col[sand] = np.array([0.7, 0.62, 0.48]) * (0.9 + 0.2 * n[sand])[..., None]
    save(name, col, h, 0.85 + 0.1 * (1 - dome), nstrength=8, height=True)


def cloth(name, seed, src=None, base=(0.86, 0.84, 0.78), rope=True):
    y, x = np.mgrid[0:N, 0:N]
    weave = 0.5 + 0.25 * np.sin(x * 1.3) * np.sign(np.sin(y * 0.65)) + 0.25 * np.sin(y * 1.3) * np.sign(np.sin(x * 0.65))
    n = fbm(seed, 6)
    if src:
        col = np.asarray(Image.open(src).convert("RGB").resize((N, N), Image.LANCZOS)).astype(float) / 255
    else:
        col = np.ones((N, N, 3)) * np.array(base)[None, None]
    col = col * (0.82 + 0.12 * weave + 0.15 * (n - 0.5))[..., None]
    h = weave * 0.3 + n * 0.2
    if rope:
        rp = (np.abs((y % 340) - 170) < 12)
        col[rp] = np.array([0.52, 0.4, 0.25]) * (0.8 + 0.2 * weave[rp])[..., None]
        h[rp] = 0.9
    save(name, col, h, 0.95, nstrength=3)


def dome_tiles(name, seed):
    y, x = np.mgrid[0:N, 0:N]
    rows = (y // 48) % 2 == 0
    xo = (x + np.where(rows, 0, 24)) % 48
    line = (xo < 3) | ((y % 48) < 3)
    n = fbm(seed, 30, 4)
    tint = noise((N, N), (N // 48, N // 48), seed + 1)
    col = np.array([0.16, 0.6, 0.64])[None, None] * (0.85 + 0.25 * tint + 0.15 * (n - 0.5))[..., None]
    col[line] = np.array([0.8, 0.78, 0.7])
    h = np.where(line, 0.0, 0.7) + 0.1 * n
    r = np.where(line, 0.9, 0.22 + 0.1 * n)
    save(name, col, h, r, nstrength=3, ao_amount=0.8)


def roof(name, seed):
    y, x = np.mgrid[0:N, 0:N]
    th = 96
    row = y // th
    xo = (x + (row % 2) * 48) % N
    lx = (xo % 96) / 96 - 0.5
    ly = (y % th) / th
    curve = np.sqrt(np.clip(1 - (2 * lx) ** 2, 0, 1))
    n = fbm(seed, 8)
    tint = noise((N, N), (N // th, N // 96), seed + 1)
    moss = np.clip((fbm(seed + 2, 6, 4) - 0.6) * 3, 0, 1) * (1 - curve)
    col = np.array([0.62, 0.34, 0.2])[None, None] * ((0.55 + 0.45 * curve) * (0.75 + 0.25 * ly) * (1 + 0.15 * (tint - 0.5) + 0.2 * (n - 0.5)))[..., None]
    col = col * (1 - moss[..., None]) + moss[..., None] * np.array([0.3, 0.32, 0.18])
    save(name, col, curve * 0.7 + ly * 0.3, 0.8, nstrength=5)


def ganch(name, seed):
    y, x = np.mgrid[0:N, 0:N] / N * 2 * math.pi
    p = np.sin(4 * x) * np.cos(4 * y) + 0.6 * np.sin(8 * (x + y)) * np.sin(8 * (x - y))
    rel = (p > 0.35).astype(float) + 0.5 * (np.abs(p) < 0.08)
    h = ndimage.gaussian_filter(rel, 2.0, mode="wrap") + 0.1 * fbm(seed, 64, 3)
    col = np.array([0.93, 0.9, 0.84])[None, None] * (0.86 + 0.1 * fbm(seed + 1, 4))[..., None]
    save(name, col, h, 0.9, nstrength=10, height=True)


def grime():
    """devor tagi kiri va yomg'ir izlari uchun: pastdan tepaga so'nuvchi alfa (RGBA PNG)"""
    y, x = np.mgrid[0:512, 0:512] / 512.0
    n = fbm(900, 8, 5, n=512)
    streak = fbm(901, 24, 3, aniso=(0.08, 3), n=512)
    a_base = np.clip((1 - y) ** 1.6 * (0.55 + 0.6 * n) + 0.25 * (streak - 0.5), 0, 1) * 0.75
    rgb = np.stack([0.26 + 0.1 * n, 0.2 + 0.08 * n, 0.14 + 0.05 * n], -1)
    Image.fromarray((np.dstack([rgb, a_base]) * 255).astype(np.uint8), "RGBA").save(f"{OUT}/grime.png")
    a_rain = np.clip(y ** 0.8 * (streak - 0.35) * 2.2, 0, 1) * 0.55
    Image.fromarray((np.dstack([rgb * 0.8, a_rain]) * 255).astype(np.uint8), "RGBA").save(f"{OUT}/rain.png")
    # yoriq va dog' decal'lari
    cr = cracks(902, 6, 40, n=512, width=2)
    cr = ndimage.gaussian_filter(cr, 0.6)
    Image.fromarray((np.dstack([np.full((512, 512, 3), 0.18), cr * 0.9]) * 255).astype(np.uint8), "RGBA").save(f"{OUT}/decal_crack.png")
    yy, xx = np.mgrid[0:512, 0:512]
    r = np.hypot(xx - 256, yy - 256) / 256
    st = np.clip((1 - r) * 1.5 * (0.5 + 0.8 * fbm(903, 6, 4, n=512)) - 0.3, 0, 1) * 0.6
    Image.fromarray((np.dstack([np.stack([0.3 + 0 * r, 0.24 + 0 * r, 0.16 + 0 * r], -1), st]) * 255).astype(np.uint8), "RGBA").save(f"{OUT}/decal_stain.png")


def sky():
    """osmon panoramasi (equirect 2048×1024): ko'k gradient, ufqda chang-tuman, to'p-to'p bulutlar, quyosh atrofida nur.
    Quyosh yo'nalishi gen_godot5.SUN_ROT bilan bir xil: g'arb (−X), 50° balandlik."""
    W, Hh = 2048, 1024
    v, u = np.mgrid[0:Hh, 0:W]
    theta = v / Hh * np.pi                      # 0 — zenit
    phi = u / W * 2 * np.pi                     # Godot: atan(x, −z)
    d = np.stack([np.sin(theta) * np.sin(phi), np.cos(theta), -np.sin(theta) * np.cos(phi)], -1)
    el = np.clip(d[..., 1], -1, 1)
    top, hor = np.array([0.24, 0.45, 0.76]), np.array([0.86, 0.82, 0.72])
    t = np.clip(el, 0, 1) ** 0.45
    col = hor[None, None] * (1 - t[..., None]) + top[None, None] * t[..., None]
    ground = np.array([0.52, 0.44, 0.33])
    g = np.clip(-el * 6, 0, 1)[..., None]
    col = col * (1 - g) + ground[None, None] * g
    sun = np.array([-0.641, 0.766, 0.045]); sun /= np.linalg.norm(sun)
    cs = np.clip((d * sun).sum(-1), -1, 1)
    glow = np.exp((cs - 1) * 60) * 0.5 + np.exp((cs - 1) * 8) * 0.18
    col = col + glow[..., None] * np.array([1.0, 0.9, 0.7])[None, None]
    # bulutlar: tekislikka proyeksiya (ufqqa yaqin siqiladi)
    cl = fbm(950, 5, 6, n=1024)
    cl = np.array(Image.fromarray((cl * 255).astype(np.uint8)).resize((W, Hh), Image.BICUBIC)) / 255.0
    cl2 = fbm(951, 3, 3, n=1024)
    cl2 = np.array(Image.fromarray((cl2 * 255).astype(np.uint8)).resize((W, Hh), Image.BICUBIC)) / 255.0
    dens = np.clip((cl * 0.7 + cl2 * 0.5 - 0.5) * 2.6, 0, 1)
    band = np.clip((el - 0.02) * 3, 0, 1) ** 2 * np.clip((0.85 - el) * 3, 0, 1)
    dens = dens * band
    shade = 0.78 + 0.22 * np.clip((cl - 0.45) * 3, 0, 1)
    cloud = np.array([1.0, 0.97, 0.92])[None, None] * shade[..., None] + glow[..., None] * 0.4
    col = col * (1 - dens[..., None] * 0.85) + cloud * dens[..., None] * 0.85
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(f"{OUT}/sky.png")


if __name__ == "__main__":
    tex5 = os.path.join(HERE, "build", "textures")
    import textures5 as T5
    os.makedirs(tex5, exist_ok=True)
    src = T5.all_textures()
    for k in ("tile_blue", "tile_turq", "girih", "majolica", "suzani", "atlas_1", "atlas_2", "carpet", "awning_r", "awning_b", "awning_g"):
        src[k][0].save(os.path.join(tex5, f"{k}.png"))
    masonry("sandstone", 11, [0.80, 0.65, 0.45], 12, (0.12, 0.3), 5)
    masonry("sandstone_dk", 12, [0.66, 0.52, 0.38], 10, (0.15, 0.32), 5, chip=0.8, crack_n=20)
    masonry("brick", 13, [0.62, 0.36, 0.24], 32, (0.07, 0.1), 4, tint_amt=0.14, chip=0.3, crack_n=8, mortar_col=[0.72, 0.66, 0.56], nstr=9)
    masonry("flagstone", 14, [0.72, 0.62, 0.47], 6, (0.18, 0.4), 6, chip=0.6, crack_n=16, rough=0.82)
    plaster("plaster", 15, [0.85, 0.73, 0.55])
    plaster("plaster_w", 16, [0.92, 0.88, 0.8], stains=0.3)
    cobble("cobble", 17)
    wood("beam", 18, [0.36, 0.23, 0.13], 3)
    wood("wood_light", 19, [0.56, 0.4, 0.24], 5)
    wood("crate", 20, [0.64, 0.46, 0.27], 6)
    wood("carved_wood", 21, [0.42, 0.27, 0.16], 3, nails=False)
    wood("vassa", 22, [0.5, 0.34, 0.19], 32, rough=0.8, nails=False)
    roof("roof", 23)
    dome_tiles("dome", 24)
    ganch("ganch", 25)
    for k, sd in (("tile_blue", 26), ("tile_turq", 27), ("girih", 28), ("majolica", 29)):
        tile_from(k, os.path.join(tex5, f"{k}.png"), sd)
    cloth("paxta", 30)
    cloth("cloth", 31, base=(0.8, 0.74, 0.6), rope=False)
    for k, sd in (("suzani", 32), ("atlas_1", 33), ("atlas_2", 34), ("carpet", 35), ("awning_r", 36), ("awning_b", 37), ("awning_g", 38)):
        cloth(k, sd, src=os.path.join(tex5, f"{k}.png"), rope=False)
    grime()
    sky()
    print("HQ teksturalar:", len([f for f in os.listdir(OUT) if f.endswith("_albedo.jpg")]), "material,",
          f"{sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1e6:.1f} MB")
