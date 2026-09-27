extends Control
## Bosh menyu: xaritani tanlash. 5v5 — Qumtepa (110×110 m), 3v3 — Qumtepa v2 low-poly (50×50 m), 5v5 botlar o'yini.
## 4 — inventar (hamma qurollar). Klaviatura: 1 / 2 / 3 / 4. O'yin ichida F10 — menyuga qaytish.

const MAPS := [
	["Qumtepa 5v5", "110 × 110 m, 5 hudud, bomba rejimi", "res://main.tscn"],
	["Qumtepa 3v3", "50 × 50 m, low-poly, bomba rejimi", "res://main_3v3.tscn"],
	["5v5 botlar o'yini", "kuzatish (tomoshabin kamerasi)", "res://bots.tscn"],
	["Inventar", "hamma qurollar: CS2, zaxira, PUBG Mobile", "res://inventory.tscn"],
]


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = Color(0.12, 0.2, 0.32)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var box := VBoxContainer.new()
	box.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	box.custom_minimum_size = Vector2(620, 0)
	box.position -= Vector2(310, 200)
	box.add_theme_constant_override("separation", 14)
	add_child(box)
	var title := Label.new()
	title.text = "QUMTEPA"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 64)
	box.add_child(title)
	for i in MAPS.size():
		var b := Button.new()
		b.text = "%d.  %s — %s" % [i + 1, MAPS[i][0], MAPS[i][1]]
		b.custom_minimum_size = Vector2(620, 64)
		b.add_theme_font_size_override("font_size", 24)
		b.pressed.connect(start.bind(i))
		box.add_child(b)
	var help := Label.new()
	help.text = "O'yin ichida: F10 — shu menyuga qaytish"
	help.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(help)


func start(i: int) -> void:
	get_tree().change_scene_to_file(MAPS[i][2])


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var k: int = event.physical_keycode - KEY_1
		if k >= 0 and k < MAPS.size():
			start(k)
