## Asosiy sahna: muhit (osmon, quyosh, tuman), yer, shahar, mashina, kamera, HUD.
##
## Buyruq qatori (sinov uchun):
##   --sinov        — 6 soniya avtomatik haydaydi, natijani chiqarib yopiladi
##   --surat=FAYL   — sinovdan keyin ekranni PNG ga saqlaydi
extends Node3D

var shahar: Shahar
var yollar: Yollar
var mashina: Mashina
var kamera: Kamera
var hud: Label
var quyosh: DirectionalLight3D
var _sinov := false
var _tepa := false
var _tun := false
var _soyasiz := false
var _oddiy := false                    # sinov: SSAO/SSIL/SDFGI/SSR/hajmli tumansiz
var _kamera_joy := Vector2.INF        # sinov suratlari uchun qo'zg'almas kamera
var _kamera_havo := false
var _surat := ""
var _vaqt := 0.0
var _kocha := ""
var _yangilash := 0.0


func _ready() -> void:
	_tugmalar()
	for a in OS.get_cmdline_user_args():
		if a == "--sinov":
			_sinov = true
		elif a.begins_with("--surat="):
			_surat = a.substr(8)
		elif a == "--tepa":
			_tepa = true
		elif a == "--tun":
			_tun = true
		elif a == "--oddiy":
			_oddiy = true
		elif a == "--soyasiz":
			_soyasiz = true
		elif a.begins_with("--kamera_yol=") or a.begins_with("--kamera_havo="):
			var q := a.split("=")[1].split(",")
			_kamera_joy = Vector2(float(q[0]), float(q[1]))
			_kamera_havo = a.begins_with("--kamera_havo=")
	_muhit()
	_yer()

	shahar = Shahar.new()
	add_child(shahar)

	yollar = Yollar.new()

	var b: Dictionary = shahar.malumot["boshlash"]
	var joy := Vector3(float(b["x"]), float(b["y"]) + 0.5, float(b["z"]))
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
	if _tepa:
		kamera.rejim = Kamera.Rejim.TEPADAN
	if _kamera_joy != Vector2.INF:
		_kamerani_qoy()

	_hud()


## Sinov suratlari: kamerani berilgan joydagi eng yaqin ko'chaga qo'yadi
## (ko'cha sathida yoki havodan), atrofni sinxron yuklaydi.
func _kamerani_qoy() -> void:
	var y := yollar.eng_yaqin(Vector3(_kamera_joy.x, 0, _kamera_joy.y), 300.0)
	if y.is_empty():
		return
	var p: Vector3 = y["nuqta"]
	var d: Vector3 = y["yonalish"]
	kamera.rejim = Kamera.Rejim.ERKIN
	mashina.boshqaruv_yoqilgan = false
	if _kamera_havo:
		kamera.global_position = p + Vector3(40, 70, 90)
		kamera.look_at(p, Vector3.UP)
	else:
		kamera.global_position = p + Vector3.UP * 1.8 - d * 6.0 + d.cross(Vector3.UP) * 1.5
		kamera.look_at(p + d * 30.0 + Vector3.UP * 3.0, Vector3.UP)
	kamera.set("_yaw", kamera.rotation.y)
	kamera.set("_pitch", kamera.rotation.x)
	shahar.darhol_yukla(kamera.global_position, 700.0)


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
	osmon_mat.sky_top_color = Color(0.16, 0.38, 0.74)
	osmon_mat.sky_horizon_color = Color(0.62, 0.72, 0.84)
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
	env.fog_density = 0.00035
	env.fog_aerial_perspective = 0.7
	env.fog_sky_affect = 0.25
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.0018
	env.volumetric_fog_albedo = Color(0.95, 0.9, 0.82)
	env.volumetric_fog_length = 160.0
	env.ssr_enabled = true
	env.ssr_max_steps = 48
	env.adjustment_enabled = true
	env.adjustment_contrast = 1.06
	env.adjustment_saturation = 1.12
	if _oddiy:
		env.ssao_enabled = false
		env.ssil_enabled = false
		env.sdfgi_enabled = false
		env.ssr_enabled = false
		env.volumetric_fog_enabled = false
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	quyosh = DirectionalLight3D.new()
	quyosh.name = "Quyosh"
	quyosh.rotation_degrees = Vector3(-38, -35, 0)   # kechki quyosh — uzun soyalar
	quyosh.light_color = Color(1.0, 0.93, 0.82)
	quyosh.light_energy = 1.6
	quyosh.light_angular_distance = 0.25
	quyosh.shadow_enabled = true
	quyosh.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	quyosh.directional_shadow_max_distance = 450.0
	quyosh.shadow_blur = 1.0
	quyosh.shadow_normal_bias = 1.5
	add_child(quyosh)
	if _soyasiz:
		quyosh.shadow_enabled = false
	if _tun:                                        # tungi ko'rinish sinovi (8-bosqichda kun/tun sikli)
		RenderingServer.global_shader_parameter_set("tun", 1.0)
		quyosh.light_energy = 0.06
		quyosh.light_color = Color(0.6, 0.7, 1.0)
		osmon_mat.sky_top_color = Color(0.01, 0.015, 0.04)
		osmon_mat.sky_horizon_color = Color(0.06, 0.06, 0.09)
		env.ambient_light_energy = 0.15
		env.fog_light_color = Color(0.05, 0.05, 0.08)
		env.volumetric_fog_enabled = false
		env.glow_intensity = 1.0


