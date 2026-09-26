"""Qumtepa 5v5 — 1-bosqich tahlili.

layout5.py dagi rejani tekshiradi: yo'l vaqtlari (panalar va o'yinchi radiusi hisobga olingan),
spawn adolatliligi, ko'rish chiziqlari, birinchi to'qnashuv vaqti, spawn xavfsizligi, smoke rejasi,
callout'lar, zonalar. Natija: docs/analysis_stage1.json, docs/blueprint_stage1.png, docs/contact_stage1.png.

Ishga tushirish:  cd qumtepa-5v5/tools && python3 analyze5.py
Kerak: numpy, scipy, pillow. Xato bo'lsa chiqish kodi 1.
"""
import json, math, os, sys
import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from PIL import Image, ImageDraw, ImageFont
import layout5 as L

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs")
SPEED = 4.5              # m/s — player.gd dagi oddiy yugurish
RADIUS = 0.35            # o'yinchi radiusi
EYE_BLOCK = 1.7          # shundan baland narsa turgan o'yinchining ko'rishini to'sadi
RES = 0.25
SIZE = L.G * L.CELL
N = int(SIZE / RES)
OPEN_SKY = set(".AB")

# ------------------------------------------------------------------ rastr
def px(x, z):
    return int((x - L.ORIGIN) / RES), int((z - L.ORIGIN) / RES)


def rect_mask(mask, x0, z0, x1, z1, val=True):
    a0, b0 = px(min(x0, x1), min(z0, z1))
    a1, b1 = px(max(x0, x1), max(z0, z1))
    mask[max(b0, 0):min(b1, N), max(a0, 0):min(a1, N)] = val


wall = np.zeros((N, N), bool)
K = int(L.CELL / RES)
for r in range(L.G):
    for c in range(L.G):
        if L.grid[r][c] == "#":
            wall[r * K:(r + 1) * K, c * K:(c + 1) * K] = True

props_block = np.zeros((N, N), bool)   # harakatni to'sadi
props_sight = np.zeros((N, N), bool)   # ko'rishni to'sadi
prop_boxes = []                        # (tur, x0, z0, x1, z1, balandlik) — chizish va tekshirish uchun
platforms = []
for p in L.PROPS:
    kind = p[0]
    if kind == "stack":
        _, x, z, pat, _yaw = p
        for dx, dz, y, s, _g in pat:
            b = (x + dx - s / 2, z + dz - s / 2, x + dx + s / 2, z + dz + s / 2)
            if y == 0:
                rect_mask(props_block, *b)
            if y + s >= EYE_BLOCK:
                rect_mask(props_sight, *b)
            prop_boxes.append(("crate", *b, y + s))
    elif kind == "crate":
        _, x, z, s, _yaw = p
        b = (x - s / 2, z - s / 2, x + s / 2, z + s / 2)
        rect_mask(props_block, *b); prop_boxes.append(("crate", *b, s))
    elif kind in ("barrel", "urn", "palm"):
        rr = {"barrel": .4, "urn": .34, "palm": .28}[kind]
        x, z = p[1], p[2]
        b = (x - rr, z - rr, x + rr, z + rr)
        rect_mask(props_block, *b); prop_boxes.append((kind, *b, {"barrel": .9, "urn": 1.0, "palm": 8.0}[kind]))
    elif kind == "sandbags":
        _, x0, z0, x1, z1 = p
        b = (min(x0, x1) - .3, min(z0, z1) - .3, max(x0, x1) + .3, max(z0, z1) + .3)
        rect_mask(props_block, *b); prop_boxes.append(("sandbags", *b, .78))
    elif kind == "wall":
        _, x0, z0, x1, z1, h = p
        rect_mask(props_block, x0, z0, x1, z1); rect_mask(props_sight, x0, z0, x1, z1)
        prop_boxes.append(("wall", x0, z0, x1, z1, h))
    elif kind == "platform":
        _, x0, z0, x1, z1, h, d = p
        platforms.append((x0, z0, x1, z1, h, d))
        prop_boxes.append(("platform", x0, z0, x1, z1, h))

blocked = wall | props_block
# o'yinchi markazi devordan kamida RADIUS uzoqda bo'lishi kerak
walk = ndimage.distance_transform_edt(~blocked) * RES > RADIUS
sight_block = wall | props_sight

