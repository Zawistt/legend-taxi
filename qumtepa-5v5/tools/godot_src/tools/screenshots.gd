extends SceneTree
## Skrinshotlar (docs uchun): xvfb-run godot --rendering-method gl_compatibility -s res://tools/screenshots.gd
## Natija: qumtepa-5v5/docs/shots/*.png (godot/ papkasida ishga tushiriladi)

const VIEWS := [
	["01_umumiy", Vector3(0, 150, 0.01), Vector3(0, 0, 0), -118.0],   # manfiy fov = ortografik, tepadan
	["02_t_spawn_top_mid", Vector3(-12.5, 1.7, -44), Vector3(-7, 1.2, -30), 80.0],
	["03_long_a_site", Vector3(-44, 1.7, -12), Vector3(-38, 1.0, 16), 80.0],
	["04_tunnels_b_site", Vector3(44, 1.7, -12), Vector3(38, 1.0, 16), 80.0],
	["05_mid_doors", Vector3(1.5, 1.7, -24), Vector3(0, 1.6, 10), 80.0],
	["06_ct_mid", Vector3(-9, 1.7, 30), Vector3(0, 1.4, 6), 80.0],
	["07_a_site_ramp", Vector3(-28, 1.7, 38), Vector3(-40, 1.0, 12), 80.0],
	["08_catwalk", Vector3(-22, 1.7, -20), Vector3(-22, 1.2, 6), 80.0],
	["09_b_site_karvonsaroy", Vector3(46, 1.7, 5), Vector3(28, 3.0, 26), 80.0],
	["10_top_mid_bozor", Vector3(14, 1.7, -34), Vector3(-12, 2.5, -20), 80.0],
	["11_ct_spawn", Vector3(3, 1.7, 47), Vector3(0, 11.0, 27), 80.0],
	["12_a_site_minora", Vector3(-24, 1.7, 26), Vector3(-50, 12.0, 31), 80.0],
	["13_t_spawn_qala", Vector3(0, 1.7, -40.5), Vector3(0, 2.0, -50), 80.0],
	["14_tandir_bozor", Vector3(11.5, 1.6, -25.0), Vector3(13.5, 0.6, -22.5), 70.0],
	["15_sori_b_platforma", Vector3(41.0, 2.2, 21.0), Vector3(47.5, 1.0, 23.0), 75.0],
	["16_kalta_minor", Vector3(38.0, 1.7, 22.0), Vector3(52.0, 12.0, 31.0), 75.0],
	["17_shom_a_site", Vector3(-24, 1.7, 26), Vector3(-50, 12.0, 31), 80.0, true],
	["18_shom_top_mid", Vector3(14, 1.7, -34), Vector3(-12, 2.5, -20), 80.0, true],
]


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var main: Node = load("res://main.tscn").instantiate()
	root.add_child(main)
	main.get_node("HUD").visible = false
	main.get_node("UI").visible = false
	var gm := main.get_node("GameMode")
	var cam := Camera3D.new()
	cam.far = 500.0
	main.add_child(cam)
	cam.make_current()
	root.size = Vector2i(1600, 900)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://../docs/shots"))
	for v in VIEWS:
		var atm = main.get_node_or_null("Atmosphere")
		if atm:
			atm.set_dusk(v.size() > 4 and v[4])
		var env: Environment = main.get_node("WorldEnvironment").environment
		env.fog_enabled = v[3] > 0.0
		if v[3] < 0.0:
			cam.projection = Camera3D.PROJECTION_ORTHOGONAL
			cam.size = -v[3]
		else:
			cam.projection = Camera3D.PROJECTION_PERSPECTIVE
			cam.fov = v[3]
		cam.global_position = v[1]
		cam.look_at(v[2], Vector3.UP)
		for i in 20:
			await process_frame
		var img := root.get_texture().get_image()
		img.save_png(ProjectSettings.globalize_path("res://../docs/shots/%s.png" % v[0]))
		print("saqlandi: ", v[0])
	# o'yin ekrani: HUD + minimap + birinchi shaxsdagi qurol (o'yinchining o'z kamerasi)
	main.get_node("HUD").visible = true
	main.get_node("UI").visible = true
	main.get_node("Atmosphere").set_dusk(false)
	var pl: Node3D = main.get_node("Player")
	gm.skip_freeze()
	pl.global_position = Vector3(-34, 0.1, 22)
	pl.rotation.y = atan2(34.0 - 44.0, 22.0 - 4.0) + PI
	pl.cam.make_current()
	pl.cam.rotation.x = -0.05
	for i in 40:
		await process_frame
	root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/19_hud_minimap.png"))
	# CT jamoasi — 1-shaxs (o'rinbosar qurol)
	pl.team = "CT"
	pl.global_position = Vector3(-34, 0.1, 22)
	for i in 40:
		await process_frame
	root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/21_fp_ct.png"))
	pl.team = "T"
	# bir paytning o'zi ikki kameradan: o'yinchining o'zi (1-shaxs) va boshqalar (3-shaxs to'liq tana)
	main.get_node("HUD").visible = false
	main.get_node("UI").visible = false
	pl.global_position = Vector3(-40.5, 0.1, 12.0)
	pl.rotation.y = PI * 0.85
	pl.cam.rotation.x = 0.12
	pl.force_crouch = true
	for i in 50:
		await process_frame
	root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/24_ozi_1shaxs.png"))
	cam.make_current()
	cam.fov = 50.0
	cam.global_position = pl.global_position + pl.global_transform.basis * Vector3(-1.2, 1.5, -3.4)
	cam.look_at(pl.global_position + Vector3(0, 0.8, 0), Vector3.UP)
	for i in 10:
		await process_frame
	root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/25_boshqalarga_3shaxs.png"))
	pl.force_crouch = false
	pl.cam.rotation.x = 0.0
	pl.global_position = Vector3(-34, 0.1, 22)
	print("saqlandi: 1-shaxs / 3-shaxs")
	main.get_node("HUD").visible = false
	main.get_node("UI").visible = true
	cam.make_current()
	cam.fov = 80.0
	cam.global_position = Vector3(-34, 1.7, 22)
	cam.look_at(Vector3(-44, 1.5, 4), Vector3.UP)
	var mm = main.get_node("UI/Minimap")
	mm.big = true
	for i in 6:
		await process_frame
	root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/20_katta_xarita.png"))
	print("saqlandi: HUD va xarita")
	quit()
