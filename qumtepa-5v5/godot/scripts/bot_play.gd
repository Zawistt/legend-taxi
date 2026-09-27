extends Node3D
## Botlar bilan o'yin (5v5 va 3v3, CS2 qoidalari): o'yinchi + (N−1) jamoadosh bot va N raqib bot; raund, iqtisod va
## bomba — game_mode.gd, zarar — combat.gd, granatalar — grenade.gd.
##
## Botlar nima qiladi (CS2 botlariga o'xshab, "professional" darajada):
##   IQTISOD: har raund pulga qarab sotib oladi — pistol raund (zirh yoki to'pponcha + granata), eco (tejash),
##     force-buy (SMG/Galil/FAMAS + zirh, ketma-ket yutqazganda), to'liq xarid (AK/M4 + zirh-kaska + granatalar,
##     CT — to'plam); har jamoada bitta snayperchi (pul yetsa AWP). Tirik qolsa — qurollari keyingi raundga qoladi.
##   T: taktika (strategies*.gd): yo'nalish, kutish, hujumdan oldin tutun va flesh, site'ga kirish, bomba faqat
##     aylana ichiga; o'rnatgandan keyin himoya joylari va CT keladigan tomonlarga qarash; bomba yerda — olib keladi.
##   CT: joylashuv, burchaklarni navbat bilan tekshiradi (har tomondan kelishi mumkin), site'da T ko'rinsa/eshitilsa
##     aylanib yordamga boradi; bomba o'rnatilsa — kamida ikki kishi yig'ilib qaytarib oladi (vaqt kam bo'lsa — darhol),
##     umid yo'q bo'lsa (1 ga 3+, vaqt yetmaydi) — qurolni saqlab qoladi; to'plam bo'lsa 5 s da zararsizlantiradi.
##   KO'RISH/ESHITISH: ~140° maydon, devor/tutun orqali ko'rmaydi; qadam (≤ 20 m) va o'q ovozi (≤ 45 m) tomonga
##     qaraydi, CT lar ma'lumotni jamoaga beradi; ko'rilgan joyni 3 s eslaydi; jamoadoshi o'lsa otuvchi tomonga qaraydi.
##   AIM: reaksiya 0.18–0.32 s; nishon oldindan qaralgan joydan chiqsa tezroq va aniqroq; boshga mo'ljal (AWP — tanaga);
##     xato = mo'ljal xatosi (kuzatgan sari kamayadi) + qurol tarqalishi (harakatda katta — bot to'xtab otadi) +
##     tepki (80% nazorat); masofaga qarab: yaqinda spray, o'rtada 3–4 lik burst, uzoqda bittalab; har o'q aniq
##     geometriya bilan (bosh / ko'krak / qorin / qo'l / oyoq) hisoblanadi — "har tomonga" otmaydi; magazin tugasa qayta o'qlaydi.
##   HOLAT: flesh ko'r qilsa — ko'rmaydi va otmaydi; olovdan chiqib ketadi; jarohatlangan CT orqaroqqa chekinadi.
## O'yinchi o'lsa — tirik jamoadoshini kuzatadi (sichqoncha chap tugmasi — keyingisi), raund boshida tiriladi.
## Dushman botlar ustidagi yozuv ko'rinmaydi (devor orqali ko'rsatmaslik uchun), jamoadoshlarniki ko'rinadi.

const BotScript := preload("res://scripts/bot.gd")
const Rules := preload("res://scripts/cs_rules.gd")
const Combat := preload("res://scripts/combat.gd")
const Grenade := preload("res://scripts/grenade.gd")
const SMOKE_LAYER := 128
const VIEW_DIST := 70.0
const FOV_DOT := 0.34
const STEP_HEAR := 20.0
const SHOT_HEAR := 45.0
const FREEZE := 0
const LIVE := 1
const PLANTED := 2
const ROUND_END := 3
const NAMES := ["Anvar", "Bobur", "Jasur", "Temur", "Sardor", "Aziz", "Dilshod", "Farrux", "Shoxrux"]