## Relyef GLB bo'laklar ichida. Bu yerda faqat pastdagi xavfsizlik tekisligi:
## mashina qandaydir yo'l bilan tushib ketsa, yo'lga qaytariladi.
func _yer() -> void:
	var tana := StaticBody3D.new()
	tana.name = "Xavfsizlik"
	var shakl := CollisionShape3D.new()
	shakl.shape = WorldBoundaryShape3D.new()
	tana.add_child(shakl)
	tana.position.y = -200.0
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
	if Input.is_action_just_pressed("qaytish") or mashina.global_position.y < -150.0:
		_yolga_qaytar()
	var kmh := absf(mashina.tezlik()) * 3.6
	if Engine.get_process_frames() % 10 == 0:
		var y := yollar.eng_yaqin(mashina.global_position, 25.0)
		_kocha = y.get("nom", "")
	hud.text = "%d km/soat   %s\nFPS %d   bo'laklar %d (+%d)\nC — kamera   R — yo'lga qaytish" % [
		kmh, _kocha, Engine.get_frames_per_second(), shahar.yuklangan_soni(), shahar.kutilayotgan_soni()]
	if _sinov:
		_sinov_qadam()


## Mashinani eng yaqin avtomobil yo'liga, yo'l bo'ylab qo'yadi.
func _yolga_qaytar() -> void:
	var y := yollar.eng_yaqin(mashina.global_position, 400.0)
	mashina.linear_velocity = Vector3.ZERO
	mashina.angular_velocity = Vector3.ZERO
	if y.is_empty():
		mashina.global_position += Vector3.UP
		mashina.rotation = Vector3(0, mashina.rotation.y, 0)
		return
	var yon: Vector3 = y["yonalish"]
	# mashina oldi yo'nalishiga yaqinroq tomonga qaraysin
	if yon.dot(mashina.global_basis.z) < 0:
		yon = -yon
	mashina.global_position = y["nuqta"] + Vector3.UP * 0.6
	mashina.rotation = Vector3(0, atan2(yon.x, yon.z), 0)


# ---------------- avtomatik sinov ----------------
var _sinov_bosh := Vector3.ZERO
var _maks_tezlik := 0.0
var _surat_olindi := false
var _maks_chetga := 0.0
var _maks_qiya := 0.0
var _tugadi := false


func _sinov_qadam() -> void:
	if _vaqt < 0.1:
		_sinov_bosh = mashina.global_position
	# 1..10 s gaz; 3..5 s keskin chapga — yo'l chegarasiga urilishi kerak
	if _vaqt > 1.0 and _vaqt < 10.0:
		Input.action_press("gaz")
	else:
		Input.action_release("gaz")
	if _vaqt > 3.0 and _vaqt < 5.0:
		Input.action_press("chap")
	else:
		Input.action_release("chap")
	_maks_tezlik = maxf(_maks_tezlik, absf(mashina.tezlik()))
	if _vaqt > 1.0:
		var y := yollar.eng_yaqin(mashina.global_position, 80.0)
		_maks_chetga = maxf(_maks_chetga, y.get("masofa", 99.0))
		_maks_qiya = maxf(_maks_qiya, rad_to_deg(mashina.global_basis.y.angle_to(Vector3.UP)))
	var tayyor := Engine.get_process_frames() > 45 if _kamera_joy != Vector2.INF else _vaqt > 2.6
	if _surat != "" and tayyor and not _surat_olindi:
		_surat_olindi = true
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(_surat)
		print("SURAT: ", _surat)
		if _kamera_joy != Vector2.INF:
			get_tree().quit()
	if _vaqt > 11.0 and not _tugadi and _kamera_joy == Vector2.INF:
		_tugadi = true
		var yer_y := mashina.global_position.y
		print("SINOV: bo'laklar=%d, yo'l=%.1f m, maks tezlik=%.1f km/soat, y=%.2f, maks qiyalik=%.1f°, yo'l o'qidan eng uzoq=%.1f m, ko'cha=%s" % [
			shahar.yuklangan_soni(), mashina.global_position.distance_to(_sinov_bosh),
			_maks_tezlik * 3.6, yer_y, _maks_qiya, _maks_chetga, _kocha])
		get_tree().quit()
