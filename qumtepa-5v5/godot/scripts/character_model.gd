extends Node3D
## Personaj modeli — VAQTINCHALIK O'RINBOSAR (low-poly manekin).
## Avvalgi qahramonlar (T, CT), ularning animatsiyalari va qurol modellari (AKM, M416) o'chirildi —
## foydalanuvchi yangilarini beradi. Shu vaqtgacha o'yin to'liq ishlashi uchun oddiy low-poly manekin kod bilan yig'iladi:
##   tana, bosh, oyoqlar, qo'llar va qurol — faqat qutilardan (tekis soya, xarita uslubiga mos), jamoa rangida.
## Skelet: hips -> spine1 -> chest -> neck -> head. Qo'llar va qurol ko'krakka bog'langan (nishonga qarab egiladi).
## Harakat oddiy protsedura: yurganda oyoqlar qadam tashlaydi, o'tirish, o'q uzganda tepki, qayta o'qlash, o'lim.
## Model +Z ga qarab turadi (Godot'da ota tugun "oldinga"sini shunga moslab buradi), +X — chap.
## first_person=true — faqat qo'llar va qurol (o'yinchi kamerasi uchun), ko'z nuqtasi kameraga bog'lanadi.
## own_body=true — o'yinchining o'z 3-shaxs tanasi: boshqa hamma kameralarga ko'rinadi, o'yinchining o'z kamerasiga
##   ko'rinmaydi (render qatlami 11, kamera uni chiqarib tashlaydi), lekin soyasi yerda ko'rinadi.
## Render qatlamlari: 1 — dunyo, 11 — o'yinchining o'z tanasi, 12 — birinchi shaxs qo'llari/quroli.

const LAYER_WORLD := 1
const LAYER_OWN_BODY := 1 << 10     ## 11-qatlam
const LAYER_VIEWMODEL := 1 << 11    ## 12-qatlam
const RUN_SPEED := 4.5
const WALK_SPEED := 2.3
const CROUCH_SPEED := 1.55
const PLACEHOLDER := true
const EYE := Vector3(0, 1.67, 0.09)
const HIPS_Y := 0.95
const RELOAD_TIME := 2.6
## o'q tegadigan zonalar (Area3D, 10-qatlam): bosh, tana, qo'llar, oyoqlar — qurol ma'lumotidagi ko'paytuvchilar uchun
const LAYER_HITBOX := 1 << 9
const WEAPON_RIFLE := 0
const WEAPON_PISTOL := 1
const WEAPON_KNIFE := 2
const WEAPON_SMG := 3
const WEAPON_SNIPER := 4
const WEAPON_SHOTGUN := 5
const WEAPON_MG := 6
const WEAPON_GRENADE := 7
const WEAPON_ZEUS := 8
const WEAPON_C4 := 9

## jamoa ranglari: ko'ylak, jilet, shim, bosh kiyim, qurol yog'ochi
const COLORS := {
	"T": {"shirt": Color(0.66, 0.54, 0.36), "vest": Color(0.4, 0.34, 0.22), "pants": Color(0.44, 0.39, 0.3),
		"hat": Color(0.76, 0.64, 0.46), "boots": Color(0.24, 0.19, 0.14), "wood": Color(0.52, 0.3, 0.16)},
	"CT": {"shirt": Color(0.2, 0.3, 0.46), "vest": Color(0.15, 0.2, 0.28), "pants": Color(0.22, 0.27, 0.34),
		"hat": Color(0.14, 0.16, 0.19), "boots": Color(0.12, 0.12, 0.13), "wood": Color(0.16, 0.16, 0.17)},
}
const SKIN := Color(0.86, 0.66, 0.5)
const METAL := Color(0.14, 0.14, 0.15)

@export var team := "T"
@export var first_person := false
@export var own_body := false
## nishonga qarash (radian, + tepaga): umurtqa (40%) va ko'krak (60%) egiladi — qo'llar va qurol birga egiladi
var aim_pitch := 0.0

var model: Node3D
var skel: Skeleton3D
var anim: AnimationPlayer           ## o'rinbosarda animatsiyalar yo'q (bo'sh pleyer — API uchun)
var tree: AnimationTree = null
var dead := false
var fire_count := 0
var reload_count := 0

