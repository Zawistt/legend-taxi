extends CanvasLayer
## O'yin interfeysi (CS2 uslubida):
##   tepada — vaqt (bomba o'rnatilsa qizil), hisob, raund, har jamoaning tirik o'yinchilari;
##   chap tepada — joy nomi (callout), jamoa; o'ng tepada — kim kimni o'ldirdi (qurol nomi, boshga — ⌖);
##   chap pastda — sog'liq, zirh (kaska bilan — ⛑); o'ng pastda — pul va granatalar (qurol/o'q — fp_view.gd);
##   o'rtada — bomba o'rnatish/zararsizlantirish chizig'i, o'rnatishda terilayotgan kod (7355608);
##   raund oxirida — kim yutdi va qancha pul olindi; TAB — statistika jadvali (K / D / A / HS% / ADR / pul);
##   zarar olganda qizil chaqnash. F1 — debug ma'lumoti.

const MapData := preload("res://maps/qumtepa3v3/scripts/map_data.gd")
const GM := preload("res://maps/qumtepa3v3/scripts/game_mode.gd")
const Rules := preload("res://scripts/cs_rules.gd")
const PHASE_NAMES := ["Tayyorgarlik", "Jang", "Bomba o'rnatildi", "Raund tugadi"]
const T_COLOR := Color(0.93, 0.55, 0.25)
const CT_COLOR := Color(0.45, 0.65, 0.95)
const GRENADE_SHORT := {"he": "HE", "flash": "FL", "smoke": "SM", "molotov": "MO", "incendiary": "IN"}

@export var game_path: NodePath = ^"../GameMode"
@export var player_path: NodePath = ^"../Player"

@onready var gm: Node = get_node(game_path)
@onready var player: CharacterBody3D = get_node(player_path)

var timer_lbl: Label
var phase_lbl: Label
var score_lbl: Label
var alive_lbl: Label
var loc_lbl: Label
var team_lbl: Label
var hint_lbl: Label
var banner_lbl: Label
var bar: ProgressBar
var bar_lbl: Label
var code_lbl: Label
var hp_lbl: Label
var money_lbl: Label
var nade_lbl: Label
var feed_lbl: RichTextLabel
var debug_lbl: Label
var help_lbl: Label
var board: PanelContainer
var board_lbl: RichTextLabel
var flash: ColorRect
var buy_panel: PanelContainer            ## eski API (v2): endi ishlatilmaydi — scripts/buy_menu.gd
var _last_surface := "stone"


