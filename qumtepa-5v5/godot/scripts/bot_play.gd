extends Node3D
## Botlar bilan o'yin (5v5 va 3v3): o'yinchi + (N−1) jamoadosh bot va N raqib bot, raund va bomba — game_mode.gd.
##
## Botlar nima qiladi:
##   - T: har raund taktika (strategies*.gd): yo'nalishlar, kutish, smoke tashlash, site'ga kirish, bomba o'rnatish,
##     o'rnatilgandan keyin himoya joylari; bomba yerda qolsa — eng yaqin T olib keladi;
##   - CT: joylashuv (2-1-2, 3-1-1, ...), site'da T lar ko'rinsa/eshitilsa — aylanib yordamga keladi,
##     bomba o'rnatilsa — qaytarib olish va zararsizlantirish (to'plam bo'lsa tezroq);
##   - ko'rish: ~140° maydon, ≤ 70 m, devor va smoke orqali ko'rmaydi (nur bilan tekshiriladi), faqat boshi
##     ko'rinayotgan nishonga qiyinroq tegadi; o'tirgan o'yinchi pastroq;
##   - eshitish: o'yinchining qadam tovushi (≤ 20 m; Shift va o'tirish — jim), o'q ovozi (≤ 45 m) —
##     bot o'sha tomonga qaraydi, CT lar ma'lumotni jamoaga beradi (aylanish);
##   - xotira: nishon ko'rinmay qolsa, oxirgi ko'rilgan joyga 3 s qarab turadi (qayta chiqsa tezroq javob);
##   - "trade": jamoadoshi o'lsa, yaqindagilar otuvchi tomonga qaraydi;
##   - jang: reaksiya 0.18–0.32 s (qiyinlik bo'yicha), birinchi o'q aniqroq, ketma-ket o'qda tarqalish o'sadi,
##     4–6 o'qdan keyin qisqa pauza; zarar — LAR-01 ma'lumoti va tana zonasi (bosh/tana/qo'l/oyoq), masofa;
##     o'z jamoasiga o'q uzmaydi.
## O'yinchi o'lsa — tirik jamoadoshini kuzatadi (sichqoncha chap tugmasi — keyingisi), raund boshida tiriladi.
## Dushman botlar ustidagi yozuv ko'rinmaydi (devor orqali ko'rsatmaslik uchun), jamoadoshlarniki ko'rinadi.

const BotScript := preload("res://scripts/bot.gd")
const RIFLE := preload("res://weapons/rifle.tres")
const WEAPONS := {"lar_01": preload("res://weapons/rifle.tres"), "rifle_vanguard": preload("res://weapons/vanguard.tres"),
	"spectre_smg": preload("res://weapons/smg.tres"), "longbow_50": preload("res://weapons/sniper.tres")}
const BOMB := preload("res://scenes/bomb.tscn")
## game_mode.gd dagi Phase qiymatlari (5v5 va 3v3 nusxalarida bir xil)
const FREEZE := 0
const LIVE := 1
const PLANTED := 2
const ROUND_END := 3
const SMOKE_LAYER := 128
const VIEW_DIST := 70.0
const FOV_DOT := 0.34
const STEP_HEAR := 20.0
const SHOT_HEAR := 45.0

@export var enabled := true
@export var team_size := 5
@export var strategies_path := "res://scripts/strategies.gd"
@export var map_data_path := "res://scripts/map_data.gd"
@export var game_path: NodePath = ^"../GameMode"
@export var player_path: NodePath = ^"../Player"
@export_range(0.5, 1.5) var difficulty := 1.1     ## 1.0 — oddiy, 1.1 — qiyin (standart), 1.3 — juda qiyin

