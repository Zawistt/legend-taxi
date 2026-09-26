"""Qumtepa 5v5 — 2-bosqich: greybox 3D geometriya.

layout5.py dan xarita modelini (GLB) va to'qnashuv ma'lumotlarini (build/meta5.json) yaratadi.
Greybox: oddiy shakllar, rang bilan kodlangan materiallar va 1 m lik to'r (masofani ko'z bilan baholash uchun).
  - pol: ochiq — qum rang, yopiq yo'lak — to'qroq, site — qizg'ish, T spawn — to'q sariq, CT spawn — ko'kish
  - panalar: to'q jigarrang — ko'rishni to'sadi (≥ 1.7 m), to'q sariq — past (ustidan otiladi)
Mantiq Qumtepa v2 build.py dan olingan (binolar, tomlar, arkalar, platforma zinapoyasi, clip'lar).

Ishga tushirish: cd qumtepa-5v5/tools && python3 build5.py
"""
import json, math, os, sys
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial
from trimesh.visual import TextureVisuals
from PIL import Image, ImageDraw, ImageFont
import layout5 as LY

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_GLB = os.path.join(HERE, "..", "godot", "map", "qumtepa5v5_greybox.glb")
OUT_META = os.path.join(HERE, "build", "meta5.json")
rng = np.random.default_rng(42)
G = LY.G
CS = LY.CELL
OFF = LY.ORIGIN
SIZE = G * CS
grid = LY.grid

FP = []        # harakatni to'sadigan pana izlari (x0, z0, x1, z1)
COL = []       # to'qnashuv qutilari: (sirt, x0, y0, z0, x1, y1, z1)
RAMPS = []     # qavariq rampa to'qnashuvi: (sirt, [nuqtalar])
CLIP_P = []    # o'yinchi uchun ko'rinmas devorlar
CLIP_G = []    # granata uchun ko'rinmas devorlar
FP_PLAT = []   # yuriladigan platformalar
LAMPS = []

OPEN = set(".AB")
COVER = LY.COVER
SLAB = 0.45
EYE_BLOCK = 1.7


def ctype(r, c):
    if r < 0 or c < 0 or r >= G or c >= G:
        return "#"
    return grid[r][c]


def cx(c):
    return OFF + c * CS


def cz(r):
    return OFF + r * CS


# ------------------------------------------------------------------ mesh buferlari
class Buf:
    def __init__(self):
        self.v, self.f, self.uv = [], [], []

    def add(self, verts, faces, uvs):
        base = len(self.v)
        self.v.extend(map(tuple, verts))
        self.uv.extend(map(tuple, uvs))
        self.f.extend([(a + base, b + base, c + base) for a, b, c in faces])


bufs = {}


def B(group, mat):
    return bufs.setdefault((group, mat), Buf())


def quad(group, mat, p, uv, want_n=None):
    p = np.asarray(p, float)
    n = np.cross(p[1] - p[0], p[2] - p[0])
    if want_n is not None and np.dot(n, want_n) < 0:
        p = p[::-1]; uv = uv[::-1]
    B(group, mat).add(p, [(0, 1, 2), (0, 2, 3)], uv)


def box(group, mat, x0, y0, z0, x1, y1, z1, scale=4.0, unit=False, yaw=0.0, top=True, bottom=False):
    """Quti. UV — dunyo koordinatalarida (scale metrda bitta tekstura), shunda 1 m to'r hamma joyda bir xil."""
    xs, ys, zs = (x0, x1), (y0, y1), (z0, z1)
    c = np.array([(x0 + x1) / 2, 0, (z0 + z1) / 2])
    ca, sa = math.cos(yaw), math.sin(yaw)

    def R(p):
        p = np.array(p, float)
        if yaw:
            d = p - c
            p = c + np.array([d[0] * ca - d[2] * sa, d[1], d[0] * sa + d[2] * ca])
        return p

    def rn(n):
        n = np.array(n, float)
        if yaw:
            n = np.array([n[0] * ca - n[2] * sa, n[1], n[0] * sa + n[2] * ca])
        return n

    faces = []
    for sgn, X in ((1, x1), (-1, x0)):
        faces.append(([(X, y0, z0), (X, y0, z1), (X, y1, z1), (X, y1, z0)], (sgn, 0, 0), lambda p: (p[2], p[1]), (zs, ys)))
    for sgn, Z in ((1, z1), (-1, z0)):
        faces.append(([(x0, y0, Z), (x1, y0, Z), (x1, y1, Z), (x0, y1, Z)], (0, 0, sgn), lambda p: (p[0], p[1]), (xs, ys)))
    if top:
        faces.append(([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0), lambda p: (p[0], p[2]), (xs, zs)))
    if bottom:
        faces.append(([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0), lambda p: (p[0], p[2]), (xs, zs)))
    for pts, n, f, (ra, rb) in faces:
        if unit:
            uv = [((f(p)[0] - ra[0]) / (ra[1] - ra[0]), (f(p)[1] - rb[0]) / (rb[1] - rb[0])) for p in pts]
        else:
            uv = [(f(p)[0] / scale, f(p)[1] / scale) for p in pts]
        quad(group, mat, [R(p) for p in pts], uv, rn(n))


