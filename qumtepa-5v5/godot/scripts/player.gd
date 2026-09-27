extends CharacterBody3D
## O'yinchi: harakat, sekin yurish, o'tirish, sakrash, sirt turiga qarab qadam tovushi, jamoa va bomba holati.
## Fizika: qatlam 4 (players), niqob 1+2 (world + player_clip).
## Tezliklar (CS ga o'xshash): oddiy harakat 4.5 m/s — qadam eshitiladi;
##   Shift — sekin yurish 2.3 m/s, qadam tovushi YO'Q; Ctrl/C — o'tirish 1.55 m/s, qadam tovushi YO'Q;
##   sakrash (Space) — qo'nishda tovush bor. O'tirganda bo'y 1.8 -> 1.25 m, ko'z 1.65 -> 1.08 m;
##   ustida shift bo'lsa (past tom), turib bo'lmaydi.
## Qurol: birinchi shaxsda qo'llar va qurol (fp_view.gd): 1/2/3 — avtomat/to'pponcha/pichoq, chap tugma — o'q,
##   o'ng tugma — nishonga olish (ADS), R — qayta o'qlash, X — o'q rejimi, B — sotib olish.
## Ko'rinish ajratilgan:
##   o'yinchining O'Z kamerasi — 1-shaxs: faqat qo'llar va qurol (Camera3D/FPView); o'z tanasi ko'rinmaydi, faqat soyasi;
##   BOSHQA har qanday kamera (tomoshabin, boshqa o'yinchi, bot kamerasi) — 3-shaxs: to'liq tana (Body), qurol qo'lda,
##   yurish/o'tirish/sakrash animatsiyalari, qayerga qarab turgani (tana egiladi), o'q uzish va qayta o'qlash.
## local_player=false — masofaviy (tarmoqdagi) o'yinchi: 1-shaxs ko'rinishi va klaviatura yo'q, faqat 3-shaxs tana.

signal footstep(surface: String)
signal fired                 ## o'q uzildi (fp_view.gd) — botlar eshitadi
signal damaged(amount: float, from_pos: Vector3)
signal died

@export var speed := 4.5
@export var walk_speed := 2.3
@export var crouch_speed := 1.55
@export var allow_sprint := false  ## raqobat rejimida o'chiq: barcha vaqtlar 4.5 m/s ga hisoblangan
@export var sprint_speed := 7.0
@export var jump_velocity := 4.8
@export var mouse_sensitivity := 0.0025
@export var local_player := true

const STAND_H := 1.8
const CROUCH_H := 1.25
const EYE_STAND := 1.65
const EYE_CROUCH := 1.08
const STEP_INTERVAL := 0.3        ## yugurish animatsiyasining yarim sikli (0.6 s / 2) — qadam tovushi oyoq tekkanda

var team := "T"
var has_bomb := false
var frozen := false   ## tayyorgarlik vaqtida harakat yo'q
var busy := false     ## bomba o'rnatish / zararsizlantirish paytida harakat yo'q
## Botlar va avtomatik testlar uchun: nol bo'lmasa, klaviatura o'rniga shu yo'nalish ishlatiladi.
var ai_move := Vector3.ZERO
## testlar uchun: klaviaturasiz sekin yurish / o'tirishni majburlash
var force_walk := false
var force_crouch := false
## sichqoncha sezgirligi ko'paytuvchisi (ADS da kamayadi — fp_view.gd)
var look_scale := 1.0
## jang (botlar bilan o'yin — bot_play.gd): sog'liq, o'lim; raund boshida qayta tiriladi
var hp := 100.0
var alive := true
var idx := 0
var carrier := false
## CS2: jihozlar va statistika (pul, qurollar, zirh, granatalar, K/D/A) — loadout.gd
var loadout = preload("res://scripts/loadout.gd").new()
## qurolga qarab tezlik (CS2: pichoq 1.0, AK 0.86, AWP 0.8) — fp_view.gd
var speed_mult := 1.0
var _tag_until := 0.0                 ## o'q tekkanda sekinlashish (CS2 tagging)
## 5-slotda bomba va chap tugma bosib turilgan (game_mode o'rnatish uchun E bilan bir xil ko'radi)
var c4_fire := false
## ekran silkinishi (bomba, granata) va flesh (oq ekran) — hud.gd chizadi
var flash_until := 0.0
var flash_total := 1.0
var _shake := 0.0

var walking := false
var crouching := false
var steps_played := 0
var lands_played := 0

const STEP_SOUNDS := {
	"stone": preload("res://audio/step_stone.wav"),
	"wood": preload("res://audio/step_wood.wav"),
	"metal": preload("res://audio/step_metal.wav"),
	"cloth": preload("res://audio/step_cloth.wav"),
}

@onready var cam: Camera3D = $Camera3D
@onready var floor_ray: RayCast3D = $FloorRay
@onready var steps: AudioStreamPlayer3D = $Steps
@onready var shape_node: CollisionShape3D = $CollisionShape3D
@onready var body: Node3D = get_node_or_null("Body")       ## 3-shaxs tana (boshqalarga ko'rinadi)
@onready var fp_view: Node3D = get_node_or_null("Camera3D/FPView")