@export var enabled := true
@export var team_size := 5
@export var strategies_path := "res://scripts/strategies.gd"
@export var map_data_path := "res://scripts/map_data.gd"
@export var game_path: NodePath = ^"../GameMode"
@export var player_path: NodePath = ^"../Player"
@export_range(0.5, 1.5) var difficulty := 1.15     ## 1.0 — oddiy, 1.15 — kuchli (standart), 1.3 — professional

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
var smokes_thrown := false
var flashes_thrown := false
var alert_count := {"A": {}, "B": {}}
var rotated := {}
var picker: Node = null
var kills: Array = []                 ## [vaqt, otuvchi, o'lgan, bosh bilanmi]
var rounds_seen := 0
var ready_ok := false
var buys: Array = []                  ## oxirgi raunddagi xaridlar (sinov/ko'rish uchun): [ism, narsalar]
var _frame := 0
var _spec_cam: Camera3D
var _spec_i := 0
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
		b.loadout.name = NAMES[i % NAMES.size()]
		bots.append(b)
	gm.bots = bots
	player.footstep.connect(func(_s: String) -> void: _sound(player.global_position, STEP_HEAR, player.team, player))
	player.fired.connect(func() -> void: _sound(player.global_position, SHOT_HEAR, player.team, player))
	player.died.connect(_on_player_died)
	player.damaged.connect(_on_player_damaged)
	gm.phase_changed.connect(_on_phase)
	gm.killed.connect(_on_kill_event)
	_spec_cam = Camera3D.new()
	_spec_cam.fov = 75.0
	_spec_cam.current = false
	add_child(_spec_cam)
	await get_tree().physics_frame
	await get_tree().physics_frame
	NavigationServer3D.map_force_update(nav_map)
	while NavigationServer3D.map_get_iteration_id(nav_map) == 0:
		await get_tree().physics_frame
	ready_ok = true
	# birinchi raund game_mode._ready da boshlangan — botlar hozir qo'shildi: ularga ham raund boshi
	for b in bots:
		b.loadout.reset_match()
	prepare_round()


# ------------------------------------------------------------------ jamoalar va raund
func allies() -> Array:
	return bots.filter(func(b): return b.team == player.team)


func enemies() -> Array:
	return bots.filter(func(b): return b.team != player.team)


func side(team: String) -> Array:
	return bots.filter(func(b): return b.team == team)


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
	flashes_thrown = false
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
		var nt := my if k < team_size - 1 else other
		if b.team != nt:
			b.loadout.strip_all()            # jamoasi o'zgardi (yarim vaqt / F2) — qurollar qolmaydi
		b.set_team(nt)
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
		b.blind_until = 0.0
		for m in ["he_used", "entry_molly", "molly_A", "molly_B", "flashed_retake"]:
			if b.has_meta(m):
				b.remove_meta(m)
		b.loadout.round_start(b.team)
		b._update_label()
	# T taktikasi: guruhlar botlarga tartib bilan (o'yinchi T bo'lsa — uning o'rni oxirgisi)
	strat = S.T_STRATS[rng.randi() % S.T_STRATS.size()]
	setup = S.CT_SETUPS[rng.randi() % S.CT_SETUPS.size()]
	exec_time = rng.randf_range(strat[4][0], strat[4][1])
	var slots := []
	for g in strat[2]:
		for n in g[2]:
			slots.append([g[0], g[1], g[3] and n == 0])
	# bomba: o'yinchi T bo'lsa — 1/N ehtimol bilan o'yinchida (CS2 dagidek tasodifiy), aks holda bomba guruhidagi botda
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
	for i in cts.size():
		var b = cts[i]
		var spot: Array = S.CT_SPOTS[setup[1][i % setup[1].size()]]
		b.role = setup[1][i % setup[1].size()]
		b.mode = "hold"
		b.set_goal(spot[0])
		b.hold_look = spot[1]
	_buy_all(ts, cts)
	for b in bots:
		_equip_best(b)


func _spawns(team: String) -> Array:
	var arr := get_tree().get_nodes_in_group("spawn_" + team)
	arr.sort_custom(func(a, b): return str(a.name) < str(b.name))
	return arr


