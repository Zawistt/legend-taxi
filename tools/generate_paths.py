#!/usr/bin/env python3
"""Legend RTS - movement structure generator (roads, lanes, ramps, natural blockers).

Run AFTER tools/generate_terrain.py. It never edits the terrain heights.
Outputs (godot/terrain_data/):
  roadmap.png    RGBA8 1024^2: R road alpha, G road class (wear), B lane id, A open-area mask
  blockmap.png   RGBA8 1024^2: R forest, G rock, B (reserved), A choke highlight
  paths.json     nodes, edges (polylines), lanes, summits, chokes, open areas, stats
  blockers.json  convex polygons carved out of the navmesh (forest / rock zones)
Deterministic (fixed seed). All distances in metres, world X/Z in [-214, 214].
"""
import json
import os
import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d, sobel, distance_transform_edt, label
from skimage.graph import route_through_array
from PIL import Image
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "godot", "terrain_data")
SEED = 7771
rng = np.random.default_rng(SEED)

meta = json.load(open(os.path.join(DATA, "terrain_meta.json")))
G, C, SZ = meta["grid"], meta["cell_m"], meta["size_m"]
H = np.fromfile(os.path.join(DATA, "heightmap.bin"), "<f4").reshape(G, G)
ax = np.linspace(-SZ / 2, SZ / 2, G)
X, Z = np.meshgrid(ax, ax)
SLOPE = np.degrees(np.arctan(np.hypot(sobel(H, axis=1), sobel(H, axis=0)) / (8 * C)))
PLAY = 180.0                     # playable half size
NAV_MAX_SLOPE = 18.0             # must match terrain_manager.nav_agent_max_slope
RES = 1024                       # raster resolution of road/block maps
PX = SZ / RES
rax = (np.arange(RES) + 0.5) * PX - SZ / 2
RX, RZ = np.meshgrid(rax, rax)


def hgt(x, z):
    i = np.clip((x + SZ / 2) / C, 0, G - 1.001); j = np.clip((z + SZ / 2) / C, 0, G - 1.001)
    i0, j0 = int(i), int(j); tx, tz = i - i0, j - j0
    return float((H[j0, i0] * (1 - tx) + H[j0, i0 + 1] * tx) * (1 - tz) + (H[j0 + 1, i0] * (1 - tx) + H[j0 + 1, i0 + 1] * tx) * tz)


def to_idx(x, z):
    return (int(round(np.clip((z + SZ / 2) / C, 0, G - 1))), int(round(np.clip((x + SZ / 2) / C, 0, G - 1))))


# ---------------------------------------------------------------- layout ----
BA = tuple(meta["base_a"]); BB = tuple(meta["base_b"])
sites = meta["resource_sites"]
exp_pads = [s["pos"] for s in sites if s["kind"] == "exp"]
SUMMITS = {"H_W": (-74, 54), "H_E": (74, -53), "H_NW": (-39, -62), "H_SE": (28, 69)}