def lathe(group, mat, cxp, cyp, czp, prof, seg=16, scale=4.0):
    verts, uvs, faces = [], [], []
    for j, (r, y) in enumerate(prof):
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg
            verts.append((cxp + r * math.cos(a), cyp + y, czp + r * math.sin(a)))
            uvs.append((i / seg * max(1, round(2 * math.pi * max(r, 0.3) / scale)), y / scale))
    W = seg + 1
    for j in range(len(prof) - 1):
        for i in range(seg):
            a, b, c, d = j * W + i, j * W + i + 1, (j + 1) * W + i + 1, (j + 1) * W + i
            faces += [(a, c, b), (a, d, c)]
    B(group, mat).add(verts, faces, uvs)


def arch_wall(group, axis, line, t, a0, a1, y_top, apex, mat="wall", seg=18, col=True):
    """Arkali o'tish joyi bor devor (v2 dan). axis='x': devor x bo'ylab, z=line da."""
    span = a1 - a0
    m = (a0 + a1) / 2
    r = span / 2
    spring = max(2.4, apex - r)
    rise = apex - spring

    def P(s, y, off):
        return (s, y, line + off) if axis == "x" else (line + off, y, s)

    def curve(s):
        k = (s - m) / r
        return spring + rise * math.sqrt(max(0.0, 1 - k * k))

    ss = np.linspace(a0, a1, seg + 1)
    nf = np.array((0, 0, 1)) if axis == "x" else np.array((1, 0, 0))
    for k5 in range(5 if col else 0):
        s0c, s1c = a0 + span * k5 / 5, a0 + span * (k5 + 1) / 5
        yb = curve((s0c + s1c) / 2)
        if axis == "x":
            COL.append(("stone", s0c, yb, line - t / 2, s1c, y_top, line + t / 2))
        else:
            COL.append(("stone", line - t / 2, yb, s0c, line + t / 2, y_top, s1c))
    for i in range(seg):
        s0, s1 = ss[i], ss[i + 1]
        y0, y1 = curve(s0), curve(s1)
        for off, sg in ((t / 2, 1), (-t / 2, -1)):
            pts = [P(s0, y0, off), P(s1, y1, off), P(s1, y_top, off), P(s0, y_top, off)]
            uv = [(s0 / 4, y0 / 4), (s1 / 4, y1 / 4), (s1 / 4, y_top / 4), (s0 / 4, y_top / 4)]
            quad(group, mat, pts, uv, nf * sg)
        pts = [P(s0, y0, -t / 2), P(s1, y1, -t / 2), P(s1, y1, t / 2), P(s0, y0, t / 2)]
        quad(group, mat, pts, [(s0 / 4, 0), (s1 / 4, 0), (s1 / 4, t / 4), (s0 / 4, t / 4)], np.array((0, -1, 0)))
    pts = [P(a0, y_top, -t / 2), P(a1, y_top, -t / 2), P(a1, y_top, t / 2), P(a0, y_top, t / 2)]
    quad(group, mat, pts, [(0, 0), (1, 0), (1, 1), (0, 1)], np.array((0, 1, 0)))


# ------------------------------------------------------------------ pol (bir xil turdagi kataklar to'rtburchaklarga birlashtiriladi)
FLOOR_MAT = {".": "floor_open", "A": "floor_site", "B": "floor_site", ",": "floor_cover", "m": "floor_cover",
             "T": "floor_t", "C": "floor_ct"}
