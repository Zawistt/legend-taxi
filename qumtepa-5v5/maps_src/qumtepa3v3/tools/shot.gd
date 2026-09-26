extends SceneTree
var views := {
	"0": [Vector3(-21.6, 1.8, -3.2), Vector3(-14, 0.8, 9)],
	"1": [Vector3(-2, 1.7, -7.5), Vector3(-2, 1.8, 3)],
	"2": [Vector3(0, 1.7, -21.8), Vector3(0, 1.6, -10)],
	"3": [Vector3(-26, 13, -27), Vector3(0, 1, 0)],
	"4": [Vector3(13, 1.8, -0.6), Vector3(17, 0.8, 8)],
}
func _initialize() -> void:
	_run.call_deferred()
func _run() -> void:
	var main: Node = load("res://main.tscn").instantiate()
	root.add_child(main)
	main.get_node("Player").set_physics_process(false)
	main.get_node("HUD").visible = false
	var cam := Camera3D.new()
	root.add_child(cam)
	cam.fov = 75
	cam.current = true
	var id := OS.get_environment("SHOT_ID")
	cam.global_position = views[id][0]
	cam.look_at(views[id][1], Vector3.UP)
	for f in 60:
		await process_frame
	await RenderingServer.frame_post_draw
	get_root().get_texture().get_image().save_png("res://s5_%s.png" % id)
	print("shot ", id)
	quit()