# Lane naming is from Player 1's (NW base) point of view facing the enemy:
# LEFT = north-east route (sheltered valley), RIGHT = south-west route (rough uplands).
N = {
    # bases (centres) - Main Base footprint stays free, roads start at the plateau edge
    "BASE_A": BA, "BASE_B": BB,
    "A_C": (-118, -118), "A_L": (-110, -137), "A_R": (-137, -110),
    "B_C": (118, 118), "B_L": (137, 110), "B_R": (110, 137),
    # centre lane
    "C1": (-88, -88), "C2": (-46, -44), "CC": (0, 0), "C3": (46, 44), "C4": (88, 88),
    # left lane (north-east)
    "L1": (-68, -108), "L2": (14, -92), "L3": (96, -100), "L4": (126, -50), "L5": (132, 2),
    "L6": (137.3, 53.6),
    # right lane (south-west)
    "R1": (-108, -68), "R2": (-92, 14), "R3": (-100, 96), "R4": (-50, 126), "R5": (2, 132),
    "R6": (53.6, 137.3),
    # forward resource pads (positions come from terrain_meta resource_sites)
    "P_A1": (-53.6, -137.3), "P_A2": (-137.3, -53.6),
    # arena entrances (central battlefield, r~48 m open)
    "AN": (30, -34), "AE": (40, 8), "AS": (-30, 34), "AW": (-40, -8),
    # resource sites reachable from the bases
    "S_A1": tuple(sites[0]["pos"]), "S_A2": tuple(sites[2]["pos"]), "S_A3": tuple(sites[4]["pos"]),
    "S_B1": tuple(sites[1]["pos"]), "S_B2": tuple(sites[3]["pos"]), "S_B3": tuple(sites[5]["pos"]),
    # elevated positions (summit plateaus)
    **{k: v for k, v in SUMMITS.items()},
}
L1 = [s for s in exp_pads if abs(s[0] + 54) < 3 and s[1] < -100]
SNAP = {"L2", "L3", "L4", "L5", "R2", "R3", "R4", "R5", "AN", "AE", "AS", "AW", "C1", "C2", "C3", "C4"}

# class table: (name, width m, slope cap deg for routing, wear value, smoothing sigma m)
CLS = {
    "trunk": (22.0, 14.0, 1.00, 9.0),    # centre lane + base trunks  - widest
    "left": (15.0, 15.0, 0.80, 8.0),    # sheltered flank lane
    "right": (12.0, 16.0, 0.65, 5.0),   # narrow winding rough lane
    "link": (9.0, 16.0, 0.55, 6.0),     # lane <-> arena connectors (alternative attack routes)
    "ramp": (9.0, 16.0, 0.50, 5.0),     # high-ground access
    "work": (5.0, 16.0, 0.35, 4.0),     # worker / resource paths, base exits
    "open": (0.0, 16.0, 0.0, 1.0),      # virtual: open floor (arena / base apron), graph only
}
LANE_ID = {"center": 1, "left": 2, "right": 3, "link": 4, "ramp": 5, "work": 6, "arena": 0, "apron": 0}

# (a, b, class, lane, via points)
E = [
    # --- centre lane (main route)
    ("A_C", "C1", "trunk", "center", []), ("C1", "C2", "trunk", "center", []),
    ("C2", "CC", "trunk", "center", []), ("CC", "C3", "trunk", "center", []),
    ("C3", "C4", "trunk", "center", []), ("C4", "B_C", "trunk", "center", []),
    # --- left lane (north-east, sheltered flank route)
    ("A_L", "L1", "left", "left", []), ("L1", "L2", "left", "left", []),
    ("L2", "L3", "left", "left", []), ("L3", "L4", "left", "left", []),
    ("L4", "L5", "left", "left", []), ("L5", "L6", "left", "left", []), ("L6", "B_L", "left", "left", []),
    # --- right lane (south-west, rough winding route)
    ("A_R", "R1", "right", "right", []), ("R1", "R2", "right", "right", []),
    ("R2", "R3", "right", "right", []), ("R3", "R4", "right", "right", []),
    ("R4", "R5", "right", "right", []), ("R5", "R6", "right", "right", []), ("R6", "B_R", "right", "right", []),
    # --- connectors: alternative attack routes into the central battlefield (arena interior stays open)
    ("L2", "AN", "link", "link", []), ("L5", "AE", "link", "link", []),
    ("R2", "AW", "link", "link", []), ("R4", "AS", "link", "link", []),
    ("C2", "AW", "link", "link", []), ("C3", "AE", "link", "link", []),
    # virtual edges (no road drawn): open arena floor, units cross it freely
    ("AN", "CC", "open", "arena", []), ("AE", "CC", "open", "arena", []),
    ("AS", "CC", "open", "arena", []), ("AW", "CC", "open", "arena", []),
    # --- high-ground ramps (every summit reachable from two different roads)
    ("AW", "H_W", "ramp", "ramp", []), ("R3", "H_W", "ramp", "ramp", []),
    ("AE", "H_E", "ramp", "ramp", []), ("L4", "H_E", "ramp", "ramp", []),
    ("C2", "H_NW", "ramp", "ramp", []), ("L2", "H_NW", "ramp", "ramp", []),
    ("C3", "H_SE", "ramp", "ramp", []), ("R5", "H_SE", "ramp", "ramp", []),
    # --- base exits / worker and resource paths
    ("BASE_A", "A_C", "open", "apron", []), ("BASE_A", "A_L", "open", "apron", []), ("BASE_A", "A_R", "open", "apron", []),
    ("BASE_B", "B_C", "open", "apron", []), ("BASE_B", "B_L", "open", "apron", []), ("BASE_B", "B_R", "open", "apron", []),
    ("S_A1", "A_L", "work", "work", []), ("S_A2", "A_R", "work", "work", []), ("S_A3", "A_C", "work", "work", []),
    ("P_A1", "L1", "work", "work", []), ("P_A2", "R1", "work", "work", []),
    ("S_B1", "B_L", "work", "work", []), ("S_B2", "B_R", "work", "work", []), ("S_B3", "B_C", "work", "work", []),
]
# BASE_x -> exit edges are short worker aprons: route them straight (inside the flat plateau)
STRAIGHT = {("BASE_A", "A_C"), ("BASE_A", "A_L"), ("BASE_A", "A_R"),
            ("BASE_B", "B_C"), ("BASE_B", "B_L"), ("BASE_B", "B_R")}

