extends PanelContainer
## Sotib olish menyusi (B): faqat sotib olish zonasida va sotib olish vaqtida ochiladi.
## 1–5 — asosiy qurolni tanlash (to'liq magazin bilan qo'lga oladi). Pul tizimi hali yo'q — hamma qurol bepul.
## Qurollar ro'yxati va ko'rsatkichlari weapons/*.tres dan olinadi (slot = 1 bo'lganlar).

var fpv: Node3D
var open := false
var items: Array = []
var _label: Label
var _gm: Node


func _ready() -> void:
	set_anchors_preset(Control.PRESET_CENTER_LEFT)
	position = Vector2(24, 200)
	custom_minimum_size = Vector2(560, 0)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.05, 0.06, 0.08, 0.82)
	sb.set_corner_radius_all(6)
	sb.set_content_margin_all(14)
	add_theme_stylebox_override("panel", sb)
	_label = Label.new()
	_label.add_theme_font_size_override("font_size", 19)
	add_child(_label)
	for w in fpv.weapons:
		if w.slot == 1:
			items.append(w)
	visible = false


func game_mode() -> Node:
	if _gm == null and fpv.player.get_parent():
		_gm = fpv.player.get_parent().get_node_or_null("GameMode")
	return _gm


func can_buy() -> bool:
	var gm := game_mode()
	return gm != null and gm.in_buy_zone() and gm.player == fpv.player


func buy_index(i: int) -> bool:
	if i < 0 or i >= items.size() or not can_buy():
		return false
	var ok: bool = fpv.buy(items[i].weapon_id)
	if ok:
		open = false
	return ok


func _unhandled_input(event: InputEvent) -> void:
	if fpv == null or not fpv.player.local_player:
		return
	if event.is_action_pressed("buy_menu"):
		open = not open
	elif visible and event is InputEventKey and event.pressed and not event.echo:
		var k: int = event.physical_keycode - KEY_1
		if k >= 0 and k < items.size():
			buy_index(k)
			get_viewport().set_input_as_handled()


func _process(_d: float) -> void:
	visible = open and can_buy() and fpv.player.cam.current
	if not visible:
		return
	var gm := game_mode()
	var t := "SOTIB OLISH   (%d s qoldi)      B — yopish\n\n" % int(gm.buy_time_left)
	for i in items.size():
		var w: Resource = items[i]
		var mark := "  ◀ qo'lda" if fpv.owned.get(1) == w else ""
		var dmg := "%d×%d" % [w.projectile_count, int(w.base_damage)] if w.projectile_count > 1 else "%d" % int(w.base_damage)
		t += "%d  %-15s %-9s zarar %s, bosh ×%.1f, %d o'q/daq, magazin %d%s\n" % [i + 1, w.weapon_name, w.category_name,
			dmg, w.headshot_multiplier, int(w.fire_rate), w.magazine_size, mark]
	t += "\nDoim: Apex-9 to'pponcha (2), pichoq (3). Pul tizimi hali yo'q — bepul."
	_label.text = t