COL.append(("stone", OFF, -0.3, OFF, OFF + SIZE, 0.0, OFF + SIZE))
done = np.zeros((G, G), bool)
for r in range(G):
    for c in range(G):
        t = grid[r][c]
        if t == "#" or done[r, c]:
            continue
        w = 1
        while c + w < G and grid[r][c + w] == t and not done[r, c + w]:
            w += 1
        h = 1
        while r + h < G and all(grid[r + h][c + k] == t and not done[r + h, c + k] for k in range(w)):
            h += 1
        done[r:r + h, c:c + w] = True
        box("Floor-col", FLOOR_MAT[t], cx(c), -0.3, cz(r), cx(c + w), 0.0, cz(r + h))

# ------------------------------------------------------------------ binolar (4x4 katakgacha bloklar, tasodifiy balandlik)
H = np.zeros((G, G))
done = np.zeros((G, G), bool)
nblocks = 0
for r in range(G):
    for c in range(G):
        if grid[r][c] != "#" or done[r, c]:
            continue
        w = 1
        while c + w < G and w < 4 and grid[r][c + w] == "#" and not done[r, c + w]:
            w += 1
        h = 1
        while r + h < G and h < 4 and all(grid[r + h][c + k] == "#" and not done[r + h, c + k] for k in range(w)):
            h += 1
        done[r:r + h, c:c + w] = True
        # hech qanday yuriladigan katakka tegmaydigan ichki bloklar pastroq — ular ko'rinmaydi
        touches = any(ctype(rr, cc) != "#" for rr in range(r - 1, r + h + 1) for cc in range(c - 1, c + w + 1))
        edge = r == 0 or c == 0 or r + h == G or c + w == G
        hh = float(rng.choice([6.5, 7.5, 8.5, 9.5])) + (1.5 if edge else 0.0)
        if not touches:
            hh = 6.0
        H[r:r + h, c:c + w] = hh
        x0, z0, x1, z1 = cx(c), cz(r), cx(c + w), cz(r + h)
        box("Walls-col", "wall" if rng.random() < 0.75 else "wall2", x0, 0, z0, x1, hh, z1)
        COL.append(("stone", x0, 0.0, z0, x1, hh + 0.55, z1))
        p = 0.3   # tom chetidagi devorcha
        for a in ((x0, z0, x1, z0 + p), (x0, z1 - p, x1, z1), (x0, z0, x0 + p, z1), (x1 - p, z0, x1, z1)):
            box("Walls-col", "trim", a[0], hh, a[1], a[2], hh + 0.55, a[3])
        nblocks += 1

# ------------------------------------------------------------------ yopiq yo'laklar: shift, tom, chiroqlar
for r in range(G):
    for c in range(G):
        t = grid[r][c]
        if t in COVER:
            h = COVER[t]
            box("Walls-col", "ceiling", cx(c), h, cz(r), cx(c) + CS, h + SLAB, cz(r) + CS, bottom=True)
            COL.append(("stone", cx(c), h, cz(r), cx(c) + CS, h + SLAB + 0.05, cz(r) + CS))
            CLIP_P.append((cx(c), h + SLAB + 0.05, cz(r), cx(c) + CS, 12.0, cz(r) + CS))
            # devorga osilgan chiroq: har 3-katakda, devor bor tomonda
            if t in ",m" and (r * 7 + c * 3) % 3 == 0:
                for dr, dc in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    if ctype(r + dr, c + dc) == "#":
                        if dc:
                            fx = cx(c + (1 if dc > 0 else 0)); m = cz(r) + 1
                            p = (fx - dc * 0.39, 2.55, m)
                            box("Decor", "lamp", fx - dc * 0.49, 2.4, m - 0.1, fx - dc * 0.29, 2.7, m + 0.1)
                        else:
                            fz = cz(r + (1 if dr > 0 else 0)); m = cx(c) + 1
                            p = (m, 2.55, fz - dr * 0.39)
                            box("Decor", "lamp", m - 0.1, 2.4, fz - dr * 0.49, m + 0.1, 2.7, fz - dr * 0.29)
                        LAMPS.append(p)
                        break

# ------------------------------------------------------------------ hudud chegaralarida arkalar (v2 dan)
runs = {}
for r in range(G):
    for c in range(G):
        a = grid[r][c]
        for dr, dc in ((0, 1), (1, 0)):
            b = ctype(r + dr, c + dc)
            if a == "#" or b == "#" or a == b:
                continue
            ha, hb = COVER.get(a), COVER.get(b)
            if ha is None and hb is None:
                continue
            if ha is not None and hb is not None and ha == hb:
                continue
            key = (dr, dc, r + dr if dr else c + dc, a, b)
            runs.setdefault(key, []).append(c if dr else r)
