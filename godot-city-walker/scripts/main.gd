extends Node3D

const CITY_SCENE_PATH := "res://assets/city_scene.glb"

# The city GLB was exported (via trimesh) without the usual Z-up -> Y-up
# correction that tools like Blender/Sketchfab bake into the root node, so it
# needs a -90 degree rotation around X here to stand upright in Godot's
# Y-up world.
const CITY_UP_AXIS_FIX_DEGREES := Vector3(-90.0, 0.0, 0.0)

@onready var city_root: Node3D = $CityRoot
@onready var player: CharacterBody3D = $Player
@onready var world_environment: WorldEnvironment = $WorldEnvironment

var _found_any_mesh := false
var _aabb_result := AABB()


func _ready() -> void:
	_setup_environment()
	_load_city()


func _setup_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color(0.29, 0.53, 0.85)
	sky_material.sky_horizon_color = Color(0.75, 0.83, 0.9)
	sky_material.ground_bottom_color = Color(0.2, 0.22, 0.25)
	sky_material.ground_horizon_color = Color(0.75, 0.83, 0.9)
	var sky := Sky.new()
	sky.sky_material = sky_material
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 1.0
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_light_color = Color(0.75, 0.83, 0.9)
	env.fog_density = 0.006
	world_environment.environment = env


func _load_city() -> void:
	var packed: PackedScene = load(CITY_SCENE_PATH)
	var city := packed.instantiate()
	city_root.add_child(city)
	city_root.rotation_degrees = CITY_UP_AXIS_FIX_DEGREES

	_generate_collisions(city)

	_found_any_mesh = false
	_aabb_result = AABB()
	_collect_world_aabb(city)

	var spawn_pos: Vector3
	if _found_any_mesh:
		var center_x: float = _aabb_result.position.x + _aabb_result.size.x * 0.5
		var center_z: float = _aabb_result.position.z + _aabb_result.size.z * 0.5
		var top_y: float = _aabb_result.position.y + _aabb_result.size.y
		spawn_pos = Vector3(center_x, top_y + 8.0, center_z)
	else:
		spawn_pos = Vector3(0.0, 5.0, 0.0)

	player.global_position = spawn_pos


func _generate_collisions(node: Node) -> void:
	if node is MeshInstance3D:
		node.create_trimesh_collision()
	for child in node.get_children():
		_generate_collisions(child)


func _collect_world_aabb(node: Node) -> void:
	if node is VisualInstance3D:
		var world_aabb: AABB = node.global_transform * node.get_aabb()
		if not _found_any_mesh:
			_aabb_result = world_aabb
			_found_any_mesh = true
		else:
			_aabb_result = _aabb_result.merge(world_aabb)
	for child in node.get_children():
		_collect_world_aabb(child)
