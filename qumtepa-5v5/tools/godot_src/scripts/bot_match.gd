extends Node3D
## 5v5 bot o'yini: 10 ta bot, T taktikalari va CT joylashuvlari (scripts/strategies.gd), smoke'lar,
## bomba, qaytarib olish. Balans sinovi uchun: har bir raund natijasi va statistika yig'iladi.
##
## Ko'rish rejimi: bots.tscn ni oching va F6 bosing (sichqoncha + WASD — erkin kamera, 1–0 — botni kuzatish,
## Space — pauza, +/- — tezlik).
## Sinov rejimi: godot --headless --fixed-fps 60 -s res://tests/run_bots.gd  (docs/bots_stage3.json)
##
## Jang modeli (soddalashtirilgan): ko'rish maydoni ~140°, masofa ≤ 70 m; smoke ko'rishni to'sadi;
## reaksiya 0.20–0.35 s (harakatda +0.12 s, oldindan mo'ljallangan burchakda −0.08 s);
## tegish ehtimoli 72% dan masofa bilan kamayadi, harakatda ×0.5, faqat boshi ko'rinsa ×0.55;
## o'q 34 (masofa bilan kamayadi), 15% — boshga (o'ldiradi), otish oralig'i 0.12 s.

signal round_finished(stats: Dictionary)
signal all_done(summary: Dictionary)

const S := preload("res://scripts/strategies.gd")
const MapData := preload("res://scripts/map_data.gd")
const BotScript := preload("res://scripts/bot.gd")
const SMOKE_LAYER := 128
const VIEW_DIST := 70.0
const FOV_DOT := 0.34

@export var rounds_to_play := 0          ## 0 — to'xtovsiz (ko'rish rejimi)
@export var seed_value := 12345
@export var visual := true
@export var pause_between := 3.0

var R: Dictionary = MapData.ROUND
var rng := RandomNumberGenerator.new()
var bots: Array = []
var t_bots: Array = []
var ct_bots: Array = []
var nav_map: RID
var space: PhysicsDirectSpaceState3D

var round_no := 0
var t := 0.0
var live := false
var strat: Array
var setup: Array
var exec_time := 0.0
var executed := false
var bomb_state := "carried"      ## carried / dropped / planted / defused / exploded
var bomb_pos := Vector3.ZERO
var bomb_site := ""
var plant_t := -1.0
var picker: Node = null
var smokes: Array = []           ## [body, until]
var smokes_thrown := false
var alert := {"A": 0.0, "B": 0.0}
var alert_count := {"A": {}, "B": {}}
var rotated := {}
var kills: Array = []
var results: Array = []
var _frame := 0
var _pause_left := 0.0
var _hud: Label
var _bomb_mesh: MeshInstance3D
var _smoke_mesh: SphereMesh


func _ready() -> void:
	rng.seed = seed_value
	space = get_world_3d().direct_space_state
	nav_map = get_world_3d().navigation_map
	var spawns_t := get_tree().get_nodes_in_group("spawn_T")
	var spawns_ct := get_tree().get_nodes_in_group("spawn_CT")
	for i in 10:
		var b: CharacterBody3D = BotScript.new()
		add_child(b)
		var team := "T" if i < 5 else "CT"
		var sp: Node3D = (spawns_t if team == "T" else spawns_ct)[i % 5]
		b.setup(team, i % 5, sp.global_position, nav_map, visual)
		bots.append(b)
		(t_bots if team == "T" else ct_bots).append(b)
	if visual:
		_make_visuals()
	await get_tree().physics_frame
	await get_tree().physics_frame
	NavigationServer3D.map_force_update(nav_map)
	start_round()


