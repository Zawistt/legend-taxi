extends Camera3D

@export var target_path: NodePath
@export var distance: float = 7.0
@export var height: float = 3.5
@export var follow_speed: float = 5.0

var target: Node3D

func _ready() -> void:
	if target_path != NodePath():
		target = get_node(target_path)

func _process(delta: float) -> void:
	if target == null:
		return
	var back: Vector3 = target.global_transform.basis.z.normalized()
	var desired_pos: Vector3 = target.global_transform.origin + back * distance + Vector3.UP * height
	global_transform.origin = global_transform.origin.lerp(desired_pos, follow_speed * delta)
	look_at(target.global_transform.origin + Vector3.UP * 1.0, Vector3.UP)
