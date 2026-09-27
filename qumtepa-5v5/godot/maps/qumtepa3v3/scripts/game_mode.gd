extends Node
## Raund tizimi (CS2 qoidalari): TAYYORGARLIK -> JANG -> (BOMBA O'RNATILDI) -> RAUND OXIRI.
## Iqtisod: boshlanishda hamma $800; g'alaba — $3250 (yo'q qilish / vaqt) yoki $3500 (bomba / zararsizlantirish);
##   mag'lubiyat bonusi $1400–$3400 (ketma-ket yutqazganda oshadi, yutganda bittaga kamayadi; 1-raund yutqazilsa $1900);
##   T yutqazsa, lekin bomba o'rnatilgan bo'lsa — har T ga +$800; o'rnatgan +$300, zararsizlantirgan +$300;
##   vaqt tugaganda tirik qolgan T lar hech narsa olmaydi; o'ldirish uchun — qurolga qarab ($100–$1500); ko'pi bilan $16000.
## Raundlar: MR12 (13 g'alabagacha, 12 raunddan keyin tomonlar almashadi, pul $800 ga qaytadi); 12:12 da qo'shimcha vaqt
##   (MR3, $12500, birinchi 16 ga). 3v3 xaritasida Wingman: MR8 (9 g'alabagacha) — map_data.gd dagi win_rounds.
## Bomba: faqat site'dagi belgilangan aylana ichida (radius 2.8 m) E ni bosib turiladi — kod teriladi (7355608, 3.2 s);
##   40 s dan keyin portlaydi: zarar masofaga qarab (CS2 formulasi, ~20 m gacha o'ldiradi), zarba to'lqini xarita bo'ylab.
##   CT: bomba yonida E ni bosib turadi — 10 s (to'plam bilan 5 s).
## Debug: F1 zonalar, F2 jamoani almashtirish, F3 raundni qayta boshlash.

signal phase_changed(phase: int)
signal round_ended(winner: String, reason: String)
signal bomb_event(event: String)
signal killed(entry: Dictionary)
signal weapon_picked(who: Node, weapon: Resource)

enum Phase { FREEZE, LIVE, PLANTED, ROUND_END }

const MapData := preload("res://maps/qumtepa3v3/scripts/map_data.gd")
const Rules := preload("res://scripts/cs_rules.gd")
const Loadout := preload("res://scripts/loadout.gd")
const BombScene := preload("res://scenes/bomb.tscn")
const WeaponDrop := preload("res://scripts/weapon_drop.gd")
const PICK_RANGE := 0.9
const DEFUSE_RANGE := 1.6
const PICKUP_RANGE := 1.0

@export var player_path: NodePath = ^"../Player"
@export var start_team := "T"

@onready var player: CharacterBody3D = get_node(player_path)

var R: Dictionary = MapData.ROUND
var phase: int = Phase.FREEZE
var time_left := 0.0
var buy_time_left := 0.0
var score := {"T": 0, "CT": 0}
var round_no := 0
var bomb: Node3D = null
var bomb_state := "none"   ## carried / dropped / planted / defused / exploded / none
var planted_site := ""
var planter: Node = null
var action := ""           ## "plant" yoki "defuse"
var action_progress := 0.0
var action_duration := 1.0
var last_winner := ""
var last_reason := ""
var match_winner := ""
var debug_visible := false
var has_defuse_kit := false  ## eski API (endi o'yinchining loadout.kit)
var bots: Array = []                      ## bot_play.gd ro'yxatga qo'shadi
var loss_count := {"T": Rules.START_LOSS, "CT": Rules.START_LOSS}
var win_target := 13
var half_len := 12
var feed: Array = []                      ## kim kimni, qaysi qurol bilan, boshga
var round_log: Array = []                 ## raund natijalari (tarix)
var plant_spots := {}                     ## site -> markaz (aylana)
var last_money := {}                      ## raund oxiridagi pul o'zgarishi (HUD uchun)
var _pickup_cooldown := 0.0
var _swapped_at := -1
var _beep: AudioStreamPlayer
var _digits := 0