# ------------------------------------------------------------------ raund
func start_round() -> void:
	var ns: int = S.T_STRATS.size()
	var nc: int = S.CT_SETUPS.size()
	strat = S.T_STRATS[round_no % ns]
	setup = S.CT_SETUPS[(round_no / ns) % nc]
	round_no += 1
	t = 0.0
	live = true
	executed = false
	exec_time = rng.randf_range(strat[4][0], strat[4][1])
	bomb_state = "carried"
	bomb_site = ""
	plant_t = -1.0
	picker = null
	for s in smokes:
		s[0].queue_free()
	smokes = []
	smokes_thrown = false
	alert = {"A": 0.0, "B": 0.0}
	alert_count = {"A": {}, "B": {}}
	rotated = {}
	kills = []
	var spawns_t := get_tree().get_nodes_in_group("spawn_T")
	var spawns_ct := get_tree().get_nodes_in_group("spawn_CT")
	for i in 5:
		t_bots[i].reset(spawns_t[i].global_position)
		ct_bots[i].reset(spawns_ct[i].global_position)
	# T guruhlari
	var k := 0
	for g in strat[2]:
		var first := true
		for n in g[2]:
			var b = t_bots[k]
			b.role = g[0]
			b.plan = S.T_ROUTES[g[0]].duplicate()
			b.entry = S.T_ENTRY[g[1]].duplicate()
			b.carrier = g[3] and first
			b.mode = "route"
			var post = S.T_POSTPLANT[strat[1]][k]
			b.post_spot = post[0]
			b.post_look = post[1]
			first = false
			k += 1
	# CT joylari
	for i in 5:
		var b = ct_bots[i]
		var spot: Array = S.CT_SPOTS[setup[1][i]]
		b.role = setup[1][i]
		b.mode = "hold"
		b.set_goal(spot[0])
		b.hold_look = spot[1]
		b.has_kit = rng.randf() < 0.5
	if _bomb_mesh:
		_bomb_mesh.visible = false


func end_round(winner: String, reason: String) -> void:
	if not live:
		return
	live = false
	var st := {
		"round": round_no, "strategy": strat[0], "site": strat[1], "setup": setup[0], "winner": winner, "reason": reason,
		"planted": plant_t >= 0.0, "plant_site": bomb_site, "plant_t": snappedf(plant_t, 0.1), "duration": snappedf(t, 0.1),
		"exec_t": snappedf(exec_time, 0.1),
		"t_alive": t_bots.filter(func(b): return b.alive).size(), "ct_alive": ct_bots.filter(func(b): return b.alive).size(),
		"kills": kills.duplicate(),
	}
	results.append(st)
	round_finished.emit(st)
	if rounds_to_play > 0 and results.size() >= rounds_to_play:
		all_done.emit(summary())
		return
	_pause_left = pause_between if visual else 0.0


# ------------------------------------------------------------------ asosiy sikl
func _physics_process(delta: float) -> void:
	if not live:
		if rounds_to_play > 0 and results.size() >= rounds_to_play:
			return
		_pause_left -= delta
		if _pause_left <= 0.0:
			start_round()
		return
	t += delta
	_frame += 1
	_update_smokes()
	if _frame % 2 == 0:
		_perceive()
	_think_t()
	_think_ct()
	_combat()
	for b in bots:
		if b.alive:
			var can_move: bool = b.busy == "" and not (b.target != null or t < b.fight_until)
			b.step(delta, can_move)
	_bomb_logic()
	_check_end()
	if visual:
		_update_hud()


# ------------------------------------------------------------------ ko'rish
func _los(from: Vector3, to: Vector3) -> bool:
	var q := PhysicsRayQueryParameters3D.create(from, to, 1 | SMOKE_LAYER)
	return space.intersect_ray(q).is_empty()


func _perceive() -> void:
	for b in bots:
		b.visible_enemies = []
		if not b.alive:
			continue
		var enemies: Array = ct_bots if b.team == "T" else t_bots
		for e in enemies:
			if not e.alive:
				continue
			var to: Vector3 = e.global_position - b.global_position
			var d := to.length()
			if d > VIEW_DIST:
				continue
			var flat := Vector3(to.x, 0, to.z).normalized()
			if d > 4.0 and flat.dot(b.look_dir) < FOV_DOT:
				continue
			var eye: Vector3 = b.eye()
			if _los(eye, e.global_position + Vector3.UP * 1.2):
				b.visible_enemies.append([e, false])
			elif _los(eye, e.global_position + Vector3.UP * 1.65):
				b.visible_enemies.append([e, true])
		# CT lar uchun ma'lumot: qaysi site'da nechta T ko'rindi
		if b.team == "CT":
			for ve in b.visible_enemies:
				var reg: String = S.REGION.get(MapData.callout_at(ve[0].global_position), "")
				if reg in ["A", "B"]:
					alert_count[reg][ve[0].idx] = t


