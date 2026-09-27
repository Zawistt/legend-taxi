extends SceneTree
## Telefon boshqaruvi sinovi (kompyuterda, sensor hodisalari taqlid qilinadi):  godot ... -s res://tools/mobile_shot.gd -- --touch
##   joystik -> o'yinchi yuradi; o'ng tomonda surish -> qaraydi; OTISH tugmasi -> o'q uziladi. Skrinshot: docs/shots/59_telefon.png

func _initialize() -> void:
	_run.call_deferred()


func touch(idx: int, p: Vector2, pressed: bool) -> void:
	var e := InputEventScreenTouch.new()
	e.index = idx
	e.position = p
	e.pressed = pressed
	Input.parse_input_event(e)


func drag(idx: int, p: Vector2, rel: Vector2) -> void:
	var e := InputEventScreenDrag.new()
	e.index = idx
	e.position = p
	e.relative = rel
	Input.parse_input_event(e)


func _run() -> void:
	root.size = Vector2i(1600, 900)
	var main: Node = load("res://main.tscn").instantiate()
	main.get_node("Bots").enabled = false
	root.add_child(main)
	var gm = main.get_node("GameMode")
	var pl = main.get_node("Player")
	var mc = main.get_node("MobileControls")
	for i in 30:
		await process_frame
	gm.skip_freeze()
	for i in 10:
		await process_frame
	gm.time_left = 1.0e6
	print("faol: ", mc.active, " tugmalar: ", mc._buttons.size())
	var p0: Vector3 = pl.global_position
	touch(0, Vector2(300, 650), true)
	for i in 5:
		drag(0, Vector2(300, 650 - 20 * (i + 1)), Vector2(0, -20))
		await process_frame
	for i in 60:
		await physics_frame
	var moved: float = pl.global_position.distance_to(p0)
	var joy_vis: bool = mc._joy_base.visible
	var yaw0: float = pl.rotation.y
	touch(1, Vector2(1000, 400), true)
	for i in 5:
		drag(1, Vector2(1000 + 30 * (i + 1), 400), Vector2(30, 0))
		await process_frame
	var turned: float = absf(pl.rotation.y - yaw0)
	root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/59_telefon.png"))
	touch(1, Vector2(1150, 400), false)
	touch(0, Vector2(300, 550), false)
	await process_frame
	var fpv = pl.get_node("Camera3D/FPView")
	var am0: int = fpv.ammo
	Input.action_press("fire")
	for i in 20:
		await process_frame
	Input.action_release("fire")
	print("joystik: %.2f m yurdi (ko'rinadi %s), qarash: %.2f rad burildi, otish: %d -> %d o'q" % [moved, joy_vis, turned, am0, fpv.ammo])
	print(("OK" if moved > 1.0 and turned > 0.2 and fpv.ammo < am0 else "XATO") + " telefon boshqaruvi")
	quit()
