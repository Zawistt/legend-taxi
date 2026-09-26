"""Stage-4 PBR textures: 1K albedo + ORM + 512 normal, all tileable.
ORM follows the glTF packing: R = occlusion, G = roughness, B = metallic.
Albedo and ORM are written to disk as JPEG so trimesh embeds the JPEG bytes as-is."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

N = 1024
NRM = 512
CACHE = "tex_cache4"
os.makedirs(CACHE, exist_ok=True)


# ---------------------------------------------------------------- noise helpers
def wrap_noise(shape, cells, seed):
    rng = np.random.default_rng(seed)
    cy, cx = cells if isinstance(cells, tuple) else (cells, cells)
    g = rng.random((cy, cx))
    z = ndimage.zoom(g, (shape[0] / cy, shape[1] / cx), order=3, mode="grid-wrap")
    return z[: shape[0], : shape[1]]


def fbm(seed, base=4, octaves=6, shape=(N, N), aniso=(1, 1)):
    out = np.zeros(shape)
    amp, tot, c = 1.0, 0.0, base
    for o in range(octaves):
        cy = max(2, min(shape[0], int(c * aniso[0])))
        cx = max(2, min(shape[1], int(c * aniso[1])))
        out += amp * wrap_noise(shape, (cy, cx), seed + o * 17)
        tot += amp
        amp *= 0.55
        c *= 2
    return out / tot


def worley(seed, cells, shape=(N, N)):
    """Tileable cellular noise -> (normalised distance to nearest site, per-cell id)."""
    rng = np.random.default_rng(seed)
    pts = rng.random((cells * cells, 2)) * cells
    ids = rng.random(cells * cells)
    y, x = np.mgrid[0:shape[0], 0:shape[1]]
    uy, ux = y / shape[0] * cells, x / shape[1] * cells
    best = np.full(shape, 1e9)
    bid = np.zeros(shape)
    for oy in (-cells, 0, cells):
        for ox in (-cells, 0, cells):
            for i, p in enumerate(pts):
                d = (uy - (p[0] + oy)) ** 2 + (ux - (p[1] + ox)) ** 2
                m = d < best
                best[m] = d[m]
                bid[m] = ids[i]
    return np.sqrt(best) / cells, bid


def worley2(seed, cells, shape=(N, N)):
    """Tileable cellular noise -> (F1, F2, cell id). F2 - F1 gives clean cell borders."""
    rng = np.random.default_rng(seed)
    pts = rng.random((cells * cells, 2)) * cells
    ids = rng.random(cells * cells)
    y, x = np.mgrid[0:shape[0], 0:shape[1]]
    uy, ux = y / shape[0] * cells, x / shape[1] * cells
    f1 = np.full(shape, 1e9)
    f2 = np.full(shape, 1e9)
    bid = np.zeros(shape)
    for oy in (-cells, 0, cells):
        for ox in (-cells, 0, cells):
            for i, p in enumerate(pts):
                d = np.sqrt((uy - (p[0] + oy)) ** 2 + (ux - (p[1] + ox)) ** 2)
                closer = d < f1
                f2 = np.where(closer, f1, np.minimum(f2, d))
                bid = np.where(closer, ids[i], bid)
                f1 = np.where(closer, d, f1)
    return f1 / cells, f2 / cells, bid


def gauss(a, s):
    return ndimage.gaussian_filter(a, s, mode="wrap")


def norm01(a):
    return (a - a.min()) / (np.ptp(a) + 1e-9)


# ---------------------------------------------------------------- map writers
def normal_map(h, strength=3.0):
    hs = np.asarray(Image.fromarray((norm01(h) * 255).astype(np.uint8)).resize((NRM, NRM), Image.LANCZOS), float) / 255
    dx = (np.roll(hs, -1, 1) - np.roll(hs, 1, 1)) * strength
    dy = (np.roll(hs, -1, 0) - np.roll(hs, 1, 0)) * strength
    nz = np.ones_like(hs)
    l = np.sqrt(dx * dx + dy * dy + nz * nz)
    n = np.stack([-dx / l, dy / l, nz / l], -1)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8), "RGB")


def orm_map(ao, rough, metal=0.0):
    if np.isscalar(rough):
        rough = np.full((N, N), rough)
    if np.isscalar(metal):
        metal = np.full((N, N), metal)
    a = np.stack([np.clip(ao, 0, 1), np.clip(rough, 0, 1), np.clip(metal, 0, 1)], -1)
    return Image.fromarray((a * 255).astype(np.uint8), "RGB")


def ao_from_height(h, radius=9, depth=1.0):
    """Cavity AO: darken wherever a pixel sits below its local neighbourhood."""
    lo = gauss(h, radius)
    return np.clip(1.0 - depth * np.clip(lo - h, 0, None) / (np.ptp(h) + 1e-9) * 3.0, 0, 1)


def rgb(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGB")


def jpg(img, name, q=88):
    p = f"{CACHE}/{name}.jpg"
    img.save(p, quality=q, subsampling=0)
    return Image.open(p)


def png(img, name):
    p = f"{CACHE}/{name}.png"
    img.save(p)
    return Image.open(p)


def block_pattern(bw, bh, mortar, seed, offset=True, jitter=0.35):
    """Per-pixel block tint, edge distance, mortar mask and per-block height offset."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N]
    row = y // bh
    xo = (x + (row % 2) * (bw // 2 if offset else 0)) % N
    col = xo // bw
    nr, nc = N // bh, N // bw
    tint = rng.normal(0, 1, (nr, nc))[row % nr, col % nc]
    bump = rng.normal(0, jitter, (nr, nc))[row % nr, col % nc]
    ex = np.minimum(xo % bw, bw - 1 - xo % bw)
    ey = np.minimum(y % bh, bh - 1 - y % bh)
    return tint, np.minimum(ex, ey).astype(float), (np.minimum(ex, ey) < mortar), bump


def grit(seed, scale=64):
    return fbm(seed, scale, 3)


# ---------------------------------------------------------------- materials
def sandstone(variant=0):
    bw, bh = [(256, 128), (170, 128)][variant]
    base = [np.array([0.80, 0.645, 0.44]), np.array([0.755, 0.63, 0.475])][variant]
    t, e, m, bump = block_pattern(bw, bh, 6, 101 + variant * 31)
    n1, n2 = fbm(10 + variant, 6), grit(20 + variant)
    pit, _ = worley(40 + variant, 26)
    pits = np.clip(1 - pit * 7, 0, 1) ** 2
    edge = np.clip(e / 20.0, 0, 1)
    chip = (fbm(60 + variant, 24, 3) > 0.63) & (edge < 0.35)

    h = edge * 0.55 + bump * 0.12 + n2 * 0.16 + n1 * 0.1 - pits * 0.3 - chip * 0.25
    h[m] = -0.25 + n2[m] * 0.1
    h = gauss(h, 1.2)

    shade = (1 + 0.115 * t + 0.05 * bump + 0.26 * (n1 - 0.5) + 0.16 * (n2 - 0.5)) * (0.86 + 0.14 * edge)
    a = base[None, None] * shade[..., None]
    a[chip] *= 1.12
    warm = np.clip(fbm(90 + variant, 2, 3) - 0.5, -0.5, 0.5)          # large warm/cool blotches
    a[..., 0] *= 1 + 0.12 * warm
    a[..., 2] *= 1 - 0.14 * warm
    a[m] = base[None, None] * (0.6 + 0.12 * n2[m])[..., None]
    streak = np.clip(fbm(80 + variant, 3, 4, aniso=(6, 0.4)) - 0.55, 0, 1) * 1.6
    a *= (1 - 0.2 * streak)[..., None]

    ao = ao_from_height(h, 11, 1.2) * (1 - 0.28 * m) * (1 - 0.3 * pits)
    rough = 0.78 + 0.14 * n2 + 0.06 * pits
    rough[m] = 0.95
    return dict(albedo=a, height=h, ao=ao, rough=rough, strength=3.2)


def plaster(variant=0):
    base = [np.array([0.87, 0.755, 0.57]), np.array([0.825, 0.735, 0.60])][variant]
    n1, n2 = fbm(150 + variant, 3), fbm(160 + variant, 40, 4)
    trowel = fbm(170 + variant, 8, 3, aniso=(0.4, 3))
    crack, _ = worley(180 + variant, 7)
    cr = np.clip(1 - np.abs(crack - 0.36) * 34, 0, 1) * (fbm(190 + variant, 6, 3) > 0.45)
    spall = gauss((fbm(200 + variant, 4, 4) > 0.80).astype(float), 3) > 0.62
    stain = np.clip((fbm(210 + variant, 2, 4) - 0.54) * 2.6, 0, 1)

    h = gauss(n2 * 0.25 + trowel * 0.2 + n1 * 0.15 - cr * 0.5 - spall * 0.18, 1.6)
    wash = np.clip(fbm(215 + variant, 2, 3) - 0.5, -0.5, 0.5)
    a = base[None, None] * (1 + 0.2 * (n1 - 0.5) + 0.1 * (n2 - 0.5) + 0.08 * (trowel - 0.5) - 0.22 * stain)[..., None]
    a[..., 0] *= 1 + 0.10 * wash
    a[..., 2] *= 1 - 0.12 * wash
    under = np.array([0.80, 0.685, 0.52]) * (0.92 + 0.16 * n2[spall])[..., None]  # stone showing through
    a[spall] = a[spall] * 0.45 + under * 0.55                                     # blend, not a hard patch
    a *= (1 - 0.35 * cr)[..., None]
    ao = ao_from_height(h, 9, 1.0) * (1 - 0.45 * cr) * (1 - 0.15 * spall)
    return dict(albedo=a, height=h, ao=ao, rough=0.86 + 0.1 * n2 + 0.04 * spall, strength=2.2)


def flagstone():
    f1, f2, cid = worley2(300, 7)
    border = f2 - f1                              # 0 at the joint, rises into the slab
    joint = border < 0.0035                       # ~8% of the surface is mortar
    edge = np.clip((border - 0.0035) / 0.02, 0, 1)   # bevel around each slab
    n1, n2 = fbm(310, 5), grit(320)
    wear = fbm(330, 3, 4)
    sand = np.clip((fbm(340, 5, 4) - 0.40) * 2.4, 0, 1) * (1 - edge * 0.5)
    base = np.array([0.845, 0.715, 0.515])
    shade = (1 + 0.1 * (cid - 0.5) + 0.18 * (n1 - 0.5) + 0.12 * (n2 - 0.5)) * (0.86 + 0.14 * edge)
    a = base[None, None] * shade[..., None]
    a = a * (1 - sand * 0.62)[..., None] + np.array([0.875, 0.775, 0.575])[None, None] * (sand * 0.62)[..., None]
    a[joint] = np.array([0.655, 0.555, 0.415]) * (0.9 + 0.26 * n2[joint])[..., None]
    h = gauss(edge * 0.62 + n2 * 0.18 + (cid - 0.5) * 0.12 - joint * 0.45, 1.3)
    ao = ao_from_height(h, 10, 0.85) * (1 - 0.25 * joint)
    rough = 0.90 + 0.08 * n2 + 0.05 * sand - 0.05 * wear
    rough[joint] = 0.97
    return dict(albedo=a, height=h, ao=ao, rough=rough, strength=3.0)


def wood(seed=400, base=(0.42, 0.28, 0.16), planks=4, rough_base=0.72):
    g = fbm(seed, 6, 5, aniso=(9, 0.5))
    g2 = fbm(seed + 5, 18, 3, aniso=(7, 0.5))
    y, x = np.mgrid[0:N, 0:N]
    pw = N // planks
    pid = x // pw
    rng = np.random.default_rng(seed)
    tint = rng.normal(0, 1, planks + 1)[pid]
    warp = rng.normal(0, 1, planks + 1)[pid]
    gap = (x % pw) < max(3, N // 180)
    rings = 0.5 + 0.5 * np.sin(g * 44 + warp * 0.6)
    knot, kid = worley(seed + 9, 5)
    kn = (np.clip(1 - knot * 9, 0, 1) ** 2) * (kid > 0.72)
    a = np.array(base)[None, None] * (1 + 0.1 * tint + 0.26 * (rings - 0.5) + 0.18 * (g2 - 0.5) - 0.45 * kn)[..., None]
    a[gap] *= 0.3
    h = rings * 0.3 + g2 * 0.28 - kn * 0.3
    h[gap] = -0.4
    h = gauss(h, 1.0)
    ao = ao_from_height(h, 8, 0.9) * (1 - 0.5 * gap)
    return dict(albedo=a, height=h, ao=ao, rough=rough_base + 0.18 * g2 - 0.1 * rings, strength=2.0)


def crate():
    d = wood(420, (0.68, 0.49, 0.29), 5, 0.68)
    a = np.rot90(d["albedo"]).copy()
    y, x = np.mgrid[0:N, 0:N]
    b = N // 10
    frame = (x < b) | (x > N - b) | (y < b) | (y > N - b)
    fr = frame | (np.abs(x - y) < N // 15)
    edge = (np.abs(x - b) < 4) | (np.abs(x - (N - b)) < 4) | (np.abs(y - b) < 4) | (np.abs(y - (N - b)) < 4)
    edge |= (np.abs(np.abs(x - y) - N // 15) < 4) & ~frame
    a[fr] *= 0.82
    a[edge] *= 0.45
    h = np.where(fr, 0.85, 0.35)
    h[edge] = 0.1
    metal = np.zeros((N, N))
    for cxp in (b // 2, N - b // 2):
        for cyp in (b // 2, N - b // 2, N // 2):
            for mm in ((x - cxp) ** 2 + (y - cyp) ** 2 < (N // 42) ** 2, (y - cxp) ** 2 + (x - cyp) ** 2 < (N // 42) ** 2):
                a[mm] = [0.34, 0.31, 0.29]
                metal[mm] = 0.9
                h[mm] = 1.0
    dirt = fbm(430, 3)
    a *= (0.84 + 0.32 * dirt)[..., None]
    h = gauss(h, 2.0)
    return dict(albedo=a, height=h, ao=ao_from_height(h, 12, 1.0) * (1 - 0.25 * edge),
                rough=np.clip(0.7 + 0.2 * dirt - 0.35 * metal, 0, 1), metal=metal * 0.85, strength=2.4)


def green_crate():
    y, x = np.mgrid[0:N, 0:N]
    n1, n2 = fbm(440, 4), grit(450)
    base = np.array([0.255, 0.335, 0.235])
    rib = (x % (N // 8)) < N // 50
    b = N // 12
    frame = (x < b) | (x > N - b) | (y < b) | (y > N - b)
    scratch = np.clip(fbm(460, 20, 3, aniso=(0.3, 7)) - 0.62, 0, 1) * 3
    wear = ((fbm(470, 14, 4) > 0.66) & frame) | (scratch > 0.4)
    rust = (fbm(480, 9, 4) > 0.66) & frame
    shade = (1 + 0.18 * (n1 - 0.5) + 0.1 * (n2 - 0.5)) * np.where(rib & ~frame, 0.86, 1.0) * np.where(frame, 0.82, 1.0)
    a = base[None, None] * shade[..., None]
    a[wear] = [0.47, 0.45, 0.42]
    a[rust] = [0.42, 0.24, 0.14]
    h = gauss(np.where(frame, 1.0, 0.45) + np.where(rib, 0.25, 0) - rust * 0.2, 2.0)
    return dict(albedo=a, height=h, ao=ao_from_height(h, 11, 1.0),
                rough=np.clip(0.42 + 0.3 * n2 + 0.35 * rust - 0.15 * wear, 0, 1),
                metal=np.where(wear, 0.9, 0.35) * (1 - rust * 0.8), strength=2.6)


def roof_tiles():
    y, x = np.mgrid[0:N, 0:N]
    th = tw = N // 8
    row = y // th
    xo = (x + (row % 2) * (tw // 2)) % N
    lx = (xo % tw) / tw - 0.5
    ly = (y % th) / th
    curve = np.sqrt(np.clip(1 - (2 * lx) ** 2, 0, 1))
    n1, n2 = fbm(490, 6), grit(500)
    rng = np.random.default_rng(5)
    nr, nc = N // th, N // tw
    tint = rng.normal(0, 1, (nr, nc))[row % nr, (xo // tw) % nc]
    moss = np.clip((fbm(510, 7, 4) - 0.6) * 3, 0, 1) * (1 - curve * 0.6)
    shade = (0.62 + 0.4 * curve) * (0.76 + 0.24 * ly) * (1 + 0.09 * tint + 0.2 * (n1 - 0.5))
    a = np.array([0.66, 0.355, 0.215])[None, None] * shade[..., None]
    a = a * (1 - moss * 0.7)[..., None] + np.array([0.36, 0.38, 0.24])[None, None] * (moss * 0.7)[..., None]
    h = gauss(curve * 0.72 + ly * 0.25 + n2 * 0.08, 1.2)
    return dict(albedo=a, height=h, ao=ao_from_height(h, 10, 1.1) * (0.72 + 0.28 * curve),
                rough=0.74 + 0.16 * n2 + 0.1 * moss, strength=3.2)


def door():
    d = wood(520, (0.30, 0.18, 0.105), 6, 0.62)
    a, h, rough = d["albedo"].copy(), d["height"].copy(), d["rough"].copy()
    y, x = np.mgrid[0:N, 0:N]
    metal = np.zeros((N, N))
    for by in (int(N * 0.14), int(N * 0.5), int(N * 0.86)):
        band = np.abs(y - by) < N // 36
        a[band] = [0.17, 0.155, 0.145]
        metal[band] = 0.9
        h[band] = 0.85
        for sx in range(N // 12, N, N // 6):
            m2 = (x - sx) ** 2 + (y - by) ** 2 < (N // 60) ** 2
            a[m2] = [0.38, 0.35, 0.32]
            h[m2] = 1.0
    rr = (x - N // 2) ** 2 + (y - int(N * 0.62)) ** 2
    ring = (rr < (N // 12) ** 2) & (rr > (N // 17) ** 2)
    a[ring] = [0.55, 0.42, 0.18]
    metal[ring] = 1.0
    h[ring] = 1.0
    h = gauss(h, 1.4)
    return dict(albedo=a, height=h, ao=ao_from_height(h, 10, 1.0),
                rough=np.clip(rough - 0.25 * metal, 0, 1), metal=metal * 0.9, strength=2.4)


def bark():
    n = fbm(530, 14, 4, aniso=(0.5, 3))
    ring = 0.5 + 0.5 * np.sin(np.mgrid[0:N, 0:N][0] / N * np.pi * 2 * 16 + n * 1.4)
    fib = fbm(540, 30, 3, aniso=(0.3, 6))
    a = np.array([0.50, 0.41, 0.29])[None, None] * (0.78 + 0.34 * ring + 0.12 * (fib - 0.5))[..., None]
    h = gauss(ring * 0.7 + fib * 0.2, 1.2)
    return dict(albedo=a, height=h, ao=ao_from_height(h, 9, 0.7), rough=0.86 + 0.12 * fib, strength=1.6)


def cloth_sack():
    y, x = np.mgrid[0:N, 0:N]
    weave = 0.5 + 0.25 * np.sin(x / N * np.pi * 2 * 90) + 0.25 * np.sin(y / N * np.pi * 2 * 90)
    n1, n2 = fbm(550, 4), grit(560, 40)
    dirt = np.clip((fbm(570, 3, 4) - 0.48) * 2, 0, 1)
    a = np.array([0.72, 0.635, 0.46])[None, None] * (1 + 0.2 * (n1 - 0.5) + 0.1 * (weave - 0.5) - 0.3 * dirt)[..., None]
    h = gauss(weave * 0.35 + n2 * 0.3 + n1 * 0.25, 2.2)
    return dict(albedo=a, height=h, ao=ao_from_height(h, 9, 1.0), rough=np.full((N, N), 0.94), strength=2.2)


def clay():
    n1, n2 = fbm(580, 4), grit(590)
    throw = 0.5 + 0.5 * np.sin(np.mgrid[0:N, 0:N][0] / N * np.pi * 2 * 26 + fbm(600, 4) * 2)
    a = np.array([0.80, 0.47, 0.32])[None, None] * (0.86 + 0.24 * (n1 - 0.5) + 0.12 * (throw - 0.5))[..., None]
    h = gauss(throw * 0.3 + n2 * 0.25, 2.0)
    return dict(albedo=a, height=h, ao=ao_from_height(h, 8, 0.8), rough=np.clip(0.55 + 0.25 * gauss(n2, 3), 0, 1), strength=1.8)


# ---------------------------------------------------------------- decals (RGBA)
def grime_decal():
    """Dark grime fading upward — sits along the bottom of walls."""
    im = np.zeros((N, N, 4))
    y = np.mgrid[0:N, 0:N][0] / N
    drip = fbm(610, 7, 4, aniso=(0.25, 5))
    splash = fbm(620, 4, 4)
    up = np.clip((y - 0.12) / 0.7, 0, 1)
    al = np.clip((1 - up) ** 2.3 * (0.42 + 0.6 * splash) + np.clip(drip - 0.55, 0, 1) * 1.7 * (1 - up) ** 1.2, 0, 1) * 0.62
    tint = 0.45 + 0.25 * splash
    im[..., 0], im[..., 1], im[..., 2], im[..., 3] = 0.30 * tint, 0.25 * tint, 0.19 * tint, al
    return Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8), "RGBA")


def sand_decal():
    """Wind-blown sand piled against wall bases."""
    im = np.zeros((N, N, 4))
    y = np.mgrid[0:N, 0:N][0] / N
    dune = fbm(630, 5, 4, aniso=(0.5, 3))
    grain = grit(640, 90)
    al = np.clip((1 - np.clip(y / 0.5, 0, 1)) ** 1.7 * (0.45 + 1.15 * dune), 0, 1) * (0.85 + 0.15 * grain) * 0.95
    im[..., 0], im[..., 1], im[..., 2] = 0.865 + 0.07 * grain, 0.765 + 0.07 * grain, 0.565 + 0.07 * grain
    im[..., 3] = al
    return Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8), "RGBA")


def stain_decal():
    """Water stains and soot for upper walls."""
    im = np.zeros((N, N, 4))
    y = np.mgrid[0:N, 0:N][0] / N
    blob = fbm(650, 3, 5)
    streak = fbm(653, 9, 4, aniso=(0.18, 6))
    al = np.clip((blob - 0.5) * 2.6, 0, 1) * np.clip(1 - np.abs(y - 0.5) * 1.9, 0, 1)
    al = np.clip(al + np.clip(streak - 0.62, 0, 1) * 1.8 * np.clip(1 - y * 1.2, 0, 1), 0, 1) * 0.5
    im[..., 0], im[..., 1], im[..., 2], im[..., 3] = 0.36, 0.31, 0.26, al
    return Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8), "RGBA")


def site_decal(letter):
    s = 512
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    red = (172, 32, 22, 240)
    d.ellipse([28, 28, s - 28, s - 28], outline=red, width=36)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 300)
    except Exception:
        f = ImageFont.load_default()
    bb = d.textbbox((0, 0), letter, font=f)
    d.text(((s - (bb[2] - bb[0])) / 2 - bb[0], (s - (bb[3] - bb[1])) / 2 - bb[1]), letter, fill=red, font=f)
    a = np.asarray(im).astype(float)
    g = fbm(660 + ord(letter), 18, 4, shape=(s, s))
    scuff = fbm(670 + ord(letter), 7, 3, shape=(s, s))
    a[..., 3] *= np.clip((g - 0.22) * 2.4, 0, 1) * np.clip(scuff * 1.6, 0, 1)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def frond():
    w, h = 256, 512
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(7)
    cxp = w // 2
    for i in range(0, h - 10, 9):
        t = i / h
        Lf = (1 - t) ** 0.6 * (w * 0.48) * (0.3 + 0.7 * min(1, t * 6))
        for sgn in (-1, 1):
            g = int(80 + rng.integers(-15, 25))
            col = (int(40 + 30 * t), g + int(40 * (1 - t)), int(25 + 10 * t), 255)
            d.polygon([(cxp, h - i), (cxp + sgn * Lf, h - i - 30), (cxp + sgn * Lf * 0.9, h - i - 36), (cxp, h - i - 7)], fill=col)
    d.line([(cxp, h), (cxp, 0)], fill=(95, 90, 45, 255), width=6)
    return im


RECIPES = {
    "sandstone": lambda: sandstone(0), "sandstone2": lambda: sandstone(1),
    "plaster": lambda: plaster(0), "plaster2": lambda: plaster(1),
    "flagstone": flagstone,
    "beam": lambda: wood(410, (0.36, 0.23, 0.13), 3, 0.75),
    "crate": crate, "green": green_crate, "roof": roof_tiles, "door": door,
    "bark": bark, "cloth": cloth_sack, "clay": clay,
}


def build(name):
    d = RECIPES[name]()
    return {
        "albedo": jpg(rgb(d["albedo"]), f"{name}_a"),
        "normal": jpg(normal_map(d["height"], d.get("strength", 3.0)), f"{name}_n", q=94),
        "orm": jpg(orm_map(d["ao"], d["rough"], d.get("metal", 0.0)), f"{name}_orm"),
    }


def all_textures(names=None):
    return {n: build(n) for n in (names or RECIPES)}