# ------------------------------------------------------------------ T qarorlari
func _think_t() -> void:
	var site: String = strat[1]
	var plant_p: Vector3 = S.PLANT[site]
	if not executed and t >= exec_time:
		executed = true
	if executed and not smokes_thrown:
		smokes_thrown = true
		for n in strat[3]:
			var sm: Array = S.SMOKES[n]
			_throw_smoke(sm[1], sm[2])
	for b in t_bots:
		if not b.alive:
			continue
		if b.busy == "plant":
			if t >= b.busy_until:
				_plant(b)
			continue
		# bomba yerda — eng yaqin tirik T olib keladi
		if bomb_state == "dropped" and b == picker:
			b.mode = "pickup"
			b.set_goal(bomb_pos)
			if b.at(bomb_pos, 1.0):
				bomb_state = "carried"
				b.carrier = true
				picker = null
				if _bomb_mesh:
					_bomb_mesh.visible = false
				b.mode = "site"
			continue
		if bomb_state == "planted":
			b.mode = "post"
		match b.mode:
			"route":
				if b.plan_i < b.plan.size():
					b.set_goal(b.plan[b.plan_i])
					if b.at(b.plan[b.plan_i], 1.0):
						b.plan_i += 1
				else:
					b.mode = "stage"
			"stage":
				b.hold_look = b.entry[0]
				if executed:
					b.mode = "entry"
			"entry":
				if b.entry_i < b.entry.size():
					b.set_goal(b.entry[b.entry_i])
					if b.at(b.entry[b.entry_i], 1.0):
						b.entry_i += 1
				else:
					b.mode = "site"
			"site":
				if b.carrier:
					b.set_goal(plant_p)
					if b.at(plant_p, 0.8) and b.visible_enemies.is_empty() and b.is_on_floor():
						b.busy = "plant"
						b.busy_until = t + R.plant_time
						b.clear_goal()
				else:
					b.set_goal(b.post_spot)
					b.hold_look = b.post_look
			"post":
				b.set_goal(b.post_spot)
				b.hold_look = b.post_look
		# hujumgacha bo'lgan yo'lda kutish joyidan o'tib ketmaslik
		if b.mode == "route" and executed:
			b.mode = "entry"


func _plant(b) -> void:
	b.busy = ""
	b.carrier = false
	bomb_state = "planted"
	bomb_pos = b.global_position
	bomb_site = strat[1]
	plant_t = t
	if _bomb_mesh:
		_bomb_mesh.global_position = bomb_pos + Vector3.UP * 0.1
		_bomb_mesh.visible = true


# ------------------------------------------------------------------ CT qarorlari
func _think_ct() -> void:
	# ma'lumot: so'nggi 5 s da site hududida ko'rilgan turli T lar soni
	var seen := {}
	for reg in ["A", "B"]:
		var n := 0
		for k in alert_count[reg]:
			if t - alert_count[reg][k] < 5.0:
				n += 1
		seen[reg] = n
	for b in ct_bots:
		if not b.alive:
			continue
		if b.busy == "defuse":
			if t >= b.busy_until:
				b.busy = ""
				bomb_state = "defused"
			continue
		var spot: Array = S.CT_SPOTS[b.role]
		var home: String = spot[2]
		if bomb_state == "planted":
			b.mode = "retake"
			b.set_goal(bomb_pos)
			b.hold_look = bomb_pos
			if b.at(bomb_pos, 1.2) and b.visible_enemies.is_empty() and b.is_on_floor():
				b.busy = "defuse"
				b.busy_until = t + (R.defuse_time_kit if b.has_kit else R.defuse_time)
				b.clear_goal()
			continue
		# aylanish: mid dagilar 2+ T ko'rilganda, boshqa site dagilar 3+ T ko'rilganda
		for reg in ["A", "B"]:
			if reg == home:
				continue
			var need := 2 if home == "M" else 3
			if seen[reg] >= need and not rotated.has(b):
				rotated[b] = reg
		if rotated.has(b):
			var reg2: String = rotated[b]
			b.mode = "rotate"
			var hold: Array = S.ROTATE_SPOT[reg2][b.idx % S.ROTATE_SPOT[reg2].size()]
			b.set_goal(hold[0])
			b.hold_look = hold[1]


