extends PanelContainer
## Sotib olish menyusi (CS2 uslubida), B — ochish/yopish. Faqat sotib olish zonasida va sotib olish vaqtida.
## Bo'limlar: 1 To'pponchalar, 2 SMG, 3 Avtomatlar (snayperlar bilan), 4 Og'ir (drobovik, pulemyot), 5 Granatalar, 6 Jihozlar.
## Klaviatura: avval bo'lim raqami, keyin qurol raqami (0 / Backspace — orqaga). Sichqoncha bilan ham bosiladi.
## Har qurolning rasmi — uning 3D shakli (character_model.gd, kichik SubViewport'da chiziladi), narxi, qisqa ma'lumoti.
## Pul, tomon (T/CT qurollari), granata cheklovlari (ko'pi bilan 4, flesh 2) — loadout.gd dagi qoidalar.

const Rules := preload("res://scripts/cs_rules.gd")
const WeaponIcon := preload("res://scripts/weapon_icon.gd")
const CATS := [
	["pistol", "To'pponchalar"], ["smg", "SMG"], ["rifle", "Avtomatlar"], ["heavy", "Og'ir"], ["grenade", "Granatalar"], ["gear", "Jihozlar"]]
const ORDER := {
	"pistol": ["glock", "usp", "p2000", "elite", "p250", "tec9", "fiveseven", "cz75", "deagle", "revolver"],
	"smg": ["mac10", "mp9", "mp7", "mp5sd", "ump45", "p90", "bizon"],
	"rifle": ["galil", "famas", "ak47", "m4a4", "m4a1s", "sg553", "aug", "ssg08", "awp", "g3sg1", "scar20"],
	"heavy": ["nova", "xm1014", "sawedoff", "mag7", "m249", "negev"],
	"grenade": ["flash", "smoke", "he", "molotov", "incendiary"],
	"gear": ["kevlar", "vesthelm", "kit", "zeus"],
}
const GEAR_NAMES := {"kevlar": "Zirh (kevlar)", "vesthelm": "Zirh + kaska", "kit": "Zararsizlantirish to'plami"}

var fpv: Node3D
var open := false
var cat := -1
var _title: Label
var _cats: VBoxContainer
var _grid: GridContainer
var _icons := {}
var _gm: Node
var _mouse_before := Input.MOUSE_MODE_CAPTURED


func _ready() -> void:
	custom_minimum_size = Vector2(940, 560)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.05, 0.06, 0.08, 0.9)
	sb.set_corner_radius_all(8)
	sb.set_content_margin_all(14)
	add_theme_stylebox_override("panel", sb)
	var v := VBoxContainer.new()
	add_child(v)
	_title = Label.new()
	_title.add_theme_font_size_override("font_size", 22)
	v.add_child(_title)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 16)
	v.add_child(h)
	_cats = VBoxContainer.new()
	_cats.custom_minimum_size = Vector2(200, 0)
	h.add_child(_cats)
	for i in CATS.size():
		var b := Button.new()
		b.text = "%d  %s" % [i + 1, CATS[i][1]]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size = Vector2(200, 56)
		b.add_theme_font_size_override("font_size", 19)
		b.pressed.connect(func() -> void: select_cat(i))
		_cats.add_child(b)
	_grid = GridContainer.new()
	_grid.columns = 3
	_grid.add_theme_constant_override("h_separation", 10)
	_grid.add_theme_constant_override("v_separation", 10)
	h.add_child(_grid)
	visible = false


func game_mode() -> Node:
	if _gm == null:
		_gm = get_tree().get_first_node_in_group("game_mode")
	return _gm


func can_buy() -> bool:
	var gm := game_mode()
	return gm != null and gm.in_buy_zone()


func items_of(c: String) -> Array:
	var team: String = fpv.player.team
	var out: Array = []
	for id in ORDER[c]:
		if Rules.GRENADES.has(id):
			var gside: String = Rules.GRENADES[id].side
			if gside == "both" or gside == team:
				out.append(id)
		elif GEAR_NAMES.has(id):
			if id != "kit" or team == "CT":
				out.append(id)
		else:
			var w: Resource = Rules.weapon(id)
			if w and (w.side == "both" or w.side == team):
				out.append(id)
	return out


## sotib olish (menyu, test yoki boshqa kod): pul yechiladi, qurol qo'lga olinadi
func buy_item(id: String) -> bool:
	if not can_buy():
		return false
	var lo = fpv.player.loadout
	if not lo.try_buy(id, fpv.player.team):
		return false
	var w: Resource = Rules.weapon(id)
	if w and id != "zeus":
		fpv.buy(id)
	return true


func select_cat(i: int) -> void:
	cat = i
	_rebuild()


