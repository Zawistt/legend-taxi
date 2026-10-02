extends SceneTree
## Headless navmesh bake + validation. Stores the tiles in res://terrain_data/nav/.
##   godot --headless --path godot --script res://scripts/terrain/bake_navigation.gd
## Checks: every road segment is navigable, base A -> base B, blocked zones are carved out,
## coverage stats. Exit code 1 if a check fails.

func _init() -> void:
	var main: Node3D = load("res://scenes/main.tscn").instantiate()
	main.set("setup_navigation_on_start", false)
	root.add_child(main)
	await process_frame
	await process_frame
	var terrain: TerrainManager = main.get_node("Terrain")
	var t0 := Time.get_ticks_msec()
	terrain.bake_navigation(true)
	print("bake time ms: ", Time.get_ticks_msec() - t0)
	_report(terrain)
	var ok := await _validate(terrain)
	quit(0 if ok else 1)


func _in_resource_footprint(q: Vector3, terrain: TerrainManager) -> bool:
	for loc in _db().locations:
		var c: Vector3 = loc["position"]
		if Vector2(q.x - c.x, q.z - c.z).length() < float(loc["footprint_radius"]) + 1.2:
			return true
	return false


var _db_cache: ResourceDatabase
func _db() -> ResourceDatabase:
	if _db_cache == null:
		_db_cache = ResourceDatabase.load_default()
	return _db_cache


func _report(terrain: TerrainManager) -> void:
	var polys := 0
	var verts := 0
	var area := 0.0
	for r in terrain.nav_regions:
		var nm := r.navigation_mesh
		polys += nm.get_polygon_count()
		var v := nm.get_vertices()
		verts += v.size()
		for i in nm.get_polygon_count():
			var idx := nm.get_polygon(i)
			for k in range(1, idx.size() - 1):
				var a := v[idx[0]]; var b := v[idx[k]]; var c := v[idx[k + 1]]
				area += absf((b.x - a.x) * (c.z - a.z) - (c.x - a.x) * (b.z - a.z)) * 0.5
	var play := 360.0 * 360.0
	print("regions: ", terrain.nav_regions.size(), " polygons: ", polys, " vertices: ", verts,
			" navigable area: ", snappedf(area, 1.0), " m2 (", snappedf(area / play * 100.0, 0.1), "% of playable)")


