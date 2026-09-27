## Asosiy sahna: muhit (osmon, quyosh, tuman), yer, shahar, mashina, kamera, HUD.
##
## Buyruq qatori (sinov uchun):
##   --sinov        — 6 soniya avtomatik haydaydi, natijani chiqarib yopiladi
##   --surat=FAYL   — sinovdan keyin ekranni PNG ga saqlaydi
extends Node3D

var shahar: Shahar
var mashina: Mashina
var kamera: Kamera
var hud: Label
var quyosh: DirectionalLight3D
var _sinov := false
var _surat := ""
var _vaqt := 0.0
var _yangilash := 0.0


func _ready() -> void:
	_tugmalar()
	for a in OS.get_cmdline_user_args():
		if a == "--sinov":
			_sinov = true
		elif a.begins_with("--surat="):
			_surat = a.substr(8)
	_muhit()
	_yer()

	shahar = Shahar.new()
	add_child(shahar)

	var b: Dictionary = shahar.malumot["boshlash"]
	var joy := Vector3(float(b["x"]), 0.6, float(b["z"]))
	shahar.darhol_yukla(joy, 500.0)

	mashina = Mashina.new()
	add_child(mashina)
	mashina.global_position = joy
	mashina.rotation.y = PI - float(b["yon"])   # yon: shimoldan soat mili bo'yicha; mashina oldi +Z

	kamera = Kamera.new()
	kamera.nishon = mashina
	add_child(kamera)
	kamera.global_position = joy + mashina.global_basis.z * -9.0 + Vector3.UP * 4.0
	kamera.make_current()

	_hud()


func _tugmalar() -> void:
	var t := {
		"gaz": [KEY_W, KEY_UP], "tormoz": [KEY_S, KEY_DOWN],
		"chap": [KEY_A, KEY_LEFT], "ong": [KEY_D, KEY_RIGHT],
		"qol_tormozi": [KEY_SPACE], "kamera": [KEY_C], "qaytish": [KEY_R],
	}
	for nom in t:
		if not InputMap.has_action(nom):
			InputMap.add_action(nom)
		for k in t[nom]:
			var e := InputEventKey.new()
			e.physical_keycode = k
			InputMap.action_add_event(nom, e)


## GTA uslubidagi yorug'lik: AgX tonemap, SDFGI, hajmli tuman, yumshoq soyalar.
func _muhit() -> void:
	var osmon_mat := ProceduralSkyMaterial.new()
	osmon_mat.sky_top_color = Color(0.22, 0.42, 0.72)
	osmon_mat.sky_horizon_color = Color(0.70, 0.76, 0.82)
	osmon_mat.sky_curve = 0.12
	osmon_mat.ground_horizon_color = Color(0.66, 0.66, 0.64)
	osmon_mat.ground_bottom_color = Color(0.35, 0.32, 0.28)
	osmon_mat.sun_angle_max = 30.0
	osmon_mat.sun_curve = 0.1
	var osmon := Sky.new()
	osmon.sky_material = osmon_mat

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = osmon
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 1.0
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.05
	env.ssao_enabled = true
	env.ssao_radius = 1.6
	env.ssao_intensity = 2.2
	env.ssil_enabled = true
	env.sdfgi_enabled = true
	env.sdfgi_use_occlusion = true
	env.glow_enabled = true
	env.glow_intensity = 0.6
	env.glow_bloom = 0.04
	env.fog_enabled = true
	env.fog_light_color = Color(0.72, 0.76, 0.82)
	env.fog_density = 0.0009
	env.fog_aerial_perspective = 0.7
	env.fog_sky_affect = 0.25
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.006
	env.volumetric_fog_albedo = Color(0.95, 0.9, 0.82)
	env.volumetric_fog_length = 160.0
	env.adjustment_enabled = true
	env.adjustment_contrast = 1.06
	env.adjustment_saturation = 1.12
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	quyosh = DirectionalLight3D.new()
	quyosh.name = "Quyosh"
	quyosh.rotation_degrees = Vector3(-38, -35, 0)   # kechki quyosh — uzun soyalar
	quyosh.light_color = Color(1.0, 0.93, 0.82)
	quyosh.light_energy = 1.6
	quyosh.light_angular_distance = 0.6
	quyosh.shadow_enabled = true
	quyosh.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	quyosh.directional_shadow_max_distance = 450.0
	quyosh.shadow_blur = 1.5
	add_child(quyosh)


