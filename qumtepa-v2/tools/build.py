import math, json
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial
from trimesh.visual import TextureVisuals
from PIL import Image
import textures as TX

rng = np.random.default_rng(42)
G = 25          # grid cells
CS = 2.0        # cell size (m)  -> 50 m x 50 m
OFF = -25.0

# ---------------------------------------------------------------- layout
import layout as LY
grid = [row[:] for row in LY.GRID]
FP = []        # blocking prop footprints (x0,z0,x1,z1)
COL = []       # simplified collision boxes: (surface, x0,y0,z0,x1,y1,z1)
RAMPS = []     # convex ramp collision: (surface, [points])
CLIP_P = []    # player clip boxes
CLIP_G = []    # grenade clip boxes
FP_PLAT = []   # walkable raised platforms

OPEN = set(".AB")
COVER = LY.COVER
SLAB = 0.45


def ctype(r, c):
    if r < 0 or c < 0 or r >= G or c >= G:
        return "#"
    return grid[r][c]


def cx(c):
    return OFF + c * CS


def cz(r):
    return OFF + r * CS


# ---------------------------------------------------------------- mesh buffers
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


def box(group, mat, x0, y0, z0, x1, y1, z1, scale=2.0, unit=False, yaw=0.0, top=True, bottom=False):
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


def lathe(group, mat, cxp, cyp, czp, prof, seg=16, scale=2.0, smooth=True):
    """prof: list of (radius, y). Smooth shared vertices."""
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


def arch_wall(group, axis, line, t, a0, a1, y_top, apex, mat="sandstone", seg=18, col=True):
    """Wall with an arched opening. axis='x': wall spans along x at z=line."""
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
    for k5 in range(5 if col else 0):   # collision follows the arch curve in 5 steps
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
            uv = [(s0 / 2.4, y0 / 2.4), (s1 / 2.4, y1 / 2.4), (s1 / 2.4, y_top / 2.4), (s0 / 2.4, y_top / 2.4)]
            quad(group, mat, pts, uv, nf * sg)
        pts = [P(s0, y0, -t / 2), P(s1, y1, -t / 2), P(s1, y1, t / 2), P(s0, y0, t / 2)]
        quad(group, mat, pts, [(s0 / 2.4, 0), (s1 / 2.4, 0), (s1 / 2.4, t / 2.4), (s0 / 2.4, t / 2.4)], np.array((0, -1, 0)))
    pts = [P(a0, y_top, -t / 2), P(a1, y_top, -t / 2), P(a1, y_top, t / 2), P(a0, y_top, t / 2)]
    quad(group, mat, pts, [(0, 0), (1, 0), (1, 1), (0, 1)], np.array((0, 1, 0)))
    # voussoir trim ring (slightly proud)
    for i in range(0, seg, 2):
        s0, s1 = ss[i], ss[min(i + 2, seg)]
        y0, y1 = curve(s0), curve(s1)
        for off, sg in ((t / 2 + 0.06, 1), (-t / 2 - 0.06, -1)):
            k = 0.35
            pts = [P(s0, y0, off), P(s1, y1, off), P(s1, y1 + k, off), P(s0, y0 + k, off)]
            quad("Walls-col", "plaster", pts, [(0, 0), (1, 0), (1, 0.2), (0, 0.2)], nf * sg)


# ---------------------------------------------------------------- floors
COL.append(("stone", -25.0, -0.3, -25.0, 25.0, 0.0, 25.0))
for r in range(G):
    for c in range(G):
        t = grid[r][c]
        if t == "#":
            continue
        mat = "flagstone"
        box("Floor-col", mat, cx(c), -0.3, cz(r), cx(c) + CS, 0.0, cz(r) + CS, scale=3.0)