LANE_ORDER = {
    "center": ["A_C-C1", "C1-C2", "C2-CC", "CC-C3", "C3-C4", "C4-B_C"],
    "left": ["A_L-L1", "L1-L2", "L2-L3", "L3-L4", "L4-L5", "L5-L6", "L6-B_L"],
    "right": ["A_R-R1", "R1-R2", "R2-R3", "R3-R4", "R4-R5", "R5-R6", "R6-B_R"],
}

# ---------------------------------------------------------------- nodes -----
def snap_node(p, r=7.0):
    d = np.hypot(X - p[0], Z - p[1])
    cost = np.where((d < r) & (np.abs(X) < PLAY - 6) & (np.abs(Z) < PLAY - 6), SLOPE + 0.15 * d, 1e9)
    j, i = np.unravel_index(np.argmin(cost), cost.shape)
    return (float(X[j, i]), float(Z[j, i]))


NODES = {}
for k, p in N.items():
    if k in SNAP:
        p = snap_node(p)
    NODES[k] = (float(p[0]), float(p[1]))

# ---------------------------------------------------------------- routing ---
def make_cost(cap):
    s = SLOPE
    cost = 1.0 + 2.2 * (np.clip(s, 0, None) / 10.0) ** 2           # gentle preference for flatter ground
    cost = np.where(s > cap, 1.0e3 + 80.0 * (s - cap), cost)
    cost = np.where((np.abs(X) > PLAY - 3) | (np.abs(Z) > PLAY - 3), 1.0e4, cost)
    return cost


COSTS = {}
def route(p, q, cap):
    if cap not in COSTS:
        COSTS[cap] = make_cost(cap)
    path, _ = route_through_array(COSTS[cap], to_idx(*p), to_idx(*q), fully_connected=True, geometric=True)
    return [(float(X[j, i]), float(Z[j, i])) for j, i in path]


def resample(pts, step=1.0):
    pts = np.array(pts, float)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    if d[-1] < 1e-6:
        return pts
    s = np.arange(0, d[-1], step)
    s = np.r_[s, d[-1]]
    return np.c_[np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])]


def smooth(pts, sigma_m):
    r = resample(pts, 1.0)
    pad = int(sigma_m * 3)
    if len(r) < 4:
        return r
    out = np.c_[gaussian_filter1d(r[:, 0], sigma_m, mode="nearest"), gaussian_filter1d(r[:, 1], sigma_m, mode="nearest")]
    # pin both ends so junctions stay exact (blend the first/last ~2 sigma)
    n = len(out)
    w = np.clip(np.arange(n) / (2 * sigma_m + 1), 0, 1) ** 2 * np.clip((n - 1 - np.arange(n)) / (2 * sigma_m + 1), 0, 1) ** 2
    w = w[:, None]
    out = r * (1 - w) + out * w
    out[0], out[-1] = r[0], r[-1]
    return resample(out, 1.0)