func _ready() -> void:
	add_to_group("game_mode")
	preload("res://maps/qumtepa3v3/scripts/input_setup.gd").ensure()
	var nav := get_node_or_null(^"../Navigation") as NavigationRegion3D
	if nav and nav.navigation_mesh and nav.navigation_mesh.get_polygon_count() == 0:
		nav.bake_navigation_mesh(false)
	win_target = int(R.win_rounds)
	half_len = win_target - 1
	player.team = start_team
	player.loadout.name = "Siz"
	_beep = AudioStreamPlayer.new()
	_beep.stream = load("res://audio/bomb_beep.wav")
	_beep.volume_db = -10.0
	add_child(_beep)
	_find_plant_spots()
	_set_debug(false)
	start_round()


func combatants() -> Array:
	var out := [player]
	for b in bots:
		if is_instance_valid(b):
			out.append(b)
	return out


func team_members(team: String) -> Array:
	return combatants().filter(func(c): return c.team == team)


# ------------------------------------------------------------------ raund oqimi
func start_round() -> void:
	if match_winner != "":
		_reset_match()
	var played: int = score["T"] + score["CT"]
	# yarim vaqt va qo'shimcha vaqt: tomonlar almashadi, pul qayta boshlanadi
	if played > 0 and played != _swapped_at:
		if played == half_len:
			_swap_sides(Rules.START_MONEY)
		elif played >= half_len * 2 and (played - half_len * 2) % Rules.OT_HALF == 0:
			var k: int = (played - half_len * 2) / Rules.OT_HALF
			if k == 0:
				_ot_money()
			else:
				_swap_sides(Rules.OT_MONEY)
		_swapped_at = played
	round_no += 1
	feed = []
	for d in get_tree().get_nodes_in_group("dropped_weapons"):
		d.queue_free()                     # CS2: yangi raundda yerdagi qurollar yo'qoladi
	_clear_bomb()
	_cancel_action()
	planter = null
	if not player.alive:
		player.revive()
	player.has_bomb = player.team == "T"
	bomb_state = "carried" if player.has_bomb else "none"
	planted_site = ""
	for c in combatants():
		c.loadout.round_start(c.team)
	if player.has_method("on_round_start"):
		player.on_round_start()
	_spawn_player(0)
	buy_time_left = R.buy_time
	player.frozen = true
	_set_phase(Phase.FREEZE, R.freeze)


func _reset_match() -> void:
	score = {"T": 0, "CT": 0}
	round_no = 0
	match_winner = ""
	win_target = int(R.win_rounds)
	_swapped_at = -1
	loss_count = {"T": Rules.START_LOSS, "CT": Rules.START_LOSS}
	for c in combatants():
		c.loadout.reset_match()


func _swap_sides(money: int) -> void:
	player.team = "CT" if player.team == "T" else "T"
	for c in combatants():
		c.loadout.strip_all()
		c.loadout.money = money
	loss_count = {"T": Rules.START_LOSS, "CT": Rules.START_LOSS}
	var s: int = score["T"]
	score["T"] = score["CT"]
	score["CT"] = s
	last_reason = "Tomonlar almashdi"


func _ot_money() -> void:
	for c in combatants():
		c.loadout.strip_all()
		c.loadout.money = Rules.OT_MONEY
	loss_count = {"T": Rules.START_LOSS, "CT": Rules.START_LOSS}


## winner: "T"/"CT"; code: elim / time / bomb / defuse (pul shunga qarab)
func end_round(winner: String, reason: String, code := "") -> void:
	if phase == Phase.ROUND_END:
		return
	if code == "":
		code = "bomb" if bomb_state == "exploded" else ("defuse" if bomb_state == "defused" else ("time" if reason.begins_with("Vaqt") else "elim"))
	_cancel_action()
	player.frozen = false
	score[winner] += 1
	last_winner = winner
	last_reason = reason
	_pay_round(winner, code)
	round_log.append({"round": round_no, "winner": winner, "reason": reason, "code": code})
	if score[winner] >= win_target:
		match_winner = winner
	elif score["T"] == win_target - 1 and score["CT"] == win_target - 1:
		win_target += Rules.OT_HALF          # qo'shimcha vaqt: yana 3 raund kerak (12:12 -> 16, 15:15 -> 19)
	_set_phase(Phase.ROUND_END, R.round_end)
	round_ended.emit(winner, reason)


