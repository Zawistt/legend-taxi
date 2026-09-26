extends Camera3D
## Bot o'yinini kuzatish: sichqonchaning o'ng tugmasi + harakat — qarash, WASD/QE — uchish, Shift — tez,
## 1–5 — T botlarni, 6–0 — CT botlarni kuzatish, Tab — erkin kamera, Space — pauza, +/- — o'yin tezligi.

var follow: Node3D = null
var yaw := 0.0
var pitch := -0.9
var speed := 20.0


func _ready() -> void:
	global_position = Vector3(0, 70, 55)
	rotation = Vector3(pitch, yaw, 0)
	far = 500.0


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		yaw -= event.relative.x * 0.004
		pitch = clamp(pitch - event.relative.y * 0.004, -1.5, 1.5)
		rotation = Vector3(pitch, yaw, 0)
	elif event is InputEventKey and event.pressed and event.keycode == KEY_F10 and ResourceLoader.exists("res://menu.tscn"):
		get_tree().change_scene_to_file("res://menu.tscn")
	elif event is InputEventKey and event.pressed:
		var m: Node = get_node("../BotMatch")
		if event.keycode >= KEY_1 and event.keycode <= KEY_9 or event.keycode == KEY_0:
			var i: int = 9 if event.keycode == KEY_0 else event.keycode - KEY_1
			follow = m.bots[i]
		elif event.keycode == KEY_TAB:
			follow = null
		elif event.keycode == KEY_SPACE:
			get_tree().paused = not get_tree().paused
		elif event.keycode == KEY_EQUAL or event.keycode == KEY_KP_ADD:
			Engine.time_scale = min(Engine.time_scale * 2.0, 8.0)
		elif event.keycode == KEY_MINUS or event.keycode == KEY_KP_SUBTRACT:
			Engine.time_scale = max(Engine.time_scale / 2.0, 0.25)


func _process(delta: float) -> void:
	var d: float = delta / max(Engine.time_scale, 0.01)
	if follow and is_instance_valid(follow) and follow.alive:
		var back := Vector3(-sin(follow.rotation.y), 0, -cos(follow.rotation.y))
		global_position = global_position.lerp(follow.global_position + back * 4.0 + Vector3.UP * 3.0, min(1.0, d * 6.0))
		look_at(follow.global_position + Vector3.UP * 1.4 - back * 6.0, Vector3.UP)
		return
	var v := Vector3.ZERO
	if Input.is_key_pressed(KEY_W): v -= basis.z
	if Input.is_key_pressed(KEY_S): v += basis.z
	if Input.is_key_pressed(KEY_A): v -= basis.x
	if Input.is_key_pressed(KEY_D): v += basis.x
	if Input.is_key_pressed(KEY_E): v += Vector3.UP
	if Input.is_key_pressed(KEY_Q): v -= Vector3.UP
	var s := speed * (3.0 if Input.is_key_pressed(KEY_SHIFT) else 1.0)
	global_position += v.normalized() * s * d
