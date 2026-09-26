extends Node3D
## Atmosfera: fon tovushlarini halqaga qo'yish, havodagi chang zarralari, kun/shom rejimlari.
## F4 — "Shom" (quyosh botishi) va "Kunduzi" o'rtasida almashtirish.
## Raqobat rejimi — "Kunduzi": quyosh sharq-g'arb o'qida, ~50° balandlikda — hech bir jamoa quyoshga qarab o'ynamaydi.
## "Shom" — faqat ko'rinish uchun (past quyosh bir tomonni ko'zni qamashtiradi), raqobatda ishlatilmaydi.

const D := preload("res://scripts/atmo_data.gd")

@export var sun_path: NodePath = ^"../Sun"
@export var env_path: NodePath = ^"../WorldEnvironment"

var dusk := false
var _day := {}


func _ready() -> void:
	for p in get_tree().get_nodes_in_group("ambient"):
		var s: AudioStreamWAV = p.stream
		if s:
			s = s.duplicate()
			s.loop_mode = AudioStreamWAV.LOOP_FORWARD
			s.loop_begin = 0
			s.loop_end = s.data.size() / 2   # 16-bit mono
			p.stream = s
			p.play(randf() * 10.0)
	if DisplayServer.get_name() != "headless":
		_make_dust()
	var sun: DirectionalLight3D = get_node(sun_path)
	var env: Environment = (get_node(env_path) as WorldEnvironment).environment
	_day = {"basis": sun.global_transform.basis, "color": sun.light_color, "energy": sun.light_energy,
		"fog": env.fog_light_color, "ambient": env.ambient_light_color}


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_F4:
		set_dusk(not dusk)


func set_dusk(v: bool) -> void:
	dusk = v
	var sun: DirectionalLight3D = get_node(sun_path)
	var env: Environment = (get_node(env_path) as WorldEnvironment).environment
	if v:
		var dir := Vector3(-0.95, 0.3, -0.05).normalized()     # g'arbda past quyosh
		sun.global_transform.basis = Basis.looking_at(-dir, Vector3.UP)
		sun.light_color = Color(1.0, 0.62, 0.38)
		sun.light_energy = 1.1
		env.fog_light_color = Color(0.95, 0.62, 0.45)
		env.ambient_light_color = Color(0.72, 0.55, 0.5)
	else:
		sun.global_transform.basis = _day.basis
		sun.light_color = _day.color
		sun.light_energy = _day.energy
		env.fog_light_color = _day.fog
		env.ambient_light_color = _day.ambient


## Havodagi chang: ochiq maydonlarda sekin suzuvchi mayda zarralar (faqat ko'rinish, ko'rishni to'smaydi)
func _make_dust() -> void:
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.albedo_color = Color(1.0, 0.95, 0.85, 0.16)
	mat.vertex_color_use_as_albedo = true
	var quad := QuadMesh.new()
	quad.size = Vector2(0.018, 0.018)
	quad.material = mat
	for b in D.DUST:
		var p := GPUParticles3D.new()
		var pm := ParticleProcessMaterial.new()
		pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
		pm.emission_box_extents = b[1] * 0.5
		pm.gravity = Vector3(0, -0.02, 0)
		pm.direction = Vector3(1, 0.1, 0.3)
		pm.spread = 180.0
		pm.initial_velocity_min = 0.05
		pm.initial_velocity_max = 0.25
		pm.turbulence_enabled = true
		pm.turbulence_noise_strength = 0.4
		pm.scale_min = 0.6
		pm.scale_max = 1.6
		var grad := Gradient.new()
		grad.set_color(0, Color(1, 1, 1, 0))
		grad.add_point(0.2, Color(1, 1, 1, 1))
		grad.add_point(0.8, Color(1, 1, 1, 1))
		grad.set_color(grad.get_point_count() - 1, Color(1, 1, 1, 0))
		var gt := GradientTexture1D.new()
		gt.gradient = grad
		pm.color_ramp = gt
		p.process_material = pm
		p.draw_pass_1 = quad
		p.amount = int(b[2])
		p.lifetime = 14.0
		p.preprocess = 14.0
		p.visibility_aabb = AABB(-b[1] * 0.6, b[1] * 1.2)
		p.position = b[0]
		add_child(p)
