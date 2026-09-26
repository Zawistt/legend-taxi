"""Generates the Godot 4.3 project for Qumtepa (stage 2) from layout.py + meta.json."""
import json, math, os, shutil, sys
import numpy as np
from scipy.io import wavfile
import layout as L

OUT = "godot2/qumtepa"
SRC = "godot_src"
meta = json.load(open("meta.json"))
st2 = json.load(open("analysis_stage2.json"))
NAVMESH = os.path.exists(f"{OUT}/map/navmesh.res")


def f(v):
    return f"{v:.4g}"


def T(x, y, z, yaw_pi=False):
    b = "-1, 0, 0, 0, 1, 0, 0, 0, -1" if yaw_pi else "1, 0, 0, 0, 1, 0, 0, 0, 1"
    return f"Transform3D({b}, {f(x)}, {f(y)}, {f(z)})"


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
    """Greedy merge of axis-aligned boxes sharing faces (x then z)."""
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


# ---------------------------------------------------------------- folders + scripts
if os.path.exists(OUT) and not NAVMESH:
    shutil.rmtree(OUT)
for d in ("map", "scripts", "scenes", "audio", "tests", "docs", "tools"):
    os.makedirs(f"{OUT}/{d}", exist_ok=True)
for sub in ("scripts", "tests"):
    for fn in os.listdir(f"{SRC}/{sub}"):
        shutil.copy(f"{SRC}/{sub}/{fn}", f"{OUT}/{sub}/{fn}")
shutil.copy("desert_map.glb", f"{OUT}/map/desert_map.glb")

# ---------------------------------------------------------------- map_data.gd
names = [""] + list(L.CALLOUTS)
def callout_of(c, r):
    if L.GRID[r][c] == "#":
        return 0
    best = None
    for i, (n, (c0, c1, r0, r1)) in enumerate(L.CALLOUTS.items()):
        if c0 <= c <= c1 and r0 <= r <= r1:
            a = (c1 - c0 + 1) * (r1 - r0 + 1)
            if best is None or a < best[0]:
                best = (a, i + 1)
    return best[1] if best else 0
