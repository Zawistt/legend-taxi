## Protsedural daraxt modellari (MultiMesh uchun). Har bir tur ikki darajada:
## yaqin (batafsil) va uzoq (sodda) — visibility_range bilan almashadi.
## Turlar: 0 chinor, 1 terak, 2 mevali (o'rik/tut), 3 archa.
class_name Daraxtlar
extends RefCounted

const BARG_SHADER := preload("res://shaderlar/barg.gdshader")
const YAQIN_MASOFA := 220.0
const UZOQ_MASOFA := 900.0

static var _kesh: Dictionary = {}

# tur: [tana balandligi, tana radiusi, [[markaz, radiuslar], ...] shabba bo'laklari,
#       barg ranglari a, b, tirqish]
const TURLAR := {
	0: [4.8, 0.28, [[Vector3(0, 9.5, 0), Vector3(4.6, 3.8, 4.6)], [Vector3(1.9, 11.2, 0.8), Vector3(3.2, 2.9, 3.2)],
		[Vector3(-1.7, 10.6, -1.2), Vector3(3.0, 2.8, 3.0)], [Vector3(0.4, 7.4, 1.6), Vector3(3.2, 2.4, 3.0)]],
		Color(0.22, 0.36, 0.11), Color(0.44, 0.54, 0.18), 0.30],
	1: [3.0, 0.2, [[Vector3(0, 11.0, 0), Vector3(1.8, 8.0, 1.8)], [Vector3(0, 17.5, 0), Vector3(1.1, 3.6, 1.1)]],
		Color(0.24, 0.36, 0.13), Color(0.40, 0.50, 0.17), 0.28],
	2: [1.9, 0.13, [[Vector3(0, 3.7, 0), Vector3(2.5, 1.9, 2.5)], [Vector3(0.9, 4.3, 0.3), Vector3(1.7, 1.4, 1.7)],
		[Vector3(-0.7, 3.3, -0.6), Vector3(1.6, 1.3, 1.6)]],
		Color(0.20, 0.34, 0.10), Color(0.38, 0.50, 0.15), 0.34],
	3: [1.2, 0.15, [[Vector3(0, 3.2, 0), Vector3(2.1, 2.6, 2.1)], [Vector3(0, 5.6, 0), Vector3(1.5, 2.2, 1.5)],
		[Vector3(0, 7.6, 0), Vector3(0.8, 1.6, 0.8)]],
		Color(0.08, 0.18, 0.09), Color(0.16, 0.28, 0.13), 0.22],
}


static func _barg_mat(tur: int) -> ShaderMaterial:
	var t: Array = TURLAR[tur]
	var m := ShaderMaterial.new()
	m.shader = BARG_SHADER
	m.set_shader_parameter("rang_a", t[3])
	m.set_shader_parameter("rang_b", t[4])
	m.set_shader_parameter("tirqish", t[5])
	if tur == 3:
		m.set_shader_parameter("shamol", 0.4)
		m.set_shader_parameter("barg_olchami", 4.0)
	return m


static func _tana_mat(tur: int) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.62, 0.58, 0.5) if tur == 0 else Color(0.33, 0.28, 0.22)
	m.roughness = 0.95
	return m


## Shovqin bilan buzilgan ellipsoid (shabba bo'lagi).
static func _top(st: SurfaceTool, markaz: Vector3, r: Vector3, seg: int, halqa: int, sh: FastNoiseLite, kuch: float) -> void:
	var nuq := []
	for i in halqa + 1:
		var fi := PI * float(i) / halqa
		var qator := []
		for j in seg + 1:
			var te := TAU * float(j) / seg
			var d := Vector3(sin(fi) * cos(te), cos(fi), sin(fi) * sin(te))
			var q := d * r
			var k := 1.0 + kuch * sh.get_noise_3dv(markaz + q * 0.6)
			qator.append(markaz + q * k)
		nuq.append(qator)
	for i in halqa:
		for j in seg:
			var a: Vector3 = nuq[i][j]
			var b: Vector3 = nuq[i + 1][j]
			var c: Vector3 = nuq[i + 1][j + 1]
			var d: Vector3 = nuq[i][j + 1]
			for v in [a, b, c, a, c, d]:
				st.add_vertex(v)


static func mesh(tur: int, yaqin: bool) -> ArrayMesh:
	var kalit := tur * 2 + (1 if yaqin else 0)
	if _kesh.has(kalit):
		return _kesh[kalit]
	var t: Array = TURLAR[tur]
	var mesh := ArrayMesh.new()
	# tana
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var c := CylinderMesh.new()
	c.top_radius = t[1] * 0.65
	c.bottom_radius = t[1]
	c.height = t[0] + 1.5
	c.radial_segments = 8 if yaqin else 5
	c.rings = 1
	st.append_from(c, 0, Transform3D(Basis(), Vector3(0, (t[0] + 1.5) / 2.0, 0)))
	st.set_material(_tana_mat(tur))
	st.commit(mesh)
	# shabba
	var sh := FastNoiseLite.new()
	sh.seed = 17 + tur
	sh.frequency = 0.45
	var bs := SurfaceTool.new()
	bs.begin(Mesh.PRIMITIVE_TRIANGLES)
	var bolaklar: Array = t[2]
	for i in bolaklar.size():
		if not yaqin and i >= 2:
			break
		var b: Array = bolaklar[i]
		var r: Vector3 = b[1]
		if not yaqin and bolaklar.size() > 2:
			r *= 1.12                                   # uzoq modelda kam bo'lak — kattaroq
		_top(bs, b[0], r, 14 if yaqin else 7, 9 if yaqin else 5, sh, 0.28 if yaqin else 0.12)
	bs.index()                                          # silliq normallar uchun
	bs.generate_normals()
	bs.set_material(_barg_mat(tur))
	bs.commit(mesh)
	_kesh[kalit] = mesh
	return mesh


## Bo'lak tuguniga daraxtlarni qo'shadi. Yozuv: [x, y, z, burilish, tur, o'lcham].
static func qosh(tugun: Node3D, yozuvlar: Array) -> void:
	var guruh := {}
	for r in yozuvlar:
		var tur := int(r[4])
		if not guruh.has(tur):
			guruh[tur] = []
		guruh[tur].append(r)
	for tur in guruh:
		var ro: Array = guruh[tur]
		for yaqin in [true, false]:
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.use_custom_data = true
			mm.mesh = mesh(tur, yaqin)
			mm.instance_count = ro.size()
			for i in ro.size():
				var r: Array = ro[i]
				var s := float(r[5])
				var b := Basis(Vector3.UP, float(r[3])).scaled(Vector3(s, s * randf_range(0.92, 1.08), s))
				mm.set_instance_transform(i, Transform3D(b, Vector3(r[0], r[1], r[2])))
				mm.set_instance_custom_data(i, Color(fmod(float(r[3]) * 0.617, 1.0), 0, 0, 0))
			var mi := MultiMeshInstance3D.new()
			mi.name = "daraxt_%d_%s" % [tur, "yaqin" if yaqin else "uzoq"]
			mi.multimesh = mm
			if yaqin:
				mi.visibility_range_end = YAQIN_MASOFA
				mi.visibility_range_end_margin = 10.0
			else:
				mi.visibility_range_begin = YAQIN_MASOFA
				mi.visibility_range_begin_margin = 10.0
				mi.visibility_range_end = UZOQ_MASOFA
				mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			mi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
			tugun.add_child(mi)
