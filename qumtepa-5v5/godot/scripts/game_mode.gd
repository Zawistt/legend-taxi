extends Node
## Raund tizimi: TAYYORGARLIK -> JANG -> (BOMBA O'RNATILDI) -> RAUND OXIRI.
## T: bomba bilan site zonasida E ni bosib turadi (plant_time).
## CT: o'rnatilgan bomba yonida E ni bosib turadi (defuse_time).
## Debug: F1 zonalar, F2 jamoani almashtirish, F3 raundni qayta boshlash.
## Qoidalar (vaqtlar) map_data.gd dagi ROUND lug'atida.

signal phase_changed(phase: int)
signal round_ended(winner: String, reason: String)
signal bomb_event(event: String)

enum Phase { FREEZE, LIVE, PLANTED, ROUND_END }

const MapData := preload("res://scripts/map_data.gd")
const BombScene := preload("res://scenes/bomb.tscn")
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
var action := ""           ## "plant" yoki "defuse"
var action_progress := 0.0
var action_duration := 1.0
var last_winner := ""
var last_reason := ""
var match_winner := ""
var debug_visible := false
var has_defuse_kit := false  ## keyinchalik sotib olish menyusidan
var _pickup_cooldown := 0.0


func _ready() -> void:
	preload("res://scripts/input_setup.gd").ensure()
	var nav := get_node_or_null(^"../Navigation") as NavigationRegion3D
	if nav and nav.navigation_mesh and nav.navigation_mesh.get_polygon_count() == 0:
		nav.bake_navigation_mesh(false)
	player.team = start_team
	_set_debug(false)
	start_round()


# ------------------------------------------------------------------ raund oqimi
func start_round() -> void:
	if match_winner != "":
		score = {"T": 0, "CT": 0}
		round_no = 0
		match_winner = ""
	round_no += 1
	_clear_bomb()
	_cancel_action()
	player.has_bomb = player.team == "T"
	bomb_state = "carried" if player.has_bomb else "none"
	planted_site = ""
	_spawn_player(0)
	buy_time_left = R.buy_time
	player.frozen = true
	_set_phase(Phase.FREEZE, R.freeze)


func end_round(winner: String, reason: String) -> void:
	if phase == Phase.ROUND_END:
		return
	_cancel_action()
	player.frozen = false
	score[winner] += 1
	last_winner = winner
	last_reason = reason
	if score[winner] >= R.win_rounds:
		match_winner = winner
	_set_phase(Phase.ROUND_END, R.round_end)
	round_ended.emit(winner, reason)


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
				end_round("CT", "Vaqt tugadi — bomba o'rnatilmadi")
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
	if player.global_position.y < -10.0:
		_player_fell()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("debug_zones"):
		_set_debug(not debug_visible)
	elif event.is_action_pressed("debug_switch_team"):
		switch_team()
	elif event.is_action_pressed("debug_restart_round"):
		start_round()
	elif event.is_action_pressed("drop_bomb") and player.has_bomb and phase in [Phase.FREEZE, Phase.LIVE]:
		drop_bomb()


# ------------------------------------------------------------------ zonalar
func current_site() -> String:
	for a in get_tree().get_nodes_in_group("bomb_sites"):
		if (a as Area3D).overlaps_body(player):
			return str(a.get_meta("site"))
	return ""


func in_buy_zone() -> bool:
	if buy_time_left <= 0.0 or not (phase in [Phase.FREEZE, Phase.LIVE]):
		return false
	for a in get_tree().get_nodes_in_group("buy_zones"):
		if str(a.get_meta("team")) == player.team and (a as Area3D).overlaps_body(player):
			return true
	return false


# ------------------------------------------------------------------ o'rnatish / zararsizlantirish
func can_plant() -> bool:
	return player.alive and phase == Phase.LIVE and player.team == "T" and player.has_bomb \
		and player.is_on_floor() and current_site() != ""


func can_defuse() -> bool:
	return player.alive and phase == Phase.PLANTED and player.team == "CT" and bomb != null \
		and player.is_on_floor() and player.global_position.distance_to(bomb.global_position) < DEFUSE_RANGE


func _action_still_valid() -> bool:
	if action == "plant":
		return phase == Phase.LIVE and player.has_bomb and current_site() != ""
	if action == "defuse":
		return phase == Phase.PLANTED and bomb != null \
			and player.global_position.distance_to(bomb.global_position) < DEFUSE_RANGE
	return false


func _update_action(delta: float) -> void:
	var holding := Input.is_action_pressed("interact")
	if action != "" and (not holding or not _action_still_valid()):
		_cancel_action()
	if action == "" and holding:
		if can_plant():
			_begin_action("plant", R.plant_time)
		elif can_defuse():
			_begin_action("defuse", R.defuse_time_kit if has_defuse_kit else R.defuse_time)
	if action != "":
		action_progress += delta
		if action_progress >= action_duration:
			if action == "plant":
				_plant()
			else:
				_defuse()


func _begin_action(kind: String, duration: float) -> void:
	action = kind
	action_progress = 0.0
	action_duration = duration
	player.busy = true


func _cancel_action() -> void:
	action = ""
	action_progress = 0.0
	player.busy = false


func _plant() -> void:
	var site := current_site()
	_cancel_action()
	player.has_bomb = false
	bomb = BombScene.instantiate()
	get_parent().add_child(bomb)
	bomb.global_position = _floor_point(player.global_position)
	bomb.plant(R.bomb_timer)
	bomb_state = "planted"
	planted_site = site
	_set_phase(Phase.PLANTED, R.bomb_timer)
	bomb_event.emit("planted")


func _defuse() -> void:
	_cancel_action()
	bomb.defuse()
	bomb_state = "defused"
	bomb_event.emit("defused")
	end_round("CT", "Bomba zararsizlantirildi")


func _explode() -> void:
	if bomb:
		bomb.explode()
	bomb_state = "exploded"
	bomb_event.emit("exploded")
	end_round("T", "Bomba portladi")


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
		end_round("CT" if loser == "T" else "T", "O'yinchi xaritadan tushib ketdi")


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
