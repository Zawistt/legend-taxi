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
import arch5

HERE = os.path.dirname(os.path.abspath(__file__))
# STYLE=greybox (2-bosqich, rangli kodlash) yoki STYLE=arch (4-bosqich, arxitektura). To'qnashuv ikkalasida bir xil.
STYLE = os.environ.get("STYLE", "greybox")
OUT_GLB = os.path.join(HERE, "..", "godot", "map", "qumtepa5v5_greybox.glb" if STYLE == "greybox" else "qumtepa5v5.glb")
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


CUR_DIST = None     # hozir qurilayotgan qismning uslubi (arch rejimida materialni tanlash uchun)
DIST = LY.DISTRICT
ART_MAP = {"ceiling": "plaster", "cover_high": "crate", "cover_low": "crate", "metal_crate": "green", "ruin": "sandstone",
           "platform": "wood_light", "sandbag": "cloth", "trunk": "bark", "barrel": "beam", "urn": "clay", "trim": "sandstone",
           "floor_site": "flagstone", "floor_cover": "flagstone", "floor_t": "flagstone", "floor_ct": "flagstone"}
ART_SCALE = {"vassa": 1.2, "girih": 1.5, "majolica": 1.0, "ganch": 1.2, "atlas_1": 1.5, "atlas_2": 1.5, "brick": 1.6, "cobble": 2.5, "flagstone": 3.0, "plaster": 3.0, "plaster_w": 3.0, "tile_blue": 1.0,
             "tile_turq": 1.0, "dome": 1.5, "roof": 2.0, "cloth": 0.8, "beam": 1.2, "wood_light": 1.2}


def resolve(mat):
    """greybox material nomi -> arch rejimida uslubga mos tekstura"""
    if STYLE != "arch":
        return mat
    if mat in ("wall", "wall2"):
        return arch5.STYLE[CUR_DIST]["wall"]
    if mat == "floor_open":
        return arch5.STYLE[CUR_DIST]["floor"]
    if mat == "ceiling":
        return arch5.STYLE[CUR_DIST].get("ceiling", "plaster")
    return ART_MAP.get(mat, mat)


def B(group, mat):
    return bufs.setdefault((group, resolve(mat)), Buf())


def quad(group, mat, p, uv, want_n=None):
    p = np.asarray(p, float)
    n = np.cross(p[1] - p[0], p[2] - p[0])
    if want_n is not None and np.dot(n, want_n) < 0:
        p = p[::-1]; uv = uv[::-1]
    B(group, mat).add(p, [(0, 1, 2), (0, 2, 3)], uv)


def box(group, mat, x0, y0, z0, x1, y1, z1, scale=None, unit=False, yaw=0.0, top=True, bottom=False):
    """Quti. UV — dunyo koordinatalarida (scale metrda bitta tekstura), shunda 1 m to'r hamma joyda bir xil."""
    if scale is None:
        scale = 4.0 if STYLE != "arch" else ART_SCALE.get(resolve(mat), 2.4)
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
        key = lambda rr, cc: (grid[rr][cc], DIST[rr][cc] if STYLE == "arch" else None)
        k0 = key(r, c)
        w = 1
        while c + w < G and key(r, c + w) == k0 and not done[r, c + w]:
            w += 1
        h = 1
        while r + h < G and all(key(r + h, c + k) == k0 and not done[r + h, c + k] for k in range(w)):
            h += 1
        done[r:r + h, c:c + w] = True
        CUR_DIST = DIST[r][c]
        box("Floor-col", FLOOR_MAT[t], cx(c), -0.3, cz(r), cx(c + w), 0.0, cz(r + h))

