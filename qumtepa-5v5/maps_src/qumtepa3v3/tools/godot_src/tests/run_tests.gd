extends SceneTree
## Avtomatik tekshiruv. Ishga tushirish (loyiha papkasida):
##   godot --headless --fixed-fps 60 -s res://tests/run_tests.gd
## Natija: har bir tekshiruv [OK] yoki [XATO]; xato bo'lsa chiqish kodi 1.

const MapData := preload("res://scripts/map_data.gd")
const GM := preload("res://scripts/game_mode.gd")

var fails := 0
var total := 0
var main: Node
var gm: Node
var pl: CharacterBody3D


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


func put(x: float, y: float, z: float) -> void:
	pl.teleport(Transform3D(Basis(), Vector3(x, y, z)))


func ray(from: Vector3, to: Vector3, mask: int, inside := false) -> Dictionary:
	var q := PhysicsRayQueryParameters3D.create(from, to, mask)
	q.hit_from_inside = inside
	return pl.get_world_3d().direct_space_state.intersect_ray(q)


func nav_path(a: Vector3, b: Vector3) -> PackedVector3Array:
	var m := pl.get_world_3d().navigation_map
	return NavigationServer3D.map_get_path(m, a, b, true)


func path_len(p: PackedVector3Array) -> float:
	var d := 0.0
	for i in range(1, p.size()):
		d += p[i].distance_to(p[i - 1])
	return d


## O'yinchini navmesh yo'li bo'ylab haqiqiy fizika bilan yurgizadi, vaqtni qaytaradi (yetolmasa -1).
func walk(from: Vector3, to: Vector3, limit: float = 30.0) -> float:
	put(from.x, from.y + 0.1, from.z)
	await frames(3)
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


