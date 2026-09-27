extends SceneTree
## Botlar bilan o'yin sinovi (5v5 yoki 3v3): o'yinchi spawn'da turadi, botlar raundlarni o'ynaydi.
##   godot --headless --fixed-fps 60 -s res://tests/run_botplay.gd -- <sahna> <raundlar> [jamoa]
## Tekshiradi: raundlar tugaydi, botlar tiqilib qolmaydi, bomba o'rnatiladi/zararsizlantiriladi, o'yinchi o'ladi va tiriladi.

var total := 0
var fails := 0


func ok(c: bool, msg: String) -> void:
	total += 1
	print(("  [OK]   " if c else "  [XATO] ") + msg)
	if not c:
		fails += 1


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var scene := args[0] if args.size() > 0 else "res://main.tscn"
	var rounds := int(args[1]) if args.size() > 1 else 6
	var team := args[2] if args.size() > 2 else "T"
	var main: Node = load(scene).instantiate()
	main.get_node("GameMode").start_team = team
	root.add_child(main)
	var gm: Node = main.get_node("GameMode")
	var bp: Node = main.get_node("Bots")
	var pl: CharacterBody3D = main.get_node("Player")
	print("\nBotlar bilan o'yin: %s, %d raund, o'yinchi — %s (jamoa %d kishi)" % [scene, rounds, team, bp.team_size])
	while not bp.ready_ok:
		await physics_frame
	# yurganda ekran qorayishi yo'q: aks ettirish zonalari atrof yorug'ligini almashtirmaydi, SDFGI/hajmli tuman o'chiq
	var probes := main.find_children("*", "ReflectionProbe", true, false)
	var bad := probes.filter(func(p): return p.ambient_mode != ReflectionProbe.AMBIENT_DISABLED)
	var env: Environment = (main.get_node("WorldEnvironment") as WorldEnvironment).environment
	ok(bad.is_empty() and not env.sdfgi_enabled and not env.volumetric_fog_enabled,
		"ekran qorayishi yo'q: %d ta ReflectionProbe atrof yorug'ligini o'zgartirmaydi, SDFGI va hajmli tuman o'chiq" % probes.size())
	await _smart_checks(main, gm, bp, pl)
	var results := []
	var reasons := {}
	var plants := 0
	var kills := 0
	var head := 0
	var player_deaths := 0
	var revived := 0
	var stuck := 0
	var max_len := 0.0
	var last_round: int = gm.round_no
	var was_dead := false
	var pos_t := {}
	var frame := 0
	var saw_planted := false
	var kill_n := 0
	gm.round_ended.connect(func(w: String, r: String) -> void:
		results.append(w)
		reasons[r] = reasons.get(r, 0) + 1)
	pl.died.connect(func() -> void: player_deaths += 1)
	while results.size() < rounds:
		await physics_frame
		frame += 1
		if gm.phase == 2:
			saw_planted = true
		if gm.round_no != last_round:
			last_round = gm.round_no
			if saw_planted:
				plants += 1
			saw_planted = false
			kills += kill_n
			kill_n = 0
			if was_dead and pl.alive:
				revived += 1
		was_dead = was_dead or not pl.alive
		kill_n = bp.kills.size()
		if gm.phase in [1, 2]:
			max_len = maxf(max_len, bp.t)
		# tiqilish: harakatlanishi kerak bo'lgan bot 6 s joyidan siljimasa
		if frame % 60 == 0 and gm.phase in [1, 2]:
			for b in bp.bots:
				if not b.alive or b.target != null or b.busy != "" or not b.has_goal or b.path_i >= b.path.size() or bp.t < b.fight_until:
					pos_t.erase(b)
					continue
				var p: Vector3 = b.global_position
				if pos_t.has(b):
					if pos_t[b][0].distance_to(p) < 0.4 and bp.t - pos_t[b][1] > 6.0:
						stuck += 1
						print("    tiqildi: %s%d %s rejim %s maqsad %s" % [b.team, b.idx + 1, p, b.mode, b.goal])
						pos_t[b] = [p, bp.t]
					elif pos_t[b][0].distance_to(p) >= 0.4:
						pos_t[b] = [p, bp.t]
				else:
					pos_t[b] = [p, bp.t]
		if frame > rounds * 60 * 200:
			break
	for k in bp.kills:
		if k[3]:
			head += 1
	var tw := results.filter(func(w): return w == "T").size()
	print("  natija: T %d : %d CT; sabablar: %s" % [tw, results.size() - tw, reasons])
	print("  bomba o'rnatilgan raundlar: %d, o'yinchi o'ldi: %d, eng uzun raund %.0f s" % [plants, player_deaths, max_len])
	ok(results.size() == rounds, "%d/%d raund tugadi" % [results.size(), rounds])
	ok(reasons.size() >= 2, "raundlar turli yo'l bilan tugaydi (%d xil)" % reasons.size())
	ok(stuck == 0, "tiqilib qolgan bot yo'q (%d)" % stuck)
	ok(bp.bots.size() == bp.team_size * 2 - 1, "botlar: %d (o'yinchi + %d jamoadosh va %d raqib)" % [bp.bots.size(), bp.team_size - 1, bp.team_size])
	print("\nNATIJA: %d / %d tekshiruv o'tdi" % [total - fails, total])
	quit(1 if fails else 0)


