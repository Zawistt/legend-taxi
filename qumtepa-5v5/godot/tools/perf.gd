extends SceneTree
## 7-bosqich: ishlash o'lchovi. Har bir kamera nuqtasida ikki holat:
##   "optimallashtirilgan" — occlusion culling, bezaklar 70 m da so'nadi va soya tashlamaydi, quyosh soyasi 2 bo'lak / 80 m,
##   "o'chirilgan" — 6-bosqichdagi holat: occlusion yo'q, bezaklar doim ko'rinadi va soya tashlaydi,
##   quyosh soyasi 4 bo'lak / 140 m. Hududiy bo'laklar ikkala holatda bor.
## O'lchanadi: kadrda chizilgan obyektlar, chizish buyruqlari, uchburchaklar, kadr vaqti.
## Ishga tushirish: xvfb-run godot --rendering-method gl_compatibility -s res://tools/perf.gd
## Natija: docs/perf_stage7.json. Eslatma: serverda videokarta yo'q (dasturiy render) — kadr vaqti faqat nisbiy.

const VIEWS := [
	["T spawn", Vector3(0, 1.7, -42), Vector3(0, 1.7, -20)],
	["Top mid", Vector3(-12, 1.7, -32), Vector3(10, 1.7, -20)],
	["Long", Vector3(-44, 1.7, -14), Vector3(-40, 1.5, 16)],
	["A site", Vector3(-34, 1.7, 22), Vector3(-44, 1.5, 4)],
	["A ramp", Vector3(-28, 1.7, 38), Vector3(-40, 1.0, 12)],
	["Mid doors", Vector3(0, 1.7, -10), Vector3(0, 1.7, 20)],
	["CT mid", Vector3(-8, 1.7, 28), Vector3(8, 1.7, 8)],
	["CT spawn", Vector3(0, 1.7, 44), Vector3(0, 1.7, 20)],
	["B site", Vector3(34, 1.7, 22), Vector3(44, 1.5, 4)],
	["Lower tunnels", Vector3(44, 1.7, -14), Vector3(40, 1.5, 16)],
	["Catwalk", Vector3(-22, 1.7, -20), Vector3(-22, 1.2, 6)],
	["B platforma", Vector3(47.5, 3.0, 22.5), Vector3(40, 1.5, 4)],
]


func _initialize() -> void:
	_run.call_deferred()


func measure(cam: Camera3D, v: Array) -> Dictionary:
	cam.global_position = v[1]
	cam.look_at(v[2], Vector3.UP)
	for i in 8:
		await process_frame
	var o := 0.0
	var dc := 0.0
	var pr := 0.0
	var t0 := Time.get_ticks_usec()
	var n := 12
	for i in n:
		await process_frame
		o += RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME)
		dc += RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)
		pr += RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)
	var ms := (Time.get_ticks_usec() - t0) / 1000.0 / n
	return {"objects": int(o / n), "draw_calls": int(dc / n), "tris": int(pr / n), "ms": snappedf(ms, 0.1)}


func set_opt(main: Node, on: bool) -> void:
	root.use_occlusion_culling = on
	var sun: DirectionalLight3D = main.get_node("Sun")
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS if on else DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.directional_shadow_max_distance = 80.0 if on else 140.0
	var lod: Node = main.get_node("MapLOD")
	_decor(main.get_node("Map"), lod.DECOR_END if on else 0.0)


func _decor(n: Node, end: float) -> void:
	if n is GeometryInstance3D and "_Decor_" in n.name:
		(n as GeometryInstance3D).visibility_range_end = end
		(n as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF if end > 0.0 else GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	for c in n.get_children():
		_decor(c, end)


func _run() -> void:
	var main: Node = load("res://main.tscn").instantiate()
	if main.get_node_or_null("Bots"):
		main.get_node("Bots").enabled = false      # botlarsiz: xarita va mexanika sinovi
	root.add_child(main)
	root.size = Vector2i(1600, 900)
	main.get_node("HUD").visible = false
	main.get_node("UI").visible = false
	var cam := Camera3D.new()
	cam.far = 500.0
	cam.fov = 80.0
	main.add_child(cam)
	cam.make_current()
	for i in 20:
		await process_frame
	var rows := []
	print("\n%-15s %28s | %28s" % ["", "optimallashtirilgan", "o'chirilgan"])
	print("%-15s %7s %7s %8s %5s | %7s %7s %8s %5s" % ["joy", "obyekt", "chizish", "uchburch", "ms", "obyekt", "chizish", "uchburch", "ms"])
	var tot := {"on": {"objects": 0, "draw_calls": 0, "tris": 0, "ms": 0.0}, "off": {"objects": 0, "draw_calls": 0, "tris": 0, "ms": 0.0}}
	for v in VIEWS:
		set_opt(main, true)
		var a: Dictionary = await measure(cam, v)
		set_opt(main, false)
		var b: Dictionary = await measure(cam, v)
		rows.append({"view": v[0], "on": a, "off": b})
		for k in a:
			tot.on[k] += a[k]
			tot.off[k] += b[k]
		print("%-15s %7d %7d %8d %5.1f | %7d %7d %8d %5.1f" % [v[0], a.objects, a.draw_calls, a.tris, a.ms, b.objects, b.draw_calls, b.tris, b.ms])
	set_opt(main, true)
	var n := float(VIEWS.size())
	var red := {}
	for k in ["objects", "draw_calls", "tris", "ms"]:
		red[k] = snappedf(100.0 * (1.0 - float(tot.on[k]) / max(float(tot.off[k]), 1.0)), 0.1)
	print("\nO'RTACHA: obyektlar %.0f → %.0f (−%.0f%%), chizish %.0f → %.0f (−%.0f%%), uchburchaklar %.0f → %.0f (−%.0f%%), kadr %.1f → %.1f ms (−%.0f%%)" % [
		tot.off.objects / n, tot.on.objects / n, red.objects, tot.off.draw_calls / n, tot.on.draw_calls / n, red.draw_calls,
		tot.off.tris / n, tot.on.tris / n, red.tris, tot.off.ms / n, tot.on.ms / n, red.ms])
	var f := FileAccess.open(ProjectSettings.globalize_path("res://../docs/perf_stage7.json"), FileAccess.WRITE)
	f.store_string(JSON.stringify({"views": rows, "reduction_pct": red, "occluders": main.get_node("Occluders").get_child_count(),
		"decor_chunks_with_lod": main.get_node("MapLOD").decor_nodes}, " "))
	f.close()
	quit()