func _unhandled_input(event: InputEvent) -> void:
	if fpv == null or not fpv.player.local_player:
		return
	if event.is_action_pressed("buy_menu"):
		set_open(not open)
		get_viewport().set_input_as_handled()
		return
	if not visible or not (event is InputEventKey) or not event.pressed or event.echo:
		return
	if event.physical_keycode == KEY_BACKSPACE or event.physical_keycode == KEY_0 or event.physical_keycode == KEY_ESCAPE:
		if cat >= 0:
			cat = -1
			_rebuild()
		else:
			set_open(false)
		get_viewport().set_input_as_handled()
		return
	var k: int = event.physical_keycode - KEY_1
	if k < 0 or k > 8:
		return
	if cat < 0:
		if k < CATS.size():
			select_cat(k)
	else:
		var its := items_of(CATS[cat][0])
		if k < its.size():
			buy_item(its[k])
			_rebuild()
	get_viewport().set_input_as_handled()


func set_open(v: bool) -> void:
	open = v
	cat = -1
	if DisplayServer.get_name() != "headless":
		if v:
			_mouse_before = Input.mouse_mode
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		elif Input.mouse_mode == Input.MOUSE_MODE_VISIBLE:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	_rebuild()


func _process(_d: float) -> void:
	var show: bool = open and can_buy() and fpv.player.cam.current
	if open and not can_buy():
		set_open(false)
	visible = show
	if show:
		size = get_combined_minimum_size()
		position = ((get_viewport_rect().size - size) * 0.5).floor()
		var gm := game_mode()
		_title.text = "SOTIB OLISH   $%d   (%d s)      B / Esc — yopish" % [fpv.player.loadout.money, int(gm.buy_time_left)]


func _rebuild() -> void:
	if _grid == null:
		return
	for c in _grid.get_children():
		c.queue_free()
	for i in _cats.get_child_count():
		(_cats.get_child(i) as Button).modulate = Color(1, 0.85, 0.4) if i == cat else Color.WHITE
	if cat < 0:
		return
	var lo = fpv.player.loadout
	var team: String = fpv.player.team
	var its := items_of(CATS[cat][0])
	for i in its.size():
		var id: String = its[i]
		var card := Button.new()
		card.custom_minimum_size = Vector2(220, 150)
		var why: String = lo.buy_block_reason(id, team)
		card.disabled = why != "" and why != "bor"
		card.modulate = Color(1, 1, 1) if why == "" else (Color(0.6, 0.9, 0.6) if why == "bor" else Color(0.55, 0.55, 0.55))
		var vb := VBoxContainer.new()
		vb.mouse_filter = Control.MOUSE_FILTER_IGNORE
		vb.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		card.add_child(vb)
		var tr := TextureRect.new()
		tr.custom_minimum_size = Vector2(200, 80)
		tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		tr.texture = _icon(id, team)
		tr.mouse_filter = Control.MOUSE_FILTER_IGNORE
		vb.add_child(tr)
		var l := Label.new()
		l.text = "%d  %s\n$%d%s" % [i + 1, _name(id), lo.price_of(id), ("   (" + why + ")") if why != "" else ""]
		l.add_theme_font_size_override("font_size", 15)
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		vb.add_child(l)
		card.tooltip_text = _info(id)
		card.pressed.connect(func() -> void:
			buy_item(id)
			_rebuild())
		_grid.add_child(card)


func _name(id: String) -> String:
	if GEAR_NAMES.has(id):
		return GEAR_NAMES[id]
	if Rules.GRENADES.has(id):
		return Rules.GRENADES[id].name
	var w: Resource = Rules.weapon(id)
	return w.weapon_name if w else id


func _info(id: String) -> String:
	var w: Resource = Rules.weapon(id)
	if w == null or id == "zeus":
		return _name(id)
	return "%s — zarar %d (bosh ×%.0f), zirh teshish %d%%, %d o'q/daq, magazin %d/%d, o'ldirish uchun $%d" % [
		w.weapon_name, int(w.base_damage), w.headshot_multiplier, int(w.armor_pen * 100.0), int(w.fire_rate),
		w.magazine_size, w.reserve_ammo, w.kill_reward]


## qurol rasmi (weapon_icon.gd), bir marta chiziladi
func _icon(id: String, team: String) -> Texture2D:
	var key := id + team
	if _icons.has(key):
		return _icons[key]
	var kind := 7
	var w: Resource = Rules.weapon(id)
	if w:
		kind = int(w.kind)
	elif id == "kit":
		kind = 9
	elif id in ["kevlar", "vesthelm"]:
		kind = -1
	var tex := WeaponIcon.make(self, kind, team, w.weapon_id if w else "", Vector2i(220, 88), id == "vesthelm")
	if tex:
		_icons[key] = tex
	return tex
