extends SceneTree
## Renders the foundation terrain from an elevated RTS camera and saves PNGs.
##   xvfb-run godot --rendering-method gl_compatibility --path godot \
##       --script res://scripts/terrain/capture_preview.gd -- /abs/out_dir
## Needs a GPU/GL context (not --headless).

func _init() -> void:
	var out := "/tmp"
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out = args[0]
	root.size = Vector2i(1920, 1080)
	var main: Node3D = load("res://scenes/main.tscn").instantiate()
	main.set("edge_pan", false)
	root.add_child(main)
	await process_frame
	await process_frame
	for n in main.get_children():
		if n is WorldEnvironment:
			# software GL has no procedural sky; use a flat sky colour for the preview
			n.environment.background_mode = Environment.BG_COLOR
			n.environment.background_color = Color(0.62, 0.74, 0.88)
	var rig: RtsCamera = main.get_node("RtsCamera")
	rig.set_process(false)
	rig.set_process_unhandled_input(false)
	var terrain: TerrainManager = main.get_node("Terrain")
	var cam: Camera3D = rig.get_child(0)
	cam.current = true
	cam.far = 3000.0
	cam.fov = 40.0
	# [camera position, look target, show_zones, show_paths]
	var shots := {
		"godot_rts_overview": [Vector3(-350, 265, -375), Vector3(8, 0, 4), false, false],
		"godot_rts_lanes": [Vector3(-350, 265, -375), Vector3(8, 0, 4), false, true],
		"godot_rts_zones": [Vector3(-350, 265, -375), Vector3(8, 0, 4), true, false],
		"godot_rts_base_view": [Vector3(-190, 55, -215), Vector3(-120, 5, -120), false, false],
	}
	for key in shots:
		var s: Array = shots[key]
		rig.global_transform = Transform3D.IDENTITY
		cam.global_position = s[0]
		cam.look_at(s[1], Vector3.UP)
		terrain.set_show_zones(s[2])
		terrain.set_show_paths(s[3])
		for i in 6:
			await process_frame
		var img := root.get_texture().get_image()
		img.save_png("%s/%s.png" % [out, key])
		print("saved ", key)
	quit()