## boshqaruvchi (o'yinchi yoki bot) har kadr to'ldiradi
var velocity_local := Vector3.ZERO   ## model fazosida: +Z oldinga, +X chapga
var crouching := false
var on_floor := true
var planting := false

var _legs: Array = []
var _gun: Node3D
var _chest: Node3D
var _hand_nodes: Array = []
var weapon_kind := WEAPON_RIFLE
var weapon_id := ""                 ## aniq qurol (shakl farqlari: AK/M4, Deagle, AWP, P90)
var hitboxes: Array = []
var _crouch_amt := 0.0
var _step := 0.0
var _kick := 0.0
var _reload_left := 0.0
var _die_t := 0.0
var _jump_t := 0.0
var _mats := {}


func _ready() -> void:
	load_model(team)


func load_model(t: String) -> void:
	team = t
	if model:
		model.queue_free()
		model = null
	_mats = {}
	_legs = []
	_hand_nodes = []
	model = Node3D.new()
	model.name = "Placeholder"
	add_child(model)
	anim = AnimationPlayer.new()
	model.add_child(anim)
	skel = Skeleton3D.new()
	skel.name = "Skeleton3D"
	model.add_child(skel)
	for b in [["hips", -1, Vector3(0, HIPS_Y, 0)], ["spine1", 0, Vector3(0, 0.15, 0)], ["chest", 1, Vector3(0, 0.2, 0)],
			["neck", 2, Vector3(0, 0.25, 0)], ["head", 3, Vector3(0, 0.08, 0)]]:
		var i := skel.add_bone(b[0])
		if b[1] >= 0:
			skel.set_bone_parent(i, b[1])
		skel.set_bone_rest(i, Transform3D(Basis(), b[2]))
		skel.set_bone_pose_position(i, b[2])
	var c: Dictionary = COLORS.get(team, COLORS["T"])
	var chest := _attach("chest")
	if not first_person:
		var hips := _attach("hips")
		_box(hips, Vector3(0.34, 0.2, 0.22), Vector3(0, 0.02, 0), c.pants)
		var sp := _attach("spine1")
		_box(sp, Vector3(0.36, 0.22, 0.22), Vector3(0, 0.1, 0), c.shirt)
		_box(chest, Vector3(0.44, 0.34, 0.26), Vector3(0, 0.12, 0), c.shirt)
		_box(chest, Vector3(0.4, 0.36, 0.32), Vector3(0, 0.06, 0.0), c.vest)          # jilet
		var head := _attach("head")
		_box(head, Vector3(0.1, 0.08, 0.1), Vector3(0, -0.04, 0), SKIN)                # bo'yin
		_box(head, Vector3(0.2, 0.24, 0.22), Vector3(0, 0.1, 0.01), SKIN)
		if team == "CT":
			_box(head, Vector3(0.25, 0.12, 0.27), Vector3(0, 0.22, -0.005), c.hat)     # dubulg'a
			_box(head, Vector3(0.18, 0.05, 0.02), Vector3(0, 0.13, 0.12), Color(0.08, 0.08, 0.09))   # ko'zoynak
		else:
			_box(head, Vector3(0.23, 0.12, 0.24), Vector3(0, 0.2, -0.01), c.hat)       # bosh o'rami
			_box(head, Vector3(0.21, 0.09, 0.05), Vector3(0, 0.06, 0.115), c.hat)      # yuz niqobi
		for side in [1, -1]:
			var leg := Node3D.new()
			leg.position = Vector3(0.1 * side, HIPS_Y - 0.05, 0)
			model.add_child(leg)
			_box(leg, Vector3(0.15, 0.46, 0.16), Vector3(0, -0.23, 0), c.pants)
			_box(leg, Vector3(0.13, 0.42, 0.14), Vector3(0, -0.66, 0), c.pants)
			_box(leg, Vector3(0.13, 0.12, 0.26), Vector3(0, -0.84, 0.04), c.boots)
			_legs.append(leg)
	_chest = chest
	_build_arms_gun(chest, c)
	_merge_all()
	hitboxes = []
	if not first_person and not own_body:
		_build_hitboxes()
	_apply_layers()
	dead = false
	_die_t = 0.0
	model.rotation = Vector3.ZERO
	model.position = Vector3.ZERO


