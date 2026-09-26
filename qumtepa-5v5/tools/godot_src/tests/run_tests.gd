extends SceneTree
## Qumtepa 5v5 — avtomatik tekshiruv (greybox). Ishga tushirish (godot/ papkasida):
##   godot --headless --fixed-fps 60 -s res://tests/run_tests.gd
## Har bir tekshiruv [OK] yoki [XATO]; xato bo'lsa chiqish kodi 1.
## Oxirida 2D tahlil va 3D fizika vaqtlari jadvali chiqadi (docs/STAGE2.md uchun).

const MapData := preload("res://scripts/map_data.gd")
const GM := preload("res://scripts/game_mode.gd")
const D := preload("res://tests/test_data.gd")

var fails := 0
var total := 0
var main: Node
var gm: Node
var pl: CharacterBody3D
var R: Dictionary = MapData.ROUND
var timing_rows: Array = []


func ok(cond: bool, msg: String) -> void:
	total += 1
	print(("  [OK]   " if cond else "  [XATO] ") + msg)
	if not cond:
		fails += 1


func frames(n: int) -> void:
	for i in n:
		await physics_frame


func secs(t: float) -> void:
	await frames(int(t * 60.0))


func _initialize() -> void:
	_run.call_deferred()


func put(p: Vector3) -> void:
	pl.teleport(Transform3D(Basis(), p + Vector3.UP * 0.1))


func ray(from: Vector3, to: Vector3, mask: int, inside := false) -> Dictionary:
	var q := PhysicsRayQueryParameters3D.create(from, to, mask)
	q.hit_from_inside = inside
	return pl.get_world_3d().direct_space_state.intersect_ray(q)


func nav_path(a: Vector3, b: Vector3) -> PackedVector3Array:
	return NavigationServer3D.map_get_path(pl.get_world_3d().navigation_map, a, b, true)


func path_len(p: PackedVector3Array) -> float:
	var d := 0.0
	for i in range(1, p.size()):
		d += p[i].distance_to(p[i - 1])
	return d


## O'yinchini hozirgi joyidan navmesh yo'li bo'ylab haqiqiy fizika bilan yurgizadi. Vaqt (s) yoki -1.
func walk_to(to: Vector3, limit: float = 40.0) -> float:
	var path := nav_path(pl.global_position, to)
	if path.size() < 2:
		return -1.0
	var i := 1
	var t := 0.0
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
	pl.ai_move = Vector3.ZERO
	var end := Vector2(to.x - pl.global_position.x, to.z - pl.global_position.z).length()
	return t if end < 0.8 else -1.0


func walk(from: Vector3, to: Vector3, limit: float = 40.0) -> float:
	gm.time_left = 1.0e6   # uzun yurish testlari paytida raund vaqti tugab qolmasin
	put(from)
	await frames(3)
	return await walk_to(to, limit)


func walk_route(wps: Array) -> float:
	gm.time_left = 1.0e6
	put(wps[0])
	await frames(3)
	var tot := 0.0
	for k in range(1, wps.size()):
		var t := await walk_to(wps[k])
		if t < 0.0:
			return -1.0
		tot += t
	return tot