## Tekis yer (2-bosqichda real relyef bilan almashtiriladi).
func _yer() -> void:
	var tana := StaticBody3D.new()
	tana.name = "Yer"
	var shakl := CollisionShape3D.new()
	shakl.shape = WorldBoundaryShape3D.new()
	tana.add_child(shakl)
	var mi := MeshInstance3D.new()
	var p := PlaneMesh.new()
	p.size = Vector2(40000, 40000)
	mi.mesh = p
	var m := Materiallar.ol("Yer_Tuproq").duplicate() as StandardMaterial3D
	m.uv1_scale = Vector3(40000.0 / 6.0, 40000.0 / 6.0, 1)
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	tana.add_child(mi)
	add_child(tana)


func _hud() -> void:
	var qatlam := CanvasLayer.new()
	hud = Label.new()
	hud.position = Vector2(18, 14)
	hud.add_theme_font_size_override("font_size", 18)
	hud.add_theme_color_override("font_outline_color", Color.BLACK)
	hud.add_theme_constant_override("outline_size", 6)
	qatlam.add_child(hud)
	add_child(qatlam)


func _process(delta: float) -> void:
	_vaqt += delta
	_yangilash -= delta
	var nishon: Vector3 = kamera.global_position if kamera.rejim == Kamera.Rejim.ERKIN else mashina.global_position
	if _yangilash <= 0.0:
		_yangilash = 0.25
		shahar.yangila(nishon)
	# soya kaskadlari mashinaga ergashadi (quyosh yo'nalishi o'zgarmaydi)
	if Input.is_action_just_pressed("qaytish"):
		_yolga_qaytar()
	var kmh := absf(mashina.tezlik()) * 3.6
	hud.text = "%d km/soat\nFPS %d   bo'laklar %d (+%d)\nC — kamera   R — qaytish" % [
		kmh, Engine.get_frames_per_second(), shahar.yuklangan_soni(), shahar.kutilayotgan_soni()]
	if _sinov:
		_sinov_qadam()


func _yolga_qaytar() -> void:
	mashina.linear_velocity = Vector3.ZERO
	mashina.angular_velocity = Vector3.ZERO
	var r := mashina.rotation
	mashina.rotation = Vector3(0, r.y, 0)
	mashina.global_position += Vector3.UP * 1.0


# ---------------- avtomatik sinov ----------------
var _sinov_bosh := Vector3.ZERO
var _maks_tezlik := 0.0
var _surat_olindi := false
var _tugadi := false


func _sinov_qadam() -> void:
	if _vaqt < 0.1:
		_sinov_bosh = mashina.global_position
	if _vaqt > 1.0 and _vaqt < 6.0:
		Input.action_press("gaz")
	else:
		Input.action_release("gaz")
	if _vaqt > 3.5 and _vaqt < 4.3:
		Input.action_press("chap")
	else:
		Input.action_release("chap")
	_maks_tezlik = maxf(_maks_tezlik, absf(mashina.tezlik()))
	if _surat != "" and _vaqt > 3.2 and not _surat_olindi:
		_surat_olindi = true
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(_surat)
		print("SURAT: ", _surat)
	if _vaqt > 7.0 and not _tugadi:
		_tugadi = true
		print("SINOV: bo'laklar=%d, bosib o'tildi=%.1f m, maks tezlik=%.1f km/soat, balandlik=%.2f, qiyalik=%.1f°" % [
			shahar.yuklangan_soni(), mashina.global_position.distance_to(_sinov_bosh),
			_maks_tezlik * 3.6, mashina.global_position.y,
			rad_to_deg(mashina.global_basis.y.angle_to(Vector3.UP))])
		get_tree().quit()
