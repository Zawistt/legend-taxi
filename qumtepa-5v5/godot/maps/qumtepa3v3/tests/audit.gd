extends SceneTree
## Yakuniy audit: devor tirqishlari, pol teshiklari, shift ketgan obyektlar,
## xaritadan chiqib ketish yo'llari, navmesh qoplami va material xatolari.
## Ishga tushirish: godot --headless -s res://tests/audit.gd

const MapData := preload("res://maps/qumtepa3v3/scripts/map_data.gd")

var main: Node
var pl: CharacterBody3D
var space: PhysicsDirectSpaceState3D
var problems := 0


func note(ok: bool, msg: String) -> void:
	print(("  [OK]   " if ok else "  [MUAMMO] ") + msg)
	if not ok:
		problems += 1


func ray(from: Vector3, to: Vector3, mask: int, inside := false) -> Dictionary:
	var q := PhysicsRayQueryParameters3D.create(from, to, mask)
	q.hit_from_inside = inside
	return space.intersect_ray(q)


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	main = load("res://main_3v3.tscn").instantiate()
	main.get_node("Bots").enabled = false      # botlarsiz: xarita sinovi
	root.add_child(main)
	pl = main.get_node("Player")
	pl.set_physics_process(false)
	for i in 20:
		await physics_frame
	space = pl.get_world_3d().direct_space_state

	var grid := _grid()

	print("\n1) Pol qoplami (har 0.5 m da tepadan pastga nur)")
	var holes: Array[Vector3] = []
	var checked := 0
	var x := -24.75
	while x < 25.0:
		var z := -24.75
		while z < 25.0:
			if _walkable(grid, x, z):
				checked += 1
				var h := ray(Vector3(x, 6.0, z), Vector3(x, -2.0, z), 1)
				if h.is_empty() or h.position.y < -0.5:
					holes.append(Vector3(x, 0, z))
			z += 0.5
		x += 0.5
	note(holes.is_empty(), "pol teshiklari: %d ta (%d nuqta tekshirildi)" % [holes.size(), checked])
	for i in mini(holes.size(), 5):
		print("         teshik: ", holes[i])

	print("\n2) Devor tirqishlari (bino va ochiq katak chegarasida ko'krak balandligida nur)")
	var gaps: Array[String] = []
	for r in range(25):
		for c in range(25):
			if grid[r][c] != "#":
				continue
			for d in [[0, 1], [0, -1], [1, 0], [-1, 0]]:
				var nr: int = r + d[0]
				var nc: int = c + d[1]
				if nr < 0 or nc < 0 or nr > 24 or nc > 24 or grid[nr][nc] == "#":
					continue
				# nur ochiq katakdan bino markaziga qarab otiladi
				var bx := -24.0 + 2.0 * c
				var bz := -24.0 + 2.0 * r
				var ox := -24.0 + 2.0 * nc
				var oz := -24.0 + 2.0 * nr
				for t in [-0.6, 0.0, 0.6]:
					for y in [0.35, 1.2, 2.4]:
						var from := Vector3(ox + (t if d[1] == 0 else 0.0), y, oz + (t if d[0] == 0 else 0.0))
						var to := Vector3(bx + (t if d[1] == 0 else 0.0), y, bz + (t if d[0] == 0 else 0.0))
						if ray(from, to, 1).is_empty():
							gaps.append("(%d,%d)->(%d,%d) y=%.1f" % [nc, nr, c, r, y])
	note(gaps.is_empty(), "devor tirqishlari: %d ta" % gaps.size())
	for i in mini(gaps.size(), 6):
		print("         ", gaps[i])

	print("\n3) Xaritadan chiqib ketish (chegarada tashqariga nur)")
	var leaks := 0
	for i in range(0, 200):
		var a := TAU * i / 200.0
		var from := Vector3(cos(a) * 3.0, 1.2, sin(a) * 3.0)
		var to := Vector3(cos(a) * 60.0, 1.2, sin(a) * 60.0)
		var h := ray(from, to, 3)
		if h.is_empty():
			leaks += 1
	note(leaks == 0, "tashqariga ochiq yo'nalishlar: %d / 200" % leaks)

	print("\n4) Shift ketgan obyektlar (havoda osilgan yoki devor ichida)")
	var floating := 0
	var buried := 0
	var props := 0
	for body in main.get_node("Navigation/Collision").get_children():
		if not (body is StaticBody3D) or not body.name.begins_with("World_"):
			continue
		for shape in body.get_children():
			var cs := shape as CollisionShape3D
			if cs == null or not (cs.shape is BoxShape3D):
				continue
			var sz: Vector3 = (cs.shape as BoxShape3D).size
			if sz.x > 3.0 or sz.z > 3.0 or sz.y > 3.0:
				continue   # katta bloklar — bino, tekshirmaymiz
			props += 1
			var p := cs.global_position
			var bottom := p.y - sz.y / 2.0
			if bottom > 0.35:
				# tayanch: ostida pol/boshqa jism, yoki yon tomonda devor (chiroq, to'sin, narvon)
				var supported := not ray(Vector3(p.x, bottom + 0.05, p.z), Vector3(p.x, bottom - 0.6, p.z), 1).is_empty()
				if not supported:
					for d in [Vector3.LEFT, Vector3.RIGHT, Vector3.FORWARD, Vector3.BACK, Vector3.UP]:
						var reach: float = 0.45 + (sz.x + sz.z) * 0.5
						if not ray(p, p + d * reach, 1, true).is_empty():
							supported = true
							break
				if not supported:
					floating += 1
					if floating <= 6:
						print("         osilgan: ", p, " o'lcham ", sz)
	note(floating == 0, "havoda osilgan obyektlar: %d (%d ta tekshirildi)" % [floating, props])

	print("\n5) Yopiq yo'laklarda shift qolgan joylar (shiftdan yuqoriga nur)")
	var noceil := 0
	for r in range(25):
		for c in range(25):
			if not (grid[r][c] in [",", "m", "T", "C"]):
				continue
			var px := -24.0 + 2.0 * c
			var pz := -24.0 + 2.0 * r
			if ray(Vector3(px, 1.5, pz), Vector3(px, 11.0, pz), 1).is_empty():
				noceil += 1
	note(noceil == 0, "shiftsiz yopiq kataklar: %d ta" % noceil)

	print("\n6) Zonalar, spawn va navmesh")
	NavigationServer3D.map_force_update(pl.get_world_3d().navigation_map)
	var nav: NavigationRegion3D = main.get_node("Navigation")
	note(nav.navigation_mesh.get_polygon_count() > 300, "navmesh: %d poligon" % nav.navigation_mesh.get_polygon_count())
	var unreach := 0
	for a in get_nodes_in_group("ai_points"):
		var start: Vector3 = Vector3(0, 0, -20) if str(a.get_meta("team")) == "T" else Vector3(0, 0, 18)
		var p := NavigationServer3D.map_get_path(pl.get_world_3d().navigation_map, start, a.global_position, true)
		if p.size() < 2 or p[-1].distance_to(a.global_position) > 0.9:
			unreach += 1
	note(unreach == 0, "bot nuqtalariga yo'l: %d ta yetib bo'lmaydi" % unreach)

	print("\n7) Materiallar va sirt turlari")
	var nosurf := 0
	for body in main.get_node("Navigation/Collision").get_children():
		if body is StaticBody3D and body.name.begins_with("World_") and not body.has_meta("surface"):
			nosurf += 1
	note(nosurf == 0, "sirt turi belgilanmagan jismlar: %d" % nosurf)

	print("\n8) Spawn nuqtalari toza (obyekt ichida emas)")
	var blocked := 0
	for team in ["T", "CT"]:
		for sp in get_nodes_in_group("spawn_" + team):
			var p: Vector3 = (sp as Node3D).global_position
			var q := PhysicsShapeQueryParameters3D.new()
			var cap := CapsuleShape3D.new()
			cap.radius = 0.35
			cap.height = 1.8
			q.shape = cap
			q.transform = Transform3D(Basis(), p + Vector3.UP * 0.9)
			q.collision_mask = 1
			if space.intersect_shape(q, 1).size() > 0:
				blocked += 1
	note(blocked == 0, "band spawn nuqtalari: %d" % blocked)

	print("\nAUDIT: %d muammo" % problems)
	quit(1 if problems > 0 else 0)


func _walkable(grid: Array, x: float, z: float) -> bool:
	var c := int(floor((x + 25.0) / 2.0))
	var r := int(floor((z + 25.0) / 2.0))
	if r < 0 or c < 0 or r > 24 or c > 24:
		return false
	return grid[r][c] != "#"


func _grid() -> Array:
	var g := []
	for row in MapData.GRID:
		g.append((row as String).split(""))
	return g