EDGES = []
for a, b, cls, lane, via in E:
    width, cap, wear, sig = CLS[cls]
    eid = f"{a}-{b}"
    pa, pb = NODES[a], NODES[b]
    if (a, b) in STRAIGHT:
        raw = [pa, pb]
    else:
        chain = [pa] + [tuple(v) for v in via] + [pb]
        raw = []
        for u, v in zip(chain[:-1], chain[1:]):
            seg = route(u, v, cap)
            raw += seg if not raw else seg[1:]
    pts = smooth(raw, sig) if (a, b) not in STRAIGHT else resample(raw, 1.0)
    EDGES.append(dict(id=eid, a=a, b=b, cls=cls, lane=lane, width=width, wear=wear, pts=pts))
EID = {e["id"]: e for e in EDGES}

# ---------------------------------------------------------------- rasters ---
def edt_to_polyline(pts):
    m = np.ones((RES, RES), bool)
    p = resample(pts, PX * 0.6)
    ii = np.clip(((p[:, 0] + SZ / 2) / PX).astype(int), 0, RES - 1)
    jj = np.clip(((p[:, 1] + SZ / 2) / PX).astype(int), 0, RES - 1)
    m[jj, ii] = False
    return distance_transform_edt(m) * PX


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


road_alpha = np.zeros((RES, RES), np.float32)
road_wear = np.zeros((RES, RES), np.float32)
road_lane = np.zeros((RES, RES), np.uint8)
free_dist = np.full((RES, RES), 1e3, np.float32)       # distance to nearest road EDGE (minus half width)
for e in sorted([e for e in EDGES if e["cls"] != "open"], key=lambda e: e["width"]):
    d = edt_to_polyline(e["pts"])
    hw = e["width"] / 2
    a = 1 - smoothstep(hw - 0.9, hw + 0.5, d)
    upd = a > road_alpha * 0.999
    road_wear = np.where(a > 0.5, e["wear"], road_wear)
    road_lane = np.where(a > 0.5, LANE_ID[e["lane"]], road_lane)
    road_alpha = np.maximum(road_alpha, a)
    free_dist = np.minimum(free_dist, d - hw)
# junction discs: turning space where roads meet
deg = {}
for e in [e for e in EDGES if e["cls"] != "open"]:
    deg.setdefault(e["a"], []).append(e); deg.setdefault(e["b"], []).append(e)
for k, es in deg.items():
    if k.startswith("BASE"):
        continue
    r = max(e["width"] for e in es) * 0.62 + (2.0 if len(es) > 2 else 0.0)
    d = np.hypot(RX - NODES[k][0], RZ - NODES[k][1])
    a = 1 - smoothstep(r - 1.0, r + 0.3, d)
    road_alpha = np.maximum(road_alpha, a.astype(np.float32))
    wear = max(e["wear"] for e in es)
    road_wear = np.where(a > 0.5, np.maximum(road_wear, wear), road_wear)
    free_dist = np.minimum(free_dist, d - r)

# ------------------------------------------------------------- open areas ---
OPEN = [  # name, centre, radius: guaranteed free of blockers
    ("base_a_apron", BA, 40.0), ("base_b_apron", BB, 40.0), ("central_arena", (0, 0), 50.0),
] + [(k, NODES[k], 13.0) for k in NODES if not k.startswith("BASE") and not k.startswith("H_")] \
  + [(k, NODES[k], 16.0) for k in SUMMITS]
keep = np.zeros((RES, RES), bool)
for _, (cx, cz), r in OPEN:
    keep |= np.hypot(RX - cx, RZ - cz) < r
