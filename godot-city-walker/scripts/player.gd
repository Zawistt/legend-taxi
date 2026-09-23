extends CharacterBody3D

const DRAGON_SCENE_PATH := "res://assets/dragon_character.glb"

@export var target_height: float = 2.6
@export var walk_speed: float = 4.5
@export var run_speed: float = 9.0
@export var jump_velocity: float = 7.0
@export var turn_speed: float = 8.0
@export var mouse_sensitivity: float = 0.0035
@export var camera_min_pitch: float = -1.2
@export var camera_max_pitch: float = 0.35

var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _camera_yaw: float = 0.0
var _camera_pitch: float = -0.35
var _anim_player: AnimationPlayer = null
var _anim_name: String = ""
var _found_any_mesh := false
var _aabb_result := AABB()

@onready var model_root: Node3D = $ModelRoot
@onready var camera_pivot: Node3D = $CameraPivot
@onready var spring_arm: SpringArm3D = $CameraPivot/SpringArm3D
@onready var camera: Camera3D = $CameraPivot/SpringArm3D/Camera3D
@onready var collision_shape: CollisionShape3D = $CollisionShape3D


func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	camera.current = true

	spring_arm.spring_length = 6.0
	spring_arm.collision_mask = 1
	var arm_shape := SphereShape3D.new()
	arm_shape.radius = 0.35
	spring_arm.shape = arm_shape
	spring_arm.margin = 0.05

	_load_dragon()
	camera_pivot.rotation = Vector3(_camera_pitch, _camera_yaw, 0.0)


func _load_dragon() -> void:
	var packed: PackedScene = load(DRAGON_SCENE_PATH)
	var model := packed.instantiate()
	model_root.add_child(model)

	_found_any_mesh = false
	_aabb_result = AABB()
	_collect_aabb(model, model.transform)

	if _found_any_mesh and _aabb_result.size.y > 0.001:
		var scale_factor: float = target_height / _aabb_result.size.y
		model_root.scale = Vector3.ONE * scale_factor

		var center_x: float = _aabb_result.position.x + _aabb_result.size.x * 0.5
		var center_z: float = _aabb_result.position.z + _aabb_result.size.z * 0.5
		var bottom_y: float = _aabb_result.position.y

		model_root.position = Vector3(
			-center_x * scale_factor,
			-bottom_y * scale_factor,
			-center_z * scale_factor
		)

		var radius: float = max(_aabb_result.size.x, _aabb_result.size.z) * 0.5 * scale_factor * 0.55
		radius = clamp(radius, 0.35, target_height * 0.4)
		var height: float = max(target_height, radius * 2.0)

		var capsule := CapsuleShape3D.new()
		capsule.radius = radius
		capsule.height = height
		collision_shape.shape = capsule
		collision_shape.position.y = height * 0.5

		spring_arm.position.y = target_height * 0.75
	else:
		var capsule := CapsuleShape3D.new()
		capsule.radius = 0.6
		capsule.height = target_height
		collision_shape.shape = capsule
		collision_shape.position.y = target_height * 0.5
		spring_arm.position.y = target_height * 0.75

	_anim_player = _find_animation_player(model)
	if _anim_player:
		var names: PackedStringArray = _anim_player.get_animation_list()
		if names.size() > 0:
			_anim_name = names[0]
			var anim: Animation = _anim_player.get_animation(_anim_name)
			anim.loop_mode = Animation.LOOP_LINEAR
			_anim_player.play(_anim_name)
			_anim_player.speed_scale = 0.5


func _collect_aabb(node: Node, transform_so_far: Transform3D) -> void:
	var my_transform := transform_so_far
	if node is VisualInstance3D:
		var local_aabb: AABB = node.get_aabb()
		var world_aabb: AABB = my_transform * local_aabb
		if not _found_any_mesh:
			_aabb_result = world_aabb
			_found_any_mesh = true
		else:
			_aabb_result = _aabb_result.merge(world_aabb)
	for child in node.get_children():
		if child is Node3D:
			_collect_aabb(child, my_transform * child.transform)


func _find_animation_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node
	for child in node.get_children():
		var found := _find_animation_player(child)
		if found:
			return found
	return null


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_camera_yaw -= event.relative.x * mouse_sensitivity
		_camera_pitch = clamp(_camera_pitch - event.relative.y * mouse_sensitivity, camera_min_pitch, camera_max_pitch)
		camera_pivot.rotation = Vector3(_camera_pitch, _camera_yaw, 0.0)

	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_ESCAPE:
			if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
				Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
			else:
				Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

	if event is InputEventMouseButton and event.pressed:
		if Input.mouse_mode == Input.MOUSE_MODE_VISIBLE:
			Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= _gravity * delta

	var forward_input := 0.0
	var strafe_input := 0.0
	if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP):
		forward_input += 1.0
	if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN):
		forward_input -= 1.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT):
		strafe_input += 1.0
	if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT):
		strafe_input -= 1.0

	var yaw_basis := Basis(Vector3.UP, _camera_yaw)
	var forward: Vector3 = -yaw_basis.z
	var right: Vector3 = yaw_basis.x
	var move_dir: Vector3 = (forward * forward_input + right * strafe_input)
	if move_dir.length() > 1.0:
		move_dir = move_dir.normalized()

	var running: bool = Input.is_physical_key_pressed(KEY_SHIFT)
	var speed: float = run_speed if running else walk_speed

	velocity.x = move_dir.x * speed
	velocity.z = move_dir.z * speed

	if Input.is_physical_key_pressed(KEY_SPACE) and is_on_floor():
		velocity.y = jump_velocity

	if move_dir.length() > 0.05:
		var target_angle: float = atan2(move_dir.x, move_dir.z)
		model_root.rotation.y = lerp_angle(model_root.rotation.y, target_angle, 1.0 - exp(-turn_speed * delta))

	move_and_slide()

	if _anim_player:
		var horizontal_speed: float = Vector2(velocity.x, velocity.z).length()
		var speed_ratio: float = clamp(horizontal_speed / run_speed, 0.0, 1.0)
		_anim_player.speed_scale = lerp(0.45, 1.4, speed_ratio)