## aniq vaziyatlar: eshitish, o'yinchiga o'q uzish, o'z jamoasiga zarar yo'q, o'lganda kuzatish, bomba tasodifiy
func _smart_checks(main: Node, gm: Node, bp: Node, pl: CharacterBody3D) -> void:
	gm.skip_freeze()
	for i in 3:
		await physics_frame
	var sp: PhysicsDirectSpaceState3D = pl.get_world_3d().direct_space_state
	var fpv = pl.get_node("Camera3D/FPView")
	var en: Array = bp.enemies()
	var al: Array = bp.allies()
	var e = en[0]
	# 1) eshitish: o'yinchi 15 m ichida o'q uzsa (ko'rinmasa ham) bot o'sha tomonga qaraydi
	pl.global_position = e.global_position + Vector3(0, 0, 12.0 if pl.team == "CT" else -12.0)
	e.look_dir = (e.global_position - pl.global_position).normalized() * Vector3(1, 0, 1)
	pl.fired.emit()
	for i in 20:
		await physics_frame
	var to_pl: Vector3 = (pl.global_position - e.global_position) * Vector3(1, 0, 1)
	ok(e.alert_until > bp.t and e.look_dir.dot(to_pl.normalized()) > 0.9, "eshitish: o'q ovozidan keyin raqib bot o'yinchi tomonga qaradi")
	# 2) o'z jamoasiga zarar yo'q
	var a = al[0] if al.size() > 0 else null
	if a:
		pl.global_position = a.global_position + Vector3(2.5, 0, 0)
		for i in 3:
			await physics_frame
		var aim: Vector3 = a.global_position + Vector3.UP * 1.3
		var d: Vector3 = (aim - pl.cam.global_position).normalized()
		pl.rotation.y = atan2(-d.x, -d.z)
		pl.cam.rotation.x = asin(d.y)
		await physics_frame
		fpv.no_spread = true
		fpv._next_shot = 0.0
		fpv._equip_end = 0.0
		fpv.fire()
		fpv.no_spread = false
		ok(a.hp == 100.0 and fpv.last_hit.get("target") == a, "o'z jamoadoshiga o'q tegdi, lekin zarar yo'q (HP %d)" % a.hp)
	# 3) raqib bot ko'rinib turgan o'yinchiga o'q uzadi
	var spot := Vector3.ZERO
	var dirs: Array = [e.look_dir]
	for k in 8:
		dirs.append(Vector3(cos(k * PI / 4.0), 0, sin(k * PI / 4.0)))
	var cands: Array = []
	for dv in dirs:
		for dd in [6.0, 9.0, 4.0, 12.0]:
			cands.append(e.global_position + dv * dd)
	for c in cands:
		var down := sp.intersect_ray(PhysicsRayQueryParameters3D.create(c + Vector3.UP * 1.5, c + Vector3.DOWN * 3.0, 1))
		if down.is_empty():
			continue
		var cand: Vector3 = down.position + Vector3.UP * 0.05
		if sp.intersect_ray(PhysicsRayQueryParameters3D.create(e.eye(), cand + Vector3.UP * 1.2, 1)).is_empty():
			spot = cand
			break
	ok(spot != Vector3.ZERO, "raqib bot ko'radigan ochiq joy topildi")
	if spot != Vector3.ZERO:
		e.look_dir = ((spot - e.global_position) * Vector3(1, 0, 1)).normalized()
		pl.global_position = spot
		var hp0: float = pl.hp
		for i in 120:
			await physics_frame
		ok(pl.hp < hp0, "raqib bot ko'rinib turgan o'yinchiga o'q uzdi (HP %d → %d)" % [int(hp0), int(pl.hp)])
	# 4) o'lganda: harakat va o'q yo'q, jamoadoshni kuzatish kamerasi
	pl.damage(500.0)
	for i in 5:
		await physics_frame
	var am: int = fpv.ammo
	fpv._next_shot = 0.0
	fpv.fire()
	ok(not pl.alive and bp._spec_cam.current == (bp.allies().filter(func(b): return b.alive).size() > 0) and fpv.ammo == am,
		"o'yinchi o'ldi: o'q uzolmaydi, jamoadoshni kuzatadi")
	gm.start_round()
	for i in 5:
		await physics_frame
	ok(pl.alive and pl.hp == 100.0 and pl.cam.current, "yangi raundda o'yinchi tiriladi")
