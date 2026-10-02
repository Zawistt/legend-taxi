#!/usr/bin/env python3
"""Legend RTS - resource system layout generator.

Run AFTER generate_terrain.py and generate_paths.py. Does NOT touch terrain, roads or blockers.
Outputs:
  godot/terrain_data/resources.json        every resource location (data for later scripts / AI)
  godot/terrain_data/resourcemap.png       ground paint under resource sites (R clearing, G type, B slot ring)
  godot/scenes/resources/resource_layout.tscn   all ResourceNode instances placed on the map
  docs/preview/07_resource_map.png         schematic overview (when --preview)

Fairness: every player-side location is placed as an exact POINT MIRROR (x,z) -> (-x,-z) of the
other player's location (same type, size, amount, tree layout), and positions must be valid for
BOTH sides, so base-to-resource distances are equal by construction.
"""
import json
import os
import sys
import numpy as np
from scipy.ndimage import sobel, distance_transform_edt, gaussian_filter
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, Point, MultiPoint
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "godot", "terrain_data")
SCENES = os.path.join(ROOT, "godot", "scenes", "resources")
os.makedirs(SCENES, exist_ok=True)
rng = np.random.default_rng(31337)

meta = json.load(open(f"{DATA}/terrain_meta.json"))
PATHS = json.load(open(f"{DATA}/paths.json"))
G, C, SZ = meta["grid"], meta["cell_m"], meta["size_m"]
H = np.fromfile(f"{DATA}/heightmap.bin", "<f4").reshape(G, G)
SL = np.degrees(np.arctan(np.hypot(sobel(H, axis=1), sobel(H, axis=0)) / (8 * C)))
RES = 1024
PX = SZ / RES
rax = (np.arange(RES) + 0.5) * PX - SZ / 2
RX, RZ = np.meshgrid(rax, rax)
road_img = np.array(Image.open(f"{DATA}/roadmap.png").convert("RGBA"))
blk_img = np.array(Image.open(f"{DATA}/blockmap.png").convert("RGBA"))
ROAD = road_img[..., 0] > 30
BLOCK = (blk_img[..., 0] > 127) | (blk_img[..., 1] > 127)
BLOCK_PAD = distance_transform_edt(~BLOCK) * PX < 1.3          # blocked + 1.3 m (worker radius + margin)
SLOPE_R = np.array(Image.fromarray(SL.astype(np.float32)).resize((RES, RES), Image.BILINEAR))
BA, BB = np.array(meta["base_a"]), np.array(meta["base_b"])
PLAY = 180.0
EDGE_MARGIN = 5.0                  # slots/footprints stay this far inside the playable square


def hgt(x, z):
    fi = np.clip((x + SZ / 2) / C, 0, G - 1.001); fj = np.clip((z + SZ / 2) / C, 0, G - 1.001)
    i, j = int(fi), int(fj); tx, tz = fi - i, fj - j
    return float((H[j, i] * (1 - tx) + H[j, i + 1] * tx) * (1 - tz) + (H[j + 1, i] * (1 - tx) + H[j + 1, i + 1] * tx) * tz)


def slope_at(x, z):
    return float(SLOPE_R[int(np.clip((z + SZ / 2) / PX, 0, RES - 1)), int(np.clip((x + SZ / 2) / PX, 0, RES - 1))])


def mask_at(m, x, z):
    return bool(m[int(np.clip((z + SZ / 2) / PX, 0, RES - 1)), int(np.clip((x + SZ / 2) / PX, 0, RES - 1))])


# ------------------------------------------------------------------ type specs
# footprint r (solid deposit / grove), clear r (free working area), slot ring r, slots, 3D asset names
TYPES = {
    "gold":    dict(scene="gold_deposit", fp=4.4, clear=14.0, slot_r=7.4, slots=8, gather_range=2.4, carry=10,
                    max_workers=8, mesh_variants=2),
    "stone":   dict(scene="stone_quarry", fp=5.6, clear=15.5, slot_r=8.6, slots=8, gather_range=2.4, carry=10,
                    max_workers=8, mesh_variants=2),
    "crystal": dict(scene="crystal_cluster", fp=3.6, clear=13.0, slot_r=6.2, slots=4, gather_range=2.4, carry=5,
                    max_workers=4, mesh_variants=2),
    "wood":    dict(scene="wood_zone", fp=9.0, clear=19.0, slot_r=None, slots=12, gather_range=2.2, carry=10,
                    max_workers=12, mesh_variants=1),
}
# economy per tier:   amount, gather_rate (units / worker / second), regen
ECON = {
    ("gold", "safe"):    dict(amount=7500, rate=2.0, regen="limited", regen_rate=0.0, respawn=-1, delay=0),
    ("gold", "side"):    dict(amount=5000, rate=2.0, regen="slow", regen_rate=0.5, respawn=240, delay=60),
    ("gold", "center"):  dict(amount=14000, rate=2.8, regen="slow", regen_rate=1.0, respawn=300, delay=90),
    ("wood", "safe"):    dict(amount=7200, rate=2.5, regen="regrow", regen_rate=0.0, respawn=90, delay=30),
    ("wood", "side"):    dict(amount=9000, rate=2.5, regen="regrow", regen_rate=0.0, respawn=90, delay=30),
    ("wood", "center"):  dict(amount=4000, rate=2.5, regen="regrow", regen_rate=0.0, respawn=120, delay=45),
    ("stone", "safe"):   dict(amount=6000, rate=1.6, regen="limited", regen_rate=0.0, respawn=-1, delay=0),
    ("stone", "flank"):  dict(amount=5000, rate=1.6, regen="limited", regen_rate=0.0, respawn=-1, delay=0),
    ("stone", "center"): dict(amount=3500, rate=1.8, regen="limited", regen_rate=0.0, respawn=-1, delay=0),
    ("crystal", "center"): dict(amount=2500, rate=0.8, regen="none", regen_rate=0.0, respawn=-1, delay=0),
}
TREE_AMOUNT = 200