cgrid = [[callout_of(c, r) for c in range(25)] for r in range(25)]
R = L.ROUND
md = f'''extends RefCounted
## AVTOMATIK YARATILGAN (tools/gen_godot.py, layout.py asosida). Qo'lda o'zgartirmang.

const CELL := 2.0
const ORIGIN := -25.0
const CALLOUT_NAMES := {json.dumps(names, ensure_ascii=False)}
const CALLOUT_GRID := {json.dumps(cgrid)}
## Raund qoidalari (soniya). 50 m xarita uchun: site'larga 5–9 s da yetiladi.
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

# ---------------------------------------------------------------- audio (procedural, placeholder)
SR = 22050
rng = np.random.default_rng(3)
def env(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))
def smooth(x, k):
    return np.convolve(x, np.ones(k) / k, mode="same")
def save(name, x):
    x = x / (np.abs(x).max() + 1e-9) * 0.8
    wavfile.write(f"{OUT}/audio/{name}.wav", SR, (x * 32767).astype(np.int16))
n = int(0.16 * SR); t = np.arange(n) / SR
save("step_stone", np.diff(rng.normal(0, 1, n + 1)) * env(n, 0.018) + 0.6 * np.sin(2 * np.pi * 95 * t) * env(n, 0.03))
save("step_wood", (np.sin(2 * np.pi * 190 * t) + 0.6 * np.sin(2 * np.pi * 430 * t)) * env(n, 0.035) + 0.3 * rng.normal(0, 1, n) * env(n, 0.01))
n2 = int(0.35 * SR); t2 = np.arange(n2) / SR
save("step_metal", sum(a * np.sin(2 * np.pi * fr * t2) for a, fr in ((1, 870), (0.7, 1640), (0.5, 2410))) * env(n2, 0.07) + 0.4 * rng.normal(0, 1, n2) * env(n2, 0.006))
save("step_cloth", smooth(rng.normal(0, 1, n), 14) * env(n, 0.04))
nb = int(0.09 * SR); tb = np.arange(nb) / SR
save("bomb_beep", np.sin(2 * np.pi * 2100 * tb) * np.minimum(1, (nb - np.arange(nb)) / 300))
ne = int(2.2 * SR); te = np.arange(ne) / SR
save("bomb_explode", smooth(rng.normal(0, 1, ne), 40) * env(ne, 0.5) * 3 + np.sin(2 * np.pi * (60 - 20 * te) * te) * env(ne, 0.7))

# ---------------------------------------------------------------- bomb.tscn
s = Scene()
scr = s.add_ext("Script", "res://scripts/bomb.gd", "1_s")
beep = s.add_ext("AudioStream", "res://audio/bomb_beep.wav", "2_b")
boom = s.add_ext("AudioStream", "res://audio/bomb_explode.wav", "3_x")
s.add_sub("StandardMaterial3D", "m_body", albedo_color="Color(0.16, 0.15, 0.13, 1)", roughness="0.6", metallic="0.4")
s.add_sub("BoxMesh", "box_body", size="Vector3(0.34, 0.12, 0.24)", material='SubResource("m_body")')
s.add_sub("StandardMaterial3D", "m_led", albedo_color="Color(1, 0.1, 0.05, 1)", emission_enabled="true", emission="Color(1, 0.1, 0.05, 1)", emission_energy_multiplier="3.0")
s.add_sub("BoxMesh", "box_led", size="Vector3(0.05, 0.02, 0.05)", material='SubResource("m_led")')
s.add_sub("StandardMaterial3D", "m_blast", transparency="1", shading_mode="0", albedo_color="Color(1, 0.6, 0.2, 0.85)", cull_mode="2")
s.add_sub("SphereMesh", "sph", radius="0.5", height="1.0", material='SubResource("m_blast")')
s.node("Bomb", "Node3D", script=scr)
s.node("Body", "Node3D", ".")
s.node("Case", "MeshInstance3D", "Body", transform=T(0, 0.06, 0), mesh='SubResource("box_body")')
s.node("LedMesh", "MeshInstance3D", "Body", transform=T(0.1, 0.13, 0.06), mesh='SubResource("box_led")')
s.node("Led", "OmniLight3D", ".", transform=T(0.1, 0.25, 0.06), light_color="Color(1, 0.12, 0.05, 1)", light_energy="0.0", omni_range="3.0")
s.node("Beep", "AudioStreamPlayer3D", ".", stream=beep, unit_size="6.0")
s.node("Boom", "AudioStreamPlayer3D", ".", stream=boom, unit_size="40.0", max_db="6.0")
s.node("Blast", "MeshInstance3D", ".", visible="false", transform=T(0, 0.5, 0), mesh='SubResource("sph")')
s.save(f"{OUT}/scenes/bomb.tscn")

# ---------------------------------------------------------------- collision.tscn
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
        for i, (sf, pts) in enumerate(meta["ramps"]):
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

# ---------------------------------------------------------------- main.tscn
s = Scene()
glb = s.add_ext("PackedScene", "res://map/desert_map.glb", "1_map")
col = s.add_ext("PackedScene", "res://map/collision.tscn", "2_col")
pscr = s.add_ext("Script", "res://scripts/player.gd", "3_pl")
gscr = s.add_ext("Script", "res://scripts/game_mode.gd", "4_gm")
hscr = s.add_ext("Script", "res://scripts/hud.gd", "5_hud")
if NAVMESH:
    nm = s.add_ext("NavigationMesh", "res://map/navmesh.res", "6_nav")
else:
    nm = s.add_sub("NavigationMesh", "navmesh", geometry_parsed_geometry_type="1", geometry_collision_mask="1",
                   cell_size="0.25", cell_height="0.25", agent_height="2.0", agent_radius="0.5",
                   agent_max_climb="0.25", agent_max_slope="45.0", filter_baking_aabb="AABB(-25, -1, -25, 50, 4, 50)")
s.add_sub("ProceduralSkyMaterial", "sky_mat", sky_top_color="Color(0.27, 0.49, 0.78, 1)", sky_horizon_color="Color(0.86, 0.8, 0.68, 1)",
          ground_bottom_color="Color(0.45, 0.36, 0.25, 1)", ground_horizon_color="Color(0.86, 0.8, 0.68, 1)")
s.add_sub("Sky", "sky", sky_material='SubResource("sky_mat")')
s.add_sub("Environment", "env", background_mode="2", sky='SubResource("sky")', ambient_light_source="3", ambient_light_energy="0.9",
          tonemap_mode="3", tonemap_exposure="0.95", ssao_enabled="true", ssao_radius="1.2", ssao_intensity="2.2", ssil_enabled="true",
          glow_enabled="true", glow_intensity="0.6", fog_enabled="true", fog_light_color="Color(0.84, 0.76, 0.62, 1)", fog_density="0.004",
          fog_sky_affect="0.2", adjustment_enabled="true", adjustment_contrast="1.05", adjustment_saturation="1.08")
s.add_sub("CapsuleShape3D", "capsule", radius="0.35", height="1.8")
s.add_sub("PlaneMesh", "ground", size="Vector2(400, 400)")
s.add_sub("StandardMaterial3D", "ground_mat", albedo_color="Color(0.62, 0.5, 0.35, 1)", roughness="1.0")
for k, c in (("site", "Color(0.85, 0.25, 0.18, 0.22)"), ("buy", "Color(0.23, 0.64, 0.35, 0.2)"), ("T", "Color(0.84, 0.38, 0.12, 0.9)"),
             ("CT", "Color(0.16, 0.36, 0.67, 0.9)"), ("ai", "Color(1, 1, 1, 0.9)")):
    s.add_sub("StandardMaterial3D", f"vm_{k}", transparency="1", shading_mode="0", cull_mode="2", no_depth_test="true", albedo_color=c)
s.add_sub("CylinderMesh", "spawn_disc", top_radius="0.35", bottom_radius="0.35", height="0.06")
s.add_sub("CylinderMesh", "ai_pole", top_radius="0.06", bottom_radius="0.06", height="1.6", material='SubResource("vm_ai")')

s.node("Main", "Node3D")
s.node("WorldEnvironment", "WorldEnvironment", ".", environment='SubResource("env")')
x = np.array([-30, 45, -18], float); z_ = x / np.linalg.norm(x)
xa = np.cross([0, 1, 0], z_); xa /= np.linalg.norm(xa); ya = np.cross(z_, xa)
basis = ", ".join(f"{v:.5f}" for v in (*xa, *ya, *z_))
s.node("Sun", "DirectionalLight3D", ".", transform=f"Transform3D({basis}, 0, 40, 0)", light_color="Color(1, 0.9, 0.74, 1)",
       light_energy="1.6", shadow_enabled="true", shadow_blur="1.5", directional_shadow_max_distance="90.0")
s.node("Map", parent=".", instance=glb)
s.node("Navigation", "NavigationRegion3D", ".", navigation_mesh=nm)
s.node("Collision", parent="Navigation", instance=col)
s.node("OuterGround", "MeshInstance3D", ".", transform=T(0, -0.32, 0), mesh='SubResource("ground")',
       **{"surface_material_override/0": 'SubResource("ground_mat")'})
s.node("Lamps", "Node3D", ".")
for i, p in enumerate(meta["lamps"]):
    s.node(f"Lamp{i}", "OmniLight3D", "Lamps", transform=T(*p), light_color="Color(1, 0.68, 0.36, 1)",
           light_energy="1.4", omni_range="6.5", omni_attenuation="1.6")
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
for i, a in enumerate(st2["ai_points"]):
    nme = f"P{i:02d}"
    s.node(nme, "Marker3D", "AIPoints", groups=["ai_points"], transform=T(*a["pos"]),
           **{"metadata/label": json.dumps(a["label"]), "metadata/kind": f'"{a["kind"]}"', "metadata/team": f'"{a["team"]}"'})
    s.node("Pole", "MeshInstance3D", f"AIPoints/{nme}", groups=["debug_viz"], visible="false", transform=T(0, 0.8, 0), mesh='SubResource("ai_pole")')
    s.node("Label", "Label3D", f"AIPoints/{nme}", groups=["debug_viz"], visible="false", transform=T(0, 1.9, 0), billboard="1",
           no_depth_test="true", font_size="40", outline_size="10", text=json.dumps(f'{a["label"]} ({a["kind"]}, {a["team"]})'))
s.node("Player", "CharacterBody3D", ".", transform=T(0, 0.2, -20, yaw_pi=True), collision_layer="8", collision_mask="3", script=pscr)
s.node("CollisionShape3D", "CollisionShape3D", "Player", transform=T(0, 0.9, 0), shape='SubResource("capsule")')
s.node("Camera3D", "Camera3D", "Player", transform=T(0, 1.65, 0), fov="80.0")
s.node("FloorRay", "RayCast3D", "Player", transform=T(0, 0.2, 0), target_position="Vector3(0, -0.6, 0)", collision_mask="1")
s.node("Steps", "AudioStreamPlayer3D", "Player", transform=T(0, 0.1, 0), volume_db="-8.0", unit_size="4.0")
s.node("GameMode", "Node", ".", script=gscr)
s.node("HUD", "CanvasLayer", ".", script=hscr)
s.save(f"{OUT}/main.tscn")

# ---------------------------------------------------------------- project.godot
open(f"{OUT}/project.godot", "w").write('''; Engine configuration file.
config_version=5

[application]

config/name="Qumtepa v2 - 5v5 cho'l xaritasi"
run/main_scene="res://main.tscn"
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

[rendering]

anti_aliasing/quality/msaa_3d=2
lights_and_shadows/directional_shadow/size=8192
textures/default_filters/anisotropic_filtering_level=4
''')
open(f"{OUT}/tools/bake_nav.gd", "w").write('''extends SceneTree
## NavMesh'ni oldindan pishirish: godot --headless -s res://tools/bake_nav.gd


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
	print("navmesh poligonlar: ", nm.get_polygon_count())
	ResourceSaver.save(nm, "res://map/navmesh.res")
	quit()
''')
print("generated", counts, "navmesh:", NAVMESH)
