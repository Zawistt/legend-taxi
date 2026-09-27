extends SceneTree
## T 3-shaxs modeli (Desert Shadow Operative) holatlari: bitta rasmda 10 ta personaj, har biri boshqa holatda.
##   xvfb-run ... godot --rendering-method gl_compatibility -s res://tools/t_shots.gd  -> docs/shots/50_t_holatlar.png, 51_..._yon.png

const CM := preload("res://scripts/character_model.gd")
const STATES := [["turish", {}], ["yugurish", {"v": Vector3(0, 0, 4.5)}], ["yonga", {"v": Vector3(4.5, 0, 0)}],
	["o'tirish", {"crouch": true}], ["to'pponcha", {"kind": 1, "wid": "glock"}], ["pichoq", {"kind": 2}],
	["granata", {"kind": 7}], ["tepaga qarash", {"pitch": 0.6}], ["qayta o'qlash", {"reload": true}], ["bomba qo'yish", {"plant": true, "kind": 9}],
	["o'lim", {"die": true}]]


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var team: String = args[0] if args.size() > 0 else "T"
	var pre := "t" if team == "T" else "ct"
	root.size = Vector2i(1800, 700)
	var world := Node3D.new()
	root.add_child(world)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.72, 0.76, 0.8)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.8, 0.8, 0.85)
	env.environment.ambient_light_energy = 0.6
	world.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-45, 30, 0)
	sun.shadow_enabled = true
	world.add_child(sun)
	var floor := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(40, 10)
	floor.mesh = pm
	world.add_child(floor)
	var models := []
	for i in STATES.size():
		var m: Node3D = CM.new()
		m.team = team
		world.add_child(m)
		m.position = Vector3((i - (STATES.size() - 1) * 0.5) * 1.2, 0, 0)
		var st: Dictionary = STATES[i][1]
		m.set_weapon(st.get("kind", 0), st.get("wid", "ak47"))
		m.velocity_local = st.get("v", Vector3.ZERO)
		m.crouching = st.get("crouch", false)
		m.planting = st.get("plant", false)
		m.aim_pitch = st.get("pitch", 0.0)
		var l := Label3D.new()
		l.text = STATES[i][0]
		l.font_size = 48
		l.pixel_size = 0.004
		l.position = Vector3(0, 2.05, 0)
		l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		m.add_child(l)
		models.append(m)
	var cam := Camera3D.new()
	world.add_child(cam)
	cam.fov = 38
	await process_frame
	for i in STATES.size():
		var st: Dictionary = STATES[i][1]
		if st.get("die", false):
			models[i].die()
	for f in 40:
		if f == 10:
			for i in STATES.size():
				if STATES[i][1].get("reload", false):
					models[i].reload()
		await process_frame
	print("rig: ", models[0].rig != null, " anims: ", models[0].anim.get_animation_list().size() if models[0].anim else 0,
		" hitboxes: ", models[0].hitboxes.size(), " eye: ", models[0].eye_point())
	cam.position = Vector3(0, 1.2, 10.5)
	cam.look_at(Vector3(0, 0.95, 0))
	await process_frame
	await process_frame
	root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/%s_holatlar.png" % ("50_t" if team == "T" else "54_ct")))
	cam.position = Vector3(11.0, 1.4, 3.0)
	cam.look_at(Vector3(0, 0.9, 0))
	await process_frame
	await process_frame
	root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/%s_holatlar_yon.png" % ("51_t" if team == "T" else "55_ct")))
	# yaqindan: to'pponcha, pichoq, granata (3/4 burchak)
	for j in [4, 5, 6, 0]:
		var mp: Vector3 = models[j].position
		cam.fov = 40
		cam.position = mp + Vector3(-1.6, 1.6, 2.2)
		cam.look_at(mp + Vector3(0, 1.25, 0))
		await process_frame
		await process_frame
		root.get_texture().get_image().save_png(ProjectSettings.globalize_path("res://../docs/shots/%s_yaqin_%d.png" % [pre, j]))
	print("saqlandi")
	quit()
