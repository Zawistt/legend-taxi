"""Qumtepa 5v5 — 2-bosqich: Godot 4.3 loyihasini yaratadi (qumtepa-5v5/godot/).

Kerak: build5.py natijasi (build/meta5.json, godot/map/*.glb) va analyze5.py natijasi (docs/analysis_stage1.json).
O'yin skriptlari, bomba sahnasi va tovushlar Qumtepa v2 dan olinadi (qumtepa-v2/), ular xaritaga bog'liq emas.
Xaritaga bog'liq hamma narsa (map_data.gd, main.tscn, collision.tscn, tests/test_data.gd) shu yerda yaratiladi.

Ishga tushirish:  cd qumtepa-5v5/tools && python3 gen_godot5.py
So'ng NavMesh:    cd ../godot && godot --headless -s res://tools/bake_nav.gd && (cd ../tools && python3 gen_godot5.py)
"""
import json, math, os, shutil
import numpy as np
import layout5 as L

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "godot"))
V2 = os.path.normpath(os.path.join(HERE, "..", "..", "qumtepa-v2"))
SRC = os.path.join(HERE, "godot_src")
meta = json.load(open(os.path.join(HERE, "build", "meta5.json")))
an = json.load(open(os.path.join(HERE, "..", "docs", "analysis_stage1.json")))
NAVMESH = os.path.exists(f"{OUT}/map/navmesh.res")
E0, SIZE = L.ORIGIN, L.G * L.CELL


def f(v):
    return f"{v:.4g}"


def T(x, y, z, yaw_pi=False):
    b = "-1, 0, 0, 0, 1, 0, 0, 0, -1" if yaw_pi else "1, 0, 0, 0, 1, 0, 0, 0, 1"
    return f"Transform3D({b}, {f(x)}, {f(y)}, {f(z)})"


def V3(p, y=None):
    if len(p) == 2:
        return f"Vector3({f(p[0])}, {f(y or 0.0)}, {f(p[1])})"
    return f"Vector3({f(p[0])}, {f(p[1])}, {f(p[2])})"


class Scene:
    def __init__(self):
        self.ext, self.sub, self.nodes = [], [], []

    def add_ext(self, typ, path, rid):
        self.ext.append(f'[ext_resource type="{typ}" path="{path}" id="{rid}"]')
        return f'ExtResource("{rid}")'

    def add_sub(self, typ, rid, **props):
        body = "".join(f"\n{k} = {v}" for k, v in props.items())
        self.sub.append(f'[sub_resource type="{typ}" id="{rid}"]{body}')
        return f'SubResource("{rid}")'

    def node(self, name, typ=None, parent=None, groups=None, instance=None, **props):
        h = f'[node name="{name}"'
        if typ:
            h += f' type="{typ}"'
        if parent is not None:
            h += f' parent="{parent}"'
        if instance:
            h += f" instance={instance}"
        if groups:
            h += " groups=[" + ", ".join(f'"{g}"' for g in groups) + "]"
        h += "]"
        self.nodes.append(h + "".join(f"\n{k} = {v}" for k, v in props.items()))

    def save(self, path):
        n = len(self.ext) + len(self.sub) + 1
        txt = f"[gd_scene load_steps={n} format=3]\n\n" + "\n\n".join(self.ext + self.sub + self.nodes) + "\n"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(txt)


def merge_boxes(boxes):
    """Yonma-yon qutilarni birlashtiradi (x, keyin z bo'ylab) — to'qnashuv shakllari soni kamayadi."""
    bx = [tuple(round(v, 3) for v in b) for b in boxes]
    for ax in (0, 2):
        o = 2 if ax == 0 else 0
        bx.sort(key=lambda b: (b[1], b[4], b[o], b[o + 3], b[ax]))
        out = []
        for b in bx:
            if out:
                p = out[-1]
                if p[1] == b[1] and p[4] == b[4] and p[o] == b[o] and p[o + 3] == b[o + 3] and abs(p[ax + 3] - b[ax]) < 1e-3:
                    q = list(p); q[ax + 3] = b[ax + 3]; out[-1] = tuple(q); continue
            out.append(b)
        bx = out
    return bx


def plat_h(x, z):
    for x0, z0, x1, z1, h in meta["plat"]:
        if x0 <= x <= x1 and z0 <= z <= z1:
            return h
    return 0.0


# ------------------------------------------------------------------ papkalar, v2 dan skriptlar va tovushlar
for d in ("map", "scripts", "scenes", "audio", "tests", "tools"):
    os.makedirs(f"{OUT}/{d}", exist_ok=True)
for fn in ("bomb.gd", "input_setup.gd"):   # game_mode.gd, hud.gd, bomb.gd, player.gd — godot_src dan (CS2 qoidalari)
    shutil.copy(f"{V2}/scripts/{fn}", f"{OUT}/scripts/{fn}")
for fn in os.listdir(f"{V2}/audio"):
    shutil.copy(f"{V2}/audio/{fn}", f"{OUT}/audio/{fn}")
shutil.copy(f"{V2}/scenes/bomb.tscn", f"{OUT}/scenes/bomb.tscn")
os.makedirs(f"{OUT}/weapons", exist_ok=True)
for sub in ("scripts", "tests", "weapons"):
    for fn in os.listdir(f"{SRC}/{sub}"):
        shutil.copy(f"{SRC}/{sub}/{fn}", f"{OUT}/{sub}/{fn}")
for fn in os.listdir(f"{SRC}/tools"):
    shutil.copy(f"{SRC}/tools/{fn}", f"{OUT}/tools/{fn}")

# ------------------------------------------------------------------ map_data.gd
R = L.ROUND
md = f'''extends RefCounted
## AVTOMATIK YARATILGAN (qumtepa-5v5/tools/gen_godot5.py, layout5.py asosida). Qo'lda o'zgartirmang.

const CELL := {L.CELL}
const ORIGIN := {L.ORIGIN}
const CALLOUT_NAMES := {json.dumps(an["callout_names"], ensure_ascii=False)}
const CALLOUT_GRID := {json.dumps(an["callout_grid"])}
## Raund qoidalari (soniya). 110 m xarita uchun: T site'ga 18–20 s, CT 12–13 s da yetadi.
const ROUND := {{
	"freeze": {R["freeze"]}, "buy_time": {R["buy_time"]}, "round_time": {R["round_time"]},
	"bomb_timer": {R["bomb_timer"]}, "plant_time": {R["plant_time"]}, "defuse_time": {R["defuse_time"]},
	"defuse_time_kit": {R["defuse_time_kit"]}, "round_end": {R["round_end"]}, "win_rounds": {R["win_rounds"]},
}}


static func callout_at(p: Vector3) -> String:
	var c := int(floor((p.x - ORIGIN) / CELL))
	var r := int(floor((p.z - ORIGIN) / CELL))
	if r < 0 or c < 0 or r >= CALLOUT_GRID.size() or c >= CALLOUT_GRID[0].size():
		return ""
	return CALLOUT_NAMES[CALLOUT_GRID[r][c]]
'''
open(f"{OUT}/scripts/map_data.gd", "w").write(md)

