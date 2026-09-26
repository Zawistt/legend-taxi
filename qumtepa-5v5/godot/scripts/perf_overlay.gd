extends Label
## F9 — ishlash ko'rsatkichlari: FPS, kadr vaqti, chizish buyruqlari, obyektlar, uchburchaklar, yorug'lik manbalari.

var on := false


func _ready() -> void:
	visible = false
	position = Vector2(20, 120)
	add_theme_font_size_override("font_size", 18)
	add_theme_color_override("font_outline_color", Color.BLACK)
	add_theme_constant_override("outline_size", 6)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_F9:
		on = not on
		visible = on


func _process(_d: float) -> void:
	if not on:
		return
	var rs := RenderingServer
	text = "FPS %d  (%.1f ms)\nchizish buyruqlari %d\nobyektlar %d\nuchburchaklar %d\nocclusion culling: %s" % [
		Engine.get_frames_per_second(), 1000.0 / max(Engine.get_frames_per_second(), 1),
		rs.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		rs.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
		rs.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME),
		"yoqilgan" if get_viewport().use_occlusion_culling else "o'chirilgan"]