# ------------------------------------------------------------------ iqtisod: botlar xaridi (CS2 bot mantig'i)
func _buy_all(ts: Array, cts: Array) -> void:
	buys = []
	var played: int = gm.score["T"] + gm.score["CT"]
	var pistol_round: bool = played == 0 or played == gm.half_len or (played >= gm.half_len * 2 and (played - gm.half_len * 2) % Rules.OT_HALF == 0)
	for arr in [ts, cts]:
		if arr.is_empty():
			continue
		var team: String = arr[0].team
		var avg := 0.0
		for b in arr:
			avg += b.loadout.money
		avg /= arr.size()
		var loss_streak: int = gm.loss_count.get(team, 1)
		var sniper_given := false
		for i in arr.size():
			var b = arr[i]
			var lo = b.loadout
			var got := []
			var want_sniper: bool = not sniper_given and (b.role.contains("platforma") or b.role == "LONG" or (i == arr.size() - 1 and team_size >= 5))
			if pistol_round:
				if team == "CT" and i == 0 and _buy(b, "kit", got):
					pass
				if rng.randf() < 0.55:
					_buy(b, "kevlar", got)
				else:
					_buy(b, "p250" if rng.randf() < 0.6 else ("tec9" if team == "T" else "fiveseven"), got)
					_buy(b, "flash", got)
			elif lo.primary != null:
				# qurol bor (tirik qolgan) — zirh va granata to'ldiriladi
				_buy(b, "vesthelm", got)
				_util(b, team, got)
			else:
				var rifle := "ak47" if team == "T" else "m4a4"
				var full: int = lo.price_of(rifle) + Rules.KEVLAR_HELMET + (Rules.KIT if team == "CT" else 0) + 300
				if want_sniper and lo.money >= Rules.weapon("awp").price + Rules.KEVLAR_HELMET:
					_buy(b, "awp", got)
					_buy(b, "vesthelm", got)
					sniper_given = true
					_util(b, team, got)
				elif lo.money >= full:
					_buy(b, rifle, got)
					_buy(b, "vesthelm", got)
					if team == "CT" and not lo.kit:
						_buy(b, "kit", got)
					_util(b, team, got)
				elif avg < 2200 and loss_streak < 3 and lo.money < 3000:
					# eco: tejash (kichik xarid)
					if lo.money >= 2000 and rng.randf() < 0.3:
						_buy(b, "p250", got)
				else:
					# force-buy: arzon avtomat / SMG + zirh
					var cheap := ("galil" if team == "T" else "famas") if lo.money >= 2700 else ("mac10" if team == "T" else "mp9")
					if want_sniper and lo.money >= 2400:
						cheap = "ssg08"
						sniper_given = true
					_buy(b, cheap, got)
					_buy(b, "kevlar", got)
					if lo.money >= 500:
						_buy(b, "flash", got)
			buys.append([lo.name, got])


func _buy(b, item: String, got: Array) -> bool:
	if b.loadout.try_buy(item, b.team):
		got.append(item)
		return true
	return false


func _util(b, team: String, got: Array) -> void:
	var order := ["smoke", "flash", "molotov" if team == "T" else "incendiary", "he", "flash"]
	for g in order:
		if b.loadout.money < 1200 and g != "smoke" and g != "flash":
			continue
		_buy(b, g, got)


func _equip_best(b) -> void:
	var lo = b.loadout
	b.weapon = lo.primary if lo.primary else lo.secondary
	if b.weapon and b.model:
		b.model.set_weapon(b.weapon.kind, b.weapon.weapon_id)
	b.burst = 0
	b.set_meta("reload_until", 0.0)


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
	if live:
		if _frame % 2 == 0:
			_perceive()
		_think_t()
		_think_ct()
		_sweep_angles()
		_avoid_fire()
		if _frame % 6 == 0:
			_utility()
		_combat()
	for b in bots:
		if b.alive:
			var can_move: bool = live and b.busy == "" and not (b.target != null or t < b.fight_until)
			b.step(delta, can_move)
	if live:
		_check_end()
	_update_spectator()


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
		if not b.alive or b.blind_until > t:
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


## burchaklarni tekshirish: to'xtab turgan bot har 2–4 s da xavfli tomonlardan biriga qaraydi
func _sweep_angles() -> void:
	if _frame % 20 != 0:
		return
	for b in bots:
		if not b.alive or b.target != null or b.moving() or b.alert_until > t:
			continue
		var pts: Array = []
		if b.team == "CT" and b.mode == "hold":
			var spot: Array = S.CT_SPOTS[b.role]
			pts.append(spot[1])
			for key in S.T_ENTRY:
				var e: Array = S.T_ENTRY[key]
				if b.global_position.distance_to(e[e.size() - 1]) < 26.0:
					pts.append(e[e.size() - 1])
		elif b.team == "T" and (b.mode == "post" or b.mode == "site"):
			pts.append(b.post_look)
			for h in S.ROTATE_SPOT.get(strat[1], []):
				pts.append(h[0])
		if pts.size() > 1 and rng.randf() < 0.35:
			b.hold_look = pts[rng.randi() % pts.size()]


