"""Stage-1 gameplay analysis for the Qumtepa layout.
Computes route timings on a 0.25 m navigation grid (props included, player radius 0.35 m),
checks spawn-to-spawn line of sight, measures sightlines and draws an annotated blueprint."""
import json, math
import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from PIL import Image, ImageDraw, ImageFont
import layout as L

RES = 0.25
N = int(50 / RES)
SPEED = 4.5          # m/s  (normal run speed in player.gd)
RADIUS = 0.35
meta = json.load(open("meta.json"))
G = L.GRID


def to_px(x, z):
    return int((x + 25) / RES), int((z + 25) / RES)


# ---------------------------------------------------------------- nav grid
wall = np.zeros((N, N), bool)          # [iz, ix]
k = int(2 / RES)
for r in range(25):
    for c in range(25):
        if G[r][c] == "#":
            wall[r * k:(r + 1) * k, c * k:(c + 1) * k] = True
props = np.zeros_like(wall)
for x0, z0, x1, z1 in meta["fp"]:
    a0, b0 = to_px(x0, z0)
    a1, b1 = to_px(x1, z1)
    props[max(0, b0):b1 + 1, max(0, a0):a1 + 1] = True
blocked = wall | props
free_dist = ndimage.distance_transform_edt(~blocked) * RES
walk = free_dist > RADIUS