var S: Script
var M: Script
var gm: Node
var player: CharacterBody3D
var rng := RandomNumberGenerator.new()
var bots: Array = []
var nav_map: RID
var space: PhysicsDirectSpaceState3D
var t := 0.0
var strat: Array
var setup: Array
var exec_time := 0.0
var executed := false
var smokes: Array = []
var smokes_thrown := false
var alert_count := {"A": {}, "B": {}}
var rotated := {}
var picker: Node = null
var kills: Array = []                 ## [vaqt, otuvchi, o'lgan, bosh bilanmi]
var rounds_seen := 0
var ready_ok := false
var _frame := 0
var _alive_prev := {}
var _spec_cam: Camera3D
var _spec_i := 0
var _layer: CanvasLayer
var _feed: Label
var _hp_lbl: Label
var _alive_lbl: Label
var _flash: ColorRect
var _smoke_mesh: SphereMesh
var _last_phase := -1


func _ready() -> void:
	if not enabled:
		set_physics_process(false)
		return
	S = load(strategies_path)
	M = load(map_data_path)
	gm = get_node(game_path)
	player = get_node(player_path)
	rng.randomize()
	space = get_world_3d().direct_space_state
	nav_map = get_world_3d().navigation_map
	for i in team_size * 2 - 1:
		var b: CharacterBody3D = BotScript.new()
		add_child(b)
		b.setup("T", i, Vector3(0, -50, 0), nav_map, true)
		bots.append(b)
		_alive_prev[b] = true
	player.footstep.connect(func(_s: String) -> void: _sound(player.global_position, STEP_HEAR, player.team, player))
	player.fired.connect(func() -> void: _sound(player.global_position, SHOT_HEAR, player.team, player))
	player.died.connect(_on_player_died)
	player.damaged.connect(_on_player_damaged)
	gm.phase_changed.connect(_on_phase)
	_make_ui()
	await get_tree().physics_frame
	await get_tree().physics_frame
	NavigationServer3D.map_force_update(nav_map)
	while NavigationServer3D.map_get_iteration_id(nav_map) == 0:
		await get_tree().physics_frame
	ready_ok = true
	prepare_round()


# ------------------------------------------------------------------ jamoalar va raund
func allies() -> Array:
	return bots.filter(func(b): return b.team == player.team)


func enemies() -> Array:
	return bots.filter(func(b): return b.team != player.team)


func side(team: String) -> Array:
	var out := bots.filter(func(b): return b.team == team)
	return out


func alive_count(team: String) -> int:
	var n := side(team).filter(func(b): return b.alive).size()
	if player.team == team and player.alive:
		n += 1
	return n


func _on_phase(p: int) -> void:
	if not ready_ok:
		return
	if p == FREEZE:
		prepare_round()
	elif p == ROUND_END:
		for b in bots:
			b.target = null
			b.busy = ""
			b.clear_goal()


