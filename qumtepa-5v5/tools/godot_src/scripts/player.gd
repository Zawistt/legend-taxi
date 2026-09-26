extends CharacterBody3D
## O'yinchi: harakat, sekin yurish, o'tirish, sakrash, sirt turiga qarab qadam tovushi, jamoa va bomba holati.
## Fizika: qatlam 4 (players), niqob 1+2 (world + player_clip).
## Tezliklar (CS ga o'xshash): oddiy harakat 4.5 m/s — qadam eshitiladi;
##   Shift — sekin yurish 2.3 m/s, qadam tovushi YO'Q; Ctrl/C — o'tirish 1.55 m/s, qadam tovushi YO'Q;
##   sakrash (Space) — qo'nishda tovush bor. O'tirganda bo'y 1.8 -> 1.25 m, ko'z 1.65 -> 1.08 m;
##   ustida shift bo'lsa (past tom), turib bo'lmaydi.
## Qurol: birinchi shaxsda qo'llar va qurol (T — AKM, CT — M416). Sichqoncha chap tugmasi — o'q uzish, R — qayta o'qlash.

signal footstep(surface: String)

@export var speed := 4.5
@export var walk_speed := 2.3
@export var crouch_speed := 1.55
@export var allow_sprint := false  ## raqobat rejimida o'chiq: barcha vaqtlar 4.5 m/s ga hisoblangan
@export var sprint_speed := 7.0
@export var jump_velocity := 4.8
@export var mouse_sensitivity := 0.0025

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
	if DisplayServer.get_name() != "headless":
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
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity)
		cam.rotate_x(-event.relative.y * mouse_sensitivity)
		cam.rotation.x = clamp(cam.rotation.x, -1.45, 1.45)
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
	var locked := frozen or busy
	var keyboard := ai_move == Vector3.ZERO
	# o'tirish: tugma bosilgan yoki tepada past tom bo'lsa
	var want_crouch := force_crouch or (keyboard and Input.is_action_pressed("crouch"))
	if want_crouch != crouching:
		if want_crouch or can_stand():
			_set_crouch(want_crouch)
	walking = force_walk or (keyboard and Input.is_action_pressed("walk") and not allow_sprint)
	if is_on_floor() and not locked and Input.is_action_just_pressed("jump"):
		velocity.y = jump_velocity

	var dir := Vector3.ZERO
	if not locked:
		if ai_move != Vector3.ZERO:
			dir = Vector3(ai_move.x, 0, ai_move.z).normalized()
		else:
			var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
			dir = (transform.basis * Vector3(input.x, 0, input.y)).normalized()
	var s := speed
	if crouching:
		s = crouch_speed
	elif walking:
		s = walk_speed
	elif allow_sprint and Input.is_action_pressed("sprint"):
		s = sprint_speed
	velocity.x = dir.x * s
	velocity.z = dir.z * s
	var air_vy := velocity.y
	move_and_slide()
	# kamera balandligi o'tirishga qarab silliq o'zgaradi
	_eye = lerpf(_eye, EYE_CROUCH if crouching else EYE_STAND, 1.0 - exp(-delta * 12.0))
	cam.position.y = _eye
	_update_footsteps(delta, air_vy)


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
