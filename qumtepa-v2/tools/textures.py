import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

N = 512


def wrap_noise(shape, cells, seed):
    rng = np.random.default_rng(seed)
    cy, cx = cells if isinstance(cells, tuple) else (cells, cells)
    g = rng.random((cy, cx))
    z = ndimage.zoom(g, (shape[0] / cy, shape[1] / cx), order=3, mode="grid-wrap")
    return z[: shape[0], : shape[1]]


def fbm(seed, base=4, octaves=6, shape=(N, N), aniso=(1, 1)):
    out = np.zeros(shape)
    amp, tot = 1.0, 0.0
    c = base
    for o in range(octaves):
        cy = max(2, min(shape[0], int(c * aniso[0])))
        cx = max(2, min(shape[1], int(c * aniso[1])))
        out += amp * wrap_noise(shape, (cy, cx), seed + o * 17)
        tot += amp
        amp *= 0.55
        c *= 2
    return out / tot


def normal_from_height(h, strength=4.0):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nz = np.ones_like(h)
    l = np.sqrt(dx * dx + dy * dy + nz * nz)
    n = np.stack([-dx / l, dy / l, nz / l], -1)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8), "RGB")


def to_img(rgb):
    return Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), "RGB")


def block_pattern(bw, bh, mortar, seed, offset=True, jitter=0.0):
    """Returns per-pixel block id tint, edge distance, mortar mask (tileable)."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N]
    row = y // bh
    xo = (x + (row % 2) * (bw // 2 if offset else 0)) % N
    col = xo // bw
    nrows, ncols = N // bh, N // bw
    tint = rng.normal(0, 1, (nrows, ncols))
    t = tint[row % nrows, col % ncols]
    ex = np.minimum(xo % bw, bw - 1 - xo % bw)
    ey = np.minimum(y % bh, bh - 1 - y % bh)
    e = np.minimum(ex, ey).astype(float)
    return t, e, (e < mortar)


def sandstone():
    t, e, m = block_pattern(128, 64, 3, 1)
    n1 = fbm(10, 6)
    n2 = fbm(20, 32, 4)
    edge = np.clip(e / 10.0, 0, 1)
    base = np.array([0.80, 0.64, 0.43])
    shade = 1 + 0.07 * t + 0.28 * (n1 - 0.5) + 0.18 * (n2 - 0.5)
    shade *= 0.80 + 0.20 * edge
    rgb = base[None, None] * shade[..., None]
    rgb[..., 2] *= 1 + 0.08 * (n1 - 0.5)
    rgb[m] = rgb[m] * 0.62
    h = edge * 0.6 + n2 * 0.3 + n1 * 0.2
    h[m] = 0
    return to_img(rgb), normal_from_height(ndimage.gaussian_filter(h, 1, mode="wrap"), 3)


def flagstone():
    t, e, m = block_pattern(128, 128, 3, 2)
    t2, e2, m2 = block_pattern(64, 64, 2, 3, offset=False)
    n1 = fbm(30, 5)
    n2 = fbm(40, 48, 3)
    edge = np.clip(e / 12.0, 0, 1)
    base = np.array([0.74, 0.62, 0.45])
    shade = (1 + 0.08 * t + 0.25 * (n1 - 0.5) + 0.15 * (n2 - 0.5)) * (0.84 + 0.16 * edge)
    rgb = base[None, None] * shade[..., None]
    rgb[m] *= 0.55
    h = edge * 0.5 + n2 * 0.4
    h[m] = 0
    return to_img(rgb), normal_from_height(ndimage.gaussian_filter(h, 1, mode="wrap"), 3)


def plaster():
    n1 = fbm(50, 3)
    n2 = fbm(60, 24, 5)
    stain = np.clip((fbm(70, 2, 4) - 0.55) * 3, 0, 1)
    base = np.array([0.86, 0.74, 0.55])
    shade = 1 + 0.18 * (n1 - 0.5) + 0.12 * (n2 - 0.5) - 0.18 * stain
    rgb = base[None, None] * shade[..., None]
    return to_img(rgb), normal_from_height(n2 * 0.5, 2)


def wood(seed=80, base=(0.42, 0.28, 0.16), planks=4, horizontal=False):
    g = fbm(seed, 6, 5, aniso=(8, 0.5))
    g2 = fbm(seed + 5, 16, 3, aniso=(6, 0.5))
    y, x = np.mgrid[0:N, 0:N]
    pw = N // planks
    pid = x // pw
    rng = np.random.default_rng(seed)
    tint = rng.normal(0, 1, planks + 1)[pid]
    gap = (x % pw) < 3
    rings = 0.5 + 0.5 * np.sin(g * 40)
    shade = 1 + 0.1 * tint + 0.25 * (rings - 0.5) + 0.2 * (g2 - 0.5)
    rgb = np.array(base)[None, None] * shade[..., None]
    rgb[gap] *= 0.35
    h = rings * 0.3 + g2 * 0.3
    h[gap] = 0
    img, nrm = to_img(rgb), normal_from_height(h, 2)
    if horizontal:
        img, nrm = img.rotate(90), nrm.rotate(90)
    return img, nrm


def crate():
    img, nrm = wood(90, (0.66, 0.47, 0.27), 5, horizontal=True)
    a = np.asarray(img).astype(float) / 255
    y, x = np.mgrid[0:N, 0:N]
    b = 52
    frame = (x < b) | (x > N - b) | (y < b) | (y > N - b)
    diag = np.abs((x - y)) < 34
    fr = frame | diag
    a[fr] *= 0.78
    edge = (np.abs(x - b) < 3) | (np.abs(x - (N - b)) < 3) | (np.abs(y - b) < 3) | (np.abs(y - (N - b)) < 3)
    edge |= (np.abs(np.abs(x - y) - 34) < 3) & ~frame
    a[edge] *= 0.45
    for cx in (26, N - 26):
        for cy in (26, N - 26, N // 2):
            m = (x - cx) ** 2 + (y - cy) ** 2 < 36
            a[m] = [0.25, 0.23, 0.22]
            m = (y - cx) ** 2 + (x - cy) ** 2 < 36
            a[m] = [0.25, 0.23, 0.22]
    dirt = fbm(95, 3)
    a *= (0.85 + 0.3 * dirt)[..., None]
    h = np.where(fr, 0.8, 0.4)
    h[edge] = 0
    return to_img(a), normal_from_height(ndimage.gaussian_filter(h, 2), 2)


def green_crate():
    y, x = np.mgrid[0:N, 0:N]
    n1 = fbm(100, 4)
    n2 = fbm(110, 64, 3)
    base = np.array([0.27, 0.36, 0.25])
    rib = (x % 64) < 10
    b = 40
    frame = (x < b) | (x > N - b) | (y < b) | (y > N - b)
    shade = 1 + 0.2 * (n1 - 0.5) + 0.1 * (n2 - 0.5)
    shade = shade * np.where(rib & ~frame, 0.85, 1.0) * np.where(frame, 0.8, 1.0)
    rgb = base[None, None] * shade[..., None]
    wear = (fbm(120, 16, 4) > 0.66) & frame
    rgb[wear] = [0.45, 0.43, 0.40]
    h = np.where(frame, 1.0, 0.5) + np.where(rib, 0.3, 0)
    return to_img(rgb), normal_from_height(ndimage.gaussian_filter(h, 2), 3)


def roof_tiles():
    y, x = np.mgrid[0:N, 0:N]
    th, tw = 64, 64
    row = y // th
    xo = (x + (row % 2) * 32) % N
    lx = (xo % tw) / tw - 0.5
    ly = (y % th) / th
    curve = np.sqrt(np.clip(1 - (2 * lx) ** 2, 0, 1))
    n1 = fbm(130, 6)
    rng = np.random.default_rng(3)
    tint = rng.normal(0, 1, (N // th, N // tw))[row % (N // th), (xo // tw) % (N // tw)]
    shade = (0.6 + 0.4 * curve) * (0.75 + 0.25 * ly) * (1 + 0.08 * tint + 0.2 * (n1 - 0.5))
    rgb = np.array([0.66, 0.36, 0.22])[None, None] * shade[..., None]
    return to_img(rgb), normal_from_height(curve * 0.7 + ly * 0.3, 3)


def door():
    img, nrm = wood(140, (0.30, 0.18, 0.10), 6)
    a = np.asarray(img).astype(float) / 255
    y, x = np.mgrid[0:N, 0:N]
    for by in (70, 250, 430):
        band = np.abs(y - by) < 14
        a[band] = [0.16, 0.15, 0.14]
        for sx in range(40, N, 85):
            m = (x - sx) ** 2 + (y - by) ** 2 < 49
            a[m] = [0.35, 0.33, 0.30]
    return to_img(a), nrm


def bark():
    y, x = np.mgrid[0:N, 0:N]
    n = fbm(150, 8, 4, aniso=(0.5, 4))
    ring = 0.5 + 0.5 * np.sin((y / N) * np.pi * 2 * 10 + n * 4)
    rgb = np.array([0.45, 0.36, 0.25])[None, None] * (0.6 + 0.5 * ring)[..., None]
    return to_img(rgb), normal_from_height(ring, 3)


def site_decal(letter):
    s = 512
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    red = (170, 30, 22, 235)
    d.ellipse([30, 30, s - 30, s - 30], outline=red, width=34)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 300)
    except Exception:
        f = ImageFont.load_default()
    bb = d.textbbox((0, 0), letter, font=f)
    d.text(((s - (bb[2] - bb[0])) / 2 - bb[0], (s - (bb[3] - bb[1])) / 2 - bb[1]), letter, fill=red, font=f)
    a = np.asarray(im).astype(float)
    grunge = fbm(160 + ord(letter), 16, 4, shape=(s, s))
    a[..., 3] *= np.clip((grunge - 0.25) * 2.2, 0, 1)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def frond():
    w, h = 256, 512
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(7)
    cx = w // 2
    for i in range(0, h - 10, 9):
        t = i / h
        L = (1 - t) ** 0.6 * (w * 0.48) * (0.3 + 0.7 * min(1, t * 6))
        for sgn in (-1, 1):
            g = int(80 + rng.integers(-15, 25))
            col = (int(40 + 30 * t), g + int(40 * (1 - t)), int(25 + 10 * t), 255)
            d.polygon([(cx, h - i), (cx + sgn * L, h - i - 30), (cx + sgn * L * 0.9, h - i - 36), (cx, h - i - 7)], fill=col)
    d.line([(cx, h), (cx, 0)], fill=(95, 90, 45, 255), width=6)
    return im


def all_textures():
    return {
        "sandstone": sandstone(),
        "flagstone": flagstone(),
        "plaster": plaster(),
        "beam": wood(80, (0.36, 0.23, 0.13), 3),
        "crate": crate(),
        "green": green_crate(),
        "roof": roof_tiles(),
        "door": door(),
        "bark": bark(),
    }
