extends Node
## Ichkarida (tunnel, spawn, mid) qadam tovushlari aks-sado beradigan shinaga o'tadi,
## ochiq havoda esa oddiy shinaga qaytadi. Shamol ovozi ichkarida pasayadi.

const OUTSIDE_BUS := "Master"
const INSIDE_BUS := "Reverb"
const WIND_OUT_DB := -14.0
const WIND_IN_DB := -26.0

@export var player_path: NodePath = ^"../Player"

@onready var player: CharacterBody3D = get_node(player_path)

var _inside := false
var _steps: AudioStreamPlayer3D
var _wind: AudioStreamPlayer


func _ready() -> void:
	_steps = player.get_node_or_null(^"Steps")
	_wind = get_parent().get_node_or_null(^"Ambience/Wind")
	_apply(false, true)


func _physics_process(_delta: float) -> void:
	var now := _is_inside()
	if now != _inside:
		_apply(now, false)


func _is_inside() -> bool:
	for a in get_tree().get_nodes_in_group("interior_audio"):
		if (a as Area3D).overlaps_body(player):
			return true
	return false


func _apply(inside: bool, force: bool) -> void:
	_inside = inside
	if _steps:
		_steps.bus = INSIDE_BUS if inside else OUTSIDE_BUS
	if _wind:
		var target := WIND_IN_DB if inside else WIND_OUT_DB
		if force:
			_wind.volume_db = target
		else:
			var tw := create_tween()
			tw.tween_property(_wind, "volume_db", target, 0.6)


## Boshqa ovozlar (masalan qurol otishi) uchun: shu yerdan joriy shinani so'rang.
func current_bus() -> String:
	return INSIDE_BUS if _inside else OUTSIDE_BUS