## olovdan qochish
func _avoid_fire() -> void:
	var fires := get_tree().get_nodes_in_group("fires")
	if fires.is_empty():
		return
	for b in bots:
		if not b.alive:
			continue
		for f in fires:
			if f.contains(b.global_position):
				var away: Vector3 = (b.global_position - f.global_position) * Vector3(1, 0, 1)
				b._unstick_dir = away.normalized() if away.length() > 0.1 else Vector3.RIGHT
				b._unstick_left = 0.5
				b.fight_until = 0.0


# ------------------------------------------------------------------ T qarorlari
func _think_t() -> void:
	var site: String = strat[1]
	var plant_p: Vector3 = gm.plant_spots.get(site, S.PLANT[site])
	if not executed and t >= exec_time:
		executed = true
	if executed and not smokes_thrown:
		smokes_thrown = true
		for n in strat[3]:
			if S.SMOKES.has(n) and _take_nade("T", "smoke"):
				var sm: Array = S.SMOKES[n]
				_lineup(sm[1], sm[2], "smoke", null)
	if executed and not flashes_thrown and t >= exec_time + 1.2:
		flashes_thrown = true
		# kirishdan oldin flesh — site ichiga (CT lar ko'r bo'ladi)
		for b in side("T"):
			if b.alive and b.mode == "entry" and _take_bot_nade(b, "flash"):
				_lineup(plant_p + Vector3.UP * 2.0, 0.9, "flash", b)
				break
	var planted: bool = gm.bomb_state == "planted"
	var bomb_pos: Vector3 = gm.bomb.global_position if gm.bomb and is_instance_valid(gm.bomb) else Vector3.ZERO
	if gm.bomb_state == "dropped" and (picker == null or not picker.alive):
		_choose_picker(bomb_pos)
	for b in side("T"):
		if not b.alive:
			continue
		if b.busy == "plant":
			if t >= b.busy_until and gm.phase == LIVE:
				b.busy = ""
				b.carrier = false
				gm.plant_bomb(b, b.global_position, site)
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
					if b.at(plant_p, 0.8) and b.visible_enemies.is_empty() and b.is_on_floor() \
							and gm.plant_circle_at(b.global_position) != "":
						b.busy = "plant"
						b.busy_until = t + gm.R.plant_time
						b.clear_goal()
				else:
					b.set_goal(b.post_spot)
					b.hold_look = b.post_look
			"post":
				b.set_goal(b.post_spot)
				if b.alert_until <= t:
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