func _ready() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	flash = ColorRect.new()
	flash.color = Color(0.8, 0, 0, 0)
	flash.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(flash)

	timer_lbl = _label(root, 44, Control.PRESET_CENTER_TOP, Vector2(-100, 10), Vector2(200, 52), HORIZONTAL_ALIGNMENT_CENTER)
	score_lbl = _label(root, 24, Control.PRESET_CENTER_TOP, Vector2(-260, 18), Vector2(160, 36), HORIZONTAL_ALIGNMENT_RIGHT)
	phase_lbl = _label(root, 18, Control.PRESET_CENTER_TOP, Vector2(-200, 62), Vector2(400, 26), HORIZONTAL_ALIGNMENT_CENTER)
	alive_lbl = _label(root, 20, Control.PRESET_CENTER_TOP, Vector2(-220, 88), Vector2(440, 28), HORIZONTAL_ALIGNMENT_CENTER)
	loc_lbl = _label(root, 24, Control.PRESET_TOP_LEFT, Vector2(24, 20), Vector2(420, 34), HORIZONTAL_ALIGNMENT_LEFT)
	team_lbl = _label(root, 18, Control.PRESET_TOP_LEFT, Vector2(24, 54), Vector2(420, 28), HORIZONTAL_ALIGNMENT_LEFT)
	hint_lbl = _label(root, 20, Control.PRESET_CENTER_BOTTOM, Vector2(-400, -150), Vector2(800, 30), HORIZONTAL_ALIGNMENT_CENTER)
	help_lbl = _label(root, 13, Control.PRESET_BOTTOM_LEFT, Vector2(24, -34), Vector2(1100, 20), HORIZONTAL_ALIGNMENT_LEFT)
	help_lbl.modulate = Color(1, 1, 1, 0.6)
	help_lbl.text = "B — sotib olish   TAB — statistika   1/2/3/4/5 — qurol/granata/bomba   G — tashlash   E — bomba   X — o'q rejimi   F7 — mashq   F10 — menyu"
	hp_lbl = _label(root, 34, Control.PRESET_BOTTOM_LEFT, Vector2(24, -86), Vector2(420, 44), HORIZONTAL_ALIGNMENT_LEFT)
	money_lbl = _label(root, 30, Control.PRESET_BOTTOM_RIGHT, Vector2(-300, -170), Vector2(280, 40), HORIZONTAL_ALIGNMENT_RIGHT)
	money_lbl.modulate = Color(0.55, 1.0, 0.55)
	nade_lbl = _label(root, 20, Control.PRESET_BOTTOM_RIGHT, Vector2(-420, -120), Vector2(400, 28), HORIZONTAL_ALIGNMENT_RIGHT)
	banner_lbl = _label(root, 36, Control.PRESET_CENTER, Vector2(-450, -170), Vector2(900, 140), HORIZONTAL_ALIGNMENT_CENTER)
	banner_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
	feed_lbl = RichTextLabel.new()
	feed_lbl.bbcode_enabled = true
	feed_lbl.fit_content = true
	feed_lbl.scroll_active = false
	feed_lbl.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	feed_lbl.position = Vector2(-520, 160)
	feed_lbl.size = Vector2(500, 200)
	feed_lbl.add_theme_font_size_override("normal_font_size", 17)
	feed_lbl.add_theme_constant_override("outline_size", 5)
	feed_lbl.add_theme_color_override("font_outline_color", Color.BLACK)
	feed_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(feed_lbl)

	bar = ProgressBar.new()
	bar.set_anchors_preset(Control.PRESET_CENTER)
	bar.position = Vector2(-160, 60)
	bar.size = Vector2(320, 18)
	bar.show_percentage = false
	bar.max_value = 1.0
	root.add_child(bar)
	bar_lbl = _label(root, 18, Control.PRESET_CENTER, Vector2(-160, 82), Vector2(320, 26), HORIZONTAL_ALIGNMENT_CENTER)
	code_lbl = _label(root, 40, Control.PRESET_CENTER, Vector2(-160, 108), Vector2(320, 50), HORIZONTAL_ALIGNMENT_CENTER)
	code_lbl.modulate = Color(1.0, 0.35, 0.3)

	buy_panel = PanelContainer.new()
	buy_panel.visible = false
	root.add_child(buy_panel)
	debug_lbl = _label(root, 15, Control.PRESET_TOP_RIGHT, Vector2(-420, 380), Vector2(400, 200), HORIZONTAL_ALIGNMENT_RIGHT)

	board = PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.04, 0.05, 0.07, 0.86)
	sb.set_corner_radius_all(6)
	sb.set_content_margin_all(16)
	board.add_theme_stylebox_override("panel", sb)
	board.set_anchors_preset(Control.PRESET_CENTER)
	board.position = Vector2(-430, -260)
	board.custom_minimum_size = Vector2(860, 0)
	board.visible = false
	root.add_child(board)
	board_lbl = RichTextLabel.new()
	board_lbl.bbcode_enabled = true
	board_lbl.fit_content = true
	board_lbl.scroll_active = false
	board_lbl.custom_minimum_size = Vector2(828, 0)
	board_lbl.add_theme_font_size_override("normal_font_size", 18)
	board_lbl.add_theme_font_size_override("mono_font_size", 18)
	board.add_child(board_lbl)

	player.footstep.connect(func(s: String) -> void: _last_surface = s)
	player.damaged.connect(func(_a: float, _p: Vector3) -> void: flash.color = Color(0.8, 0, 0, 0.35))


func _settings(size: int) -> LabelSettings:
	var ls := LabelSettings.new()
	ls.font_size = size
	ls.outline_size = maxi(4, size / 6)
	ls.outline_color = Color(0, 0, 0, 0.85)
	return ls