# (id, type, tier, anchor of the PLAYER-1 / first copy, radius override, search radius)
# owner 0 -> mirrored copy is owner 1. owner -1 -> neutral pair (NE / SW copies)
LOCS = [
    ("gold_safe_a", "gold", "safe", 0, (-100, -161), None),
    ("gold_safe_b", "gold", "safe", 0, (-161, -100), None),
    ("wood_safe", "wood", "safe", 0, (-166, -166), 9.0),
    ("stone_safe", "stone", "safe", 0, (-165, -64), None),
    ("gold_side", "gold", "side", 0, (-40, -150), None),
    ("wood_side", "wood", "side", 0, (-150, -24), 10.5),
    ("stone_flank", "stone", "flank", -1, (112, -88), None),
    ("gold_center", "gold", "center", -1, (12, -24), None),
    ("crystal_center", "crystal", "center", -1, (36, -12), None),
    ("wood_center", "wood", "center", -1, (62, -30), 7.5),
    ("stone_center", "stone", "center", -1, (-16, -28), None),
]
SEARCH_R = 44.0
STEP = 2.0


def ring_slots(pos, yaw, r, n):
    return [(pos[0] + r * np.sin(yaw + 2 * np.pi * k / n), pos[1] + r * np.cos(yaw + 2 * np.pi * k / n)) for k in range(n)]


def slot_ok(p):
    x, z = p
    if abs(x) > PLAY - EDGE_MARGIN or abs(z) > PLAY - EDGE_MARGIN:
        return False
    if slope_at(x, z) > 16.0:        # (decorative blockers on a slot are removed afterwards)
        return False
    return True


def window(pos, r):
    x0 = int(np.clip((pos[0] - r + SZ / 2) / PX, 0, RES - 1)); x1 = int(np.clip((pos[0] + r + SZ / 2) / PX, 1, RES))
    z0 = int(np.clip((pos[1] - r + SZ / 2) / PX, 0, RES - 1)); z1 = int(np.clip((pos[1] + r + SZ / 2) / PX, 1, RES))
    return slice(z0, z1), slice(x0, x1)


REASONS = {}


def REJ(k):
    REASONS[k] = REASONS.get(k, 0) + 1
    return None


def wedge(pos, yaw, r, half_deg=40.0, n=9):
    pts = [pos] + [(pos[0] + r * np.sin(yaw + np.radians(a)), pos[1] + r * np.cos(yaw + np.radians(a))) for a in np.linspace(-half_deg, half_deg, n)]
    return Polygon(pts)


def eval_site(pos, spec, target_yaw, placed, R):
    """Terrain / road / separation test + list of decorative blockers that would have to be removed.
    Returns (cost, yaw, slots, hits) or None when the site is invalid."""
    x, z = pos
    fp = R
    clear = spec["clear"] if spec["type"] != "wood" else R + 7.5
    if abs(x) > PLAY - EDGE_MARGIN - fp or abs(z) > PLAY - EDGE_MARGIN - fp:
        return REJ(1)
    for b in (BA, BB):                                   # keep the Main Base + building plateau free
        if np.hypot(x - b[0], z - b[1]) < 29.0 + fp:
            return REJ(2)
    for sv in PATHS["summits"].values():                 # summit plateaus stay free for ranged units / vision
        if np.hypot(x - sv[0], z - sv[2]) < 22.0 + fp:
            return REJ(4)
    if spec["tier"] == "center" and np.hypot(x, z) > 112.0:
        return REJ(7)
    for q in placed:                                     # no overlap with other work areas
        if np.hypot(x - q["x"], z - q["z"]) < 0.78 * (clear + q["clear"]):
            return REJ(3)
    work = (spec["slot_r"] + 2.0) if spec["slot_r"] else (R + 4.4)
    sl, sx = window(pos, clear)
    wx, wz = RX[sl, sx], RZ[sl, sx]
    d = np.hypot(wx - x, wz - z)
    disc = d < work
    if (ROAD[sl, sx] & (d < fp + 2.5)).any():            # deposit never sits on a road
        return REJ(5)
    s_ = SLOPE_R[sl, sx][disc]
    if s_.mean() > 10.5 or np.percentile(s_, 95) > 17.0:
        return REJ(6)
    n = spec["slots"]
    sr = spec["slot_r"] if spec["slot_r"] else fp + 2.4
    best = None
    yaws = sorted((target_yaw + k * 2 * np.pi / 48 for k in range(48)), key=lambda a: abs((a - target_yaw + np.pi) % (2 * np.pi) - np.pi))
    for yaw in yaws:
        pts = ring_slots(pos, yaw, sr, n)
        ok = [slot_ok(p) for p in pts]
        if spec["type"] == "wood":
            if sum(ok) >= 8:
                best = (yaw, [p for p, o in zip(pts, ok) if o]); break
        elif all(ok):
            best = (yaw, pts); break
    if best is None:
        return REJ(8)
    yaw, pts = best
    # protected area = work disc + slot ring + 80 degree approach wedge facing the base
    prot = Point(pos).buffer(work).union(wedge(pos, target_yaw, clear)).union(MultiPoint(pts).buffer(1.5))
    hits = [i for i in BLK_TREE.query(prot) if BLK_POLYS[i].intersects(prot)]
    cost = float(s_.mean()) + 4.0 * len(hits)
    return cost, yaw, pts, hits