func _pay_round(winner: String, code: String) -> void:
	var loser := "CT" if winner == "T" else "T"
	last_money = {}
	for c in combatants():
		var add := 0
		if c.team == winner:
			add = Rules.WIN_REWARD.get(code, 3250)
		else:
			add = Rules.loss_bonus(loss_count[loser])
			if loser == "T" and code == "time" and c.alive:
				add = 0                          # vaqt tugaganda tirik qolgan T lar pul olmaydi
			elif loser == "T" and planted_site != "":
				add += Rules.PLANT_TEAM_BONUS
		c.loadout.add_money(add)
		last_money[c] = add
	loss_count[winner] = maxi(0, loss_count[winner] - 1)
	loss_count[loser] = mini(Rules.LOSS_BONUS.size() - 1, loss_count[loser] + 1)


func _set_phase(p: int, t: float) -> void:
	phase = p
	time_left = t
	phase_changed.emit(p)


func _process(delta: float) -> void:
	buy_time_left = max(0.0, buy_time_left - delta)
	_pickup_cooldown = max(0.0, _pickup_cooldown - delta)
	match phase:
		Phase.FREEZE:
			time_left -= delta
			if time_left <= 0.0:
				player.frozen = false
				_set_phase(Phase.LIVE, R.round_time)
		Phase.LIVE:
			time_left -= delta
			if time_left <= 0.0:
				end_round("CT", "Vaqt tugadi — bomba o'rnatilmadi", "time")
		Phase.PLANTED:
			time_left -= delta
			if bomb:
				bomb.time_left = time_left
			if time_left <= 0.0:
				_explode()
		Phase.ROUND_END:
			time_left -= delta
			if time_left <= 0.0:
				start_round()
	_update_action(delta)
	_update_dropped_bomb()
	_update_pickups()
	if player.global_position.y < -10.0:
		_player_fell()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("debug_zones"):
		_set_debug(not debug_visible)
	elif event.is_action_pressed("debug_switch_team"):
		switch_team()
	elif event.is_action_pressed("debug_restart_round"):
		start_round()
	elif event.is_action_pressed("drop_bomb") and player.has_bomb and phase in [Phase.FREEZE, Phase.LIVE] \
			and player.get("fp_view") == null:           # o'yinchida fp_view bor — G ni o'sha boshqaradi (qurol yoki bomba)
		drop_bomb()


# ------------------------------------------------------------------ zonalar
func current_site() -> String:
	for a in get_tree().get_nodes_in_group("bomb_sites"):
		if (a as Area3D).overlaps_body(player):
			return str(a.get_meta("site"))
	return ""


## site'dagi o'rnatish aylanasi ichidami (bo'sh satr — yo'q)
func plant_circle_at(p: Vector3) -> String:
	for s in plant_spots:
		var c: Vector3 = plant_spots[s]
		if Vector2(p.x - c.x, p.z - c.z).length() <= Rules.PLANT_RADIUS and absf(p.y - c.y) < 1.6:
			return s
	return ""


func in_buy_zone() -> bool:
	if not player.alive or buy_time_left <= 0.0 or not (phase in [Phase.FREEZE, Phase.LIVE]):
		return false
	for a in get_tree().get_nodes_in_group("buy_zones"):
		if str(a.get_meta("team")) == player.team and (a as Area3D).overlaps_body(player):
			return true
	return false


func _find_plant_spots() -> void:
	for m in get_tree().get_nodes_in_group("ai_points"):
		var lbl := str(m.get_meta("label", ""))
		if lbl.ends_with(" plant"):
			plant_spots[lbl.substr(0, 1)] = (m as Node3D).global_position
	# aylana belgisi yerda (qizil halqa + ichida yarim shaffof doira)
	for s in plant_spots:
		var ring := MeshInstance3D.new()
		var tm := TorusMesh.new()
		tm.inner_radius = Rules.PLANT_RADIUS - 0.12
		tm.outer_radius = Rules.PLANT_RADIUS
		tm.rings = 48
		tm.ring_segments = 6
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(0.9, 0.15, 0.1)
		m.emission_enabled = true
		m.emission = Color(0.6, 0.05, 0.02)
		tm.material = m
		ring.mesh = tm
		ring.scale = Vector3(1, 0.15, 1)
		ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		ring.name = "PlantRing" + s
		get_parent().add_child.call_deferred(ring)
		ring.set_deferred("global_position", plant_spots[s] + Vector3.UP * 0.03)


