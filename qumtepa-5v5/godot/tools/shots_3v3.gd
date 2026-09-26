extends SceneTree
## Skrinshotlar: bosh menyu, 3v3 xaritasi (Qumtepa v2 low-poly), sotib olish menyusi, snayper optikasi.
## xvfb-run ... godot --rendering-method gl_compatibility -s res://tools/shots_3v3.gd

func _shot(name: String) -> void:
	root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/%s.png" % name))
	print("saqlandi: ", name)


func _wait(n: int) -> void:
	for i in n:
		await process_frame


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	root.size = Vector2i(1600, 900)
	var menu = load("res://menu.tscn").instantiate()
	root.add_child(menu)
	await _wait(10)
	_shot("30_menyu")
	menu.queue_free()
	var main = load("res://main_3v3.tscn").instantiate()
	root.add_child(main)
	var gm = main.get_node("GameMode")
	var pl = main.get_node("Player")
	var fpv = pl.get_node("Camera3D/FPView")
	await _wait(30)
	pl.cam.make_current()
	# 1) spawn: sotib olish menyusi ochiq
	fpv.buy_menu.open = true
	await _wait(20)
	_shot("31_3v3_sotib_olish")
	fpv.buy_menu.open = false
	gm.skip_freeze()
	# 2) xarita ko'rinishlari (kuzatuvchi kamera)
	var cam := Camera3D.new()
	main.add_child(cam)
	cam.make_current()
	main.get_node("HUD").visible = false
	for v in [["32_3v3_umumiy", Vector3(0, 55, 30), Vector3(0, 0, 0), 60.0],
			["33_3v3_a_site", Vector3(-8, 3.0, 14), Vector3(-17, 1.0, 5), 75.0],
			["34_3v3_b_site", Vector3(8, 3.0, 14), Vector3(17, 1.0, 5), 75.0],
			["35_3v3_mid", Vector3(0, 2.2, -12), Vector3(0, 1.4, 6), 75.0]]:
		cam.fov = v[3]
		cam.global_position = v[1]
		cam.look_at(v[2], Vector3.UP)
		await _wait(25)
		_shot(v[0])
	# 3) snayper optikasi (o'yinchi kamerasi)
	pl.cam.make_current()
	main.get_node("HUD").visible = true
	fpv.buy("longbow_50")
	await _wait(60)
	fpv.force_ads = true
	await _wait(60)
	_shot("36_snayper_optika")
	fpv.force_ads = false
	fpv.buy("breacher_12")
	await _wait(60)
	_shot("37_drobovik")
	quit()
