extends Control
## Inventar (bosh menyu -> 4): hamma qurollar nomi, rasmi va xususiyatlari bilan.
##   1  CS2 qurollari — o'yinda sotib olinadigan 34 ta qurol (+ pichoq, Zeus), bo'limlar CS2 dagidek
##   2  Zaxira — o'zimiz yasagan eski qurollar (LAR-01, AR-44, Spectre-9, Longbow-50, Breacher-12, Apex-9):
##      o'yindan olib tashlangan, shu yerda saqlanadi
##   3  PUBG Mobile — eng mashhur 10 ta qurol (o'yinda sotilmaydi)
## Kartochka bosilsa — o'ngda to'liq ma'lumot. Esc / Backspace — bosh menyuga.

const Rules := preload("res://scripts/cs_rules.gd")
const WeaponIcon := preload("res://scripts/weapon_icon.gd")
const TABS := [["cs2", "CS2 qurollari"], ["zaxira", "Zaxira (eski qurollar)"], ["pubg", "PUBG Mobile"]]
const CAT_TITLE := {"pistol": "To'pponchalar", "smg": "SMG", "rifle": "Avtomatlar va snayperlar", "heavy": "Og'ir qurollar",
	"other": "Pichoq va Zeus"}
const SIDE := {"T": "faqat T", "CT": "faqat CT", "both": "ikkala tomon"}
const MODES := ["bittalik", "3 talik", "avtomat"]

var tab := 0
var selected: Resource = null
var _list: VBoxContainer
var _tabs: HBoxContainer
var _info: RichTextLabel
var _preview: TextureRect
var _count: Label


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = Color(0.08, 0.1, 0.14)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var root := VBoxContainer.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.offset_left = 24
	root.offset_right = -24
	root.offset_top = 16
	root.offset_bottom = -16
	root.add_theme_constant_override("separation", 10)
	add_child(root)
	var head := HBoxContainer.new()
	root.add_child(head)
	var title := Label.new()
	title.text = "INVENTAR"
	title.add_theme_font_size_override("font_size", 34)
	head.add_child(title)
	_count = Label.new()
	_count.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_count.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	head.add_child(_count)
	var back := Button.new()
	back.text = "  Esc — orqaga  "
	back.pressed.connect(close)
	head.add_child(back)
	_tabs = HBoxContainer.new()
	_tabs.add_theme_constant_override("separation", 8)
	root.add_child(_tabs)
	for i in TABS.size():
		var b := Button.new()
		b.text = "%d  %s (%d)" % [i + 1, TABS[i][1], weapons_of(TABS[i][0]).size()]
		b.custom_minimum_size = Vector2(300, 44)
		b.add_theme_font_size_override("font_size", 18)
		b.pressed.connect(select_tab.bind(i))
		_tabs.add_child(b)
	var body := HBoxContainer.new()
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 16)
	root.add_child(body)
	var sc := ScrollContainer.new()
	sc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.size_flags_stretch_ratio = 2.2
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	body.add_child(sc)
	_list = VBoxContainer.new()
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_list.add_theme_constant_override("separation", 6)
	sc.add_child(_list)
	var side := PanelContainer.new()
	side.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.12, 0.14, 0.19)
	sb.set_corner_radius_all(8)
	sb.set_content_margin_all(14)
	side.add_theme_stylebox_override("panel", sb)
	body.add_child(side)
	var sv := VBoxContainer.new()
	side.add_child(sv)
	_preview = TextureRect.new()
	_preview.custom_minimum_size = Vector2(0, 170)
	_preview.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_preview.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	sv.add_child(_preview)
	_info = RichTextLabel.new()
	_info.bbcode_enabled = true
	_info.fit_content = true
	_info.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_info.add_theme_font_size_override("normal_font_size", 17)
	sv.add_child(_info)
	select_tab(0)


## origin bo'yicha qurollar (cs2 — pichoq va Zeus ham)
func weapons_of(origin: String) -> Array:
	var out: Array = Rules.by_origin(origin)
	if origin == "cs2":
		out.append(Rules.weapon("combat_knife"))
		out.append(Rules.weapon("zeus"))
	return out