# ------------------------------------------------------------------ binolar (4x4 katakgacha bloklar, tasodifiy balandlik)
H = np.zeros((G, G))
BID = [[0] * G for _ in range(G)]
BLOCKS = []
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
        for rr in range(r, r + h):
            for cc in range(c, c + w):
                BID[rr][cc] = nblocks + 1
        x0, z0, x1, z1 = cx(c), cz(r), cx(c + w), cz(r + h)
        if touches:
            BLOCKS.append((x0, z0, x1, z1, hh))      # 7-bosqich: occluder'lar uchun
        CUR_DIST = DIST[r][c]
        box("Walls-col", "wall" if rng.random() < 0.75 else "wall2", x0, 0, z0, x1, hh, z1)
        COL.append(("stone", x0, 0.0, z0, x1, hh + 0.55, z1))
        p = 0.3   # tom chetidagi devorcha
        for a in ((x0, z0, x1, z0 + p), (x0, z1 - p, x1, z1), (x0, z0, x0 + p, z1), (x1 - p, z0, x1, z1)):
            box("Walls-col", "trim", a[0], hh, a[1], a[2], hh + 0.55, a[3])
        if STYLE == "arch":
            box("Decor", "plaster", x0 + 0.3, hh, z0 + 0.3, x1 - 0.3, hh + 0.04, z1 - 0.3, scale=3)        # tom
            box("Decor", "plaster", x0 - 0.12, hh - 0.35, z0 - 0.12, x1 + 0.12, hh - 0.1, z1 + 0.12, scale=3)  # karniz
        nblocks += 1

# ------------------------------------------------------------------ yopiq yo'laklar: shift, tom, chiroqlar
for r in range(G):
    for c in range(G):
        t = grid[r][c]
        if t in COVER:
            h = COVER[t]
            CUR_DIST = DIST[r][c]
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
    CUR_DIST = DIST[line if dr else idx[0]][idx[0] if dr else line]
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
    paxta = LY.district_at(x, z) in LY.PAXTA_DISTRICTS      # 5-bosqich: paxta toylari (mato sirti)
    for dx, dz, y, s, g in pattern:
        if y == 0:
            FP.append((x + dx - s / 2, z + dz - s / 2, x + dx + s / 2, z + dz + s / 2))
        surf = "metal" if g else ("cloth" if paxta else "wood")
        COL.append((surf, x + dx - s / 2, y, z + dz - s / 2, x + dx + s / 2, y + s, z + dz + s / 2))
        if STYLE == "arch" and paxta and not g:
            bale(x + dx, y, z + dz, s)
            continue
        mat = "metal_crate" if g else ("cover_high" if tall else "cover_low")
        box("Props-col", mat, x + dx - s / 2, y, z + dz - s / 2, x + dx + s / 2, y + s, z + dz + s / 2, unit=True, yaw=yaw)


def bale(x, y, z, s):
    """paxta toyi: biroz yumaloqlangan qanor bo'lak, arqon bilan bog'langan (to'qnashuv — o'sha quti)"""
    e = 0.04
    box("Props-col", "paxta", x - s / 2 + e, y, z - s / 2 + e, x + s / 2 - e, y + s - e, z + s / 2 - e, unit=True)
    box("Props-col", "paxta", x - s / 2, y + 0.08, z - s / 2 + 0.1, x + s / 2, y + s - 0.12, z + s / 2 - 0.1, unit=True)
    box("Props-col", "paxta", x - s / 2 + 0.1, y + 0.08, z - s / 2, x + s / 2 - 0.1, y + s - 0.12, z + s / 2, unit=True)


def barrel(x, z):
    FP.append((x - .4, z - .4, x + .4, z + .4))
    tandir = LY.district_at(x, z) in LY.TANDIR_DISTRICTS    # 5-bosqich: tandir (tosh sirti)
    COL.append(("stone" if tandir else "wood", x - .4, 0.0, z - .4, x + .4, 0.9, z + .4))
    if STYLE == "arch" and tandir:
        # tandir: loy gumbaz, yon tomonida og'zi, pastida g'isht supa
        box("Props-col", "brick", x - 0.42, 0, z - 0.42, x + 0.42, 0.22, z + 0.42, scale=1.6)
        lathe("Props-col", "clay", x, 0, z, [(0.40, 0.22), (0.41, 0.45), (0.36, 0.7), (0.24, 0.86), (0.16, 0.9), (0.0, 0.9)], 16, 1.5)
        lathe("Decor", "dark", x, 0, z, [(0.15, 0.905), (0.0, 0.905)], 12)
        return
    if STYLE == "arch":
        lathe("Props-col", "barrel", x, 0, z, [(0.0, 0), (0.33, 0), (0.38, 0.25), (0.40, 0.45), (0.38, 0.65), (0.33, 0.9), (0.0, 0.9)], 14, 1.5)
        for y in (0.2, 0.7):
            lathe("Decor", "metal", x, 0, z, [(0.395, y), (0.405, y + 0.04), (0.395, y + 0.08)], 14)
    else:
        lathe("Props-col", "barrel", x, 0, z, [(0.0, 0), (0.36, 0), (0.40, 0.45), (0.36, 0.9), (0.0, 0.9)], 12)


