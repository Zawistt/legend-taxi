extends CanvasLayer
## O'yin interfeysi: vaqt, hisob, joy nomi (callout), jamoa, bomba holati,
## o'rnatish/zararsizlantirish chizig'i, sotib olish menyusi va F1 debug ma'lumoti.

const MapData := preload("res://scripts/map_data.gd")
const GM := preload("res://scripts/game_mode.gd")
const PHASE_NAMES := ["Tayyorgarlik", "Jang", "Bomba o'rnatildi", "Raund tugadi"]
const T_COLOR := Color(0.93, 0.55, 0.25)
const CT_COLOR := Color(0.45, 0.65, 0.95)

@export var game_path: NodePath = ^"../GameMode"
@export var player_path: NodePath = ^"../Player"

@onready var gm: Node = get_node(game_path)
@onready var player: CharacterBody3D = get_node(player_path)

var timer_lbl: Label
var phase_lbl: Label
var score_lbl: Label
var loc_lbl: Label
var team_lbl: Label
var hint_lbl: Label
var banner_lbl: Label
var bar: ProgressBar
var bar_lbl: Label
var buy_panel: PanelContainer
var buy_lbl: Label
var debug_lbl: Label
var help_lbl: Label
var _buy_open := false
var _last_surface := "stone"


func _ready() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	timer_lbl = _label(root, 44, Control.PRESET_CENTER_TOP, Vector2(-100, 14), Vector2(200, 52), HORIZONTAL_ALIGNMENT_CENTER)
	phase_lbl = _label(root, 18, Control.PRESET_CENTER_TOP, Vector2(-150, 66), Vector2(300, 26), HORIZONTAL_ALIGNMENT_CENTER)
	score_lbl = _label(root, 22, Control.PRESET_CENTER_TOP, Vector2(-150, 92), Vector2(300, 30), HORIZONTAL_ALIGNMENT_CENTER)
	loc_lbl = _label(root, 24, Control.PRESET_TOP_LEFT, Vector2(24, 20), Vector2(420, 34), HORIZONTAL_ALIGNMENT_LEFT)
	team_lbl = _label(root, 18, Control.PRESET_TOP_LEFT, Vector2(24, 54), Vector2(420, 28), HORIZONTAL_ALIGNMENT_LEFT)
	hint_lbl = _label(root, 20, Control.PRESET_CENTER_BOTTOM, Vector2(-400, -110), Vector2(800, 30), HORIZONTAL_ALIGNMENT_CENTER)
	help_lbl = _label(root, 14, Control.PRESET_BOTTOM_LEFT, Vector2(24, -40), Vector2(700, 24), HORIZONTAL_ALIGNMENT_LEFT)
	help_lbl.modulate = Color(1, 1, 1, 0.7)
	help_lbl.text = "E — o'rnatish/zararsizlantirish   G — bombani tashlash   B — sotib olish   F1 — zonalar   F2 — jamoa   F3 — raund   F4 — grafika sifati"
	banner_lbl = _label(root, 40, Control.PRESET_CENTER, Vector2(-450, -140), Vector2(900, 110), HORIZONTAL_ALIGNMENT_CENTER)
	banner_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD

	var cross := ColorRect.new()
	cross.color = Color(1, 1, 1, 0.85)
	cross.set_anchors_preset(Control.PRESET_CENTER)
	cross.position = Vector2(-2, -2)
	cross.size = Vector2(4, 4)
	cross.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(cross)

	bar = ProgressBar.new()
	bar.set_anchors_preset(Control.PRESET_CENTER)
	bar.position = Vector2(-160, 60)
	bar.size = Vector2(320, 18)
	bar.show_percentage = false
	bar.max_value = 1.0
	root.add_child(bar)
	bar_lbl = _label(root, 18, Control.PRESET_CENTER, Vector2(-160, 82), Vector2(320, 26), HORIZONTAL_ALIGNMENT_CENTER)

	buy_panel = PanelContainer.new()
	buy_panel.set_anchors_preset(Control.PRESET_CENTER_LEFT)
	buy_panel.position = Vector2(24, -110)
	buy_panel.size = Vector2(360, 220)
	root.add_child(buy_panel)
	buy_lbl = Label.new()
	buy_lbl.label_settings = _settings(18)
	buy_panel.add_child(buy_lbl)

	debug_lbl = _label(root, 15, Control.PRESET_TOP_RIGHT, Vector2(-420, 20), Vector2(400, 200), HORIZONTAL_ALIGNMENT_RIGHT)

	player.footstep.connect(func(s: String) -> void: _last_surface = s)


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


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("buy_menu"):
		_buy_open = not _buy_open


