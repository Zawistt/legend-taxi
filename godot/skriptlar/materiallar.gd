## GLB ichidagi material nomlarini (Devor_Suvoq, Yol_Asfalt, ...) Godot materiallariga
## almashtiradi. GLB'dagi UV metrda: 1 birlik = 1 metr.
##
## Hozircha (1-bosqich) teksturalar protsedural: FastNoiseLite'dan normal va
## g'adir-budurlik xaritalari. 3-bosqichda bular real PBR teksturalar bilan
## almashtiriladi — shu fayldagi `_yasa` ni o'zgartirish kifoya.
class_name Materiallar
extends RefCounted

static var _kesh: Dictionary = {}

# nom: [rang, g'adir-budurlik, tekstura o'lchami (metr), shovqin kuchi]
const TAVSIF := {
	"Devor_Suvoq":  [Color(0.86, 0.80, 0.69), 0.90, 3.0, 0.35],
	"Devor_Gisht":  [Color(0.70, 0.50, 0.37), 0.92, 1.5, 0.60],
	"Devor_Panel":  [Color(0.80, 0.78, 0.74), 0.85, 3.0, 0.30],
	"Devor_Dokon":  [Color(0.84, 0.82, 0.78), 0.70, 3.0, 0.25],
	"Devor_Jamoat": [Color(0.88, 0.84, 0.74), 0.85, 3.0, 0.30],
	"Devor_Garaj":  [Color(0.62, 0.60, 0.57), 0.95, 2.0, 0.40],
	"Obida_Gisht":  [Color(0.84, 0.70, 0.49), 0.90, 1.2, 0.55],
	"Tom_Tekis":    [Color(0.42, 0.41, 0.40), 0.95, 4.0, 0.35],
	"Tom_Shifer":   [Color(0.58, 0.60, 0.59), 0.80, 1.0, 0.50],
	"Tom_Obida":    [Color(0.13, 0.50, 0.74), 0.35, 2.0, 0.20],
	"Yol_Asfalt":   [Color(0.20, 0.21, 0.22), 0.88, 4.0, 0.45],
	"Yol_Mahalla":  [Color(0.29, 0.29, 0.29), 0.93, 4.0, 0.55],
	"Yol_Piyoda":   [Color(0.64, 0.58, 0.48), 0.90, 1.0, 0.50],
	"Yol_Tuproq":   [Color(0.55, 0.47, 0.36), 1.00, 3.0, 0.60],
	"Temir_Yol":    [Color(0.32, 0.28, 0.25), 0.95, 2.0, 0.50],
	"Yer_Maysa":    [Color(0.33, 0.47, 0.23), 1.00, 3.0, 0.60],
	"Yer_Dala":     [Color(0.48, 0.50, 0.28), 1.00, 4.0, 0.60],
	"Yer_Qabr":     [Color(0.50, 0.50, 0.41), 1.00, 3.0, 0.50],
	"Yer_Tuproq":   [Color(0.58, 0.52, 0.42), 1.00, 6.0, 0.50],
	"Suv":          [Color(0.10, 0.24, 0.30), 0.05, 8.0, 0.30],
	"Balkon":       [Color(0.80, 0.79, 0.76), 0.85, 1.0, 0.25],
}


const DEVOR_SHADER := preload("res://shaderlar/devor.gdshader")
const TOM_SHADER := preload("res://shaderlar/tom.gdshader")

# Devorlar (devor.gdshader): turi, 3 ta rang (bino urug'i bo'yicha tanlanadi), deraza o'lchamlari
const DEVORLAR := {
	"Devor_Suvoq": {"turi": 0, "rang_a": Color(0.90, 0.85, 0.74), "rang_b": Color(0.93, 0.80, 0.62),
		"rang_c": Color(0.86, 0.87, 0.84), "deraza_eni": 1.3, "deraza_boyi": 1.5, "oraliq": 3.6, "darvoza": true},
	"Devor_Gisht": {"turi": 1, "rang_a": Color(0.66, 0.40, 0.27), "rang_b": Color(0.78, 0.60, 0.42),
		"rang_c": Color(0.62, 0.50, 0.40), "deraza_eni": 1.3, "deraza_boyi": 1.5, "oraliq": 3.6, "darvoza": true},
	"Devor_Panel": {"turi": 2, "rang_a": Color(0.80, 0.78, 0.73), "rang_b": Color(0.86, 0.80, 0.68),
		"rang_c": Color(0.74, 0.76, 0.78), "deraza_eni": 1.45, "deraza_boyi": 1.45, "oraliq": 3.0},
	"Devor_Dokon": {"turi": 0, "rang_a": Color(0.90, 0.89, 0.86), "rang_b": Color(0.80, 0.78, 0.74),
		"rang_c": Color(0.92, 0.86, 0.72), "deraza_eni": 1.6, "deraza_boyi": 1.6, "oraliq": 3.4, "dokon_qavat": true},
	"Devor_Jamoat": {"turi": 0, "rang_a": Color(0.93, 0.88, 0.72), "rang_b": Color(0.86, 0.90, 0.88),
		"rang_c": Color(0.95, 0.83, 0.70), "deraza_eni": 2.0, "deraza_boyi": 1.9, "oraliq": 3.3},
	"Devor_Garaj": {"turi": 1, "rang_a": Color(0.62, 0.55, 0.47), "rang_b": Color(0.70, 0.66, 0.60),
		"rang_c": Color(0.58, 0.58, 0.56), "garaj": true},
	"Obida_Gisht": {"turi": 6, "rang_a": Color(0.86, 0.72, 0.50), "rang_b": Color(0.82, 0.68, 0.46),
		"rang_c": Color(0.88, 0.76, 0.56), "derazalar": false},
}
const TOMLAR := {
	"Tom_Shifer": {"turi": 0, "rang": Color(0.60, 0.61, 0.60)},
	"Tom_Tekis": {"turi": 1, "rang": Color(0.36, 0.35, 0.34)},
	"Tom_Obida": {"turi": 1, "rang": Color(0.74, 0.64, 0.48)},
}


