extends Control
## Minimap (radar): o'ng yuqori burchakda xarita, o'yinchi (o'q), bomba va (bot rejimida) hamma botlar.
## M — katta xarita. Shimol (T spawn) — tepada. Xarita: res://ui/minimap.png (tools/minimap5.py).

const MAP := preload("res://ui/minimap.png")
const MapData := preload("res://scripts/map_data.gd")
const SMALL := 240.0
const BIG := 720.0
const WORLD := 110.0

var big := false
var player: Node3D = null
var gm: Node = null
var bot_match: Node = null


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var root := get_tree().current_scene if get_tree().current_scene else get_parent().get_parent()
	player = root.get_node_or_null("Player")
	gm = root.get_node_or_null("GameMode")
	bot_match = root.get_node_or_null("BotMatch")


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_M:
		big = not big
		queue_redraw()


func _process(_d: float) -> void:
	queue_redraw()


func _to_map(p: Vector3, rect: Rect2) -> Vector2:
	return rect.position + Vector2((p.x - MapData.ORIGIN) / WORLD, (p.z - MapData.ORIGIN) / WORLD) * rect.size


func _arrow(c: Vector2, yaw: float, col: Color, s: float) -> void:
	# yaw: Godot'da -Z oldinga; xaritada tepaga = -Z
	var f := Vector2(-sin(yaw), -cos(yaw))
	var r := Vector2(-f.y, f.x)
	draw_colored_polygon(PackedVector2Array([c + f * s, c - f * s * 0.6 + r * s * 0.6, c - f * s * 0.3, c - f * s * 0.6 - r * s * 0.6]), col)


func _draw() -> void:
	var sz := BIG if big else SMALL
	var vp := get_viewport_rect().size
	var rect := Rect2(Vector2(vp.x - sz - 16, 16) if not big else (vp - Vector2(sz, sz)) / 2.0, Vector2(sz, sz))
	draw_rect(rect.grow(4), Color(0, 0, 0, 0.55))
	draw_texture_rect(MAP, rect, false, Color(1, 1, 1, 0.92))
	var dot := 5.0 if not big else 9.0
	if bot_match:
		for b in bot_match.bots:
			if b.alive:
				var col: Color = Color(0.95, 0.5, 0.15) if b.team == "T" else Color(0.25, 0.5, 1.0)
				_arrow(_to_map(b.global_position, rect), b.rotation.y + PI, col, dot * 1.4)
		if bot_match.bomb_state in ["dropped", "planted"]:
			var bp := _to_map(bot_match.bomb_pos, rect)
			draw_circle(bp, dot, Color(1, 0.1, 0.1))
	if player:
		_arrow(_to_map(player.global_position, rect), player.rotation.y, Color(1, 1, 0.3), dot * 1.8)
	if gm and gm.bomb and is_instance_valid(gm.bomb):
		draw_circle(_to_map(gm.bomb.global_position, rect), dot, Color(1, 0.1, 0.1))
