## Legend Taxi mashinasi. VehicleBody3D: old tomoni +Z.
## Boshqaruv: W/↑ gaz, S/↓ tormoz va orqaga, A D/← → rul, Probel — qo'l tormozi.
class_name Mashina
extends VehicleBody3D

@export var maks_kuch := 3200.0       ## har bir yetakchi g'ildirakka, N
@export var maks_tezlik := 33.0       ## m/s (~120 km/soat)
@export var tormoz_kuchi := 28.0
@export var rul_chegarasi := 0.55     ## radian
@export var rul_tezligi := 2.2

var boshqaruv_yoqilgan := true
var _oldingi_g := []
var _orqa_g := []


func _init() -> void:
	name = "Mashina"
	mass = 1300.0
	center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	center_of_mass = Vector3(0, 0.45, 0.1)
	continuous_cd = true
	var shakl := CollisionShape3D.new()
	var quti := BoxShape3D.new()
	quti.size = Vector3(1.78, 0.95, 4.35)
	shakl.shape = quti
	shakl.position = Vector3(0, 0.85, 0)
	add_child(shakl)
	_korinish()
	for joy in [Vector3(0.8, 0.42, 1.38), Vector3(-0.8, 0.42, 1.38), Vector3(0.8, 0.42, -1.33), Vector3(-0.8, 0.42, -1.33)]:
		var g := VehicleWheel3D.new()
		g.position = joy
		var oldingi: bool = joy.z > 0
		g.use_as_steering = oldingi
		g.use_as_traction = not oldingi
		g.wheel_radius = 0.33
		g.wheel_rest_length = 0.18
		g.suspension_travel = 0.18
		g.suspension_stiffness = 42.0
		g.suspension_max_force = 30000.0
		g.damping_compression = 2.4
		g.damping_relaxation = 3.2
		g.wheel_friction_slip = 3.2 if oldingi else 3.0
		g.wheel_roll_influence = 0.08
		var gm := MeshInstance3D.new()
		var c := CylinderMesh.new()
		c.top_radius = 0.33
		c.bottom_radius = 0.33
		c.height = 0.24
		gm.mesh = c
		gm.rotation.z = PI / 2
		gm.material_override = _mat(Color(0.08, 0.08, 0.08), 0.8)
		g.add_child(gm)
		add_child(g)
		(_oldingi_g if oldingi else _orqa_g).append(g)


func _mat(rang: Color, g_b: float, metall := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = rang
	m.roughness = g_b
	m.metallic = metall
	return m


## Vaqtincha korpus (7-bosqichda real mashina modeli bilan almashtiriladi).
func _korinish() -> void:
	var sariq := _mat(Color(0.95, 0.72, 0.03), 0.25, 0.3)
	sariq.clearcoat_enabled = true
	sariq.clearcoat = 1.0
	var oyna := _mat(Color(0.05, 0.07, 0.09), 0.05, 0.6)
	var qismlar := [
		[Vector3(1.78, 0.62, 4.35), Vector3(0, 0.72, 0), sariq],
		[Vector3(1.56, 0.55, 2.1), Vector3(0, 1.28, -0.2), oyna],
		[Vector3(1.5, 0.06, 1.8), Vector3(0, 1.58, -0.25), sariq],
		[Vector3(0.62, 0.2, 0.28), Vector3(0, 1.71, -0.2), _mat(Color(1, 1, 1), 0.4)],
	]
	for q in qismlar:
		var mi := MeshInstance3D.new()
		var b := BoxMesh.new()
		b.size = q[0]
		mi.mesh = b
		mi.position = q[1]
		mi.material_override = q[2]
		add_child(mi)
	var chiroq := _mat(Color(1, 0.97, 0.85), 0.2)
	chiroq.emission_enabled = true
	chiroq.emission = Color(1, 0.95, 0.8)
	chiroq.emission_energy_multiplier = 3.0
	var stop := _mat(Color(0.6, 0.05, 0.03), 0.3)
	stop.emission_enabled = true
	stop.emission = Color(1, 0.1, 0.05)
	stop.emission_energy_multiplier = 1.5
	for x in [-0.6, 0.6]:
		for z_m in [[2.18, chiroq], [-2.18, stop]]:
			var mi := MeshInstance3D.new()
			var b := BoxMesh.new()
			b.size = Vector3(0.42, 0.16, 0.04)
			mi.mesh = b
			mi.position = Vector3(x, 0.82, z_m[0])
			mi.material_override = z_m[1]
			add_child(mi)


## Oldinga tezlik, m/s (orqaga — manfiy)
func tezlik() -> float:
	return linear_velocity.dot(global_basis.z)


func _physics_process(delta: float) -> void:
	var gaz := 0.0
	var orqa := 0.0
	var rul := 0.0
	var qol := false
	if boshqaruv_yoqilgan:
		gaz = Input.get_action_strength("gaz")
		orqa = Input.get_action_strength("tormoz")
		rul = Input.get_axis("ong", "chap")
		qol = Input.is_action_pressed("qol_tormozi")
	var v := tezlik()
	if gaz > 0.0:
		if v < -1.0:
			engine_force = 0.0
			brake = tormoz_kuchi * gaz
		else:
			engine_force = maks_kuch * gaz * clampf(1.0 - v / maks_tezlik, 0.0, 1.0)
			brake = 0.0
	elif orqa > 0.0:
		if v > 1.0:
			engine_force = 0.0
			brake = tormoz_kuchi * orqa
		else:
			engine_force = -maks_kuch * 0.55 * orqa * clampf(1.0 + v / 9.0, 0.0, 1.0)
			brake = 0.0
	else:
		engine_force = 0.0
		brake = 1.2                                  # motor bilan sekinlashish
	if qol:
		brake = tormoz_kuchi * 0.6
	for g in _orqa_g:
		g.wheel_friction_slip = 1.4 if qol else 3.0  # qo'l tormozida orqa sirpanadi
	var chegara := rul_chegarasi / (1.0 + absf(v) / 14.0)
	steering = move_toward(steering, rul * chegara, rul_tezligi * delta)
