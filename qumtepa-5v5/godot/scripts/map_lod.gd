extends Node
## Masofa bo'yicha ko'rinish (HLOD): faqat sof bezak bo'laklari ("_Decor_") 70 m dan uzoqda yumshoq so'nadi
## va soya tashlamaydi (soya xaritasiga chizilmaydi — kadrga eng katta yutuq).
## Panalar, devorlar, pol va mo'ljal binolari HECH QACHON yashirilmaydi — o'yinchi uzoqdan ham panani ko'rishi shart.

const DECOR_END := 70.0
const DECOR_MARGIN := 8.0

@export var map_path: NodePath = ^"../Map"
var decor_nodes := 0


func _ready() -> void:
	var m := get_node_or_null(map_path)
	if m:
		_walk(m)


func _walk(n: Node) -> void:
	if n is GeometryInstance3D and "_Decor_" in n.name:
		var g := n as GeometryInstance3D
		g.visibility_range_end = DECOR_END
		g.visibility_range_end_margin = DECOR_MARGIN
		g.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		g.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		decor_nodes += 1
	for c in n.get_children():
		_walk(c)
