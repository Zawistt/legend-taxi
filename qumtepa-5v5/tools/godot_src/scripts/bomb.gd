extends Node3D
## Bomba (C4). O'rnatilgach signal beradi, vaqt kamaygan sari tezlashadi.
## Portlaganda: olov shari va xarita bo'ylab tarqaladigan zarba to'lqini (44 m gacha, CS2 radiusi), chang halqasi.

var time_left := 0.0
var total := 35.0
var planted := false
var _beep_timer := 0.0

@onready var body: Node3D = $Body
@onready var led: OmniLight3D = $Led
@onready var beep: AudioStreamPlayer3D = $Beep
@onready var boom: AudioStreamPlayer3D = $Boom
@onready var blast: MeshInstance3D = $Blast


func plant(timer: float) -> void:
	planted = true
	total = timer
	time_left = timer
	_beep_timer = 0.0


func _process(delta: float) -> void:
	if not planted:
		led.light_energy = 0.0
		return
	_beep_timer -= delta
	if _beep_timer <= 0.0:
		_beep_timer = clamp(time_left / total, 0.08, 1.0)
		beep.play()
		led.light_energy = 3.0
	led.light_energy = max(0.0, led.light_energy - delta * 14.0)


func defuse() -> void:
	planted = false


func explode() -> void:
	planted = false
	body.visible = false
	boom.play()
	blast.visible = true
	blast.scale = Vector3.ONE * 0.2
	blast.transparency = 0.0
	var tw := create_tween()
	tw.tween_property(blast, "scale", Vector3.ONE * 9.0, 0.5).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_EXPO)
	tw.tween_property(blast, "transparency", 1.0, 0.9)
	# zarba to'lqini: shaffof shar va yerdagi chang halqasi 44 m gacha kengayadi
	var wave := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 1.0
	sm.height = 2.0
	sm.radial_segments = 32
	sm.rings = 16
	var wm := StandardMaterial3D.new()
	wm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	wm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	wm.cull_mode = BaseMaterial3D.CULL_DISABLED
	wm.albedo_color = Color(1.0, 0.85, 0.6, 0.35)
	sm.material = wm
	wave.mesh = sm
	add_child(wave)
	var ring := MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = 0.8
	tm.outer_radius = 1.0
	tm.rings = 48
	var rm := wm.duplicate()
	rm.albedo_color = Color(0.75, 0.65, 0.5, 0.6)
	tm.material = rm
	ring.mesh = tm
	ring.scale = Vector3(1, 0.4, 1)
	add_child(ring)
	var tw2 := create_tween().set_parallel(true)
	tw2.tween_property(wave, "scale", Vector3.ONE * 44.0, 1.3).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
	tw2.tween_property(wm, "albedo_color:a", 0.0, 1.3)
	tw2.tween_property(ring, "scale", Vector3(44.0, 2.0, 44.0), 1.6).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
	tw2.tween_property(rm, "albedo_color:a", 0.0, 1.6)
	var fl := OmniLight3D.new()
	fl.light_color = Color(1.0, 0.7, 0.4)
	fl.light_energy = 16.0
	fl.omni_range = 40.0
	fl.position = Vector3.UP * 2.0
	add_child(fl)
	tw2.tween_property(fl, "light_energy", 0.0, 1.0)