func prepare_round() -> void:
	rounds_seen += 1
	t = 0.0
	executed = false
	smokes_thrown = false
	for s in smokes:
		s[0].queue_free()
	smokes = []
	alert_count = {"A": {}, "B": {}}
	rotated = {}
	picker = null
	kills = []
	if not player.alive:
		player.revive()
	player.cam.make_current()
	var my: String = player.team
	var other := "CT" if my == "T" else "T"
	var k := 0
	for b in bots:
		b.set_team(my if k < team_size - 1 else other)
		b.show_label = b.team == my
		k += 1
	var ts: Array = side("T")
	var cts: Array = side("CT")
	var sp_t := _spawns("T")
	var sp_ct := _spawns("CT")
	var off_t := 1 if my == "T" else 0          # o'yinchi — 0-spawn'da (game_mode)
	var off_ct := 1 if my == "CT" else 0
	for i in ts.size():
		ts[i].reset(sp_t[(i + off_t) % sp_t.size()].global_position)
		ts[i].idx = i + off_t
	for i in cts.size():
		cts[i].reset(sp_ct[(i + off_ct) % sp_ct.size()].global_position)
		cts[i].idx = i + off_ct
	for b in bots:
		b.clock = 0.0
		_alive_prev[b] = true
		b._update_label()
	# T taktikasi: guruhlar botlarga tartib bilan (o'yinchi T bo'lsa — uning o'rni oxirgisi)
	strat = S.T_STRATS[rng.randi() % S.T_STRATS.size()]
	setup = S.CT_SETUPS[rng.randi() % S.CT_SETUPS.size()]
	exec_time = rng.randf_range(strat[4][0], strat[4][1])
	var slots := []
	for g in strat[2]:
		for n in g[2]:
			slots.append([g[0], g[1], g[3] and n == 0])
	# bomba: o'yinchi T bo'lsa — 1/N ehtimol bilan o'yinchida (CS dagidek tasodifiy), aks holda bomba guruhidagi botda
	var bomb_given: bool = my == "T" and (ts.is_empty() or rng.randf() < 1.0 / team_size)
	if my == "T" and not bomb_given:
		player.has_bomb = false
	for i in ts.size():
		var b = ts[i]
		var sl: Array = slots[i % slots.size()]
		b.role = sl[0]
		b.plan = S.T_ROUTES[sl[0]].duplicate()
		b.entry = S.T_ENTRY[sl[1]].duplicate()
		b.carrier = sl[2] and not bomb_given
		if b.carrier:
			bomb_given = true
		b.mode = "route"
		var posts: Array = S.T_POSTPLANT[strat[1]]
		var post: Array = posts[i % posts.size()]
		b.post_spot = post[0]
		b.post_look = post[1]
	if not bomb_given and ts.size() > 0:
		ts[0].carrier = true
	if not player.has_bomb:
		gm.bomb_state = "carried"
	_give_weapons(ts, cts)
	for i in cts.size():
		var b = cts[i]
		var spot: Array = S.CT_SPOTS[setup[1][i % setup[1].size()]]
		b.role = setup[1][i % setup[1].size()]
		b.mode = "hold"
		b.set_goal(spot[0])
		b.hold_look = spot[1]
		b.has_kit = rng.randf() < 0.5


## qurollar: 5v5 da har jamoada bitta snayper (CT — platformadagi, T — Long guruhidagi), rush'dagilar — SMG,
## qolganlar — LAR-01 yoki AR-44. 3v3 da snayper 50% ehtimol bilan.
func _give_weapons(ts: Array, cts: Array) -> void:
	for arr in [ts, cts]:
		var sniper_ok: bool = team_size >= 5 or rng.randf() < 0.5
		for b in arr:
			var w := "lar_01" if rng.randf() < 0.6 else "rifle_vanguard"
			if sniper_ok and (b.role.begins_with("A platforma") or b.role.begins_with("B platforma") or b.role == "LONG"):
				w = "longbow_50"
				sniper_ok = false
			elif "rush" in str(strat[0]) and b.team == "T" and rng.randf() < 0.5:
				w = "spectre_smg"
			b.weapon = WEAPONS[w]
			if b.model:
				b.model.set_weapon(b.weapon.kind)


func _spawns(team: String) -> Array:
	var arr := get_tree().get_nodes_in_group("spawn_" + team)
	arr.sort_custom(func(a, b): return str(a.name) < str(b.name))
	return arr


# ------------------------------------------------------------------ asosiy sikl
func _physics_process(delta: float) -> void:
	if not ready_ok:
		return
	var ph: int = gm.phase
	var live: bool = ph == LIVE or ph == PLANTED
	if live:
		t += delta
	for b in bots:
		b.clock = t
	_frame += 1
	_update_smokes()
	if live:
		if _frame % 2 == 0:
			_perceive()
		_think_t()
		_think_ct()
		_combat()
	for b in bots:
		if b.alive:
			var can_move: bool = live and b.busy == "" and not (b.target != null or t < b.fight_until)
			b.step(delta, can_move)
	_process_deaths()
	if live:
		_check_end()
	_update_spectator()
	_update_ui(delta)


# ------------------------------------------------------------------ ko'rish va eshitish
func _los(from: Vector3, to: Vector3) -> bool:
	var q := PhysicsRayQueryParameters3D.create(from, to, 1 | SMOKE_LAYER)
	return space.intersect_ray(q).is_empty()


