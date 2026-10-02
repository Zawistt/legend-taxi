extends SceneTree
## Builds the shared low-poly resource meshes + materials (run once, results are committed):
##   godot --headless --path godot --script res://scripts/tools/build_resource_assets.gd
## Everything is flat-shaded vertex-colour geometry: 1 material per family, no textures,
## 2 detail levels per mesh (LOD0 / LOD1). Trees are meant for MultiMesh.

const OUT_MESH := "res://resources/meshes/"
const OUT_MAT := "res://resources/materials/"

var _mats := {}
var _report: Array[String] = []


# ---------------------------------------------------------------- mesh soup builder
class MB:
	var v := PackedVector3Array()
	var n := PackedVector3Array()
	var c := PackedColorArray()

	## One flat-shaded triangle, wound so the outward side (away from `centre`) is the front face.
	func tri(a: Vector3, b: Vector3, d: Vector3, col: Color, centre: Vector3) -> void:
		var nn := (d - a).cross(b - a)
		if nn.length_squared() < 1e-10:
			return
		if nn.dot((a + b + d) / 3.0 - centre) < 0.0:
			var t := b
			b = d
			d = t
			nn = -nn
		nn = nn.normalized()
		v.append(a); v.append(b); v.append(d)
		n.append(nn); n.append(nn); n.append(nn)
		c.append(col); c.append(col); c.append(col)

	func tris() -> int:
		return v.size() / 3


func _hash3(p: Vector3) -> float:
	return fposmod(sin(p.dot(Vector3(12.9898, 78.233, 37.719)) * 43758.5453), 1.0)


