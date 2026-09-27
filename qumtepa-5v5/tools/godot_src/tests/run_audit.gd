extends SceneTree
## Yakuniy audit: xaritadagi texnik nuqsonlarni qidiradi.
##  1) Teshiklar: yuriladigan har bir nuqtadan (2 m to'r) ko'z balandligida 16 yo'nalishga nur — devorga urilmasdan
##     xaritadan chiqib ketsa, bu devorlar orasidagi tirqish (leak).
##  2) Tom teshiklari: yopiq kataklardan tepaga nur — tomga urilishi kerak.
##  3) Yetib bo'lmaydigan joylar: har bir yuriladigan nuqtaga T spawn'dan NavMesh yo'li bo'lishi kerak.
##  4) Tiqilib qolish: o'yinchi haqiqiy fizika bilan har bir callout hududi markaziga yurib boradi.
##  5) Xaritadan chiqish: chegara va tom clip'lari, tushib ketish.
## Ishga tushirish (godot/ papkasida): godot --headless --fixed-fps 60 -s res://tests/run_audit.gd
## Natija: docs/audit_final.json

const D := preload("res://tests/test_data.gd")
const MapData := preload("res://scripts/map_data.gd")

var fails := 0
var total := 0
var pl: CharacterBody3D
var report := {}


func ok(cond: bool, msg: String) -> void:
	total += 1
	print(("  [OK]   " if cond else "  [XATO] ") + msg)
	if not cond:
		fails += 1


func _initialize() -> void:
	_run.call_deferred()


func walkable_points() -> Array:
	var pts := []
	var g: Array = D.SIDE_GRID
	for r in g.size():
		for c in g[r].size():
			if g[r][c] != 9:
				pts.append(Vector3(D.MAP_MIN + c * 2.0 + 1.0, 0.0, D.MAP_MIN + r * 2.0 + 1.0))
	return pts


