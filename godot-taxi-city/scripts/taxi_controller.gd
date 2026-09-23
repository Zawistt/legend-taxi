extends CharacterBody3D

@export var max_speed: float = 14.0
@export var acceleration: float = 10.0
@export var braking: float = 18.0
@export var friction: float = 6.0
@export var turn_speed: float = 2.2
@export var gravity: float = 20.0

var speed: float = 0.0

func _physics_process(delta: float) -> void:
	var throttle := 0.0
	if Input.is_action_pressed("ui_up") or Input.is_physical_key_pressed(KEY_W):
		throttle = 1.0
	elif Input.is_action_pressed("ui_down") or Input.is_physical_key_pressed(KEY_S):
		throttle = -1.0

	var steer := 0.0
	if Input.is_action_pressed("ui_left") or Input.is_physical_key_pressed(KEY_A):
		steer = 1.0
	elif Input.is_action_pressed("ui_right") or Input.is_physical_key_pressed(KEY_D):
		steer = -1.0

	if throttle != 0.0:
		speed += throttle * acceleration * delta
	else:
		speed = move_toward(speed, 0.0, friction * delta)

	if Input.is_action_pressed("ui_select") or Input.is_physical_key_pressed(KEY_SPACE):
		speed = move_toward(speed, 0.0, braking * delta)

	speed = clamp(speed, -max_speed * 0.5, max_speed)

	if abs(speed) > 0.1:
		rotate_y(steer * turn_speed * delta * sign(speed))

	var forward: Vector3 = -global_transform.basis.z
	velocity.x = forward.x * speed
	velocity.z = forward.z * speed

	if is_on_floor():
		velocity.y = 0.0
	else:
		velocity.y -= gravity * delta

	move_and_slide()
