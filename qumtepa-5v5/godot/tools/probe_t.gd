extends SceneTree
func _initialize():
	var sc = load("res://characters/t_shadow.glb").instantiate()
	root.add_child(sc)
	_dump(sc, 0)
	var ap: AnimationPlayer = sc.find_children("*", "AnimationPlayer", true, false)[0]
	print("anims: ", ap.get_animation_list())
	var a := ap.get_animation("idle")
	for i in mini(a.get_track_count(), 6):
		print("track ", a.track_get_path(i), " type ", a.track_get_type(i))
	print("len idle ", a.length, " loop ", a.loop_mode)
	var sk: Skeleton3D = sc.find_children("*", "Skeleton3D", true, false)[0]
	for n in ["hips", "chest", "head", "weapon", "hand.R", "upper_arm.R", "toe.L"]:
		var i := sk.find_bone(n)
		var g := sk.get_bone_global_rest(i)
		print(n, " pos ", g.origin, " x ", g.basis.x, " y ", g.basis.y, " z ", g.basis.z)
	quit()
func _dump(n, d):
	print("  ".repeat(d), n.name, " (", n.get_class(), ")")
	for c in n.get_children():
		if d < 4: _dump(c, d + 1)