# ------------------------------------------------------------------ collision.tscn
s = Scene()
s.add_sub("StandardMaterial3D", "m_pclip", transparency="1", shading_mode="0", cull_mode="2", albedo_color="Color(0.6, 0.2, 0.9, 0.18)")
s.add_sub("StandardMaterial3D", "m_gclip", transparency="1", shading_mode="0", cull_mode="2", albedo_color="Color(0.95, 0.8, 0.1, 0.12)")
s.node("Collision", "Node3D")
counts = {}
sid = 0
for surf in ("stone", "wood", "metal", "cloth"):
    boxes = merge_boxes([c[1:] for c in meta["col"] if c[0] == surf])
    body = f"World_{surf}"
    s.node(body, "StaticBody3D", ".", collision_layer="1", collision_mask="0", **{"metadata/surface": f'"{surf}"'})
    for b in boxes:
        sid += 1
        sz = (b[3] - b[0], b[4] - b[1], b[5] - b[2])
        sh = s.add_sub("BoxShape3D", f"b{sid}", size=f"Vector3({f(sz[0])}, {f(sz[1])}, {f(sz[2])})")
        s.node(f"S{sid}", "CollisionShape3D", body, transform=T((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2), shape=sh)
    if surf == "stone":
        for i, (_sf, pts) in enumerate(meta["ramps"]):
            sid += 1
            arr = ", ".join(f"{f(p[0])}, {f(p[1])}, {f(p[2])}" for p in pts)
            sh = s.add_sub("ConvexPolygonShape3D", f"r{sid}", points=f"PackedVector3Array({arr})")
            s.node(f"Ramp{i}", "CollisionShape3D", body, shape=sh)
    counts[surf] = len(boxes)
for key, name, layer, mat in (("clip_p", "PlayerClip", 2, "m_pclip"), ("clip_g", "GrenadeClip", 4, "m_gclip")):
    boxes = merge_boxes(meta[key])
    s.node(name, "StaticBody3D", ".", collision_layer=str(layer), collision_mask="0")
    for b in boxes:
        sid += 1
        sz = (b[3] - b[0], b[4] - b[1], b[5] - b[2])
        sh = s.add_sub("BoxShape3D", f"b{sid}", size=f"Vector3({f(sz[0])}, {f(sz[1])}, {f(sz[2])})")
        ms = s.add_sub("BoxMesh", f"bm{sid}", size=f"Vector3({f(sz[0])}, {f(sz[1])}, {f(sz[2])})", material=f'SubResource("{mat}")')
        tr = T((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2)
        s.node(f"S{sid}", "CollisionShape3D", name, transform=tr, shape=sh)
        s.node(f"V{sid}", "MeshInstance3D", name, groups=["debug_viz"], visible="false", transform=tr, mesh=ms)
    counts[name] = len(boxes)
s.save(f"{OUT}/map/collision.tscn")

# ------------------------------------------------------------------ main.tscn (arxitektura) va main_greybox.tscn
ART = os.path.exists(f"{OUT}/map/qumtepa5v5.glb")


# ------------------------------------------------------------------ 6-bosqich: yorug'lik, tovush, atmosfera ma'lumotlari
COVERED = [(r, c) for r in range(L.G) for c in range(L.G) if L.grid[r][c] in L.COVER]
FILL_LIGHTS = []
_lamps = [tuple(p) for p in meta["lamps"]]
for r, c in COVERED:
    x_, z_ = L.m(c, r)
    if all(math.hypot(x_ - p[0], z_ - p[2]) > 5.0 for p in _lamps + FILL_LIGHTS):
        FILL_LIGHTS.append((x_, 3.0, z_))
# qopqoqli kataklarni to'rtburchaklarga birlashtirish (aks-sado zonalari)
REVERB_RECTS = []
_done = set()
for r, c in COVERED:
    if (r, c) in _done:
        continue
    t_ = L.grid[r][c]
    w_ = 1
    while (r, c + w_) not in _done and c + w_ < L.G and L.grid[r][c + w_] == t_:
        w_ += 1
    h_ = 1
    while r + h_ < L.G and all(L.grid[r + h_][c + k] == t_ and (r + h_, c + k) not in _done for k in range(w_)):
        h_ += 1
    for rr in range(r, r + h_):
        for cc in range(c, c + w_):
            _done.add((rr, cc))
    REVERB_RECTS.append((L.ORIGIN + c * L.CELL, L.ORIGIN + r * L.CELL, L.ORIGIN + (c + w_) * L.CELL, L.ORIGIN + (r + h_) * L.CELL, L.COVER[t_]))
# fon tovushi manbalari: har hududning ochiq kataklari markazida; yopiq yo'laklarda "tunnel"
AMB_FILES = ["bozor", "masjid", "madrasa", "karvon", "qala", "tunnel"]
AMB_SOURCES = []
for d_ in ("bozor", "masjid", "madrasa", "karvon", "qala"):
    cells = [(r, c) for r in range(L.G) for c in range(L.G) if L.grid[r][c] in ".AB" and L.DISTRICT[r][c] == d_]
    if not cells:
        cells = [(r, c) for r in range(L.G) for c in range(L.G) if L.grid[r][c] != "#" and L.DISTRICT[r][c] == d_]
    mx = sum(L.m(c, r)[0] for r, c in cells) / len(cells)
    mz = sum(L.m(c, r)[1] for r, c in cells) / len(cells)
    best = min(cells, key=lambda rc: (L.m(rc[1], rc[0])[0] - mx) ** 2 + (L.m(rc[1], rc[0])[1] - mz) ** 2)
    bx, bz = L.m(best[1], best[0])
    AMB_SOURCES.append((d_, (bx, 5.0, bz), -20.0))
for zname in ("Lower tunnels", "Upper tunnels", "Mid", "Catwalk"):
    x0_, z0_, x1_, z1_ = L.zone_rect_m(zname)
    AMB_SOURCES.append(("tunnel", ((x0_ + x1_) / 2, 2.5, (z0_ + z1_) / 2), -22.0))
# havodagi chang: katta ochiq maydonlar ustida
DUST = []
for zname, n in (("A site", 260), ("B site", 260), ("Top mid", 200), ("CT mid", 120), ("Long", 90), ("Outside long", 80)):
    x0_, z0_, x1_, z1_ = L.zone_rect_m(zname)
    DUST.append((((x0_ + x1_) / 2, 2.2, (z0_ + z1_) / 2), (x1_ - x0_, 3.6, z1_ - z0_), n))

# Quyosh: g'arbda, 50° balandlikda, sharq-g'arb o'qidan 4° og'gan. Euler YXZ: avval pastga (−50°), keyin sharqqa buriladi.
SUN_ROT = "Vector3(-50, -86, 0)"
DECAL_COUNT = {}


LOWPOLY = os.environ.get("LOOK", "lowpoly") == "lowpoly"


def sky_env(s, full=True):
    if LOWPOLY:
        return sky_env_lowpoly(s, full)
    return sky_env_pbr(s, full)


def sky_env_lowpoly(s, full=True):
    """Stilizatsiya (low-poly): gradient osmon, iliq quyosh, yumshoq soya (SSAO), yengil tuman. Teksturasiz.
    Og'ir effektlar (SDFGI, SSR, hajmli tuman) yo'q — tekis ranglar va aniq shakllar uchun kerak emas."""
    s.add_sub("ProceduralSkyMaterial", "sky_mat", sky_top_color="Color(0.24, 0.5, 0.84, 1)", sky_horizon_color="Color(0.78, 0.84, 0.88, 1)",
              sky_curve="0.12", ground_bottom_color="Color(0.52, 0.42, 0.3, 1)", ground_horizon_color="Color(0.84, 0.78, 0.66, 1)",
              sun_angle_max="18.0", sun_curve="0.12", energy_multiplier="1.0")
    s.add_sub("Sky", "sky", sky_material='SubResource("sky_mat")', radiance_size="1")
    props = dict(background_mode="2", sky='SubResource("sky")', ambient_light_source="3", ambient_light_color="Color(0.8, 0.76, 0.7, 1)",
                 ambient_light_sky_contribution="0.7", ambient_light_energy="0.75", reflected_light_source="2",
                 tonemap_mode="2", tonemap_exposure="0.85", tonemap_white="6.0",
                 fog_enabled="true", fog_light_color="Color(0.82, 0.84, 0.86, 1)", fog_density="0.0015", fog_sky_affect="0.1",
                 volumetric_fog_density="0.0")
    if full:
        props.update(ssao_enabled="true", ssao_radius="1.2", ssao_intensity="1.6", ssao_detail="0.3", ssil_enabled="true", ssil_intensity="0.6",
                     glow_enabled="true", glow_intensity="0.35", glow_bloom="0.03", glow_hdr_threshold="1.3",
                     adjustment_enabled="true", adjustment_saturation="1.12", adjustment_contrast="1.04")
    s.add_sub("Environment", "env", **props)


def sky_env_pbr(s, full=True):
    """8-bosqich: osmon panoramasi (bulutlar, quyosh nuri) va realistik muhit.
    SDFGI (yorug'likning devorlardan qaytishi), SSR (koshinlarda aks), osmondan tushadigan atrof yorug'ligi.
    Tuman va quyosh 6-bosqich chegaralarida qoladi (test 15)."""
    sky_tex = s.add_ext("Texture2D", "res://textures/sky.png", "s_sky")
    s.add_sub("PanoramaSkyMaterial", "sky_mat", panorama=sky_tex, energy_multiplier="1.0")
    s.add_sub("Sky", "sky", sky_material='SubResource("sky_mat")', radiance_size="2")
    props = dict(background_mode="2", sky='SubResource("sky")', ambient_light_source="3", ambient_light_color="Color(0.8, 0.74, 0.64, 1)",
                 ambient_light_sky_contribution="0.75", ambient_light_energy="0.85", reflected_light_source="2",
                 tonemap_mode="3", tonemap_exposure="0.92", tonemap_white="6.0")
    if full:
        props.update(ssr_enabled="true", ssr_max_steps="48", ssr_fade_in="0.15", ssr_fade_out="2.0", ssr_depth_tolerance="0.2",
                     ssao_enabled="true", ssao_radius="1.4", ssao_intensity="1.8", ssao_detail="0.6",
                     ssil_enabled="true", ssil_intensity="0.8",
                     sdfgi_enabled="true", sdfgi_use_occlusion="true", sdfgi_cascades="4", sdfgi_min_cell_size="0.25",
                     sdfgi_bounce_feedback="0.45", sdfgi_energy="0.9", sdfgi_normal_bias="1.1",
                     glow_enabled="true", glow_intensity="0.5", glow_bloom="0.05", glow_hdr_threshold="1.2",
                     fog_enabled="true", fog_light_color="Color(0.86, 0.78, 0.64, 1)", fog_density="0.0015", fog_sky_affect="0.25",
                     fog_aerial_perspective="0.35",
                     volumetric_fog_enabled="true", volumetric_fog_density="0.004", volumetric_fog_albedo="Color(0.95, 0.88, 0.75, 1)",
                     volumetric_fog_anisotropy="0.5", volumetric_fog_length="80.0",
                     adjustment_enabled="true", adjustment_saturation="1.04", adjustment_contrast="1.06")
    s.add_sub("Environment", "env", **props)


def decals(s):
    """8-bosqich: realistik eskirish izlari (faqat ko'rinish, to'qnashuvga ta'sirsiz, Forward+ renderda):
    devor tagidagi kir, tom qirrasidan tushgan yomg'ir izlari, devordagi yoriqlar, poldagi dog'lar."""
    import random
    rnd = random.Random(8)
    tex = {k: s.add_ext("Texture2D", f"res://textures/{fn}.png", f"d_{k}") for k, fn in
           (("grime", "grime"), ("rain", "rain"), ("crack", "decal_crack"), ("stain", "decal_stain"))}
    s.node("Decals", "Node3D", ".")
    G = L.G

    def cell(x, z):
        c, r = int((x - E0) // L.CELL), int((z - E0) // L.CELL)
        return L.grid[r][c] if 0 <= r < G and 0 <= c < G else None

    def basis(X, Y, Z):
        return ", ".join(f(v) for v in (X[0], Y[0], Z[0], X[1], Y[1], Z[1], X[2], Y[2], Z[2]))

    def cross(a, b):
        return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

    def put(kind, pos, X, Y, Z, size, mod="Color(1, 1, 1, 1)", fade=30.0):
        n = len(s.nodes)
        s.node(f"D{n}_{kind}", "Decal", "Decals", transform=f"Transform3D({basis(X, Y, Z)}, {f(pos[0])}, {f(pos[1])}, {f(pos[2])})",
               size=f"Vector3({f(size[0])}, {f(size[1])}, {f(size[2])})", texture_albedo=tex[kind], modulate=mod,
               normal_fade="0.5", upper_fade="0.2", lower_fade="0.2", cast_shadow="false",
               distance_fade_enabled="true", distance_fade_begin=f(fade), distance_fade_length="10.0")
        cnt[kind] += 1

    cnt = {k: 0 for k in tex}
    UP = (0.0, 1.0, 0.0)
    for (x0, z0, x1, z1, h) in meta["blocks"]:
        for n, a, b, fixed, along_x in (((0, 0, -1), x0, x1, z0, True), ((0, 0, 1), x0, x1, z1, True),
                                        ((-1, 0, 0), z0, z1, x0, False), ((1, 0, 0), z0, z1, x1, False)):
            ln = b - a
            k = max(1, math.ceil(ln / 6.0))
            seg = ln / k
            for i in range(k):
                m = a + seg * (i + 0.5)
                px, pz = (m, fixed) if along_x else (fixed, m)
                out = cell(px + n[0] * 1.0, pz + n[2] * 1.0)
                if out is None or out == "#":
                    continue
                covered = out in L.COVER
                t_g = cross(n, UP)
                put("grime", (px, 0.5, pz), t_g, n, UP, (seg + 0.1, 0.8, 1.15), "Color(1, 1, 1, 0.9)")
                if not covered and h > 3.5:
                    put("rain", (px, h - 1.3, pz), t_g, n, UP, (seg + 0.1, 0.8, 2.6), "Color(1, 1, 1, 0.75)", 40.0)
                if rnd.random() < 0.18:
                    hh = rnd.uniform(1.0, 2.6 if covered else 3.2)
                    sz = rnd.uniform(1.0, 1.8)
                    put("crack", (px + rnd.uniform(-1, 1) * (along_x), hh, pz + rnd.uniform(-1, 1) * (not along_x)), t_g, n, UP,
                        (sz, 0.6, sz), "Color(1, 1, 1, 0.85)", 25.0)
    for r in range(G):
        for c in range(G):
            t = L.grid[r][c]
            if t == "#" or rnd.random() > 0.07:
                continue
            x, z = E0 + (c + 0.5) * L.CELL, E0 + (r + 0.5) * L.CELL
            a = rnd.uniform(0, math.tau)
            X, Z = (math.cos(a), 0.0, -math.sin(a)), (math.sin(a), 0.0, math.cos(a))
            sz = rnd.uniform(1.2, 2.4)
            put("stain", (x + rnd.uniform(-0.4, 0.4), 0.3, z + rnd.uniform(-0.4, 0.4)), X, UP, Z, (sz, 1.2, sz), "Color(1, 1, 1, 0.8)", 30.0)
    return cnt


def perf_nodes(s, root_is_main=True, art=True):
    """7-bosqich: occluder'lar (bino bloklari), masofa bo'yicha bezakni yashirish, minimap va F9 ko'rsatkichlari"""
    if art and not LOWPOLY:
        ms = s.add_ext("Script", "res://scripts/materials.gd", "11_mat")
        s.node("Materials", "Node", ".", script=ms)
        DECAL_COUNT.update(decals(s))
    s.node("Occluders", "Node3D", ".")
    for i, (x0, z0, x1, z1, h) in enumerate(meta["blocks"]):
        oc = s.add_sub("BoxOccluder3D", f"oc{i}", size=f"Vector3({f(x1 - x0 - 0.1)}, {f(h - 0.1)}, {f(z1 - z0 - 0.1)})")
        s.node(f"Occ{i}", "OccluderInstance3D", "Occluders", transform=T((x0 + x1) / 2, h / 2, (z0 + z1) / 2), occluder=oc)
    lod = s.add_ext("Script", "res://scripts/map_lod.gd", "8_lod")
    s.node("MapLOD", "Node", ".", script=lod)
    mm = s.add_ext("Script", "res://scripts/minimap.gd", "9_mm")
    po = s.add_ext("Script", "res://scripts/perf_overlay.gd", "10_po")
    s.node("UI", "CanvasLayer", ".", layer="5")
    s.node("Minimap", "Control", "UI", script=mm)
    s.node("Perf", "Label", "UI", script=po)


def player_scene(art, out):
    """O'yinchi sahnasi. art=True: 1-shaxs qo'llar/qurol (Camera3D/FPView) + 3-shaxs tana (Body).
    O'z kamerasi — 1-shaxs; boshqa kameralar — 3-shaxs tana (render qatlamlari, player.gd)."""
    s = Scene()
    pscr = s.add_ext("Script", "res://scripts/player.gd", "1_pl")
    s.add_sub("CapsuleShape3D", "capsule", radius="0.35", height="1.8")
    s.node("Player", "CharacterBody3D", None, collision_layer="8", collision_mask="3", script=pscr)
    s.node("CollisionShape3D", "CollisionShape3D", ".", transform=T(0, 0.9, 0), shape='SubResource("capsule")')
    s.node("Camera3D", "Camera3D", ".", transform=T(0, 1.65, 0), fov="80.0", far="400.0")
    s.node("FloorRay", "RayCast3D", ".", transform=T(0, 0.2, 0), target_position="Vector3(0, -0.6, 0)", collision_mask="1")
    s.node("Steps", "AudioStreamPlayer3D", ".", transform=T(0, 0.1, 0), volume_db="-8.0", unit_size="4.0")
    if art:
        fpv = s.add_ext("Script", "res://scripts/fp_view.gd", "2_fp")
        s.node("FPView", "Node3D", "Camera3D", script=fpv)
        cmod = s.add_ext("Script", "res://scripts/character_model.gd", "3_cm")
        s.node("Body", "Node3D", ".", transform=T(0, 0, 0, yaw_pi=True), script=cmod, team='"T"', own_body="true")
    s.save(f"{OUT}/scenes/{out}")


player_scene(True, "player.tscn")
player_scene(False, "player_greybox.tscn")


def main_scene(glb_path, out_name):
  s = Scene()
  glb = s.add_ext("PackedScene", glb_path, "1_map")
  col = s.add_ext("PackedScene", "res://map/collision.tscn", "2_col")
  gscr = s.add_ext("Script", "res://scripts/game_mode.gd", "4_gm")
  hscr = s.add_ext("Script", "res://scripts/hud.gd", "5_hud")
  if NAVMESH:
      nm = s.add_ext("NavigationMesh", "res://map/navmesh.res", "6_nav")
  else:
      nm = s.add_sub("NavigationMesh", "navmesh", geometry_parsed_geometry_type="1", geometry_collision_mask="1",
                     cell_size="0.25", cell_height="0.25", agent_height="2.0", agent_radius="0.5",
                     agent_max_climb="0.25", agent_max_slope="45.0",
                     filter_baking_aabb=f"AABB({f(E0)}, -1, {f(E0)}, {f(SIZE)}, 4, {f(SIZE)})")
  sky_env(s)
  s.add_sub("PlaneMesh", "ground", size="Vector2(600, 600)")
  s.add_sub("StandardMaterial3D", "ground_mat", albedo_color="Color(0.62, 0.5, 0.35, 1)", roughness="1.0")
  for k, c in (("site", "Color(0.85, 0.25, 0.18, 0.22)"), ("buy", "Color(0.23, 0.64, 0.35, 0.2)"), ("T", "Color(0.84, 0.38, 0.12, 0.9)"),
               ("CT", "Color(0.16, 0.36, 0.67, 0.9)"), ("ai", "Color(1, 1, 1, 0.9)"), ("smoke", "Color(0.85, 0.85, 0.85, 0.35)")):
      s.add_sub("StandardMaterial3D", f"vm_{k}", transparency="1", shading_mode="0", cull_mode="2", no_depth_test="true", albedo_color=c)
  s.add_sub("CylinderMesh", "spawn_disc", top_radius="0.35", bottom_radius="0.35", height="0.06")
  s.add_sub("CylinderMesh", "ai_pole", top_radius="0.06", bottom_radius="0.06", height="1.6", material='SubResource("vm_ai")')
  s.add_sub("SphereMesh", "smoke_sph", radius=f(L.SMOKE_R), height=f(2 * L.SMOKE_R), material='SubResource("vm_smoke")')

  s.node("Main", "Node3D")
  s.node("WorldEnvironment", "WorldEnvironment", ".", environment='SubResource("env")')
  s.node("Sun", "DirectionalLight3D", ".", transform=T(0, 40, 0), rotation_degrees=SUN_ROT, light_color="Color(1, 0.9, 0.74, 1)",
         light_energy="0.95", shadow_enabled="true", shadow_blur="1.5", directional_shadow_max_distance="80.0", directional_shadow_mode="1")
  s.node("Map", parent=".", instance=glb)
  s.node("Navigation", "NavigationRegion3D", ".", navigation_mesh=nm)
  s.node("Collision", parent="Navigation", instance=col)
  s.node("OuterGround", "MeshInstance3D", ".", transform=T(0, -0.32, 0), mesh='SubResource("ground")',
         **{"surface_material_override/0": 'SubResource("ground_mat")'})
  s.node("Lamps", "Node3D", ".")
  for i, p in enumerate(meta["lamps"]):
      s.node(f"Lamp{i}", "OmniLight3D", "Lamps", groups=["lamps"], transform=T(*p), light_color="Color(1, 0.68, 0.36, 1)",
             light_energy="1.4", omni_range="7.0", omni_attenuation="1.6",
             distance_fade_enabled="true", distance_fade_begin="45.0", distance_fade_length="10.0")
  # 6-bosqich: chiroqdan uzoq yopiq kataklarga ko'rinmas yumshoq to'ldiruvchi yorug'lik (qorong'i burchak qolmasin)
  for i, p in enumerate(FILL_LIGHTS):
      s.node(f"Fill{i}", "OmniLight3D", "Lamps", groups=["lamps"], transform=T(*p), light_color="Color(1, 0.86, 0.66, 1)",
             light_energy="0.55", omni_range="7.5", omni_attenuation="1.2", light_specular="0.1",
             distance_fade_enabled="true", distance_fade_begin="40.0", distance_fade_length="10.0")
  # fon tovushlari (hudud markazlarida) va yopiq joylarda aks-sado
  amb = {n: s.add_ext("AudioStream", f"res://audio/amb_{n}.wav", f"a_{n}") for n in AMB_FILES}
  s.node("Ambient", "Node3D", ".")
  for i, (name, pos, vol) in enumerate(AMB_SOURCES):
      s.node(f"Amb{i}_{name}", "AudioStreamPlayer3D", "Ambient", groups=["ambient"], transform=T(*pos), stream=amb[name],
             volume_db=f(vol), unit_size="12.0", max_distance="45.0", bus='&"Ambient"', **{"metadata/district": f'"{name}"'})
  s.node("Reverb", "Node3D", ".")
  for i, (x0, z0, x1, z1, h) in enumerate(REVERB_RECTS):
      sh = s.add_sub("BoxShape3D", f"rv{i}", size=f"Vector3({f(x1 - x0)}, {f(h)}, {f(z1 - z0)})")
      s.node(f"Rev{i}", "Area3D", "Reverb", groups=["reverb"], transform=T((x0 + x1) / 2, h / 2, (z0 + z1) / 2),
             collision_layer="64", collision_mask="0", monitoring="false", reverb_bus_enabled="true", reverb_bus_name='&"Reverb"',
             reverb_bus_amount="0.7", reverb_bus_uniformity="0.3")
      s.node("Shape", "CollisionShape3D", f"Reverb/Rev{i}", shape=sh)
  ascr = s.add_ext("Script", "res://scripts/atmosphere.gd", "7_atm")
  s.node("Atmosphere", "Node3D", ".", script=ascr)
  perf_nodes(s, art="greybox" not in glb_path)
  s.node("Zones", "Node3D", ".")
  for kind, data, grp, h, vm in (("BombSite", L.BOMB_ZONES, "bomb_sites", 3.5, "vm_site"), ("BuyZone", L.BUY_ZONES, "buy_zones", 5.0, "vm_buy")):
      for k, (x0, z0, x1, z1) in data.items():
          nme = f"{kind}{k}"
          sh = s.add_sub("BoxShape3D", f"z_{nme}", size=f"Vector3({f(x1 - x0)}, {h}, {f(z1 - z0)})")
          ms = s.add_sub("BoxMesh", f"zm_{nme}", size=f"Vector3({f(x1 - x0)}, {h}, {f(z1 - z0)})", material=f'SubResource("{vm}")')
          mkey = "metadata/site" if kind == "BombSite" else "metadata/team"
          s.node(nme, "Area3D", "Zones", groups=[grp], transform=T((x0 + x1) / 2, h / 2, (z0 + z1) / 2),
                 collision_layer="64", collision_mask="8", monitorable="false", **{mkey: f'"{k}"'})
          s.node("Shape", "CollisionShape3D", f"Zones/{nme}", shape=sh)
          s.node("Viz", "MeshInstance3D", f"Zones/{nme}", groups=["debug_viz"], visible="false", mesh=ms)
  s.node("Spawns", "Node3D", ".")
  for team, pts in L.SPAWNS.items():
      for i, (x0, z0) in enumerate(pts):
          nme = f"{team}{i + 1}"
          s.node(nme, "Marker3D", "Spawns", groups=[f"spawn_{team}"], transform=T(x0, 0.05, z0, yaw_pi=(team == "T")))
          s.node("Viz", "MeshInstance3D", f"Spawns/{nme}", groups=["debug_viz"], visible="false", mesh='SubResource("spawn_disc")',
                 **{"surface_material_override/0": f'SubResource("vm_{team}")'})
  s.node("AIPoints", "Node3D", ".")
  for i, (label, kind, team, x0, z0) in enumerate(L.AI_POINTS):
      nme = f"P{i:02d}"
      s.node(nme, "Marker3D", "AIPoints", groups=["ai_points"], transform=T(x0, plat_h(x0, z0), z0),
             **{"metadata/label": json.dumps(label, ensure_ascii=False), "metadata/kind": f'"{kind}"', "metadata/team": f'"{team}"'})
      s.node("Pole", "MeshInstance3D", f"AIPoints/{nme}", groups=["debug_viz"], visible="false", transform=T(0, 0.8, 0), mesh='SubResource("ai_pole")')
      s.node("Label", "Label3D", f"AIPoints/{nme}", groups=["debug_viz"], visible="false", transform=T(0, 1.9, 0), billboard="1",
             no_depth_test="true", font_size="40", outline_size="10", text=json.dumps(f"{label} ({kind}, {team})", ensure_ascii=False))
  s.node("Smokes", "Node3D", ".")   # F1 da ko'rinadi: smoke rejasidagi nishonlar
  for i, (name, team, tgt, throw, _lines) in enumerate(L.SMOKES):
      nme = f"Smoke{i:02d}"
      s.node(nme, "Marker3D", "Smokes", groups=["smoke_targets"], transform=T(tgt[0], 1.0, tgt[1]),
             **{"metadata/label": json.dumps(name, ensure_ascii=False), "metadata/team": f'"{team}"'})
      s.node("Viz", "MeshInstance3D", f"Smokes/{nme}", groups=["debug_viz"], visible="false", mesh='SubResource("smoke_sph")')
      s.node("Label", "Label3D", f"Smokes/{nme}", groups=["debug_viz"], visible="false", transform=T(0, 3.2, 0), billboard="1",
             no_depth_test="true", font_size="48", outline_size="10", text=json.dumps(f"smoke: {name} ({team})", ensure_ascii=False))
  tx, tz = L.SPAWNS["T"][0]
  # o'yinchi — alohida sahna (scenes/player.tscn): tarmoqdagi boshqa o'yinchilar ham shu sahnadan (local_player=false)
  pl_scene = s.add_ext("PackedScene", "res://scenes/player_greybox.tscn" if "greybox" in glb_path else "res://scenes/player.tscn", "3_pl")
  s.node("Player", parent=".", instance=pl_scene, transform=T(tx, 0.2, tz, yaw_pi=True))
  s.node("GameMode", "Node", ".", script=gscr)
  s.node("HUD", "CanvasLayer", ".", script=hscr)
  if "greybox" not in glb_path:
      # F7 — mashq nishonlari (qurol va tana zonalarini sinash uchun)
      prs = s.add_ext("Script", "res://scripts/practice.gd", "12_pr")
      s.node("Practice", "Node3D", ".", script=prs)
      # botlar bilan o'yin: o'yinchi + 4 jamoadosh va 5 raqib (scripts/bot_play.gd)
      bps = s.add_ext("Script", "res://scripts/bot_play.gd", "13_bp")
      s.node("Bots", "Node3D", ".", script=bps)
  s.save(f"{OUT}/{out_name}")



main_scene("res://map/qumtepa5v5.glb" if ART else "res://map/qumtepa5v5_greybox.glb", "main.tscn")
main_scene("res://map/qumtepa5v5_greybox.glb", "main_greybox.tscn")
open(f"{OUT}/menu.tscn", "w").write('''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/menu.gd" id="1_menu"]

[node name="Menu" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
script = ExtResource("1_menu")
''')
open(f"{OUT}/inventory.tscn", "w").write('''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/inventory.gd" id="1_inv"]

[node name="Inventory" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
script = ExtResource("1_inv")
''')
# ------------------------------------------------------------------ tests/test_data.gd — testlar uchun xarita ma'lumotlari
def gd_route(wps):
    return "[" + ", ".join(V3(p) for p in wps) + "]"


plats = [(x0, z0, x1, z1, h, d) for (k, x0, z0, x1, z1, h, d) in [p for p in L.PROPS if p[0] == "platform"]]
def plat_top(p):
    x0, z0, x1, z1, h, d = p
    return V3(((x0 + x1) / 2, h, (z0 + z1) / 2))


def plat_foot(p):
    x0, z0, x1, z1, h, d = p
    return V3(((x1 + 2.5) if d == "+x" else (x0 - 2.5), 0.0, (z0 + z1) / 2))


samples = [(0.0, -46.0), (-44.0, -5.0), (0.0, -24.0), (-22.0, -10.0), (22.0, -10.0), (34.0, -24.0), (0.0, 7.0),
           L.A_PLANT, L.B_PLANT, (8.0, 15.0), (-31.0, -12.0), (0.0, 42.0), (-28.0, 38.0), (14.0, 15.0)]
def cname(p):
    c, r = int((p[0] - L.ORIGIN) // L.CELL), int((p[1] - L.ORIGIN) // L.CELL)
    return an["callout_names"][an["callout_grid"][r][c]]


walls = [p for p in L.PROPS if p[0] == "wall"]
quduq = next(p for p in walls if (p[1], p[2]) == (-33.5, 23.0))   # A quduq
routes = [(n, t, wps, an["routes"][n]["time"]) for n, t, wps in L.ROUTES]
td = f'''extends RefCounted
## AVTOMATIK YARATILGAN (tools/gen_godot5.py). Testlar uchun xarita ma'lumotlari, layout5.py va 2D tahlildan.

const T_SPAWN := {V3(L.T_SPAWN)}
const CT_SPAWN := {V3(L.CT_SPAWN)}
const A_PLANT := {V3(L.A_PLANT)}
const B_PLANT := {V3(L.B_PLANT)}
const MAP_MIN := {f(E0)}
const MAP_MAX := {f(E0 + SIZE)}
## 2D tahlildagi eng qisqa vaqtlar (s) — 3D fizika bilan solishtiriladi
const SHORTEST_2D := {json.dumps(an["shortest"], ensure_ascii=False)}
## [nom, jamoa, yo'l nuqtalari, 2D vaqt]
const ROUTES := [
{chr(10).join(f'	[{json.dumps(n, ensure_ascii=False)}, "{t}", {gd_route(w)}, {e}],' for n, t, w, e in routes)}
]
## [pastdagi nuqta, platforma usti]
const PLATFORMS := [{", ".join(f"[{plat_foot(p)}, {plat_top(p)}]" for p in plats)}]
## [nuqta, kutilgan callout]
const CALLOUTS := [{", ".join(f'[{V3(p)}, {json.dumps(cname(p), ensure_ascii=False)}]' for p in samples)}]
## [ray boshi (tepada), sirt, izoh]
const SURFACES := [
	[Vector3(10, 3, -24), "stone", "Top mid poli"],
	[Vector3(-20.5, 5, 23), "wood", "A CT qutilari"],
	[Vector3(12.5, 3, -49), "metal", "T spawn yashil qutisi"],
	[Vector3(-40.5, 3, 12), "cloth", "A site qum qoplari"],
]
## xaroba/quduq ustida player clip bor: [x, z]; nazorat nuqtasi — ochiq joy
const WALL_TOP := Vector3({f((quduq[1] + quduq[3]) / 2)}, {f(quduq[5])}, {f((quduq[2] + quduq[4]) / 2)})
const OPEN_CONTROL := Vector3(-40.0, 0.0, 22.0)
## Mid doors: eshik o'rtasidan ko'rinadi, devor orqasidan ko'rinmaydi
const MID_DOORS_OPEN := [Vector3(0, 1.6, -16), Vector3(0, 1.6, 9)]
const MID_DOORS_WALL := [Vector3(-3.5, 1.6, -16), Vector3(-3.5, 1.6, 9)]
## yopiq yo'lak (T spawn tomi 5.0 m)
const COVERED_POINT := Vector3(0, 0, -46)
const COVERED_H := {L.COVER["T"]}
## hudud to'ri (2 m kataklar): 1 — T hududi, -1 — CT hududi, 0 — talashuvli, 9 — bino
const SIDE_GRID := {json.dumps(an["side_grid"])}
## yopiq kataklar markazlari (aks-sado va yorug'lik qamrovi testlari uchun)
const COVERED_CELLS := [{", ".join(V3(L.m(c, r), 1.0) for r, c in COVERED)}]
## smoke rejasi: [nom, jamoa, nishon, otish joyi]
const SMOKES := [
{chr(10).join(f'	[{json.dumps(n, ensure_ascii=False)}, "{t}", {V3(tg)}, {V3(th)}],' for n, t, tg, th, _l in L.SMOKES)}
]
'''
open(f"{OUT}/tests/test_data.gd", "w").write(td)

# ------------------------------------------------------------------ scripts/strategies.gd — bot o'yinlari uchun
lineups = {}
lp = os.path.join(HERE, "..", "docs", "smokes_stage3.json")
if os.path.exists(lp):
    lineups = {r["name"]: r["lineup"] for r in json.load(open(lp))}
REGION = {"A site": "A", "A platforma": "A", "A default": "A", "A short chiqishi": "A", "A long chiqishi": "A", "A ramp": "A",
          "A CT": "A", "Long": "A", "Long pit": "A", "Catwalk": "A",
          "B site": "B", "B platforma": "B", "B default": "B", "B window chiqishi": "B", "B tunnel chiqishi": "B", "B ramp": "B",
          "B doors": "B", "Lower tunnels": "B", "Tunnel cho'ntagi": "B", "B window": "B",
          "Mid doors": "M", "CT mid": "M", "Mid": "M", "Mid-window": "M"}
unknown = set(REGION) - set(an["callout_names"])
assert not unknown, unknown


def gdarr(pts):
    return "[" + ", ".join(V3(p) for p in pts) + "]"


def gdstr(x):
    return json.dumps(x, ensure_ascii=False)


st = f'''extends RefCounted
## AVTOMATIK YARATILGAN (tools/gen_godot5.py, layout5.py dagi 3-bosqich taktikalaridan). Qo'lda o'zgartirmang.

const PLANT := {{"A": {V3(L.A_PLANT)}, "B": {V3(L.B_PLANT)}}}
const SMOKE_R := {L.SMOKE_R}
const SMOKE_TIME := 15.0
## callout -> hudud (CT lar qaysi site'da T ko'rganini bilishi uchun)
const REGION := {gdstr(REGION)}
const T_ROUTES := {{
{chr(10).join(f"	{gdstr(k)}: {gdarr(v)}," for k, v in L.T_ROUTES.items())}
}}
const T_ENTRY := {{
{chr(10).join(f"	{gdstr(k)}: {gdarr(v)}," for k, v in L.T_ENTRY.items())}
}}
const T_POSTPLANT := {{
{chr(10).join(f"	{gdstr(k)}: [" + ", ".join(f"[{V3(p)}, {V3(l)}]" for p, l in v) + "]," for k, v in L.T_POSTPLANT.items())}
}}
## [nom, site, [[yo'l, kirish, odam, bomba], ...], [smoke'lar], [hujum vaqti dan, gacha]]
const T_STRATS := [
{chr(10).join(f"	[{gdstr(n)}, {gdstr(site)}, [" + ", ".join(f"[{gdstr(g[0])}, {gdstr(g[1])}, {g[2]}, {str(g[3]).lower()}]" for g in groups) + f"], {gdstr(sm)}, [{tw[0]}, {tw[1]}]]," for n, site, groups, sm, tw in L.T_STRATS)}
]
## nom -> [joy, qaraydigan nuqta, hudud]
const CT_SPOTS := {{
{chr(10).join(f"	{gdstr(k)}: [{V3(p)}, {V3(l)}, {gdstr(r)}]," for k, (p, l, r) in L.CT_SPOTS.items())}
}}
const CT_SETUPS := [
{chr(10).join(f"	[{gdstr(n)}, {gdstr(v)}]," for n, v in L.CT_SETUPS)}
]
## aylanib kelgan CT lar turadigan joylar
const ROTATE_SPOT := {{
{chr(10).join(f"	{gdstr(site)}: [" + ", ".join(f"[{V3(p)}, {V3(l)}]" for k, (p, l, r) in L.CT_SPOTS.items() if r == site) + "]," for site in ("A", "B"))}
}}
## smoke: nom -> [jamoa, nishon, uchish vaqti (s, fizika bilan topilgan lineup'dan)]
const SMOKES := {{
{chr(10).join(f"	{gdstr(n)}: [{gdstr(tm)}, {V3(tg)}, {lineups.get(n, {}).get('flight_s', 2.0)}]," for n, tm, tg, _th, _l in L.SMOKES)}
}}
'''
open(f"{OUT}/scripts/strategies.gd", "w").write(st)

# ------------------------------------------------------------------ bots.tscn — 5v5 bot o'yini (kuzatish va balans sinovi)
s = Scene()
glb = s.add_ext("PackedScene", "res://map/qumtepa5v5.glb" if ART else "res://map/qumtepa5v5_greybox.glb", "1_map")
col = s.add_ext("PackedScene", "res://map/collision.tscn", "2_col")
mscr = s.add_ext("Script", "res://scripts/bot_match.gd", "3_bm")
cscr = s.add_ext("Script", "res://scripts/spectator.gd", "4_sp")
nm = s.add_ext("NavigationMesh", "res://map/navmesh.res", "6_nav") if NAVMESH else s.add_sub("NavigationMesh", "navmesh")
sky_env(s, full=False)
s.node("Bots", "Node3D")
s.node("WorldEnvironment", "WorldEnvironment", ".", environment='SubResource("env")')
s.node("Sun", "DirectionalLight3D", ".", transform=T(0, 40, 0), rotation_degrees=SUN_ROT, light_color="Color(1, 0.9, 0.74, 1)",
       light_energy="0.95", shadow_enabled="true", directional_shadow_max_distance="80.0", directional_shadow_mode="1")
s.node("Map", parent=".", instance=glb)
s.node("Navigation", "NavigationRegion3D", ".", navigation_mesh=nm)
s.node("Collision", parent="Navigation", instance=col)
s.node("Spawns", "Node3D", ".")
for team, pts in L.SPAWNS.items():
    for i, (x0, z0) in enumerate(pts):
        s.node(f"{team}{i + 1}", "Marker3D", "Spawns", groups=[f"spawn_{team}"], transform=T(x0, 0.05, z0, yaw_pi=(team == "T")))
s.node("BotMatch", "Node3D", ".", script=mscr)
perf_nodes(s, art=ART)
s.node("Spectator", "Camera3D", ".", script=cscr, current="true")
s.save(f"{OUT}/bots.tscn")

# ------------------------------------------------------------------ scripts/atmo_data.gd, default_bus_layout.tres
open(f"{OUT}/scripts/atmo_data.gd", "w").write('''extends RefCounted
## AVTOMATIK YARATILGAN (tools/gen_godot5.py). Havodagi chang zonalari: [markaz, o'lcham, zarralar soni]
const DUST := [
''' + "\n".join(f"\t[{V3(c)}, {V3(sz)}, {n}]," for c, sz, n in DUST) + "\n]\n")
open(f"{OUT}/default_bus_layout.tres", "w").write('''[gd_resource type="AudioBusLayout" load_steps=2 format=3]

[sub_resource type="AudioEffectReverb" id="rev"]
room_size = 0.55
damping = 0.6
spread = 0.8
hipass = 0.15
dry = 1.0
wet = 0.22

[resource]
bus/1/name = &"Reverb"
bus/1/solo = false
bus/1/mute = false
bus/1/bypass_fx = false
bus/1/volume_db = 0.0
bus/1/send = &"Master"
bus/1/effect/0/effect = SubResource("rev")
bus/1/effect/0/enabled = true
bus/2/name = &"Ambient"
bus/2/solo = false
bus/2/mute = false
bus/2/bypass_fx = false
bus/2/volume_db = -4.0
bus/2/send = &"Master"
''')

# ------------------------------------------------------------------ 8-bosqich: HQ teksturalarni import sozlamalari
# Skript orqali yuklanadigan teksturalarni Godot "3D uchun" deb avtomatik aniqlamaydi, shuning uchun .import ni o'zimiz yozamiz:
# VRAM siqish (videoxotira ~4× kam), mipmap'lar; normal xaritalar uchun maxsus siqish.
TEXDIR = f"{OUT}/textures"
if os.path.isdir(TEXDIR):
    for fn in sorted(os.listdir(TEXDIR)):
        if not fn.endswith((".jpg", ".png")) or os.path.exists(f"{TEXDIR}/{fn}.import"):
            continue
        ui = fn in ("sky.png",) or fn.startswith(("grime", "rain", "decal_"))
        nrm = fn.endswith("_normal.jpg")
        open(f"{TEXDIR}/{fn}.import", "w").write(f'''[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="res://textures/{fn}"

[params]

compress/mode={0 if fn == "sky.png" else 2}
compress/high_quality=false
compress/lossy_quality=0.7
compress/hdr_compression=1
compress/normal_map={1 if nrm else 2}
compress/channel_pack=0
mipmaps/generate={"false" if fn == "sky.png" else "true"}
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/fix_alpha_border=true
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to={0 if ui else 1}
''')

# ------------------------------------------------------------------ project.godot, bake_nav.gd
open(f"{OUT}/project.godot", "w").write('''; Engine configuration file.
config_version=5

[application]

config/name="Qumtepa 5v5 - greybox (2-bosqich)"
run/main_scene="res://menu.tscn"
config/features=PackedStringArray("4.3", "Forward Plus")

[display]

window/size/viewport_width=1600
window/size/viewport_height=900

[layer_names]

3d_physics/layer_1="world"
3d_physics/layer_2="player_clip"
3d_physics/layer_3="grenade_clip"
3d_physics/layer_4="players"
3d_physics/layer_5="hitboxes"
3d_physics/layer_6="grenades"
3d_physics/layer_7="triggers"
3d_physics/layer_8="smoke"
3d_render/layer_1="dunyo"
3d_render/layer_11="o'yinchining o'z tanasi (3-shaxs)"
3d_render/layer_12="1-shaxs qo'llar va qurol"

[audio]

buses/default_bus_layout="res://default_bus_layout.tres"

[rendering]

occlusion_culling/use_occlusion_culling=true
anti_aliasing/quality/msaa_3d=2
anti_aliasing/quality/screen_space_aa=1
anti_aliasing/quality/use_debanding=true
lights_and_shadows/directional_shadow/size=8192
lights_and_shadows/directional_shadow/soft_shadow_filter_quality=3
lights_and_shadows/positional_shadow/soft_shadow_filter_quality=3
textures/default_filters/anisotropic_filtering_level=4
limits/cluster_builder/max_clustered_elements=4096
environment/ssao/quality=2
environment/ssil/quality=1
global_illumination/sdfgi/probe_ray_count=1
''')
open(f"{OUT}/tools/bake_nav.gd", "w").write('''extends SceneTree
## NavMesh'ni oldindan pishirish: godot --headless -s res://tools/bake_nav.gd
## Pishirgandan keyin tozalash: to'siqlar (qutilar, devorchalar) ICHIDAGI va bino tomlaridagi poligonlar olib tashlanadi.
## Sabab: NavMesh generatori qutini faqat yuzalar sifatida ko'radi va yopiq qutining ichidagi polni ham
## "yuriladigan" deb hisoblaydi. Bunday orolchalarga bot yoki o'yinchining maqsadi tushib qolmasligi kerak.


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var main: Node = load("res://main.tscn").instantiate()
	root.add_child(main)
	await physics_frame
	await physics_frame
	var region: NavigationRegion3D = main.get_node("Navigation")
	region.bake_navigation_mesh(false)
	var nm := region.navigation_mesh
	var space := (main.get_node("Player") as Node3D).get_world_3d().direct_space_state
	var verts := nm.get_vertices()
	var clean := NavigationMesh.new()
	for prop in ["cell_size", "cell_height", "agent_height", "agent_radius", "agent_max_climb", "agent_max_slope"]:
		clean.set(prop, nm.get(prop))
	clean.set_vertices(verts)
	var removed_inside := 0
	var removed_roof := 0
	var q := PhysicsPointQueryParameters3D.new()
	q.collision_mask = 1
	var keep := []
	for i in nm.get_polygon_count():
		var poly := nm.get_polygon(i)
		var c := Vector3.ZERO
		for k in poly:
			c += verts[k]
		c /= poly.size()
		if c.y > 2.0:
			removed_roof += 1
			continue
		q.position = c + Vector3.UP * 0.6
		if not space.intersect_point(q, 1).is_empty():
			removed_inside += 1
			continue
		keep.append(poly)
	# asosiy maydonga ulanmagan orolchalar (qutilar va devor orasidagi yopiq bo'shliqlar) ham olib tashlanadi:
	# poligonlar umumiy uchlar orqali bog'lanadi, T spawn joylashgan qism qoladi
	var parent := {}
	var find := func(x):
		while parent.get(x, x) != x:
			x = parent[x]
		return x
	for poly in keep:
		var r0 = find.call(poly[0])
		for k in poly:
			var rk = find.call(k)
			if rk != r0:
				parent[rk] = r0
	var t_spawn := Vector3(0, 0, -47)
	var best := -1
	var bd := INF
	for poly in keep:
		for k in poly:
			var d := verts[k].distance_to(t_spawn)
			if d < bd:
				bd = d
				best = k
	var main_root = find.call(best)
	var removed_island := 0
	for poly in keep:
		if find.call(poly[0]) == main_root:
			clean.add_polygon(poly)
		else:
			removed_island += 1
	print("navmesh poligonlar: ", clean.get_polygon_count(), " (olib tashlandi: to'siq ichida ", removed_inside, ", tomlarda ", removed_roof, ", yakka orolchalar ", removed_island, ")")
	ResourceSaver.save(clean, "res://map/navmesh.res")
	quit()
''')
print("yaratildi:", OUT, counts, "navmesh:", NAVMESH)