def urn(x, z, s=1.0):
    FP.append((x - .34 * s, z - .34 * s, x + .34 * s, z + .34 * s))
    COL.append(("stone", x - .3 * s, 0.0, z - .3 * s, x + .3 * s, 1.0 * s, z + .3 * s))
    if STYLE == "arch":
        lathe("Props-col", "urn", x, 0, z, [(0.0, 0), (0.18 * s, 0), (0.30 * s, 0.25 * s), (0.34 * s, 0.45 * s), (0.25 * s, 0.75 * s),
                                            (0.14 * s, 0.9 * s), (0.18 * s, 0.98 * s), (0.12 * s, 1.0 * s)], 16, 1.5)
    else:
        lathe("Props-col", "urn", x, 0, z, [(0.0, 0), (0.2 * s, 0), (0.34 * s, 0.45 * s), (0.16 * s, 0.9 * s), (0.12 * s, 1.0 * s), (0.0, 1.0 * s)], 12)


def sandbags(x0, z0, x1, z1):
    b = (min(x0, x1) - .3, min(z0, z1) - .22, max(x0, x1) + .3, max(z0, z1) + .22)
    FP.append((b[0], b[1] - .08, b[2], b[3] + .08))
    COL.append(("cloth", b[0], 0.0, b[1], b[2], 0.78, b[3]))
    if STYLE != "arch":
        box("Props-col", "sandbag", b[0], 0.0, b[1], b[2], 0.78, b[3])
        return
    Ln = math.hypot(x1 - x0, z1 - z0)
    yaw = -math.atan2(z1 - z0, x1 - x0)
    n = max(2, int(Ln / 0.6) + 1)
    for row in range(3):
        for i in range(n - (row % 2)):
            t = (i + 0.5 * (row % 2)) / max(n - 1, 1)
            px_, pz_ = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
            box("Props-col", "cloth", px_ - 0.3, row * 0.26, pz_ - 0.2, px_ + 0.3, row * 0.26 + 0.26, pz_ + 0.2, scale=0.8, yaw=yaw)


def wall(x0, z0, x1, z1, h):
    COL.append(("stone", x0, 0.0, z0, x1, h, z1))
    CLIP_P.append((x0, h, z0, x1, 12.0, z1))          # tepasiga chiqib bo'lmaydi
    box("Props-col", "ruin", x0, 0.0, z0, x1, h, z1)
    if STYLE != "arch":
        return
    w, d = x1 - x0, z1 - z0
    if h >= 5.0:
        # eshik o'rni (Mid doors, B doors, Long doors): yog'och eshik tavaqasi devorga ochib qo'yilgan (ichkaridan 0.08 m)
        box("Decor", "door", x0 - 0.02, 0.02, z0 - 0.02, x1 + 0.02, 2.6, z0 + 0.06, unit=True) if w >= d else \
            box("Decor", "door", x0 - 0.02, 0.02, z0 - 0.02, x0 + 0.06, 2.6, z1 + 0.02, unit=True)
        box("Decor", "sandstone", x0 - 0.05, 0, z0 - 0.05, x1 + 0.05, 0.5, z1 + 0.05)
    elif 2.4 <= h <= 2.6 and w > 3 and d > 2.5:
        # quduq (sardoba): tosh devorlar, ustida kichik gumbaz (clip ustida — faqat ko'rinish)
        box("Decor", "sandstone", x0 - 0.08, h - 0.2, z0 - 0.08, x1 + 0.08, h, z1 + 0.08)
        r0 = min(w, d) * 0.45
        prof = [(r0 * math.cos(a), h + r0 * 0.8 * math.sin(a)) for a in np.linspace(0, math.pi / 2, 8)]
        prof[-1] = (0.0, prof[-1][1])
        lathe("Decor", "plaster_w", (x0 + x1) / 2, 0, (z0 + z1) / 2, prof, 16, 2)
    else:
        # xaroba: tepasi notekis, sinib tushgan toshlar
        rr = np.random.default_rng(int(abs(x0 * 13 + z0 * 7)))
        n = max(2, int(max(w, d) / 0.9))
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            hh = h + rr.uniform(-0.6, 0.35)
            if w >= d:
                box("Decor", "sandstone", x0 + w * t0, h - 0.05, z0, x0 + w * t1 - 0.03, hh, z1)
            else:
                box("Decor", "sandstone", x0, h - 0.05, z0 + d * t0, x1, hh, z0 + d * t1 - 0.03)