func _run() -> void:
	var main: Node = load("res://main.tscn").instantiate()
	if main.get_node_or_null("Bots"):
		main.get_node("Bots").enabled = false      # botlarsiz: xarita va mexanika sinovi
	root.add_child(main)
	pl = main.get_node("Player")
	var gm: Node = main.get_node("GameMode")
	for i in 30:
		await physics_frame
	var space := pl.get_world_3d().direct_space_state
	var nav := pl.get_world_3d().navigation_map
	NavigationServer3D.map_force_update(nav)
	var pts := walkable_points()

	print("\n1) Devorlardagi tirqishlar (ko'z balandligida 16 yo'nalish, %d nuqta)" % pts.size())
	var leaks := []
	for p in pts:
		var nav_p := NavigationServer3D.map_get_closest_point(nav, p)
		if Vector2(nav_p.x - p.x, nav_p.z - p.z).length() > 1.2 or nav_p.y > 1.5:
			continue
		var eye := Vector3(nav_p.x, 1.6, nav_p.z)
		for k in 16:
			var a := TAU * k / 16.0
			var to := eye + Vector3(cos(a), 0, sin(a)) * 200.0
			var h := space.intersect_ray(PhysicsRayQueryParameters3D.create(eye, to, 1))
			if h.is_empty():
				leaks.append([snappedf(eye.x, 0.1), snappedf(eye.z, 0.1), k])
	ok(leaks.is_empty(), "hech bir nurdan xaritadan tashqariga ko'rinmaydi (tirqish yo'q)" + ("" if leaks.is_empty() else " — %d ta: %s" % [leaks.size(), str(leaks.slice(0, 5))]))
	report["leaks"] = leaks

	print("\n2) Tomlar (yopiq kataklardan tepaga)")
	var roof_holes := []
	for c in D.COVERED_CELLS:
		for off in [Vector3(-0.8, 0, -0.8), Vector3(0.8, 0, 0.8), Vector3(0, 0, 0)]:
			var from: Vector3 = c + off + Vector3(0, 0.6, 0)
			var h := space.intersect_ray(PhysicsRayQueryParameters3D.create(from, from + Vector3.UP * 30.0, 1))
			if h.is_empty() or h.position.y > 6.0:
				roof_holes.append([snappedf(from.x, 0.1), snappedf(from.z, 0.1)])
	ok(roof_holes.is_empty(), "yopiq yo'laklar tomida teshik yo'q (%d katak)" % D.COVERED_CELLS.size() + ("" if roof_holes.is_empty() else " — %s" % str(roof_holes.slice(0, 5))))

	print("\n3) Yetib bo'lmaydigan joylar (NavMesh)")
	var unreach := []
	var checked := 0
	for p in pts:
		var np := NavigationServer3D.map_get_closest_point(nav, p)
		if Vector2(np.x - p.x, np.z - p.z).length() > 1.2 or np.y > 1.5:
			continue
		checked += 1
		var path := NavigationServer3D.map_get_path(nav, D.T_SPAWN, np, true)
		if path.is_empty() or path[-1].distance_to(np) > 0.6:
			unreach.append([snappedf(np.x, 0.1), snappedf(np.z, 0.1), MapData.callout_at(np)])
	ok(unreach.is_empty(), "hamma yuriladigan nuqtalarga yo'l bor (%d nuqta)" % checked + ("" if unreach.is_empty() else " — yetib bo'lmaydi: %s" % str(unreach.slice(0, 8))))
	report["unreachable"] = unreach
	var no_nav := 0
	for p in pts:
		var np2 := NavigationServer3D.map_get_closest_point(nav, p)
		if Vector2(np2.x - p.x, np2.z - p.z).length() > 1.2:
			no_nav += 1
	report["cells_without_nav"] = no_nav
	print("         (NavMesh yo'q kataklar — panalar ostida: %d)" % no_nav)

	print("\n4) Tiqilib qolish: har bir callout hududiga fizika bilan yurish")
	gm.skip_freeze()
	for i in 3:
		await physics_frame
	var targets := {}
	for p in pts:
		var cn: String = MapData.callout_at(p)
		if cn != "" and not targets.has(cn):
			var np3 := NavigationServer3D.map_get_closest_point(nav, p)
			if Vector2(np3.x - p.x, np3.z - p.z).length() < 0.5 and np3.y < 1.5:
				targets[cn] = np3
	var stuck := []
	for cn in targets:
		for start in [D.T_SPAWN, D.CT_SPAWN]:
			gm.time_left = 1.0e6
			pl.teleport(Transform3D(Basis(), start + Vector3.UP * 0.1))
			for i in 3:
				await physics_frame
			var t := await walk_to(nav, targets[cn], 45.0)
			if t < 0.0:
				stuck.append([cn, "T" if start == D.T_SPAWN else "CT", snappedf(pl.global_position.x, 0.1), snappedf(pl.global_position.z, 0.1)])
	ok(stuck.is_empty(), "o'yinchi %d ta hududga ikkala spawn'dan tiqilmasdan yetib boradi" % targets.size() + ("" if stuck.is_empty() else " — tiqildi: %s" % str(stuck)))
	report["stuck"] = stuck

	print("\n5) Xaritadan chiqib ketish")
	var esc := 0
	for p in [Vector3(0, 11.0, -24), Vector3(-40, 11.0, 15), Vector3(40, 11.0, 15), Vector3(0, 11.0, 42)]:
		var h := space.intersect_ray(PhysicsRayQueryParameters3D.create(p, p + Vector3.UP * 5.0, 2))
		if h.is_empty():
			esc += 1
	ok(esc == 0, "12 m da ko'rinmas qopqoq hamma joyda (sakrab binoga chiqib bo'lmaydi)")
	var border := 0
	for dir in [Vector3.RIGHT, Vector3.LEFT, Vector3.FORWARD, Vector3.BACK]:
		var h := space.intersect_ray(PhysicsRayQueryParameters3D.create(Vector3(0, 8, 0), Vector3(0, 8, 0) + dir * 200.0, 2))
		if h and h.position.length() < 60.0:
			border += 1
	ok(border == 4, "xarita chegarasida ko'rinmas devor (4 tomon)")

	print("\nAUDIT: %d / %d o'tdi" % [total - fails, total])
	var f := FileAccess.open(ProjectSettings.globalize_path("res://../docs/audit_final.json"), FileAccess.WRITE)
	f.store_string(JSON.stringify(report, " "))
	f.close()
	quit(1 if fails else 0)


func walk_to(nav: RID, to: Vector3, limit: float) -> float:
	var path := NavigationServer3D.map_get_path(nav, pl.global_position, to, true)
	if path.size() < 2:
		return -1.0
	var i := 1
	var t := 0.0
	var last := pl.global_position
	var still := 0.0
	while t < limit:
		var target := path[i]
		var d := Vector2(target.x - pl.global_position.x, target.z - pl.global_position.z)
		if d.length() < 0.35:
			i += 1
			if i >= path.size():
				break
			continue
		pl.ai_move = Vector3(d.x, 0, d.y)
		await physics_frame
		t += 1.0 / 60.0
		still = still + 1.0 / 60.0 if pl.global_position.distance_to(last) < 0.02 else 0.0
		last = pl.global_position
		if still > 2.0:
			break
	pl.ai_move = Vector3.ZERO
	return t if Vector2(to.x - pl.global_position.x, to.z - pl.global_position.z).length() < 0.8 else -1.0
