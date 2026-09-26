extends Node3D
## Personaj modeli (T yoki CT): skelet, qurol va animatsiyalar (tools/rig_characters.py yaratadi).
## Harakatdan (tezlik, o'tirish, havoda) animatsiyani o'zi tanlaydi va aralashtiradi:
##   turish ↔ sekin yurish (Shift, 2.3 m/s) ↔ yugurish (4.5 m/s), 4 yo'nalish (oldinga, orqaga, chapga, o'ngga);
##   o'tirish va o'tirib yurish; sakrash (ko'tarilish, havoda, qo'nish);
##   tananing yuqori qismi alohida: o'q uzish va qayta o'qlash yugurganda ham oyoqlarni buzmaydi;
##   bomba qo'yish/zararsizlantirish (tiz cho'kish) va o'lim.
## Model +Z ga qarab turadi (Godot'da ota tugun "oldinga"sini shunga moslab buradi).
## first_person=true — faqat qo'llar va qurol (o'yinchi kamerasi uchun), ko'z nuqtasi kameraga bog'lanadi.
## own_body=true — o'yinchining o'z 3-shaxs tanasi: boshqa hamma kameralarga ko'rinadi, o'yinchining o'z kamerasiga
##   ko'rinmaydi (render qatlami 11, kamera uni chiqarib tashlaydi), lekin soyasi yerda ko'rinadi (CS2 dagidek).
## Render qatlamlari: 1 — dunyo, 11 — o'yinchining o'z tanasi, 12 — birinchi shaxs qo'llari/quroli.

const LOOPS := ["idle", "crouch_idle", "jump_air", "plant",
	"walk_f", "walk_b", "walk_l", "walk_r", "run_f", "run_b", "run_l", "run_r",
	"crouch_f", "crouch_b", "crouch_l", "crouch_r"]
const UPPER := ["spine1", "chest", "neck", "head", "clavicle.L", "clavicle.R", "upper_arm.L", "upper_arm.R",
	"forearm.L", "forearm.R", "hand.L", "hand.R", "fingers.L", "fingers.R", "weapon", "mag"]
const LAYER_WORLD := 1
const LAYER_OWN_BODY := 1 << 10     ## 11-qatlam
const LAYER_VIEWMODEL := 1 << 11    ## 12-qatlam
const RUN_SPEED := 4.5
const WALK_SPEED := 2.3
const CROUCH_SPEED := 1.55
const SCENES := {
	"T": "res://characters/t_operator.glb", "CT": "res://characters/ct_hero.glb",
	"T_fp": "res://characters/t_arms.glb", "CT_fp": "res://characters/ct_hero_arms.glb",
}
## CT qahramoni — foydalanuvchi bergan model va animatsiyalar (Mixamo skeleti, tools/hero_ct.py). Masshtab: ct_hero.json
const HERO_INFO := "res://characters/ct_hero.json"
## skelet turlari: suyak nomlari (bizning skelet / Mixamo)
const MIXAMO_UPPER := ["Spine1", "Spine2", "Neck", "Head", "LeftShoulder", "RightShoulder", "LeftArm", "RightArm",
	"LeftForeArm", "RightForeArm", "LeftHand", "RightHand", "LeftHandMiddle4", "RightHandMiddle4"]

@export var team := "T"
@export var first_person := false
@export var own_body := false
## nishonga qarash (radian, + tepaga): tananing yuqori qismi (umurtqa, ko'krak) egiladi — boshqalar qayerga
## qarab turganingizni ko'radi. Qo'llar va qurol ko'krakka bog'langani uchun birga egiladi.
var aim_pitch := 0.0

var model: Node3D
var skel: Skeleton3D
var anim: AnimationPlayer
var tree: AnimationTree
var dead := false

## boshqaruvchi (o'yinchi yoki bot) har kadr to'ldiradi
var velocity_local := Vector3.ZERO   ## model fazosida: +Z oldinga, +X chapga
var crouching := false
var on_floor := true
var planting := false

var _crouch_amt := 0.0
var _air_amt := 0.0
var _plant_amt := 0.0
var _blend := Vector2.ZERO
var _was_floor := true
var _head := -1
var _spine: Array = []


func _ready() -> void:
	load_model(team)