def platform(x0, z0, x1, z1, h, stair_dir):
    FP_PLAT.append((x0, z0, x1, z1, h))
    COL.append(("wood", x0, 0.0, z0, x1, h, z1))          # 5-bosqich: so'ri (yog'och sirti)
    box("Props-col", "platform", x0, 0, z0, x1, h, z1)
    if STYLE == "arch":
        sufa_decor(x0, z0, x1, z1, h, stair_dir)
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


def sufa_decor(x0, z0, x1, z1, h, stair_dir):
    """so'ri: o'ymakor yog'och yon devorlar, ustida so'zana to'shalgan, orqa chetida yostiqlar (faqat ko'rinish)"""
    for zz in (z0, z1 - 0.06):
        box("Decor", "carved_wood", x0 - 0.02, 0.05, zz - 0.02, x1 + 0.02, h - 0.05, zz + 0.08, unit=True)
    bx = x0 if stair_dir == "+x" else x1 - 0.06
    box("Decor", "carved_wood", bx - 0.02, 0.05, z0, bx + 0.08, h - 0.05, z1, unit=True)
    box("Decor", "wood_light", x0 - 0.05, h - 0.06, z0 - 0.05, x1 + 0.05, h, z1 + 0.05, scale=1.2)
    quad("Decor", "suzani", [(x0 + 0.2, h + 0.01, z0 + 0.3), (x1 - 0.2, h + 0.01, z0 + 0.3), (x1 - 0.2, h + 0.01, z1 - 0.3), (x0 + 0.2, h + 0.01, z1 - 0.3)],
         [(0, 0), (1, 0), (1, 3), (0, 3)], np.array([0, 1, 0]))
    # yostiqlar orqa chetda (zinapoyaning qarshi tomonida), 0.25 m — ko'rishga ta'sir qilmaydi
    cx0 = x0 + 0.05 if stair_dir == "+x" else x1 - 0.45
    zz = z0 + 0.4
    k = 0
    while zz < z1 - 0.8:
        box("Decor", "atlas_1" if k % 2 == 0 else "atlas_2", cx0, h, zz, cx0 + 0.4, h + 0.28, zz + 0.9, unit=True)
        zz += 1.0
        k += 1