# ------------------------------------------------------------------ jang
func _combat() -> void:
	for b in bots:
		if not b.alive:
			continue
		# nishon tanlash
		var cur = null
		var head_only := false
		for ve in b.visible_enemies:
			if ve[0] == b.target and ve[0].alive:
				cur = ve[0]
				head_only = ve[1]
		if cur == null:
			var best := INF
			for ve in b.visible_enemies:
				if not ve[0].alive:
					continue
				var d: float = b.global_position.distance_to(ve[0].global_position)
				if d < best:
					best = d
					cur = ve[0]
					head_only = ve[1]
			if cur != null:
				var react := rng.randf_range(0.20, 0.35)
				if b.moving():
					react += 0.12
				if b.hold_look != Vector3.ZERO and not b.moving():
					var aim: Vector3 = (b.hold_look - b.global_position)
					var to: Vector3 = (cur.global_position - b.global_position)
					if Vector3(aim.x, 0, aim.z).normalized().dot(Vector3(to.x, 0, to.z).normalized()) > 0.9:
						react -= 0.08
				b.react_at = t + react
		b.target = cur
		if cur == null:
			continue
		b.fight_until = t + 1.0
		if b.busy != "":
			b.busy = ""          # o'rnatish / zararsizlantirish to'xtaydi
		if t < b.react_at or t < b.next_shot:
			continue
		b.next_shot = t + 0.12
		var dist: float = b.global_position.distance_to(cur.global_position)
		var p := clampf(0.72 - 0.0075 * dist, 0.15, 0.72)
		if b.moving():
			p *= 0.5
		if head_only:
			p *= 0.55
		if rng.randf() < p:
			var dmg := 100.0 if rng.randf() < 0.15 else 34.0 * (1.0 - dist / 200.0)
			# otilgan bot otuvchiga buriladi
			if cur.target == null:
				cur.look_dir = Vector3(b.global_position.x - cur.global_position.x, 0, b.global_position.z - cur.global_position.z).normalized()
				cur.fight_until = t + 1.0
			if cur.damage(dmg):
				_on_kill(b, cur)


func _on_kill(killer, victim) -> void:
	kills.append({"t": snappedf(t, 0.1), "killer": killer.team, "victim": victim.team,
		"where": MapData.callout_at(victim.global_position), "from": MapData.callout_at(killer.global_position),
		"dist": snappedf(killer.global_position.distance_to(victim.global_position), 0.1),
		"kp": [snappedf(killer.global_position.x, 0.1), snappedf(killer.global_position.z, 0.1)],
		"vp": [snappedf(victim.global_position.x, 0.1), snappedf(victim.global_position.z, 0.1)]})
	if victim.carrier and bomb_state == "carried":
		victim.carrier = false
		bomb_state = "dropped"
		bomb_pos = victim.global_position
		_choose_picker()
		if _bomb_mesh:
			_bomb_mesh.global_position = bomb_pos + Vector3.UP * 0.1
			_bomb_mesh.visible = true
	if victim == picker:
		_choose_picker()
	for b in bots:
		if b.target == victim:
			b.target = null


func _choose_picker() -> void:
	picker = null
	var best := INF
	for b in t_bots:
		if b.alive:
			var d: float = b.global_position.distance_to(bomb_pos)
			if d < best:
				best = d
				picker = b


# ------------------------------------------------------------------ smoke
func _throw_smoke(target: Vector3, flight: float) -> void:
	var body := StaticBody3D.new()
	body.collision_layer = SMOKE_LAYER
	body.collision_mask = 0
	var cs := CollisionShape3D.new()
	var sh := SphereShape3D.new()
	sh.radius = S.SMOKE_R
	cs.shape = sh
	body.add_child(cs)
	add_child(body)
	body.global_position = target + Vector3.UP * 1.2
	body.process_mode = Node.PROCESS_MODE_DISABLED   # uchib borguncha ishlamaydi
	if visual:
		var mi := MeshInstance3D.new()
		mi.mesh = _smoke_mesh
		body.add_child(mi)
	body.visible = false
	smokes.append([body, t + flight, t + flight + S.SMOKE_TIME])


func _update_smokes() -> void:
	var keep := []
	for s in smokes:
		if t >= s[2]:
			s[0].queue_free()
			continue
		if t >= s[1] and s[0].process_mode == Node.PROCESS_MODE_DISABLED:
			s[0].process_mode = Node.PROCESS_MODE_INHERIT
			s[0].visible = true
		keep.append(s)
	smokes = keep


# ------------------------------------------------------------------ bomba va raund oxiri
func _bomb_logic() -> void:
	if bomb_state == "planted" and t - plant_t >= R.bomb_timer:
		bomb_state = "exploded"


func _check_end() -> void:
	var ta := t_bots.filter(func(b): return b.alive).size()
	var ca := ct_bots.filter(func(b): return b.alive).size()
	if bomb_state == "exploded":
		end_round("T", "bomba portladi")
	elif bomb_state == "defused":
		end_round("CT", "bomba zararsizlantirildi")
	elif ca == 0:
		end_round("T", "CT lar yo'q qilindi")
	elif ta == 0 and bomb_state != "planted":
		end_round("CT", "T lar yo'q qilindi")
	elif bomb_state != "planted" and t >= R.round_time:
		end_round("CT", "vaqt tugadi")


