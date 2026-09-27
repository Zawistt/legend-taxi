extends RigidBody3D
## Granatalar (CS2): fizika bilan uchadi, devor/poldan qaytadi.
##   HE — 1.6 s: 8.9 m radiusda zarar (ko'pi bilan 98, devor to'sadi, zirh yarmini oladi);
##   flesh — 1.6 s: 25 m ichida ko'rib turgan har kim ko'r bo'ladi (to'g'ri qarasa ~4.9 s, orqa o'girgan bo'lsa qisqa);
##   tutun — to'xtagach yoyiladi: 18 s, radius 3 m, ko'rishni to'sadi (botlar ham ko'rmaydi), olovni o'chiradi;
##   molotov (T) / yondiruvchi (CT) — polga tegsa yoki 2 s dan keyin: 2.8 m doira 7 s yonadi (sekundiga ~35 zarar).
## O'yinchi ham, botlar ham ishlatadi. Zarar kimga yozilishi — tashlovchi (combat.gd).

const Rules := preload("res://scripts/cs_rules.gd")
const Combat := preload("res://scripts/combat.gd")
const WeaponData := preload("res://scripts/weapon_data.gd")
const SMOKE_LAYER := 128
const SMOKE_R := 3.0
const SMOKE_TIME := 18.0
const FIRE_R := 2.8
const FIRE_TIME := 7.0
const FIRE_DPS := 35.0
const HE_R := 8.9
const HE_MAX := 98.0

var type := "he"
var thrower: Node = null
var _t := 0.0
var _done := false
var _still := 0.0
var _wd: Resource


static func throw(parent: Node, t: String, pos: Vector3, vel: Vector3, who: Node) -> RigidBody3D:
	var g: RigidBody3D = (load("res://scripts/grenade.gd") as GDScript).new()
	g.type = t
	g.thrower = who
	parent.add_child(g)
	g.global_position = pos
	g.linear_velocity = vel
	return g


func _ready() -> void:
	collision_layer = 0
	collision_mask = 1 | 4
	mass = 0.4
	continuous_cd = true
	contact_monitor = true
	max_contacts_reported = 4
	var pm := PhysicsMaterial.new()
	pm.bounce = 0.35
	pm.friction = 0.7
	physics_material_override = pm
	var cs := CollisionShape3D.new()
	var sh := SphereShape3D.new()
	sh.radius = 0.06
	cs.shape = sh
	add_child(cs)
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.07, 0.11, 0.07)
	var m := StandardMaterial3D.new()
	m.albedo_color = {"he": Color(0.25, 0.35, 0.2), "flash": Color(0.6, 0.62, 0.66), "smoke": Color(0.45, 0.47, 0.5),
		"molotov": Color(0.55, 0.35, 0.15), "incendiary": Color(0.6, 0.25, 0.1)}.get(type, Color.GRAY)
	bm.material = m
	mi.mesh = bm
	add_child(mi)
	_wd = WeaponData.new()
	_wd.weapon_id = type
	_wd.weapon_name = Rules.GRENADES.get(type, {}).get("name", type)
	_wd.armor_pen = 0.5
	_wd.kill_reward = int(Rules.GRENADES.get(type, {}).get("reward", 300))
	body_entered.connect(_on_body)


func _on_body(_b: Node) -> void:
	if (type == "molotov" or type == "incendiary") and not _done:
		# polga (tepasi ochiq sirtga) tegsa — yonadi
		var q := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 0.2, global_position + Vector3.DOWN * 0.4, 1)
		var hit := get_world_3d().direct_space_state.intersect_ray(q)
		if not hit.is_empty() and hit.normal.y > 0.7:
			_detonate()


func _physics_process(delta: float) -> void:
	if _done:
		return
	_t += delta
	if linear_velocity.length() < 0.3:
		_still += delta
	else:
		_still = 0.0
	match type:
		"he", "flash":
			if _t >= 1.6:
				_detonate()
		"smoke":
			if (_t > 0.8 and _still > 0.25) or _t > 6.0:
				_detonate()
		_:
			if _t >= 2.0:
				_detonate()
	if global_position.y < -20.0:
		queue_free()


func _gm() -> Node:
	return get_tree().get_first_node_in_group("game_mode")


func _victims() -> Array:
	var gm := _gm()
	return gm.combatants() if gm else []


func _los(a: Vector3, b: Vector3) -> bool:
	var q := PhysicsRayQueryParameters3D.create(a, b, 1)
	return get_world_3d().direct_space_state.intersect_ray(q).is_empty()