# ---------------------------------------------------------------- primitives
func _ico(subdiv: int) -> Array:
	var t := (1.0 + sqrt(5.0)) / 2.0
	var verts: Array[Vector3] = []
	for p in [Vector3(-1, t, 0), Vector3(1, t, 0), Vector3(-1, -t, 0), Vector3(1, -t, 0), Vector3(0, -1, t), Vector3(0, 1, t),
			Vector3(0, -1, -t), Vector3(0, 1, -t), Vector3(t, 0, -1), Vector3(t, 0, 1), Vector3(-t, 0, -1), Vector3(-t, 0, 1)]:
		verts.append(p.normalized())
	var faces: Array = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
			[3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
	for _i in subdiv:
		var cache := {}
		var nf: Array = []
		for f in faces:
			var m: Array[int] = []
			for e in [[f[0], f[1]], [f[1], f[2]], [f[2], f[0]]]:
				var key := Vector2i(mini(e[0], e[1]), maxi(e[0], e[1]))
				if not cache.has(key):
					verts.append(((verts[e[0]] + verts[e[1]]) * 0.5).normalized())
					cache[key] = verts.size() - 1
				m.append(cache[key])
			nf.append([f[0], m[0], m[2]]); nf.append([f[1], m[1], m[0]]); nf.append([f[2], m[2], m[1]]); nf.append([m[0], m[1], m[2]])
		faces = nf
	return [verts, faces]


## Lumpy boulder. `flat_bottom` squashes everything below y=0 so it sits on the ground.
func _rock(mb: MB, centre: Vector3, radii: Vector3, seed_: float, subdiv: int, c_low: Color, c_high: Color,
		flat_bottom := true, lump := 0.28, strata := 0.0) -> void:
	var ico := _ico(subdiv)
	var verts: Array = ico[0]
	var pos: Array[Vector3] = []
	for u in verts:
		var h := _hash3(u * 3.7 + Vector3(seed_, seed_ * 1.3, seed_ * 0.7))
		var p: Vector3 = u * (1.0 - lump * 0.5 + lump * h) * radii
		if flat_bottom and p.y < 0.0:
			p.y *= 0.28
		pos.append(centre + p)
	for f in ico[1]:
		var a := pos[f[0]]; var b := pos[f[1]]; var d := pos[f[2]]
		var cy := ((a.y + b.y + d.y) / 3.0 - centre.y) / maxf(radii.y, 0.01)
		var col := c_low.lerp(c_high, clampf(cy * 0.5 + 0.5, 0.0, 1.0))
		col = col.darkened(0.12 * _hash3(a * 5.1))
		if strata > 0.0:
			col = col.lerp(col.darkened(0.25), 0.5 + 0.5 * sin((a.y + b.y + d.y) * strata))
		mb.tri(a, b, d, col, centre)


## Slightly irregular block (stepped quarry faces).
func _block(mb: MB, base: Vector3, size: Vector3, seed_: float, c_low: Color, c_high: Color, strata := 3.0) -> void:
	var corners: Array[Vector3] = []
	for iy in 2:
		for ix in 2:
			for iz in 2:
				var p := Vector3((ix - 0.5) * size.x, iy * size.y, (iz - 0.5) * size.z)
				var j := (Vector3(_hash3(p + Vector3(seed_, 1, 2)), _hash3(p + Vector3(3, seed_, 4)), _hash3(p + Vector3(5, 6, seed_))) - Vector3.ONE * 0.5)
				p += j * Vector3(size.x * 0.16, size.y * 0.1 if iy == 1 else 0.0, size.z * 0.16)
				corners.append(base + p)
	var centre := base + Vector3(0, size.y * 0.5, 0)
	# corner index = iy*4 + ix*2 + iz
	var quads := [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
	for q in quads:
		var a := corners[q[0]]; var b := corners[q[1]]; var c := corners[q[2]]; var d := corners[q[3]]
		var cy := ((a.y + b.y + c.y + d.y) * 0.25 - base.y) / maxf(size.y, 0.01)
		var col := c_low.lerp(c_high, cy)
		col = col.lerp(col.darkened(0.22), 0.5 + 0.5 * sin((a.y + c.y) * strata))
		mb.tri(a, b, c, col, centre)
		mb.tri(a, c, d, col.darkened(0.04), centre)


func _basis_from(axis: Vector3) -> Basis:
	var y := axis.normalized()
	var x := y.cross(Vector3.FORWARD if absf(y.dot(Vector3.FORWARD)) < 0.9 else Vector3.RIGHT).normalized()
	return Basis(x, y, x.cross(y))


## Frustum / pointed prism along `axis`. r1 = 0 gives a cone, tip_extra adds a pointed cap above the top ring.
func _frustum(mb: MB, base: Vector3, axis: Vector3, r0: float, r1: float, h: float, sides: int, c0: Color, c1: Color,
		tip := 0.0, c_tip := Color(0, 0, 0, 0), jitter := 0.0, seed_ := 0.0) -> void:
	var bs := _basis_from(axis)
	var top := base + bs.y * h
	var centre := base + bs.y * h * 0.5
	var ring0: Array[Vector3] = []
	var ring1: Array[Vector3] = []
	for i in sides:
		var a := TAU * i / sides
		var dir := bs.x * cos(a) + bs.z * sin(a)
		var jr := 1.0 + jitter * (_hash3(dir * 7.0 + Vector3(seed_, i, 0)) - 0.5)
		ring0.append(base + dir * r0 * jr)
		ring1.append(top + dir * r1 * jr)
	for i in sides:
		var j := (i + 1) % sides
		var col := c0.lerp(c1, 0.5).darkened(0.08 * float(i % 2))
		if r1 > 0.001:
			mb.tri(ring0[i], ring0[j], ring1[j], col, centre)
			mb.tri(ring0[i], ring1[j], ring1[i], col, centre)
		else:
			mb.tri(ring0[i], ring0[j], top, col, centre)
		if tip > 0.0:
			var col_t := c_tip if c_tip.a > 0.0 else c1
			mb.tri(ring1[i], ring1[j], top + bs.y * tip, col_t.darkened(0.06 * float(i % 2)), centre)


# ---------------------------------------------------------------- materials / saving
func _mat(name: String, setup: Callable) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	setup.call(m)
	var path := OUT_MAT + name + ".tres"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_MAT))
	ResourceSaver.save(m, path)
	_mats[name] = load(path)
	return _mats[name]


