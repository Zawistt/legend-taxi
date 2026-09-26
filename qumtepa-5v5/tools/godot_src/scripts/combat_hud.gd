extends Control
## Jang HUD'i (Legend Tactical FPS'dagi CombatHUD g'oyasi asosida):
##   - nishon belgisi: 4 chiziq, oradagi bo'shliq hozirgi tarqalishga teng (ekranda o'q qayerga tushishi mumkinligi);
##     ADS da so'nadi (qurol markazda), pichoqda — nuqta;
##   - tegish belgisi (X): tanaga — oq, boshga — qizil, o'ldirganda — kattaroq; 0.25 s ko'rinadi.

var fpv: Node3D
var hit_t := -1.0
var hit_zone := ""
var hit_killed := false
var _t := 0.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	fpv.hit_confirmed.connect(_on_hit)


func _on_hit(zone: String, _dmg: float, killed: bool) -> void:
	hit_t = _t
	hit_zone = zone
	hit_killed = killed


func hitmarker_visible() -> bool:
	return hit_t >= 0.0 and _t - hit_t < 0.25


func _process(delta: float) -> void:
	_t += delta
	queue_redraw()


func _draw() -> void:
	if fpv == null or fpv.player == null:
		return
	var vs := get_viewport_rect().size
	var c := vs * 0.5
	var cam: Camera3D = fpv.player.cam
	# tarqalish burchagi -> piksel (vertikal FOV bo'yicha)
	var px: float = tan(fpv.current_spread()) / tan(deg_to_rad(cam.fov) * 0.5) * vs.y * 0.5
	var a: float = 1.0 - fpv.ads_amt
	var col := Color(0.55, 1.0, 0.6, 0.9 * a)
	if fpv.is_knife():
		draw_circle(c, 2.5, Color(1, 1, 1, 0.9))
	elif a > 0.05:
		var gap := 4.0 + px
		var ln := 9.0
		for d in [Vector2.RIGHT, Vector2.LEFT, Vector2.UP, Vector2.DOWN]:
			draw_line(c + d * gap, c + d * (gap + ln), Color(0, 0, 0, 0.6 * a), 4.0)
			draw_line(c + d * gap, c + d * (gap + ln), col, 2.0)
		draw_circle(c, 1.5, col)
	if hitmarker_visible():
		var k := 1.0 - (_t - hit_t) / 0.25
		var hc := Color(1.0, 0.2, 0.15, k) if hit_zone == "head" else Color(1, 1, 1, k)
		var s := 14.0 if hit_killed else 10.0
		for d in [Vector2(1, 1), Vector2(-1, 1), Vector2(1, -1), Vector2(-1, -1)]:
			draw_line(c + d * 5.0, c + d * s, hc, 2.5)