func _targets_for(b) -> Array:
	var out: Array = []
	for e in bots:
		if e.team != b.team and e.alive:
			out.append(e)
	if player.alive and player.team != b.team:
		out.append(player)
	return out


func _perceive() -> void:
	for b in bots:
		b.visible_enemies = []
		if not b.alive:
			continue
		for e in _targets_for(b):
			var to: Vector3 = e.global_position - b.global_position
			var d := to.length()
			if d > VIEW_DIST:
				continue
			var flat := Vector3(to.x, 0, to.z).normalized()
			if d > 4.0 and flat.dot(b.look_dir) < FOV_DOT:
				continue
			var eye: Vector3 = b.eye()
			var low: bool = e == player and player.crouching
			var chest: Vector3 = e.global_position + Vector3.UP * (0.8 if low else 1.2)
			var head: Vector3 = e.global_position + Vector3.UP * (1.2 if low else 1.65)
			if _los(eye, chest):
				b.visible_enemies.append([e, false])
			elif _los(eye, head):
				b.visible_enemies.append([e, true])
		for ve in b.visible_enemies:
			# ko'rilgan joyni eslab qoladi; CT lar site'dagi T larni jamoaga aytadi
			b.alert_look = ve[0].global_position
			b.alert_until = t + 3.0
			if b.team == "CT":
				_report(ve[0])


func _report(e: Node3D) -> void:
	var reg: String = S.REGION.get(M.callout_at(e.global_position), "")
	if reg in ["A", "B"]:
		alert_count[reg][e.get_instance_id()] = t


## tovush: radius ichidagi boshqa jamoa botlari o'sha tomonga qaraydi; CT lar hududni jamoaga aytadi
func _sound(pos: Vector3, radius: float, team: String, src: Node3D) -> void:
	if not ready_ok:
		return
	for b in bots:
		if not b.alive or b.team == team or b.target != null:
			continue
		if b.global_position.distance_to(pos) <= radius:
			b.alert_look = pos
			b.alert_until = t + 2.5
			if b.team == "CT" and src:
				_report(src)


# ------------------------------------------------------------------ T qarorlari
func _think_t() -> void:
	var site: String = strat[1]
	var plant_p: Vector3 = S.PLANT[site]
	if not executed and t >= exec_time:
		executed = true
	if executed and not smokes_thrown:
		smokes_thrown = true
		for n in strat[3]:
			if S.SMOKES.has(n):
				var sm: Array = S.SMOKES[n]
				_throw_smoke(sm[1], sm[2])
	var planted: bool = gm.bomb_state == "planted"
	var bomb_pos: Vector3 = gm.bomb.global_position if gm.bomb and is_instance_valid(gm.bomb) else Vector3.ZERO
	# bomba yerda — eng yaqin tirik T bot olib keladi (o'yinchi T bo'lsa u ham olishi mumkin — game_mode)
	if gm.bomb_state == "dropped" and (picker == null or not picker.alive):
		_choose_picker(bomb_pos)
	for b in side("T"):
		if not b.alive:
			continue
		if b.busy == "plant":
			if t >= b.busy_until and gm.phase == LIVE:
				_bot_plant(b, site)
			continue
		if gm.bomb_state == "dropped" and b == picker:
			b.mode = "pickup"
			b.set_goal(bomb_pos)
			if b.at(bomb_pos, 1.0):
				gm._clear_bomb()
				gm.bomb_state = "carried"
				b.carrier = true
				picker = null
				b.mode = "site"
			continue
		if planted:
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
			"site", "pickup":
				b.mode = "site"
				if b.carrier:
					b.set_goal(plant_p)
					if b.at(plant_p, 0.8) and b.visible_enemies.is_empty() and b.is_on_floor():
						b.busy = "plant"
						b.busy_until = t + gm.R.plant_time
						b.clear_goal()
				else:
					b.set_goal(b.post_spot)
					b.hold_look = b.post_look
			"post":
				b.set_goal(b.post_spot)
				b.hold_look = b.post_look
		if b.mode == "route" and executed:
			b.mode = "entry"