# ---------------------------------------------------------------- buildings
rng3 = np.random.default_rng(7)          # stage-3 detail randomness (keeps layout/props stable)
BID = np.zeros((G, G), int)
MATG = [["sandstone"] * G for _ in range(G)]
VIGA = {}
bcount = 0
H = np.zeros((G, G))
done = np.zeros((G, G), bool)
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
        edge = r == 0 or c == 0 or r + h == G or c + w == G
        hh = float(rng.choice([6.5, 7.5, 8.5, 9.5])) + (1.5 if edge else 0)
        done[r:r + h, c:c + w] = True
        H[r:r + h, c:c + w] = hh
        x0, z0, x1, z1 = cx(c), cz(r), cx(c + w), cz(r + h)
        mat = "sandstone" if rng.random() < 0.72 else "plaster"
        box("Walls-col", mat, x0, 0, z0, x1, hh, z1, scale=2.4)
        COL.append(("stone", x0, 0.0, z0, x1, hh + 0.55, z1))
        bcount += 1
        BID[r:r + h, c:c + w] = bcount
        for rr in range(r, r + h):
            for kk in range(c, c + w):
                MATG[rr][kk] = mat
        VIGA[bcount] = rng3.random() < 0.5
        if rng3.random() < 0.3:   # crenellated parapet
            for xx in np.arange(x0 + 0.25, x1 - 0.35, 0.8):
                for za, zb in ((z0, z0 + 0.3), (z1 - 0.3, z1)):
                    box("Walls-col", "sandstone", xx, hh + 0.55, za, xx + 0.4, hh + 0.92, zb, scale=2.4)
            for zz in np.arange(z0 + 0.25, z1 - 0.35, 0.8):
                for xa_, xb_ in ((x0, x0 + 0.3), (x1 - 0.3, x1)):
                    box("Walls-col", "sandstone", xa_, hh + 0.55, zz, xb_, hh + 0.92, zz + 0.4, scale=2.4)
        box("Walls-col", "plaster", x0 + 0.3, hh, z0 + 0.3, x1 - 0.3, hh + 0.04, z1 - 0.3, scale=3)
        # parapet + cornice
        p = 0.3
        for a in ((x0, z0, x1, z0 + p), (x0, z1 - p, x1, z1), (x0, z0, x0 + p, z1), (x1 - p, z0, x1, z1)):
            box("Walls-col", "sandstone", a[0], hh, a[1], a[2], hh + 0.55, a[3], scale=2.4)
        box("Walls-col", "plaster", x0 - 0.12, hh - 0.35, z0 - 0.12, x1 + 0.12, hh - 0.1, z1 + 0.12, scale=3)
        # rooftop dressing
        if w * h >= 4 and rng.random() < 0.35:
            dx, dz = (x0 + x1) / 2, (z0 + z1) / 2
            rad = min(x1 - x0, z1 - z0) * 0.32
            box("Walls-col", "sandstone", dx - rad - .3, hh, dz - rad - .3, dx + rad + .3, hh + 1.0, dz + rad + .3, scale=2.4)
            prof = [(rad * math.cos(a), hh + 1.0 + rad * math.sin(a)) for a in np.linspace(0, math.pi / 2, 9)]
            prof[-1] = (0.0, prof[-1][1])
            lathe("Walls-col", "plaster", dx, 0, dz, prof, 24, 3)
            lathe("Decor", "metal", dx, 0, dz, [(0.08, hh + 1.0 + rad), (0.05, hh + 1.6 + rad), (0.0, hh + 1.65 + rad)], 8)
        elif rng.random() < 0.25:
            # small roof shed with tiles
            sx0, sz0 = x0 + 0.6, z0 + 0.6
            sx1, sz1 = sx0 + min(3, x1 - x0 - 1.2), sz0 + min(3, z1 - z0 - 1.2)
            box("Walls-col", "plaster", sx0, hh, sz0, sx1, hh + 2.2, sz1, scale=3)
            box("Walls-col", "roof", sx0 - .2, hh + 2.2, sz0 - .2, sx1 + .2, hh + 2.45, sz1 + .2, scale=2)

# ---------------------------------------------------------------- facade details
DIRS = [(0, 1, "E"), (0, -1, "W"), (1, 0, "S"), (-1, 0, "N")]
lamp_positions = []
QUOINS = set()


def quoins(ax, fx, out, end, s2, hh):
    k, y = 0, 0.55
    while y + 0.5 < hh - 0.35:
        l1, l2 = (0.62, 0.34) if k % 2 == 0 else (0.34, 0.62)
        n0, n1 = sorted((fx - out * l1, fx + out * 0.07))
        e0, e1 = sorted((end - s2 * l2, end + s2 * 0.07))
        if ax == "x":
            box("Walls-col", "sandstone", e0, y, n0, e1, y + 0.5, n1, scale=2.4)
        else:
            box("Walls-col", "sandstone", n0, y, e0, n1, y + 0.5, e1, scale=2.4)
        y += 0.56
        k += 1


