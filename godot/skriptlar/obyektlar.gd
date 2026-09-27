## Ko'p takrorlanadigan obyektlar (balkonlar; keyingi bosqichlarda daraxtlar,
## fonarlar, svetoforlar) — GPU instancing (MultiMesh) bilan chiziladi.
## Joylashuv: shahar/bolak_X_Z.obyektlar.json  {tur: [[x, y, z, burilish, ...], ...]}
## Obyekt mahalliy o'qlari: +Z — devordan tashqariga (yoki oldinga), X — yon.
class_name Obyektlar
extends RefCounted

static var _meshlar: Dictionary = {}


static func _mat(rang: Color, g_b: float, metall := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = rang
	m.roughness = g_b
	m.metallic = metall
	return m


static func _quti(st: SurfaceTool, olcham: Vector3, markaz: Vector3) -> void:
	var b := BoxMesh.new()
	b.size = olcham
	st.append_from(b, 0, Transform3D(Basis(), markaz))


## Balkon: beton pol plitasi + to'siq. Oynavand turida yuqori qismi oyna.
static func _balkon(yopiq: bool) -> ArrayMesh:
	var mesh := ArrayMesh.new()
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	_quti(st, Vector3(2.5, 0.16, 1.1), Vector3(0, -0.08, 0.55))           # pol
	_quti(st, Vector3(2.5, 1.0, 0.06), Vector3(0, 0.5, 1.07))             # old to'siq
	_quti(st, Vector3(0.06, 1.0, 1.1), Vector3(-1.22, 0.5, 0.55))         # yonlar
	_quti(st, Vector3(0.06, 1.0, 1.1), Vector3(1.22, 0.5, 0.55))
	if yopiq:
		_quti(st, Vector3(2.5, 0.12, 1.1), Vector3(0, 2.44, 0.55))        # ayvoncha tomi
	st.set_material(_mat(Color(0.82, 0.8, 0.76), 0.85))
	st.commit(mesh)
	if yopiq:
		var og := SurfaceTool.new()
		og.begin(Mesh.PRIMITIVE_TRIANGLES)
		_quti(og, Vector3(2.44, 1.36, 0.03), Vector3(0, 1.7, 1.07))
		_quti(og, Vector3(0.03, 1.36, 1.06), Vector3(-1.22, 1.7, 0.55))
		_quti(og, Vector3(0.03, 1.36, 1.06), Vector3(1.22, 1.7, 0.55))
		var oyna := _mat(Color(0.12, 0.16, 0.18), 0.05, 0.4)
		oyna.metallic_specular = 1.0
		og.set_material(oyna)
		og.commit(mesh)
	return mesh


static func mesh(tur: String) -> Mesh:
	if _meshlar.has(tur):
		return _meshlar[tur]
	var m: Mesh = null
	match tur:
		"balkon":
			m = _balkon(false)
		"balkon_yopiq":
			m = _balkon(true)
	_meshlar[tur] = m
	return m


## Bo'lak tuguniga MultiMeshInstance3D'larni qo'shadi.
static func qosh(tugun: Node3D, malumot: Dictionary) -> void:
	for tur in malumot:
		var guruhlar := {}                     # mesh nomi -> [Transform3D]
		for r in malumot[tur]:
			var nom: String = tur
			if tur == "balkon" and r.size() > 4 and int(r[4]) == 1:
				nom = "balkon_yopiq"
			if not guruhlar.has(nom):
				guruhlar[nom] = []
			guruhlar[nom].append(Transform3D(Basis(Vector3.UP, float(r[3])), Vector3(r[0], r[1], r[2])))
		for nom in guruhlar:
			var m := mesh(nom)
			if m == null:
				continue
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.mesh = m
			var tr: Array = guruhlar[nom]
			mm.instance_count = tr.size()
			for i in tr.size():
				mm.set_instance_transform(i, tr[i])
			var mi := MultiMeshInstance3D.new()
			mi.name = nom
			mi.multimesh = mm
			tugun.add_child(mi)