func _run() -> void:
	main = load("res://main.tscn").instantiate()
	root.add_child(main)
	gm = main.get_node("GameMode")
	pl = main.get_node("Player")
	await frames(40)

	print("\n1) To'qnashuv va spawn nuqtalari")
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

	print("\n2) Sirt turlari (qadam tovushlari uchun)")
	for c in [[Vector3(0, 3, -11), "stone", "Top mid poli"], [Vector3(-17.0, 6, 4.6), "wood", "A default qutisi"],
			[Vector3(5.4, 6, -13.2), "metal", "yashil metall quti"], [Vector3(-10.5, 3, 2.8), "cloth", "qum qoplari"]]:
		var h := ray(c[0], c[0] + Vector3.DOWN * 8, 1)
		var s: String = str(h.collider.get_meta("surface")) if h and h.collider.has_meta("surface") else "?"
		ok(s == c[1], "%s -> %s" % [c[2], s])

	print("\n3) Player clip va grenade clip")
	var h1 := ray(Vector3(0, 20, -12), Vector3(0, -5, -12), 2)
	ok(h1 and h1.position.y > 11.9, "xarita ustida o'yinchi uchun ko'rinmas qopqoq (y = %.1f)" % (h1.position.y if h1 else -1.0))
	var h2 := ray(Vector3(0, 8, -16), Vector3(0, 4.5, -16), 2, true)
	ok(h2.size() > 0, "yopiq yo'lak tomiga chiqib bo'lmaydi")
	var h3 := ray(Vector3(0, 15, 0), Vector3(80, 15, 0), 4)
	ok(h3 and absf(h3.position.x - 25.0) < 1.1, "granata xarita chegarasidan chiqmaydi")
	var h4 := ray(Vector3(0, 15, 0), Vector3(80, 15, 0), 1)
	ok(h4.size() == 0, "granata binolar ustidan ucha oladi (15 m balandlikda to'siq yo'q)")

	print("\n4) NavMesh (botlar uchun)")
	await frames(5)
	NavigationServer3D.map_force_update(pl.get_world_3d().navigation_map)
	var nav: NavigationRegion3D = main.get_node("Navigation")
	ok(nav.navigation_mesh.get_polygon_count() > 50, "navmesh pishirilgan (%d ta poligon)" % nav.navigation_mesh.get_polygon_count())
	var pts := {"T spawn": Vector3(0, 0, -20), "CT spawn": Vector3(0, 0, 18), "A plant": Vector3(-15, 0, 8), "B plant": Vector3(16, 0, 7)}
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

	print("\n5) Haqiqiy yurish vaqtlari (fizika bilan, 4.5 m/s)")
	gm.skip_freeze()
	await frames(3)
	for w in [["T spawn", "A plant"], ["T spawn", "B plant"], ["CT spawn", "A plant"], ["CT spawn", "B plant"]]:
		var tt := await walk(pts[w[0]], pts[w[1]])
		ok(tt > 0.0, "%s -> %s: %.1f s" % [w[0], w[1], tt])
	var tp := await walk(Vector3(-15, 0, 8), Vector3(-21.8, 1.3, 10.0))
	ok(tp > 0.0 and pl.global_position.y > 1.2, "A platformasiga zina orqali chiqiladi (%.1f s)" % tp)
	tp = await walk(Vector3(16, 0, 7), Vector3(22.0, 1.3, 6.5))
	ok(tp > 0.0 and pl.global_position.y > 1.2, "B platformasiga zina orqali chiqiladi (%.1f s)" % tp)

	print("\n6) Callout (joy nomlari)")
	for c in [[Vector3(-20, 0, -8), "Long"], [Vector3(0, 0, -11), "Top mid"], [Vector3(-15, 0, 8), "A site"],
			[Vector3(16, 0, 7), "B site"], [Vector3(4, 0, 4), "Mid doors"], [Vector3(-10, 0, -8), "Short (catwalk)"]]:
		ok(MapData.callout_at(c[0]) == c[1], "%s -> '%s'" % [c[1], MapData.callout_at(c[0])])

	print("\n7) Raund: tayyorgarlik, sotib olish zonasi")
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
	await secs(4.3)
	ok(gm.phase == GM.Phase.LIVE and not pl.frozen, "5 s dan keyin jang boshlanadi")

	print("\n8) Bomba: site tashqarisida o'rnatib bo'lmaydi, qo'yib yuborsa bekor bo'ladi")
	put(0, 0.1, -11)
	await frames(10)
	Input.action_press("interact")
	await secs(3.5)
	Input.action_release("interact")
	await frames(2)
	ok(gm.bomb_state == "carried", "Top mid'da o'rnatilmadi")
	put(-15, 0.1, 8)
	await frames(10)
	ok(gm.current_site() == "A", "A site zonasi aniqlandi")
	Input.action_press("interact")
	await secs(1.5)
	ok(gm.action == "plant" and pl.busy, "o'rnatish boshlandi, o'yinchi harakatlanmaydi")
	Input.action_release("interact")
	await frames(3)
	ok(gm.action == "" and gm.bomb_state == "carried", "E qo'yib yuborilsa bekor bo'ladi")

	print("\n9) Bomba o'rnatish va zararsizlantirish")
	Input.action_press("interact")
	await secs(3.2)
	Input.action_release("interact")
	await frames(2)
	ok(gm.phase == GM.Phase.PLANTED and gm.planted_site == "A", "bomba A'ga o'rnatildi (3 s)")
	ok(absf(gm.time_left - (35.0 - 0.03)) < 0.3, "bomba taymeri 35 s")
	gm.switch_team()
	await frames(5)
	ok(pl.team == "CT" and pl.global_position.z > 14.0, "F2: CT spawn'ga o'tildi")
	var bp: Vector3 = gm.bomb.global_position
	put(bp.x + 0.8, 0.1, bp.z)
	await frames(10)
	Input.action_press("interact")
	await secs(4.0)
	ok(gm.action == "defuse", "zararsizlantirish jarayonda")
	await secs(3.2)
	Input.action_release("interact")
	await frames(2)
	ok(gm.bomb_state == "defused" and gm.last_winner == "CT" and gm.score["CT"] == 1, "zararsizlantirildi (7 s), CT +1")

	print("\n10) Bomba portlashi")
	await secs(5.3)
	ok(gm.phase == GM.Phase.FREEZE, "5 s dan keyin yangi raund")
	gm.switch_team()
	gm.start_round()
	gm.skip_freeze()
	await frames(3)
	put(16, 0.1, 7)
	await frames(10)
	Input.action_press("interact")
	await secs(3.2)
	Input.action_release("interact")
	await frames(2)
	ok(gm.planted_site == "B", "bomba B'ga o'rnatildi")
	await secs(35.3)
	ok(gm.bomb_state == "exploded" and gm.last_winner == "T" and gm.score["T"] == 1, "35 s da portladi, T +1")

	print("\n11) Vaqt tugashi")
	gm.start_round()
	gm.skip_freeze()
	await frames(3)
	gm.time_left = 0.2
	await secs(0.5)
	ok(gm.last_winner == "CT" and gm.last_reason.begins_with("Vaqt"), "bomba o'rnatilmasa CT yutadi")

	print("\n12) Bombani tashlash va olish")
	gm.start_round()
	gm.skip_freeze()
	await frames(3)
	gm.drop_bomb()
	await frames(2)
	ok(gm.bomb_state == "dropped" and not pl.has_bomb, "G: bomba yerga tashlandi")
	await secs(1.2)
	var db: Vector3 = gm.bomb.global_position
	put(db.x, 0.1, db.z)
	await frames(5)
	ok(gm.bomb_state == "carried" and pl.has_bomb, "ustidan yurilganda qayta olindi")

	print("\n13) Xaritadan tushib ketish")
	put(0, -15, -11)
	await frames(3)
	ok(gm.phase == GM.Phase.ROUND_END and gm.last_reason.contains("tushib"), "tushib ketish aniqlanadi, o'yinchi spawn'ga qaytadi")

	print("\nNATIJA: %d / %d tekshiruv o'tdi" % [total - fails, total])
	main.queue_free()
	await frames(2)
	quit(1 if fails else 0)