for k, (x, z) in [(k, v) for k, v in NODES.items() if k.startswith("S_")]:
    keep |= np.hypot(RX - x, RZ - z) < 14.0
oob = (np.abs(RX) > PLAY - 4) | (np.abs(RZ) > PLAY - 4)
keep |= oob            # no blockers on the very edge - the rim already bounds the map


# ------------------------------------------------------------- blockers -----
def ellipse_mask(cx, cz, rx, rz, rot):
    c, s = np.cos(rot), np.sin(rot)
    u = ((RX - cx) * c + (RZ - cz) * s) / rx
    v = (-(RX - cx) * s + (RZ - cz) * c) / rz
    return u * u + v * v <= 1.0


BLOCKERS = []
block_forest = np.zeros((RES, RES), bool)
block_rock = np.zeros((RES, RES), bool)


def try_add(cx, cz, rx, rz, rot, kind, clearance, shrink=(1.0, 0.8, 0.62)):
    for k in shrink:
        a, b = rx * k, rz * k
        if a < 3.0 or b < 2.5:
            return False
        m = ellipse_mask(cx, cz, a + clearance, b + clearance, rot)   # test with clearance ring
        if (m & keep).any() or (free_dist[m] < clearance).any():
            continue
        # keep blockers from overlapping each other too heavily
        em = ellipse_mask(cx, cz, a, b, rot)
        BLOCKERS.append(dict(kind=kind, cx=float(cx), cz=float(cz), rx=float(a), rz=float(b), rot=float(rot)))
        (block_forest if kind == "forest" else block_rock).__ior__(em)
        return True
    return False


def lane_poly(lane):
    pts = []
    for eid in LANE_ORDER[lane]:
        e = EID[eid]
        pts += list(map(tuple, e["pts"] if not pts else e["pts"][1:]))
    return resample(np.array(pts), 1.0)


def tangent_normal(poly, i):
    j0, j1 = max(i - 3, 0), min(i + 3, len(poly) - 1)
    t = poly[j1] - poly[j0]
    t = t / (np.hypot(*t) + 1e-9)
    return t, np.array([-t[1], t[0]])


CHOKES = []
LANE_CFG = {
    #            kind     hw   open margin (min,max)  choke margin  rx range  rz range  chokes (fractions)  gap chance
    "left":   ("forest", 8.0, (3.0, 5.0), 0.8, (7, 11), (5, 8), (0.34, 0.66), 0.10),
    "right":  ("rock", 6.0, (1.5, 8.0), 0.7, (4, 8), (3.5, 6.5), (0.20, 0.47, 0.76), 0.22),
    "center": ("rock", 12.0, (13.0, 18.0), 5.0, (6, 10), (4, 7), (0.17, 0.83), 0.35),
}
for lane, (kind, hw, (m0, m1), mchoke, rxr, rzr, chokes, gap) in LANE_CFG.items():
    poly = lane_poly(lane)
    L = len(poly)
    cpos = [int(f * L) for f in chokes]
    for cp in cpos:
        CHOKES.append(dict(lane=lane, pos=[float(poly[cp][0]), float(poly[cp][1])]))
    s = 34
    while s < L - 34:
        rx, rz = rng.uniform(*rxr), rng.uniform(*rzr)
        t, nrm = tangent_normal(poly, s)
        rot = float(np.arctan2(t[1], t[0]))
        near_choke = min(abs(s - cp) for cp in cpos)
        pinch = np.exp(-(near_choke / 11.0) ** 2)
        for side in (1, -1):
            if near_choke > 16 and rng.random() < gap:
                continue
            mg = (1 - pinch) * rng.uniform(m0, m1) + pinch * mchoke
            if lane == "center" and near_choke > 28 and np.hypot(*poly[s]) < 70:
                continue                      # keep the arena approach open
            off = hw + mg + rz
            c = poly[s] + side * nrm * off
            if abs(c[0]) > PLAY - 12 or abs(c[1]) > PLAY - 12:
                continue
            try_add(c[0], c[1], rx, rz, rot + rng.normal(0, 0.12), kind, clearance=1.2)
        s += int(rx * 1.55)