func _apply_layers() -> void:
	for m in _all(model, "MeshInstance3D"):
		var mi := m as MeshInstance3D
		if first_person:
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			mi.layers = LAYER_VIEWMODEL
		elif own_body:
			mi.layers = LAYER_OWN_BODY
		else:
			mi.layers = LAYER_WORLD


## o'q tegadigan zonalar: har biri suyakka bog'langan Area3D (o'tirish, egilish, o'limda birga harakatlanadi)
func _build_hitboxes() -> void:
	for z in [["head", "head", Vector3(0.26, 0.3, 0.27), Vector3(0, 0.12, 0)],
			["body", "chest", Vector3(0.44, 0.42, 0.32), Vector3(0, 0.08, 0)],
			["body", "spine1", Vector3(0.38, 0.24, 0.26), Vector3(0, 0.1, 0)],
			["body", "hips", Vector3(0.36, 0.22, 0.26), Vector3(0, 0.02, 0)],
			["arm", "chest", Vector3(0.12, 0.3, 0.3), Vector3(-0.27, 0.0, 0.08)],
			["arm", "chest", Vector3(0.12, 0.3, 0.3), Vector3(0.2, -0.02, 0.14)]]:
		_hitbox(_attach(z[1]), z[0], z[2], z[3])
	for leg in _legs:
		_hitbox(leg, "leg", Vector3(0.18, 0.92, 0.2), Vector3(0, -0.44, 0.02))


func _hitbox(parent: Node3D, zone: String, size: Vector3, pos: Vector3) -> void:
	var a := Area3D.new()
	a.collision_layer = LAYER_HITBOX
	a.collision_mask = 0
	a.monitoring = false
	a.set_meta("zone", zone)
	a.set_meta("owner_model", self)
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	cs.shape = bs
	a.add_child(cs)
	a.position = pos
	parent.add_child(a)
	hitboxes.append(a)


## o'q tekkan zonani egasiga yetkazadi: ota tugunlardan take_hit() bor birinchisi (bot, mashq nishoni, o'yinchi)
func receiver() -> Node:
	var n: Node = self
	while n:
		if n.has_method("take_hit"):
			return n
		n = n.get_parent()
	return null


## qo'ldagi qurolni almashtirish (1-shaxs va 3-shaxsda bir xil shakl)
func set_weapon(kind: int, wid := "") -> void:
	if kind == weapon_kind and wid == weapon_id and _gun:
		return
	weapon_kind = kind
	weapon_id = wid
	if model:
		var was_dead := dead
		load_model(team)                 # qutilar birlashtirilgan — qo'l va qurol butunlay qayta yig'iladi (arzon)
		if was_dead:
			die()


## optimizatsiya: har bir bo'g'indagi qutilar bitta mesh'ga (vertex rang bilan) birlashtiriladi —
## personaj ~27 ta chizish o'rniga ~7 ta (10 personajda ~200 kam draw call)
func _merge_all() -> void:
	var parents := {}
	for m in _all(model, "MeshInstance3D"):
		if (m as MeshInstance3D).mesh is BoxMesh:
			parents[m.get_parent()] = true
	for p in parents:
		_merge(p)


func _merge(parent: Node3D) -> void:
	var boxes := parent.get_children().filter(func(ch): return ch is MeshInstance3D and ch.mesh is BoxMesh)
	if boxes.size() < 2:
		return
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for mi in boxes:
		var arr: Array = (mi.mesh as BoxMesh).get_mesh_arrays()
		var xf: Transform3D = mi.transform
		var col: Color = (mi.material_override as StandardMaterial3D).albedo_color
		var verts: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
		var nrm: PackedVector3Array = arr[Mesh.ARRAY_NORMAL]
		var idx: PackedInt32Array = arr[Mesh.ARRAY_INDEX]
		for i in idx:
			st.set_color(col)
			st.set_normal((xf.basis * nrm[i]).normalized())
			st.add_vertex(xf * verts[i])
		parent.remove_child(mi)
		mi.queue_free()
	var out := MeshInstance3D.new()
	out.name = "Merged"
	out.mesh = st.commit()
	out.material_override = _vc_material()
	parent.add_child(out)