def chinor(x, z, h=7.5):
    """chinor daraxti: yo'g'on oqish tana, 3 ta shox, barg kartochkalaridan toj (faqat tana to'qnashuvi)"""
    prng = np.random.default_rng(int(abs(x * 29 + z * 11)))
    lathe("Decor", "bark_light", x, 0, z, [(0.27, 0), (0.22, h * 0.45), (0.18, h * 0.6), (0.0, h * 0.62)], 10, 1.0)
    crowns = [(x, h * 0.9, z, 2.8)]
    for k in range(3):
        a = k * 2.1 + prng.uniform(0, 0.8)
        ex, ez = x + math.cos(a) * 1.6, z + math.sin(a) * 1.6
        ey = h * 0.62 + prng.uniform(0.8, 1.6)
        v = np.array([ex - x, ey - h * 0.55, ez - z])
        L_ = np.linalg.norm(v)
        for i in range(6):
            t0, t1 = i / 6, (i + 1) / 6
            p0 = np.array([x, h * 0.55, z]) + v * t0
            p1 = np.array([x, h * 0.55, z]) + v * t1
            r0, r1 = 0.14 * (1 - t0 * 0.5), 0.14 * (1 - t1 * 0.5)
            side = np.array([-v[2], 0, v[0]]) / max(1e-6, math.hypot(v[0], v[2]))
            quad("Decor", "bark_light", [p0 - side * r0, p0 + side * r0, p1 + side * r1, p1 - side * r1], [(0, 0), (1, 0), (1, 1), (0, 1)], np.array([0, 0, 1]))
            quad("Decor", "bark_light", [p0 - side * r0, p0 + side * r0, p1 + side * r1, p1 - side * r1][::-1], [(0, 0), (1, 0), (1, 1), (0, 1)][::-1], np.array([0, 0, -1]))
        crowns.append((ex, ey + 0.6, ez, 2.2))
    for (px_, py_, pz_, r) in crowns:
        for k in range(4):
            a = k * math.pi / 4 + prng.uniform(0, 0.3)
            dx, dz = math.cos(a) * r, math.sin(a) * r
            quad("Decor", "leaves", [(px_ - dx, py_ - r * 0.8, pz_ - dz), (px_ + dx, py_ - r * 0.8, pz_ + dz),
                                     (px_ + dx, py_ + r * 0.8, pz_ + dz), (px_ - dx, py_ + r * 0.8, pz_ - dz)],
                 [(0, 1), (1, 1), (1, 0), (0, 0)], np.array([-dz, 0, dx]))
        quad("Decor", "leaves", [(px_ - r, py_, pz_ - r), (px_ + r, py_, pz_ - r), (px_ + r, py_, pz_ + r), (px_ - r, py_, pz_ + r)],
             [(0, 1), (1, 1), (1, 0), (0, 0)], np.array([0, 1, 0]))


def palm(x, z, h=7.5):
    FP.append((x - .28, z - .28, x + .28, z + .28))
    COL.append(("wood", x - .22, 0.0, z - .22, x + .22, h * 0.9, z + .22))
    if STYLE == "arch":
        chinor(x, z, h)          # 5-bosqich: palma o'rnida chinor
        return
    lathe("Decor", "trunk", x, 0, z, [(0.26, 0), (0.2, h * 0.5), (0.16, h), (0.0, h)], 8)
    lathe("Decor", "foliage", x, 0, z, [(0.0, h + 0.6), (2.6, h - 0.4), (1.8, h - 1.2), (0.0, h - 0.6)], 10)


def palm_art(x, z, h, lean=(0.3, 0.2)):
    """v2 palmasi: egilgan tana va 11 ta osilgan barg (faqat ko'rinish, to'qnashuv — tana silindri)"""
    prng = np.random.default_rng(int(abs(x * 31 + z * 17)))
    segs = 10
    prev = None
    for i in range(segs + 1):
        t = i / segs
        px_ = x + lean[0] * t * t * h * 0.25
        pz_ = z + lean[1] * t * t * h * 0.25
        r = 0.24 - 0.08 * t
        ring = [(px_ + r * math.cos(a), t * h, pz_ + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 9)]
        if prev:
            for k in range(8):
                quad("Decor", "bark", [prev[k], prev[k + 1], ring[k + 1], ring[k]],
                     [(k / 8, (i - 1) / 3), ((k + 1) / 8, (i - 1) / 3), ((k + 1) / 8, i / 3), (k / 8, i / 3)],
                     np.array([math.cos((k + .5) / 8 * 2 * math.pi), 0, math.sin((k + .5) / 8 * 2 * math.pi)]))
        prev = ring
    top = np.array(prev).mean(0)
    for f in range(11):
        ang = f / 11 * 2 * math.pi + prng.normal(0, 0.15)
        Lf = 3.2 + prng.normal(0, 0.3)
        droop = 0.9 + prng.random() * 0.8
        dirv = np.array([math.cos(ang), 0, math.sin(ang)])
        side = np.array([-dirv[2], 0, dirv[0]])
        pts = [top + dirv * Lf * (i / 8) + np.array([0, 0.9 * (i / 8) - droop * (i / 8) ** 2 * 1.8, 0]) for i in range(9)]
        for i in range(8):
            w0 = 0.55 + 0.4 * math.sin(math.pi * min(1, i / 8 + 0.15))
            w1 = 0.55 + 0.4 * math.sin(math.pi * min(1, (i + 1) / 8 + 0.15))
            a, b = pts[i], pts[i + 1]
            quad("Decor", "frond", [a - side * w0, a + side * w0, b + side * w1, b - side * w1],
                 [(0, i / 8), (1, i / 8), (1, (i + 1) / 8), (0, (i + 1) / 8)], np.array([0, 1, 0]))
    lathe("Decor", "frond_core", top[0], top[1] - 0.3, top[2], [(0.0, 0), (0.35, 0.1), (0.3, 0.45), (0.0, 0.6)], 8)


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
M["barrel"] = M["urn"] = M["cover_low"]

