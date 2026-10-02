class_name RtsCamera
extends Node3D
## Classic RTS rig: pivot on the ground (follows terrain height), pitched camera
## on a boom. WASD / screen-edge pan, Q/E rotate, mouse wheel zoom, MMB drag rotate.
## Optional: assign `terrain` (TerrainManager) to clamp to the map and follow height.

@export var terrain: TerrainManager
@export var pan_speed := 55.0             # m/s at default zoom; scales with zoom
@export var edge_pan := true
@export var edge_margin := 12.0
@export var rotate_speed := 1.6
@export var zoom_min := 12.0              # workers/buildings fill the screen
@export var zoom_max := 330.0             # whole ~360 m battlefield in view
@export var zoom_step := 0.12
@export var pitch_deg := -52.0
@export var map_limit := 195.0

var _zoom := 110.0
var _target_zoom := 110.0
var _yaw := 0.0
var _cam: Camera3D


func _ready() -> void:
	_cam = Camera3D.new()
	_cam.fov = 40.0
	_cam.near = 0.3
	_cam.far = 1500.0
	add_child(_cam)
	_apply()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_target_zoom *= 1.0 - zoom_step
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_target_zoom *= 1.0 + zoom_step
		_target_zoom = clampf(_target_zoom, zoom_min, zoom_max)
	elif event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_MIDDLE):
		_yaw -= event.relative.x * 0.005


func _process(delta: float) -> void:
	var dir := Vector2(
			Input.get_axis("cam_left", "cam_right"),
			Input.get_axis("cam_forward", "cam_back"))
	if edge_pan and dir == Vector2.ZERO:
		var vp := get_viewport()
		var m := vp.get_mouse_position()
		var s := vp.get_visible_rect().size
		if Rect2(Vector2.ZERO, s).has_point(m):
			if m.x < edge_margin: dir.x -= 1.0
			elif m.x > s.x - edge_margin: dir.x += 1.0
			if m.y < edge_margin: dir.y -= 1.0
			elif m.y > s.y - edge_margin: dir.y += 1.0
	_yaw += Input.get_axis("cam_rotate_left", "cam_rotate_right") * rotate_speed * delta
	_zoom = lerpf(_zoom, _target_zoom, 1.0 - exp(-10.0 * delta))

	if dir != Vector2.ZERO:
		var speed := pan_speed * (_zoom / 110.0) * delta
		var move := Vector3(dir.x, 0.0, dir.y).normalized().rotated(Vector3.UP, _yaw)
		position += move * speed
	position.x = clampf(position.x, -map_limit, map_limit)
	position.z = clampf(position.z, -map_limit, map_limit)
	_apply()


func _apply() -> void:
	if terrain != null and terrain.data != null:
		position.y = lerpf(position.y, terrain.data.height_at(position.x, position.z), 0.15)
	rotation = Vector3(0.0, _yaw, 0.0)
	_cam.rotation_degrees = Vector3(pitch_deg, 0.0, 0.0)
	_cam.position = Vector3(0.0, 0.0, 0.0) + (_cam.basis * Vector3(0.0, 0.0, _zoom))