func _label(parent: Control, size: int, preset: int, pos: Vector2, box: Vector2, align: int) -> Label:
	var l := Label.new()
	l.label_settings = _settings(size)
	l.set_anchors_preset(preset)
	l.position += pos
	l.size = box
	l.horizontal_alignment = align
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l


func _process(delta: float) -> void:
	var blind: float = player.blind_amount() if player.has_method("blind_amount") else 0.0
	if blind > 0.0:
		flash.color = Color(1, 1, 1, blind)            # flesh: oq ekran
	else:
		flash.color = Color(0.8, 0, 0, maxf(0.0, flash.color.a - delta * 1.2) if flash.color.r < 0.9 else 0.0)
	var t: float = max(gm.time_left, 0.0)
	timer_lbl.text = "%d:%02d" % [int(t) / 60, int(t) % 60]
	timer_lbl.modulate = Color(1, 0.35, 0.3) if gm.phase == GM.Phase.PLANTED else Color.WHITE
	phase_lbl.text = PHASE_NAMES[gm.phase] + "   •   Raund %d   •   %d gacha" % [gm.round_no, gm.win_target]
	score_lbl.text = ""
	var dots := func(team: String) -> String:
		var s := ""
		for c in gm.team_members(team):
			s += "●" if c.alive else "○"
		return s
	alive_lbl.text = "T %d  %s     %s  %d CT" % [gm.score["T"], dots.call("T"), dots.call("CT"), gm.score["CT"]]
	var where := MapData.callout_at(player.global_position)
	loc_lbl.text = where if where != "" else "—"
	team_lbl.text = ("Terrorchilar (T)" if player.team == "T" else "Maxsus kuchlar (CT)") + ("   •   bomba sizda" if player.has_bomb else "")
	team_lbl.modulate = T_COLOR if player.team == "T" else CT_COLOR
	var lo = player.loadout
	hp_lbl.text = ("+ %d" % int(ceil(player.hp))) + ("     %s %d" % ["Zirh+kaska" if lo.helmet else "Zirh", int(lo.armor)] if lo.armor > 0 else "") \
		if player.alive else "O'LDINGIZ — jamoadoshni kuzatish (sichqoncha)"
	hp_lbl.modulate = Color(1, 0.35, 0.3) if player.alive and player.hp <= 30 else Color.WHITE
	money_lbl.text = "$%d" % lo.money
	var ns := []
	for g in lo.grenades:
		ns.append(GRENADE_SHORT.get(g, g))
	if lo.zeus:
		ns.append("ZEUS")
	if lo.kit:
		ns.append("KIT")
	nade_lbl.text = "  ".join(ns)

	bar.visible = gm.action != ""
	bar_lbl.visible = bar.visible
	code_lbl.visible = gm.action == "plant"
	if bar.visible:
		bar.value = gm.action_progress / gm.action_duration
		bar_lbl.text = ("Bomba o'rnatilmoqda… " if gm.action == "plant" else "Zararsizlantirilmoqda… ") + "%.1f s" % max(gm.action_duration - gm.action_progress, 0.0)
		code_lbl.text = gm.plant_code_shown()
	hint_lbl.text = _hint()
	_update_feed()

	banner_lbl.visible = gm.phase == GM.Phase.ROUND_END
	if banner_lbl.visible:
		var who: String = "T" if gm.last_winner == "T" else "CT"
		banner_lbl.text = "%s g'alaba qozondi\n%s" % [who, gm.last_reason]
		var got: int = gm.last_money.get(player, 0)
		banner_lbl.text += "\n+$%d" % got
		if gm.match_winner != "":
			banner_lbl.text += "\nO'YIN TUGADI — %s yutdi" % gm.match_winner
		banner_lbl.modulate = T_COLOR if gm.last_winner == "T" else CT_COLOR
	board.visible = Input.is_key_pressed(KEY_TAB) or _force_board
	if board.visible:
		board_lbl.text = scoreboard_text()

	debug_lbl.visible = gm.debug_visible
	if debug_lbl.visible:
		var p := player.global_position
		debug_lbl.text = "FPS %d\npos %.1f, %.1f, %.1f\nsirt: %s\nsite: %s\nsotib olish zonasi: %s\nbomba: %s" % [
			Engine.get_frames_per_second(), p.x, p.y, p.z, _last_surface,
			gm.current_site() if gm.current_site() != "" else "—", "ha" if gm.in_buy_zone() else "yo'q", gm.bomb_state]