# ------------------------------------------------------------------ 4-bosqich: arxitektura bezaklari va teksturali materiallar
if STYLE == "arch":
    import textures5 as TX
    ctx = {"box": box, "quad": quad, "lathe": lathe, "arch_wall": arch_wall, "grid": grid, "H": H, "DIST": DIST, "G": G,
           "cx": cx, "cz": cz, "ctype": ctype, "COVER": COVER, "BID": BID, "LANDMARKS": LY.LANDMARKS,
           "ORIGIN": OFF, "CELL": CS}
    n_col = len(COL)
    decor_stats = arch5.decorate(ctx)
    assert len(COL) == n_col, "arxitektura to'qnashuvni o'zgartirmasligi kerak"
    T = TX.all_textures()
    M = {}
    for k, (img, nrm) in T.items():
        M[k] = PBRMaterial(name=k, baseColorTexture=img, normalTexture=nrm, metallicFactor=0.0,
                           roughnessFactor={"green": 0.6, "tile_blue": 0.35, "tile_turq": 0.35, "dome": 0.3}.get(k, 0.9))
    M["dark"] = PBRMaterial(name="window_dark", baseColorFactor=[18, 14, 10, 255], metallicFactor=0, roughnessFactor=0.6)
    M["dark_tile"] = PBRMaterial(name="niche_dark", baseColorTexture=T["tile_blue"][0], baseColorFactor=[70, 80, 120, 255],
                                 metallicFactor=0, roughnessFactor=0.5)
    M["metal"] = PBRMaterial(name="iron", baseColorFactor=[40, 36, 32, 255], metallicFactor=0.8, roughnessFactor=0.5)
    M["lamp"] = PBRMaterial(name="lamp_glow", baseColorFactor=[255, 200, 120, 255], emissiveFactor=[1.0, 0.72, 0.38], metallicFactor=0)
    M["cloth"] = PBRMaterial(name="cloth", baseColorTexture=T["plaster"][0], baseColorFactor=[210, 190, 150, 255], metallicFactor=0, roughnessFactor=1)
    M["clay"] = PBRMaterial(name="clay", baseColorTexture=T["plaster"][0], baseColorFactor=[230, 150, 110, 255], metallicFactor=0, roughnessFactor=0.85)
    V2T = TX.V2
    M["frond"] = PBRMaterial(name="palm_frond", baseColorTexture=V2T.frond(), alphaMode="MASK", alphaCutoff=0.5, doubleSided=True, metallicFactor=0, roughnessFactor=0.8)
    M["frond_core"] = PBRMaterial(name="palm_core", baseColorFactor=[70, 85, 35, 255], metallicFactor=0)
    M["leaves"] = PBRMaterial(name="chinor_leaves", baseColorTexture=TX.leaves(), alphaMode="MASK", alphaCutoff=0.5, doubleSided=True, metallicFactor=0, roughnessFactor=0.9)
    M["lagan"] = PBRMaterial(name="lagan", baseColorTexture=TX.lagan(), alphaMode="MASK", alphaCutoff=0.5, metallicFactor=0, roughnessFactor=0.3)
    M["bark_light"] = PBRMaterial(name="chinor_bark", baseColorTexture=T["bark"][0], baseColorFactor=[220, 205, 180, 255], doubleSided=True, metallicFactor=0, roughnessFactor=1)
    M["siteA"] = PBRMaterial(name="site_A", baseColorTexture=V2T.site_decal("A"), alphaMode="BLEND", metallicFactor=0, roughnessFactor=0.9)
    M["siteB"] = PBRMaterial(name="site_B", baseColorTexture=V2T.site_decal("B"), alphaMode="BLEND", metallicFactor=0, roughnessFactor=0.9)
    for (g_, m_) in bufs:
        assert m_ in M, f"material yo'q: {m_}"