func _drop_bomb_at(pos: Vector3) -> void:
	gm._clear_bomb()
	var bomb: Node3D = gm.BombScene.instantiate()
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
	var cts := side("CT")
	var alive_ct := alive_count("CT")
	var alive_t := alive_count("T")
	for b in cts:
		if not b.alive:
			continue
		if b.busy == "defuse":
			if t >= b.busy_until and gm.phase == PLANTED:
				b.busy = ""
				gm._defuse(b)
			continue
		var spot: Array = S.CT_SPOTS[b.role]
		var home: String = spot[2]
		if gm.bomb_state == "planted" and gm.bomb and is_instance_valid(gm.bomb):
			var bp: Vector3 = gm.bomb.global_position
			var need: float = gm.R.defuse_time_kit if b.loadout.kit else gm.R.defuse_time
			var dist: float = b.global_position.distance_to(bp)
			var arrive: float = dist / 4.2 + need
			# umid yo'q: yolg'iz 3+ T ga qarshi va vaqt yetmaydi — qurolni saqlash
			if alive_ct <= 1 and alive_t >= 3 and gm.time_left < arrive:
				b.mode = "save"
				b.set_goal(_spawns("CT")[0].global_position)
				continue
			# guruh bo'lib qaytarish: yaqinda (≤ 22 m) kamida 2 CT bo'lguncha kutish (vaqt kam bo'lsa — darhol)
			var near := cts.filter(func(o): return o.alive and o.global_position.distance_to(bp) < 22.0).size()
			var wait_ok: bool = gm.time_left > arrive + 8.0 and near < mini(2, alive_ct) and dist > 12.0
			var rot: Array = S.ROTATE_SPOT.get(gm.planted_site, [[bp, bp]])
			b.mode = "retake"
			if wait_ok:
				var hold: Array = rot[b.idx % rot.size()]
				b.set_goal(hold[0])
				b.hold_look = bp
			else:
				if b.at(bp, 14.0) and b.visible_enemies.is_empty() and not b.get_meta("flashed_retake", false) and _take_bot_nade(b, "flash"):
					b.set_meta("flashed_retake", true)
					_lineup(bp + Vector3.UP * 2.2, 0.9, "flash", b)
				b.set_goal(bp)
				b.hold_look = bp
				if b.at(bp, 1.2) and b.visible_enemies.is_empty() and b.is_on_floor():
					b.busy = "defuse"
					b.busy_until = t + need
					b.clear_goal()
			continue
		b.set_meta("flashed_retake", false)
		# jarohatlangan (≤ 35 HP) va dushman ko'rinmayapti — orqaroqqa chekinib ushlab turish
		if b.hp <= 35.0 and b.visible_enemies.is_empty() and b.mode == "hold" and home in ["A", "B"]:
			var back: Array = S.ROTATE_SPOT[home][0]
			b.set_goal(back[0])
			b.hold_look = back[1]
			b.mode = "fallback"
		# site'ga ko'p T kirsa — molotov/yondiruvchi kirish joyiga
		for reg in ["A", "B"]:
			if reg == home and seen[reg] >= 2 and b.target == null and b.alert_until > t and not b.get_meta("molly_" + reg, false):
				if _take_bot_nade(b, "incendiary"):
					b.set_meta("molly_" + reg, true)
					_lineup(b.alert_look, 1.0, "incendiary", b)
		for reg in ["A", "B"]:
			if reg == home:
				continue
			var need2 := need_mid if home == "M" else need_far
			if seen[reg] >= need2 and not rotated.has(b):
				rotated[b] = reg
		if rotated.has(b):
			var reg2: String = rotated[b]
			b.mode = "rotate"
			var hold2: Array = S.ROTATE_SPOT[reg2][b.idx % S.ROTATE_SPOT[reg2].size()]
			b.set_goal(hold2[0])
			b.hold_look = hold2[1]


# ------------------------------------------------------------------ granatalar (botlar)
## vaziyatga qarab granata: zararsizlantirilayotgan bombaga molotov (T), dushman eshitilgan/yashiringan joyga HE,
## yaqin kelayotgan dushmanga flesh (o'zi ko'r bo'lmasligi uchun teskari tomonga qaramaydi — nishon joyiga tashlaydi)
func _utility() -> void:
	var defusing: bool = gm.action == "defuse"
	for b in side("CT"):
		if b.alive and b.busy == "defuse":
			defusing = true
	for b in bots:
		if not b.alive or b.busy != "":
			continue
		var nades: Array = b.loadout.grenades
		if nades.is_empty():
			continue
		# 1) T: bomba zararsizlantirilyapti — molotov bomba ustiga (ko'rmasa ham, joyini biladi)
		if b.team == "T" and defusing and gm.bomb and is_instance_valid(gm.bomb) and "molotov" in nades:
			var bp: Vector3 = gm.bomb.global_position
			if b.global_position.distance_to(bp) < 28.0:
				_take_bot_nade(b, "molotov")
				_lineup(bp, 1.1, "molotov", b)
				continue
		# 2) dushman shu yerda edi (eshitildi / ko'rindi), hozir ko'rinmayapti — HE o'sha joyga
		if "he" in nades and b.target == null and b.alert_until > t and not b.has_meta("he_used"):
			var d: float = b.global_position.distance_to(b.alert_look)
			if d > 7.0 and d < 26.0 and rng.randf() < 0.35:
				_take_bot_nade(b, "he")
				b.set_meta("he_used", true)
				_lineup(b.alert_look, 0.4 + d / 18.0, "he", b)
				continue
		# 3) T: site'ga kirishda molotov CT turadigan burchakka (strategiyaning maqsad site'i)
		if b.team == "T" and b.mode == "entry" and "molotov" in nades and not b.has_meta("entry_molly"):
			var site: String = strat[1]
			for key in S.CT_SPOTS:
				var sp: Array = S.CT_SPOTS[key]
				if sp[2] == site and b.global_position.distance_to(sp[0]) < 24.0:
					_take_bot_nade(b, "molotov")
					b.set_meta("entry_molly", true)
					_lineup(sp[0], 1.2, "molotov", b)
					break