static func ol(nom: String) -> Material:
	if _kesh.has(nom):
		return _kesh[nom]
	var m: Material
	if DEVORLAR.has(nom):
		m = _shader(DEVOR_SHADER, DEVORLAR[nom], nom)
	elif TOMLAR.has(nom):
		m = _shader(TOM_SHADER, TOMLAR[nom], nom)
	else:
		m = _yasa(nom)
	_kesh[nom] = m
	return m


static func _shader(sh: Shader, param: Dictionary, nom: String) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.resource_name = nom
	m.shader = sh
	for k in param:
		m.set_shader_parameter(k, param[k])
	return m


static func _shovqin(chastota: float, normal: bool, seed_: int) -> NoiseTexture2D:
	var n := FastNoiseLite.new()
	n.seed = seed_
	n.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	n.frequency = chastota
	n.fractal_octaves = 4
	var t := NoiseTexture2D.new()
	t.width = 512
	t.height = 512
	t.seamless = true
	t.as_normal_map = normal
	t.bump_strength = 4.0
	t.noise = n
	if not normal:
		# rang uchun: 0.8..1.0 oralig'ida (MUL aralashmada juda qoraymasin)
		var g := Gradient.new()
		g.set_color(0, Color(0.8, 0.8, 0.8))
		g.set_color(1, Color(1, 1, 1))
		t.color_ramp = g
	return t


static func _yasa(nom: String) -> Material:
	var tv: Array = TAVSIF.get(nom, [Color(1, 0, 1), 1.0, 1.0, 0.0])
	var m := StandardMaterial3D.new()
	m.resource_name = nom
	m.albedo_color = tv[0]
	m.roughness = tv[1]
	var olcham: float = tv[2]
	m.uv1_scale = Vector3(1.0 / olcham, 1.0 / olcham, 1.0)
	var kuch: float = tv[3]
	if kuch > 0.0:
		m.normal_enabled = true
		m.normal_texture = _shovqin(0.02, true, nom.hash())
		m.normal_scale = kuch
		# rangdagi bir tekis bo'lmagan dog'lar
		m.detail_enabled = true
		m.detail_blend_mode = BaseMaterial3D.BLEND_MODE_MUL
		m.detail_albedo = _shovqin(0.008, false, nom.hash() + 7)
		m.detail_uv_layer = BaseMaterial3D.DETAIL_UV_1
	if nom == "Suv":
		m.metallic = 0.0
		m.roughness = 0.04
		m.metallic_specular = 0.9
	if nom.begins_with("Yol_") or nom.begins_with("Yer_") or nom == "Suv" or nom == "Temir_Yol":
		# yer qatlamlari ustma-ust tushganda miltillamasin
		m.render_priority = 0
	return m


## Sahnadagi barcha MeshInstance3D sirtlariga nom bo'yicha material qo'yadi.
static func qoy(ildiz: Node) -> void:
	for n in ildiz.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		if mi.mesh == null:
			continue
		for i in mi.mesh.get_surface_count():
			var eski := mi.mesh.surface_get_material(i)
			var nom := eski.resource_name if eski else ""
			if TAVSIF.has(nom) or DEVORLAR.has(nom) or TOMLAR.has(nom):
				mi.set_surface_override_material(i, ol(nom))
		if mi.name.begins_with("Devor_") or mi.name.begins_with("Obida_") or mi.name.begins_with("Tom_"):
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		else:
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