for (dr, dc, line, a, b), idx in runs.items():
    idx.sort()
    groups, cur = [], [idx[0]]
    for i in idx[1:]:
        if i == cur[-1] + 1:
            cur.append(i)
        else:
            groups.append(cur); cur = [i]
    groups.append(cur)
    hs = [h for h in (COVER.get(a), COVER.get(b)) if h is not None]
    top = max(hs) + SLAB + (0.5 if len(hs) == 1 else 0.0)
    apex = min(hs) - 0.35
    for g in groups:
        g0 = cx(g[0]) if dr else cz(g[0])
        g1 = cx(g[-1] + 1) if dr else cz(g[-1] + 1)
        if dr:
            arch_wall("Walls-col", "x", cz(line), 0.7, g0, g1, top, apex, mat="trim")
        else:
            arch_wall("Walls-col", "z", cx(line), 0.7, g0, g1, top, apex, mat="trim")

# ------------------------------------------------------------------ panalar va obyektlar (layout5.PROPS)


def crate(x, z, s=1.1, y=0.0, yaw=0.0, green=False):
    if y == 0:
        FP.append((x - s / 2, z - s / 2, x + s / 2, z + s / 2))
    COL.append(("metal" if green else "wood", x - s / 2, y, z - s / 2, x + s / 2, y + s, z + s / 2))
    mat = "metal_crate" if green else ("cover_high" if y + s >= EYE_BLOCK else "cover_low")
    box("Props-col", mat, x - s / 2, y, z - s / 2, x + s / 2, y + s, z + s / 2, unit=True, yaw=yaw)


def stack(x, z, pattern, yaw=0.0):
    tall = max(y + s for _dx, _dz, y, s, _g in pattern) >= EYE_BLOCK
    for dx, dz, y, s, g in pattern:
        if y == 0:
            FP.append((x + dx - s / 2, z + dz - s / 2, x + dx + s / 2, z + dz + s / 2))
        COL.append(("metal" if g else "wood", x + dx - s / 2, y, z + dz - s / 2, x + dx + s / 2, y + s, z + dz + s / 2))
        mat = "metal_crate" if g else ("cover_high" if tall else "cover_low")
        box("Props-col", mat, x + dx - s / 2, y, z + dz - s / 2, x + dx + s / 2, y + s, z + dz + s / 2, unit=True, yaw=yaw)


def barrel(x, z):
    FP.append((x - .4, z - .4, x + .4, z + .4))
    COL.append(("wood", x - .4, 0.0, z - .4, x + .4, 0.9, z + .4))
    lathe("Props-col", "cover_low", x, 0, z, [(0.0, 0), (0.36, 0), (0.40, 0.45), (0.36, 0.9), (0.0, 0.9)], 12)


def urn(x, z, s=1.0):
    FP.append((x - .34 * s, z - .34 * s, x + .34 * s, z + .34 * s))
    COL.append(("stone", x - .3 * s, 0.0, z - .3 * s, x + .3 * s, 1.0 * s, z + .3 * s))
    lathe("Props-col", "cover_low", x, 0, z, [(0.0, 0), (0.2 * s, 0), (0.34 * s, 0.45 * s), (0.16 * s, 0.9 * s), (0.12 * s, 1.0 * s), (0.0, 1.0 * s)], 12)


def sandbags(x0, z0, x1, z1):
    b = (min(x0, x1) - .3, min(z0, z1) - .22, max(x0, x1) + .3, max(z0, z1) + .22)
    FP.append((b[0], b[1] - .08, b[2], b[3] + .08))
    COL.append(("cloth", b[0], 0.0, b[1], b[2], 0.78, b[3]))
    box("Props-col", "sandbag", b[0], 0.0, b[1], b[2], 0.78, b[3])


def wall(x0, z0, x1, z1, h):
    COL.append(("stone", x0, 0.0, z0, x1, h, z1))
    CLIP_P.append((x0, h, z0, x1, 12.0, z1))          # tepasiga chiqib bo'lmaydi
    box("Props-col", "ruin", x0, 0.0, z0, x1, h, z1)


