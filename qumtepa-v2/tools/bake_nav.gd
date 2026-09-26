extends SceneTree
## NavMesh'ni oldindan pishirish: godot --headless -s res://tools/bake_nav.gd


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var main: Node = load("res://main.tscn").instantiate()
	root.add_child(main)
	await physics_frame
	await physics_frame
	var region: NavigationRegion3D = main.get_node("Navigation")
	region.bake_navigation_mesh(false)
	var nm := region.navigation_mesh
	print("navmesh poligonlar: ", nm.get_polygon_count())
	ResourceSaver.save(nm, "res://map/navmesh.res")
	quit()
