extends CharacterBody3D
## O'yinchi: harakat, sakrash, sirt turiga qarab qadam tovushi, jamoa va bomba holati.
## Fizika: qatlam 4 (players), niqob 1+2 (world + player_clip).

signal footstep(surface: String)

@export var speed := 4.5
@export var allow_sprint := false  ## raqobat rejimida o'chiq: barcha vaqtlar 4.5 m/s ga hisoblangan
@export var sprint_speed := 7.0
@export var jump_velocity := 4.8
@export var mouse_sensitivity := 0.0025

var team := "T"
var has_bomb := false
var frozen := false   ## tayyorgarlik vaqtida harakat yo'q
var busy := false     ## bomba o'rnatish / zararsizlantirish paytida harakat yo'q
## Botlar va avtomatik testlar uchun: nol bo'lmasa, klaviatura o'rniga shu yo'nalish ishlatiladi.
var ai_move := Vector3.ZERO

const STEP_SOUNDS := {
	"stone": preload("res://audio/step_stone.wav"),
	"wood": preload("res://audio/step_wood.wav"),
	"metal": preload("res://audio/step_metal.wav"),
	"cloth": preload("res://audio/step_cloth.wav"),
}

@onready var cam: Camera3D = $Camera3D
@onready var floor_ray: RayCast3D = $FloorRay
@onready var steps: AudioStreamPlayer3D = $Steps

var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _step_timer := 0.0


func _ready() -> void:
	preload("res://scripts/input_setup.gd").ensure()
	if DisplayServer.get_name() != "headless":
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity)
		cam.rotate_x(-event.relative.y * mouse_sensitivity)
		cam.rotation.x = clamp(cam.rotation.x, -1.45, 1.45)
	elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseButton and event.pressed:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta
	var locked := frozen or busy
	if is_on_floor() and not locked and Input.is_action_just_pressed("jump"):
		velocity.y = jump_velocity

	var dir := Vector3.ZERO
	if not locked:
		if ai_move != Vector3.ZERO:
			dir = Vector3(ai_move.x, 0, ai_move.z).normalized()
		else:
			var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
			dir = (transform.basis * Vector3(input.x, 0, input.y)).normalized()
	var s := sprint_speed if (allow_sprint and Input.is_action_pressed("sprint")) else speed
	velocity.x = dir.x * s
	velocity.z = dir.z * s
	move_and_slide()
	_update_footsteps(delta)


func _update_footsteps(delta: float) -> void:
	var hs := Vector2(velocity.x, velocity.z).length()
	if is_on_floor() and hs > 1.0:
		_step_timer -= delta
		if _step_timer <= 0.0:
			_step_timer = 0.42 * speed / hs
			var surf := surface_under()
			steps.stream = STEP_SOUNDS.get(surf, STEP_SOUNDS["stone"])
			steps.pitch_scale = randf_range(0.9, 1.1)
			steps.play()
			footstep.emit(surf)
	else:
		_step_timer = 0.0


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