def window(fbox, m, wy, trim, style):
    fbox("Decor", "dark", m - 0.5, m + 0.5, wy, wy + 1.3, 0.0, 0.03)
    fbox("Walls-col", trim, m - 0.66, m - 0.5, wy - 0.1, wy + 1.3, 0, 0.17, scale=3)
    fbox("Walls-col", trim, m + 0.5, m + 0.66, wy - 0.1, wy + 1.3, 0, 0.17, scale=3)
    fbox("Walls-col", trim, m - 0.74, m + 0.74, wy + 1.3, wy + 1.52, 0, 0.21, scale=3)
    fbox("Walls-col", trim, m - 0.72, m + 0.72, wy - 0.24, wy - 0.1, 0, 0.25, scale=3)
    if style == "shutters":
        fbox("Decor", "beam", m - 0.5, m + 0.5, wy + 0.62, wy + 0.68, 0.03, 0.08, scale=1)
        fbox("Decor", "door", m - 0.98, m - 0.68, wy, wy + 1.3, 0.02, 0.07, unit=True)
        fbox("Decor", "door", m + 0.68, m + 0.98, wy, wy + 1.3, 0.02, 0.07, unit=True)
    elif style == "grille":
        for k in range(5):
            xs = m - 0.4 + k * 0.2
            fbox("Decor", "metal", xs - 0.015, xs + 0.015, wy, wy + 1.3, 0.1, 0.13)
        for yy in (wy + 0.35, wy + 0.95):
            fbox("Decor", "metal", m - 0.5, m + 0.5, yy, yy + 0.03, 0.1, 0.13)
    else:
        fbox("Decor", "beam", m - 0.5, m + 0.5, wy + 0.62, wy + 0.7, 0.03, 0.09, scale=1)
        fbox("Decor", "beam", m - 0.04, m + 0.04, wy, wy + 1.3, 0.03, 0.09, scale=1)


def arched_door(fbox, ax, fx, out, m, trim):
    fbox("Decor", "door", m - 0.62, m + 0.62, 0.02, 2.4, 0.0, 0.05, unit=True)
    fbox("Decor", "dark", m - 0.62, m + 0.62, 2.4, 3.0, 0.0, 0.02)
    for sgn in (-1, 1):
        a, b = sorted((m + sgn * 0.62, m + sgn * 0.86))
        fbox("Walls-col", trim, a, b, 0, 3.3, 0, 0.16, scale=3)
    arch_wall("Walls-col", ax, fx + out * 0.08, 0.16, m - 0.62, m + 0.62, 3.3, 3.0, mat=trim, seg=12, col=False)
    fbox("Walls-col", trim, m - 0.11, m + 0.11, 2.88, 3.42, 0, 0.24, scale=3)
    fbox("Walls-col", trim, m - 0.95, m + 0.95, 3.3, 3.42, 0, 0.2, scale=3)


def balcony(fbox, a0, a1):
    y = 3.9
    s0, s1 = a0 + 0.15, a1 - 0.15
    m = (a0 + a1) / 2
    fbox("Decor", "dark", m - 0.45, m + 0.45, y, y + 2.0, 0, 0.02)
    fbox("Walls-col", "plaster", m - 0.6, m + 0.6, y + 2.0, y + 2.15, 0, 0.12, scale=3)
    COL.append(("wood", *fbox("Walls-col", "beam", s0, s1, y - 0.14, y, 0, 1.0, scale=1.2)))
    CLIP_P.append(fbox(None, None, s0, s1, y, 12.0, 0, 1.0))
    for p in (s0 + 0.12, m, s1 - 0.12):
        fbox("Decor", "beam", p - 0.07, p + 0.07, y - 0.55, y - 0.14, 0, 0.22, scale=1)
        fbox("Decor", "beam", p - 0.07, p + 0.07, y - 0.34, y - 0.14, 0.22, 0.6, scale=1)
    for p in np.linspace(s0 + 0.05, s1 - 0.05, 9):
        fbox("Decor", "beam", p - 0.025, p + 0.025, y, y + 0.9, 0.93, 0.98, scale=1)
    fbox("Decor", "beam", s0, s1, y + 0.9, y + 0.98, 0.9, 1.0, scale=1)
    for sx in (s0, s1 - 0.06):
        fbox("Decor", "beam", sx, sx + 0.06, y + 0.9, y + 0.98, 0, 1.0, scale=1)
        for d in (0.33, 0.66):
            fbox("Decor", "beam", sx, sx + 0.06, y, y + 0.9, d - 0.025, d + 0.025, scale=1)
