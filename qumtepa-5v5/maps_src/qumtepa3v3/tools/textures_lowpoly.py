"""Stylized low-poly look: flat colour palette with a touch of large-scale variation.

Textures stay tiny (128 px) and carry only broad tonal blocks — no grain, no normal maps,
no roughness detail. The silhouette and the flat shading carry the style instead.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

N = 128
CACHE = "tex_cache_lp"
os.makedirs(CACHE, exist_ok=True)


def wrap_noise(shape, cells, seed):
    rng = np.random.default_rng(seed)
    cy, cx = cells if isinstance(cells, tuple) else (cells, cells)
    g = rng.random((cy, cx))
    z = ndimage.zoom(g, (shape[0] / cy, shape[1] / cx), order=1, mode="grid-wrap")
    return z[: shape[0], : shape[1]]


def posterize(a, steps):
    """Quantise into flat bands — the core of the stylized look."""
    return np.floor(a * steps) / (steps - 1)


def rgb(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGB")


def png(img, name):
    p = f"{CACHE}/{name}.png"
    img.save(p)
    return Image.open(p)


def flat(base, seed, steps=4, amount=0.16, cells=6):
    """Solid colour with a few flat tonal patches."""
    n = posterize(wrap_noise((N, N), cells, seed), steps)
    a = np.array(base)[None, None] * (1 - amount / 2 + amount * n)[..., None]
    return a


def bands(base, seed, rows, cols, amount=0.2, jitter=0.5):
    """Blocky masonry: one flat tone per block, no mortar texture — just tone steps."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N]
    bh, bw = N // rows, N // cols
    row = y // bh
    xo = (x + (row % 2) * (bw // 2)) % N
    col = xo // bw
    tone = posterize(rng.random((rows + 1, cols + 1)), 4)[row % rows, col % cols]
    a = np.array(base)[None, None] * (1 - amount / 2 + amount * tone)[..., None]
    # thin darker seam so blocks stay readable at distance
    seam = (y % bh < 1) | (xo % bw < 1)
    a[seam] *= 0.86
    return a


PALETTE = {
    "sandstone": (0.84, 0.69, 0.47),
    "sandstone2": (0.79, 0.65, 0.47),
    "plaster": (0.90, 0.80, 0.63),
    "plaster2": (0.86, 0.77, 0.63),
    "flagstone": (0.78, 0.68, 0.52),
    "beam": (0.42, 0.28, 0.17),
    "crate": (0.72, 0.52, 0.30),
    "green": (0.30, 0.40, 0.27),
    "roof": (0.70, 0.36, 0.24),
    "door": (0.34, 0.21, 0.13),
    "bark": (0.48, 0.38, 0.27),
    "cloth": (0.80, 0.72, 0.55),
    "clay": (0.80, 0.45, 0.30),
}


def build(name):
    p = PALETTE[name]
    if name.startswith("sandstone"):
        a = bands(p, 11, 8, 4, 0.22)
    elif name == "flagstone":
        rng = np.random.default_rng(5)
        y, x = np.mgrid[0:N, 0:N]
        cellsz = N // 5
        cid = (y // cellsz) * 5 + (x // cellsz)
        shift = rng.integers(0, cellsz // 2, 25)[cid % 25]
        cid2 = ((y + shift) // cellsz) * 7 + (x // cellsz)
        tone = posterize(rng.random(64), 4)[cid2 % 64]
        a = np.array(p)[None, None] * (0.9 + 0.2 * tone)[..., None]
        seam = ((y + shift) % cellsz < 1) | (x % cellsz < 1)
        a[seam] *= 0.84
    elif name.startswith("plaster"):
        a = flat(p, 21, 3, 0.12, 4)
    elif name in ("beam", "door", "bark"):
        y, x = np.mgrid[0:N, 0:N]
        rng = np.random.default_rng(31 + len(name))
        planks = 4 if name != "bark" else 6
        pw = N // planks
        idx = (x // pw) if name != "bark" else (y // (N // 8))
        tone = posterize(rng.random(planks + 8), 3)[idx % (planks + 8)]
        a = np.array(p)[None, None] * (0.88 + 0.24 * tone)[..., None]
        gap = (x % pw < 1) if name != "bark" else (y % (N // 8) < 1)
        a[gap] *= 0.8
    elif name in ("crate", "green"):
        y, x = np.mgrid[0:N, 0:N]
        b = N // 9
        frame = (x < b) | (x > N - b) | (y < b) | (y > N - b) | (np.abs(x - y) < N // 14)
        a = np.array(p)[None, None] * np.ones((N, N, 1))
        a[frame] *= 0.84
    elif name == "roof":
        y, x = np.mgrid[0:N, 0:N]
        th = N // 6
        row = y // th
        xo = (x + (row % 2) * (th // 2)) % N
        step = posterize((y % th) / th, 3)
        a = np.array(p)[None, None] * (0.82 + 0.3 * step)[..., None]
        a[(xo % th) < 1] *= 0.8
    else:
        a = flat(p, 41, 3, 0.12, 5)
    return {"albedo": png(rgb(a), name)}


def all_textures(names=None):
    return {n: build(n) for n in (names or PALETTE)}


def site_decal(letter):
    s = 256
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    red = (185, 45, 35, 255)
    d.ellipse([16, 16, s - 16, s - 16], outline=red, width=18)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 150)
    except Exception:
        f = ImageFont.load_default()
    bb = d.textbbox((0, 0), letter, font=f)
    d.text(((s - (bb[2] - bb[0])) / 2 - bb[0], (s - (bb[3] - bb[1])) / 2 - bb[1]), letter, fill=red, font=f)
    return im


def frond():
    """Flat, chunky palm leaf — a few big shapes instead of many thin ones."""
    w, h = 128, 256
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    greens = [(54, 92, 44, 255), (66, 108, 48, 255), (44, 78, 38, 255)]
    for i in range(0, h - 8, 26):
        t = i / h
        L = (1 - t) ** 0.5 * (w * 0.46)
        for sgn in (-1, 1):
            c = greens[(i // 26) % 3]
            d.polygon([(w // 2, h - i), (w // 2 + sgn * L, h - i - 30),
                       (w // 2 + sgn * L * 0.8, h - i - 46), (w // 2, h - i - 18)], fill=c)
    d.line([(w // 2, h), (w // 2, 0)], fill=(80, 78, 40, 255), width=7)
    return im
