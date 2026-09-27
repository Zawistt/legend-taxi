extends Node3D
## Molotov / yondiruvchi granata olovi: 2.8 m doira, 7 s; ichida turgan har kimga sekundiga ~35 zarar
## (zirh kamaytirmaydi). Tutun tushsa o'chadi (grenade.gd). Botlar olovga kirmaydi (bot_play.gd — "fires" guruhi).

const Combat := preload("res://scripts/combat.gd")
const R := 2.8
const TIME := 7.0
const DPS := 35.0

var thrower: Node = null
var wd: Resource = null
var _t := 0.0
var _tick := 0.0
var _flames: Array = []


func _ready() -> void:
	add_to_group("fires")
	if wd:
		wd.armor_pen = 1.0
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(1.0, 0.45, 0.08, 0.85)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	var disc := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = R
	cm.bottom_radius = R
	cm.height = 0.04
	cm.radial_segments = 16
	cm.material = mat
	disc.mesh = cm
	add_child(disc)
	for k in 14:
		var f := MeshInstance3D.new()
		var pm := PrismMesh.new()
		pm.size = Vector3(0.35, 0.7, 0.35)
		var fm := mat.duplicate()
		fm.albedo_color = Color(1.0, randf_range(0.3, 0.7), 0.05, 0.9)
		pm.material = fm
		f.mesh = pm
		var a := randf() * TAU
		var r := sqrt(randf()) * (R - 0.3)
		f.position = Vector3(cos(a) * r, 0.35, sin(a) * r)
		add_child(f)
		_flames.append(f)
	if DisplayServer.get_name() != "headless":
		var l := OmniLight3D.new()
		l.light_color = Color(1.0, 0.55, 0.2)
		l.light_energy = 2.5
		l.omni_range = 7.0
		l.position = Vector3.UP * 0.8
		add_child(l)


func _physics_process(delta: float) -> void:
	_t += delta
	_tick += delta
	for f in _flames:
		f.scale.y = 0.7 + 0.5 * absf(sin(_t * 9.0 + f.position.x * 3.0))
	if _tick >= 0.25:
		_tick = 0.0
		var gm := get_tree().get_first_node_in_group("game_mode")
		if gm:
			for c in gm.combatants():
				if not c.alive:
					continue
				var d := Vector2(c.global_position.x - global_position.x, c.global_position.z - global_position.z).length()
				if d <= R and absf(c.global_position.y - global_position.y) < 1.5:
					Combat.hit(c, DPS * 0.25, "leg", thrower, wd, get_tree())
	if _t >= TIME:
		queue_free()


func contains(p: Vector3) -> bool:
	return Vector2(p.x - global_position.x, p.z - global_position.z).length() <= R + 0.4