for r in range(G):
    for c in range(G):
        if grid[r][c] != "#":
            continue
        for dr, dc, nm in DIRS:
            nt = ctype(r + dr, c + dc)
            if nt == "#":
                continue
            # face plane
            if nm == "E":
                fx = cx(c + 1); ax = "z"; a0, a1 = cz(r), cz(r + 1); out = 1
            elif nm == "W":
                fx = cx(c); ax = "z"; a0, a1 = cz(r), cz(r + 1); out = -1
            elif nm == "S":
                fx = cz(r + 1); ax = "x"; a0, a1 = cx(c), cx(c + 1); out = 1
            else:
                fx = cz(r); ax = "x"; a0, a1 = cx(c), cx(c + 1); out = -1

            def fbox(group, mat, s0, s1, y0, y1, d0, d1, **kw):
                lo, hi = sorted((fx + out * d0, fx + out * d1))
                bb = (s0, y0, lo, s1, y1, hi) if ax == "x" else (lo, y0, s0, hi, y1, s1)
                if group:
                    box(group, mat, *bb, **kw)
                return bb

            # plinth
            fbox("Walls-col", "sandstone", a0, a1, 0, 0.55, 0, 0.1, scale=2.4)
            hh = H[r, c]
            trim = "plaster" if MATG[r][c] == "sandstone" else "sandstone"
            if nt in OPEN:
                # exterior corner quoins where the wall turns into open space
                for end, (ddr, ddc), s2 in ((a0, (-1, 0) if ax == "z" else (0, -1), -1), (a1, (1, 0) if ax == "z" else (0, 1), 1)):
                    if ctype(r + ddr, c + ddc) in OPEN:
                        key = (round(fx, 2), round(end, 2), ax)
                        if key not in QUOINS:
                            QUOINS.add(key)
                            quoins(ax, fx, out, end, s2, hh)
                if hh > 6:   # string course
                    fbox("Walls-col", trim, a0, a1, 3.05, 3.2, 0, 0.09, scale=3)
                if VIGA.get(BID[r, c]) and hh >= 7:   # protruding roof beams
                    for sb in (a0 + 0.5, a0 + 1.5):
                        fbox("Decor", "beam", sb - 0.08, sb + 0.08, hh - 1.05, hh - 0.89, 0, 0.38, scale=1)
                roll = rng3.random()
                m = (a0 + a1) / 2
                if roll < 0.16:
                    arched_door(fbox, ax, fx, out, m, trim)
                elif hh > 6.4 and roll < 0.27:
                    balcony(fbox, a0, a1)
                elif hh > 6 and roll < 0.72:
                    wy = 3.6 + (rng3.random() < 0.4) * 1.1
                    window(fbox, m, wy, trim, ["shutters", "grille", "cross"][int(rng3.integers(3))])
                    if rng3.random() < 0.25:  # awning
                        fbox("Decor", "cloth", m - 0.75, m + 0.75, wy + 1.55, wy + 1.62, 0, 0.7, scale=2)
            elif nt in COVER and (r * 7 + c * 3) % 3 == 0:
                m = (a0 + a1) / 2
                fbox("Decor", "metal", m - 0.05, m + 0.05, 2.75, 2.85, 0, 0.35)
                fbox("Decor", "metal", m - 0.14, m + 0.14, 2.35, 2.75, 0.25, 0.53)
                fbox("Decor", "lamp", m - 0.1, m + 0.1, 2.4, 2.7, 0.29, 0.49)
                p = (m, 2.55, fx + out * 0.39) if ax == "x" else (fx + out * 0.39, 2.55, m)
                lamp_positions.append(p)

# ---------------------------------------------------------------- ceilings
for r in range(G):
    for c in range(G):
        t = grid[r][c]
        if t in COVER:
            h = COVER[t]
            box("Walls-col", "plaster", cx(c), h, cz(r), cx(c) + CS, h + SLAB, cz(r) + CS, scale=3, bottom=True)
            COL.append(("stone", cx(c), h, cz(r), cx(c) + CS, h + SLAB + 0.05, cz(r) + CS))
            CLIP_P.append((cx(c), h + SLAB + 0.05, cz(r), cx(c) + CS, 12.0, cz(r) + CS))
            box("Walls-col", "roof" if t in "TC" else "plaster", cx(c), h + SLAB, cz(r), cx(c) + CS, h + SLAB + 0.05, cz(r) + CS, scale=2)

# wooden beams in spawns (auto from layout)
for t in "TC":
    cells = [(r, c) for r in range(G) for c in range(G) if grid[r][c] == t]
    r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
    c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
    h = COVER[t]
    x = cx(c0) + 0.9
    while x < cx(c1 + 1) - 0.5:
        box("Decor", "beam", x - 0.14, h - 0.32, cz(r0), x + 0.14, h, cz(r1 + 1), scale=1.2)
        x += 1.6