# rock rings on the flanks of every summit; gaps where the ramps arrive
for name, (sx, sz) in SUMMITS.items():
    ramp_dirs = []
    for e in EDGES:
        if e["lane"] == "ramp" and name in (e["a"], e["b"]):
            other = e["a"] if e["b"] == name else e["b"]
            ramp_dirs.append(np.arctan2(NODES[other][1] - sz, NODES[other][0] - sx))
    for ang in np.arange(0, 2 * np.pi, np.pi / 7):
        ang += rng.uniform(-0.12, 0.12)
        if any(abs((ang - d + np.pi) % (2 * np.pi) - np.pi) < 0.62 for d in ramp_dirs):
            continue
        if rng.random() < 0.28:
            continue                          # random natural gap
        r0 = rng.uniform(30, 36)
        try_add(sx + r0 * np.cos(ang), sz + r0 * np.sin(ang), rng.uniform(6, 10), rng.uniform(3.5, 5.5),
                ang + np.pi / 2, "rock", clearance=1.2)

# a few isolated groves / outcrops between the lanes (not walls, just terrain character)
for _ in range(260):
    cx, cz = rng.uniform(-PLAY + 14, PLAY - 14, 2)
    kind = "forest" if rng.random() < 0.55 else "rock"
    try_add(cx, cz, rng.uniform(6, 11), rng.uniform(4, 7), rng.uniform(0, np.pi), kind, clearance=5.0)
    if sum(b["kind"] != "x" for b in BLOCKERS) > 230:
        break

blocked = block_forest | block_rock

# ---------------------------------------------------------------- export ----
def soft(mask, sigma=1.1):
    return np.clip(gaussian_filter(mask.astype(np.float32), sigma) * 1.6 - 0.3, 0, 1)


choke_hi = np.zeros((RES, RES), np.float32)
for c in CHOKES:
    d = np.hypot(RX - c["pos"][0], RZ - c["pos"][1])
    choke_hi = np.maximum(choke_hi, np.exp(-(d / 14.0) ** 2))

road_img = np.zeros((RES, RES, 4), np.uint8)
road_img[..., 0] = (road_alpha * 255).astype(np.uint8)
road_img[..., 1] = (road_wear * 255).astype(np.uint8)
road_img[..., 2] = road_lane * 32
road_img[..., 3] = 255
Image.fromarray(road_img, "RGBA").save(os.path.join(DATA, "roadmap.png"))
blk = np.zeros((RES, RES, 4), np.uint8)
blk[..., 0] = (soft(block_forest) * 255).astype(np.uint8)
blk[..., 1] = (soft(block_rock) * 255).astype(np.uint8)
blk[..., 3] = (choke_hi * 255).astype(np.uint8)
Image.fromarray(blk, "RGBA").save(os.path.join(DATA, "blockmap.png"))


def poly_pts(b, n=20):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    c, s = np.cos(b["rot"]), np.sin(b["rot"])
    u, v = b["rx"] * np.cos(t), b["rz"] * np.sin(t)
    return [[round(float(b["cx"] + u[i] * c - v[i] * s), 2), round(float(b["cz"] + u[i] * s + v[i] * c), 2)] for i in range(n)]


json.dump({"blockers": [dict(kind=b["kind"], polygon=poly_pts(b)) for b in BLOCKERS]},
          open(os.path.join(DATA, "blockers.json"), "w"))

# ---------------------------------------------------------------- validate --
def rix(x, z):
    return (np.clip(((z + SZ / 2) / PX).astype(int), 0, RES - 1), np.clip(((x + SZ / 2) / PX).astype(int), 0, RES - 1))


slope_r = np.array(Image.fromarray(SLOPE.astype(np.float32)).resize((RES, RES), Image.BILINEAR))
walk = (slope_r < NAV_MAX_SLOPE) & (np.abs(RX) <= PLAY) & (np.abs(RZ) <= PLAY) & ~blocked
clear = distance_transform_edt(walk) * PX          # radius of free space around every walkable point