func _process(_delta: float) -> void:
	var t: float = max(gm.time_left, 0.0)
	timer_lbl.text = "%d:%02d" % [int(t) / 60, int(t) % 60]
	timer_lbl.modulate = Color(1, 0.35, 0.3) if gm.phase == GM.Phase.PLANTED else Color.WHITE
	phase_lbl.text = PHASE_NAMES[gm.phase] + "   •   Raund %d" % gm.round_no
	score_lbl.text = "T  %d : %d  CT" % [gm.score["T"], gm.score["CT"]]

	var where := MapData.callout_at(player.global_position)
	loc_lbl.text = where if where != "" else "—"
	team_lbl.text = ("Terrorchilar (T)" if player.team == "T" else "Maxsus kuchlar (CT)") + ("   •   bomba sizda" if player.has_bomb else "")
	team_lbl.modulate = T_COLOR if player.team == "T" else CT_COLOR

	bar.visible = gm.action != ""
	bar_lbl.visible = bar.visible
	if bar.visible:
		bar.value = gm.action_progress / gm.action_duration
		bar_lbl.text = ("Bomba o'rnatilmoqda… " if gm.action == "plant" else "Zararsizlantirilmoqda… ") + "%.1f s" % max(gm.action_duration - gm.action_progress, 0.0)

	hint_lbl.text = _hint()

	banner_lbl.visible = gm.phase == GM.Phase.ROUND_END
	if banner_lbl.visible:
		var who: String = "T" if gm.last_winner == "T" else "CT"
		banner_lbl.text = "%s g'alaba qozondi\n%s" % [who, gm.last_reason]
		if gm.match_winner != "":
			banner_lbl.text += "\nO'YIN TUGADI — %s yutdi" % gm.match_winner
		banner_lbl.modulate = T_COLOR if gm.last_winner == "T" else CT_COLOR

	var can_buy: bool = gm.in_buy_zone()
	buy_panel.visible = _buy_open and can_buy
	if buy_panel.visible:
		buy_lbl.text = "Sotib olish   (%d s qoldi)\n\nAKM — model tayyor bo'lgach\nPichoq — model tayyor bo'lgach\nGranata — model tayyor bo'lgach\nZararsizlantirish to'plami (CT)\n\nB — yopish" % int(gm.buy_time_left)

	debug_lbl.visible = gm.debug_visible
	if debug_lbl.visible:
		var p := player.global_position
		var gfx := get_parent().get_node_or_null(^"Graphics")
		debug_lbl.text = ("grafika: %s\n" % gfx.level_name() if gfx else "") + "FPS %d\npos %.1f, %.1f, %.1f\nsirt: %s\nsite: %s\nsotib olish zonasi: %s\nbomba: %s" % [
			Engine.get_frames_per_second(), p.x, p.y, p.z, _last_surface,
			gm.current_site() if gm.current_site() != "" else "—", "ha" if can_buy else "yo'q", gm.bomb_state]


func _hint() -> String:
	var site: String = gm.current_site()
	match gm.phase:
		GM.Phase.FREEZE:
			return "Tayyorlaning…  B — sotib olish menyusi"
		GM.Phase.LIVE:
			if player.team == "T":
				if player.has_bomb:
					return "E ni bosib turing — bomba o'rnatish" if site != "" else "Bomba sizda — A yoki B site'ga boring"
				if gm.bomb_state == "dropped":
					return "Bomba yerda — ustidan yurib oling"
				return "Site'ni egallang"
			return "Site'larni himoya qiling"
		GM.Phase.PLANTED:
			if player.team == "CT":
				if gm.can_defuse() or gm.action == "defuse":
					return "E ni bosib turing — zararsizlantirish"
				return "Bomba %s site'da! Zararsizlantiring" % gm.planted_site
			return "Bomba o'rnatildi — uni himoya qiling"
	return ""