func _make_materials() -> void:
	_mat("rock_vc", func(m):
		m.vertex_color_use_as_albedo = true
		m.roughness = 0.95)
	_mat("tree_vc", func(m):
		m.vertex_color_use_as_albedo = true
		m.roughness = 0.9)
	_mat("gold_ore", func(m):
		m.albedo_color = Color(1.0, 0.76, 0.18)
		m.vertex_color_use_as_albedo = true
		m.metallic = 0.55
		m.roughness = 0.32
		m.emission_enabled = true
		m.emission = Color(1.0, 0.66, 0.12)
		m.emission_energy_multiplier = 0.9)
	_mat("crystal_glow", func(m):
		m.albedo_color = Color(1, 1, 1)
		m.vertex_color_use_as_albedo = true
		m.roughness = 0.12
		m.metallic = 0.1
		m.emission_enabled = true
		m.emission = Color(0.42, 0.18, 1.0)
		m.emission_energy_multiplier = 0.85)


func _save(name: String, parts: Array) -> void:
	## parts: [[MB, material_name], ...] -> one surface each
	var mesh := ArrayMesh.new()
	var tris := 0
	for p in parts:
		var mb: MB = p[0]
		if mb.v.is_empty():
			continue
		var arr := []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = mb.v
		arr[Mesh.ARRAY_NORMAL] = mb.n
		arr[Mesh.ARRAY_COLOR] = mb.c
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
		mesh.surface_set_material(mesh.get_surface_count() - 1, _mats[p[1]])
		tris += mb.tris()
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_MESH))
	ResourceSaver.save(mesh, OUT_MESH + name + ".res")
	_report.append("%-24s %4d tris  size %s" % [name, tris, str(mesh.get_aabb().size.snapped(Vector3(0.1, 0.1, 0.1)))])


# ---------------------------------------------------------------- GOLD
func _gold(variant: int, lod: bool) -> void:
	var rock := MB.new()
	var ore := MB.new()
	var sd := 3.0 + variant * 11.0
	var sub := 0 if lod else 1
	var low := Color(0.20, 0.17, 0.15)
	var high := Color(0.40, 0.34, 0.28)
	var bodies: Array = [[Vector3(0, 0.2, 0), Vector3(3.5, 3.1, 3.3)]]
	if variant == 0:
		bodies += [[Vector3(-3.1, 0, 1.0), Vector3(1.8, 1.7, 1.7)], [Vector3(2.6, 0, -2.0), Vector3(2.0, 1.9, 1.9)], [Vector3(1.0, 0, 3.0), Vector3(1.3, 1.1, 1.3)]]
	else:
		bodies += [[Vector3(2.9, 0, 1.6), Vector3(2.0, 2.2, 1.8)], [Vector3(-2.6, 0, -1.8), Vector3(1.7, 1.5, 1.7)], [Vector3(-0.6, 0, 3.2), Vector3(1.2, 1.0, 1.2)]]
	for b in bodies:
		_rock(rock, b[0], b[1], sd + b[0].x, sub, low, high, true, 0.3)
	var nug := 5 if lod else (16 if variant == 0 else 14)
	for k in nug:
		var body: Array = bodies[k % bodies.size()]
		var d := Vector3(_hash3(Vector3(k, sd, 1)) - 0.5, 0.15 + _hash3(Vector3(k, sd, 2)) * 0.85, _hash3(Vector3(k, sd, 3)) - 0.5).normalized()
		var pos: Vector3 = body[0] + d * body[1] * 0.93
		var s := (0.6 + 0.65 * _hash3(Vector3(k, sd, 4))) * (1.0 + 0.45 * (1.0 if k % bodies.size() == 0 else 0.0))
		_frustum(ore, pos - d * 0.25, d, s * 0.62, s * 0.42, s * 1.5, 4, Color(1.0, 0.72, 0.15), Color(1.0, 0.88, 0.35), s * 0.7,
				Color(1.0, 0.95, 0.55), 0.3, k)
	_save("gold_deposit_%s%s" % ["a" if variant == 0 else "b", "_lod" if lod else ""], [[rock, "rock_vc"], [ore, "gold_ore"]])


