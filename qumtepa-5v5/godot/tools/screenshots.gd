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
]


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var main: Node = load("res://main.tscn").instantiate()
	root.add_child(main)
	main.get_node("HUD").visible = false
	var gm := main.get_node("GameMode")
	var cam := Camera3D.new()
	cam.far = 500.0
	main.add_child(cam)
	cam.make_current()
	root.size = Vector2i(1600, 900)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://../docs/shots"))
	for v in VIEWS:
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
		for i in 12:
			await process_frame
		var img := root.get_texture().get_image()
		img.save_png(ProjectSettings.globalize_path("res://../docs/shots/%s.png" % v[0]))
		print("saqlandi: ", v[0])
	quit()