idx = -np.ones((N, N), int)
ys, xs = np.nonzero(walk)
idx[ys, xs] = np.arange(len(ys))
rows, cols, w = [], [], []
for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
    ok = np.zeros_like(walk)
    y0, y1 = max(0, -dy), N - max(0, dy)
    x0, x1 = max(0, -dx), N - max(0, dx)
    a = walk[y0:y1, x0:x1] & walk[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
    if dy and dx:  # no corner cutting
        a &= walk[y0 + dy:y1 + dy, x0:x1] & walk[y0:y1, x0 + dx:x1 + dx]
    yy, xx = np.nonzero(a)
    yy, xx = yy + y0, xx + x0
    rows.append(idx[yy, xx]); cols.append(idx[yy + dy, xx + dx])
    w.append(np.full(len(yy), RES * math.hypot(dy, dx)))
rows, cols, w = map(np.concatenate, (rows, cols, w))
graph = coo_matrix((np.r_[w, w], (np.r_[rows, cols], np.r_[cols, rows])), shape=(len(ys), len(ys))).tocsr()


def node(p):
    ix, iz = to_px(*p)
    if walk[iz, ix]:
        return idx[iz, ix]
    d = np.hypot(ys - iz, xs - ix)
    return int(np.argmin(d))


_cache = {}


def sp(a, b):
    na, nb = node(a), node(b)
    if na not in _cache:
        _cache[na] = dijkstra(graph, indices=na, return_predecessors=True)
    dist, pred = _cache[na]
    d = dist[nb]
    path, cur = [], nb
    while cur != na and cur >= 0:
        path.append(cur); cur = pred[cur]
    path.append(na)
    path = path[::-1]
    pts = [((xs[i] + 0.5) * RES - 25, (ys[i] + 0.5) * RES - 25) for i in path]
    return d, pts


def route(wps):
    total, pts = 0.0, []
    for a, b in zip(wps, wps[1:]):
        d, p = sp(a, b)
        total += d
        pts += p if not pts else p[1:]
    return total, pts[::4] + [pts[-1]]


results = []
for name, team, wps in L.ROUTES + [(n, t, w) for n, t, w in L.ROTATIONS]:
    d, pts = route(wps)
    results.append({"name": name, "team": team, "dist": round(d, 1), "time": round(d / SPEED, 1), "pts": [[round(x, 2), round(z, 2)] for x, z in pts]})
R = {r["name"]: r for r in results}

# ---------------------------------------------------------------- line of sight (walls only, eye height ignores props)
def visible(p, q, step=0.1):
    n = max(2, int(math.dist(p, q) / step))
    t = np.linspace(0, 1, n)
    x = p[0] + (q[0] - p[0]) * t
    z = p[1] + (q[1] - p[1]) * t
    c = np.clip(((x + 25) // 2).astype(int), 0, 24)
    r = np.clip(((z + 25) // 2).astype(int), 0, 24)
    return not any(G[rr][cc] == "#" for rr, cc in zip(r, c))


def cells_of(ch):
    pts = []
    for r in range(25):
        for c in range(25):
            if G[r][c] == ch:
                for ox in (0.3, 1.0, 1.7):
                    for oz in (0.3, 1.0, 1.7):
                        pts.append((-25 + 2 * c + ox, -25 + 2 * r + oz))
    return pts


tp, cp = cells_of("T"), cells_of("C")
spawn_los = sum(visible(a, b) for a in tp for b in cp)


def region(p):
    c, r = int((p[0] + 25) // 2), int((p[1] + 25) // 2)
    for name, (c0, c1, r0, r1) in L.CALLOUTS.items():
        if c0 <= c <= c1 and r0 <= r <= r1:
            return name
    return "?"


open_pts = [(-24 + 2 * c, -24 + 2 * r) for r in range(25) for c in range(25) if G[r][c] != "#"]
sightlines = []
for label, src in (("A plant", L.A_PLANT), ("B plant", L.B_PLANT), ("Mid doors", L.MID_DOORS), ("Top mid", (0.0, -11.0))):
    best = max((math.dist(src, q), q) for q in open_pts if visible(src, q))
    sightlines.append({"from": label, "to": region(best[1]), "m": round(best[0], 1), "p": [src, best[1]]})

# ---------------------------------------------------------------- balance summary
tA = min(R["T → A (Long)"]["time"], R["T → A (Short)"]["time"])
tB = min(R["T → B (Tunnels)"]["time"], R["T → B (Mid → Lower)"]["time"])
cA = R["CT → A"]["time"]
cB = min(R["CT → B (Ramp)"]["time"], R["CT → B (B doors)"]["time"])
summary = {
    "A_T": tA, "A_CT": cA, "A_lead": round(tA - cA, 1),
    "B_T": tB, "B_CT": cB, "B_lead": round(tB - cB, 1),
    "mid_T": R["T → Mid doors"]["time"], "mid_CT": R["CT → Mid doors"]["time"],
    "spawn_los_pairs": spawn_los,
    "walk_cells_reachable": bool(np.isfinite(dijkstra(graph, indices=node(L.T_SPAWN))).mean() > 0.97),
}
json.dump({"routes": results, "sightlines": sightlines, "summary": summary}, open("analysis.json", "w"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- blueprint image
S = 20  # px per meter
W, H = 50 * S + 560, 50 * S + 80
img = Image.new("RGB", (W, H), (236, 224, 200))
d = ImageDraw.Draw(img)
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f12, f14, f16, f22, f30 = (ImageFont.truetype(FB if s >= 22 else F, s) for s in (12, 14, 16, 22, 30))
fb14 = ImageFont.truetype(FB, 14)
fb16 = ImageFont.truetype(FB, 16)
OX, OY = 40, 40


def P(x, z):
    return OX + (x + 25) * S, OY + (z + 25) * S


COL = {"#": (92, 72, 52), ".": (226, 204, 160), ",": (196, 172, 132), "m": (190, 166, 126),
       "T": (214, 150, 90), "C": (120, 150, 190), "A": (232, 190, 160), "B": (232, 190, 160)}
for r in range(25):
    for c in range(25):
        ch = G[r][c]
        x0, y0 = P(-25 + 2 * c, -25 + 2 * r)
        d.rectangle([x0, y0, x0 + 2 * S, y0 + 2 * S], fill=COL[ch])
        if ch in ",mTC":
            for k2 in range(0, 2 * S, 8):
                d.line([x0 + k2, y0, x0, y0 + k2], fill=tuple(int(v * 0.93) for v in COL[ch]))
                d.line([x0 + 2 * S, y0 + k2, x0 + k2, y0 + 2 * S], fill=tuple(int(v * 0.93) for v in COL[ch]))
for x0, z0, x1, z1, h in meta["plat"]:
    d.rectangle([*P(x0, z0), *P(x1, z1)], fill=(205, 178, 130), outline=(120, 95, 60), width=2)
for x0, z0, x1, z1 in meta["fp"]:
    d.rectangle([*P(x0, z0), *P(x1, z1)], fill=(120, 82, 46), outline=(70, 48, 28))
for letter, p in (("A", L.A_PLANT), ("B", L.B_PLANT)):
    cxp, czp = P(*p)
    d.ellipse([cxp - 50, czp - 50, cxp + 50, czp + 50], outline=(170, 34, 22), width=5)
    d.text((cxp, czp), letter, font=ImageFont.truetype(FB, 54), fill=(170, 34, 22), anchor="mm")
for s_ in sightlines:
    d.line([P(*s_["p"][0]), P(*s_["p"][1])], fill=(90, 90, 90), width=1)
TCOL, CTCOL = (214, 96, 30), (40, 92, 170)
offs = {}
for r_ in results:
    if "rotatsiya" in r_["name"]:
        continue
    col = TCOL if r_["team"] == "T" else CTCOL
    pts = [P(x, z) for x, z in r_["pts"]]
    d.line(pts, fill=col, width=4, joint="curve")
    ex, ey = pts[-1]
    d.ellipse([ex - 6, ey - 6, ex + 6, ey + 6], fill=col)
for name, (c0, c1, r0, r1) in L.CALLOUTS.items():
    x0, y0 = P(-25 + 2 * c0, -25 + 2 * r0)
    x1, y1 = P(-25 + 2 * (c1 + 1), -25 + 2 * (r1 + 1))
    tx, ty = (x0 + x1) / 2, (y0 + y1) / 2
    if name in ("A site", "B site"):
        ty = y0 + 18
    bb = d.textbbox((tx, ty), name, font=fb14, anchor="mm")
    d.rectangle([bb[0] - 4, bb[1] - 2, bb[2] + 4, bb[3] + 2], fill=(250, 244, 230))
    d.text((tx, ty), name, font=fb14, fill=(40, 28, 18), anchor="mm")
d.rectangle([OX, OY, OX + 50 * S, OY + 50 * S], outline=(40, 28, 18), width=2)
d.text((OX, 10), "0 m", font=f12, fill=(60, 45, 30))
d.text((OX + 50 * S, 10), "50 m", font=f12, fill=(60, 45, 30), anchor="ra")

# side panel
X = OX + 50 * S + 36
y = OY
d.text((X, y), "Qumtepa v2 — 1-bosqich", font=f30, fill=(40, 28, 18)); y += 46
d.text((X, y), f"Yugurish tezligi {SPEED} m/s, o'yinchi radiusi {RADIUS} m", font=f14, fill=(90, 70, 50)); y += 34
d.text((X, y), "Yo'nalish vaqtlari", font=f22, fill=(40, 28, 18)); y += 34
for r_ in results:
    col = TCOL if r_["team"] == "T" else CTCOL
    d.rectangle([X, y + 4, X + 12, y + 16], fill=col)
    d.text((X + 22, y), r_["name"], font=f16, fill=(40, 28, 18))
    d.text((X + 470, y), f"{r_['time']:.1f} s", font=fb16, fill=(40, 28, 18), anchor="ra")
    y += 26
y += 14
d.text((X, y), "Balans", font=f22, fill=(40, 28, 18)); y += 34
for line in (f"A: CT {summary['A_lead']:+.1f} s oldin yetadi",
             f"B: CT {summary['B_lead']:+.1f} s oldin yetadi",
             f"Mid doors: T {summary['mid_T']} s / CT {summary['mid_CT']} s",
             "Spawn → spawn ko'rinish: " + ("YO'Q ✓" if spawn_los == 0 else f"{spawn_los} ta chiziq ✗")):
    d.text((X, y), line, font=f16, fill=(40, 28, 18)); y += 26
y += 14
d.text((X, y), "Eng uzun ko'rinish chiziqlari", font=f22, fill=(40, 28, 18)); y += 34
for s_ in sightlines:
    d.text((X, y), f"{s_['from']} → {s_['to']}: {s_['m']} m", font=f16, fill=(40, 28, 18)); y += 26
y += 14
for col, txt in (((226, 204, 160), "Ochiq osmon"), ((196, 172, 132), "Yopiq yo'lak / zal"), ((92, 72, 52), "Bino"),
                 ((120, 82, 46), "Pana (quti, bochka)"), ((205, 178, 130), "Baland platforma")):
    d.rectangle([X, y + 3, X + 16, y + 17], fill=col, outline=(60, 45, 30))
    d.text((X + 26, y), txt, font=f14, fill=(40, 28, 18)); y += 24
img.save("blueprint_v2.png")
print(json.dumps(summary, ensure_ascii=False, indent=1))
for r_ in results:
    print(f"{r_['name']:32s} {r_['dist']:6.1f} m  {r_['time']:5.1f} s")
for s_ in sightlines:
    print(s_["from"], "->", s_["to"], s_["m"])
