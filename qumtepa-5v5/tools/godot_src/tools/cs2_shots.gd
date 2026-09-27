extends SceneTree
## 12-bosqich skrinshotlari (CS2 qoidalari): sotib olish menyusi, kill feed va HUD, TAB statistika, bomba kodi,
## portlash to'lqini, tutun va molotov. Botlar haqiqatan o'ynaydi (kill feed — haqiqiy o'ldirishlar).
##   xvfb-run -a -s "-screen 0 1600x900x24" godot --rendering-method gl_compatibility --rendering-driver opengl3 -s res://tools/cs2_shots.gd

var main: Node
var gm: Node
var pl: CharacterBody3D
var bp: Node


func _initialize() -> void:
	_run.call_deferred()


func frames(n: int) -> void:
	for i in n:
		await process_frame


func save(name: String) -> void:
	await frames(3)
	root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/%s.png" % name))
	print("saqlandi: ", name)


func look_at_point(p: Vector3) -> void:
	var e: Vector3 = pl.cam.global_position
	var d := (p - e).normalized()
	pl.rotation.y = atan2(-d.x, -d.z)
	pl.cam.rotation.x = asin(d.y)


func _run() -> void:
	root.size = Vector2i(1600, 900)
	main = load("res://main.tscn").instantiate()
	root.add_child(main)
	gm = main.get_node("GameMode")
	pl = main.get_node("Player")
	bp = main.get_node("Bots")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://../docs/shots"))
	while not bp.ready_ok:
		await process_frame
	await frames(30)
	var fpv = pl.get_node("Camera3D/FPView")
	var bm = fpv.buy_menu
	# 1) sotib olish menyusi: pistol raund ($800) — to'pponchalar
	bm.set_open(true)
	bm.select_cat(0)
	await frames(20)
	await save("40_sotib_olish_toppancha")
	# 2) avtomatlar ($4750 — ikki raund yutqazgandan keyin)
	pl.loadout.money = 4750
	bm.select_cat(2)
	await frames(20)
	await save("41_sotib_olish_avtomat")
	bm.buy_item("ak47")
	bm.buy_item("vesthelm")
	bm.select_cat(4)
	await frames(20)
	await save("42_sotib_olish_granata")
	bm.set_open(false)
	# 3) raund o'ynaladi: kill feed to'lguncha (o'yinchi spawn'da qoladi)
	gm.skip_freeze()
	Engine.time_scale = 5.0
	var guard := 0
	while gm.feed.size() < 4 and gm.phase in [1, 2] and guard < 60 * 60:
		await process_frame
		guard += 1
	Engine.time_scale = 1.0
	await frames(10)
	await save("43_kill_feed")
	# 4) TAB statistika
	main.get_node("HUD")._force_board = true
	await frames(10)
	await save("44_tab_statistika")
	main.get_node("HUD")._force_board = false
	# 5) bomba kodi: A aylanasi ichida o'rnatish
	while gm.phase != 0:
		gm.start_round()
		await frames(5)
	if pl.team != "T":
		gm.switch_team()
		gm.start_round()
	await frames(10)
	bp.enabled = false
	for b in bp.bots:
		b.global_position = Vector3(0, -60, 0)
		b.alive = false
	bp.set_physics_process(false)
	gm.skip_freeze()
	pl.has_bomb = true
	gm.bomb_state = "carried"
	var sa: Vector3 = gm.plant_spots["A"]
	pl.teleport(Transform3D(Basis(), sa + Vector3(0.6, 0.1, 1.8)))
	await frames(20)
	look_at_point(sa + Vector3(0, 0.3, 0))
	fpv.equip(5, true)
	await frames(10)
	Input.action_press("interact")
	var guard2 := 0
	while not (gm.action == "plant" and gm.action_progress > gm.action_duration * 0.55) and guard2 < 2000:
		await process_frame
		guard2 += 1
	await save("45_bomba_kodi")
	while gm.bomb_state != "planted":
		await process_frame
	Input.action_release("interact")
	# 6) portlash to'lqini: tepadan, 35 m narida
	var cam := Camera3D.new()
	cam.far = 500.0
	main.add_child(cam)
	cam.global_position = sa + Vector3(30, 22, 30)
	cam.look_at(sa, Vector3.UP)
	cam.make_current()
	main.get_node("HUD").visible = false
	pl.teleport(Transform3D(Basis(), sa + Vector3(60, 0.1, 60)))
	gm.time_left = 0.05
	var t0 := Time.get_ticks_msec()
	while gm.bomb_state != "exploded":
		await process_frame
	while Time.get_ticks_msec() - t0 < 450:
		await process_frame
	await save("46_portlash_tolqini")
	while Time.get_ticks_msec() - t0 < 1000:
		await process_frame
	await save("47_portlash_tolqini_2")
	main.get_node("HUD").visible = true
	# 7) tutun va molotov
	gm.start_round()
	await frames(5)
	gm.skip_freeze()
	pl.revive()
	pl.teleport(Transform3D(Basis(), Vector3(0, 0.1, -24)))
	pl.rotation.y = -PI * 0.5
	pl.cam.rotation.x = -0.08
	pl.cam.make_current()
	await frames(10)
	var G = load("res://scripts/grenade.gd")
	var fwd: Vector3 = -pl.global_transform.basis.z
	var side: Vector3 = pl.global_transform.basis.x
	G.throw(main, "smoke", pl.global_position + fwd * 11.0 - side * 2.5 + Vector3.UP * 0.4, Vector3.ZERO, pl)
	G.throw(main, "molotov", pl.global_position + fwd * 7.0 + side * 2.5 + Vector3.UP * 0.4, Vector3.ZERO, pl)
	var t1 := Time.get_ticks_msec()
	while Time.get_ticks_msec() - t1 < 3200:
		await process_frame
	await save("48_tutun_molotov")
	quit()