# ------------------------------------------------------------------ navigatsiya grafi
idx = -np.ones((N, N), np.int64)
ys, xs = np.nonzero(walk)
idx[ys, xs] = np.arange(len(ys))
rows, cols, w = [], [], []
for dy, dx, d in [(0, 1, 1.0), (1, 0, 1.0), (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2))]:
    y2, x2 = ys + dy, xs + dx
    ok = (y2 < N) & (x2 >= 0) & (x2 < N)
    ok[ok] &= walk[y2[ok], x2[ok]]
    if dx and dy:
        ok[ok] &= walk[ys[ok], x2[ok]] & walk[y2[ok], xs[ok]]
    rows.append(idx[ys[ok], xs[ok]]); cols.append(idx[y2[ok], x2[ok]]); w.append(np.full(ok.sum(), d * RES))
rows, cols, w = map(np.concatenate, (rows, cols, w))
graph = coo_matrix((np.r_[w, w], (np.r_[rows, cols], np.r_[cols, rows])), shape=(len(ys),) * 2).tocsr()
labels, ncomp = ndimage.label(walk, structure=np.ones((3, 3)))


def node(p):
    n = _node(p)
    if n is None:
        raise ValueError(f"nuqta {p} yuriladigan joyda emas")
    return n


def _node(p):
    ix, iz = px(*p)
    if 0 <= ix < N and 0 <= iz < N and walk[iz, ix]:
        return idx[iz, ix]
    d = np.hypot(ys - iz, xs - ix)
    j = int(np.argmin(d))
    return j if d[j] * RES < 0.8 else None


_cache = {}


def field(p):
    n = node(p)
    if n not in _cache:
        _cache[n] = dijkstra(graph, indices=n, return_predecessors=True)
    return _cache[n]


def sp(a, b):
    na, nb = node(a), node(b)
    dist, pred = field(a)
    path, cur = [], nb
    while cur != na and cur >= 0:
        path.append(cur); cur = pred[cur]
    path.append(na)
    return dist[nb], [((xs[i] + .5) * RES + L.ORIGIN, (ys[i] + .5) * RES + L.ORIGIN) for i in path[::-1]]


def route(wps):
    tot, pts = 0.0, []
    for a, b in zip(wps, wps[1:]):
        d, p = sp(a, b); tot += d; pts += p
    return tot, pts


def tmap(p):
    """butun xarita bo'yicha p dan vaqt (s), yetib bo'lmasa inf"""
    t = np.full((N, N), np.inf)
    t[ys, xs] = field(p)[0] / SPEED
    return t


# ------------------------------------------------------------------ callout'lar
name_of = {n: L.ALIASES.get(n, n) for n, *_ in L.ZONES}
CNAMES = [""]
cgrid = [[0] * L.G for _ in range(L.G)]


def cid(n):
    if n not in CNAMES:
        CNAMES.append(n)
    return CNAMES.index(n)


for n, c0, r0, c1, r1, _ in L.ZONES:
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            cgrid[r][c] = cid(name_of[n])
for n, x0, z0, x1, z1 in L.CALLOUT_SPLITS:
    for r in range(L.G):
        for c in range(L.G):
            x, z = L.m(c, r)
            if L.grid[r][c] != "#" and x0 <= x <= x1 and z0 <= z <= z1:
                cgrid[r][c] = cid(n)