func select_tab(i: int) -> void:
	tab = i
	for k in _tabs.get_child_count():
		(_tabs.get_child(k) as Button).modulate = Color(1, 0.85, 0.4) if k == i else Color.WHITE
	for c in _list.get_children():
		c.queue_free()
	var ws: Array = weapons_of(TABS[i][0])
	_count.text = "%s: %d ta qurol" % [TABS[i][1], ws.size()]
	var groups := {}
	var order: Array = []
	for w in ws:
		var g: String = w.buy_category if w.buy_category in CAT_TITLE else ("other" if w.kind in [2, 8] else _cat_of(w))
		if not groups.has(g):
			groups[g] = []
			order.append(g)
		groups[g].append(w)
	for g in ["pistol", "smg", "rifle", "heavy", "other"]:
		if not groups.has(g):
			continue
		var h := Label.new()
		h.text = "%s  (%d)" % [CAT_TITLE[g], groups[g].size()]
		h.add_theme_font_size_override("font_size", 20)
		h.modulate = Color(0.75, 0.85, 1.0)
		_list.add_child(h)
		var grid := GridContainer.new()
		grid.columns = 4
		grid.add_theme_constant_override("h_separation", 8)
		grid.add_theme_constant_override("v_separation", 8)
		_list.add_child(grid)
		for w in groups[g]:
			grid.add_child(_card(w))
	show_weapon(ws[0] if ws.size() else null)


func _cat_of(w: Resource) -> String:
	match int(w.kind):
		1:
			return "pistol"
		3:
			return "smg"
		5, 6:
			return "heavy"
	return "rifle"


func _card(w: Resource) -> Button:
	var b := Button.new()
	b.custom_minimum_size = Vector2(230, 120)
	var vb := VBoxContainer.new()
	vb.mouse_filter = Control.MOUSE_FILTER_IGNORE
	vb.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	b.add_child(vb)
	var tr := TextureRect.new()
	tr.custom_minimum_size = Vector2(210, 70)
	tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	tr.texture = WeaponIcon.make(self, int(w.kind), "T" if w.side == "T" else "CT", w.weapon_id)
	tr.mouse_filter = Control.MOUSE_FILTER_IGNORE
	vb.add_child(tr)
	var l := Label.new()
	l.text = "%s\n%s" % [w.weapon_name, ("$%d" % w.price) if w.price > 0 else w.category_name]
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", 15)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	vb.add_child(l)
	b.pressed.connect(show_weapon.bind(w))
	return b


func show_weapon(w: Resource) -> void:
	selected = w
	if w == null:
		_info.text = ""
		_preview.texture = null
		return
	_preview.texture = WeaponIcon.make(self, int(w.kind), "T" if w.side == "T" else "CT", w.weapon_id, Vector2i(440, 170))
	_info.text = describe(w)


## qurolning to'liq ma'lumoti (matn — testlar ham tekshiradi)
func describe(w: Resource) -> String:
	var s := "[b][font_size=26]%s[/font_size][/b]\n%s" % [w.weapon_name, w.category_name]
	match w.origin:
		"cs2":
			s += "  •  CS2  •  %s" % SIDE.get(w.side, w.side)
		"zaxira":
			s += "  •  zaxira (eski, o'zimiz yasagan) — o'yinda sotilmaydi"
		"pubg":
			s += "  •  PUBG Mobile — o'yinda sotilmaydi"
	s += "\n\n"
	if w.price > 0:
		s += "Narx: [b]$%d[/b]     O'ldirish mukofoti: $%d\n" % [w.price, w.kill_reward]
	if w.kind == 8:
		return s + "Bitta otishda o'ldiradi (%.1f m gacha), keyin %d s da qayta zaryadlanadi." % [w.max_range, int(Rules.ZEUS_RECHARGE)]
	var dmg := "%d" % int(w.base_damage)
	if w.projectile_count > 1:
		dmg = "%d × %d sochma" % [w.projectile_count, int(w.base_damage)]
	s += "Zarar: [b]%s[/b]  (bosh ×%.2g → %d)\n" % [dmg, w.headshot_multiplier, int(w.base_damage * w.headshot_multiplier)]
	if w.kind == 2:
		return s + "Masofa: %.1f m" % w.max_range
	s += "Zirh teshish: %d%%\n" % int(round(w.armor_pen * 100.0))
	var modes: Array = []
	for m in w.fire_modes:
		modes.append(MODES[int(m)])
	s += "Tezlik: %d o'q/daqiqa  (%s)\n" % [int(w.fire_rate), ", ".join(modes)]
	s += "Magazin: %d / %d     Qayta o'qlash: %.1f s\n" % [w.magazine_size, w.reserve_ammo, w.reload_time]
	if w.range_modifier > 0.0:
		s += "Masofada: 25 m da %d, 50 m da %d\n" % [int(w.damage_at(25.0, "body")), int(w.damage_at(50.0, "body"))]
	s += "Yurish tezligi: ×%.2f" % w.move_speed
	if w.scope:
		s += "\nOptika (o'ng tugma)"
	elif w.ads_ready:
		s += "\nNishonga olish (o'ng tugma)"
	return s


func close() -> void:
	get_tree().change_scene_to_file("res://menu.tscn")


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode in [KEY_ESCAPE, KEY_BACKSPACE]:
			close()
		else:
			var k: int = event.physical_keycode - KEY_1
			if k >= 0 and k < TABS.size():
				select_tab(k)
