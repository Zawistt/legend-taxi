## Avtomobil yo'llari markaz chiziqlari (shahar/yollar.json).
## Eng yaqin yo'lni topish: mashinani yo'lga qaytarish, ko'cha nomi, keyinchalik
## AI transport va minixarita uchun.
class_name Yollar
extends RefCounted

const FAYL := "res://shahar/yollar.json"
const KATAK := 50.0

var nomlar: PackedStringArray
var yollar: Array = []            # [{sinf, nom, nuqtalar: PackedVector3Array}]
var _katak: Dictionary = {}       # Vector2i -> Array[[yol_i, seg_i]]


func _init() -> void:
	var d: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(FAYL))
	nomlar = PackedStringArray(d["nomlar"])
	for y in d["yollar"]:
		var k: Array = y[2]
		var p := PackedVector3Array()
		p.resize(k.size() / 3)
		for i in p.size():
			p[i] = Vector3(k[i * 3], k[i * 3 + 1], k[i * 3 + 2])
		var yi := yollar.size()
		yollar.append({"sinf": y[0], "nom": nomlar[y[1]] if int(y[1]) >= 0 else "", "nuqtalar": p})
		for i in range(1, p.size()):
			var m := (p[i - 1] + p[i]) * 0.5
			var kk := Vector2i(floori(m.x / KATAK), floori(m.z / KATAK))
			if not _katak.has(kk):
				_katak[kk] = []
			_katak[kk].append([yi, i])


## Eng yaqin yo'l nuqtasi. Natija: {nuqta, yonalish (Vector3, yo'l bo'ylab), nom, masofa}
## yoki bo'sh lug'at (radiusda yo'l yo'q bo'lsa).
func eng_yaqin(pos: Vector3, radius := 60.0) -> Dictionary:
	var eng := {}
	var eng_m := radius
	var r := ceili(radius / KATAK)
	var c := Vector2i(floori(pos.x / KATAK), floori(pos.z / KATAK))
	var p2 := Vector2(pos.x, pos.z)
	for a in range(-r, r + 1):
		for b in range(-r, r + 1):
			var ro: Array = _katak.get(c + Vector2i(a, b), [])
			for s in ro:
				var p: PackedVector3Array = yollar[s[0]]["nuqtalar"]
				var A := p[s[1] - 1]
				var B := p[s[1]]
				var a2 := Vector2(A.x, A.z)
				var ab := Vector2(B.x, B.z) - a2
				var t := clampf((p2 - a2).dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
				var m := p2.distance_to(a2 + ab * t)
				if m < eng_m:
					eng_m = m
					eng = {"nuqta": A.lerp(B, t), "yonalish": (B - A).normalized(),
						"nom": yollar[s[0]]["nom"], "masofa": m}
	return eng