# ------------------------------------------------------------------ statistika
func summary() -> Dictionary:
	var n := results.size()
	var tw := results.filter(func(r): return r.winner == "T").size()
	var by := func(key: String) -> Dictionary:
		var out := {}
		for r in results:
			var k: String = str(r[key])
			if not out.has(k):
				out[k] = {"rounds": 0, "t_wins": 0, "plants": 0}
			out[k].rounds += 1
			out[k].t_wins += 1 if r.winner == "T" else 0
			out[k].plants += 1 if r.planted else 0
		for k in out:
			out[k]["t_win_pct"] = snappedf(100.0 * out[k].t_wins / out[k].rounds, 0.1)
		return out
	var plants := results.filter(func(r): return r.planted)
	var retakes := plants.filter(func(r): return r.winner == "CT").size()
	var kill_where := {}
	var first_where := {}
	var first_t := 0.0
	for r in results:
		for kk in r.kills:
			kill_where[kk.where] = kill_where.get(kk.where, 0) + 1
		if not r.kills.is_empty():
			var f0 = r.kills[0]
			var key: String = "%s → %s (%s o'ldirdi)" % [f0.from, f0.where, f0.killer]
			first_where[key] = first_where.get(key, 0) + 1
			first_t += f0.t
	var reasons := {}
	for r in results:
		reasons[r.reason] = reasons.get(r.reason, 0) + 1
	return {
		"rounds": n, "t_wins": tw, "t_win_pct": snappedf(100.0 * tw / max(n, 1), 0.1),
		"plant_pct": snappedf(100.0 * plants.size() / max(n, 1), 0.1),
		"retake_pct": snappedf(100.0 * retakes / max(plants.size(), 1), 0.1),
		"avg_first_kill_s": snappedf(first_t / max(n, 1), 0.1),
		"by_site": by.call("site"), "by_strategy": by.call("strategy"), "by_setup": by.call("setup"),
		"reasons": reasons, "kills_by_callout": kill_where, "first_kills": first_where,
	}


# ------------------------------------------------------------------ ko'rinish (faqat ko'rish rejimida)
func _make_visuals() -> void:
	_smoke_mesh = SphereMesh.new()
	_smoke_mesh.radius = S.SMOKE_R
	_smoke_mesh.height = S.SMOKE_R * 2.0
	var sm := StandardMaterial3D.new()
	sm.albedo_color = Color(0.82, 0.82, 0.8, 0.92)
	sm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_smoke_mesh.material = sm
	_bomb_mesh = MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.4, 0.2, 0.3)
	var mm := StandardMaterial3D.new()
	mm.albedo_color = Color(1, 0.1, 0.05)
	mm.emission_enabled = true
	mm.emission = Color(1, 0.1, 0.05)
	bm.material = mm
	_bomb_mesh.mesh = bm
	_bomb_mesh.visible = false
	add_child(_bomb_mesh)
	var layer := CanvasLayer.new()
	add_child(layer)
	_hud = Label.new()
	_hud.position = Vector2(20, 16)
	_hud.add_theme_font_size_override("font_size", 20)
	_hud.add_theme_color_override("font_outline_color", Color.BLACK)
	_hud.add_theme_constant_override("outline_size", 6)
	layer.add_child(_hud)


func _update_hud() -> void:
	if not _hud:
		return
	var tw := results.filter(func(r): return r.winner == "T").size()
	var s := "Raund %d   T %d : %d CT   vaqt %.0f s\n" % [round_no, tw, results.size() - tw, t]
	s += "T taktikasi: %s (hujum %.0f s da)\nCT joylashuvi: %s\n" % [strat[0], exec_time, setup[0]]
	s += "Bomba: %s%s\n" % [bomb_state, (" (%s, %.0f s qoldi)" % [bomb_site, R.bomb_timer - (t - plant_t)]) if bomb_state == "planted" else ""]
	s += "Tirik: T %d, CT %d\n" % [t_bots.filter(func(b): return b.alive).size(), ct_bots.filter(func(b): return b.alive).size()]
	for k in kills.slice(max(0, kills.size() - 5)):
		s += "  %.0f s: %s (%s) → %s (%s), %.0f m\n" % [k.t, k.killer, k.from, k.victim, k.where, k.dist]
	_hud.text = s