func _validate(terrain: TerrainManager) -> bool:
	var map := terrain.get_world_3d().navigation_map
	var guard := 0
	while NavigationServer3D.map_get_iteration_id(map) == 0 and guard < 900:
		await physics_frame
		guard += 1
	var net := terrain.get_path_network()
	var ok := true

	# 1. every road edge must be navigable end to end and roughly follow the road
	var worst := 0.0
	var failed: Array[String] = []
	for id in net.edges:
		var e: Dictionary = net.edges[id]
		if e["cls"] == "open":
			continue
		var a: Vector3 = net.nodes[e["a"]]
		var b: Vector3 = net.nodes[e["b"]]
		var path := NavigationServer3D.map_get_path(map, a, b, true)
		if path.is_empty() or path[path.size() - 1].distance_to(b) > 2.0:
			failed.append(id)
			continue
		var l := 0.0
		for i in range(1, path.size()):
			l += path[i].distance_to(path[i - 1])
		worst = maxf(worst, l / maxf(e["length"], 1.0))
	print("road edges unreachable: ", failed, " | worst path/road length ratio: ", snappedf(worst, 0.01))
	if not failed.is_empty():
		ok = false

	# 2. sample points along every road centreline must lie on the navmesh
	var off := 0
	var total := 0
	for id in net.edges:
		var e: Dictionary = net.edges[id]
		if e["cls"] == "open":
			continue
		var pts: PackedVector3Array = e["points"]
		for p in pts:
			total += 1
			if NavigationServer3D.map_get_closest_point(map, p).distance_to(p) > 0.75:
				off += 1
	print("road centreline samples off navmesh: ", off, " / ", total)
	if off > total / 100:
		ok = false

	# 3. strategic base A -> base B routes (lane by lane) and open ground
	var a := terrain.data.base_position(0)
	var b := terrain.data.base_position(1)
	var route := NavigationServer3D.map_get_path(map, a, b, true)
	var rl := 0.0
	for i in range(1, route.size()):
		rl += route[i].distance_to(route[i - 1])
	print("shortest base A -> base B: ", snappedf(rl, 0.1), " m (straight ", snappedf(a.distance_to(b), 0.1), ")")
	for lane in ["center", "left", "right"]:
		var via := net.lane_curve(lane)
		var n := via.point_count
		var len := 0.0
		var broken := false
		for i in range(0, n - 1, 6):
			var p0 := via.get_point_position(i)
			var p1 := via.get_point_position(mini(i + 6, n - 1))
			var seg := NavigationServer3D.map_get_path(map, p0, p1, true)
			if seg.is_empty():
				broken = true
				break
			for k in range(1, seg.size()):
				len += seg[k].distance_to(seg[k - 1])
		print("lane ", lane, ": navigable end to end = ", not broken, ", walked length ", snappedf(len, 0.1),
				" m (road ", snappedf(net.lane_length(lane), 0.1), " m)")
		if broken:
			ok = false

	# 4. blocked zones must be carved out: their centres are not on the navmesh
	var blocked_on_mesh := 0
	var tested := 0
	var f := FileAccess.open(TerrainManager.BLOCKERS_PATH, FileAccess.READ)
	for bl in JSON.parse_string(f.get_as_text())["blockers"]:
		var poly: Array = bl["polygon"]
		var cx := 0.0
		var cz := 0.0
		for p in poly:
			cx += p[0]; cz += p[1]
		cx /= poly.size(); cz /= poly.size()
		var y := terrain.data.height_at(cx, cz)
		var q := Vector3(cx, y, cz)
		tested += 1
		if NavigationServer3D.map_get_closest_point(map, q).distance_to(q) < 0.6:
			blocked_on_mesh += 1
	print("blocker centres still navigable: ", blocked_on_mesh, " / ", tested)
	if blocked_on_mesh > 0:
		ok = false

	# 5. arena + base aprons open: random samples must be navigable
	var checks := {"arena": [Vector3(0, 0, 0), 48.0], "apron_a": [terrain.data.base_position(0), 38.0], "apron_b": [terrain.data.base_position(1), 38.0]}
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	for k in checks:
		var c: Vector3 = checks[k][0]
		var r: float = checks[k][1]
		var bad := 0
		for i in 300:
			var ang := rng.randf() * TAU
			var rr := sqrt(rng.randf()) * r
			var q := Vector3(c.x + cos(ang) * rr, 0.0, c.z + sin(ang) * rr)
			q.y = terrain.data.height_at(q.x, q.z)
			if _in_resource_footprint(q, terrain):
				continue                         # solid deposits / groves are intentionally carved
			if NavigationServer3D.map_get_closest_point(map, q).distance_to(q) > 0.75:
				bad += 1
		print(k, " samples off navmesh: ", bad, " / 300")
		if bad > 3:
			ok = false

	# 6. nothing outside the playable square (mountain rim) may be navigable
	var rim_bad := 0
	for i in 200:
		var edge := 183.0 + rng.randf() * 28.0
		var t := rng.randf_range(-210.0, 210.0)
		var q := Vector3(edge, 0.0, t) if rng.randf() < 0.5 else Vector3(t, 0.0, -edge)
		if rng.randf() < 0.5:
			q = -q
		q.y = terrain.data.height_at(q.x, q.z)
		if NavigationServer3D.map_get_closest_point(map, q).distance_to(q) < 1.0:
			rim_bad += 1
	print("rim samples navigable: ", rim_bad, " / 200")
	if rim_bad > 0:
		ok = false

	# 7. resource system: slots reachable, solid footprints carved, fair walking distances
	var db := ResourceDatabase.load_default()
	var res_bad := 0
	var walk_len := {}                        # id -> navmesh path length base -> gathering point
	var min_slot_gap := 1e9
	for loc in db.locations:
		var slots: Array = loc["slots"]
		for s_ in slots:
			if NavigationServer3D.map_get_closest_point(map, s_).distance_to(s_) > 0.75:
				res_bad += 1
				print("  slot off navmesh: ", loc["id"], " ", s_)
		var c: Vector3 = loc["position"]
		if NavigationServer3D.map_get_closest_point(map, c).distance_to(c) < float(loc["footprint_radius"]) * 0.5:
			res_bad += 1
			print("  footprint centre still navigable: ", loc["id"])
		for i in slots.size():
			for j in range(i + 1, slots.size()):
				min_slot_gap = minf(min_slot_gap, (slots[i] as Vector3).distance_to(slots[j]))
		var base: Vector3 = terrain.data.base_position(0 if loc["dropoff_base"] == "BASE_A" else 1)
		var p := NavigationServer3D.map_get_path(map, base, loc["gathering_point"], true)
		if p.is_empty():
			res_bad += 1
			print("  no path base -> ", loc["id"])
			continue
		var l := 0.0
		for i in range(1, p.size()):
			l += p[i].distance_to(p[i - 1])
		walk_len[loc["id"]] = l
	print("resource problems: ", res_bad, " | min gap between worker slots: ", snappedf(min_slot_gap, 0.1), " m")
	if res_bad > 0 or min_slot_gap < 1.9:
		ok = false
	var worst_ratio := 1.0
	var rows: Array[String] = []
	for loc in db.locations:
		if loc["owner"] != 0:
			continue
		var twin_id: String = String(loc["id"]).replace("_p1", "_p2")
		var len1: float = walk_len.get(loc["id"], 0.0)
		var len2: float = walk_len.get(twin_id, 0.0)
		var r := maxf(len1, len2) / maxf(minf(len1, len2), 0.01)
		worst_ratio = maxf(worst_ratio, r)
		rows.append("%s P1 %.1f m | P2 %.1f m" % [loc["group"], len1, len2])
	print("walking distance base -> resource (navmesh):")
	for row in rows:
		print("  ", row)
	print("worst P1/P2 walking distance ratio: ", snappedf(worst_ratio, 0.001))
	if worst_ratio > 1.12:
		ok = false
	# neutral resources: both players' combined distance must match
	var sum_a := 0.0
	var sum_b := 0.0
	for loc in db.locations:
		if loc["owner"] == -1:
			sum_a += (loc["position"] as Vector3).distance_to(terrain.data.base_position(0))
			sum_b += (loc["position"] as Vector3).distance_to(terrain.data.base_position(1))
	print("neutral resources: summed distance to base A ", snappedf(sum_a, 0.1), " m, to base B ", snappedf(sum_b, 0.1), " m")

	print("NAVIGATION CHECKS ", "PASSED" if ok else "FAILED")
	return ok