# ---------------------------------------------------------------- arches on region boundaries
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
    ha, hb = COVER.get(a), COVER.get(b)
    hs = [h for h in (ha, hb) if h is not None]
    top = max(hs) + SLAB + (0.5 if len(hs) == 1 else 0.0)
    apex = min(hs) - 0.35
    span_r = None
    for g in groups:
        g0 = cx(g[0]) if dr else cz(g[0])
        g1 = cx(g[-1] + 1) if dr else cz(g[-1] + 1)
        ln = cz(line) if dr else cx(line)
        spring = max(2.4, apex - (g1 - g0) / 2)
        for se, sg in ((g0, 1), (g1, -1)):
            p0, p1 = sorted((se, se + sg * 0.16))
            c0_, c1_ = sorted((se, se + sg * 0.26))
            for (q0, q1, y0, y1, dd) in ((p0, p1, 0.0, spring - 0.22, 0.45), (c0_, c1_, spring - 0.22, spring, 0.52)):
                bb = (q0, y0, ln - dd, q1, y1, ln + dd) if dr else (ln - dd, y0, q0, ln + dd, y1, q1)
                box("Walls-col", "sandstone", *bb, scale=2.4)
                COL.append(("stone", *bb))
    for g in groups:
        if dr:  # boundary along x at z = line
            arch_wall("Walls-col", "x", cz(line), 0.7, cx(g[0]), cx(g[-1] + 1), top, apex)
        else:
            arch_wall("Walls-col", "z", cx(line), 0.7, cz(g[0]), cz(g[-1] + 1), top, apex)

# ribs in straight corridors (auto)
for t in ",m":
    h = COVER[t]
    for r in range(1, G - 1):          # N-S corridors -> rib spans x
        c = 0
        while c < G:
            if grid[r][c] == t:
                c0 = c
                while c < G and grid[r][c] == t:
                    c += 1
                c1 = c - 1
                if (c1 - c0 < 3 and ctype(r, c0 - 1) == "#" and ctype(r, c1 + 1) == "#" and r % 2 == 0
                        and all(ctype(r - 1, k) == t and ctype(r + 1, k) == t for k in range(c0, c1 + 1))):
                    arch_wall("Walls-col", "x", cz(r) + 1, 0.45, cx(c0), cx(c1 + 1), h, h - 0.25)
            else:
                c += 1
    for c in range(1, G - 1):          # E-W corridors -> rib spans z
        r = 0
        while r < G:
            if grid[r][c] == t:
                r0 = r
                while r < G and grid[r][c] == t:
                    r += 1
                r1 = r - 1
                if (r1 - r0 < 3 and ctype(r0 - 1, c) == "#" and ctype(r1 + 1, c) == "#" and c % 2 == 0
                        and all(ctype(k, c - 1) == t and ctype(k, c + 1) == t for k in range(r0, r1 + 1))):
                    arch_wall("Walls-col", "z", cx(c) + 1, 0.45, cz(r0), cz(r1 + 1), h, h - 0.25)
            else:
                r += 1

# ---------------------------------------------------------------- props


def crate(x, z, s=1.1, y=0.0, yaw=0.0, green=False):
    if y == 0:
        FP.append((x - s / 2, z - s / 2, x + s / 2, z + s / 2))
    COL.append(("metal" if green else "wood", x - s / 2, y, z - s / 2, x + s / 2, y + s, z + s / 2))
    box("Props-col", "green" if green else "crate", x - s / 2, y, z - s / 2, x + s / 2, y + s, z + s / 2,
        unit=True, yaw=yaw, bottom=False)


def stack(x, z, pattern, yaw=0.0):
    for (dx, dz, lvl, s, g) in pattern:
        crate(x + dx, z + dz, s, lvl, yaw + rng.normal(0, 0.05), g)


def barrel(x, z, mat="beam"):
    FP.append((x - .4, z - .4, x + .4, z + .4))
    COL.append(("metal" if mat == "green" else "wood", x - .4, 0.0, z - .4, x + .4, 0.9, z + .4))
    prof = [(0.0, 0), (0.33, 0), (0.38, 0.25), (0.40, 0.45), (0.38, 0.65), (0.33, 0.9), (0.0, 0.9)]
    lathe("Props-col", mat, x, 0, z, prof, 14, 1.5)
    for y in (0.2, 0.7):
        lathe("Decor", "metal", x, 0, z, [(0.395, y), (0.405, y + 0.04), (0.395, y + 0.08)], 14)


def urn(x, z, s=1.0):
    FP.append((x - .34 * s, z - .34 * s, x + .34 * s, z + .34 * s))
    COL.append(("stone", x - .3 * s, 0.0, z - .3 * s, x + .3 * s, 1.0 * s, z + .3 * s))
    prof = [(0.0, 0), (0.18 * s, 0), (0.30 * s, 0.25 * s), (0.34 * s, 0.45 * s), (0.25 * s, 0.75 * s), (0.14 * s, 0.9 * s), (0.18 * s, 0.98 * s), (0.12 * s, 1.0 * s)]
    lathe("Props-col", "clay", x, 0, z, prof, 16, 1.5)