# ------------------------------------------------------------------ o'rnatish / zararsizlantirish
func can_plant() -> bool:
	return player.alive and phase == Phase.LIVE and player.team == "T" and player.has_bomb \
		and player.is_on_floor() and plant_circle_at(player.global_position) != ""


func can_defuse() -> bool:
	return player.alive and phase == Phase.PLANTED and player.team == "CT" and bomb != null \
		and player.is_on_floor() and player.global_position.distance_to(bomb.global_position) < DEFUSE_RANGE


func _action_still_valid() -> bool:
	if action == "plant":
		return player.alive and phase == Phase.LIVE and player.has_bomb and plant_circle_at(player.global_position) != ""
	if action == "defuse":
		return player.alive and phase == Phase.PLANTED and bomb != null \
			and player.global_position.distance_to(bomb.global_position) < DEFUSE_RANGE
	return false


func _update_action(delta: float) -> void:
	var holding: bool = Input.is_action_pressed("interact") or bool(player.get("c4_fire"))
	if action != "" and (not holding or not _action_still_valid()):
		_cancel_action()
	if action == "" and holding:
		if can_plant():
			_begin_action("plant", R.plant_time)
		elif can_defuse():
			_begin_action("defuse", R.defuse_time_kit if (player.loadout.kit or has_defuse_kit) else R.defuse_time)
	if action != "":
		action_progress += delta
		if action == "plant":
			var d := mini(Rules.BOMB_CODE.length(), int(action_progress / action_duration * (Rules.BOMB_CODE.length() + 0.5)))
			if d > _digits:
				_digits = d
				_beep.pitch_scale = 1.6
				_beep.play()
		if action_progress >= action_duration:
			if action == "plant":
				_plant()
			else:
				_defuse(player)


## HUD uchun: terilayotgan kod ("735****")
func plant_code_shown() -> String:
	if action != "plant":
		return ""
	return Rules.BOMB_CODE.substr(0, _digits) + "*".repeat(Rules.BOMB_CODE.length() - _digits)


func _begin_action(kind: String, duration: float) -> void:
	action = kind
	action_progress = 0.0
	action_duration = duration
	_digits = 0
	player.busy = true


func _cancel_action() -> void:
	action = ""
	action_progress = 0.0
	_digits = 0
	player.busy = false


func _plant() -> void:
	var site := plant_circle_at(player.global_position)
	_cancel_action()
	player.has_bomb = false
	plant_bomb(player, player.global_position, site)


## bombani o'rnatish (o'yinchi yoki bot)
func plant_bomb(who: Node, pos: Vector3, site: String) -> void:
	_clear_bomb()
	bomb = BombScene.instantiate()
	get_parent().add_child(bomb)
	bomb.global_position = _floor_point(pos)
	bomb.plant(R.bomb_timer)
	bomb_state = "planted"
	planted_site = site
	planter = who
	if who and "loadout" in who:
		who.loadout.add_money(Rules.PLANT_REWARD)
	_set_phase(Phase.PLANTED, R.bomb_timer)
	bomb_event.emit("planted")


func _defuse(who: Node = null) -> void:
	if who == player:
		_cancel_action()
	if bomb:
		bomb.defuse()
	bomb_state = "defused"
	if who and "loadout" in who:
		who.loadout.add_money(Rules.DEFUSE_REWARD)
	bomb_event.emit("defused")
	end_round("CT", "Bomba zararsizlantirildi", "defuse")


func _explode() -> void:
	var center := bomb.global_position if bomb else Vector3.ZERO
	if bomb:
		bomb.explode()
	bomb_state = "exploded"
	bomb_event.emit("exploded")
	# zarar: masofa bo'yicha (CS2), zirh zararning yarmini oladi; bomba bilan o'lish — hech kimning hisobiga yozilmaydi
	if player.alive and player.global_position.distance_to(center) > Rules.BOMB_RADIUS:
		player.shake(0.3)                       # uzoqda ham yer silkinadi
	for c in combatants():
		if not c.alive:
			continue
		var d: float = (c.global_position + Vector3.UP).distance_to(center)
		var dmg: float = Rules.bomb_damage(d)
		if dmg <= 0.0:
			continue
		if c.loadout.armor > 0.0:
			var ad := minf(c.loadout.armor, dmg * 0.25)
			c.loadout.armor -= ad
			dmg *= 0.5
		if c == player:
			player.shake(clampf(1.4 - d / 50.0, 0.3, 1.4))
		var was: bool = c.alive
		c.damage(dmg, center)
		if was and not c.alive:
			_log_kill(null, c, "Bomba", false)
	end_round("T", "Bomba portladi", "bomb")