def callout(p):
    c, r = int((p[0] - L.ORIGIN) // L.CELL), int((p[1] - L.ORIGIN) // L.CELL)
    return CNAMES[cgrid[r][c]] if 0 <= r < L.G and 0 <= c < L.G else ""


def ctype(p):
    c, r = int((p[0] - L.ORIGIN) // L.CELL), int((p[1] - L.ORIGIN) // L.CELL)
    return L.grid[r][c]


# ------------------------------------------------------------------ tekshiruvlar
checks = []


def check(ok, msg):
    checks.append((bool(ok), msg))


def rng(v, lo, hi):
    return lo <= v <= hi


# 1) yo'llar
routes = {}
for name, team, wps in L.ROUTES + L.ROTATIONS:
    d, pts = route(wps)
    routes[name] = {"team": team, "dist": round(d, 1), "time": round(d / SPEED, 1), "pts": pts}
RT = lambda n: routes[n]["time"]
TG = L.TARGETS
t_lanes = [RT(n) for n in ("T → A (Long)", "T → A (Short)", "T → B (Tunnels)", "T → B (Window)")]
for n in ("T → A (Long)", "T → A (Short)", "T → B (Tunnels)", "T → B (Window)"):
    check(rng(RT(n), *TG["t_lane"]), f"{n}: {RT(n)} s (maqsad {TG['t_lane'][0]}–{TG['t_lane'][1]} s)")
check(max(t_lanes) - min(t_lanes) <= TG["t_lane_spread"],
      f"T yo'llari farqi {max(t_lanes) - min(t_lanes):.1f} s (≤ {TG['t_lane_spread']} s)")
ct = {n: RT(n) for n in ("CT → A (Ramp)", "CT → A (CT mid)", "CT → B (Ramp)", "CT → B (B doors)")}
for n, v in ct.items():
    check(rng(v, *TG["ct_site"]), f"{n}: {v} s (maqsad {TG['ct_site'][0]}–{TG['ct_site'][1]} s)")
ctA, ctB = min(ct["CT → A (Ramp)"], ct["CT → A (CT mid)"]), min(ct["CT → B (Ramp)"], ct["CT → B (B doors)"])
check(abs(ctA - ctB) <= TG["ct_ab_diff"], f"CT: A {ctA} s, B {ctB} s — farq {abs(ctA - ctB):.1f} s (≤ {TG['ct_ab_diff']} s)")
tA, tB = min(RT("T → A (Long)"), RT("T → A (Short)")), min(RT("T → B (Tunnels)"), RT("T → B (Window)"))
check(tA - ctA >= TG["ct_lead"] and tB - ctB >= TG["ct_lead"],
      f"CT site'ga oldin yetadi: A da {tA - ctA:.1f} s, B da {tB - ctB:.1f} s (≥ {TG['ct_lead']} s)")
check(abs(tA - tB) <= 1.0, f"T uchun A ({tA} s) va B ({tB} s) farqi {abs(tA - tB):.1f} s (≤ 1.0 s)")
gap = RT("T → Mid doors") - RT("CT → Mid doors")
check(rng(gap, *TG["mid_gap"]), f"Mid doors: CT {gap:.1f} s oldin (maqsad {TG['mid_gap'][0]}–{TG['mid_gap'][1]} s)")
check(RT("CT rotatsiya A → B") < RT("T rotatsiya Long → Tunnels"),
      f"Rotatsiya: CT {RT('CT rotatsiya A → B')} s < T {RT('T rotatsiya Long → Tunnels')} s")
check(RT("CT rotatsiya A → B") + L.ROUND["defuse_time"] + 5 <= L.ROUND["bomb_timer"],
      f"Qaytarib olish: rotatsiya {RT('CT rotatsiya A → B')} s + zararsizlantirish {L.ROUND['defuse_time']} s + 5 s zaxira ≤ bomba {L.ROUND['bomb_timer']} s")

# 2) spawn adolatliligi
EXITS = {"T": {"Long doors": (-20.0, -42.0), "T ramp g'arb": (-7.0, -37.0), "T ramp sharq": (7.0, -37.0), "Upper tunnels": (20.0, -42.0)},
         "CT": {"CT mid g'arb": (-9.0, 33.0), "CT mid sharq": (9.0, 33.0), "A ramp yo'li": (-21.0, 41.0), "B ramp yo'li": (21.0, 41.0)}}
spawn_rep = {}
for team, slots in L.SPAWNS.items():
    rep = []
    for s in slots:
        dist = field(s)[0]
        ex = {n: round(dist[node(p)] / SPEED, 2) for n, p in EXITS[team].items()}
        rep.append({"pos": s, "exits": ex, "nearest_exit_s": min(ex.values()),
                    "A_s": round(dist[node(L.A_PLANT)] / SPEED, 2), "B_s": round(dist[node(L.B_PLANT)] / SPEED, 2)})
        check(walk[px(*s)[1], px(*s)[0]], f"{team} spawn {s} bo'sh joyda")
        bz = L.BUY_ZONES[team]
        check(bz[0] <= s[0] <= bz[2] and bz[1] <= s[1] <= bz[3], f"{team} spawn {s} sotib olish zonasida")
    sp_ = max(r["nearest_exit_s"] for r in rep) - min(r["nearest_exit_s"] for r in rep)
    check(sp_ <= TG["spawn_exit_spread"], f"{team}: 5 spawn joyidan eng yaqin chiqishgacha farq {sp_:.2f} s (≤ {TG['spawn_exit_spread']} s)")
    spawn_rep[team] = {"slots": rep, "nearest_exit_spread_s": round(sp_, 2)}

# 3) zonalar, nuqtalar, bog'lanish
for s, p in (("A", L.A_PLANT), ("B", L.B_PLANT)):
    z = L.BOMB_ZONES[s]
    check(z[0] <= p[0] <= z[2] and z[1] <= p[1] <= z[3] and ctype(p) == s, f"{s} plant nuqtasi bomba zonasi ichida")
    zc = sum(1 for r in range(L.G) for c in range(L.G) if L.grid[r][c] == s and z[0] <= L.m(c, r)[0] <= z[2] and z[1] <= L.m(c, r)[1] <= z[3])
    check(zc >= 80, f"{s} bomba zonasi {zc * 4} m² (≥ 320 m²)")
main_lbl = labels[px(*L.T_SPAWN)[1], px(*L.T_SPAWN)[0]]
sizes = ndimage.sum(np.ones_like(labels), labels, range(1, ncomp + 1)) * RES * RES
islands = [s for i, s in enumerate(sizes, 1) if i != main_lbl and s > 1.0]
check(labels[px(*L.CT_SPAWN)[1], px(*L.CT_SPAWN)[0]] == main_lbl and not islands,
      f"Butun xarita bitta bog'langan hudud (ajralib qolgan joy > 1 m²: {len(islands)})")
tT, tC = tmap(L.T_SPAWN), tmap(L.CT_SPAWN)
ai_rep = []
for n, kind, team, x, z in L.AI_POINTS:
    nd = _node((x, z))
    ok = nd is not None and np.isfinite(field(L.T_SPAWN if team == "T" else L.CT_SPAWN)[0][nd])
    ai_rep.append({"label": n, "kind": kind, "team": team, "pos": [x, z], "reachable": bool(ok),
                   "from_spawn_s": round(float(field(L.T_SPAWN if team == "T" else L.CT_SPAWN)[0][nd]) / SPEED, 1) if ok else None,
                   "callout": callout((x, z))})
bad_ai = [a["label"] for a in ai_rep if not a["reachable"]]
check(not bad_ai, f"{len(L.AI_POINTS)} ta bot nuqtasiga yetib boriladi" + (f" (yetib bo'lmaydi: {bad_ai})" if bad_ai else ""))
bad_props = [b for b in prop_boxes if b[0] != "wall" and wall[px((b[1] + b[3]) / 2, (b[2] + b[4]) / 2)[1], px((b[1] + b[3]) / 2, (b[2] + b[4]) / 2)[0]]]
check(not bad_props, f"{len(L.PROPS)} ta pana/obyekt bino ichida emas" + (f" ({bad_props})" if bad_props else ""))
no_callout = [(c, r) for r in range(L.G) for c in range(L.G) if L.grid[r][c] != "#" and cgrid[r][c] == 0]
check(not no_callout, f"Har bir yuriladigan katakning callout nomi bor ({len(CNAMES) - 1} ta nom)")

# 4) ko'rish chiziqlari — 1 m to'rda, ko'z darajasida
STEP = 1.0
gx = np.arange(L.ORIGIN + STEP / 2, L.ORIGIN + SIZE, STEP)
PX, PZ = np.meshgrid(gx, gx)
ii = ((PX - L.ORIGIN) / RES).astype(int); jj = ((PZ - L.ORIGIN) / RES).astype(int)
ok = walk[jj, ii]
P = np.stack([PX[ok], PZ[ok]], 1)
PT, PC = tT[jj[ok], ii[ok]], tC[jj[ok], ii[ok]]
M = len(P)


def visible_from(p, Q):
    d = np.hypot(Q[:, 0] - p[0], Q[:, 1] - p[1])
    n = int(np.ceil(d.max() / (RES * 0.9))) + 1
    t = np.linspace(0, 1, n)[None, :]
    sx = p[0] + (Q[:, 0:1] - p[0]) * t
    sz = p[1] + (Q[:, 1:2] - p[1]) * t
    a = ((sx - L.ORIGIN) / RES).astype(int).clip(0, N - 1)
    b = ((sz - L.ORIGIN) / RES).astype(int).clip(0, N - 1)
    hit = sight_block[b, a]
    # har bir chiziq faqat o'z uzunligigacha tekshiriladi
    hit &= (t * d[:, None] <= d[:, None])
    return ~hit.any(1), d


def visible_line(p, q, smoke=None):
    v, _ = visible_from(np.array(p), np.array([q]))
    if not v[0]:
        return False
    if smoke is not None:
        return seg_dist(p, q, smoke) > L.SMOKE_R
    return True


def seg_dist(p, q, c):
    p, q, c = map(np.array, (p, q, c))
    d = q - p
    t = np.clip(np.dot(c - p, d) / max(np.dot(d, d), 1e-9), 0, 1)
    return float(np.linalg.norm(p + t * d - c))


# kichikroq to'r bilan butun juftliklar (2 m) — to'qnashuv va ko'rish chiziqlari
sub = np.zeros(M, bool)
sub[((P[:, 0] - L.ORIGIN) % 2.0 < 1.0) & ((P[:, 1] - L.ORIGIN) % 2.0 < 1.0)] = True
Q = P[sub]; QT, QC = PT[sub], PC[sub]
def side(tt, tc):
    """1 — T hududi, -1 — CT hududi, 0 — talashuvli (farq 3 s dan kam)"""
    return np.where(tt + 3.0 < tc, 1, np.where(tc + 3.0 < tt, -1, 0))


QS = side(QT, QC)
inbuy = lambda p, t: L.BUY_ZONES[t][0] <= p[0] <= L.BUY_ZONES[t][2] and L.BUY_ZONES[t][1] <= p[1] <= L.BUY_ZONES[t][3]
contact = np.full(len(Q), np.inf)       # shu nuqtada eng erta mumkin bo'lgan otishma vaqti
first = (np.inf, None, None)
spawn_safe = {"T": (np.inf, None, None), "CT": (np.inf, None, None)}
longest = (0.0, None, None)
long_by_callout = {}
for i in range(len(Q)):
    vis, d = visible_from(Q[i], Q)
    if not vis.any():
        continue
    # T i-da, CT j-da   va   CT i-da, T j-da
    c1 = np.where(vis, np.maximum(QT[i], QC), np.inf)
    c2 = np.where(vis, np.maximum(QC[i], QT), np.inf)
    contact[i] = min(c1.min(), c2.min())
    j = int(np.argmin(c1))
    if c1[j] < first[0]:
        first = (float(c1[j]), tuple(Q[i]), tuple(Q[j]))
    if inbuy(Q[i], "T"):
        v = np.where(vis, QC, np.inf).min()
        if v < spawn_safe["T"][0]:
            spawn_safe["T"] = (float(v), tuple(Q[i]), tuple(Q[int(np.argmin(np.where(vis, QC, np.inf)))]))
    if inbuy(Q[i], "CT"):
        v = np.where(vis, QT, np.inf).min()
        if v < spawn_safe["CT"][0]:
            spawn_safe["CT"] = (float(v), tuple(Q[i]), tuple(Q[int(np.argmin(np.where(vis, QT, np.inf)))]))
    side_i = side(QT[i], QC[i])
    dm = np.where(vis & ~((side_i != 0) & (QS == side_i)), d, 0)
    j = int(np.argmax(dm))
    if dm[j] > longest[0]:
        longest = (float(dm[j]), tuple(Q[i]), tuple(Q[j]))
    co = callout(Q[i])
    if dm[j] > long_by_callout.get(co, (0,))[0]:
        long_by_callout[co] = (float(dm[j]), callout(Q[j]))

fc, fa, fb = first
check(fc >= TG["first_contact"],
      f"Birinchi to'qnashuv {fc:.1f} s da: T {callout(fa)} ↔ CT {callout(fb)} (≥ {TG['first_contact']} s)")
for team in ("T", "CT"):
    v, p, q = spawn_safe[team]
    check(v >= TG["spawn_safe"], f"{team} spawn zonasini dushman eng erta {v:.1f} s da ko'radi — {callout(p)} ↔ {callout(q)} (≥ {TG['spawn_safe']} s)")
check(longest[0] <= TG["max_sightline"],
      f"Eng uzun talashuvli ko'rish chizig'i {longest[0]:.1f} m: {callout(longest[1])} ↔ {callout(longest[2])} (≤ {TG['max_sightline']} m)")

# 5) smoke rejasi
smoke_rep = []
for name, team, tgt, throw, lines in L.SMOKES:
    t_throw = (tT if team == "T" else tC)[px(*throw)[1], px(*throw)[0]]
    dist = math.hypot(tgt[0] - throw[0], tgt[1] - throw[1])
    ok_lines = [visible_line(a, b) and seg_dist(a, b, tgt) <= L.SMOKE_R for a, b in lines]
    rep = {"name": name, "team": team, "target": tgt, "throw_from": throw, "throw_callout": callout(throw),
           "throw_dist_m": round(dist, 1), "open_sky": ctype(tgt) in OPEN_SKY, "lines_blocked": ok_lines,
           "throw_from_s": round(float(t_throw), 1)}
    smoke_rep.append(rep)
    check(rep["open_sky"] and dist <= 45 and np.isfinite(t_throw) and all(ok_lines),
          f"Smoke \"{name}\" ({team}): {callout(throw)} dan {dist:.0f} m, {sum(ok_lines)}/{len(ok_lines)} chiziqni to'sadi")

# ------------------------------------------------------------------ natija
fails = [m for ok, m in checks if not ok]
for ok_, msg in checks:
    print(("  [OK]   " if ok_ else "  [XATO] ") + msg)
print(f"\nTekshiruvlar: {len(checks) - len(fails)} / {len(checks)}")
print("\nYo'llar:")
for n, r in routes.items():
    print(f"  {n:30s} {r['dist']:6.1f} m  {r['time']:5.1f} s")
print("\nEng uzun ko'rish chiziqlari (callout bo'yicha):")
for co, (d, to) in sorted(long_by_callout.items(), key=lambda kv: -kv[1][0])[:10]:
    print(f"  {co:22s} {d:5.1f} m  -> {to}")

os.makedirs(DOCS, exist_ok=True)
json.dump({
    "size_m": SIZE, "speed": SPEED, "round": L.ROUND, "targets": TG,
    "routes": {n: {k: v for k, v in r.items() if k != "pts"} for n, r in routes.items()},
    "spawns": spawn_rep, "ai_points": ai_rep, "smokes": smoke_rep,
    "first_contact": {"time_s": round(fc, 1), "T": list(fa), "CT": list(fb), "T_callout": callout(fa), "CT_callout": callout(fb)},
    "spawn_safety": {k: {"s": round(v[0], 1), "own": list(v[1]), "enemy": list(v[2]), "enemy_callout": callout(v[2])} for k, v in spawn_safe.items()},
    "longest_sightline": {"m": round(longest[0], 1), "from": callout(longest[1]), "to": callout(longest[2]), "p": list(longest[1]), "q": list(longest[2])},
    "longest_by_callout": {k: [round(v[0], 1), v[1]] for k, v in long_by_callout.items()},
    "callout_names": CNAMES, "callout_grid": cgrid,
    "checks": [{"ok": o, "msg": m_} for o, m_ in checks],
}, open(os.path.join(DOCS, "analysis_stage1.json"), "w"), ensure_ascii=False, indent=1)

# ------------------------------------------------------------------ rasmlar
try:
    F = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", s)
    FB = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", s)
    F(10)
except OSError:
    F = FB = lambda s: ImageFont.load_default()
S = 14                       # px / katak
PAD = 40
COL = {"#": (92, 72, 56), ".": (228, 208, 164), ",": (198, 172, 130), "m": (188, 160, 118),
       "T": (214, 160, 92), "C": (122, 160, 186), "A": (232, 184, 156), "B": (232, 184, 156)}
TCOL, CTCOL = (206, 96, 28), (36, 88, 170)


def base_map(img, dr, props=True):
    for r in range(L.G):
        for c in range(L.G):
            x, y = PAD + c * S, PAD + r * S
            dr.rectangle([x, y, x + S - 1, y + S - 1], fill=COL[L.grid[r][c]])
    if props:
        for kind, x0, z0, x1, z1, h in prop_boxes:
            a, b = P2(x0, z0); c_, d = P2(x1, z1)
            fill = {"wall": (92, 72, 56), "platform": (176, 150, 110), "sandbags": (150, 140, 110)}.get(kind, (120, 84, 52) if h >= EYE_BLOCK else (160, 116, 70))
            dr.rectangle([a, b, c_, d], fill=fill, outline=(70, 50, 36))


def P2(x, z):
    return PAD + (x - L.ORIGIN) / L.CELL * S, PAD + (z - L.ORIGIN) / L.CELL * S


def label(dr, x, z, t, size=11, bold=False):
    X, Y = P2(x, z)
    f = FB(size) if bold else F(size)
    tw = dr.textlength(t, font=f)
    dr.rectangle([X - tw / 2 - 3, Y - size / 2 - 2, X + tw / 2 + 3, Y + size / 2 + 2], fill=(252, 247, 236))
    dr.text((X - tw / 2, Y - size / 2 - 1), t, fill=(40, 30, 20), font=f)


def legend_block(dr, X, y, items):
    for col, txt in items:
        dr.rectangle([X, y + 2, X + 14, y + 16], fill=col); dr.text((X + 22, y), txt, fill=(60, 50, 40), font=F(13)); y += 21
    return y


W = PAD * 2 + L.G * S
PANEL = 560
img = Image.new("RGB", (W + PANEL, W), (234, 224, 200))
dr = ImageDraw.Draw(img)
base_map(img, dr)
for zname, rect in L.BOMB_ZONES.items():
    dr.rectangle([*P2(rect[0], rect[1]), *P2(rect[2], rect[3])], outline=(200, 40, 40), width=3)
for team, rect in L.BUY_ZONES.items():
    dr.rectangle([*P2(rect[0], rect[1]), *P2(rect[2], rect[3])], outline=(40, 150, 70), width=3)
for n, r in routes.items():
    if "rotatsiya" in n:
        continue
    dr.line([P2(*p) for p in r["pts"][::6]], fill=TCOL if r["team"] == "T" else CTCOL, width=3)
for name, team, tgt, throw, lines in L.SMOKES:
    X, Y = P2(*tgt); rr = L.SMOKE_R / L.CELL * S
    dr.ellipse([X - rr, Y - rr, X + rr, Y + rr], outline=(110, 110, 110), width=2, fill=(214, 214, 210))
for team, slots in L.SPAWNS.items():
    for k, s in enumerate(slots, 1):
        X, Y = P2(*s)
        dr.ellipse([X - 7, Y - 7, X + 7, Y + 7], fill=TCOL if team == "T" else CTCOL, outline=(255, 255, 255))
        dr.text((X - 3, Y - 7), str(k), fill=(255, 255, 255), font=FB(10))
for n, kind, team, x, z in L.AI_POINTS:
    X, Y = P2(x, z)
    colk = {"plant": (200, 40, 40), "hold": (40, 90, 170), "entry": (220, 120, 30), "retake": (30, 150, 150), "lurk": (120, 70, 160), "rotate": (150, 110, 200)}[kind]
    dr.polygon([(X, Y - 6), (X - 5, Y + 4), (X + 5, Y + 4)], fill=colk)
for s, p in (("A", L.A_PLANT), ("B", L.B_PLANT)):
    X, Y = P2(*p); dr.text((X - 10, Y - 17), s, fill=(170, 30, 30), font=FB(30))
shown = set()
for n, c0, r0, c1, r1, _ in L.ZONES:
    nm = name_of[n]
    if nm in shown or nm in ("T spawn", "CT spawn", "A site", "B site"):
        continue
    shown.add(nm)
    label(dr, *L.m((c0 + c1) / 2, (r0 + r1) / 2), nm)
for n, x0, z0, x1, z1 in L.CALLOUT_SPLITS:
    label(dr, (x0 + x1) / 2, (z0 + z1) / 2 + (2.5 if "platforma" in n else 0), n, 10)
for n, p in (("T spawn", (0, -41.5)), ("CT spawn", (0, 46.5)), ("A site", (-40, 24)), ("B site", (40, 24))):
    label(dr, *p, n, 12, True)
dr.text((PAD, 14), "0 m", fill=(60, 50, 40), font=F(12)); dr.text((PAD + L.G * S - 44, 14), f"{SIZE:.0f} m", fill=(60, 50, 40), font=F(12))
X, y = W + 10, PAD
dr.text((X, y), "Qumtepa 5v5 — 1-bosqich", fill=(40, 30, 20), font=FB(24)); y += 34
dr.text((X, y), f"2D blokaut · {SIZE:.0f} × {SIZE:.0f} m · tezlik {SPEED} m/s", fill=(90, 70, 50), font=F(14)); y += 30
dr.text((X, y), "Yo'l vaqtlari", fill=(40, 30, 20), font=FB(16)); y += 24
for n, r in routes.items():
    dr.text((X, y), n, fill=TCOL if r["team"] == "T" else CTCOL, font=F(13))
    dr.text((X + 290, y), f"{r['time']:5.1f} s", fill=(40, 30, 20), font=FB(13)); y += 19
y += 10
dr.text((X, y), "Muvozanat", fill=(40, 30, 20), font=FB(16)); y += 24
for t in (f"Birinchi to'qnashuv: {fc:.1f} s ({callout(fa)} ↔ {callout(fb)})",
          f"Spawn xavfsizligi: T {spawn_safe['T'][0]:.1f} s, CT {spawn_safe['CT'][0]:.1f} s",
          f"Eng uzun ko'rish chizig'i: {longest[0]:.0f} m",
          f"Raund {L.ROUND['round_time']:.0f} s, bomba {L.ROUND['bomb_timer']:.0f} s, tayyorgarlik {L.ROUND['freeze']:.0f} s",
          f"Tekshiruvlar: {len(checks) - len(fails)} / {len(checks)}"):
    dr.text((X, y), t, fill=(60, 50, 40), font=F(13)); y += 19
y += 12
y = legend_block(dr, X, y, [((200, 40, 40), "Bomba zonasi (chegara)"), ((40, 150, 70), "Sotib olish zonasi (chegara)"),
                            ((120, 84, 52), "Baland pana (ko'rishni to'sadi)"), ((160, 116, 70), "Past pana (egilib)"),
                            ((176, 150, 110), "Platforma 1.3 m (zinapoyali)"), ((214, 214, 210), "Smoke nishoni"),
                            (TCOL, "T yo'llari / spawn"), (CTCOL, "CT yo'llari / spawn")])
dr.text((X, y + 4), "Uchburchak — bot nuqtalari (ushlash, kirish, qaytarib olish ...)", fill=(60, 50, 40), font=F(12))
img.save(os.path.join(DOCS, "blueprint_stage1.png"))

# to'qnashuv xaritasi: har nuqtada eng erta mumkin bo'lgan otishma vaqti
img2 = Image.new("RGB", (W + PANEL, W), (234, 224, 200))
d2 = ImageDraw.Draw(img2)
base_map(img2, d2, props=False)
stops = [(0, (170, 20, 20)), (10, (230, 110, 30)), (15, (240, 200, 60)), (22, (140, 190, 120)), (30, (90, 150, 200))]


def ramp(v):
    if not np.isfinite(v):
        return None
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if v <= b:
            t = max(0.0, (v - a) / (b - a))
            return tuple(int(ca[k] + (cb[k] - ca[k]) * t) for k in range(3))
    return stops[-1][1]


for (x, z), v in zip(Q, contact):
    col = ramp(v)
    if col:
        X, Y = P2(x - 1, z - 1)
        d2.rectangle([X, Y, X + S - 1, Y + S - 1], fill=col)
for kind, x0, z0, x1, z1, h in prop_boxes:
    if h >= EYE_BLOCK or kind == "wall":
        d2.rectangle([*P2(x0, z0), *P2(x1, z1)], fill=(70, 50, 36))
d2.line([P2(*fa), P2(*fb)], fill=(20, 20, 20), width=3)
shown = set()
for n, c0, r0, c1, r1, _ in L.ZONES:
    nm = name_of[n]
    if nm not in shown:
        shown.add(nm); label(d2, *L.m((c0 + c1) / 2, (r0 + r1) / 2), nm, 10)
X, y = W + 10, PAD
d2.text((X, y), "Birinchi to'qnashuv xaritasi", fill=(40, 30, 20), font=FB(22)); y += 34
for t in ("Har bir joy — raund boshidan necha soniyadan keyin",
          "u yerda dushman bilan ko'z-ko'z bo'lish mumkin.",
          "Qizil — erta to'qnashuv (mid doors, top mid).",
          "Ko'k — tinch hudud (spawn'lar, orqa yo'llar).",
          f"Qora chiziq — eng birinchi to'qnashuv: {fc:.1f} s."):
    d2.text((X, y), t, fill=(60, 50, 40), font=F(14)); y += 21
y += 10
for v, t in ((5, "≤ 5 s"), (10, "10 s"), (15, "15 s"), (22, "22 s"), (30, "≥ 30 s")):
    d2.rectangle([X, y + 2, X + 30, y + 18], fill=ramp(v)); d2.text((X + 40, y + 2), t, fill=(60, 50, 40), font=F(13)); y += 24
img2.save(os.path.join(DOCS, "contact_stage1.png"))

sys.exit(1 if fails else 0)
