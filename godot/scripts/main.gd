extends Node3D
## Sets up lighting / atmosphere and starts the foundation terrain scene.
## Terrain only - spawns no props, buildings, units or resources.

@onready var terrain: TerrainManager = $Terrain
@onready var rts_camera: RtsCamera = $RtsCamera

## Start the camera above faction A's base so the RTS view is immediately usable.
@export var start_over_faction := 0
## Loads the pre-baked navmesh tiles (or bakes at startup if none are stored).
@export var setup_navigation_on_start := true


func _ready() -> void:
	_setup_environment()
	rts_camera.terrain = terrain
	if terrain.data == null:
		await terrain.terrain_ready
	rts_camera.position = terrain.data.base_position(start_over_faction)
	if setup_navigation_on_start:
		terrain.setup_navigation()


func _setup_environment() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.32, 0.50, 0.78)
	sky_mat.sky_horizon_color = Color(0.72, 0.80, 0.88)
	sky_mat.ground_horizon_color = Color(0.72, 0.80, 0.88)
	sky_mat.ground_bottom_color = Color(0.35, 0.40, 0.35)
	sky_mat.sun_angle_max = 25.0
	var sky := Sky.new()
	sky.sky_material = sky_mat

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.55, 0.64, 0.80)
	env.ambient_light_energy = 0.30
	env.tonemap_mode = Environment.TONE_MAPPER_ACES
	env.tonemap_exposure = 0.85
	# Cheap depth fog (works on every renderer / mobile) with aerial perspective.
	env.fog_enabled = true
	env.fog_light_color = Color(0.72, 0.80, 0.88)
	env.fog_density = 0.0005
	env.fog_aerial_perspective = 0.35
	env.fog_sky_affect = 0.0
	env.fog_height = 8.0
	env.fog_height_density = 0.003
	env.ssao_enabled = false
	env.glow_enabled = false
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-24.0, -50.0, 0.0)   # low-ish sun: slopes stay readable
	sun.light_color = Color(1.0, 0.94, 0.84)
	sun.light_energy = 2.0
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.directional_shadow_max_distance = 300.0
	sun.directional_shadow_split_1 = 0.08
	sun.directional_shadow_split_2 = 0.22
	sun.directional_shadow_split_3 = 0.5
	sun.shadow_normal_bias = 0.4
	add_child(sun)