func load_model(t: String) -> void:
	team = t
	if model:
		model.queue_free()
		model = null
	var key := team + ("_fp" if first_person else "")
	var ps: PackedScene = load(SCENES[key])
	model = ps.instantiate()
	add_child(model)
	skel = _find(model, "Skeleton3D")
	anim = _find(model, "AnimationPlayer")
	mixamo = skel.find_bone("mixamorig_Hips") >= 0
	model.scale = Vector3.ONE * _hero_scale() if mixamo else Vector3.ONE
	# glTF import animatsiya nomini "<nom>" qiladi; eski eksportlarda "<nom>_Skeleton" bo'lishi mumkin
	_head = skel.find_bone("mixamorig_Head" if mixamo else "head")
	for n in LOOPS:
		if anim.has_animation(n):
			anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	for m in _all(model, "MeshInstance3D"):
		var mi := m as MeshInstance3D
		if first_person:
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			mi.layers = LAYER_VIEWMODEL
		elif own_body:
			mi.layers = LAYER_OWN_BODY
		else:
			mi.layers = LAYER_WORLD
	_build_tree()
	dead = false


func _find(n: Node, cls: String) -> Node:
	if n.is_class(cls):
		return n
	for c in n.get_children():
		var r := _find(c, cls)
		if r:
			return r
	return null


func _all(n: Node, cls: String, out: Array = []) -> Array:
	if n.is_class(cls):
		out.append(n)
	for c in n.get_children():
		_all(c, cls, out)
	return out


var mixamo := false


func _hero_scale() -> float:
	if not FileAccess.file_exists(HERO_INFO):
		return 1.0
	var d = JSON.parse_string(FileAccess.get_file_as_string(HERO_INFO))
	return float(d.get("scale", 1.0)) if d is Dictionary else 1.0


## animatsiya hali berilmagan bo'lsa — tik turish ishlatiladi (qahramon animatsiyalari bittadan qo'shib boriladi)
func _a(name: String) -> AnimationNodeAnimation:
	var a := AnimationNodeAnimation.new()
	a.animation = name if anim.has_animation(name) else "idle"
	return a


func has_anim(name: String) -> bool:
	return anim != null and anim.has_animation(name)


func _space(prefix: String, center: String, r: float) -> AnimationNodeBlendSpace2D:
	var s := AnimationNodeBlendSpace2D.new()
	s.min_space = Vector2(-1.1, -1.1)
	s.max_space = Vector2(1.1, 1.1)
	s.sync = true
	s.add_blend_point(_a(center), Vector2.ZERO)
	for d in [["f", Vector2(0, 1)], ["b", Vector2(0, -1)], ["l", Vector2(-1, 0)], ["r", Vector2(1, 0)]]:
		s.add_blend_point(_a(prefix + "_" + d[0]), d[1] * r)
	return s


func _build_tree() -> void:
	if tree:
		tree.queue_free()
	tree = AnimationTree.new()
	tree.name = "AnimationTree"
	model.add_child(tree)
	tree.anim_player = tree.get_path_to(anim)
	tree.root_node = tree.get_path_to(model)
	var bt := AnimationNodeBlendTree.new()
	# tik turish: markazda turish, 0.51 radiusda sekin yurish, 1.0 da yugurish
	var stand := _space("run", "idle", 1.0)
	var wr := WALK_SPEED / RUN_SPEED
	for d in [["f", Vector2(0, 1)], ["b", Vector2(0, -1)], ["l", Vector2(-1, 0)], ["r", Vector2(1, 0)]]:
		stand.add_blend_point(_a("walk_" + d[0]), d[1] * wr)
	bt.add_node("stand", stand)
	bt.add_node("crouch", _space("crouch", "crouch_idle", 1.0))
	bt.add_node("crouch_amt", AnimationNodeBlend2.new())
	bt.connect_node("crouch_amt", 0, "stand")
	bt.connect_node("crouch_amt", 1, "crouch")
	bt.add_node("jump_air", _a("jump_air"))
	bt.add_node("air_amt", AnimationNodeBlend2.new())
	bt.connect_node("air_amt", 0, "crouch_amt")
	bt.connect_node("air_amt", 1, "jump_air")
	var land := AnimationNodeOneShot.new()
	land.fadein_time = 0.05
	land.fadeout_time = 0.15
	bt.add_node("land", land)
	bt.add_node("jump_land", _a("jump_land"))
	bt.connect_node("land", 0, "air_amt")
	bt.connect_node("land", 1, "jump_land")
	var jump := AnimationNodeOneShot.new()
	jump.fadein_time = 0.05
	jump.fadeout_time = 0.1
	bt.add_node("jump", jump)
	bt.add_node("jump_start", _a("jump_start"))
	bt.connect_node("jump", 0, "land")
	bt.connect_node("jump", 1, "jump_start")
	bt.add_node("plant", _a("plant"))
	bt.add_node("plant_amt", AnimationNodeBlend2.new())
	bt.connect_node("plant_amt", 0, "jump")
	bt.connect_node("plant_amt", 1, "plant")
	# tananing yuqori qismi: o'q uzish va qayta o'qlash (oyoqlar harakatda qoladi)
	var fire := AnimationNodeOneShot.new()
	fire.fadein_time = 0.02
	fire.fadeout_time = 0.08
	var reload := AnimationNodeOneShot.new()
	reload.fadein_time = 0.12
	reload.fadeout_time = 0.2
	for os in [fire, reload]:
		os.filter_enabled = true
		for p in _upper_paths():
			os.set_filter_path(p, true)
	bt.add_node("fire", fire)
	bt.add_node("fire_anim", _a("fire"))
	bt.connect_node("fire", 0, "plant_amt")
	bt.connect_node("fire", 1, "fire_anim")
	bt.add_node("reload", reload)
	bt.add_node("reload_anim", _a("reload"))
	bt.connect_node("reload", 0, "fire")
	bt.connect_node("reload", 1, "reload_anim")
	bt.connect_node("output", 0, "reload")
	tree.tree_root = bt
	tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	tree.active = true
	_spine = [skel.find_bone("mixamorig_Spine1"), skel.find_bone("mixamorig_Spine2")] if mixamo \
		else [skel.find_bone("spine1"), skel.find_bone("chest")]