# ------------------------------------------------------------------ clip'lar (xarita ustida qopqoq, chegaralar)
E0, E1 = OFF, OFF + SIZE
CLIP_P.append((E0, 12.0, E0, E1, 12.5, E1))
CLIP_G.append((E0, 30.0, E0, E1, 30.5, E1))
for (a, b_, c_, d_) in ((E0 - 1, E0 - 1, E0, E1 + 1), (E1, E0 - 1, E1 + 1, E1 + 1), (E0 - 1, E0 - 1, E1 + 1, E0), (E0 - 1, E1, E1 + 1, E1 + 1)):
    CLIP_G.append((a, 0.0, b_, c_, 30.0, d_))
    CLIP_P.append((a, 0.0, b_, c_, 12.0, d_))

# ------------------------------------------------------------------ eksport
# 7-bosqich: har bir (guruh, material) meshi 4x4 hududiy bo'lakka (27.5 m) ajratiladi — kameraga ko'rinmaydigan
# bo'laklar chizilmaydi (frustum va occlusion culling), mayda bezaklarni masofa bo'yicha yashirish mumkin.
# "Landmark" (mo'ljal binolari, tomdagi gumbazlar) bo'linmaydi — ular uzoqdan ko'rinishi kerak.
CHUNKS = int(os.environ.get("CHUNKS", "4"))
CH = SIZE / CHUNKS
scene = trimesh.Scene()
tris = 0
nodes = 0
for (group, mat), b in sorted(bufs.items()):
    if not b.f:
        continue
    V = np.array(b.v); F = np.array(b.f); UV = np.array(b.uv)
    area = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    F = F[area > 1e-9]
    tris += len(F)
    gname = group.replace('-col', '')
    if group.startswith("Landmark") or CHUNKS <= 1:
        parts = {(0, 0): F}
    else:
        cen = V[F].mean(1)
        ci = np.clip(((cen[:, 0] - OFF) // CH).astype(int), 0, CHUNKS - 1)
        cj = np.clip(((cen[:, 2] - OFF) // CH).astype(int), 0, CHUNKS - 1)
        parts = {}
        for i_ in range(CHUNKS):
            for j_ in range(CHUNKS):
                sel = F[(ci == i_) & (cj == j_)]
                if len(sel):
                    parts[(i_, j_)] = sel
    for (i_, j_), Fp in parts.items():
        used = np.unique(Fp)
        remap = -np.ones(len(V), int)
        remap[used] = np.arange(len(used))
        mesh = trimesh.Trimesh(vertices=V[used], faces=remap[Fp], process=False)
        mesh.visual = TextureVisuals(uv=UV[used], material=M[mat])
        name = f"{mat}_{gname}" + ("" if len(parts) == 1 and (i_, j_) == (0, 0) and (group.startswith("Landmark") or CHUNKS <= 1) else f"_c{i_}{j_}")
        scene.add_geometry(mesh, node_name=name, geom_name=name)
        nodes += 1
os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
os.makedirs(os.path.dirname(OUT_META), exist_ok=True)
scene.export(OUT_GLB, include_normals=True)
if STYLE == "greybox":
    json.dump({"lamps": LAMPS, "tris": tris, "fp": FP, "plat": FP_PLAT, "col": COL, "ramps": RAMPS,
               "clip_p": CLIP_P, "clip_g": CLIP_G, "blocks": BLOCKS}, open(OUT_META, "w"))
else:
    # arxitektura modeli to'qnashuvni o'zgartirmasligini tekshirish
    old = json.load(open(OUT_META))
    same = json.loads(json.dumps(COL)) == old["col"] and json.loads(json.dumps(CLIP_P)) == old["clip_p"]
    assert same, "arch to'qnashuvi greybox bilan bir xil emas — avval STYLE=greybox ni ishga tushiring"
    print("bezaklar:", decor_stats)
print(f"[{STYLE}] mesh bo'laklari {nodes}, uchburchaklar {tris}, bloklar {nblocks}, chiroqlar {len(LAMPS)}, to'qnashuv qutilari {len(COL)}, "
      f"GLB {os.path.getsize(OUT_GLB) / 1e6:.1f} MB")
