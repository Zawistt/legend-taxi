extends Node
## Grafika sifati: F4 bilan uch daraja aylanadi.
## Yuqori — SDFGI, volumetrik tuman, SSIL, SSAO, chang (kuchli kompyuter uchun).
## O'rta  — SSAO va chang qoladi, SDFGI va volumetrik tuman o'chadi.
## Past   — faqat quyosh, soyalar va oddiy tuman.
## Raqobatli o'yinda "O'rta" eng barqaror FPS beradi.

enum Level { HIGH, MEDIUM, LOW }
const NAMES := ["Yuqori", "O'rta", "Past"]

@export var start_level: int = Level.HIGH

var level: int = Level.HIGH
var _env: Environment


func _ready() -> void:
	preload("res://scripts/input_setup.gd").ensure()
	var we := get_parent().get_node_or_null(^"WorldEnvironment") as WorldEnvironment
	if we:
		_env = we.environment
	apply(start_level)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("graphics_quality"):
		apply((level + 1) % NAMES.size())


func apply(new_level: int) -> void:
	level = new_level
	var high := level == Level.HIGH
	var mid_or_better := level <= Level.MEDIUM
	if _env:
		_env.sdfgi_enabled = high
		_env.volumetric_fog_enabled = high
		_env.ssil_enabled = high
		_env.ssao_enabled = mid_or_better
		_env.glow_enabled = mid_or_better
		_env.fog_enabled = true
	for n in get_tree().get_nodes_in_group("fx_dust"):
		n.visible = mid_or_better
	var sun := get_parent().get_node_or_null(^"Sun") as DirectionalLight3D
	if sun:
		sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS if mid_or_better \
			else DirectionalLight3D.SHADOW_ORTHOGONAL
		sun.directional_shadow_max_distance = 95.0 if mid_or_better else 55.0
	for p in get_tree().get_nodes_in_group("fx_probes"):
		p.visible = mid_or_better


func level_name() -> String:
	return NAMES[level]