# ------------------------------------------------------------------ zarar va o'ldirish hisobi (combat.gd chaqiradi)
func record_damage(attacker: Node, victim: Node, dealt: float, weapon: Resource, zone: String, was_kill: bool) -> void:
	if attacker and attacker != victim and "loadout" in attacker and attacker.team != victim.team:
		var lo = attacker.loadout
		lo.damage += dealt
		lo.round_damage[victim] = lo.round_damage.get(victim, 0.0) + dealt
	if not was_kill:
		return
	var wname: String = weapon.weapon_name if weapon else "?"
	var head := zone == "head"
	if attacker and attacker != victim and "loadout" in attacker:
		attacker.loadout.kills += 1
		attacker.loadout.round_kills += 1
		if head:
			attacker.loadout.hs += 1
		if weapon:
			attacker.loadout.add_money(int(weapon.kill_reward))
	# assist: o'ldirmagan, lekin ≥ 41 zarar bergan jamoadoshlar
	for c in combatants():
		if c != attacker and c.team != victim.team and c.loadout.round_damage.get(victim, 0.0) >= Rules.ASSIST_DAMAGE:
			c.loadout.assists += 1
	_log_kill(attacker, victim, wname, head)


func _log_kill(attacker: Node, victim: Node, wname: String, head: bool) -> void:
	victim.loadout.deaths += 1
	victim.loadout.strip_all()
	if victim == player and player.has_bomb:
		pass                                  # bomba tashlanishi — bot_play/_on_player_died
	var e := {"killer": attacker.loadout.name if attacker else "", "killer_team": attacker.team if attacker else "",
		"victim": victim.loadout.name, "victim_team": victim.team, "weapon": wname, "head": head,
		"t": Time.get_ticks_msec() / 1000.0, "attacker": attacker, "victim_node": victim}
	feed.append(e)
	killed.emit(e)


# ------------------------------------------------------------------ qurol tashlash / olish (CS2)
## qurolni yerga tashlash (G yoki o'lganda)
func drop_weapon(who: Node, w: Resource, am: Array, pos: Vector3, vel: Vector3) -> Node:
	if w == null or w.kind in [2, 8]:
		return null                         # pichoq va Zeus tashlanmaydi
	return WeaponDrop.spawn(get_parent(), w, am, pos, vel, who)


## o'lganda: eng qimmat quroli (asosiy, bo'lmasa to'pponcha) yerga tushadi
func drop_best(c: Node) -> void:
	var lo = c.loadout
	if c == player and player.get("fp_view"):
		player.fp_view._save_ammo()
	var w: Resource = lo.primary if lo.primary else lo.secondary
	if w == null or not c.is_inside_tree():
		return
	var am: Array = lo.ammo.get(w.weapon_id, [w.magazine_size, w.reserve_ammo])
	var fwd: Vector3 = -c.global_transform.basis.z if c == player else Vector3(c.look_dir.x, 0, c.look_dir.z)
	drop_weapon(c, w, am, c.global_position + Vector3.UP * 1.1, fwd.normalized() * 1.5 + Vector3.UP * 1.0)


## qo'lga olish: shu turdagi joy bo'sh bo'lsa
func give_drop(c: Node, d: Node) -> void:
	var lo = c.loadout
	var w: Resource = d.weapon
	if w.slot == 1:
		lo.primary = w
	else:
		lo.secondary = w
	lo.ammo[w.weapon_id] = d.ammo.duplicate()
	d.remove_from_group("dropped_weapons")
	d.queue_free()
	weapon_picked.emit(c, w)
	if c == player and player.get("fp_view"):
		var fp = player.fp_view
		if fp.slot == 3 or fp.current == null:
			fp.equip(w.slot)                 # qo'li bo'sh (pichoq) bo'lsa — olgan qurolini darhol qo'lga oladi