func _vc_material() -> StandardMaterial3D:
	if not _mats.has("vc"):
		var m := StandardMaterial3D.new()
		m.vertex_color_use_as_albedo = true
		m.roughness = 0.9
		_mats["vc"] = m
	return _mats["vc"]


## qo'llar va qurol (3-shaxsda ham, 1-shaxsda ham bir xil joyda): ko'krak suyagi fazosida
func _build_arms_gun(chest: Node3D, c: Dictionary) -> void:
	var o := Vector3(0, HIPS_Y + 0.35, 0)            # ko'krak suyagining model fazosidagi joyi (tinch holat)
	var shape: Dictionary = make_weapon_shape(weapon_kind, team, weapon_id)
	_gun = shape.node
	_gun.name = "Weapon"
	chest.add_child(_gun)
	_gun.position = shape.at - o
	var grip: Vector3 = _gun.position + shape.grip
	var fore: Vector3 = _gun.position + shape.fore if shape.two_hands else Vector3(0.22, 1.1, 0.12) - o
	# qo'llar: yelka -> tirsak -> musht (ko'krak fazosida)
	for arm in [[Vector3(-0.22, 1.42, 0) - o, Vector3(-0.3, 1.2, 0.02) - o, grip], [Vector3(0.22, 1.42, 0) - o, Vector3(0.1, 1.22, 0.28) - o, fore]]:
		if not first_person:
			_hand_nodes.append(_limb(chest, arm[0], arm[1], 0.1, c.shirt))
		_hand_nodes.append(_limb(chest, arm[1], arm[2], 0.085, c.shirt if not first_person else c.vest))
		_hand_nodes.append(_box(chest, Vector3(0.08, 0.09, 0.09), arm[2], Color(0.18, 0.16, 0.14)))   # qo'lqop