var _force_board := false


func _update_feed() -> void:
	var now := Time.get_ticks_msec() / 1000.0
	var s := ""
	for e in gm.feed:
		if now - float(e.t) > 8.0:
			continue
		var kc := "#%s" % (T_COLOR if e.killer_team == "T" else CT_COLOR).to_html(false)
		var vc := "#%s" % (T_COLOR if e.victim_team == "T" else CT_COLOR).to_html(false)
		var mine: bool = e.get("attacker") == player or e.get("victim_node") == player
		var line := ("[color=%s]%s[/color]  " % [kc, e.killer] if e.killer != "" else "") + "[%s]%s  [color=%s]%s[/color]" % [
			e.weapon, " (HS)" if e.head else "", vc, e.victim]
		s += ("[bgcolor=#8a1a1a88]%s[/bgcolor]" % line if mine else line) + "\n"
	feed_lbl.text = s


## TAB jadvali: har jamoa, K / D / A / HS% / ADR / pul (raqib pulini ko'rsatmaydi)
func scoreboard_text() -> String:
	var s := "[center][b]T %d : %d CT[/b]   —   raund %d, %d gacha[/center]\n" % [gm.score["T"], gm.score["CT"], gm.round_no, gm.win_target]
	for team in ["CT", "T"]:
		var col := (T_COLOR if team == "T" else CT_COLOR).to_html(false)
		s += "\n[color=#%s][b]%s[/b][/color]\n[table=7]" % [col, "Maxsus kuchlar (CT)" if team == "CT" else "Terrorchilar (T)"]
		for h in ["O'yinchi", "K", "D", "A", "HS%", "ADR", "Pul"]:
			s += "[cell][color=#aaaaaa]%s[/color]     [/cell]" % h
		var mem: Array = gm.team_members(team)
		mem.sort_custom(func(a, b): return a.loadout.kills > b.loadout.kills)
		for c in mem:
			var lo = c.loadout
			var money := "$%d" % lo.money if team == player.team else "—"
			var nm: String = lo.name + ("" if c.alive else " †")
			var cells := [nm, str(lo.kills), str(lo.deaths), str(lo.assists), "%d%%" % lo.hs_pct(), str(lo.adr()), money]
			for v in cells:
				s += ("[cell][b]%s[/b]     [/cell]" % v) if c == player else "[cell]%s     [/cell]" % v
		s += "[/table]\n"
	return s

func _hint() -> String:
	match gm.phase:
		GM.Phase.FREEZE:
			return "Tayyorlaning…  B — sotib olish menyusi"
		GM.Phase.LIVE:
			if not player.alive:
				return ""
			if player.team == "T":
				if player.has_bomb:
					return "E ni bosib turing — bomba o'rnatish (kod)" if gm.plant_circle_at(player.global_position) != "" \
						else ("Bombani qizil aylana ichiga qo'ying" if gm.current_site() != "" else "Bomba sizda — A yoki B site'dagi aylanaga boring")
				if gm.bomb_state == "dropped":
					return "Bomba yerda — ustidan yurib oling"
				return "Site'ni egallang"
			return "Site'larni himoya qiling"
		GM.Phase.PLANTED:
			if player.team == "CT" and player.alive:
				if gm.can_defuse() or gm.action == "defuse":
					return "E ni bosib turing — zararsizlantirish" + ("" if player.loadout.kit else " (to'plamsiz 10 s)")
				return "Bomba %s site'da! Zararsizlantiring" % gm.planted_site
			return "Bomba o'rnatildi — uni himoya qiling"
	return ""
