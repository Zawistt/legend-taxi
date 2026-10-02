class_name TerrainManager
extends Node3D
## Builds the 2 km x 2 km battlefield from the baked heightmap as a grid of
## modular chunks. Each chunk has:
##   * 3 LOD meshes (full / 1/2 / 1/4 resolution) switched with visibility ranges
##   * a skirt on every LOD so neighbouring LODs never show cracks
##   * ONE coarse HeightMapShape3D collider (layer "terrain") - cheap & navmesh-friendly
##   * one NavigationRegion3D (tiled navmesh, bake with bake_navigation())
## Nothing else is spawned: no props, buildings, units or resources.

signal terrain_ready
signal navigation_baked

const TERRAIN_LAYER := 1 << 0

@export var chunks_per_side := 4
@export_group("LOD")
## Distance (m) at which LOD0 -> LOD1 and LOD1 -> LOD2. Measured to chunk centre.
@export var lod1_distance := 170.0
@export var lod2_distance := 330.0
@export var lod_fade_margin := 20.0
@export var skirt_depth := 1.5
@export_group("Collision")
## Collision samples every N cells (4 => 3.3 m grid). Keep coarse; units follow navmesh.
@export var collision_step := 4
@export_group("Navigation")
# Sized for WorldScale: worker ~1.2 m tall / 0.4 m radius, 0.5 m nav radius for tight formations.
@export var nav_cell_size := 0.25
@export var nav_cell_height := 0.25
@export var nav_agent_radius := 0.5
@export var nav_agent_height := 1.5
@export var nav_agent_max_climb := 0.5
@export var nav_agent_max_slope := 35.0
@export var nav_chunk_margin := 1.5
@export var terrain_material: ShaderMaterial

var data: TerrainData
var chunks: Array[Node3D] = []
var nav_regions: Array[NavigationRegion3D] = []

var _cells_per_chunk: int


func _ready() -> void:
	data = TerrainData.load_default()
	if data == null:
		return
	_cells_per_chunk = data.cells / chunks_per_side
	if terrain_material == null:
		terrain_material = _default_material()
	_build_chunks()
	terrain_ready.emit()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_zones"):
		set_show_zones(not terrain_material.get_shader_parameter("show_zones"))


func set_show_zones(on: bool) -> void:
	terrain_material.set_shader_parameter("show_zones", on)


func _default_material() -> ShaderMaterial:
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/terrain.gdshader")
	mat.set_shader_parameter("zone_map", load(TerrainData.ZONEMAP_PATH))
	mat.set_shader_parameter("map_size", data.size_m)
	mat.set_shader_parameter("world_scale", data.meta["world_scale_from_design"])
	return mat


# ---------------------------------------------------------------- chunks ----

func _build_chunks() -> void:
	var chunk_m := _cells_per_chunk * data.cell_m
	for cz in chunks_per_side:
		for cx in chunks_per_side:
			var origin_col := cx * _cells_per_chunk
			var origin_row := cz * _cells_per_chunk
			var chunk := Node3D.new()
			chunk.name = "Chunk_%d_%d" % [cx, cz]
			chunk.position = Vector3(
					-data.size_m * 0.5 + (cx + 0.5) * chunk_m, 0.0,
					-data.size_m * 0.5 + (cz + 0.5) * chunk_m)
			add_child(chunk)
			chunks.append(chunk)
			_add_lods(chunk, origin_col, origin_row)
			_add_collision(chunk, origin_col, origin_row)


func _add_lods(chunk: Node3D, origin_col: int, origin_row: int) -> void:
	var steps := [1, 2, 4]
	var ranges := [
		Vector2(0.0, lod1_distance),
		Vector2(lod1_distance, lod2_distance),
		Vector2(lod2_distance, 0.0),
	]
	for i in steps.size():
		var mi := MeshInstance3D.new()
		mi.name = "LOD%d" % i
		mi.mesh = _build_mesh(origin_col, origin_row, steps[i])
		mi.material_override = terrain_material
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if i == 0 \
				else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.visibility_range_begin = ranges[i].x
		mi.visibility_range_end = ranges[i].y
		var fade := GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mi.visibility_range_begin_margin = lod_fade_margin if i > 0 else 0.0
		mi.visibility_range_end_margin = lod_fade_margin if i < steps.size() - 1 else 0.0
		mi.visibility_range_fade_mode = fade
		chunk.add_child(mi)