def nearest_base(p):
    return (0, BA) if np.hypot(*(np.array(p) - BA)) <= np.hypot(*(np.array(p) - BB)) else (1, BB)


def tgt_yaw(pos, owner, copy):
    if owner == 0:
        b = BA if copy == 0 else BB
    else:
        b = nearest_base(pos)[1]
    return np.arctan2(b[0] - pos[0], b[1] - pos[1])


BLOCKERS_ALL = json.load(open(f"{DATA}/blockers.json"))["blockers"]
BLK_POLYS = [Polygon(b["polygon"]) for b in BLOCKERS_ALL]
BLK_TREE = STRtree(BLK_POLYS)

placed = []
RESULT = []
OFFS1 = np.arange(-int(SEARCH_R / STEP), int(SEARCH_R / STEP) + 1) * STEP     # grids always include offset 0
for lid, typ, tier, owner, anchor, rad in LOCS:
    spec = dict(TYPES[typ]); spec["type"] = typ; spec["tier"] = tier
    R = rad if rad else spec["fp"]
    clear = spec["clear"] if typ != "wood" else R + 7.5
    best = None
    for dx in OFFS1:
        for dz in OFFS1:
            if np.hypot(dx, dz) > SEARCH_R:
                continue
            p = (anchor[0] + dx, anchor[1] + dz)
            mp = (-p[0], -p[1])                          # EXACT point mirror => identical distances
            e1 = eval_site(p, spec, tgt_yaw(p, owner, 0), placed, R)
            if e1 is None:
                continue
            probe = placed + [dict(x=p[0], z=p[1], clear=clear)]
            e2 = eval_site(mp, spec, tgt_yaw(mp, owner, 1), probe, R)
            if e2 is None:
                continue
            cost = np.hypot(dx, dz) + 1.2 * (e1[0] + e2[0])
            if best is None or cost < best[0]:
                best = (cost, p, mp, e1, e2)
    if best is None:
        print("FAILED to place", lid, "anchor", anchor, "rejections", REASONS); sys.exit(1)
    cost, p, mp, e1, e2 = best
    placed += [dict(x=p[0], z=p[1], clear=clear), dict(x=mp[0], z=mp[1], clear=clear)]
    RESULT.append(dict(lid=lid, typ=typ, tier=tier, owner=owner, spec=spec, R=R, clear=clear,
                       a=dict(pos=p, yaw=e1[1], slots=e1[2], hits=e1[3]), b=dict(pos=mp, yaw=e2[1], slots=e2[2], hits=e2[3]),
                       anchor_dev=float(np.hypot(p[0] - anchor[0], p[1] - anchor[1]))))
    print(f"placed {lid:16s} at ({p[0]:7.1f},{p[1]:7.1f}) / ({mp[0]:7.1f},{mp[1]:7.1f})  anchor dev {RESULT[-1]['anchor_dev']:5.1f} m  "
          f"blockers to clear {len(e1[3])}+{len(e2[3])}")

# ---- clear the (decorative) blockers that overlap a resource work area; roads / lanes stay untouched
remove = sorted({i for r in RESULT for k in ("a", "b") for i in r[k]["hits"]})
removed_info = [dict(kind=BLOCKERS_ALL[i]["kind"], at=[round(float(BLK_POLYS[i].centroid.x), 1), round(float(BLK_POLYS[i].centroid.y), 1)]) for i in remove]
keep_blk = [b for i, b in enumerate(BLOCKERS_ALL) if i not in set(remove)]
json.dump({"blockers": keep_blk}, open(f"{DATA}/blockers.json", "w"))
fm = Image.new("L", (RES, RES), 0); rm = Image.new("L", (RES, RES), 0)
for b in keep_blk:
    pts = [((x + SZ / 2) / PX, (z + SZ / 2) / PX) for x, z in b["polygon"]]
    ImageDraw.Draw(fm if b["kind"] == "forest" else rm).polygon(pts, fill=255)
def soft(m, sigma=1.1):
    return np.clip(gaussian_filter((np.array(m) > 127).astype(np.float32), sigma) * 1.6 - 0.3, 0, 1)
blk_new = blk_img.copy()
blk_new[..., 0] = (soft(fm) * 255).astype(np.uint8); blk_new[..., 1] = (soft(rm) * 255).astype(np.uint8)
Image.fromarray(blk_new, "RGBA").save(f"{DATA}/blockmap.png")
BLOCK_NEW = (blk_new[..., 0] > 127) | (blk_new[..., 1] > 127)
if not removed_info and os.path.exists(f"{DATA}/resources.json"):          # re-run on already pruned blockers: keep the record
    removed_info = json.load(open(f"{DATA}/resources.json")).get("removed_blockers", [])
print(f"removed {len(remove)} of {len(BLOCKERS_ALL)} decorative blockers inside resource work areas (record: {len(removed_info)})")

# ------------------------------------------------------------------ build locations
def poly(pos, r, n=20):
    return [[round(float(pos[0] + r * np.cos(t)), 2), round(float(pos[1] + r * np.sin(t)), 2)] for t in np.linspace(0, 2 * np.pi, n, endpoint=False)]