var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _step_timer := 0.0
var _eye := EYE_STAND
var _was_floor := true
var _air_time := 0.0
var _capsule: CapsuleShape3D
var _stand_query: PhysicsShapeQueryParameters3D


func _ready() -> void:
	preload("res://scripts/input_setup.gd").ensure()
	_ensure_extra_input()
	if local_player and DisplayServer.get_name() != "headless":
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	_capsule = (shape_node.shape as CapsuleShape3D).duplicate()
	shape_node.shape = _capsule
	var stand := CapsuleShape3D.new()
	stand.radius = _capsule.radius
	stand.height = STAND_H
	_stand_query = PhysicsShapeQueryParameters3D.new()
	_stand_query.shape = stand
	_stand_query.collision_mask = 1 | 2
	_stand_query.exclude = [get_rid()]
	var CM := preload("res://scripts/character_model.gd")
	if local_player:
		# o'z kamerasi o'z tanasini ko'rmaydi (11-qatlam), 1-shaxs qo'llarini ko'radi (12-qatlam)
		cam.cull_mask = (cam.cull_mask & ~CM.LAYER_OWN_BODY) | CM.LAYER_VIEWMODEL
	else:
		if fp_view:
			fp_view.queue_free()
			fp_view = null
		cam.current = false
	if body and not local_player and body.own_body:
		body.own_body = false
		body.load_model(team)


static func _ensure_extra_input() -> void:
	var extra := {"walk": [KEY_SHIFT], "crouch": [KEY_CTRL, KEY_C], "reload": [KEY_R]}
	for action in extra:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action)
		for key in extra[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
	if not InputMap.has_action("fire"):
		InputMap.add_action("fire")
		var mb := InputEventMouseButton.new()
		mb.button_index = MOUSE_BUTTON_LEFT
		InputMap.action_add_event("fire", mb)


func _unhandled_input(event: InputEvent) -> void:
	if not local_player:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity * look_scale)
		cam.rotate_x(-event.relative.y * mouse_sensitivity * look_scale)
		cam.rotation.x = clamp(cam.rotation.x, -1.45, 1.45)
	elif event is InputEventKey and event.pressed and event.keycode == KEY_F10 and ResourceLoader.exists("res://menu.tscn"):
		get_tree().change_scene_to_file("res://menu.tscn")      # bosh menyu (xarita tanlash)
	elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


## tik turish mumkinmi (tepada to'siq yo'qmi)
func can_stand() -> bool:
	_stand_query.transform = Transform3D(Basis(), global_position + Vector3.UP * (STAND_H / 2 + 0.02))
	return get_world_3d().direct_space_state.intersect_shape(_stand_query, 1).is_empty()


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta
	var locked := frozen or busy or not alive
	var keyboard := ai_move == Vector3.ZERO and local_player
	# o'tirish: tugma bosilgan yoki tepada past tom bo'lsa
	var want_crouch := force_crouch or (keyboard and Input.is_action_pressed("crouch"))
	if want_crouch != crouching:
		if want_crouch or can_stand():
			_set_crouch(want_crouch)
	walking = force_walk or (keyboard and Input.is_action_pressed("walk") and not allow_sprint)
	if keyboard and alive and is_on_floor() and not locked and Input.is_action_just_pressed("jump"):
		velocity.y = jump_velocity
		if body:
			body.jump()

	var dir := Vector3.ZERO
	if not locked:
		if ai_move != Vector3.ZERO:
			dir = Vector3(ai_move.x, 0, ai_move.z).normalized()
		elif local_player:
			var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
			dir = (transform.basis * Vector3(input.x, 0, input.y)).normalized()
	var s := speed
	if crouching:
		s = crouch_speed
	elif walking:
		s = walk_speed
	elif allow_sprint and Input.is_action_pressed("sprint"):
		s = sprint_speed
	s *= speed_mult
	# CS2 "tagging": o'q tekkandan keyin qisqa vaqt sekinlashadi (0.4 s da asta tiklanadi)
	var tag_left: float = _tag_until - Time.get_ticks_msec() / 1000.0
	if tag_left > 0.0:
		s *= lerpf(1.0, 0.45, clampf(tag_left / 0.4, 0.0, 1.0))
	velocity.x = dir.x * s
	velocity.z = dir.z * s
	var air_vy := velocity.y
	move_and_slide()
	# kamera balandligi o'tirishga qarab silliq o'zgaradi
	_eye = lerpf(_eye, EYE_CROUCH if crouching else EYE_STAND, 1.0 - exp(-delta * 12.0))
	cam.position.y = _eye
	if _shake > 0.0:
		_shake = maxf(0.0, _shake - delta * 1.2)
		cam.h_offset = randf_range(-1.0, 1.0) * _shake * 0.06
		cam.v_offset = randf_range(-1.0, 1.0) * _shake * 0.06
	elif cam.h_offset != 0.0:
		cam.h_offset = 0.0
		cam.v_offset = 0.0
	_update_footsteps(delta, air_vy)
	_update_body()