def platform(x0, z0, x1, z1, h, stair_dir):
    FP_PLAT.append((x0, z0, x1, z1, h))
    COL.append(("stone", x0, 0.0, z0, x1, h, z1))
    box("Props-col", "platform", x0, 0, z0, x1, h, z1)
    steps = 4
    L = steps * 0.35 + 0.35
    zA, zB = z0 + 0.3, z1 - 0.3
    xa, xb = (x1 + L, x1) if stair_dir == "+x" else (x0 - L, x0)
    RAMPS.append(("stone", [(xb, h, zA), (xb, h, zB), (xa, 0, zB), (xa, 0, zA), (xb, 0, zA), (xb, 0, zB)]))
    for i in range(steps):
        sh = h * (i + 1) / (steps + 1)
        d = (steps - i) * 0.35
        if stair_dir == "+x":
            box("Props-col", "platform", x1, 0, z0 + 0.3, x1 + d, sh, z1 - 0.3)
        else:
            box("Props-col", "platform", x0 - d, 0, z0 + 0.3, x0, sh, z1 - 0.3)


def palm(x, z, h=7.5):
    FP.append((x - .28, z - .28, x + .28, z + .28))
    COL.append(("wood", x - .22, 0.0, z - .22, x + .22, h * 0.9, z + .22))
    lathe("Decor", "trunk", x, 0, z, [(0.26, 0), (0.2, h * 0.5), (0.16, h), (0.0, h)], 8)
    lathe("Decor", "foliage", x, 0, z, [(0.0, h + 0.6), (2.6, h - 0.4), (1.8, h - 1.2), (0.0, h - 0.6)], 10)


def decal(x, z, letter, size=4.4):
    s = size / 2
    quad("Decor", "site" + letter, [(x - s, 0.02, z - s), (x + s, 0.02, z - s), (x + s, 0.02, z + s), (x - s, 0.02, z + s)],
         [(0, 1), (1, 1), (1, 0), (0, 0)], np.array([0, 1, 0]))


for p in LY.PROPS:
    k = p[0]
    if k == "stack":
        stack(p[1], p[2], p[3], p[4])
    elif k == "crate":
        crate(p[1], p[2], p[3], yaw=p[4])
    elif k == "barrel":
        barrel(p[1], p[2])
    elif k == "urn":
        urn(p[1], p[2])
    elif k == "sandbags":
        sandbags(*p[1:])
    elif k == "wall":
        wall(*p[1:])
    elif k == "platform":
        platform(*p[1:])
    elif k == "palm":
        palm(p[1], p[2], p[3])
    elif k == "decal":
        decal(p[1], p[2], p[3])
    else:
        raise ValueError(f"noma'lum obyekt turi: {k}")

# ------------------------------------------------------------------ materiallar: rang + 1 m to'r
def grid_tex(rgb, px_m=64, metres=4, major=True):
    """Tekstura `metres` x `metres` m ni qoplaydi; har 1 m da ingichka, har `metres` m da qalin chiziq."""
    n = px_m * metres
    base = np.ones((n, n, 3)) * np.array(rgb)[None, None]
    noise = np.random.default_rng(int(sum(rgb) * 1000)).normal(0, 0.012, (n, n, 1))
    img = base + noise
    line = 0.82
    for k in range(metres):
        a = k * px_m
        w = 2 if (k == 0 and major) else 1
        img[a:a + w, :, :] *= line
        img[:, a:a + w, :] *= line
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def site_decal(letter):
    s = 512
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    red = (170, 30, 22, 235)
    d.ellipse([30, 30, s - 30, s - 30], outline=red, width=34)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 300)
    except OSError:
        f = ImageFont.load_default()
    bb = d.textbbox((0, 0), letter, font=f)
    d.text(((s - (bb[2] - bb[0])) / 2 - bb[0], (s - (bb[3] - bb[1])) / 2 - bb[1]), letter, fill=red, font=f)
    return im


def crate_tex(rgb):
    n = 256
    img = np.ones((n, n, 3)) * np.array(rgb)[None, None]
    for a in (0, n - 12):          # ramka — qutilar bir-biridan ajralib ko'rinsin
        img[a:a + 12, :, :] *= 0.72
        img[:, a:a + 12, :] *= 0.72
    for k in range(-n, n, 1):      # diagonal taxta
        for t in range(-5, 6):
            i, j = k + t, k
            if 0 <= i < n and 0 <= j < n:
                img[i, j] *= 0.8
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


