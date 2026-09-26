extends SceneTree
## Bot o'yinidan skrinshot (docs uchun): xvfb-run godot --rendering-method gl_compatibility -s res://tools/bots_shot.gd

func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var scene: Node = load("res://bots.tscn").instantiate()
	root.add_child(scene)
	root.size = Vector2i(1600, 900)
	var cam: Camera3D = scene.get_node("Spectator")
	var m: Node = scene.get_node("BotMatch")
	cam.set_process(false)
	cam.set_process_unhandled_input(false)
	for v in [[36.0, "bots_1_hujum", Vector3(-26, 26, 38), Vector3(-36, 0, 12)], [22.0, "bots_2_mid", Vector3(12, 16, 22), Vector3(0, 0, 0)]]:
		while m.t < v[0]:
			await physics_frame
		cam.global_position = v[2]
		cam.look_at(v[3], Vector3.UP)
		for i in 6:
			await process_frame
		root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/%s.png" % v[1]))
		print("saqlandi ", v[1])
		m.start_round()
	quit()
