extends Node3D
## Birinchi shaxs ko'rinishi: kameraga bog'langan qo'llar va qurol (T — AKM, CT — M416).
## O'yinchining harakatidan o'sha animatsiyalar o'ynaydi (yugurishda qurol tebranadi, o'tirganda pastlaydi),
## ko'z nuqtasi doim kamerada turadi. Model 0.6 marta kichraytirilgan va kameraga yaqinlashtirilgan —
## ko'rinishi aynan bir xil, lekin devorga kirib ketmaydi. Soya tashlamaydi.
## Sichqoncha chap tugmasi — o'q uzish (avtomatik, 600 o'q/daqiqa), R — qayta o'qlash (30 o'q).

const CharacterModel := preload("res://scripts/character_model.gd")
const SCALE := 0.6
const FIRE_INTERVAL := 0.1
const MAG := 30
## qurol ekranda CS dagidek o'ng pastda: kameraga nisbatan siljish (m, kichraytirishdan oldin) va og'ish (°)
## har bir personaj uchun alohida: [siljish, og'ish °, ko'tarilish °] (qurol ekranda o'ng pastda, og'zi nishon tomonga)
const TUNE := {
	"T": [Vector3(0.13, 0.07, -0.06), 5.0, 1.5],
	"CT": [Vector3(0.09, 0.12, -0.1), 4.0, 5.0],
}

var player: CharacterBody3D
var ch: Node3D
var ammo := MAG
var reserve := 90
var shots_fired := 0
var _next_shot := 0.0
var _eye_s := Vector3.ZERO
var _team := ""
var _flash: OmniLight3D
var _shot: AudioStreamPlayer
var _reload_snd: AudioStreamPlayer
var _label: Label
var _t := 0.0
var _reload_end := -1.0


func _ready() -> void:
	player = get_parent().get_parent() as CharacterBody3D
	ch = CharacterModel.new()
	ch.first_person = true
	ch.team = player.team
	_team = player.team
	add_child(ch)
	_flash = OmniLight3D.new()
	_flash.light_color = Color(1.0, 0.75, 0.4)
	_flash.omni_range = 6.0
	_flash.light_energy = 0.0
	_flash.shadow_enabled = false
	_flash.position = Vector3(0.12, -0.12, -0.9)
	add_child(_flash)
	_shot = AudioStreamPlayer.new()
	_shot.stream = load("res://audio/shot_%s.wav" % ("akm" if _team == "T" else "m416"))
	_shot.volume_db = -6.0
	add_child(_shot)
	_reload_snd = AudioStreamPlayer.new()
	_reload_snd.stream = load("res://audio/reload.wav")
	_reload_snd.volume_db = -8.0
	add_child(_reload_snd)
	var layer := CanvasLayer.new()
	layer.layer = 4
	add_child(layer)
	_label = Label.new()
	_label.anchor_left = 1.0
	_label.anchor_top = 1.0
	_label.anchor_right = 1.0
	_label.anchor_bottom = 1.0
	_label.offset_left = -230
	_label.offset_top = -70
	_label.add_theme_font_size_override("font_size", 30)
	_label.add_theme_color_override("font_outline_color", Color.BLACK)
	_label.add_theme_constant_override("outline_size", 6)
	layer.add_child(_label)


func fire() -> bool:
	if ammo <= 0 or _reload_end > _t or player.busy:
		return false
	ammo -= 1
	shots_fired += 1
	ch.fire()
	if player.body:
		player.body.fire()
	_shot.pitch_scale = randf_range(0.96, 1.04)
	_shot.play()
	_flash.light_energy = 3.0
	# tepki: kamera biroz tepaga
	player.cam.rotation.x = clamp(player.cam.rotation.x + 0.006, -1.45, 1.45)
	return true


func reload() -> void:
	if ammo >= MAG or reserve <= 0 or _reload_end > _t:
		return
	ch.reload()
	if player.body:
		player.body.reload()
	_reload_snd.play()
	_reload_end = _t + 2.6


func _process(delta: float) -> void:
	_t += delta
	if player.team != _team:
		_team = player.team
		ch.load_model(_team)
		_shot.stream = load("res://audio/shot_%s.wav" % ("akm" if _team == "T" else "m416"))
	if _reload_end > 0.0 and _t >= _reload_end:
		var need: int = min(MAG - ammo, reserve)
		ammo += need
		reserve -= need
		_reload_end = -1.0
	if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		if Input.is_action_pressed("fire") and _t >= _next_shot:
			if fire():
				_next_shot = _t + FIRE_INTERVAL
		if Input.is_action_just_pressed("reload") or (ammo == 0 and Input.is_action_just_pressed("fire")):
			reload()
	_flash.light_energy = maxf(0.0, _flash.light_energy - delta * 60.0)
	# harakat -> animatsiya (o'yinchi fazosida: -Z oldinga)
	var v: Vector3 = player.global_transform.basis.inverse() * player.velocity
	ch.velocity_local = Vector3(-v.x, 0, -v.z)
	ch.crouching = player.crouching
	ch.on_floor = player.is_on_floor()
	ch.planting = player.busy
	# ko'z nuqtasi kameraga: sekin o'zgarishlar (o'tirish) to'liq qoplanadi, tez tebranish qoladi
	var e: Vector3 = ch.eye_point()
	_eye_s = e if _eye_s == Vector3.ZERO else _eye_s.lerp(e, 1.0 - exp(-delta * 4.0))
	var tn: Array = TUNE.get(_team, TUNE["T"])
	var r := Basis(Vector3.UP, deg_to_rad(tn[1])) * Basis(Vector3.RIGHT, deg_to_rad(tn[2]))
	var b := (r * Basis(Vector3.UP, PI)).scaled(Vector3.ONE * SCALE)
	ch.transform = Transform3D(b, -(b * _eye_s) + tn[0] * SCALE)
	_label.text = "%d / %d" % [ammo, reserve]
	# 1-shaxs faqat o'yinchining o'z kamerasi faol bo'lganda (boshqa kamerada o'yinchi 3-shaxs tana bo'lib ko'rinadi)
	_label.visible = player.cam.current
	ch.visible = player.cam.current