## 3-shaxs tana o'yinchi holatiga ergashadi (boshqa kameralar shuni ko'radi)
func _update_body() -> void:
	if body == null:
		return
	if body.team != team:
		body.load_model(team)
	var v: Vector3 = global_transform.basis.inverse() * velocity
	body.velocity_local = Vector3(-v.x, 0, -v.z)      # tana 180° burilgan: +Z — o'yinchining oldi
	body.crouching = crouching
	body.on_floor = is_on_floor()
	body.planting = busy
	body.aim_pitch = cam.rotation.x


func _set_crouch(c: bool) -> void:
	crouching = c
	_capsule.height = CROUCH_H if c else STAND_H
	shape_node.position.y = _capsule.height / 2.0


## Qadam tovushi faqat oddiy harakatda (4.5 m/s). Sekin yurish (Shift) va o'tirib yurish — jim.
## Sakrab qo'nganda (≥ 0.25 s havoda) har doim tovush bor.
func _update_footsteps(delta: float, air_vy: float) -> void:
	var hs := Vector2(velocity.x, velocity.z).length()
	var on_floor := is_on_floor()
	if not on_floor:
		_air_time += delta
	if on_floor and not _was_floor and _air_time > 0.25 and air_vy < -2.0:
		_play_step(1.0)
		lands_played += 1
	if on_floor:
		_air_time = 0.0
	_was_floor = on_floor
	var loud := not walking and not crouching
	if on_floor and hs > 1.0 and loud:
		_step_timer -= delta
		if _step_timer <= 0.0:
			_step_timer = STEP_INTERVAL * speed / hs
			_play_step(randf_range(0.9, 1.1))
			steps_played += 1
	else:
		_step_timer = 0.0 if loud else STEP_INTERVAL * 0.5


func _play_step(pitch: float) -> void:
	var surf := surface_under()
	steps.stream = STEP_SOUNDS.get(surf, STEP_SOUNDS["stone"])
	steps.pitch_scale = pitch
	steps.play()
	footstep.emit(surf)


## Oyoq ostidagi sirt: "stone", "wood", "metal" yoki "cloth" (StaticBody3D metadata/surface dan).
func surface_under() -> String:
	if floor_ray.is_colliding():
		var c := floor_ray.get_collider()
		if c and c.has_meta("surface"):
			return str(c.get_meta("surface"))
	return "stone"


func teleport(xform: Transform3D) -> void:
	global_transform = xform
	velocity = Vector3.ZERO
	cam.rotation.x = 0.0
	if crouching:
		_set_crouch(false)


# ------------------------------------------------------------------ jang
func eye() -> Vector3:
	return global_position + Vector3.UP * cam.position.y


## zarar (botlar o'qi): true — o'ldi
func damage(amount: float, from_pos := Vector3.ZERO) -> bool:
	if not alive or amount <= 0.0:
		return false
	hp -= amount
	_tag_until = Time.get_ticks_msec() / 1000.0 + 0.4
	damaged.emit(amount, from_pos)
	if hp <= 0.0:
		die()
		return true
	return false


## o'q zonasi orqali: zirh va kaska hisobga olinadi (combat.gd), o'z jamoasiga zarar yo'q
func take_hit(amount: float, zone: String, from: Node, weapon: Resource = null) -> bool:
	return preload("res://scripts/combat.gd").hit(self, amount, zone, from, weapon)


## raund boshi (game_mode.gd): qurol tanlash
func on_round_start() -> void:
	if fp_view and fp_view.has_method("on_round_start"):
		fp_view.on_round_start()


func die() -> void:
	if not alive:
		return
	alive = false
	hp = 0.0
	busy = false
	velocity = Vector3.ZERO
	collision_layer = 0
	var gm := get_tree().get_first_node_in_group("game_mode") if is_inside_tree() else null
	if gm and loadout:
		gm.drop_best(self)              # CS2: eng yaxshi quroli yerga tushadi
	if loadout:
		loadout.strip_all()             # CS2: o'lsa qurol, zirh, granatalar yo'qoladi
	if crouching:
		_set_crouch(false)
	if body:
		body.die()
	died.emit()


func revive() -> void:
	alive = true
	hp = 100.0
	collision_layer = 8
	if body:
		body.revive()


func shake(amount: float) -> void:
	_shake = maxf(_shake, amount)


## flesh ko'r qildi (grenade.gd): d soniya oq ekran (asta so'nadi)
func flashed(d: float) -> void:
	var now := Time.get_ticks_msec() / 1000.0
	if now + d > flash_until:
		flash_until = now + d
		flash_total = d


func blind_amount() -> float:
	var left := flash_until - Time.get_ticks_msec() / 1000.0
	if left <= 0.0:
		return 0.0
	return clampf(left / minf(flash_total, 2.0), 0.0, 1.0)
