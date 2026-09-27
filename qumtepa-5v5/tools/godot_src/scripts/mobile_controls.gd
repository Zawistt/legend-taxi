extends CanvasLayer
## Telefon (Android) uchun sensor boshqaruv. Faqat sensorli qurilmada (yoki --touch bilan) yoqiladi.
##   chap yarmi — suzuvchi joystik (barmoq qo'yilgan joyda paydo bo'ladi): kam egilsa — sekin (jim) yurish, ko'p — yugurish
##   o'ng yarmi — barmoqni surib qarash (OTISH tugmasini bosib turib surish ham qaratadi, CS mobil o'yinlaridagidek)
##   tugmalar: OTISH, NISHON (o'ng tugma / optika), SAKRASH, O'TIRISH, QAYTA O'QLASH, E (bomba / qurol olish),
##   1-5 (qurollar), Q (oldingi), G (tashlash), B (sotib olish), TAB (statistika), MENYU
## Tugmalar TouchScreenButton — Input amallarini (fire, jump, ...) bosadi, shuning uchun o'yin kodi klaviaturadagidek ishlaydi.

const LOOK_SENS := 0.0042          ## radian / piksel (mantiqiy 1600×900 ekranda)
const JOY_R := 110.0

var active := false
var player: Node = null
var hud: Node = null
var _joy_finger := -1
var _joy_center := Vector2.ZERO
var _joy_vec := Vector2.ZERO
var _look_fingers := {}             ## barmoq -> oxirgi joy
var _buttons: Array = []            ## [TouchScreenButton, markaz, radius, qarashga ruxsat]
var _joy_base: Control
var _joy_knob: Control
var _fire_btn: TouchScreenButton


static func wanted() -> bool:
	return OS.has_feature("mobile") or DisplayServer.is_touchscreen_available() or "--touch" in OS.get_cmdline_user_args()


func _ready() -> void:
	layer = 20
	active = wanted()
	if not active:
		set_process(false)
		set_process_input(false)
		return
	player = get_node_or_null("../Player")
	hud = get_node_or_null("../HUD")
	if player:
		player.touch_active = true
	_build()


func _circle(r: float, col: Color) -> ImageTexture:
	var n := int(r * 2)
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	for y in n:
		for x in n:
			var d := Vector2(x + 0.5 - r, y + 0.5 - r).length()
			if d <= r:
				var a := col.a * (1.0 if d < r - 3.0 else 0.6) * (1.0 if d > r - 6.0 else 0.75)
				img.set_pixel(x, y, Color(col.r, col.g, col.b, a))
	return ImageTexture.create_from_image(img)


func _btn(text: String, action: String, center: Vector2, r: float, col: Color, look_ok := false) -> TouchScreenButton:
	var b := TouchScreenButton.new()
	b.texture_normal = _circle(r, col)
	b.texture_pressed = _circle(r, Color(col.r, col.g, col.b, minf(1.0, col.a + 0.3)))
	var sh := CircleShape2D.new()
	sh.radius = r
	b.shape = sh
	b.shape_centered = true
	b.action = action
	b.passby_press = false
	b.visibility_mode = TouchScreenButton.VISIBILITY_ALWAYS
	b.position = center - Vector2(r, r)
	var l := Label.new()
	l.text = text
	l.size = Vector2(r * 2, r * 2)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", int(clampf(r * 0.42, 14, 30)))
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	l.add_theme_constant_override("outline_size", 4)
	b.add_child(l)
	add_child(b)
	_buttons.append([b, center, r, look_ok])
	return b