def make_trees(R, count, seed):
    """Irregular grove of `count` trees inside radius R, min spacing 2.5 m (same layout for both players)."""
    r = np.random.default_rng(seed)
    pts = []
    tries = 0
    shape = r.uniform(0.82, 1.0, 12)
    while len(pts) < count and tries < 20000:
        tries += 1
        ang = r.uniform(0, 2 * np.pi); rad = R * np.sqrt(r.uniform(0, 1))
        lim = R * np.interp(ang % (2 * np.pi), np.linspace(0, 2 * np.pi, 12), shape)
        if rad > lim:
            continue
        p = np.array([rad * np.cos(ang), rad * np.sin(ang)])
        if all(np.hypot(*(p - q)) > 2.5 for q, _, _, _ in pts):
            variety = r.choice(3, p=[0.45, 0.35, 0.20])
            pts.append((p, int(variety), float(r.uniform(0.85, 1.25)), float(r.uniform(0, 2 * np.pi))))
    return pts


LOCATIONS = []
def add_location(lid, typ, tier, owner, side, spec, R, clear, info, trees_seed):
    pos = info["pos"]; yaw = info["yaw"]
    econ = ECON[(typ, tier)]
    y = hgt(*pos)
    if typ != "wood":
        ys = [hgt(pos[0] + R * np.cos(t), pos[1] + R * np.sin(t)) for t in np.linspace(0, 2 * np.pi, 8, endpoint=False)]
        y = float(np.mean(ys))
    base_idx, base_pos = (owner if owner >= 0 else nearest_base(pos)[0]), None
    base_idx = owner if owner >= 0 else nearest_base(pos)[0]
    base_pos = BA if base_idx == 0 else BB
    slots = [[round(float(s[0]), 2), round(hgt(*s), 2), round(float(s[1]), 2)] for s in info["slots"]]
    gp = min(slots, key=lambda s: np.hypot(s[0] - base_pos[0], s[2] - base_pos[1]))
    trees = None
    amount = econ["amount"]
    if typ == "wood":
        count = int(round(R * R * 0.095 * (3.14159 / 3.14159)))        # ~ one tree per 10.5 m2
        count = {7.5: 18, 9.0: 28, 10.5: 36}[R]
        trees = make_trees(R, count, trees_seed)
        amount = len(trees) * TREE_AMOUNT
    d_dir = np.array([base_pos[0] - pos[0], base_pos[1] - pos[1]]); d_dir /= np.hypot(*d_dir)
    appr = [round(float(pos[0] + d_dir[0] * clear * 0.85), 2), round(hgt(pos[0] + d_dir[0] * clear * 0.85, pos[1] + d_dir[1] * clear * 0.85), 2),
            round(float(pos[1] + d_dir[1] * clear * 0.85), 2)]
    loc = dict(
        id=f"{lid}_{side}", group=lid, type=typ, tier=tier, owner=owner if owner >= 0 else -1, side=side,
        scene=f"res://scenes/resources/{spec['scene']}.tscn",
        position=[round(float(pos[0]), 2), round(y, 2), round(float(pos[1]), 2)], yaw=round(float(yaw), 4),
        footprint_radius=R, clear_radius=round(clear, 1), interaction_radius=round(R + spec["gather_range"] + 3.0 if typ != "wood" else R + 4.5, 1),
        amount=amount, gather_rate=econ["rate"], gather_range=spec["gather_range"], carry_capacity=spec["carry"],
        max_workers=len(slots) if typ == "wood" else spec["max_workers"],
        respawn_time=econ["respawn"], regen_rule=econ["regen"], regen_rate=econ["regen_rate"], regen_delay=econ["delay"],
        dropoff_base="BASE_A" if base_idx == 0 else "BASE_B",
        dist_to_base_a=round(float(np.hypot(pos[0] - BA[0], pos[1] - BA[1])), 1),
        dist_to_base_b=round(float(np.hypot(pos[0] - BB[0], pos[1] - BB[1])), 1),
        gathering_point=gp, approach_point=appr, slots=slots,
        nav_footprint=poly(pos, R + 0.8), mesh_variant=int(trees_seed % spec["mesh_variants"]),
        tree_count=len(trees) if trees else 0, strategic_value={"gold": 3, "wood": 1, "stone": 2, "crystal": 5}[typ] * (2 if tier == "center" else 1),
    )
    if trees:
        loc["_trees"] = trees
    LOCATIONS.append(loc)


for i, r in enumerate(RESULT):
    seed = 1000 + i
    if r["owner"] == 0:
        add_location(r["lid"], r["typ"], r["tier"], 0, "p1", r["spec"], r["R"], r["clear"], r["a"], seed)
        add_location(r["lid"], r["typ"], r["tier"], 1, "p2", r["spec"], r["R"], r["clear"], r["b"], seed)
    else:
        add_location(r["lid"], r["typ"], r["tier"], -1, "ne" if r["a"]["pos"][0] > r["a"]["pos"][1] else "sw", r["spec"], r["R"], r["clear"], r["a"], seed)
        add_location(r["lid"], r["typ"], r["tier"], -1, "sw" if r["a"]["pos"][0] > r["a"]["pos"][1] else "ne", r["spec"], r["R"], r["clear"], r["b"], seed)
# unique side names for neutral pairs (a/b)
seen = {}
for l in LOCATIONS:
    if l["owner"] == -1:
        k = l["group"]; seen[k] = seen.get(k, 0) + 1
        l["id"] = f"{k}_{'a' if seen[k] == 1 else 'b'}"
        l["side"] = "a" if seen[k] == 1 else "b"