## qurol shakli (qutilardan): 1-/3-shaxs va sotib olish menyusidagi rasm uchun bir xil.
## Natija: node (qurol, og'zi +Z), at — model fazosidagi joyi, grip/fore — mushtlar (qurolga nisbatan).
static func make_weapon_shape(kind: int, team: String, wid := "") -> Dictionary:
	var g := Node3D.new()
	var c: Dictionary = COLORS.get(team, COLORS["T"])
	var wood: Color = c.wood
	var dark := Color(0.14, 0.14, 0.15)
	var olive := Color(0.33, 0.37, 0.24)
	var at := Vector3(-0.13, 1.37, 0.12)
	var grip := Vector3(0, -0.07, 0.16)
	var fore := Vector3(0, -0.04, 0.5)
	var muzzle := 0.82
	var two := true
	match kind:
		WEAPON_PISTOL:
			var big := wid == "deagle"
			at = Vector3(-0.05, 1.36, 0.42)
			_sbox(g, Vector3(0.035, 0.055 if big else 0.05, 0.26 if big else 0.2), Vector3(0, 0.02, 0.05), dark)
			_sbox(g, Vector3(0.032, 0.11, 0.05), Vector3(0, -0.05, -0.02), wood if wid == "glock" else dark).rotation.x = -0.25
			grip = Vector3(0, -0.06, -0.03)
			fore = Vector3(0.04, -0.07, -0.02)
			muzzle = 0.2 if big else 0.16
		WEAPON_KNIFE:
			at = Vector3(-0.2, 1.2, 0.34)
			_sbox(g, Vector3(0.03, 0.03, 0.11), Vector3(0, 0, -0.02), wood)
			_sbox(g, Vector3(0.008, 0.035, 0.17), Vector3(0, 0.005, 0.12), Color(0.72, 0.74, 0.76))
			grip = Vector3(0, 0, -0.03)
			two = false
			muzzle = 0.2
		WEAPON_ZEUS:
			at = Vector3(-0.08, 1.33, 0.4)
			_sbox(g, Vector3(0.04, 0.06, 0.18), Vector3(0, 0.02, 0.05), Color(0.95, 0.8, 0.1))
			_sbox(g, Vector3(0.035, 0.1, 0.05), Vector3(0, -0.05, -0.02), dark).rotation.x = -0.25
			_sbox(g, Vector3(0.03, 0.02, 0.02), Vector3(0, 0.03, 0.15), Color(0.2, 0.6, 1.0))
			grip = Vector3(0, -0.06, -0.03)
			two = false
			muzzle = 0.16
		WEAPON_GRENADE:
			at = Vector3(-0.14, 1.3, 0.36)
			_sbox(g, Vector3(0.07, 0.11, 0.07), Vector3.ZERO, olive)
			_sbox(g, Vector3(0.03, 0.03, 0.03), Vector3(0, 0.07, 0), dark)
			grip = Vector3(0, -0.02, -0.03)
			two = false
			muzzle = 0.05
		WEAPON_C4:
			at = Vector3(-0.08, 1.25, 0.36)
			_sbox(g, Vector3(0.2, 0.07, 0.14), Vector3.ZERO, Color(0.36, 0.32, 0.22))
			_sbox(g, Vector3(0.08, 0.02, 0.06), Vector3(0.02, 0.045, 0.0), Color(0.1, 0.1, 0.1))
			_sbox(g, Vector3(0.03, 0.01, 0.02), Vector3(0.02, 0.058, 0.0), Color(1, 0.15, 0.1))
			grip = Vector3(-0.08, -0.03, 0)
			fore = Vector3(0.09, -0.03, 0)
			muzzle = 0.1
		WEAPON_SMG:
			at = Vector3(-0.13, 1.37, 0.16)
			var p90 := wid == "p90"
			_sbox(g, Vector3(0.06, 0.09, 0.42 if p90 else 0.32), Vector3(0, 0, 0.2), dark)
			_sbox(g, Vector3(0.03, 0.03, 0.12), Vector3(0, 0.01, 0.46 if p90 else 0.42), dark)
			if p90:
				_sbox(g, Vector3(0.05, 0.03, 0.3), Vector3(0, 0.06, 0.22), Color(0.2, 0.2, 0.22))
			else:
				_sbox(g, Vector3(0.035, 0.18, 0.045), Vector3(0, -0.13, 0.26), dark)
				_sbox(g, Vector3(0.02, 0.05, 0.18), Vector3(0, -0.01, -0.05), dark)
			_sbox(g, Vector3(0.04, 0.1, 0.05), Vector3(0, -0.08, 0.1), dark).rotation.x = -0.3
			grip = Vector3(0, -0.07, 0.11)
			fore = Vector3(0, -0.12, 0.26)
			muzzle = 0.52 if p90 else 0.48
		WEAPON_SNIPER:
			at = Vector3(-0.13, 1.37, 0.1)
			var body_col: Color = olive if wid == "awp" else (wood if wid == "longbow_50" else dark)
			_sbox(g, Vector3(0.06, 0.09, 0.5), Vector3(0, 0, 0.26), body_col)
			_sbox(g, Vector3(0.035, 0.035, 0.6), Vector3(0, 0.02, 0.8), dark)
			_sbox(g, Vector3(0.055, 0.055, 0.3), Vector3(0, 0.1, 0.3), dark)
			_sbox(g, Vector3(0.055, 0.12, 0.26), Vector3(0, -0.03, -0.1), body_col)
			_sbox(g, Vector3(0.04, 0.06, 0.04), Vector3(0.05, 0.03, 0.2), dark)
			grip = Vector3(0, -0.07, 0.14)
			fore = Vector3(0, -0.05, 0.46)
			muzzle = 1.1
		WEAPON_SHOTGUN:
			_sbox(g, Vector3(0.065, 0.1, 0.36), Vector3(0, 0, 0.22), dark)
			_sbox(g, Vector3(0.045, 0.045, 0.42), Vector3(0, 0.025, 0.6), dark)
			_sbox(g, Vector3(0.05, 0.05, 0.3), Vector3(0, -0.035, 0.55), dark)
			_sbox(g, Vector3(0.07, 0.07, 0.14), Vector3(0, -0.035, 0.52), wood)
			_sbox(g, Vector3(0.055, 0.11, 0.26), Vector3(0, -0.03, -0.08), wood)
			grip = Vector3(0, -0.07, 0.14)
			fore = Vector3(0, -0.05, 0.52)
			muzzle = 0.81
		WEAPON_MG:
			_sbox(g, Vector3(0.08, 0.11, 0.5), Vector3(0, 0, 0.26), dark)
			_sbox(g, Vector3(0.04, 0.04, 0.4), Vector3(0, 0.02, 0.7), dark)
			_sbox(g, Vector3(0.1, 0.12, 0.12), Vector3(0.02, -0.12, 0.28), olive)
			_sbox(g, Vector3(0.05, 0.1, 0.24), Vector3(0, -0.02, -0.08), dark)
			_sbox(g, Vector3(0.012, 0.16, 0.012), Vector3(0.03, -0.08, 0.72), dark).rotation.x = 0.4
			_sbox(g, Vector3(0.012, 0.16, 0.012), Vector3(-0.03, -0.08, 0.72), dark).rotation.x = 0.4
			grip = Vector3(0, -0.08, 0.16)
			fore = Vector3(0, -0.05, 0.5)
			muzzle = 0.9
		_:
			var t_rifle := wid in ["ak47", "galil"] or (wid == "" and team == "T") or wid == "lar_01"
			_sbox(g, Vector3(0.06, 0.09, 0.44), Vector3(0, 0, 0.28), dark)
			_sbox(g, Vector3(0.03, 0.03, 0.34 if t_rifle else 0.3), Vector3(0, 0.02, 0.66), dark)
			_sbox(g, Vector3(0.065, 0.075, 0.22), Vector3(0, -0.005, 0.5), wood if t_rifle else dark)
			_sbox(g, Vector3(0.05, 0.1, 0.24), Vector3(0, -0.02, -0.08), wood if t_rifle else dark)
			_sbox(g, Vector3(0.045, 0.16, 0.08), Vector3(0, -0.12, 0.34), dark).rotation.x = 0.35 if t_rifle else 0.1
			_sbox(g, Vector3(0.04, 0.1, 0.05), Vector3(0, -0.08, 0.15), dark).rotation.x = -0.3
			if not t_rifle:
				_sbox(g, Vector3(0.035, 0.05, 0.1), Vector3(0, 0.07, 0.3), dark)
	var mz := Node3D.new()
	mz.name = "Muzzle"
	mz.position = Vector3(0, 0.02, muzzle)
	g.add_child(mz)
	return {"node": g, "at": at, "grip": grip, "fore": fore, "two_hands": two}