func _build() -> void:
	var s: Vector2 = get_viewport().get_visible_rect().size
	var W := s.x
	var H := s.y
	var red := Color(0.85, 0.2, 0.15, 0.45)
	var grey := Color(0.1, 0.1, 0.12, 0.42)
	var blue := Color(0.2, 0.4, 0.8, 0.42)
	_fire_btn = _btn("OTISH", "fire", Vector2(W - 210, H - 330), 88, red, true)
	_btn("OTISH", "fire", Vector2(250, H - 470), 52, red, true)                     # chap qo'l uchun ikkinchi otish
	_btn("NISHON", "aim", Vector2(W - 390, H - 420), 50, grey)
	_btn("SAKRASH", "jump", Vector2(W - 80, H - 430), 48, grey)
	_btn("O'TIRISH", "crouch", Vector2(W - 330, H - 150), 50, grey)
	_btn("R", "reload", Vector2(W - 400, H - 270), 42, grey)
	_btn("E", "interact", Vector2(W - 500, H - 120), 44, blue)
	# qurollar — minimap ostida bir qatorda, Q va G — ikkinchi qatorda
	for i in 5:
		_btn(str(i + 1), "weapon_%d" % (i + 1), Vector2(W - 348 + i * 72, 300), 30, grey)
	_btn("Q", "last_weapon", Vector2(W - 60, 372), 28, grey)
	_btn("G", "drop_bomb", Vector2(W - 132, 372), 28, grey)
	_btn("B", "buy_menu", Vector2(70, 170), 40, Color(0.2, 0.6, 0.3, 0.45))
	var tab := _btn("TAB", "", Vector2(70, 265), 36, grey)
	tab.pressed.connect(func() -> void:
		if hud:
			hud._force_board = true)
	tab.released.connect(func() -> void:
		if hud:
			hud._force_board = false)
	var menu := _btn("MENYU", "", Vector2(70, 355), 36, grey)
	menu.pressed.connect(func() -> void:
		if ResourceLoader.exists("res://menu.tscn"):
			get_tree().change_scene_to_file("res://menu.tscn"))
	_joy_base = _ring(JOY_R, Color(1, 1, 1, 0.18))
	_joy_knob = _ring(46.0, Color(1, 1, 1, 0.45))
	_joy_base.visible = false
	_joy_knob.visible = false
	if hud and hud.get("help_lbl"):
		hud.help_lbl.visible = false


func _ring(r: float, col: Color) -> Control:
	var t := TextureRect.new()
	t.texture = _circle(r, col)
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	t.size = Vector2(r * 2, r * 2)
	add_child(t)
	return t


func _on_button(p: Vector2) -> Array:
	for b in _buttons:
		if p.distance_to(b[1]) <= b[2] + 6.0:
			return b
	return []


func _input(event: InputEvent) -> void:
	if not active or player == null:
		return
	var W: float = get_viewport().get_visible_rect().size.x
	if event is InputEventScreenTouch:
		var p: Vector2 = event.position
		if event.pressed:
			var b := _on_button(p)
			if not b.is_empty():
				if b[3]:
					_look_fingers[event.index] = p          # otish tugmasi: surilsa — qarash ham
				return
			if p.x < W * 0.45 and _joy_finger < 0:
				_joy_finger = event.index
				_joy_center = p
				_joy_vec = Vector2.ZERO
				_joy_base.visible = true
				_joy_knob.visible = true
				_joy_base.position = p - Vector2(JOY_R, JOY_R)
				_joy_knob.position = p - Vector2(46, 46)
			elif p.x >= W * 0.45:
				_look_fingers[event.index] = p
		else:
			if event.index == _joy_finger:
				_joy_finger = -1
				_joy_vec = Vector2.ZERO
				_joy_base.visible = false
				_joy_knob.visible = false
			_look_fingers.erase(event.index)
	elif event is InputEventScreenDrag:
		if event.index == _joy_finger:
			var d: Vector2 = event.position - _joy_center
			if d.length() > JOY_R:
				d = d.normalized() * JOY_R
			_joy_vec = d / JOY_R
			_joy_knob.position = _joy_center + d - Vector2(46, 46)
		elif _look_fingers.has(event.index):
			var rel: Vector2 = event.position - _look_fingers[event.index]
			_look_fingers[event.index] = event.position
			var k: float = LOOK_SENS * float(player.get("look_scale") if player.get("look_scale") != null else 1.0)
			player.rotate_y(-rel.x * k)
			player.cam.rotate_x(-rel.y * k)
			player.cam.rotation.x = clampf(player.cam.rotation.x, -1.45, 1.45)


func _process(_d: float) -> void:
	if player == null or not is_instance_valid(player):
		return
	if Input.mouse_mode != Input.MOUSE_MODE_VISIBLE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE         # telefonda kursor ushlanmaydi (menyular sensor bilan bosiladi)
	# joystik: y — oldinga/orqaga, x — yonga; kam egilsa (≤ 55%) — sekin yurish (qadam tovushi yo'q)
	player.touch_move = _joy_vec
	player.touch_walk = _joy_vec.length() > 0.05 and _joy_vec.length() <= 0.55
	var fp = player.get("fp_view")
	var menu_open: bool = fp != null and fp.buy_menu != null and fp.buy_menu.visible
	for b in _buttons:
		b[0].visible = not menu_open or b[0].action == "buy_menu"