# ------------------------------------------------------------------ validation / balance
problems = []
for l in LOCATIONS:
    for s in l["slots"]:
        if abs(s[0]) > PLAY or abs(s[2]) > PLAY or mask_at(BLOCK_NEW, s[0], s[2]):
            problems.append(f"{l['id']}: slot {s} invalid")
    if any(np.hypot(l["position"][0] - o["position"][0], l["position"][2] - o["position"][2]) < 0.7 * (l["clear_radius"] + o["clear_radius"])
           for o in LOCATIONS if o is not l):
        problems.append(f"{l['id']}: overlaps another resource area")
bal = {}
for l in LOCATIONS:
    if l["owner"] in (0, 1):
        d = l["dist_to_base_a"] if l["owner"] == 0 else l["dist_to_base_b"]
        bal.setdefault(l["owner"], []).append((l["group"], round(d, 1), l["amount"]))
a_d = sorted(bal[0]); b_d = sorted(bal[1])
stats = dict(
    locations=len(LOCATIONS),
    by_type={t: sum(l["type"] == t for l in LOCATIONS) for t in TYPES},
    player_amounts={t: [sum(l["amount"] for l in LOCATIONS if l["owner"] == o and l["type"] == t) for o in (0, 1)] for t in TYPES},
    base_distance_p1=a_d, base_distance_p2=b_d,
    max_distance_mismatch_m=round(max(abs(x[1] - y[1]) for x, y in zip(a_d, b_d)), 2),
    center_distance_sum={"to_base_a": round(sum(l["dist_to_base_a"] for l in LOCATIONS if l["owner"] == -1), 1),
                         "to_base_b": round(sum(l["dist_to_base_b"] for l in LOCATIONS if l["owner"] == -1), 1)},
    problems=problems,
)

TYPE_DEFAULTS = {t: dict(scene=f"res://scenes/resources/{v['scene']}.tscn", footprint_radius=v["fp"], clear_radius=v["clear"],
                         gather_range=v["gather_range"], carry_capacity=v["carry"], max_workers=v["max_workers"]) for t, v in TYPES.items()}
out = dict(version=1, units="metres; world X/Z centred, Y up", resource_types=TYPE_DEFAULTS,
           variables=["resource_type", "resource_amount", "gather_rate", "gather_range", "respawn_time", "max_workers"],
           economy={f"{k[0]}:{k[1]}": v for k, v in ECON.items()}, tree_amount=TREE_AMOUNT,
           removed_blockers=removed_info,
           locations=[{k: v for k, v in l.items() if not k.startswith("_")} for l in LOCATIONS], stats=stats)
json.dump(out, open(f"{DATA}/resources.json", "w"), indent=1)

# ------------------------------------------------------------------ ground paint
paint = np.zeros((RES, RES, 4), np.uint8)
clr = np.zeros((RES, RES), np.float32); typ_code = np.zeros((RES, RES), np.uint8); ringm = np.zeros((RES, RES), np.float32)
CODE = {"gold": 64, "wood": 128, "stone": 192, "crystal": 255}
for l in LOCATIONS:
    x, z = l["position"][0], l["position"][2]
    sl, sx = window((x, z), l["clear_radius"] + 3)
    d = np.hypot(RX[sl, sx] - x, RZ[sl, sx] - z)
    ang = np.arctan2(RZ[sl, sx] - z, RX[sl, sx] - x)
    wob = 1 + 0.10 * np.sin(ang * 3 + x) + 0.06 * np.sin(ang * 7 + z)
    r_patch = l["clear_radius"] * 0.72 * wob
    a = np.clip(1 - (d - r_patch * 0.7) / (r_patch * 0.3), 0, 1)
    upd = a > clr[sl, sx]
    typ_code[sl, sx] = np.where(upd, CODE[l["type"]], typ_code[sl, sx])
    clr[sl, sx] = np.maximum(clr[sl, sx], a)
    r0 = l["footprint_radius"] + 1.0 if l["type"] != "wood" else l["footprint_radius"] + 0.5
    ringm[sl, sx] = np.maximum(ringm[sl, sx], np.clip(1 - np.abs(d - (r0 + 2.6)) / 2.2, 0, 1))
paint[..., 0] = (gaussian_filter(clr, 1.0) * 255).astype(np.uint8)
paint[..., 1] = typ_code
paint[..., 2] = (ringm * 255).astype(np.uint8)
paint[..., 3] = 255
Image.fromarray(paint, "RGBA").save(f"{DATA}/resourcemap.png")

# ------------------------------------------------------------------ scene writer
RM = "res://resources/meshes/"
VARIETY = ["pine", "oak", "birch"]
LAYER_RESOURCES, LAYER_UNITS = 8, 2              # physics layer 4 "resources", layer 2 "units"


def f(v):
    return ("%.4f" % v).rstrip("0").rstrip(".") if abs(v) > 1e-6 else "0"


def fl(v):
    t = f(float(v))
    return t if "." in t else t + ".0"


def tf_origin(p):
    return f"Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, {p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f})"