COLORS = {
    "floor_open": (0.80, 0.71, 0.54), "floor_site": (0.84, 0.62, 0.52), "floor_cover": (0.60, 0.54, 0.45),
    "floor_t": (0.86, 0.66, 0.42), "floor_ct": (0.56, 0.66, 0.78),
    "wall": (0.72, 0.69, 0.63), "wall2": (0.66, 0.63, 0.58), "trim": (0.68, 0.64, 0.58), "ceiling": (0.66, 0.62, 0.57),
    "ruin": (0.62, 0.57, 0.50), "platform": (0.73, 0.63, 0.46), "sandbag": (0.70, 0.66, 0.50),
}
M = {}
for k, rgb in COLORS.items():
    M[k] = PBRMaterial(name=k, baseColorTexture=grid_tex(rgb), metallicFactor=0.0, roughnessFactor=0.95)
M["cover_high"] = PBRMaterial(name="cover_high", baseColorTexture=crate_tex((0.52, 0.34, 0.20)), metallicFactor=0, roughnessFactor=0.9)
M["cover_low"] = PBRMaterial(name="cover_low", baseColorTexture=crate_tex((0.88, 0.56, 0.24)), metallicFactor=0, roughnessFactor=0.9)
M["metal_crate"] = PBRMaterial(name="metal_crate", baseColorTexture=crate_tex((0.30, 0.44, 0.30)), metallicFactor=0.5, roughnessFactor=0.6)
M["lamp"] = PBRMaterial(name="lamp_glow", baseColorFactor=[255, 200, 120, 255], emissiveFactor=[1.0, 0.72, 0.38], metallicFactor=0)
M["trunk"] = PBRMaterial(name="trunk", baseColorFactor=[110, 84, 56, 255], metallicFactor=0, roughnessFactor=1)
M["foliage"] = PBRMaterial(name="foliage", baseColorFactor=[86, 120, 60, 255], metallicFactor=0, roughnessFactor=1, doubleSided=True)
M["siteA"] = PBRMaterial(name="site_A", baseColorTexture=site_decal("A"), alphaMode="BLEND", metallicFactor=0, roughnessFactor=0.9)
M["siteB"] = PBRMaterial(name="site_B", baseColorTexture=site_decal("B"), alphaMode="BLEND", metallicFactor=0, roughnessFactor=0.9)

# ------------------------------------------------------------------ clip'lar (xarita ustida qopqoq, chegaralar)
E0, E1 = OFF, OFF + SIZE
CLIP_P.append((E0, 12.0, E0, E1, 12.5, E1))
CLIP_G.append((E0, 30.0, E0, E1, 30.5, E1))
for (a, b_, c_, d_) in ((E0 - 1, E0 - 1, E0, E1 + 1), (E1, E0 - 1, E1 + 1, E1 + 1), (E0 - 1, E0 - 1, E1 + 1, E0), (E0 - 1, E1, E1 + 1, E1 + 1)):
    CLIP_G.append((a, 0.0, b_, c_, 30.0, d_))
    CLIP_P.append((a, 0.0, b_, c_, 12.0, d_))

# ------------------------------------------------------------------ eksport
scene = trimesh.Scene()
tris = 0
for (group, mat), b in sorted(bufs.items()):
    if not b.f:
        continue
    V = np.array(b.v); F = np.array(b.f)
    area = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    F = F[area > 1e-9]
    mesh = trimesh.Trimesh(vertices=V, faces=F, process=False)
    mesh.visual = TextureVisuals(uv=np.array(b.uv), material=M[mat])
    tris += len(F)
    name = f"{mat}_{group.replace('-col', '')}"
    scene.add_geometry(mesh, node_name=name, geom_name=name)
os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
os.makedirs(os.path.dirname(OUT_META), exist_ok=True)
scene.export(OUT_GLB, include_normals=True)
json.dump({"lamps": LAMPS, "tris": tris, "fp": FP, "plat": FP_PLAT, "col": COL, "ramps": RAMPS,
           "clip_p": CLIP_P, "clip_g": CLIP_G}, open(OUT_META, "w"))
print(f"uchburchaklar {tris}, bloklar {nblocks}, chiroqlar {len(LAMPS)}, to'qnashuv qutilari {len(COL)}, "
      f"GLB {os.path.getsize(OUT_GLB) / 1e6:.1f} MB")
