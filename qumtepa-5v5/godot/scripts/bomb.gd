extends Node3D
## Bomba (vaqtinchalik model). O'rnatilgach signal beradi, vaqt kamaygan sari tezlashadi.

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