class Scn:
    """Tiny .tscn text writer (ext resources, sub resources, node blocks)."""
    def __init__(self):
        self.ext, self.subs, self.nodes = [], [], []

    def x(self, kind, path):
        for i, (k, p_) in enumerate(self.ext):
            if p_ == path:
                return f'ExtResource("{i + 1}")'
        self.ext.append((kind, path)); return f'ExtResource("{len(self.ext)}")'

    def sub(self, text_after_header, kind, rid):
        self.subs.append(f'[sub_resource type="{kind}" id="{rid}"]\n{text_after_header}\n')
        return f'SubResource("{rid}")'

    def node(self, header, *lines):
        self.nodes.append(header); self.nodes += list(lines); self.nodes.append("")

    def text(self, root_header, root_lines):
        head = f'[gd_scene load_steps={len(self.ext) + len(self.subs) + 1} format=3]\n\n'
        head += "".join(f'[ext_resource type="{k}" path="{p_}" id="{i + 1}"]\n' for i, (k, p_) in enumerate(self.ext)) + "\n"
        return head + "\n".join(self.subs) + "\n" + root_header + "\n" + "\n".join(root_lines) + "\n\n" + "\n".join(self.nodes) + "\n"


META_ORDER = ["location_id", "resource_type", "tier", "owner", "resource_amount", "gather_rate", "gather_range", "respawn_time",
              "max_workers", "carry_capacity", "regen_rule", "regen_rate", "regen_delay", "dropoff_base", "strategic_value"]


def meta_lines(d):
    out = []
    for k in META_ORDER:
        v = d[k]
        out.append(f"metadata/{k} = " + (f'"{v}"' if isinstance(v, str) else (fl(v) if isinstance(v, float) else str(v))))
    return out


def write_base():
    sc = Scn()
    body = sc.sub("height = 4.0\nradius = 4.0", "CylinderShape3D", "Shape_body")
    area = sc.sub("radius = 9.0", "SphereShape3D", "Shape_area")
    grad = sc.sub("offsets = PackedFloat32Array(0, 1)\ncolors = PackedColorArray(1, 1, 1, 1, 1, 1, 1, 0)", "Gradient", "Gradient_glow")
    gtex = sc.sub(f'gradient = SubResource("Gradient_glow")\nwidth = 64\nheight = 64\nfill = 1\nfill_from = Vector2(0.5, 0.5)\nfill_to = Vector2(1, 0.5)', "GradientTexture2D", "Tex_glow")
    sc.node('[node name="CollisionShape3D" type="CollisionShape3D" parent="."]', "transform = " + tf_origin((0, 2, 0)), f"shape = {body}")
    sc.node('[node name="Mesh" type="MeshInstance3D" parent="."]', "visibility_range_end = 150.0", "visibility_range_end_margin = 20.0", "visibility_range_fade_mode = 1")
    sc.node('[node name="MeshLOD" type="MeshInstance3D" parent="."]', "visibility_range_begin = 150.0", "visibility_range_begin_margin = 20.0", "visibility_range_fade_mode = 1", "cast_shadow = 0")
    sc.node('[node name="GatheringPoint" type="Marker3D" parent="."]', "transform = " + tf_origin((0, 0, 6)))
    sc.node('[node name="WorkerInteractionArea" type="Area3D" parent="."]', "collision_layer = 0", f"collision_mask = {LAYER_UNITS}", "monitorable = false")
    sc.node('[node name="CollisionShape3D" type="CollisionShape3D" parent="WorkerInteractionArea"]', f"shape = {area}")
    sc.node('[node name="NavigationAccess" type="Node3D" parent="."]')
    sc.node('[node name="Approach" type="Marker3D" parent="NavigationAccess"]', "transform = " + tf_origin((0, 0, 12)))
    sc.node('[node name="ResourceVisual" type="Node3D" parent="."]')
    sc.node('[node name="Glow" type="Sprite3D" parent="ResourceVisual"]', "visible = false", "transform = " + tf_origin((0, 3, 0)),
            "modulate = Color(1, 1, 1, 0.35)", "pixel_size = 0.03", "billboard = 1", "shaded = false", "double_sided = false",
            f"texture = {gtex}")
    root = ('[node name="ResourceNode" type="StaticBody3D" groups=["resource_nodes"]]',
            [f"collision_layer = {LAYER_RESOURCES}", "collision_mask = 0",
             'metadata/location_id = ""', 'metadata/resource_type = ""', 'metadata/tier = ""', "metadata/owner = -1",
             "metadata/resource_amount = 0", "metadata/gather_rate = 1.0", "metadata/gather_range = 2.4",
             "metadata/respawn_time = -1", "metadata/max_workers = 8", "metadata/carry_capacity = 10",
             'metadata/regen_rule = "limited"', "metadata/regen_rate = 0.0", "metadata/regen_delay = 0",
             'metadata/dropoff_base = ""', "metadata/strategic_value = 1"])
    open(f"{SCENES}/resource_node.tscn", "w").write(sc.text(*root))


TYPED = {
    # type: (scene, node name, mesh base, collider r/h, glow colour)
    "gold": ("gold_deposit", "GoldDeposit", "gold_deposit", (4.0, 4.0), "Color(1, 0.78, 0.25, 0.42)"),
    "stone": ("stone_quarry", "StoneQuarry", "stone_quarry", (5.2, 4.5), None),
    "crystal": ("crystal_cluster", "CrystalCluster", "crystal_cluster", (3.0, 6.0), "Color(0.7, 0.45, 1, 0.5)"),
    "wood": ("wood_zone", "WoodZone", None, (6.0, 6.0), None),
}


