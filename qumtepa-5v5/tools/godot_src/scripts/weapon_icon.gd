extends RefCounted
## Qurol rasmi: qurolning 3D shakli (character_model.gd) kichik SubViewport'da yondan chiziladi.
## Sotib olish menyusi va inventar ishlatadi. Headless rejimda (testlar) rasm chizilmaydi — null.

const CharacterModel := preload("res://scripts/character_model.gd")


## kind: WeaponData.Kind (−1 — zirh, "vesthelm" — kaska bilan); holder — SubViewport shu tugunga qo'shiladi
static func make(holder: Node, kind: int, team: String, wid: String, px: Vector2i = Vector2i(220, 88), helmet := false) -> Texture2D:
	if DisplayServer.get_name() == "headless":
		return null
	var sv := SubViewport.new()
	sv.size = px
	sv.transparent_bg = true
	sv.own_world_3d = true
	sv.render_target_update_mode = SubViewport.UPDATE_ONCE
	holder.add_child(sv)
	var root := Node3D.new()
	sv.add_child(root)
	if kind >= 0:
		var shape: Dictionary = CharacterModel.make_weapon_shape(kind, team, wid)
		root.add_child(shape.node)
		if kind == 7:
			shape.node.scale = Vector3.ONE * 4.0
	else:
		CharacterModel._sbox(root, Vector3(0.1, 0.5, 0.42), Vector3(0, 0, 0.3), Color(0.3, 0.33, 0.25))
		if helmet:
			CharacterModel._sbox(root, Vector3(0.3, 0.16, 0.3), Vector3(0, 0.36, 0.3), Color(0.2, 0.22, 0.2))
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 0.62 if kind in [1, 7, 8, 9] else 1.25
	root.add_child(cam)
	cam.position = Vector3(-2.0, 0.0, 0.3 if kind in [0, 3, 4, 5, 6] else 0.1)
	cam.look_at(Vector3(0, 0, cam.position.z), Vector3.UP)
	var l := DirectionalLight3D.new()
	l.rotation_degrees = Vector3(-40, -60, 0)
	root.add_child(l)
	return sv.get_texture()