# ---------------------------------------------------------------- STONE
func _stone(variant: int, lod: bool) -> void:
	var rock := MB.new()
	var sd := 7.0 + variant * 5.0
	var grey := Color(0.46, 0.45, 0.44)
	var tan := Color(0.64, 0.58, 0.48)
	var m := 1.0 if variant == 0 else -1.0
	var sub := 0 if lod else 1
	# angular rock wall at the back (sub 0 keeps the faces large and cut-looking), terraces in front
	for b in [[Vector3(-3.0 * m, 0, -2.6), Vector3(3.4, 3.8, 2.6), 0], [Vector3(0.6 * m, 0, -3.0), Vector3(3.8, 4.5, 2.8), 0], [Vector3(3.6 * m, 0, -2.2), Vector3(2.8, 3.0, 2.4), 0],
			[Vector3(-1.6 * m, 0, 0.0), Vector3(3.2, 2.4, 2.6), sub], [Vector3(2.0 * m, 0, 0.6), Vector3(3.0, 2.0, 2.4), sub],
			[Vector3(-3.8 * m, 0, 1.2), Vector3(1.9, 1.5, 1.8), sub], [Vector3(4.2 * m, 0, 2.6), Vector3(1.6, 1.2, 1.6), sub]]:
		_rock(rock, b[0], b[1], sd + b[0].x * 1.7, b[2], grey.darkened(0.05), tan, true, 0.46, 2.2)
	if not lod:
		for k in 8:
			var a := TAU * k / 8.0 + sd
			_rock(rock, Vector3(cos(a) * 5.0, 0, sin(a) * 4.6 + 0.8), Vector3.ONE * (0.4 + 0.5 * _hash3(Vector3(k, sd, 9))), sd + k, 0, grey, tan, true, 0.45)
	_save("stone_quarry_%s%s" % ["a" if variant == 0 else "b", "_lod" if lod else ""], [[rock, "rock_vc"]])


# ---------------------------------------------------------------- CRYSTAL
func _crystal(variant: int, lod: bool) -> void:
	var rock := MB.new()
	var cr := MB.new()
	var sd := 11.0 + variant * 9.0
	_rock(rock, Vector3(0, 0, 0), Vector3(2.7, 1.0, 2.7), sd, 0 if lod else 1, Color(0.18, 0.15, 0.24), Color(0.32, 0.27, 0.40), true, 0.3)
	var n := 4 if lod else (9 if variant == 0 else 8)
	var sides := 4 if lod else 6
	for k in n:
		var main := k == 0
		var a := TAU * k / maxf(n - 1, 1) + sd
		var tilt := 0.0 if main else 0.28 + 0.34 * _hash3(Vector3(k, sd, 1))
		var axis := Vector3(sin(tilt) * cos(a), cos(tilt), sin(tilt) * sin(a))
		var h := 6.4 if main else 2.4 + 2.8 * _hash3(Vector3(k, sd, 2))
		var r := 0.95 if main else 0.42 + 0.3 * _hash3(Vector3(k, sd, 3))
		var base := Vector3(0, 0.1, 0) if main else Vector3(cos(a), 0.05, sin(a)) * (0.9 + 0.9 * _hash3(Vector3(k, sd, 4)))
		var hue := _hash3(Vector3(k, sd, 5))
		var c0 := Color(0.22, 0.08, 0.55).lerp(Color(0.10, 0.20, 0.62), hue)
		var c1 := Color(0.50, 0.26, 0.95).lerp(Color(0.26, 0.62, 0.98), hue)
		_frustum(cr, base, axis, r, r * 0.78, h * 0.72, sides, c0, c1, h * 0.28, c1.lightened(0.12), 0.12, k)
	_save("crystal_cluster_%s%s" % ["a" if variant == 0 else "b", "_lod" if lod else ""], [[rock, "rock_vc"], [cr, "crystal_glow"]])