def platform(x0, z0, x1, z1, h, stair_dir):
    FP_PLAT.append((x0, z0, x1, z1, h))
    COL.append(("stone", x0, 0.0, z0, x1, h, z1))
    box("Props-col", "sandstone", x0, 0, z0, x1, h, z1, scale=2.4)
    box("Decor", "plaster", x0 - .05, h - .1, z0 - .05, x1 + .05, h + .05, z1 + .05, scale=3)
    steps = 4
    # invisible collision ramp over the steps (Godot: -colonly)
    L = steps * 0.35 + 0.35
    zA, zB = z0 + 0.3, z1 - 0.3
    if stair_dir == "+x":
        xa, xb = x1 + L, x1
    else:
        xa, xb = x0 - L, x0
    top = [(xb, h, zA), (xb, h, zB), (xa, 0, zB), (xa, 0, zA)]
    RAMPS.append(("stone", [(xb, h, zA), (xb, h, zB), (xa, 0, zB), (xa, 0, zA), (xb, 0, zA), (xb, 0, zB)]))
    quad("Ramps-colonly", "dark", top, [(0, 0), (1, 0), (1, 1), (0, 1)], np.array([0, 1, 0]))
    quad("Ramps-colonly", "dark", [(xb, 0, zA), (xb, 0, zB), (xb, h, zB), (xb, h, zA)], [(0, 0), (1, 0), (1, 1), (0, 1)], np.array([1 if stair_dir == "-x" else -1, 0, 0]))
    for i in range(steps):
        sh = h * (i + 1) / (steps + 1)
        d = (steps - i) * 0.35
        if stair_dir == "+x":
            box("Props-col", "sandstone", x1, 0, z0 + 0.3, x1 + d, sh, z1 - 0.3, scale=2.4)
        else:
            box("Props-col", "sandstone", x0 - d, 0, z0 + 0.3, x0, sh, z1 - 0.3, scale=2.4)


def palm(x, z, h=7.5, lean=(0.3, 0.2)):
    FP.append((x - .28, z - .28, x + .28, z + .28))
    COL.append(("wood", x - .22, 0.0, z - .22, x + .22, h * 0.9, z + .22))
    segs = 10
    prev = None
    for i in range(segs + 1):
        t = i / segs
        px = x + lean[0] * t * t * h * 0.25
        pz = z + lean[1] * t * t * h * 0.25
        py = t * h
        r = 0.24 - 0.08 * t
        ring = [(px + r * math.cos(a), py, pz + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 9)]
        if prev:
            for k in range(8):
                quad("Decor", "bark", [prev[k], prev[k + 1], ring[k + 1], ring[k]],
                     [(k / 8, (i - 1) / 3), ((k + 1) / 8, (i - 1) / 3), ((k + 1) / 8, i / 3), (k / 8, i / 3)],
                     np.array([math.cos((k + .5) / 8 * 2 * math.pi), 0, math.sin((k + .5) / 8 * 2 * math.pi)]))
        prev = ring
    top = np.array(prev).mean(0)
    nf = 11
    for f in range(nf):
        ang = f / nf * 2 * math.pi + rng.normal(0, 0.15)
        L = 3.2 + rng.normal(0, 0.3)
        droop = 0.9 + rng.random() * 0.8
        dirv = np.array([math.cos(ang), 0, math.sin(ang)])
        side = np.array([-dirv[2], 0, dirv[0]])
        n = 8
        pts = []
        for i in range(n + 1):
            t = i / n
            p = top + dirv * L * t + np.array([0, 0.9 * t - droop * t * t * 1.8, 0])
            pts.append(p)
        for i in range(n):
            w0 = 0.55 + 0.4 * math.sin(math.pi * min(1, i / n + 0.15))
            w1 = 0.55 + 0.4 * math.sin(math.pi * min(1, (i + 1) / n + 0.15))
            a, b = pts[i], pts[i + 1]
            quad("Decor", "frond", [a - side * w0, a + side * w0, b + side * w1, b - side * w1],
                 [(0, i / n), (1, i / n), (1, (i + 1) / n), (0, (i + 1) / n)], np.array([0, 1, 0]))
    lathe("Decor", "frond_core", top[0], top[1] - 0.3, top[2], [(0.0, 0), (0.35, 0.1), (0.3, 0.45), (0.0, 0.6)], 8)


def decal(x, z, letter, size=4.4):
    s = size / 2
    quad("Decor", "site" + letter, [(x - s, 0.02, z - s), (x + s, 0.02, z - s), (x + s, 0.02, z + s), (x - s, 0.02, z + s)],
         [(0, 1), (1, 1), (1, 0), (0, 0)], np.array([0, 1, 0]))


