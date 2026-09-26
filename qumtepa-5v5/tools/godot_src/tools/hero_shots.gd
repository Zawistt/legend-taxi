extends SceneTree
## CT qahramoni skrinshotlari (1-shaxs va 3-shaxs): xvfb-run godot --rendering-method gl_compatibility -s res://tools/hero_shots.gd
const OUT := "res://../docs/shots/"
func _initialize() -> void:
	_run.call_deferred()
func shot(n: String) -> void:
	for i in 12: await process_frame
	root.get_texture().get_image().save_png(ProjectSettings.globalize_path(OUT + n))
	print("saqlandi ", n)
func _run() -> void:
	var main: Node = load("res://main.tscn").instantiate()
	root.add_child(main)
	root.size = Vector2i(1600, 900)
	main.get_node("GameMode").skip_freeze()
	main.get_node("HUD").visible = false
	var pl = main.get_node("Player")
	pl.team = "CT"
	pl.global_position = Vector3(-40.5, 0.1, 12.0)
	pl.rotation.y = PI * 0.85
	pl.cam.rotation.x = -0.04
	pl.cam.make_current()
	for i in 60: await process_frame
	await shot("ct_idle_1shaxs.png")
	main.get_node("UI").visible = false
	var cam := Camera3D.new(); main.add_child(cam); cam.make_current(); cam.fov = 45.0
	var b: Basis = pl.global_transform.basis
	cam.global_position = pl.global_position + b * Vector3(-1.0, 1.55, -3.6)
	cam.look_at(pl.global_position + Vector3(0, 0.95, 0), Vector3.UP)
	await shot("ct_idle_3shaxs.png")
	cam.fov = 30.0
	cam.global_position = pl.global_position + b * Vector3(-1.4, 1.5, -1.9)
	cam.look_at(pl.global_position + Vector3(0, 1.15, 0), Vector3.UP)
	await shot("ct_idle_3shaxs_yaqin.png")
	cam.fov = 45.0
	cam.global_position = pl.global_position + b * Vector3(-3.6, 1.3, 0.2)
	cam.look_at(pl.global_position + Vector3(0, 0.95, 0), Vector3.UP)
	await shot("ct_idle_3shaxs_yon.png")
	quit()
