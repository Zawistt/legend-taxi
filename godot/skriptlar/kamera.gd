## Kamera: orqadan kuzatish, tepadan (GTA 1 uslubi) va erkin uchish.
## C — rejimni almashtirish. Erkin rejimda: sichqoncha + WASD, Shift — tez.
class_name Kamera
extends Camera3D

enum Rejim { ORQADAN, TEPADAN, ERKIN }

var nishon: Node3D
var rejim := Rejim.ORQADAN
var _yaw := 0.0
var _pitch := -0.3


func _init() -> void:
	name = "Kamera"
	fov = 68.0
	near = 0.2
	far = 3000.0


func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("kamera"):
		rejim = ((rejim + 1) % 3) as Rejim
		var erkin := rejim == Rejim.ERKIN
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if erkin else Input.MOUSE_MODE_VISIBLE
		if nishon is Mashina:
			(nishon as Mashina).boshqaruv_yoqilgan = not erkin
		if erkin:
			_yaw = rotation.y
			_pitch = rotation.x
	if rejim == Rejim.ERKIN and e is InputEventMouseMotion:
		_yaw -= e.relative.x * 0.003
		_pitch = clampf(_pitch - e.relative.y * 0.003, -1.5, 1.5)


func _process(delta: float) -> void:
	if nishon == null:
		return
	var np := nishon.global_position
	match rejim:
		Rejim.ORQADAN:
			var v: float = (nishon as RigidBody3D).linear_velocity.length() if nishon is RigidBody3D else 0.0
			var orqa := -nishon.global_basis.z
			orqa.y = 0
			orqa = orqa.normalized()
			var maqsad: Vector3 = np + orqa * (7.5 + v * 0.08) + Vector3.UP * (2.6 + v * 0.02)
			global_position = global_position.lerp(maqsad, 1.0 - exp(-delta * 6.0))
			look_at(np + Vector3.UP * 1.3 - orqa * 3.0, Vector3.UP)
		Rejim.TEPADAN:
			var v: float = (nishon as RigidBody3D).linear_velocity.length() if nishon is RigidBody3D else 0.0
			var bal: float = 55.0 + v * 1.6
			var maqsad: Vector3 = np + Vector3(0, bal, bal * 0.3)
			global_position = global_position.lerp(maqsad, 1.0 - exp(-delta * 3.0))
			look_at(np, Vector3.UP)
		Rejim.ERKIN:
			rotation = Vector3(_pitch, _yaw, 0)
			var yon := Input.get_vector("chap", "ong", "gaz", "tormoz")
			var tez := 60.0 if Input.is_key_pressed(KEY_SHIFT) else 18.0
			global_position += (global_basis * Vector3(yon.x, 0, yon.y)) * tez * delta
			if Input.is_key_pressed(KEY_E):
				global_position.y += tez * delta
			if Input.is_key_pressed(KEY_Q):
				global_position.y -= tez * delta