func _take_nade(team: String, type: String) -> bool:
	for b in side(team):
		if b.alive and _take_bot_nade(b, type):
			return true
	return false


func _take_bot_nade(b, type: String) -> bool:
	if type in b.loadout.grenades:
		b.loadout.grenades.erase(type)
		return true
	return false


## "lineup": granata belgilangan vaqtdan keyin nishonga tushadi (fizika bilan topilgan smoke lineup'lari —
## strategies*.gd), keyin haqiqiy granata sifatida ishlaydi (tutun ko'rishni to'sadi, flesh ko'r qiladi, olov yonadi)
func _lineup(target: Vector3, flight: float, type: String, who) -> void:
	var tw := get_tree().create_timer(flight)
	tw.timeout.connect(func() -> void:
		if not is_inside_tree() or gm.phase == ROUND_END:
			return
		Grenade.throw(get_parent(), type, target + Vector3.UP * 0.25, Vector3.DOWN * 2.0, who))


# ------------------------------------------------------------------ jang: professional aim modeli
func _combat() -> void:
	for b in bots:
		if not b.alive:
			continue
		if b.blind_until > t:
			b.target = null
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
				var to: Vector3 = cur.global_position - b.global_position
				var look_pt: Vector3 = b.alert_look if b.alert_until > t else b.hold_look
				var pre := false
				if look_pt != Vector3.ZERO and not b.moving():
					var aim: Vector3 = look_pt - b.global_position
					pre = Vector3(aim.x, 0, aim.z).normalized().dot(Vector3(to.x, 0, to.z).normalized()) > 0.9
					if pre:
						react -= 0.08
				b.react_at = t + maxf(0.1, react)
				b.burst = 0
				b.set_meta("track_from", t)
				b.set_meta("pre_aim", pre)
		b.target = cur
		if cur == null:
			continue
		b.fight_until = t + 1.0
		if b.busy != "":
			b.busy = ""
		var W: Resource = b.weapon if b.weapon else Rules.weapon("glock")
		if t < b.react_at or t < b.next_shot or t < float(b.get_meta("reload_until", 0.0)):
			continue
		# magazin
		var am: Array = b.loadout.ammo.get(W.weapon_id, [W.magazine_size, W.reserve_ammo])
		if am[0] <= 0:
			if am[1] <= 0 and b.loadout.secondary and W != b.loadout.secondary:
				b.weapon = b.loadout.secondary                     # o'q tugadi — to'pponchaga
				if b.model:
					b.model.set_weapon(b.weapon.kind, b.weapon.weapon_id)
				continue
			var n: int = mini(W.magazine_size, am[1])
			b.loadout.ammo[W.weapon_id] = [n, am[1] - n]
			b.set_meta("reload_until", t + W.reload_time)
			b.burst = 0
			continue
		am[0] -= 1
		b.loadout.ammo[W.weapon_id] = am
		var dist: float = b.global_position.distance_to(cur.global_position)
		# otish ritmi: yaqinda spray, o'rtada burst, uzoqda bittalab (tepki tiklanadi)
		b.burst += 1
		var interval: float = W.shot_interval()
		var sniper: bool = W.kind == 4
		var auto: bool = W.fire_modes.size() > 0 and int(W.fire_modes[0]) == 2
		if auto:
			var max_burst := 30 if dist < 10.0 else (5 if dist < 20.0 else (3 if dist < 35.0 else 1))
			if W.kind == 3:
				max_burst = 30 if dist < 18.0 else 4
			if b.burst >= max_burst:
				interval += 0.28 if dist >= 20.0 else 0.15
				b.burst = 0
		elif W.kind == 1:
			interval = maxf(interval, 0.22 if dist > 15.0 else 0.14)
		b.next_shot = t + interval
		b.on_shot()
		_sound(b.global_position, SHOT_HEAR, b.team, b)
		for pellet in W.projectile_count:
			var zone := _shot_zone(b, cur, W, dist, head_only, sniper)
			if zone == "":
				continue
			var raw: float = W.damage_at(dist, zone)
			var killed: bool = cur.take_hit(raw, zone, b, W) if cur != player else Combat.hit(player, raw, zone, b, W)
			if cur != player and cur.target == null:
				cur.alert_look = b.global_position
				cur.alert_until = t + 3.0
				cur.fight_until = t + 1.0
			if killed:
				break


