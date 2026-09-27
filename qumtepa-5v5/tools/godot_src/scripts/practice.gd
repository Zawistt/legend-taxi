extends Node3D
## Mashq nishonlari (Legend Tactical FPS'dagi TrainingTarget g'oyasi): F7 — o'yinchi qarab turgan tomonda
## 3 ta manekin paydo bo'ladi (yaqin, o'rta, uzoq), qayta F7 — olib tashlanadi.
## Nishon: 100 HP, bosh/tana/qo'l/oyoq zonalari (character_model.gd), tepada oxirgi zarar va qolgan HP;
## o'lsa yiqiladi va 2.5 s dan keyin tiriladi. Faqat o'q tegadigan zonalar bor — yurishga to'sqinlik qilmaydi.

const CharacterModel := preload("res://scripts/character_model.gd")

@export var player_path: NodePath = ^"../Player"


class Target:
	extends Node3D
	var hp := 100.0
	var model: Node3D
	var label: Label3D
	var last_zone := ""
	var last_damage := 0.0
	var hits := 0
	var _revive_at := -1.0

	func setup(team: String) -> void:
		model = CharacterModel.new()
		model.team = team
		add_child(model)
		label = Label3D.new()
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.no_depth_test = true
		label.font_size = 40
		label.outline_size = 8
		label.position = Vector3(0, 2.2, 0)
		add_child(label)
		_update()

	func take_hit(dmg: float, zone: String, _from: Node, _weapon: Resource = null) -> bool:
		if hp <= 0.0:
			return false
		hp -= dmg
		hits += 1
		last_zone = zone
		last_damage = dmg
		var killed := hp <= 0.0
		if killed:
			model.die()
			_revive_at = Time.get_ticks_msec() / 1000.0 + 2.5
		_update()
		return killed

	func _process(_d: float) -> void:
		if _revive_at > 0.0 and Time.get_ticks_msec() / 1000.0 >= _revive_at:
			_revive_at = -1.0
			hp = 100.0
			model.revive()
			_update()

	func _update() -> void:
		var z := {"head": "BOSH", "body": "TANA", "arm": "QO'L", "leg": "OYOQ"}
		label.text = ("%s −%d\n" % [z.get(last_zone, ""), int(round(last_damage))] if hits else "") + "%d HP" % maxi(0, int(ceil(hp)))


var targets: Array = []


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F7:
		toggle()


func toggle() -> void:
	if targets.is_empty():
		spawn()
	else:
		clear()


func clear() -> void:
	for t in targets:
		t.queue_free()
	targets = []


## o'yinchining oldida (devorgacha) 3 ta nishon: ~5 m, ~12 m va ~25 m (devor yaqin bo'lsa — undan 1.5 m oldin)
func spawn(distances := [5.0, 12.0, 25.0]) -> Array:
	clear()
	var pl: CharacterBody3D = get_node(player_path)
	var space := pl.get_world_3d().direct_space_state
	var fwd := -pl.global_transform.basis.z
	fwd = Vector3(fwd.x, 0, fwd.z).normalized()
	var eye := pl.global_position + Vector3.UP * 1.5
	var wall := space.intersect_ray(PhysicsRayQueryParameters3D.create(eye, eye + fwd * 60.0, 1))
	var limit := eye.distance_to(wall.position) - 1.5 if not wall.is_empty() else 60.0
	var side := fwd.cross(Vector3.UP)
	var i := 0
	for d in distances:
		var dd := minf(d, limit - i * 0.8)
		if dd < 2.0:
			continue
		var p := pl.global_position + fwd * dd + side * (i - 1) * 0.9
		var down := space.intersect_ray(PhysicsRayQueryParameters3D.create(p + Vector3.UP * 2.0, p + Vector3.DOWN * 4.0, 1))
		if not down.is_empty():
			p.y = down.position.y
		var t := Target.new()
		t.setup("CT" if pl.team == "T" else "T")
		add_child(t)
		t.global_position = p
		t.look_at(Vector3(pl.global_position.x, p.y, pl.global_position.z), Vector3.UP, true)
		targets.append(t)
		i += 1
	return targets