stats = {"edges": {}, "lanes": {}}
problems = []
for e in EDGES:
    p = e["pts"]
    j, i = rix(p[:, 0], p[:, 1])
    hs = np.array([hgt(x, z) for x, z in p])
    seg = np.hypot(*np.diff(p, axis=0).T)
    sl = np.degrees(np.arctan2(np.abs(np.diff(hs)), seg))
    sl_s = gaussian_filter1d(sl, 3.0) if len(sl) > 6 else sl
    cl = clear[j, i] * 2                              # free width at each road point
    stats["edges"][e["id"]] = dict(length=round(float(seg.sum()), 1), max_slope_deg=round(float(sl_s.max()), 1),
                                    min_free_width=round(float(cl.min()), 1), width=e["width"])
    if e["cls"] == "open":
        e["length"] = float(seg.sum()); continue
    if not walk[j, i].all():
        problems.append(f"{e['id']}: {int((~walk[j, i]).sum())} centreline points not walkable")
    if cl.min() < e["width"] * 0.98 and e["a"][:4] != "BASE":
        problems.append(f"{e['id']}: free width {cl.min():.1f} < road width {e['width']}")
    e["length"] = float(seg.sum())

graph = nx.Graph()
for e in EDGES:
    graph.add_edge(e["a"], e["b"], length=e["length"], eid=e["id"], lane=e["lane"])
assert nx.is_connected(graph), "road graph is not connected"
bridges = [tuple(b) for b in nx.bridges(graph)]
important = [k for k in NODES if not k.startswith(("S_", "P_"))]   # dead-end resource spurs sit on open ground
# a bridge only matters if it separates 'important' nodes (dead-end worker aprons / resource sites are fine)
crit = []
for a, b in bridges:
    g2 = graph.copy(); g2.remove_edge(a, b)
    comps = list(nx.connected_components(g2))
    sides = [c for c in comps if any(n in important and not n.startswith("BASE") for n in c)]
    if len([c for c in comps if len([n for n in c if n in important and not n.startswith('BASE')]) > 0]) > 1:
        crit.append((a, b))
for lane in ("center", "left", "right"):
    stats["lanes"][lane] = None
# lane lengths (base exit to base exit)
def path_len(p):
    return float(sum(graph[u][v]["length"] for u, v in zip(p[:-1], p[1:])))
route_len = {}
def lane_route(lane, a, b):
    ids = LANE_ORDER[lane]
    return sum(EID[i]["length"] for i in ids)
for lane in ("center", "left", "right"):
    ids = LANE_ORDER[lane]
    route_len[lane] = round(sum(EID[i]["length"] for i in ids), 1)
    cl = min(stats["edges"][i]["min_free_width"] for i in ids)
    mx = max(stats["edges"][i]["max_slope_deg"] for i in ids)
    stats["lanes"][lane] = dict(length_m=route_len[lane], min_free_width_m=cl, max_slope_deg=mx)

# every important node must have 2 edge-disjoint routes to each base
disjoint = {}
for k in important:
    if k.startswith("BASE"):
        continue
    disjoint[k] = min(nx.edge_connectivity(graph, k, "BASE_A") if k != "BASE_A" else 9,
                      nx.edge_connectivity(graph, k, "BASE_B"))
weak = [k for k, v in disjoint.items() if v < 2 and not k.startswith(("A_", "B_"))]