func _choose_picker(pos: Vector3) -> void:
	picker = null
	var best := INF
	for b in side("T"):
		if b.alive:
			var d: float = b.global_position.distance_to(pos)
			if d < best:
				best = d
				picker = b


func _bot_plant(b, site: String) -> void:
	b.busy = ""
	b.carrier = false
	gm._clear_bomb()
	var bomb: Node3D = BOMB.instantiate()
	gm.get_parent().add_child(bomb)
	bomb.global_position = gm._floor_point(b.global_position)
	bomb.plant(gm.R.bomb_timer)
	gm.bomb = bomb
	gm.bomb_state = "planted"
	gm.planted_site = site
	gm._set_phase(PLANTED, gm.R.bomb_timer)
	gm.bomb_event.emit("planted")


func _drop_bomb_at(pos: Vector3) -> void:
	gm._clear_bomb()
	var bomb: Node3D = BOMB.instantiate()
	gm.get_parent().add_child(bomb)
	bomb.global_position = gm._floor_point(pos)
	gm.bomb = bomb
	gm.bomb_state = "dropped"
	gm.bomb_event.emit("dropped")
	_choose_picker(pos)


# ------------------------------------------------------------------ CT qarorlari
func _think_ct() -> void:
	var seen := {}
	for reg in ["A", "B"]:
		var n := 0
		for k in alert_count[reg]:
			if t - alert_count[reg][k] < 5.0:
				n += 1
		seen[reg] = n
	var need_mid := 1 if team_size <= 3 else 2
	var need_far := 2 if team_size <= 3 else 3
	for b in side("CT"):
		if not b.alive:
			continue
		if b.busy == "defuse":
			if t >= b.busy_until and gm.phase == PLANTED:
				b.busy = ""
				gm._defuse()
			continue
		var spot: Array = S.CT_SPOTS[b.role]
		var home: String = spot[2]
		if gm.bomb_state == "planted" and gm.bomb and is_instance_valid(gm.bomb):
			var bp: Vector3 = gm.bomb.global_position
			b.mode = "retake"
			b.set_goal(bp)
			b.hold_look = bp
			if b.at(bp, 1.2) and b.visible_enemies.is_empty() and b.is_on_floor():
				b.busy = "defuse"
				b.busy_until = t + (gm.R.defuse_time_kit if b.has_kit else gm.R.defuse_time)
				b.clear_goal()
			continue
		for reg in ["A", "B"]:
			if reg == home:
				continue
			var need := need_mid if home == "M" else need_far
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
				var react := rng.randf_range(0.18, 0.32) / difficulty
				if b.moving():
					react += 0.1
				# oldindan qaralgan (eshitilgan / oxirgi ko'rilgan / turish) tomondan chiqsa — tezroq
				var to: Vector3 = cur.global_position - b.global_position
				var look_pt: Vector3 = b.alert_look if b.alert_until > t else b.hold_look
				if look_pt != Vector3.ZERO and not b.moving():
					var aim: Vector3 = look_pt - b.global_position
					if Vector3(aim.x, 0, aim.z).normalized().dot(Vector3(to.x, 0, to.z).normalized()) > 0.9:
						react -= 0.08
				b.react_at = t + maxf(0.1, react)
				b.burst = 0
		b.target = cur
		if cur == null:
			continue
		b.fight_until = t + 1.0
		if b.busy != "":
			b.busy = ""
		if t < b.react_at or t < b.next_shot:
			continue
		var W: Resource = b.weapon if b.weapon else RIFLE
		var sniper: bool = W.kind == 4
		b.burst += 1
		b.next_shot = t + W.shot_interval()
		if b.burst % rng.randi_range(4, 6) == 0:
			b.next_shot += 0.18                  # qisqa pauza (nishonni tiklash)
		b.on_shot()
		_sound(b.global_position, SHOT_HEAR, b.team, b)
		var dist: float = b.global_position.distance_to(cur.global_position)
		var p := clampf(0.74 - 0.0075 * dist, 0.15, 0.74) * difficulty
		if sniper:
			p = clampf(0.88 - 0.002 * dist, 0.6, 0.88) * difficulty    # snayper: masofa deyarli ta'sir qilmaydi
		elif W.kind == 3:
			p *= clampf(1.1 - dist / 60.0, 0.5, 1.1)                  # SMG: yaqinda yaxshi, uzoqda yomon
		if b.moving():
			p *= 0.2 if sniper else 0.5
		if head_only:
			p *= 0.55
		if cur == player:
			var sp := Vector2(player.velocity.x, player.velocity.z).length()
			if sp > 3.0:
				p *= 0.75
			if player.crouching:
				p *= 0.92
		p *= maxf(0.55, 1.0 - 0.05 * (b.burst - 1))       # ketma-ket o'qlarda tarqalish
		if b.burst == 1:
			p = minf(p * 1.15, 0.92)                        # birinchi o'q aniqroq
		if rng.randf() >= p:
			continue
		var zone := "body"
		if head_only:
			zone = "head"
		else:
			var r := rng.randf()
			var hc := 0.13 * difficulty
			if r < hc:
				zone = "head"
			elif r < hc + 0.14:
				zone = "leg"
			elif r < hc + 0.24:
				zone = "arm"
		var dmg: float = W.damage_at(dist, zone)
		var killed := false
		if cur == player:
			killed = player.damage(dmg, b.global_position)
		else:
			if cur.target == null:
				cur.alert_look = b.global_position
				cur.alert_until = t + 3.0
				cur.fight_until = t + 1.0
			cur.last_attacker = b
			killed = cur.damage(dmg)
		if killed:
			_on_kill(b, cur, zone == "head")