# ---------------------------------------------------------------- TREES
func _pine(lod: bool) -> void:
	var mb := MB.new()
	var bark := Color(0.30, 0.20, 0.12)
	if not lod:
		_frustum(mb, Vector3.ZERO, Vector3.UP, 0.32, 0.24, 1.7, 6, bark, bark.lightened(0.1))
	var g0 := Color(0.07, 0.24, 0.12)
	var g1 := Color(0.14, 0.38, 0.17)
	_frustum(mb, Vector3(0, 1.2, 0), Vector3.UP, 1.75, 0.0, 2.8, 5 if lod else 7, g0, g1, 0, Color(0, 0, 0, 0), 0.15, 1)
	_frustum(mb, Vector3(0, 2.7, 0), Vector3.UP, 1.4, 0.0, 2.6, 5 if lod else 7, g0.lightened(0.04), g1, 0, Color(0, 0, 0, 0), 0.15, 2)
	if not lod:
		_frustum(mb, Vector3(0, 4.1, 0), Vector3.UP, 1.0, 0.0, 2.4, 7, g0.lightened(0.08), g1.lightened(0.08), 0, Color(0, 0, 0, 0), 0.15, 3)
	_save("tree_pine" + ("_lod" if lod else ""), [[mb, "tree_vc"]])


func _oak(lod: bool) -> void:
	var mb := MB.new()
	var bark := Color(0.34, 0.23, 0.14)
	_frustum(mb, Vector3.ZERO, Vector3.UP, 0.42, 0.3, 2.6, 4 if lod else 6, bark, bark.lightened(0.08))
	var lo := Color(0.16, 0.34, 0.10)
	var hi := Color(0.34, 0.52, 0.16)
	_rock(mb, Vector3(0, 4.0, 0), Vector3(2.0, 1.6, 2.0), 4.0, 0 if lod else 1, lo, hi, false, 0.3)
	if not lod:
		_rock(mb, Vector3(1.2, 3.3, 0.5), Vector3(1.2, 1.1, 1.2), 5.0, 0, lo, hi, false, 0.3)
		_rock(mb, Vector3(-1.1, 3.5, -0.7), Vector3(1.1, 1.0, 1.1), 6.0, 0, lo, hi, false, 0.3)
	_save("tree_oak" + ("_lod" if lod else ""), [[mb, "tree_vc"]])


func _birch(lod: bool) -> void:
	var mb := MB.new()
	var bark := Color(0.86, 0.84, 0.78)
	_frustum(mb, Vector3.ZERO, Vector3.UP, 0.22, 0.14, 4.2, 4 if lod else 6, bark, bark.darkened(0.12))
	var lo := Color(0.30, 0.46, 0.12)
	var hi := Color(0.55, 0.70, 0.22)
	_rock(mb, Vector3(0, 4.9, 0), Vector3(1.35, 2.2, 1.35), 8.0, 0, lo, hi, false, 0.3)
	if not lod:
		_rock(mb, Vector3(0.45, 3.4, 0.2), Vector3(1.0, 1.4, 1.0), 9.0, 0, lo, hi, false, 0.3)
	_save("tree_birch" + ("_lod" if lod else ""), [[mb, "tree_vc"]])


func _init() -> void:
	_make_materials()
	for lod in [false, true]:
		for v in 2:
			_gold(v, lod)
			_stone(v, lod)
			_crystal(v, lod)
		_pine(lod)
		_oak(lod)
		_birch(lod)
	for r in _report:
		print(r)
	quit()