## E: qarab turgan qurolni olish — qo'ldagi o'sha turdagi qurol yerga tushadi
func swap_pickup(c: Node, d: Node) -> void:
	var lo = c.loadout
	var w: Resource = d.weapon
	var old: Resource = lo.primary if w.slot == 1 else lo.secondary
	if old:
		if c == player and player.get("fp_view"):
			player.fp_view._save_ammo()
		var am: Array = lo.ammo.get(old.weapon_id, [old.magazine_size, old.reserve_ammo])
		lo.ammo.erase(old.weapon_id)
		drop_weapon(c, old, am, d.global_position + Vector3.UP * 0.3, Vector3.UP * 1.0)
		if w.slot == 1:
			lo.primary = null
		else:
			lo.secondary = null
	give_drop(c, d)
	if c == player and player.get("fp_view"):
		player.fp_view.current = null
		player.fp_view.equip(w.slot, true)


func _update_pickups() -> void:
	var drops := get_tree().get_nodes_in_group("dropped_weapons")
	if drops.is_empty():
		return
	for c in combatants():
		if not c.alive:
			continue
		var lo = c.loadout
		for d in drops:
			if not is_instance_valid(d) or d.is_queued_for_deletion() or (d.dropped_by == c and d.age < 1.5) or d.age < 0.4:
				continue
			var w: Resource = d.weapon
			if (w.slot == 1 and lo.primary != null) or (w.slot != 1 and lo.secondary != null):
				continue
			var dp: Vector3 = d.global_position
			if Vector2(c.global_position.x - dp.x, c.global_position.z - dp.z).length() < PICK_RANGE and absf(c.global_position.y + 0.3 - dp.y) < 1.4:
				give_drop(c, d)
				break


# ------------------------------------------------------------------ bombani tashlash / olish
func drop_bomb() -> void:
	if not player.has_bomb:
		return
	_cancel_action()
	player.has_bomb = false
	_clear_bomb()
	bomb = BombScene.instantiate()
	get_parent().add_child(bomb)
	var fwd := -player.global_transform.basis.z
	bomb.global_position = _floor_point(player.global_position + Vector3(fwd.x, 0, fwd.z).normalized() * 1.0)
	bomb_state = "dropped"
	_pickup_cooldown = 1.0
	bomb_event.emit("dropped")


func _update_dropped_bomb() -> void:
	if bomb_state != "dropped" or bomb == null or player.team != "T" or not player.alive or _pickup_cooldown > 0.0:
		return
	var d := Vector2(player.global_position.x - bomb.global_position.x, player.global_position.z - bomb.global_position.z)
	if d.length() < PICKUP_RANGE and absf(player.global_position.y - bomb.global_position.y) < 1.5:
		_clear_bomb()
		player.has_bomb = true
		bomb_state = "carried"
		bomb_event.emit("picked_up")


func _clear_bomb() -> void:
	if bomb and is_instance_valid(bomb):
		bomb.queue_free()
	bomb = null


# ------------------------------------------------------------------ yordamchilar
func switch_team() -> void:
	_cancel_action()
	if player.has_bomb:
		drop_bomb()
	player.team = "CT" if player.team == "T" else "T"
	player.loadout.round_start(player.team)
	if player.has_method("on_round_start"):
		player.on_round_start()
	_spawn_player(0)
	player.frozen = phase == Phase.FREEZE


func _spawn_player(slot: int) -> void:
	var spawns := get_tree().get_nodes_in_group("spawn_" + player.team)
	if spawns.is_empty():
		return
	var s := spawns[slot % spawns.size()] as Node3D
	player.teleport(s.global_transform)


func _player_fell() -> void:
	var loser: String = player.team
	if player.has_bomb:
		player.has_bomb = false
		bomb_state = "none"
	_spawn_player(0)
	if phase in [Phase.LIVE, Phase.PLANTED, Phase.FREEZE]:
		end_round("CT" if loser == "T" else "T", "O'yinchi xaritadan tushib ketdi", "elim")


func _floor_point(p: Vector3) -> Vector3:
	var space := player.get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(p + Vector3.UP * 0.5, p + Vector3.DOWN * 3.0, 1)
	var hit := space.intersect_ray(q)
	return hit.position + Vector3.UP * 0.02 if hit else p


func _set_debug(v: bool) -> void:
	debug_visible = v
	for n in get_tree().get_nodes_in_group("debug_viz"):
		n.visible = v


func skip_freeze() -> void:
	if phase == Phase.FREEZE:
		time_left = 0.0