func _run() -> void:
	main = load("res://main.tscn").instantiate()
	root.add_child(main)
	gm = main.get_node("GameMode")
	pl = main.get_node("Player")
	await frames(40)

	print("\n1) Spawn nuqtalari va pol")
	ok(pl.is_on_floor() and absf(pl.global_position.y) < 0.2, "o'yinchi T spawn'da polda turibdi (y = %.2f)" % pl.global_position.y)
	for team in ["T", "CT"]:
		var sp := get_nodes_in_group("spawn_" + team)
		ok(sp.size() == 5, "%s: 5 ta spawn nuqtasi" % team)
		var good := 0
		for s in sp:
			var h := ray(s.global_position + Vector3.UP, s.global_position + Vector3.DOWN, 1)
			if h and absf(h.position.y) < 0.05:
				good += 1
		ok(good == sp.size(), "%s: barcha spawn'lar ostida pol bor (%d/%d)" % [team, good, sp.size()])
	var blocked := 0
	var pairs := 0
	for a in get_nodes_in_group("spawn_T"):
		for b in get_nodes_in_group("spawn_CT"):
			pairs += 1
			if ray(a.global_position + Vector3.UP * 1.6, b.global_position + Vector3.UP * 1.6, 1):
				blocked += 1
	ok(blocked == pairs, "T va CT spawn'lari bir-birini ko'rmaydi (%d/%d chiziq to'silgan)" % [blocked, pairs])

	print("\n2) Sirt turlari (qadam tovushlari uchun)")
	for c in D.SURFACES:
		var h := ray(c[0], c[0] + Vector3.DOWN * 8, 1)
		var s: String = str(h.collider.get_meta("surface")) if h and h.collider.has_meta("surface") else "?"
		ok(s == c[1], "%s -> %s" % [c[2], s])

	print("\n3) Player clip va grenade clip")
	var h1 := ray(Vector3(0, 20, -24), Vector3(0, -5, -24), 2)
	ok(h1 and h1.position.y > 11.9, "xarita ustida o'yinchi uchun ko'rinmas qopqoq (y = %.1f)" % (h1.position.y if h1 else -1.0))
	var cp := D.COVERED_POINT
	var h2 := ray(cp + Vector3.UP * 8.0, cp + Vector3.UP * (D.COVERED_H + 0.6), 2, true)
	ok(h2.size() > 0, "yopiq yo'lak tomiga chiqib bo'lmaydi")
	var h3 := ray(Vector3(0, 15, 0), Vector3(D.MAP_MAX + 30, 15, 0), 4)
	ok(h3 and absf(h3.position.x - D.MAP_MAX) < 1.1, "granata xarita chegarasidan chiqmaydi (x = %.1f)" % (h3.position.x if h3 else -1.0))
	var h4 := ray(Vector3(D.MAP_MIN + 1, 15, 0), Vector3(D.MAP_MAX - 1, 15, 0), 1)
	ok(h4.size() == 0, "granata binolar ustidan ucha oladi (15 m da to'siq yo'q)")
	var wt := D.WALL_TOP
	var h5 := ray(Vector3(wt.x, 11.5, wt.z), Vector3(wt.x, wt.y + 0.05, wt.z), 2, true)
	ok(h5.size() > 0, "quduq/xaroba ustiga chiqib bo'lmaydi (player clip)")
	var oc := D.OPEN_CONTROL
	var h6 := ray(Vector3(oc.x, 11.5, oc.z), Vector3(oc.x, 0.5, oc.z), 2)
	ok(h6.size() == 0, "ochiq site ustida ortiqcha clip yo'q (sakrash, granata)")

	print("\n4) Ko'rish chiziqlari (3D, ko'z balandligi 1.6 m)")
	var mo: Array = D.MID_DOORS_OPEN
	var mw: Array = D.MID_DOORS_WALL
	ok(ray(mo[0], mo[1], 1).size() == 0, "Mid doors eshigidan Top mid <-> CT mid ko'rinadi (snayper dueli)")
	ok(ray(mw[0], mw[1], 1).size() > 0, "Mid doors devori orqasidan ko'rinmaydi")
	var sm := get_nodes_in_group("smoke_targets")
	var sm_ok := 0
	for s in sm:
		var up := ray(s.global_position + Vector3.UP * 0.5, s.global_position + Vector3.UP * 25.0, 1 | 4)
		if up.is_empty():
			sm_ok += 1
		else:
			print("         tepasi yopiq: ", s.get_meta("label"))
	ok(sm_ok == sm.size(), "smoke nishonlari ochiq osmon ostida — granata tushadi (%d/%d)" % [sm_ok, sm.size()])

	print("\n5) NavMesh (botlar uchun)")
	await frames(5)
	NavigationServer3D.map_force_update(pl.get_world_3d().navigation_map)
	var nav: NavigationRegion3D = main.get_node("Navigation")
	ok(nav.navigation_mesh.get_polygon_count() > 200, "navmesh pishirilgan (%d ta poligon)" % nav.navigation_mesh.get_polygon_count())
	var pts := {"T spawn": D.T_SPAWN, "CT spawn": D.CT_SPAWN, "A plant": D.A_PLANT, "B plant": D.B_PLANT}
	for pair in [["T spawn", "A plant"], ["T spawn", "B plant"], ["CT spawn", "A plant"], ["CT spawn", "B plant"]]:
		var p := nav_path(pts[pair[0]], pts[pair[1]])
		var reach := p.size() > 1 and p[-1].distance_to(pts[pair[1]]) < 0.6
		ok(reach, "%s -> %s: yo'l bor, %.1f m" % [pair[0], pair[1], path_len(p)])
	var ai_ok := 0
	var ai := get_nodes_in_group("ai_points")
	for a in ai:
		var start: Vector3 = pts["T spawn"] if str(a.get_meta("team")) == "T" else pts["CT spawn"]
		var p := nav_path(start, a.global_position)
		if p.size() > 1 and p[-1].distance_to(a.global_position) < 0.8:
			ai_ok += 1
		else:
			print("         yetib bo'lmadi: ", a.get_meta("label"))
	ok(ai_ok == ai.size(), "bot nuqtalariga yo'l bor (%d/%d)" % [ai_ok, ai.size()])

	print("\n6) Haqiqiy yurish vaqtlari (fizika bilan, 4.5 m/s) va 2D tahlil bilan solishtirish")
	gm.skip_freeze()
	await frames(3)
	var sh := {}
	for w in [["T→A", "T spawn", "A plant"], ["T→B", "T spawn", "B plant"], ["CT→A", "CT spawn", "A plant"], ["CT→B", "CT spawn", "B plant"]]:
		var tt := await walk(pts[w[1]], pts[w[2]])
		var e: float = D.SHORTEST_2D[w[0]]
		sh[w[0]] = tt
		timing_rows.append([w[0] + " (eng qisqa)", e, tt])
		ok(tt > 0.0 and absf(tt - e) / e < 0.12, "%s: 3D %.1f s, 2D %.1f s (farq %+.0f%%, ≤ 12%%)" % [w[0], tt, e, (tt - e) / e * 100.0])
	## eng yaxshi vaqt: navmesh yo'li va har bir yo'nalish bo'yicha yurishning eng tezi
	## (navmesh yo'li har doim ham eng qisqasi emas, shuning uchun ikkalasi ham hisobga olinadi)
	for r in D.ROUTES:
		var tt := await walk_route(r[2])
		var e: float = r[3]
		timing_rows.append([r[0], e, tt])
		ok(tt > 0.0 and absf(tt - e) / e < 0.12, "%s: 3D %.1f s, 2D %.1f s (farq %+.0f%%)" % [r[0], tt, e, (tt - e) / e * 100.0])
		var key: String = ("T" if r[1] == "T" else "CT") + "→" + ("A" if " A " in r[0] + " " else ("B" if " B " in r[0] + " " else "-"))
		if sh.has(key) and tt > 0.0:
			sh[key] = minf(sh[key], tt)
	ok(absf(sh["T→A"] - sh["T→B"]) <= 1.0, "3D eng tez: T uchun A %.1f s, B %.1f s — farq ≤ 1 s" % [sh["T→A"], sh["T→B"]])
	ok(absf(sh["CT→A"] - sh["CT→B"]) <= 0.6, "3D eng tez: CT uchun A %.1f s, B %.1f s — farq ≤ 0.6 s" % [sh["CT→A"], sh["CT→B"]])
	ok(minf(sh["T→A"], sh["T→B"]) - maxf(sh["CT→A"], sh["CT→B"]) >= 4.0, "3D: CT site'ga T dan kamida 4 s oldin yetadi (%.1f s)" % (minf(sh["T→A"], sh["T→B"]) - maxf(sh["CT→A"], sh["CT→B"])))
	for p in D.PLATFORMS:
		var tp := await walk(p[0], p[1])
		ok(tp > 0.0 and pl.global_position.y > p[1].y - 0.1, "platformaga zina orqali chiqiladi (%.1f s, y = %.2f)" % [tp, pl.global_position.y])

	gm.score = {"T": 0, "CT": 0}
	print("\n7) Callout (joy nomlari)")
	for c in D.CALLOUTS:
		ok(MapData.callout_at(c[0]) == c[1], "%s -> '%s'" % [c[1], MapData.callout_at(c[0])])

	print("\n8) Raund: tayyorgarlik, sotib olish zonasi")
	gm.start_round()
	await frames(5)
	ok(gm.phase == GM.Phase.FREEZE and pl.frozen, "raund tayyorgarlikdan boshlanadi, o'yinchi qotgan")
	ok(gm.in_buy_zone(), "T spawn'da sotib olish mumkin")
	ok(pl.has_bomb and gm.bomb_state == "carried", "bomba T'da")
	var z0 := pl.global_position
	pl.ai_move = Vector3(0, 0, 1)
	await secs(1.0)
	pl.ai_move = Vector3.ZERO
	ok(pl.global_position.distance_to(z0) < 0.05, "tayyorgarlikda yurib bo'lmaydi")
	await secs(R.freeze - 1.0 + 0.3)
	ok(gm.phase == GM.Phase.LIVE and not pl.frozen, "%d s dan keyin jang boshlanadi" % int(R.freeze))

	print("\n9) Bomba: site tashqarisida o'rnatib bo'lmaydi, qo'yib yuborsa bekor bo'ladi")
	put(Vector3(0, 0, -24))
	await frames(10)
	Input.action_press("interact")
	await secs(R.plant_time + 0.5)
	Input.action_release("interact")
	await frames(2)
	ok(gm.bomb_state == "carried", "Top mid'da o'rnatilmadi")
	put(D.A_PLANT)
	await frames(10)
	ok(gm.current_site() == "A", "A site zonasi aniqlandi")
	Input.action_press("interact")
	await secs(1.5)
	ok(gm.action == "plant" and pl.busy, "o'rnatish boshlandi, o'yinchi harakatlanmaydi")
	Input.action_release("interact")
	await frames(3)
	ok(gm.action == "" and gm.bomb_state == "carried", "E qo'yib yuborilsa bekor bo'ladi")

	print("\n10) Bomba o'rnatish va zararsizlantirish")
	Input.action_press("interact")
	await secs(R.plant_time + 0.2)
	Input.action_release("interact")
	await frames(2)
	ok(gm.phase == GM.Phase.PLANTED and gm.planted_site == "A", "bomba A'ga o'rnatildi (%d s)" % int(R.plant_time))
	ok(absf(gm.time_left - R.bomb_timer) < 0.3, "bomba taymeri %d s" % int(R.bomb_timer))
	gm.switch_team()
	await frames(5)
	ok(pl.team == "CT" and pl.global_position.distance_to(D.CT_SPAWN) < 6.0, "F2: CT spawn'ga o'tildi")
	var bp: Vector3 = gm.bomb.global_position
	put(Vector3(bp.x + 0.8, 0, bp.z))
	await frames(10)
	Input.action_press("interact")
	await secs(R.defuse_time * 0.5)
	ok(gm.action == "defuse", "zararsizlantirish jarayonda")
	await secs(R.defuse_time * 0.5 + 0.3)
	Input.action_release("interact")
	await frames(2)
	ok(gm.bomb_state == "defused" and gm.last_winner == "CT" and gm.score["CT"] == 1, "zararsizlantirildi (%d s), CT +1" % int(R.defuse_time))

	print("\n11) Bomba portlashi")
	await secs(R.round_end + 0.3)
	ok(gm.phase == GM.Phase.FREEZE, "%d s dan keyin yangi raund" % int(R.round_end))
	gm.switch_team()
	gm.start_round()
	gm.skip_freeze()
	await frames(3)
	put(D.B_PLANT)
	await frames(10)
	Input.action_press("interact")
	await secs(R.plant_time + 0.2)
	Input.action_release("interact")
	await frames(2)
	ok(gm.planted_site == "B", "bomba B'ga o'rnatildi")
	await secs(R.bomb_timer + 0.3)
	ok(gm.bomb_state == "exploded" and gm.last_winner == "T" and gm.score["T"] == 1, "%d s da portladi, T +1" % int(R.bomb_timer))

	print("\n12) Vaqt tugashi")
	gm.start_round()
	gm.skip_freeze()
	await frames(3)
	gm.time_left = 0.2
	await secs(0.5)
	ok(gm.last_winner == "CT" and gm.last_reason.begins_with("Vaqt"), "bomba o'rnatilmasa CT yutadi")

	print("\n13) Bombani tashlash va olish")
	gm.start_round()
	gm.skip_freeze()
	await frames(3)
	gm.drop_bomb()
	await frames(2)
	ok(gm.bomb_state == "dropped" and not pl.has_bomb, "G: bomba yerga tashlandi")
	await secs(1.2)
	var db: Vector3 = gm.bomb.global_position
	put(Vector3(db.x, 0, db.z))
	await frames(5)
	ok(gm.bomb_state == "carried" and pl.has_bomb, "ustidan yurilganda qayta olindi")

	print("\n14) Xaritadan tushib ketish")
	put(Vector3(0, -15, -24))
	await frames(3)
	ok(gm.phase == GM.Phase.ROUND_END and gm.last_reason.contains("tushib"), "tushib ketish aniqlanadi, o'yinchi spawn'ga qaytadi")

	print("\nVAQTLAR (2D tahlil -> 3D fizika):")
	for row in timing_rows:
		print("  %-28s %5.1f s -> %5.1f s" % [row[0], row[1], row[2]])
	print("\nNATIJA: %d / %d tekshiruv o'tdi" % [total - fails, total])
	main.queue_free()
	await frames(2)
	quit(1 if fails else 0)