func _upper_paths() -> Array:
	var out := []
	var a := anim.get_animation("idle")
	for i in a.get_track_count():
		var p := a.track_get_path(i)
		var bone := p.get_concatenated_subnames()
		if bone in UPPER or bone.trim_prefix("mixamorig_") in MIXAMO_UPPER:
			out.append(p)
	return out


# ------------------------------------------------------------------ boshqaruv
func fire() -> void:
	if tree and not dead:
		tree.set("parameters/fire/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


func reload() -> void:
	if tree and not dead and not is_reloading():
		tree.set("parameters/reload/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


func is_reloading() -> bool:
	return tree != null and bool(tree.get("parameters/reload/active"))


func jump() -> void:
	if tree and not dead:
		tree.set("parameters/jump/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


func die() -> void:
	if dead:
		return
	dead = true
	tree.active = false
	anim.play("death", 0.15)


func revive() -> void:
	dead = false
	anim.stop()
	tree.active = true
	tree.advance(0.0)
	_air_amt = 0.0


## ko'z nuqtasi (model fazosida): bosh suyagidan biroz oldinga va tepaga
func eye_point() -> Vector3:
	if skel == null or _head < 0:
		return Vector3(0, 1.67, 0.09)
	var hp := skel.get_bone_global_pose(_head).origin
	var k := model.scale.x
	return to_local(skel.to_global(hp)) if not is_inside_tree() else (to_local(skel.to_global(hp)) + Vector3(0, 0.08, 0.09) * k)


func _process(delta: float) -> void:
	if tree == null or dead:
		return
	var k := 1.0 - exp(-delta * 10.0)
	var sp := Vector2(-velocity_local.x, velocity_local.z)      # blend fazosi: +x — o'ngga, +y — oldinga
	var target: Vector2
	if crouching:
		target = sp / CROUCH_SPEED
	else:
		target = sp / RUN_SPEED
	if target.length() > 1.0:
		target = target.normalized()
	_blend = _blend.lerp(target, k)
	_crouch_amt = lerpf(_crouch_amt, 1.0 if crouching else 0.0, 1.0 - exp(-delta * 8.0))
	_air_amt = lerpf(_air_amt, 0.0 if on_floor else 1.0, 1.0 - exp(-delta * 12.0))
	_plant_amt = lerpf(_plant_amt, 1.0 if planting else 0.0, 1.0 - exp(-delta * 6.0))
	tree.set("parameters/stand/blend_position", _blend)
	tree.set("parameters/crouch/blend_position", _blend)
	tree.set("parameters/crouch_amt/blend_amount", _crouch_amt)
	tree.set("parameters/air_amt/blend_amount", _air_amt)
	tree.set("parameters/plant_amt/blend_amount", _plant_amt)
	if on_floor and not _was_floor:
		tree.set("parameters/land/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	_was_floor = on_floor
	tree.advance(delta)
	_apply_aim()


## animatsiyadan keyin: umurtqa (40%) va ko'krak (60%) nishon burchagiga egiladi (model +Z oldinga, +X chapga)
func _apply_aim() -> void:
	if first_person or absf(aim_pitch) < 0.001:
		return
	var share := [0.4, 0.6]
	for k in _spine.size():
		var i: int = _spine[k]
		if i < 0:
			continue
		var g := skel.get_bone_global_pose(i).basis.orthonormalized()
		var r := Basis(Vector3.RIGHT, -aim_pitch * share[k])
		var d := Quaternion(g.inverse() * r * g)
		skel.set_bone_pose_rotation(i, (skel.get_bone_pose_rotation(i) * d).normalized())