def sandbags(x0, z0, x1, z1):
    FP.append((min(x0, x1) - .3, min(z0, z1) - .3, max(x0, x1) + .3, max(z0, z1) + .3))
    COL.append(("cloth", min(x0, x1) - .3, 0.0, min(z0, z1) - .22, max(x0, x1) + .3, 0.78, max(z0, z1) + .22))
    Ln = math.hypot(x1 - x0, z1 - z0)
    yaw = -math.atan2(z1 - z0, x1 - x0)
    n = int(Ln / 0.6)
    for row in range(3):
        for i in range(n - (row % 2)):
            t = (i + 0.5 + 0.5 * (row % 2)) / n
            px, pz = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
            box("Props-col", "cloth", px - 0.3, row * 0.26, pz - 0.2, px + 0.3, row * 0.26 + 0.26, pz + 0.2, scale=0.8, yaw=yaw)


# ---------------- v2 prop placement (cover planned for gameplay)
# --- A site: x -23..-7, z -1..13  (open, long sightlines from Long)
decal(-15.0, 8.0, "A")
stack(-17.6, 4.6, [(0, 0, 0, 1.2, False), (1.2, 0, 0, 1.2, False), (0.6, 0, 1.2, 1.2, False)])   # default
stack(-11.6, 9.6, [(0, 0, 0, 1.2, True), (0, 1.25, 0, 1.2, False)], 0.15)                        # plant cover
platform(-23.0, 7.5, -20.5, 12.8, 1.3, "+x")                                                     # A back platform
stack(-19.6, 1.3, [(0, 0, 0, 1.1, False)])                                                        # long exit cover
barrel(-8.0, 0.4); sandbags(-11.8, 2.8, -9.2, 2.8)                                                # short exit cover
stack(-9.4, 11.0, [(0, 0, 0, 1.0, False), (1.05, 0, 0, 1.0, False)], -0.1)                        # CT side
palm(-22.4, 0.3, 8.5, (0.5, -0.2)); palm(-7.9, 12.3, 7.0, (-0.3, -0.4))
# --- Long + long doors
stack(-18.2, -9.0, [(0, 0, 0, 1.1, True)]); urn(-22.3, -14.0); palm(-22.3, -6.5, 8.0, (0.4, 0.1))
stack(-20.3, -22.2, [(0, 0, 0, 1.1, False)]); barrel(-8.3, -22.3)
# --- Top mid: x -7..7, z -15..-7
stack(-5.2, -9.2, [(0, 0, 0, 1.2, False), (0, 0, 1.2, 1.0, False)])
stack(5.4, -13.2, [(0, 0, 0, 1.2, True)]); barrel(6.2, -8.2); urn(-6.3, -14.3)
palm(-6.1, -7.9, 7.5, (0.2, 0.3))
# --- Mid corridor + CT mid
crate(-4.2, -4.0, 0.9, yaw=0.2); urn(-4.4, 2.3)
stack(4.2, 9.9, [(0, 0, 0, 1.1, False), (0, 0, 1.1, 0.9, True)])                                 # CT mid pocket
barrel(-2.3, 12.3); urn(2.3, 5.8); palm(-2.2, 6.0, 7.5, (0.3, 0.2))
# --- B site: x 7..23, z -1..13 (tight, lots of close cover)
decal(16.0, 7.0, "B")
stack(12.2, 4.6, [(0, 0, 0, 1.2, False), (0, 1.25, 0, 1.2, False), (0, 0.6, 1.2, 1.2, False)], -0.1)
stack(17.8, 9.6, [(0, 0, 0, 1.3, True)])
stack(16.2, 1.4, [(0, 0, 0, 1.1, False), (1.1, 0, 0, 1.1, False)], 0.1)                          # tunnel exit cover
platform(20.8, 3.5, 23.0, 9.5, 1.3, "-x")                                                          # B back platform
barrel(8.3, 3.8); urn(8.3, 8.4, 1.1)                                                               # B doors flanks
sandbags(19.5, 11.9, 22.5, 11.9); barrel(22.3, 0.3, "green")
palm(8.0, 0.0, 8.5, (0.4, 0.3)); palm(22.2, 12.2, 7.2, (-0.4, -0.3))
# --- Tunnels
barrel(8.4, -22.3); crate(15.6, -22.2, 0.9, yaw=0.3); crate(18.2, -16.0, 0.9, yaw=0.3)
urn(11.7, -5.5); barrel(14.3, -3.2)
# --- Spawns and CT connectors
stack(-5.8, -21.9, [(0, 0, 0, 1.1, False), (1.1, 0, 0, 1.1, False)]); stack(5.9, -21.8, [(0, 0, 0, 1.2, True)])
barrel(-6.3, -17.8); barrel(6.3, -17.8); urn(0.0, -22.4, 1.2)
stack(-7.6, 19.9, [(0, 0, 0, 1.2, True)]); stack(7.4, 20.0, [(0, 0, 0, 1.1, False), (0, -1.1, 0, 1.1, False)])
barrel(-3.9, 20.3); urn(3.9, 20.4)
urn(-16.3, 18.3); crate(-10.0, 18.4, 0.9, yaw=0.2); barrel(16.3, 18.3); crate(10.0, 18.4, 0.9, yaw=-0.2)