func _on_kill(killer, victim, head: bool) -> void:
	kills.append([t, killer, victim, head])
	# "trade": yaqindagi jamoadoshlar otuvchi tomonga qaraydi
	for b in bots:
		if b.alive and b.team == victim.team and b != victim and b.global_position.distance_to(victim.global_position) < 18.0:
			b.alert_look = killer.global_position
			b.alert_until = t + 3.0
	for b in bots:
		if b.target == victim:
			b.target = null


## botning o'limi (o'yinchi o'qidan ham): bomba tashlanadi, o'ldirilganlar ro'yxati
func _process_deaths() -> void:
	for b in bots:
		if _alive_prev.get(b, true) and not b.alive:
			_alive_prev[b] = false
			if not kills.any(func(k): return k[2] == b):
				var who: Node3D = b.last_attacker if b.last_attacker else player
				_on_kill(who, b, false)
			if b.carrier and gm.bomb_state == "carried":
				b.carrier = false
				_drop_bomb_at(b.global_position)
			if b == picker:
				picker = null


func _on_player_died() -> void:
	if player.has_bomb:
		gm.drop_bomb()
		_choose_picker(gm.bomb.global_position if gm.bomb else player.global_position)
	if gm.action != "":
		gm._cancel_action()
	_spec_i = 0


func _on_player_damaged(_amount: float, from_pos: Vector3) -> void:
	if _flash:
		_flash.color.a = 0.35
	# o'yinchining jamoadoshlari otuvchi tomonga qaraydi
	for b in allies():
		if b.alive and b.target == null and b.global_position.distance_to(player.global_position) < 20.0:
			b.alert_look = from_pos
			b.alert_until = t + 2.0


func _check_end() -> void:
	var ta := alive_count("T")
	var ca := alive_count("CT")
	if gm.phase == LIVE:
		if ca == 0:
			gm.end_round("T", "CT lar yo'q qilindi")
		elif ta == 0:
			gm.end_round("CT", "T lar yo'q qilindi")
	elif gm.phase == PLANTED and ca == 0:
		gm.end_round("T", "CT lar yo'q qilindi")


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
	body.process_mode = Node.PROCESS_MODE_DISABLED
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