## Builds one chunk mesh (local space: origin at chunk centre).
func _build_mesh(origin_col: int, origin_row: int, step: int) -> ArrayMesh:
	var n := _cells_per_chunk / step          # quads per side
	var vside := n + 1
	var half := _cells_per_chunk * data.cell_m * 0.5
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var idx := PackedInt32Array()
	verts.resize(vside * vside)
	normals.resize(vside * vside)
	uvs.resize(vside * vside)

	for r in vside:
		for c in vside:
			var col := origin_col + c * step
			var row := origin_row + r * step
			var i := r * vside + c
			verts[i] = Vector3(c * step * data.cell_m - half, data.height_at_index(col, row),
					r * step * data.cell_m - half)
			normals[i] = _normal_at_index(col, row)
			uvs[i] = Vector2(float(col) / data.cells, float(row) / data.cells)

	for r in n:
		for c in n:
			var a := r * vside + c
			var b := a + 1
			var d := a + vside
			var e := d + 1
			# Godot front faces are clockwise
			idx.append_array([a, b, d, b, e, d])

	# Skirts: duplicate border vertices dropped by skirt_depth (hides LOD cracks).
	var border: Array[int] = []
	for c in vside: border.append(c)                          # top
	for r in range(1, vside): border.append(r * vside + vside - 1)   # right
	for c in range(vside - 2, -1, -1): border.append((vside - 1) * vside + c)  # bottom
	for r in range(vside - 2, 0, -1): border.append(r * vside)         # left
	var base := verts.size()
	for bi in border:
		verts.append(verts[bi] - Vector3(0, skirt_depth, 0))
		normals.append(normals[bi])
		uvs.append(uvs[bi])
	var count := border.size()
	for k in count:
		var v0 := border[k]
		var v1 := border[(k + 1) % count]
		var s0 := base + k
		var s1 := base + (k + 1) % count
		# both windings so the skirt is visible from either side
		idx.append_array([v0, v1, s0, v1, s1, s0])
		idx.append_array([v0, s0, v1, v1, s0, s1])

	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_INDEX] = idx
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.custom_aabb = AABB(Vector3(-half, -skirt_depth, -half),
			Vector3(half * 2.0, data.meta["max_height_m"] + skirt_depth, half * 2.0))
	return mesh


## Normals always come from the full-res heightmap so all LODs light identically.
func _normal_at_index(col: int, row: int) -> Vector3:
	var dx := data.height_at_index(col + 1, row) - data.height_at_index(col - 1, row)
	var dz := data.height_at_index(col, row + 1) - data.height_at_index(col, row - 1)
	return Vector3(-dx, 2.0 * data.cell_m, -dz).normalized()


func _add_collision(chunk: Node3D, origin_col: int, origin_row: int) -> void:
	var w := _cells_per_chunk / collision_step + 1
	var map := PackedFloat32Array()
	map.resize(w * w)
	for r in w:
		for c in w:
			map[r * w + c] = data.height_at_index(origin_col + c * collision_step,
					origin_row + r * collision_step)
	var shape := HeightMapShape3D.new()
	shape.map_width = w
	shape.map_depth = w
	shape.map_data = map
	var body := StaticBody3D.new()
	body.name = "Collision"
	body.collision_layer = TERRAIN_LAYER
	body.collision_mask = 0
	var cs := CollisionShape3D.new()
	cs.shape = shape
	# HeightMapShape3D has 1 unit between samples and is centred on its origin.
	cs.scale = Vector3(collision_step * data.cell_m, 1.0, collision_step * data.cell_m)
	body.add_child(cs)
	chunk.add_child(body)


# ------------------------------------------------------------ navigation ----

func _make_navmesh(chunk_aabb: AABB) -> NavigationMesh:
	var nm := NavigationMesh.new()
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_STATIC_COLLIDERS
	nm.geometry_collision_mask = TERRAIN_LAYER
	nm.geometry_source_geometry_mode = NavigationMesh.SOURCE_GEOMETRY_ROOT_NODE_CHILDREN
	nm.cell_size = nav_cell_size
	nm.cell_height = nav_cell_height
	nm.agent_radius = nav_agent_radius
	nm.agent_height = nav_agent_height
	nm.agent_max_climb = nav_agent_max_climb
	nm.agent_max_slope = nav_agent_max_slope
	nm.region_min_size = 2.0
	nm.region_merge_size = 8.0
	nm.border_size = nav_chunk_margin
	nm.filter_baking_aabb = chunk_aabb.grow(nav_chunk_margin)
	return nm


## Bakes one navmesh tile per chunk (call once at load, or from the editor tool
## script res://scripts/terrain/bake_navigation.gd to store the result on disk).
func bake_navigation() -> void:
	for r in nav_regions:
		r.queue_free()
	nav_regions.clear()
	var chunk_m := _cells_per_chunk * data.cell_m
	var maxh: float = data.meta["max_height_m"]
	for chunk in chunks:
		var aabb := AABB(Vector3(chunk.position.x - chunk_m * 0.5, -5.0, chunk.position.z - chunk_m * 0.5),
				Vector3(chunk_m, maxh + 10.0, chunk_m))
		var nm := _make_navmesh(aabb)
		# Parse from this node so every chunk's terrain collider is a source.
		var source := NavigationMeshSourceGeometryData3D.new()
		NavigationServer3D.parse_source_geometry_data(nm, source, self)
		NavigationServer3D.bake_from_source_geometry_data(nm, source)
		var region := NavigationRegion3D.new()
		region.name = "Nav_" + chunk.name
		region.navigation_mesh = nm
		add_child(region)
		nav_regions.append(region)
	navigation_baked.emit()