def write_typed():
    for typ, (scene, nname, mesh_base, (cr, ch), glow) in TYPED.items():
        spec = TYPES[typ]
        for variant in ((0, 1) if mesh_base else (0,)):
            sc = Scn()
            if variant == 0:
                base = sc.x("PackedScene", "res://scenes/resources/resource_node.tscn")
                lines = []
                econ = next(v for k, v in ECON.items() if k[0] == typ)
                lines += [f'metadata/resource_type = "{typ}"', f"metadata/resource_amount = {econ['amount']}", f"metadata/gather_rate = {fl(econ['rate'])}",
                          f"metadata/gather_range = {fl(spec['gather_range'])}", f"metadata/respawn_time = {econ['respawn']}",
                          f"metadata/max_workers = {spec['max_workers']}", f"metadata/carry_capacity = {spec['carry']}",
                          f'metadata/regen_rule = "{econ["regen"]}"', f"metadata/regen_rate = {fl(econ['regen_rate'])}", f"metadata/regen_delay = {econ['delay']}"]
                shp = sc.sub(f"height = {ch}\nradius = {cr}", "CylinderShape3D", "Shape_body")
                sc.node('[node name="CollisionShape3D" parent="." index="0"]', "transform = " + tf_origin((0, ch / 2, 0)), f"shape = {shp}")
                iarea = (spec["fp"] + spec["gather_range"] + 3.0) if typ != "wood" else 14.0
                sph = sc.sub(f"radius = {iarea:.1f}", "SphereShape3D", "Shape_area")
                sc.node('[node name="CollisionShape3D" parent="WorkerInteractionArea" index="0"]', f"shape = {sph}")
                if mesh_base:
                    sc.node('[node name="Mesh" parent="." index="1"]', f'mesh = {sc.x("ArrayMesh", RM + mesh_base + "_a.res")}')
                    sc.node('[node name="MeshLOD" parent="." index="2"]', f'mesh = {sc.x("ArrayMesh", RM + mesh_base + "_a_lod.res")}')
                    sr = spec["slot_r"]
                    sc.node('[node name="GatheringPoint" parent="." index="3"]', "transform = " + tf_origin((0, 0, sr)))
                    sc.node('[node name="Approach" parent="NavigationAccess" index="0"]', "transform = " + tf_origin((0, 0, spec["clear"] * 0.85)))
                    for k in range(spec["slots"]):
                        a_ = 2 * np.pi * k / spec["slots"]
                        sc.node(f'[node name="Slot_{k}" type="Marker3D" parent="NavigationAccess"]', "transform = " + tf_origin((sr * np.sin(a_), 0, sr * np.cos(a_))))
                if glow:
                    sc.node('[node name="Glow" parent="ResourceVisual" index="0"]', "visible = true", f"modulate = {glow}",
                            f"pixel_size = {0.06 if typ == 'crystal' else 0.05}")
                open(f"{SCENES}/{scene}.tscn", "w").write(sc.text(f'[node name="{nname}" instance={base}]', lines))
            else:
                base = sc.x("PackedScene", f"res://scenes/resources/{scene}.tscn")
                sc.node('[node name="Mesh" parent="." index="1"]', f'mesh = {sc.x("ArrayMesh", RM + mesh_base + "_b.res")}')
                sc.node('[node name="MeshLOD" parent="." index="2"]', f'mesh = {sc.x("ArrayMesh", RM + mesh_base + "_b_lod.res")}')
                open(f"{SCENES}/{scene}_b.tscn", "w").write(sc.text(f'[node name="{nname}B" instance={base}]', []))


write_base()
write_typed()

