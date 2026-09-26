extends SceneTree
## NavMesh'ni oldindan pishirish: godot --headless -s res://tools/bake_nav.gd
## Pishirgandan keyin tozalash: to'siqlar (qutilar, devorchalar) ICHIDAGI va bino tomlaridagi poligonlar olib tashlanadi.
## Sabab: NavMesh generatori qutini faqat yuzalar sifatida ko'radi va yopiq qutining ichidagi polni ham
## "yuriladigan" deb hisoblaydi. Bunday orolchalarga bot yoki o'yinchining maqsadi tushib qolmasligi kerak.


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
	var space := (main.get_node("Player") as Node3D).get_world_3d().direct_space_state
	var verts := nm.get_vertices()
	var clean := NavigationMesh.new()
	for prop in ["cell_size", "cell_height", "agent_height", "agent_radius", "agent_max_climb", "agent_max_slope"]:
		clean.set(prop, nm.get(prop))
	clean.set_vertices(verts)
	var removed_inside := 0
	var removed_roof := 0
	var q := PhysicsPointQueryParameters3D.new()
	q.collision_mask = 1
	var keep := []
	for i in nm.get_polygon_count():
		var poly := nm.get_polygon(i)
		var c := Vector3.ZERO
		for k in poly:
			c += verts[k]
		c /= poly.size()
		if c.y > 2.0:
			removed_roof += 1
			continue
		q.position = c + Vector3.UP * 0.6
		if not space.intersect_point(q, 1).is_empty():
			removed_inside += 1
			continue
		keep.append(poly)
	# asosiy maydonga ulanmagan orolchalar (qutilar va devor orasidagi yopiq bo'shliqlar) ham olib tashlanadi:
	# poligonlar umumiy uchlar orqali bog'lanadi, T spawn joylashgan qism qoladi
	var parent := {}
	var find := func(x):
		while parent.get(x, x) != x:
			x = parent[x]
		return x
	for poly in keep:
		var r0 = find.call(poly[0])
		for k in poly:
			var rk = find.call(k)
			if rk != r0:
				parent[rk] = r0
	var t_spawn := Vector3(0, 0, -47)
	var best := -1
	var bd := INF
	for poly in keep:
		for k in poly:
			var d := verts[k].distance_to(t_spawn)
			if d < bd:
				bd = d
				best = k
	var main_root = find.call(best)
	var removed_island := 0
	for poly in keep:
		if find.call(poly[0]) == main_root:
			clean.add_polygon(poly)
		else:
			removed_island += 1
	print("navmesh poligonlar: ", clean.get_polygon_count(), " (olib tashlandi: to'siq ichida ", removed_inside, ", tomlarda ", removed_roof, ", yakka orolchalar ", removed_island, ")")
	ResourceSaver.save(clean, "res://map/navmesh.res")
	quit()