# ------------------------------------------------------------------ kuzatish (o'yinchi o'lganda)
func _unhandled_input(event: InputEvent) -> void:
	if ready_ok and not player.alive and event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_spec_i += 1


func _update_spectator() -> void:
	if player.alive:
		return
	var al := allies().filter(func(b): return b.alive)
	if al.is_empty():
		return
	var b: Node3D = al[_spec_i % al.size()]
	var fwd: Vector3 = b.look_dir if b.look_dir != Vector3.ZERO else Vector3.FORWARD
	var want := b.global_position - fwd * 2.6 + Vector3.UP * 2.1
	var q := PhysicsRayQueryParameters3D.create(b.global_position + Vector3.UP * 1.7, want, 1)
	var hit := space.intersect_ray(q)
	if not hit.is_empty():
		want = hit.position + (b.global_position + Vector3.UP * 1.7 - hit.position).normalized() * 0.3
	_spec_cam.global_position = _spec_cam.global_position.lerp(want, 0.25) if _spec_cam.current else want
	_spec_cam.look_at(b.global_position + Vector3.UP * 1.5 + fwd * 3.0, Vector3.UP)
	if not _spec_cam.current:
		_spec_cam.make_current()


# ------------------------------------------------------------------ interfeys
func _make_ui() -> void:
	_smoke_mesh = SphereMesh.new()
	_smoke_mesh.radius = S.SMOKE_R
	_smoke_mesh.height = S.SMOKE_R * 2.0
	_smoke_mesh.radial_segments = 10
	_smoke_mesh.rings = 6
	var sm := StandardMaterial3D.new()
	sm.albedo_color = Color(0.82, 0.82, 0.8, 0.94)
	sm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_smoke_mesh.material = sm
	_spec_cam = Camera3D.new()
	_spec_cam.fov = 75.0
	_spec_cam.current = false
	add_child(_spec_cam)
	_layer = CanvasLayer.new()
	_layer.layer = 3
	add_child(_layer)
	_flash = ColorRect.new()
	_flash.color = Color(0.8, 0.0, 0.0, 0.0)
	_flash.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.add_child(_flash)
	_hp_lbl = _mk_label(34, Vector2(24, -80), Control.PRESET_BOTTOM_LEFT)
	_alive_lbl = _mk_label(22, Vector2(-180, 124), Control.PRESET_CENTER_TOP)
	_alive_lbl.custom_minimum_size = Vector2(360, 0)
	_alive_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_feed = _mk_label(18, Vector2(-460, 150), Control.PRESET_TOP_RIGHT)
	_feed.custom_minimum_size = Vector2(440, 0)
	_feed.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT


func _mk_label(size: int, pos: Vector2, preset: int) -> Label:
	var l := Label.new()
	l.set_anchors_preset(preset)
	l.position += pos
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	l.add_theme_constant_override("outline_size", 6)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.add_child(l)
	return l


func _name(n: Node) -> String:
	if n == player:
		return "SIZ"
	return "%s%d" % [n.team, n.idx + 1]


func _update_ui(delta: float) -> void:
	_flash.color.a = maxf(0.0, _flash.color.a - delta * 1.2)
	_hp_lbl.text = ("+ %d" % int(ceil(player.hp))) if player.alive else "O'LDINGIZ — jamoadoshni kuzatish (sichqoncha: keyingisi)"
	_hp_lbl.modulate = Color(1, 1, 1) if player.hp > 30 or not player.alive else Color(1, 0.35, 0.3)
	var dots := func(team: String) -> String:
		var n := alive_count(team)
		return "●".repeat(n) + "○".repeat(maxi(0, team_size - n))
	_alive_lbl.text = "T %s    %s CT" % [dots.call("T"), dots.call("CT")]
	var s := ""
	for k in kills.slice(maxi(0, kills.size() - 5)):
		s += "%s  →  %s%s\n" % [_name(k[1]), _name(k[2]), "  (bosh)" if k[3] else ""]
	_feed.text = s
	_layer.visible = player.cam.current or (_spec_cam and _spec_cam.current)