# ---------------------------------------------------------------- materials


def tex(img):
    return img


T = TX.all_textures()
M = {}
for k in ("sandstone", "flagstone", "plaster", "beam", "crate", "green", "roof", "door", "bark"):
    img, nrm = T[k]
    M[k] = PBRMaterial(name=k, baseColorTexture=img, normalTexture=nrm, metallicFactor=0.0,
                       roughnessFactor={"green": 0.6}.get(k, 0.9))
M["dark"] = PBRMaterial(name="window_dark", baseColorFactor=[18, 14, 10, 255], metallicFactor=0, roughnessFactor=0.6)
M["metal"] = PBRMaterial(name="iron", baseColorFactor=[40, 36, 32, 255], metallicFactor=0.8, roughnessFactor=0.5)
M["lamp"] = PBRMaterial(name="lamp_glow", baseColorFactor=[255, 200, 120, 255], emissiveFactor=[1.0, 0.72, 0.38], metallicFactor=0)
M["cloth"] = PBRMaterial(name="cloth", baseColorTexture=TX.plaster()[0], baseColorFactor=[210, 190, 150, 255], metallicFactor=0, roughnessFactor=1)
M["clay"] = PBRMaterial(name="clay", baseColorTexture=TX.plaster()[0], baseColorFactor=[230, 150, 110, 255], metallicFactor=0, roughnessFactor=0.85)
M["frond"] = PBRMaterial(name="palm_frond", baseColorTexture=TX.frond(), alphaMode="MASK", alphaCutoff=0.5, doubleSided=True, metallicFactor=0, roughnessFactor=0.8)
M["frond_core"] = PBRMaterial(name="palm_core", baseColorFactor=[70, 85, 35, 255], metallicFactor=0)
M["siteA"] = PBRMaterial(name="site_A", baseColorTexture=TX.site_decal("A"), alphaMode="BLEND", metallicFactor=0, roughnessFactor=0.9)
M["siteB"] = PBRMaterial(name="site_B", baseColorTexture=TX.site_decal("B"), alphaMode="BLEND", metallicFactor=0, roughnessFactor=0.9)

CLIP_P.append((-25.0, 12.0, -25.0, 25.0, 12.5, 25.0))
CLIP_G.append((-25.0, 30.0, -25.0, 25.0, 30.5, 25.0))
for (a, b_, c_, d_) in ((-26.0, -26.0, -25.0, 26.0), (25.0, -26.0, 26.0, 26.0), (-26.0, -26.0, 26.0, -25.0), (-26.0, 25.0, 26.0, 26.0)):
    CLIP_G.append((a, 0.0, b_, c_, 30.0, d_))
    CLIP_P.append((a, 0.0, b_, c_, 12.0, d_))
scene = trimesh.Scene()
stats = 0
for (group, mat), b in sorted(bufs.items()):
    if not b.f:
        continue
    if "colonly" in group:
        continue
    V = np.array(b.v); F = np.array(b.f)
    area = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    F = F[area > 1e-9]
    mesh = trimesh.Trimesh(vertices=V, faces=F, process=False)
    mesh.visual = TextureVisuals(uv=np.array(b.uv), material=M[mat])
    stats += len(F)
    name = f"{mat}_{group.replace('-col', '')}"
    scene.add_geometry(mesh, node_name=name, geom_name=name)

scene.export("desert_map.glb", include_normals=True)
json.dump({"lamps": lamp_positions, "tris": stats, "fp": FP, "plat": FP_PLAT,
           "col": COL, "ramps": RAMPS, "clip_p": CLIP_P, "clip_g": CLIP_G,
           "t_spawn": [LY.T_SPAWN[0], 0.1, LY.T_SPAWN[1]], "ct_spawn": [LY.CT_SPAWN[0], 0.1, LY.CT_SPAWN[1]]},
          open("meta.json", "w"))
print("triangles", stats, "nodes", len(scene.geometry), "lamps", len(lamp_positions))
for row in grid:
    print("".join(row))
