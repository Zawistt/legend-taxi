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
	if main.get_node_or_null("Bots"):
		main.get_node("Bots").enabled = false      # botlarsiz: xarita va mexanika sinovi
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

	print("\n15) Yorug'lik, atmosfera va tovush (6-bosqich)")
	var sun: DirectionalLight3D = main.get_node("Sun")
	var ld := -sun.global_transform.basis.z          # yorug'lik yo'nalishi
	var elev := rad_to_deg(asin(-ld.y))
	ok(elev >= 40.0 and elev <= 65.0, "quyosh balandligi %.0f° (40–65°: soyalar aniq, ko'zni qamashtirmaydi)" % elev)
	var ns := absf(ld.z) / Vector2(ld.x, ld.z).length()
	ok(ns <= 0.2, "quyosh sharq-g'arb o'qida (shimol-janub ulushi %.2f ≤ 0.2): T ham, CT ham quyoshga qarab o'ynamaydi" % ns)
	var env: Environment = (main.get_node("WorldEnvironment") as WorldEnvironment).environment
	ok(env.ssao_enabled and env.ssil_enabled and env.glow_enabled, "SSAO, SSIL va glow yoqilgan")
	ok(env.fog_density <= 0.003 and env.volumetric_fog_density <= 0.006, "tuman yengil (uzoq ko'rish chiziqlari xiralashmaydi)")
	ok(AudioServer.get_bus_index("Reverb") >= 0 and AudioServer.get_bus_index("Ambient") >= 0, "Reverb va Ambient tovush shinalari bor")
	var amb := get_nodes_in_group("ambient")
	var amb_ok := 0
	var districts := {}
	for p in amb:
		var st: AudioStreamWAV = p.stream
		if p.volume_db <= -18.0 and p.bus == &"Ambient" and st and st.loop_mode != AudioStreamWAV.LOOP_DISABLED:
			amb_ok += 1
		districts[str(p.get_meta("district"))] = true
	ok(amb.size() >= 6 and amb_ok == amb.size(), "fon tovushlari: %d ta manba, hammasi halqada va ≤ −18 dB (qadam tovushini bosmaydi)" % amb.size())
	ok(districts.size() == 6, "6 xil fon: %s" % ", ".join(districts.keys()))
	var q := PhysicsPointQueryParameters3D.new()
	q.collide_with_areas = true
	q.collide_with_bodies = false
	q.collision_mask = 64
	var rv_ok := 0
	var lit_ok := 0
	var lamps := get_nodes_in_group("lamps")
	for cpos in D.COVERED_CELLS:
		q.position = cpos
		for h in pl.get_world_3d().direct_space_state.intersect_point(q, 8):
			if h.collider is Area3D and h.collider.reverb_bus_enabled:
				rv_ok += 1
				break
		for l in lamps:
			if Vector2(l.global_position.x - cpos.x, l.global_position.z - cpos.z).length() <= 6.0:
				lit_ok += 1
				break
	ok(rv_ok == D.COVERED_CELLS.size(), "hamma yopiq kataklarda aks-sado bor (%d/%d)" % [rv_ok, D.COVERED_CELLS.size()])
	ok(lit_ok == D.COVERED_CELLS.size(), "hamma yopiq kataklar chiroqdan ≤ 6 m (%d/%d): qorong'i burchak yo'q" % [lit_ok, D.COVERED_CELLS.size()])

	print("\n16) Optimallashtirish va minimap (7-bosqich)")
	var occ := main.get_node("Occluders").get_child_count()
	ok(occ >= 100 and ProjectSettings.get_setting("rendering/occlusion_culling/use_occlusion_culling"), "occlusion culling yoqilgan, %d ta bino occluder'i" % occ)
	var lodn: Node = main.get_node("MapLOD")
	var hidden_gameplay := 0
	var chunks := 0
	var stack := [main.get_node("Map")]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		if n is GeometryInstance3D:
			chunks += 1
			var gi := n as GeometryInstance3D
			if gi.visibility_range_end > 0.0 and not ("_Decor_" in n.name):
				hidden_gameplay += 1
		stack.append_array(n.get_children())
	ok(lodn.decor_nodes > 20 and hidden_gameplay == 0, "masofada faqat bezak so'nadi (%d bo'lak); panalar, devorlar, pol doim ko'rinadi (%d ta mesh bo'lagi)" % [lodn.decor_nodes, chunks])
	var fade_ok := 0
	for l in get_nodes_in_group("lamps"):
		if (l as Light3D).distance_fade_enabled:
			fade_ok += 1
	ok(fade_ok == get_nodes_in_group("lamps").size(), "hamma chiroqlar uzoqda so'nadi (%d)" % fade_ok)
	ok(sun.directional_shadow_mode == DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS and sun.directional_shadow_max_distance <= 90.0, "quyosh soyasi: 2 bo'lak, ≤ 90 m")
	var mm: Control = main.get_node_or_null("UI/Minimap")
	ok(mm != null and mm.MAP != null and mm.player == pl, "minimap bor va o'yinchini kuzatadi")

	print("\n17) Stilizatsiya qilingan low-poly ko'rinish")
	var lp_mats := {}
	var lp_tex := 0
	var lp_vc := 0
	var lp_surf := 0
	var lp_smooth := 0
	var lstack := [main.get_node("Map")]
	while not lstack.is_empty():
		var n: Node = lstack.pop_back()
		lstack.append_array(n.get_children())
		if not (n is MeshInstance3D) or (n as MeshInstance3D).mesh == null:
			continue
		var mesh: Mesh = (n as MeshInstance3D).mesh
		for i in mesh.get_surface_count():
			var lpm := mesh.surface_get_material(i) as BaseMaterial3D
			if lpm == null or lpm.resource_name.begins_with("site_"):
				continue
			lp_surf += 1
			lp_mats[lpm.resource_name] = true
			if lpm.albedo_texture or lpm.normal_texture:
				lp_tex += 1
			var arr := mesh.surface_get_arrays(i)
			if arr[Mesh.ARRAY_COLOR] != null and lpm.vertex_color_use_as_albedo:
				lp_vc += 1
			# tekis soya: har uchburchakning 3 ta normali bir xil (uchlar ulashilmagan)
			var nr: PackedVector3Array = arr[Mesh.ARRAY_NORMAL]
			var ix: PackedInt32Array = arr[Mesh.ARRAY_INDEX] if arr[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
			var tri_n := (ix.size() if ix.size() else nr.size()) / 3
			for t in mini(tri_n, 40):
				var i0 := ix[t * 3] if ix.size() else t * 3
				var i1 := ix[t * 3 + 1] if ix.size() else t * 3 + 1
				var i2 := ix[t * 3 + 2] if ix.size() else t * 3 + 2
				if nr[i0].dot(nr[i1]) < 0.999 or nr[i0].dot(nr[i2]) < 0.999:
					lp_smooth += 1
					break
	ok(lp_surf > 200 and lp_tex == 0 and lp_mats.size() >= 25, "tekis rangli materiallar: %d ta sirt, %d xil rang, teksturasiz" % [lp_surf, lp_mats.size()])
	ok(lp_vc == lp_surf, "yuzalar orasida rang farqi va devor tagida yumshoq qorayish (vertex rang): %d/%d sirt" % [lp_vc, lp_surf])
	ok(lp_smooth == 0, "tekis soya (flat shading): silliqlangan sirt yo'q")
	ok(main.get_node_or_null("Decals") == null and main.get_node_or_null("Materials") == null, "PBR teksturalar va decal'lar yo'q")
	var skym = env.sky.sky_material if env.sky else null
	ok(skym is ProceduralSkyMaterial and env.ambient_light_source == Environment.AMBIENT_SOURCE_SKY, "gradient osmon, atrof yorug'ligi osmondan")
	ok(not env.sdfgi_enabled and not env.ssr_enabled and not env.volumetric_fog_enabled, "og'ir effektlar (SDFGI, SSR, hajmli tuman) o'chirilgan")

	await section_characters()
	await section_views()
	await section_weapons()
	await section_cs2()

	print("\nVAQTLAR (2D tahlil -> 3D fizika):")
	for row in timing_rows:
		print("  %-28s %5.1f s -> %5.1f s" % [row[0], row[1], row[2]])
	print("\nNATIJA: %d / %d tekshiruv o'tdi" % [total - fails, total])
	main.queue_free()
	await frames(2)
	quit(1 if fails else 0)


## 18-bo'lim alohida funksiyada (o'zgaruvchi nomlari _run bilan to'qnashmasin)
func section_characters() -> void:
	print("\n18) Personajlar (vaqtinchalik low-poly o'rinbosar), harakat turlari")
	for key in ["T", "CT"]:
		var chm = load("res://scripts/character_model.gd").new()
		chm.team = key
		root.add_child(chm)
		await frames(2)
		var nmesh: int = chm.find_children("*", "MeshInstance3D", true, false).size()
		var gun: Node3D = chm.model.find_child("Weapon", true, false)
		if chm.rig:
			ok(nmesh >= 2 and gun != null and chm.skel.find_bone("chest") >= 0 and chm.hitboxes.size() >= 13,
				"%s: 3-shaxs skeletli model (%d mesh, qurol \"weapon\" suyagida, %d o'q zonasi suyaklarga bog'langan)" % [key, nmesh, chm.hitboxes.size()])
		else:
			ok(chm.PLACEHOLDER and nmesh >= 5 and nmesh <= 9 and gun != null and chm.skel.find_bone("chest") >= 0,
				"%s: o'rinbosar manekin (qutilar %d ta mesh'ga birlashtirilgan, qurol ko'krakka bog'langan)" % [key, nmesh])
		chm.crouching = true
		await secs(0.6)
		var e_c: float = chm.eye_point().y
		chm.crouching = false
		chm.die()
		await secs(0.6 if chm.rig == null else chm.anim.get_animation("death").length + 0.3)
		var lying: bool
		if chm.rig:
			lying = chm.eye_point().y < 0.7                     # skeletli model: "death" klipi — yerda yotadi
		else:
			lying = absf(chm.model.rotation.x) > 1.4
		chm.revive()
		await secs(0.3)
		var up_ok: bool = chm.eye_point().y > 1.4 if chm.rig else chm.model.rotation.x == 0.0
		ok(e_c < 1.35 and lying and up_ok, "%s: o'tirish (ko'z %.2f m), o'lim (yiqiladi) va qayta tirilish%s" % [key, e_c,
			" — skeletli model, %d animatsiya (yotgan %s, turgan %s)" % [chm.anim.get_animation_list().size(), lying, up_ok] if chm.rig else ""])
		chm.queue_free()
	# harakat turlari: oddiy (qadam eshitiladi), Shift (sekin, jim), o'tirish (sekin, jim, past), sakrash (qo'nish tovushi)
	gm.skip_freeze()
	gm.time_left = 1.0e6
	var open_pt := Vector3(0, 0.1, -24)
	var mvmodes := [["oddiy", false, false, 4.5, true], ["Shift — sekin yurish", true, false, 2.3, false], ["o'tirib yurish", false, true, 1.55, false]]
	for mo in mvmodes:
		pl.teleport(Transform3D(Basis(), open_pt))
		pl.force_walk = mo[1]
		pl.force_crouch = mo[2]
		await frames(3)
		var st0: int = pl.steps_played
		var pp0: Vector3 = pl.global_position
		pl.ai_move = Vector3(1, 0, 0)
		await secs(1.5)
		pl.ai_move = Vector3.ZERO
		var vv := Vector2(pl.global_position.x - pp0.x, pl.global_position.z - pp0.z).length() / 1.5
		var nst: int = pl.steps_played - st0
		ok(absf(vv - mo[3]) < 0.25 and ((nst >= 3) if mo[4] else (nst == 0)),
			"%s: %.2f m/s, qadam tovushi %d ta%s" % [mo[0], vv, nst, " (eshitiladi)" if mo[4] else " (jim)"])
	ok(pl.crouching and absf((pl.get_node("CollisionShape3D").shape as CapsuleShape3D).height - 1.25) < 0.01 and pl.cam.position.y < 1.2,
		"o'tirganda bo'y 1.25 m, ko'z %.2f m" % pl.cam.position.y)
	pl.force_crouch = false
	pl.force_walk = false
	await frames(3)
	ok(not pl.crouching, "tugma qo'yib yuborilganda qaddini tiklaydi")
	var ld0: int = pl.lands_played
	pl.velocity.y = pl.jump_velocity
	await secs(1.2)
	ok(pl.lands_played == ld0 + 1, "sakrab qo'nganda tovush chiqadi")
	var fpv = pl.get_node_or_null("Camera3D/FPView")
	ok(fpv != null and fpv.ch != null and fpv.ch.model != null, "birinchi shaxs: qo'llar va qurol kamerada")
	if fpv:
		var am0: int = fpv.ammo
		fpv.fire()
		await frames(2)
		ok(fpv.ammo == am0 - 1 and fpv.ch.fire_count == 1, "o'q uzish: o'q soni kamaydi, tepki")


## 19-bo'lim: o'yinchi o'ziga 1-shaxs, boshqalarga 3-shaxs
func section_views() -> void:
	print("\n19) Ko'rinish: o'yinchining o'ziga 1-shaxs, boshqalarga 3-shaxs")
	var CM := preload("res://scripts/character_model.gd")
	var body: Node3D = pl.get_node_or_null("Body")
	var fpv = pl.get_node_or_null("Camera3D/FPView")
	pl.cam.make_current()
	await frames(2)
	var body_meshes: Array = body.find_children("*", "MeshInstance3D", true, false) if body else []
	var vm_meshes: Array = fpv.ch.find_children("*", "MeshInstance3D", true, false) if fpv else []
	var body_ok := body_meshes.size() >= 2
	for m in body_meshes:
		body_ok = body_ok and m.layers == CM.LAYER_OWN_BODY and m.cast_shadow != GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var vm_ok := vm_meshes.size() >= 2
	for m in vm_meshes:
		vm_ok = vm_ok and m.layers == CM.LAYER_VIEWMODEL and m.cast_shadow == GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	ok(body_ok and (pl.cam.cull_mask & CM.LAYER_OWN_BODY) == 0,
		"o'yinchining o'z kamerasi o'z tanasini ko'rmaydi (%d mesh, 11-qatlam), lekin tana soya tashlaydi" % body_meshes.size())
	ok(vm_ok and (pl.cam.cull_mask & CM.LAYER_VIEWMODEL) != 0 and fpv.ch.visible,
		"o'z kamerasida 1-shaxs qo'llar va qurol ko'rinadi (12-qatlam, soyasiz)")
	# boshqa kamera (tomoshabin / boshqa o'yinchi)
	var other := Camera3D.new()
	main.add_child(other)
	other.global_position = pl.global_position + Vector3(0, 1.8, 4.0)
	other.make_current()
	await frames(2)
	ok((other.cull_mask & CM.LAYER_OWN_BODY) != 0 and body.visible and not fpv.ch.visible,
		"boshqa kamera o'yinchini 3-shaxs to'liq tana sifatida ko'radi, 1-shaxs qo'llar esa unga ko'rinmaydi")
	other.queue_free()
	pl.cam.make_current()
	await frames(2)
	# tana o'yinchi holatiga ergashadi: o'tirish, harakat, qarash burchagi
	pl.force_crouch = true
	pl.ai_move = Vector3(0, 0, -1)
	await frames(20)
	var follows: bool = body.crouching and body.velocity_local.z > 1.0
	pl.force_crouch = false
	pl.ai_move = Vector3.ZERO
	await frames(10)
	var chest: int = body.skel.find_bone("chest")
	pl.cam.rotation.x = 0.0
	await frames(3)
	var c0: Vector3 = body.skel.get_bone_global_pose(chest).basis.y
	pl.cam.rotation.x = 0.6
	await frames(3)
	var c1: Vector3 = body.skel.get_bone_global_pose(chest).basis.y
	pl.cam.rotation.x = 0.0
	ok(follows and c0.angle_to(c1) > 0.25, "3-shaxs tana o'yinchiga ergashadi: o'tirish, yurish, tepaga qarasa tana egiladi (%.0f°)" % rad_to_deg(c0.angle_to(c1)))
	# masofaviy (tarmoqdagi) o'yinchi: faqat 3-shaxs
	var remote: CharacterBody3D = load("res://scenes/player.tscn").instantiate()
	remote.local_player = false
	remote.name = "RemotePlayer"
	main.add_child(remote)
	remote.global_position = pl.global_position + Vector3(2, 0, 0)
	await frames(3)
	var rb: Node3D = remote.get_node_or_null("Body")
	var r_ok: bool = remote.get_node_or_null("Camera3D/FPView") == null and rb != null and not rb.own_body and pl.cam.current
	for m in rb.find_children("*", "MeshInstance3D", true, false):
		r_ok = r_ok and m.layers == CM.LAYER_WORLD
	ok(r_ok, "masofaviy o'yinchi: 1-shaxs yo'q, 3-shaxs tana hamma kameraga (shu jumladan bizning kameraga) ko'rinadi")
	remote.queue_free()
	await frames(2)


func _aim_at(p: Vector3) -> void:
	var e: Vector3 = pl.global_position + Vector3.UP * pl.cam.position.y
	var d := (p - e).normalized()
	pl.rotation.y = atan2(-d.x, -d.z)
	pl.cam.rotation.x = asin(d.y)


func _zone_pos(t: Node3D, zone: String) -> Vector3:
	for h in t.model.hitboxes:
		if h.get_meta("zone") == zone:
			return h.global_position
	return t.global_position


## 20-bo'lim: qurol tizimi (CS2): standart to'pponcha, sotib olish, zonalar, zirh, tepki, optika, o'q to'ldirish, Zeus
func section_weapons() -> void:
	print("\n20) Qurollar (CS2): zonalar, zirh, tepki, optika, sotib olish, raundda o'q to'ldirish, Zeus")
	var fpv = pl.get_node("Camera3D/FPView")
	var pr = main.get_node_or_null("Practice")
	var bm = fpv.buy_menu
	var lo = pl.loadout
	var Rules = load("res://scripts/cs_rules.gd")
	gm.match_winner = "T"
	gm.start_round()                 # yangi o'yin: hamma $800, T — Glock-18
	await frames(4)
	ok(lo.money == 800 and lo.primary == null and lo.secondary.weapon_id == "glock" and fpv.current.weapon_id == "glock"
		and fpv.ammo == 20 and pl.body.weapon_kind == 1,
		"o'yin boshi: $%d, qo'lda Glock-18 (20/%d), asosiy qurol yo'q" % [lo.money, fpv.reserve])
	var cats := []
	for c in bm.CATS:
		cats.append("%s %d" % [c[1], bm.items_of(c[0]).size()])
	ok(Rules.catalog().size() >= 27 and bm.items_of("rifle").has("ak47") and not bm.items_of("rifle").has("m4a4")
		and bm.items_of("grenade").has("molotov") and not bm.items_of("grenade").has("incendiary") and not bm.items_of("gear").has("kit"),
		"sotib olish bo'limlari (T): %s" % ", ".join(cats))
	var no_money: bool = not bm.buy_item("ak47")
	var why: String = lo.buy_block_reason("ak47", "T")
	lo.money = 16000
	var b1: bool = bm.buy_item("ak47")
	var m1: int = lo.money
	var b2: bool = bm.buy_item("vesthelm")
	var b3: bool = bm.buy_item("m4a4")
	var b4: bool = bm.buy_item("flash") and bm.buy_item("flash") and not bm.buy_item("flash") and bm.buy_item("smoke") and bm.buy_item("he") \
		and not bm.buy_item("he") and not bm.buy_item("molotov")
	await secs(0.8)
	ok(no_money and why != "" and b1 and m1 == 16000 - 2700 and b2 and lo.armor == 100.0 and lo.helmet and not b3 and b4
		and lo.grenades.size() == 4 and fpv.current.weapon_id == "ak47",
		"$800 ga AK-47 olinmaydi (%s); $16000: AK-47 ($2700), zirh+kaska, 2 flesh + tutun + HE (ko'pi bilan 4 granata, flesh 2, HE 1), M4A4 — CT quroli" % why)
	gm.skip_freeze()
	gm.buy_time_left = 0.0
	ok(not bm.buy_item("deagle"), "sotib olish vaqti tugagach sotib olinmaydi")
	gm.time_left = 1.0e6
	pl.force_crouch = false
	pl.force_walk = false
	pl.ai_move = Vector3.ZERO
	pl.teleport(Transform3D(Basis(), Vector3(0, 0.1, -24)))
	pl.rotation.y = -PI * 0.5
	pl.cam.rotation.x = 0.0
	await frames(5)
	var tg: Array = pr.spawn([6.0, 12.0]) if pr else []
	await frames(3)
	ok(tg.size() == 2, "F7 mashq nishonlari: %d ta manekin (o'q tegadigan zonalar bilan)" % tg.size())
	if tg.size() < 2:
		return
	var t0: Node3D = tg[0]
	var t1: Node3D = tg[1]
	t0.hp = 1000.0
	t1.hp = 1000.0
	fpv.no_spread = true
	var W: Resource = fpv.current
	var res := {}
	var hm := false
	for z in [[t1, "head"], [t1, "leg"], [t1, "body"], [t1, "arm"]]:
		fpv._next_shot = 0.0
		_aim_at(_zone_pos(z[0], z[1]))
		await frames(2)
		fpv.fire()
		res[z[1]] = [fpv.last_hit.get("zone", "-"), float(fpv.last_hit.get("damage", 0.0)), float(fpv.last_hit.get("distance", 0.0))]
		await frames(1)
		hm = hm or fpv.hud.hitmarker_visible()
		await secs(0.4)
	var zones_ok := true
	for z in ["head", "leg", "body", "arm"]:
		zones_ok = zones_ok and res[z][0] == z and absf(res[z][1] - W.damage_at(res[z][2], z)) < 0.05
	var bd: float = res.body[1]
	zones_ok = zones_ok and absf(res.head[1] / bd - 4.0) < 0.05 and absf(res.leg[1] / bd - 0.75) < 0.05 and absf(res.arm[1] / bd - 1.0) < 0.05
	ok(zones_ok and bd < 36.0 and bd > 34.5, "AK-47 zonalari (12 m): bosh %.0f, tana %.1f, qo'l %.1f, oyoq %.1f (36 × 4 / 1 / 1 / 0.75, masofa bilan ×0.98^(d/12.7))" % [res.head[1], bd, res.arm[1], res.leg[1]])
	ok(hm, "tegish belgisi HUD'da")
	# zirh (CS2 formulasi)
	var a1: Array = W.damage_vs_armor(36.0, "body", 100.0, true)
	var a2: Array = W.damage_vs_armor(144.0, "head", 100.0, false)
	var a3: Array = W.damage_vs_armor(144.0, "head", 100.0, true)
	var a4: Array = W.damage_vs_armor(27.0, "leg", 100.0, true)
	ok(absf(a1[0] - 27.9) < 0.05 and absf(a1[1] - 4.05) < 0.05 and a2[0] == 144.0 and absf(a3[0] - 111.6) < 0.05 and a4[0] == 27.0,
		"zirh: AK tana 36 -> %.1f (zirhga %.2f); kaskasiz bosh 144 -> %.0f, kaska bilan -> %.1f; oyoqni zirh himoyalamaydi" % [a1[0], a1[1], a2[0], a3[0]])
	# o'ldirish
	t0.hp = 100.0
	fpv._next_shot = 0.0
	_aim_at(_zone_pos(t0, "head"))
	await frames(2)
	fpv.fire()
	var killed: bool = fpv.last_hit.get("killed", false)
	await frames(2)
	var hits_dead: int = t0.hits
	var am_dead: int = fpv.ammo
	fpv._next_shot = 0.0
	fpv.fire()
	ok(killed and t0.model.dead and fpv.ammo == am_dead - 1 and t0.hits == hits_dead, "AK-47 bitta bosh o'qi o'ldiradi; o'lgan nishonga o'q tegmaydi")
	# tepki naqshi va qaytish
	_aim_at(pl.global_position + Vector3(0, 1.6, 0) + (-pl.global_transform.basis.z) * 5.0)
	pl.cam.rotation.x = 0.0
	await secs(0.5)
	var p0: float = pl.cam.rotation.x
	for i in 6:
		fpv._next_shot = 0.0
		fpv.fire()
		await frames(1)
	var kick := rad_to_deg(pl.cam.rotation.x - p0)
	var expect := 0.0
	for i in 6:
		expect += W.recoil_pattern_v[i] * W.recoil_scale
	var bl: float = fpv.bloom
	ok(absf(kick - expect) < 0.3 and bl > W.base_spread, "tepki naqshi: 6 o'qda %.2f° tepaga (kutilgan %.2f°), tarqalish o'sdi" % [kick, expect])
	await secs(1.5)
	ok(absf(rad_to_deg(pl.cam.rotation.x - p0)) < 0.3 and fpv.bloom < W.base_spread * 0.2, "otish to'xtaganda nishon joyiga qaytadi, tarqalish tiklanadi")
	fpv.ammo = 5
	var r0: int = fpv.reserve
	fpv.reload()
	await secs(W.reload_time + 0.2)
	ok(fpv.ammo == 30 and fpv.reserve == r0 - 25, "qayta o'qlash %.1f s: magazin 30, zaxira %d" % [W.reload_time, fpv.reserve])
	fpv.equip(2)
	await secs(0.5)
	var m0: int = fpv.fire_mode
	fpv.cycle_mode()
	var gm1: int = fpv.fire_mode
	fpv.cycle_mode()
	ok(fpv.current.weapon_id == "glock" and fpv.ch.weapon_kind == 1 and pl.body.weapon_kind == 1 and m0 != gm1 and fpv.fire_mode == m0,
		"2-tugma: Glock-18 qo'lda (1- va 3-shaxs), o'q rejimi: bittalik <-> 3 talik")
	fpv.equip(3)
	await secs(0.4)
	fpv._next_shot = 0.0
	_aim_at(_zone_pos(t1, "body"))
	await frames(2)
	var h0: int = t1.hits
	fpv.fire()
	var far_miss: bool = t1.hits == h0
	var dir: Vector3 = (pl.global_position - t1.global_position)
	dir.y = 0.0
	pl.teleport(Transform3D(Basis(), t1.global_position + dir.normalized() * 1.6 + Vector3.UP * 0.1))
	await frames(4)
	fpv._next_shot = 0.0
	_aim_at(_zone_pos(t1, "body"))
	await frames(2)
	fpv.fire()
	ok(far_miss and t1.hits == h0 + 1 and absf(t1.last_damage - 75.0) < 0.1, "pichoq: 12 m da yetmaydi, 1.6 m da 75 zarar")
	# Zeus: pichoq ustida 3 ni yana bosish; bitta otishda o'ldiradi, keyin 30 s zaryadlanadi
	lo.zeus = true
	fpv.equip(3)
	await secs(0.8)
	var zeus_on: bool = fpv.is_zeus()
	t1.hp = 100.0
	fpv._next_shot = 0.0
	_aim_at(_zone_pos(t1, "body"))
	await frames(2)
	var z1: bool = fpv.fire()
	var zk: bool = t1.hp <= 0.0
	fpv._next_shot = 0.0
	var z2: bool = fpv.fire()
	var left: float = lo.zeus_ready_at - Time.get_ticks_msec() / 1000.0
	ok(zeus_on and z1 and zk and not z2 and left > 29.0 and left <= 30.0 and lo.zeus,
		"Zeus x27: 1.6 m da bir otishda o'ldiradi, keyin %.0f s zaryadlanadi (HUD'da foiz)" % left)
	# snayper (AWP): tana 115, zatvor, optika
	pl.teleport(Transform3D(Basis(), Vector3(0, 0.1, -24)))
	pl.rotation.y = -PI * 0.5
	pl.cam.rotation.x = 0.0
	await frames(4)
	pr.clear()
	await frames(2)
	tg = pr.spawn([6.0, 12.0])
	await frames(3)
	t0 = tg[0]
	t1 = tg[1]
	fpv.buy("awp")
	await secs(1.2)
	fpv._next_shot = 0.0
	_aim_at(_zone_pos(t1, "body"))
	await frames(2)
	var s1: bool = fpv.fire()
	var dmg_sn: float = t1.last_damage
	var s2: bool = fpv.fire()
	await secs(1.6)
	var s3: bool = fpv.fire()
	fpv.force_ads = true
	await secs(0.8)
	var sc_ok: bool = fpv.scoped() and pl.cam.fov < 80.0 * 0.45 and not fpv.ch.visible
	fpv.force_ads = false
	await secs(0.8)
	ok(s1 and not s2 and s3 and dmg_sn > 110.0 and dmg_sn <= 115.0 and sc_ok and pl.cam.fov > 79.0,
		"AWP: tana %.0f (bitta o'q o'ldiradi), otishlar orasi 1.46 s, o'ng tugma — optika" % dmg_sn)
	# drobovik: 9 sochma
	fpv.buy("nova")
	await secs(0.8)
	t0.hp = 1000.0
	fpv._next_shot = 0.0
	_aim_at(_zone_pos(t0, "body"))
	await frames(2)
	fpv.fire()
	ok(fpv.last_shot.pellets == 9 and fpv.last_shot.hits == 9, "Nova: bir otishda %d sochma, %d tasi tegdi, jami %.0f zarar" % [fpv.last_shot.pellets, fpv.last_shot.hits, fpv.last_shot.damage])
	# raund boshida o'q to'ladi, tirik qolgan qurolini saqlaydi; o'lsa hammasi yo'qoladi
	fpv.buy("ak47")
	await secs(0.8)
	fpv.ammo = 3
	fpv.reserve = 10
	gm.end_round("T", "test", "elim")
	gm.start_round()
	await frames(4)
	var kept: bool = lo.primary != null and lo.primary.weapon_id == "ak47" and fpv.current.weapon_id == "ak47"
	ok(kept and fpv.ammo == 30 and fpv.reserve == 90 and lo.armor == 100.0, "yangi raund: tirik qolgan AK-47 saqlanadi, o'q to'ladi (30/90), zirh qoladi")
	pl.damage(500.0)
	gm.end_round("CT", "test", "elim")
	gm.start_round()
	await frames(4)
	ok(lo.primary == null and lo.armor == 0.0 and lo.grenades.is_empty() and fpv.current.weapon_id == "glock",
		"o'lsa: qurol, zirh, granatalar yo'qoladi — keyingi raund Glock-18 bilan")
	fpv.no_spread = false
	pr.clear()
	await frames(2)


## 21-bo'lim: CS2 qoidalari — iqtisod, bomba aylanasi va kodi, portlash, granatalar, kill feed, TAB
func section_cs2() -> void:
	print("\n21) CS2 qoidalari: iqtisod, bomba, granatalar, statistika")
	var Rules = load("res://scripts/cs_rules.gd")
	var lo = pl.loadout
	var hud = main.get_node("HUD")
	gm.match_winner = "T"
	gm.start_round()
	await frames(2)
	# iqtisod (pul — o'yinchida; jamoa bir xil hisoblanadi)
	var team: String = pl.team
	var enemy := "CT" if team == "T" else "T"
	var m0: int = lo.money
	gm.end_round(enemy, "test", "elim")
	var lost1: int = lo.money - m0
	gm.start_round()
	m0 = lo.money
	gm.end_round(enemy, "test", "elim")
	var lost2: int = lo.money - m0
	gm.start_round()
	m0 = lo.money
	gm.end_round(team, "test", "elim")
	var won: int = lo.money - m0
	gm.start_round()
	m0 = lo.money
	gm.end_round(enemy, "test", "elim")
	var lost3: int = lo.money - m0
	ok(lost1 == 1900 and lost2 == 2400 and won == 3250 and lost3 == 2400,
		"pul: boshida $800; mag'lubiyat +%d, yana +%d; g'alaba +%d; keyingi mag'lubiyat +%d (g'alaba bonusni bir pog'ona tushiradi)" % [lost1, lost2, won, lost3])
	lo.money = 15900
	gm.start_round()
	gm.end_round(team, "test", "elim")
	ok(lo.money == 16000, "pul chegarasi $16000")
	# bomba: faqat aylana ichida, kod teriladi, $300 + jamoaga $800
	gm.match_winner = "T"
	gm.start_round()
	if pl.team != "T":
		gm.switch_team()
		gm.start_round()
	await frames(2)
	gm.skip_freeze()
	var spots: Dictionary = gm.plant_spots
	ok(spots.has("A") and spots.has("B"), "A va B da o'rnatish aylanasi (radius %.1f m): %s" % [Rules.PLANT_RADIUS, str(spots.keys())])
	if not spots.has("A"):
		return
	var sa: Vector3 = spots["A"]
	put(sa + Vector3(Rules.PLANT_RADIUS + 1.5, 0.1, 0))
	await frames(10)
	var out_circle: bool = not gm.can_plant()
	put(sa + Vector3(0.5, 0.1, 0.3))
	await frames(40)
	var in_circle: bool = gm.can_plant()
	var m1: int = lo.money
	Input.action_press("interact")
	await secs(gm.R.plant_time * 0.5)
	var code_mid: String = gm.plant_code_shown()
	await secs(gm.R.plant_time * 0.5 + 0.3)
	Input.action_release("interact")
	var planted: bool = gm.bomb_state == "planted" and gm.planted_site == "A"
	ok(out_circle and in_circle and planted and code_mid.begins_with("73") and code_mid.contains("*") and lo.money - m1 == 300,
		"bomba faqat aylanada: tashqarida yo'q, ichida bor; o'rnatishda kod teriladi (%s), o'rnatganga +$300" % code_mid)
	# portlash: yaqindagi o'ladi, uzoqdagi yarador, zirh yarmini oladi
	var near: float = Rules.bomb_damage(3.0)
	var mid: float = Rules.bomb_damage(20.0)
	var far: float = Rules.bomb_damage(50.0)
	ok(near > 480.0 and mid > 50.0 and mid < 260.0 and far == 0.0, "portlash zarari masofaga qarab: 3 m %.0f, 20 m %.0f, 50 m %.0f" % [near, mid, far])
	put(sa + Vector3(0, 0.1, 22.0))
	await frames(4)
	lo.armor = 0.0
	var hp0: float = pl.hp
	m1 = lo.money
	gm._explode()
	await frames(2)
	var hp_lost: float = hp0 - pl.hp
	var wave: Node = null
	for n in main.get_children():
		if str(n.name).begins_with("Shockwave") or n.is_in_group("shockwave"):
			wave = n
	ok(gm.last_winner == "T" and gm.last_reason.contains("portladi") and (hp_lost > 20.0 or not pl.alive) and lo.money - m1 == 3500,
		"bomba portladi: 22 m dagi o'yinchi %.0f zarar oldi, T +$3500" % hp_lost)
	# granatalar: HE zarari, tutun ko'rishni to'sadi, olov o'chadi
	gm.start_round()
	gm.skip_freeze()
	gm.time_left = 1.0e6
	await frames(2)
	put(Vector3(0, 0.1, -24))
	await frames(6)
	var G = load("res://scripts/grenade.gd")
	var he = G.throw(main, "he", pl.global_position + Vector3(2.0, 0.3, 0), Vector3.ZERO, null)
	var hp1: float = pl.hp
	await secs(1.8)
	var he_dmg: float = hp1 - pl.hp
	ok(he_dmg > 20.0 and he_dmg < 98.0, "HE granata: 2 m da %.0f zarar (8.9 m radius, zirhsiz)" % he_dmg)
	pl.hp = 100.0
	var sm = G.throw(main, "smoke", pl.global_position + Vector3(4.0, 0.3, 0), Vector3.ZERO, null)
	await secs(1.6)
	var smokes := get_nodes_in_group("smokes")
	var blocked := false
	if smokes.size():
		var c: Vector3 = smokes[0].global_position
		var q := PhysicsRayQueryParameters3D.create(c + Vector3(-6, 0, 0), c + Vector3(6, 0, 0), 128)
		blocked = not pl.get_world_3d().direct_space_state.intersect_ray(q).is_empty()
	ok(smokes.size() == 1 and blocked, "tutun: 18 s, ko'rishni to'sadi (botlar orqasini ko'rmaydi)")
	var mo = G.throw(main, "molotov", pl.global_position + Vector3(-5.0, 0.3, 0), Vector3.ZERO, null)
	await secs(2.3)
	var fires := get_nodes_in_group("fires")
	var in_fire: bool = fires.size() == 1 and fires[0].contains(fires[0].global_position)
	var hp2: float = pl.hp
	put(fires[0].global_position + Vector3.UP * 0.1 if fires.size() else pl.global_position)
	await secs(1.0)
	ok(in_fire and hp2 - pl.hp > 20.0, "molotov: olov doirasi (2.8 m, 7 s), ichida turgan zarar oladi (%.0f / s)" % (hp2 - pl.hp))
	for f in fires:
		f.queue_free()
	for s in smokes:
		s.queue_free()
	put(Vector3(0, 0.1, -24))
	await frames(4)
	# kill feed va TAB statistika
	var enemy_bot: CharacterBody3D = load("res://scripts/bot.gd").new()
	main.add_child(enemy_bot)
	enemy_bot.setup("CT" if pl.team == "T" else "T", 7, pl.global_position + Vector3(0, 0, 6), pl.get_world_3d().navigation_map, true)
	enemy_bot.loadout.name = "Sinov"
	gm.bots.append(enemy_bot)
	await frames(2)
	ok(hud.has_method("scoreboard_text") and hud.scoreboard_text().contains("K") and hud.scoreboard_text().contains("HS"),
		"TAB — statistika jadvali (o'ldirdi / o'ldi / assist / HS% / ADR / pul)")
	var feed0: int = gm.feed.size()
	var k0: int = lo.kills
	if enemy_bot:
		var W = Rules.weapon("ak47")
		preload("res://scripts/combat.gd").hit(enemy_bot, 200.0, "head", pl, W)
		ok(gm.feed.size() == feed0 + 1 and gm.feed[-1].head and gm.feed[-1].weapon == "AK-47" and lo.kills == k0 + 1 and lo.hs >= 1,
			"kill feed: kim kimni, qaysi qurol bilan, boshga — %s [%s] %s" % [gm.feed[-1].killer, gm.feed[-1].weapon, gm.feed[-1].victim])
		gm.bots.erase(enemy_bot)
		enemy_bot.queue_free()
	# yarim vaqt: 12 raunddan keyin tomonlar almashadi, pul $800
	gm.score = {"T": 7, "CT": 5}
	gm._swapped_at = -1
	var t_before: String = pl.team
	lo.money = 9000
	gm.start_round()
	ok(pl.team != t_before and lo.money == 800 and gm.score["T"] == 5 and gm.score["CT"] == 7,
		"yarim vaqt (12 raund): tomonlar almashdi (%s -> %s), pul $800, hisob ham almashdi" % [t_before, pl.team])
	gm.score = {"T": 12, "CT": 11}
	gm.end_round("CT", "test", "elim")
	ok(gm.win_target == 16 and gm.match_winner == "", "12:12 — qo'shimcha vaqt (MR3): g'alaba uchun 16 raund")
	gm.start_round()
	ok(lo.money == 12500, "qo'shimcha vaqtda hammaga $12500")
	gm.match_winner = "T"
	gm.start_round()
	await frames(2)