static func _sbox(parent: Node3D, size: Vector3, pos: Vector3, col: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	var m := StandardMaterial3D.new()
	m.albedo_color = col
	m.roughness = 0.9
	mi.material_override = m
	mi.position = pos
	parent.add_child(mi)
	return mi


## qurol og'zi (dunyo fazosida) — o'q izi shu yerdan chiqadi
func muzzle_position() -> Vector3:
	var m := _gun.get_node_or_null("Muzzle") as Node3D if _gun else null
	return m.global_position if m else global_position + Vector3.UP * 1.4


func _attach(bone: String) -> BoneAttachment3D:
	var a := BoneAttachment3D.new()
	a.bone_name = bone
	skel.add_child(a)
	return a


func _mat(col: Color) -> StandardMaterial3D:
	var k := col.to_html()
	if not _mats.has(k):
		var m := StandardMaterial3D.new()
		m.albedo_color = col
		m.roughness = 0.9
		_mats[k] = m
	return _mats[k]


func _box(parent: Node3D, size: Vector3, pos: Vector3, col: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = _mat(col)
	mi.position = pos
	parent.add_child(mi)
	return mi


func _limb(parent: Node3D, a: Vector3, b: Vector3, thick: float, col: Color) -> MeshInstance3D:
	var mi := _box(parent, Vector3(thick, thick, (b - a).length()), (a + b) * 0.5, col)
	var up := Vector3.UP if absf((b - a).normalized().dot(Vector3.UP)) < 0.95 else Vector3.RIGHT
	mi.basis = Basis.looking_at(b - a, up)
	return mi


func _all(n: Node, cls: String, out: Array = []) -> Array:
	if n.is_class(cls):
		out.append(n)
	for ch in n.get_children():
		_all(ch, cls, out)
	return out


func has_anim(_name: String) -> bool:
	return false


# ------------------------------------------------------------------ boshqaruv
func fire() -> void:
	if not dead:
		fire_count += 1
		_kick = 1.0


func reload() -> void:
	if not dead and not is_reloading():
		reload_count += 1
		_reload_left = RELOAD_TIME


func is_reloading() -> bool:
	return _reload_left > 0.0


func jump() -> void:
	if not dead:
		_jump_t = 0.3


func die() -> void:
	if dead:
		return
	dead = true
	_die_t = 0.0
	_set_hitboxes(false)


func _set_hitboxes(on: bool) -> void:
	for h in hitboxes:
		if is_instance_valid(h):
			h.collision_layer = LAYER_HITBOX if on else 0


func revive() -> void:
	dead = false
	_set_hitboxes(true)
	_die_t = 0.0
	model.rotation = Vector3.ZERO
	model.position = Vector3.ZERO


## ko'z nuqtasi (model fazosida): o'tirganda pastga tushadi
func eye_point() -> Vector3:
	return EYE - Vector3(0, 0.42 * _crouch_amt, 0)


func _process(delta: float) -> void:
	if model == null:
		return
	if dead:
		# o'lim: orqaga yiqiladi (0.45 s)
		_die_t = minf(_die_t + delta, 0.45)
		var k := _die_t / 0.45
		model.rotation.x = -PI * 0.5 * k * k
		model.position = Vector3(0, 0.12 * k, -0.25 * k)
		return
	var sp := Vector2(velocity_local.x, velocity_local.z).length()
	_crouch_amt = lerpf(_crouch_amt, 1.0 if (crouching or planting) else 0.0, 1.0 - exp(-delta * 10.0))
	_kick = maxf(0.0, _kick - delta * 12.0)
	_reload_left = maxf(0.0, _reload_left - delta)
	_jump_t = maxf(0.0, _jump_t - delta)
	# qadam: oyoqlar tezlikka mos tebranadi (havoda — bir oz bukilgan)
	var moving := on_floor and sp > 0.2
	_step += delta * (4.0 + sp * 1.6) if moving else 0.0
	var amp := clampf(sp / RUN_SPEED, 0.0, 1.0) * 0.55 if moving else 0.0
	var dirz := signf(velocity_local.z) if absf(velocity_local.z) > absf(velocity_local.x) * 0.5 else 1.0
	var hips_drop := 0.42 * _crouch_amt
	for i in _legs.size():
		var leg: Node3D = _legs[i]
		var ph := _step + PI * i
		leg.rotation.x = sin(ph) * amp * dirz + (0.0 if on_floor else 0.35) - 0.9 * _crouch_amt
		leg.position.y = HIPS_Y - 0.05 - hips_drop
		leg.position.z = 0.18 * _crouch_amt
		leg.scale.y = 1.0 - 0.1 * _crouch_amt
	var bob := absf(sin(_step)) * 0.025 * amp
	skel.set_bone_pose_position(0, Vector3(0, HIPS_Y - hips_drop + bob, 0))
	# nishonga qarash + tepki + qayta o'qlashda qurol pastga
	var share := [0.4, 0.6]
	for k in 2:
		var r := Quaternion(Vector3.RIGHT, -aim_pitch * share[k] - (0.05 * _kick if k == 1 else 0.0))
		skel.set_bone_pose_rotation(k + 1, r)
	if _gun:
		var rl := sin(clampf(1.0 - _reload_left / RELOAD_TIME, 0.0, 1.0) * PI) if _reload_left > 0.0 else 0.0
		_gun.rotation = Vector3(0.6 * rl - (0.9 * _kick if weapon_kind == WEAPON_KNIFE else 0.0), 0.0, -0.5 * rl)
