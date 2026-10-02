extends SceneTree
## Headless navmesh validation/bake:
##   godot --headless --path godot --script res://scripts/terrain/bake_navigation.gd
## Builds the terrain, bakes the per-chunk navmesh, prints stats and tests a
## path between the two faction bases.

func _init() -> void:
	var main: Node3D = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	await process_frame
	var terrain: TerrainManager = main.get_node("Terrain")
	var t0 := Time.get_ticks_msec()
	terrain.bake_navigation()
	print("bake time ms: ", Time.get_ticks_msec() - t0)
	var polys := 0
	var verts := 0
	for r in terrain.nav_regions:
		polys += r.navigation_mesh.get_polygon_count()
		verts += r.navigation_mesh.get_vertices().size()
	print("regions: ", terrain.nav_regions.size(), " polygons: ", polys, " vertices: ", verts)
	var map := terrain.get_world_3d().navigation_map
	var guard := 0
	while NavigationServer3D.map_get_iteration_id(map) == 0 and guard < 600:
		await physics_frame
		guard += 1
	var a := terrain.data.base_position(0)
	var b := terrain.data.base_position(1)
	print("map active=", NavigationServer3D.map_is_active(map), " regions=", NavigationServer3D.map_get_regions(map).size(), " cell=", NavigationServer3D.map_get_cell_size(map))
	print("closest to A: ", NavigationServer3D.map_get_closest_point(map, a), " B: ", NavigationServer3D.map_get_closest_point(map, b))
	var path := NavigationServer3D.map_get_path(map, a, b, true)
	var len := 0.0
	for i in range(1, path.size()):
		len += path[i].distance_to(path[i - 1])
	print("path base A -> base B: points=", path.size(), " length=", snappedf(len, 0.1),
			" end=", path[path.size() - 1] if path.size() > 0 else "none")
	quit()