## bitta o'q qayerga tegadi: mo'ljal nuqtasi + burchak xatosi (mo'ljal, qurol tarqalishi, tepki) -> zona yoki "" (tegmadi)
func _shot_zone(b, cur, W: Resource, dist: float, head_only: bool, sniper: bool) -> String:
	var tracked: float = t - float(b.get_meta("track_from", t))
	var pre: bool = b.get_meta("pre_aim", false)
	var s_aim: float = (0.012 if not pre else 0.006) * exp(-tracked / 0.35) + 0.0022
	s_aim /= difficulty
	var tgt_moving: bool = Vector2(cur.velocity.x, cur.velocity.z).length() > 2.5
	if tgt_moving:
		s_aim += 0.004 / difficulty
	var s_w: float = W.base_spread
	if sniper:
		s_w *= W.ads_spread_multiplier            # bot har doim optika bilan, to'xtab otadi
	if b.moving():
		s_w *= W.spread_walk_mult
	s_w += W.spread_bloom_per_shot * clampf(b.burst - 1, 0.0, 8.0)
	var s_r := 0.0
	if W.recoil_pattern_v.size() > 0 and b.burst > 1:
		var i: int = mini(b.burst - 1, W.recoil_pattern_v.size() - 1)
		s_r = deg_to_rad(W.recoil_pattern_v[i] * W.recoil_scale) * 0.2          # 80% tepki nazorati
	var sig := sqrt(s_aim * s_aim + s_w * s_w + s_r * s_r)
	var low: bool = cur == player and player.crouching
	var head_h := 1.2 if low else 1.65
	var aim_head: bool = head_only or (not sniper and (dist < 35.0 or rng.randf() < 0.6) and rng.randf() < 0.55 * difficulty)
	var aim_y: float = head_h if aim_head else (0.95 if low else 1.3)
	var dx := rng.randfn(0.0, sig) * dist
	var dy := rng.randfn(0.0, sig) * dist
	var y := aim_y + dy
	var x := dx
	if Vector2(x, y - head_h).length() < 0.12:
		return "head"
	if head_only:
		return ""
	var top := (head_h - 0.18)
	var bottom := 0.55 if low else 0.95
	if absf(x) <= 0.2 and y >= bottom and y <= top:
		return "body" if y > (bottom + top) * 0.5 else "stomach"
	if absf(x) > 0.2 and absf(x) <= 0.3 and y >= bottom and y <= top:
		return "arm"
	if absf(x) <= 0.17 and y >= 0.0 and y < bottom:
		return "leg"
	return ""


func _on_kill_event(e: Dictionary) -> void:
	var killer = e.get("attacker")
	var victim = e.get("victim_node")
	kills.append([t, killer, victim, e.get("head", false)])
	if victim == null:
		return
	for b in bots:
		if b.alive and b.team == victim.team and b != victim and killer and b.global_position.distance_to(victim.global_position) < 18.0:
			b.alert_look = killer.global_position
			b.alert_until = t + 3.0
	for b in bots:
		if b.target == victim:
			b.target = null
	if victim in bots:
		if victim.carrier and gm.bomb_state == "carried":
			victim.carrier = false
			_drop_bomb_at(victim.global_position)
		if victim == picker:
			picker = null


func _on_player_died() -> void:
	if player.has_bomb:
		gm.drop_bomb()
		_choose_picker(gm.bomb.global_position if gm.bomb else player.global_position)
	if gm.action != "":
		gm._cancel_action()
	_spec_i = 0


func _on_player_damaged(_amount: float, from_pos: Vector3) -> void:
	for b in allies():
		if b.alive and b.target == null and b.global_position.distance_to(player.global_position) < 20.0:
			b.alert_look = from_pos
			b.alert_until = t + 2.0


func _check_end() -> void:
	var ta := alive_count("T")
	var ca := alive_count("CT")
	if gm.phase == LIVE:
		if ca == 0:
			gm.end_round("T", "CT lar yo'q qilindi", "elim")
		elif ta == 0:
			gm.end_round("CT", "T lar yo'q qilindi", "elim")
	elif gm.phase == PLANTED and ca == 0:
		gm.end_round("T", "CT lar yo'q qilindi", "elim")


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