# open space checks
arena = np.hypot(RX, RZ) < 50
apron_a = np.hypot(RX - BA[0], RZ - BA[1]) < 40
apron_b = np.hypot(RX - BB[0], RZ - BB[1]) < 40
play_area = (np.abs(RX) <= PLAY) & (np.abs(RZ) <= PLAY)
stats.update(
    nodes=len(NODES), edges_count=len(EDGES), blockers=len(BLOCKERS),
    forest_blockers=sum(b["kind"] == "forest" for b in BLOCKERS), rock_blockers=sum(b["kind"] == "rock" for b in BLOCKERS),
    blocked_pct_playable=round(float(blocked[play_area].mean() * 100), 1),
    road_pct_playable=round(float((road_alpha[play_area] > 0.5).mean() * 100), 1),
    walkable_pct_playable=round(float(walk[play_area].mean() * 100), 1),
    arena_walkable_pct=round(float(walk[arena].mean() * 100), 1),
    apron_a_walkable_pct=round(float(walk[apron_a].mean() * 100), 1),
    apron_b_walkable_pct=round(float(walk[apron_b].mean() * 100), 1),
    critical_bridges=[list(b) for b in crit], weak_nodes=weak,
    problems=problems,
)
# largest walkable component must contain everything important
lab, n = label(walk)
main = np.bincount(lab[lab > 0]).argmax()
stats["all_nodes_in_main_walkable_region"] = all(
    lab[tuple(a[0] for a in rix(np.array([x]), np.array([z])))] == main for x, z in NODES.values())
stats["walkable_main_region_pct_of_walkable"] = round(float((lab == main).sum() / max(walk.sum(), 1) * 100), 1)

paths = {
    "version": 1,
    "nav_max_slope_deg": NAV_MAX_SLOPE,
    "lane_ids": LANE_ID,
    "classes": {k: dict(width=v[0], slope_cap_deg=v[1]) for k, v in CLS.items()},
    "nodes": {k: [round(p[0], 2), round(hgt(*p), 2), round(p[1], 2)] for k, p in NODES.items()},
    "edges": [dict(id=e["id"], a=e["a"], b=e["b"], cls=e["cls"], lane=e["lane"], width=e["width"], length=round(e["length"], 1),
                   points=[[round(float(x), 2), round(hgt(x, z), 2), round(float(z), 2)] for x, z in e["pts"][::3]] +
                          [[round(float(e["pts"][-1][0]), 2), round(hgt(*e["pts"][-1]), 2), round(float(e["pts"][-1][1]), 2)]])
              for e in EDGES],
    "lanes": {k: v for k, v in LANE_ORDER.items()},
    "lane_roles": {
        "center": "widest, most direct, open arena fight (main battle route)",
        "left": "sheltered forest valley, flanking route (player-1 left = north-east)",
        "right": "narrow winding rocky uplands, ambush / surprise route (player-1 right = south-west)",
    },
    "summits": {k: [v[0], round(hgt(*v), 2), v[1]] for k, v in SUMMITS.items()},
    "chokes": [],
    "open_areas": [dict(name=n, pos=[p[0], p[1]], radius=r) for n, p, r in OPEN if n in ("base_a_apron", "base_b_apron", "central_arena")],
    "stats": stats,
}
for c in CHOKES:
    j, i = rix(np.array([c["pos"][0]]), np.array([c["pos"][1]]))
    # width = free corridor measured at the choke along the road normal (approx: nearest road free width)
    lane_pts = lane_poly(c["lane"])
    k = int(np.argmin(np.hypot(lane_pts[:, 0] - c["pos"][0], lane_pts[:, 1] - c["pos"][1])))
    jj, ii = rix(lane_pts[max(k - 6, 0):k + 7, 0], lane_pts[max(k - 6, 0):k + 7, 1])
    paths["chokes"].append(dict(lane=c["lane"], pos=[round(c["pos"][0], 1), round(c["pos"][1], 1)],
                                free_width=round(float(clear[jj, ii].min() * 2), 1)))
json.dump(paths, open(os.path.join(DATA, "paths.json"), "w"), indent=1)

print(json.dumps({k: v for k, v in stats.items() if k != "edges"}, indent=1))
print("route lengths A->B:", route_len)
print("chokes:", paths["chokes"])
print("worst edges (free width/width):", sorted(((v["min_free_width"] / v["width"], k) for k, v in stats["edges"].items() if v["width"] > 0))[:5])
print("max slope per edge:", sorted(((v["max_slope_deg"], k) for k, v in stats["edges"].items()), reverse=True)[:6])