func _detonate() -> void:
	_done = true
	freeze = true
	var p := global_position
	match type:
		"he":
			for c in _victims():
				if not c.alive:
					continue
				var tp: Vector3 = c.global_position + Vector3.UP * 1.0
				var d := tp.distance_to(p)
				if d > HE_R or not _los(p + Vector3.UP * 0.2, tp):
					continue
				var raw := HE_MAX * pow(1.0 - d / HE_R, 1.5) * 1.3
				if raw > 0.5:
					Combat.hit(c, raw, "body", thrower, _wd, get_tree())
			_boom(Color(1.0, 0.6, 0.25), 1.6, 0.35)
		"flash":
			for c in _victims():
				if not c.alive:
					continue
				var eye: Vector3 = c.eye() if c.has_method("eye") else c.global_position + Vector3.UP * 1.6
				var d := eye.distance_to(p)
				if d > 25.0 or not _los(p, eye):
					continue
				var fwd: Vector3
				if c.has_method("get") and c.get("cam"):
					fwd = -c.cam.global_transform.basis.z
				else:
					fwd = c.look_dir
				var facing := fwd.normalized().dot((p - eye).normalized())
				var dur := lerpf(0.7, 4.9, clampf((facing + 0.2) / 1.2, 0.0, 1.0)) * clampf(1.2 - d / 25.0, 0.2, 1.0)
				if c.has_method("flashed"):
					c.flashed(dur)
				elif "blind_until" in c:
					c.blind_until = c.clock + dur
			_boom(Color(1, 1, 1), 3.0, 0.15)
		"smoke":
			var body := StaticBody3D.new()
			body.collision_layer = SMOKE_LAYER
			body.collision_mask = 0
			body.add_to_group("smokes")
			var cs := CollisionShape3D.new()
			var sh := SphereShape3D.new()
			sh.radius = SMOKE_R
			cs.shape = sh
			body.add_child(cs)
			var mat := StandardMaterial3D.new()
			mat.albedo_color = Color(0.78, 0.78, 0.76, 0.97)
			mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			mat.cull_mode = BaseMaterial3D.CULL_DISABLED
			for k in 7:
				var mi := MeshInstance3D.new()
				var sm := SphereMesh.new()
				sm.radius = SMOKE_R * (0.7 if k else 0.95)
				sm.height = sm.radius * 2.0
				sm.radial_segments = 10
				sm.rings = 6
				sm.material = mat
				mi.mesh = sm
				mi.position = Vector3(randf_range(-1.4, 1.4), randf_range(0.3, 1.6), randf_range(-1.4, 1.4)) if k else Vector3(0, 1.0, 0)
				body.add_child(mi)
			get_parent().add_child(body)
			body.global_position = p + Vector3.UP * 0.8
			get_tree().create_timer(SMOKE_TIME).timeout.connect(body.queue_free)
			# tutun olovni o'chiradi
			for f in get_tree().get_nodes_in_group("fires"):
				if f.global_position.distance_to(p) < SMOKE_R + FIRE_R:
					f.queue_free()
		_:
			# olov: tutun ichiga tushsa yonmaydi
			for s in get_tree().get_nodes_in_group("smokes"):
				if s.global_position.distance_to(p) < SMOKE_R + 0.5:
					queue_free()
					return
			var fire := Node3D.new()
			fire.set_script(load("res://scripts/fire_area.gd"))
			fire.set("thrower", thrower)
			fire.set("wd", _wd)
			get_parent().add_child(fire)
			var q := PhysicsRayQueryParameters3D.create(p + Vector3.UP * 0.3, p + Vector3.DOWN * 3.0, 1)
			var hit := get_world_3d().direct_space_state.intersect_ray(q)
			fire.global_position = (hit.position if not hit.is_empty() else p) + Vector3.UP * 0.02
	queue_free.call_deferred()


func _boom(col: Color, energy: float, size: float) -> void:
	if DisplayServer.get_name() == "headless":
		return
	var l := OmniLight3D.new()
	l.light_color = col
	l.light_energy = energy * 3.0
	l.omni_range = 9.0
	get_parent().add_child(l)
	l.global_position = global_position + Vector3.UP * 0.3
	var mi := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = size
	sm.height = size * 2.0
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = col
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	sm.material = m
	mi.mesh = sm
	get_parent().add_child(mi)
	mi.global_position = global_position
	var tw := mi.create_tween()
	tw.tween_property(mi, "scale", Vector3.ONE * (8.0 if type == "he" else 3.0), 0.25)
	tw.parallel().tween_property(m, "albedo_color:a", 0.0, 0.3)
	tw.tween_callback(mi.queue_free)
	var tl := l.create_tween()
	tl.tween_property(l, "light_energy", 0.0, 0.35)
	tl.tween_callback(l.queue_free)
	var snd := AudioStreamPlayer3D.new()
	snd.stream = load("res://audio/bomb_explode.wav")
	snd.pitch_scale = 1.8
	snd.volume_db = -4.0
	get_parent().add_child(snd)
	snd.global_position = global_position
	snd.play()
	snd.finished.connect(snd.queue_free)