# ---- layout: every resource location instanced on the map ---------------------------------
lay = Scn()
nid = 0
for l in LOCATIONS:
    typ = l["type"]
    scene = TYPES[typ]["scene"] + ("_b" if l["mesh_variant"] == 1 and typ != "wood" else "")
    name = l["id"]
    yaw = l["yaw"]; c, s_ = np.cos(yaw), np.sin(yaw)
    tfm = f"Transform3D({c:.5f}, 0, {s_:.5f}, 0, 1, 0, {-s_:.5f}, 0, {c:.5f}, {l['position'][0]:.3f}, {l['position'][1]:.3f}, {l['position'][2]:.3f})"
    meta_kv = dict(location_id=l["id"], resource_type=typ, tier=l["tier"], owner=l["owner"], resource_amount=l["amount"],
                   gather_rate=l["gather_rate"], gather_range=l["gather_range"], respawn_time=l["respawn_time"],
                   max_workers=l["max_workers"], carry_capacity=l["carry_capacity"], regen_rule=l["regen_rule"],
                   regen_rate=l["regen_rate"], regen_delay=l["regen_delay"], dropoff_base=l["dropoff_base"], strategic_value=l["strategic_value"])
    sref = lay.x("PackedScene", f"res://scenes/resources/{scene}.tscn")
    lay.node(f'[node name="{name}" parent="." instance={sref} groups=["resource_nodes", "{typ}_nodes"]]', "transform = " + tfm, *meta_lines(meta_kv))

    def to_local(p):                                # world point -> node-local (inverse yaw rotation)
        dx, dz = p[0] - l["position"][0], p[2] - l["position"][2]
        return (dx * c - dz * s_, p[1] - l["position"][1], dx * s_ + dz * c)
    gp, ap = to_local(l["gathering_point"]), to_local(l["approach_point"])
    lay.node(f'[node name="GatheringPoint" parent="{name}" index="3"]', "transform = " + tf_origin(gp))
    lay.node(f'[node name="Approach" parent="{name}/NavigationAccess" index="0"]', "transform = " + tf_origin(ap))
    if typ != "wood":
        continue
    nid += 1
    sid = lay.sub(f"height = 6.0\nradius = {l['footprint_radius'] * 0.92:.2f}", "CylinderShape3D", f"cyl_{nid}")
    lay.node(f'[node name="CollisionShape3D" parent="{name}" index="0"]', "transform = " + tf_origin((0, 3, 0)), f"shape = {sid}")
    sid2 = lay.sub(f"radius = {l['interaction_radius']:.2f}", "SphereShape3D", f"sph_{nid}")
    lay.node(f'[node name="CollisionShape3D" parent="{name}/WorkerInteractionArea" index="0"]', f"shape = {sid2}")
    for k, sp in enumerate(l["slots"]):
        lp = to_local(sp)
        lay.node(f'[node name="Slot_{k}" type="Marker3D" parent="{name}/NavigationAccess"]', "transform = " + tf_origin(lp))
    for v in range(3):
        tl = [t for t in l["_trees"] if t[1] == v]
        if not tl:
            continue
        buf = []
        for p_, _, sc_, rot in tl:
            wx, wz = l["position"][0] + p_[0], l["position"][2] + p_[1]
            ty = hgt(wx, wz) - l["position"][1] - 0.15
            lx, lz = p_[0] * c + p_[1] * s_, -p_[0] * s_ + p_[1] * c
            rr = rot - yaw
            cc, ss = np.cos(rr) * sc_, np.sin(rr) * sc_
            buf += [cc, 0, ss, lx, 0, sc_, 0, ty, -ss, 0, cc, lz]
        for lod in (0, 1):
            nid += 1
            mref = lay.x("ArrayMesh", RM + f"tree_{VARIETY[v]}" + ("_lod" if lod else "") + ".res")
            mm = lay.sub(f'transform_format = 1\ninstance_count = {len(tl)}\nmesh = {mref}\nbuffer = PackedFloat32Array({", ".join(f(x) for x in buf)})',
                         "MultiMesh", f"mm_{nid}")
            vis = ["visibility_range_begin = 150.0", "visibility_range_begin_margin = 20.0", "visibility_range_fade_mode = 1", "cast_shadow = 0"] if lod \
                else ["visibility_range_end = 150.0", "visibility_range_end_margin = 20.0", "visibility_range_fade_mode = 1"]
            lay.node(f'[node name="Trees_{VARIETY[v].capitalize()}{"_LOD" if lod else ""}" type="MultiMeshInstance3D" parent="{name}/ResourceVisual"]',
                     f"multimesh = {mm}", *vis)
open(f"{SCENES}/resource_layout.tscn", "w").write(lay.text('[node name="Resources" type="Node3D"]', []))

print(json.dumps({k: v for k, v in stats.items() if k not in ("base_distance_p1", "base_distance_p2")}, indent=1))
print("P1 distances:", a_d); print("P2 distances:", b_d)

# ------------------------------------------------------------------ preview
if "--preview" in sys.argv:
    W = 1370
    base = Image.open("/tmp/x/paths_debug.png").convert("RGB").resize((W, W)) if os.path.exists("/tmp/x/paths_debug.png") else Image.new("RGB", (W, W), (60, 90, 50))
    d = ImageDraw.Draw(base, "RGBA"); S = W / SZ
    px = lambda x, z: ((x + SZ / 2) * S, (z + SZ / 2) * S)
    col = {"gold": (255, 205, 40), "wood": (40, 170, 60), "stone": (190, 190, 190), "crystal": (190, 90, 255)}
    for l in LOCATIONS:
        x, z = px(l["position"][0], l["position"][2]); r = l["clear_radius"] * S
        d.ellipse([x - r, z - r, x + r, z + r], outline=col[l["type"]] + (230,), width=2, fill=col[l["type"]] + (45,))
        rr = 7 if l["type"] != "crystal" else 6
        if l["type"] == "crystal":
            d.polygon([(x, z - 9), (x + 7, z), (x, z + 9), (x - 7, z)], fill=col["crystal"] + (255,), outline=(255, 255, 255, 255))
        else:
            d.ellipse([x - rr, z - rr, x + rr, z + rr], fill=col[l["type"]] + (255,), outline=(0, 0, 0, 255), width=2)
        for s in l["slots"]:
            sx_, sz_ = px(s[0], s[2]); d.ellipse([sx_ - 1.5, sz_ - 1.5, sx_ + 1.5, sz_ + 1.5], fill=(255, 255, 255, 220))
    lg = [("GOLD", col["gold"]), ("WOOD", col["wood"]), ("STONE", col["stone"]), ("CRYSTAL", col["crystal"])]
    d.rectangle([W - 190, 16, W - 16, 150], fill=(0, 0, 0, 150))
    for i, (nm, c_) in enumerate(lg):
        d.ellipse([W - 176, 30 + i * 28, W - 160, 46 + i * 28], fill=c_ + (255,), outline=(0, 0, 0, 255)); d.text((W - 150, 31 + i * 28), nm + (" (rare, central only)" if nm == "CRYSTAL" else ""), fill=(255, 255, 255, 255))
    d.text((W - 180, 134), "white dots = worker slots", fill=(255, 255, 255, 255))
    for nm, b in (("PLAYER 1", BA), ("PLAYER 2", BB)):
        x, z = px(*b); d.ellipse([x - 9, z - 9, x + 9, z + 9], fill=(255, 40, 40, 255), outline=(255, 255, 255, 255), width=2); d.text((x + 12, z - 6), nm, fill=(255, 255, 255, 255))
    base.save(sys.argv[sys.argv.index("--preview") + 1] if len(sys.argv) > sys.argv.index("--preview") + 1 else "/tmp/x/resource_map.png")
