extends Node3D
## 3-SHAXS tana — skeletli model va uning animatsiyalari (hozircha T: "Desert Shadow Operative", tools/rig_t_shadow.py).
## Faqat boshqalar ko'radigan tana (botlar, o'yinchining o'z soyasi). Birinchi shaxs bu modelga bog'liq emas —
## u character_model.gd (first_person=true) ichidagi alohida qo'l va qurol.
## character_model.gd shu tugunni yaratadi va API (fire, reload, die, set_weapon, ...) ni shu yerga uzatadi.
##
## AnimationTree (qo'lda yangilanadi, keyin nishonga egilish qo'shiladi):
##   turish/yurish/yugurish (BlendSpace2D, tezlik m/s)  ─┐
##   o'tirib turish/yurish (BlendSpace2D)               ─┴ o'tirish aralashmasi -> havoda (sakrash) -> bomba qo'yish
##   -> qurol pozasi (to'pponcha / pichoq / granata / C4 — faqat yelka, qo'l va qurol suyaklariga)
##   -> o'q uzish, qayta o'qlash, harakat (pichoq zarbasi / granata otish) — bir martalik, faqat tananing yuqori qismi.
## O'lim — alohida (daraxt to'xtaydi, "death" klipi oxirgi kadrda qoladi).

const SCENES := {"T": "res://characters/t_shadow.glb"}
const SK := "Skeleton/Skeleton3D:"
const LOOPS := ["idle", "walk_f", "walk_b", "walk_l", "walk_r", "run_f", "run_b", "run_l", "run_r", "crouch_idle",
	"crouch_f", "crouch_b", "crouch_l", "crouch_r", "jump_air", "plant"]
const ARM_BONES := ["clavicle.L", "upper_arm.L", "forearm.L", "hand.L", "fingers.L", "clavicle.R", "upper_arm.R", "forearm.R",
	"hand.R", "fingers.R", "weapon", "mag"]
const UPPER_BONES := ["spine1", "chest", "neck", "head"]
## o'q tegadigan zonalar: suyak, zona, eni/qalinligi (m), uzunligi (0 — keyingi suyakkacha)
const HITBOXES := [["head", "head", Vector3(0.24, 0, 0.26), 0.27], ["chest", "body", Vector3(0.42, 0, 0.3), 0.0],
	["spine1", "body", Vector3(0.38, 0, 0.27), 0.0], ["spine", "stomach", Vector3(0.36, 0, 0.26), 0.0],
	["hips", "stomach", Vector3(0.36, 0, 0.25), 0.0],
	["upper_arm.L", "arm", Vector3(0.12, 0, 0.12), 0.0], ["forearm.L", "arm", Vector3(0.1, 0, 0.1), 0.0],
	["upper_arm.R", "arm", Vector3(0.12, 0, 0.12), 0.0], ["forearm.R", "arm", Vector3(0.1, 0, 0.1), 0.0],
	["thigh.L", "leg", Vector3(0.17, 0, 0.17), 0.0], ["shin.L", "leg", Vector3(0.13, 0, 0.13), 0.0],
	["thigh.R", "leg", Vector3(0.17, 0, 0.17), 0.0], ["shin.R", "leg", Vector3(0.13, 0, 0.13), 0.0]]
## qurol turi -> qo'l pozasi (bo'sh — avtomat pozasi, u yurish kliplarining o'zida)
const HOLD := {1: "hold_pistol", 2: "hold_knife", 7: "hold_nade", 8: "hold_pistol", 9: "hold_c4"}

var cm: Node3D                      ## character_model.gd (egasi)
var inst: Node3D
var skel: Skeleton3D
var ap: AnimationPlayer
var tree: AnimationTree
var gun: Node3D
var gun_att: BoneAttachment3D
var hitboxes: Array = []
var _crouch := 0.0
var _air := 0.0
var _plant := 0.0
var _hold := 0.0
var _dead := false
var _i_spine1 := -1
var _i_chest := -1
var _i_head := -1
var _i_hand := -1
var _in_hand := false               ## bir qo'lli qurol: har kadr o'ng kaftga qo'yiladi (IK xatosi ko'rinmasin)
var _grip := Vector3.ZERO
var _aim := 0.0


static func available(team: String) -> bool:
	return SCENES.has(team) and ResourceLoader.exists(SCENES[team])


func setup(owner_model: Node3D, team: String) -> void:
	cm = owner_model
	inst = (load(SCENES[team]) as PackedScene).instantiate()
	inst.name = "Rig"
	add_child(inst)
	skel = inst.find_children("*", "Skeleton3D", true, false)[0]
	ap = inst.find_children("*", "AnimationPlayer", true, false)[0]
	for n in LOOPS:
		if ap.has_animation(n):
			ap.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	_i_spine1 = skel.find_bone("spine1")
	_i_chest = skel.find_bone("chest")
	_i_head = skel.find_bone("head")
	_i_hand = skel.find_bone("hand.R")
	_build_tree()
	gun_att = BoneAttachment3D.new()
	gun_att.bone_name = "weapon"
	skel.add_child(gun_att)
	for m in inst.find_children("*", "MeshInstance3D", true, false):
		(m as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON


func _anim(name: String) -> AnimationNodeAnimation:
	var a := AnimationNodeAnimation.new()
	a.animation = name
	return a


func _space(prefix: String, idle: String, speeds: Array) -> AnimationNodeBlendSpace2D:
	var bs := AnimationNodeBlendSpace2D.new()
	bs.min_space = Vector2(-5, -5)
	bs.max_space = Vector2(5, 5)
	bs.add_blend_point(_anim(idle), Vector2.ZERO)
	for sp in speeds:
		var g: String = sp[0]
		var v: float = sp[1]
		bs.add_blend_point(_anim(g + "_f"), Vector2(0, v))
		bs.add_blend_point(_anim(g + "_b"), Vector2(0, -v))
		bs.add_blend_point(_anim(g + "_l"), Vector2(v, 0))
		bs.add_blend_point(_anim(g + "_r"), Vector2(-v, 0))
	return bs


func _filter(node: AnimationNode, bones: Array) -> void:
	node.filter_enabled = true
	for b in bones:
		node.set_filter_path(NodePath(SK + b), true)


func _build_tree() -> void:
	var bt := AnimationNodeBlendTree.new()
	bt.add_node("stand", _space("", "idle", [["walk", 2.3], ["run", 4.5]]), Vector2(0, 0))
	bt.add_node("crouch", _space("", "crouch_idle", [["crouch", 1.55]]), Vector2(0, 200))
	var cmix := AnimationNodeBlend2.new()
	bt.add_node("crouch_mix", cmix, Vector2(250, 100))
	bt.connect_node("crouch_mix", 0, "stand")
	bt.connect_node("crouch_mix", 1, "crouch")
	bt.add_node("jump", _anim("jump_air"), Vector2(250, 300))
	bt.add_node("air", AnimationNodeBlend2.new(), Vector2(500, 100))
	bt.connect_node("air", 0, "crouch_mix")
	bt.connect_node("air", 1, "jump")
	bt.add_node("plant_anim", _anim("plant"), Vector2(500, 300))
	bt.add_node("plant", AnimationNodeBlend2.new(), Vector2(750, 100))
	bt.connect_node("plant", 0, "air")
	bt.connect_node("plant", 1, "plant_anim")
	var sel := AnimationNodeTransition.new()
	sel.xfade_time = 0.15
	var holds := ["hold_pistol", "hold_knife", "hold_nade", "hold_c4"]
	for i in holds.size():
		sel.add_input(holds[i])
		bt.add_node(holds[i], _anim(holds[i]), Vector2(500, 400 + i * 80))
	bt.add_node("hold_anim", sel, Vector2(750, 300))
	for i in holds.size():
		bt.connect_node("hold_anim", i, holds[i])
	var hold := AnimationNodeBlend2.new()
	_filter(hold, ARM_BONES)
	bt.add_node("hold", hold, Vector2(1000, 100))
	bt.connect_node("hold", 0, "plant")
	bt.connect_node("hold", 1, "hold_anim")
	bt.add_node("fire_anim", _anim("fire"), Vector2(1000, 300))
	var fire := AnimationNodeOneShot.new()
	fire.fadein_time = 0.02
	fire.fadeout_time = 0.08
	_filter(fire, ARM_BONES + UPPER_BONES)
	bt.add_node("fire", fire, Vector2(1250, 100))
	bt.connect_node("fire", 0, "hold")
	bt.connect_node("fire", 1, "fire_anim")
	bt.add_node("reload_anim", _anim("reload"), Vector2(1250, 300))
	var rs := AnimationNodeTimeScale.new()
	bt.add_node("reload_speed", rs, Vector2(1400, 300))
	bt.connect_node("reload_speed", 0, "reload_anim")
	var rl := AnimationNodeOneShot.new()
	rl.fadein_time = 0.15
	rl.fadeout_time = 0.2
	_filter(rl, ARM_BONES)
	bt.add_node("reload", rl, Vector2(1500, 100))
	bt.connect_node("reload", 0, "fire")
	bt.connect_node("reload", 1, "reload_speed")
	var asel := AnimationNodeTransition.new()
	asel.xfade_time = 0.0
	for i in 2:
		var an: String = ["slash", "throw"][i]
		asel.add_input(an)
		bt.add_node(an, _anim(an), Vector2(1400, 400 + i * 80))
	bt.add_node("act_anim", asel, Vector2(1500, 300))
	for i in 2:
		bt.connect_node("act_anim", i, ["slash", "throw"][i])
	var act := AnimationNodeOneShot.new()
	act.fadein_time = 0.05
	act.fadeout_time = 0.15
	_filter(act, ARM_BONES + UPPER_BONES)
	bt.add_node("action", act, Vector2(1750, 100))
	bt.connect_node("action", 0, "reload")
	bt.connect_node("action", 1, "act_anim")
	bt.connect_node("output", 0, "action")
	tree = AnimationTree.new()
	tree.name = "AnimationTree"
	inst.add_child(tree)
	tree.anim_player = tree.get_path_to(ap)
	tree.tree_root = bt
	tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	tree.active = true
	tree.set("parameters/reload_speed/scale", 1.0)


## qo'ldagi qurol: shakl (character_model.make_weapon_shape) "weapon" suyagiga, dasta suyak boshida.
## Suyak fazosi: +Y — og'iz tomoni, +Z — tepa, +X — o'ng; shaklda +Z — og'iz, +Y — tepa, +X — chap.
func set_weapon(kind: int, wid: String) -> void:
	if gun:
		gun.queue_free()
		gun = null
	var shape: Dictionary = cm.make_weapon_shape(kind, cm.team, wid)
	gun = shape.node
	gun.name = "Weapon"
	var h: String = HOLD.get(kind, "")
	_in_hand = h != ""
	_grip = shape.grip
	if _in_hand:
		add_child(gun)
		_place_in_hand()
	else:
		gun_att.add_child(gun)
		var b := Basis(Vector3(-1, 0, 0), Vector3(0, 0, 1), Vector3(0, 1, 0))
		gun.transform = Transform3D(b, -(b * shape.grip))
	_hold = 1.0 if h != "" else 0.0
	if h != "":
		tree.set("parameters/hold_anim/transition_request", h)
	apply_layers(cm.first_person, cm.own_body)


func apply_layers(_fp: bool, own: bool) -> void:
	for m in find_children("*", "MeshInstance3D", true, false):
		(m as MeshInstance3D).layers = cm.LAYER_OWN_BODY if own else cm.LAYER_WORLD


func build_hitboxes(layer: int) -> Array:
	hitboxes = []
	for h in HITBOXES:
		var i := skel.find_bone(h[0])
		if i < 0:
			continue
		var length: float = h[3]
		if length <= 0.0:
			for c in skel.get_bone_children(i):
				length = maxf(length, skel.get_bone_rest(c).origin.length())
		var att := BoneAttachment3D.new()
		att.bone_name = h[0]
		skel.add_child(att)
		var a := Area3D.new()
		a.collision_layer = layer
		a.collision_mask = 0
		a.monitoring = false
		a.set_meta("zone", h[1])
		a.set_meta("owner_model", cm)
		var cs := CollisionShape3D.new()
		var bs := BoxShape3D.new()
		bs.size = Vector3(h[2].x, length, h[2].z)
		cs.shape = bs
		a.add_child(cs)
		a.position = Vector3(0, length * 0.5, 0)
		att.add_child(a)
		hitboxes.append(a)
	return hitboxes


func fire(kind: int) -> void:
	if _dead:
		return
	if kind == 2 or kind == 7:
		tree.set("parameters/act_anim/transition_request", "slash" if kind == 2 else "throw")
		tree.set("parameters/action/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	else:
		tree.set("parameters/fire/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


func reload(duration: float) -> void:
	if _dead:
		return
	var L: float = ap.get_animation("reload").length
	tree.set("parameters/reload_speed/scale", L / maxf(0.3, duration))
	tree.set("parameters/reload/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)


func is_reloading() -> bool:
	return bool(tree.get("parameters/reload/active"))


func die() -> void:
	_dead = true
	tree.active = false
	ap.play("death", 0.1)
	if gun:
		gun.visible = false             # CS2 dagidek qurol qo'ldan tushadi


func revive() -> void:
	_dead = false
	ap.stop()
	tree.active = true
	if gun:
		gun.visible = true


## bir qo'lli qurol o'ng kaftda: og'zi tananing oldiga (nishonga qarab egilgan holda)
func _place_in_hand() -> void:
	if gun == null or _i_hand < 0:
		return
	var hb := skel.get_bone_global_pose(_i_hand)
	var palm := hb.origin + hb.basis.y.normalized() * 0.075
	var b := Basis(Vector3.RIGHT, -_aim)
	gun.transform = Transform3D(b, to_local(skel.to_global(palm)) - b * _grip)


func has_anim(n: String) -> bool:
	return ap.has_animation(n)


## ko'z (egasi fazosida)
func eye_point() -> Vector3:
	var g := skel.get_bone_global_pose(_i_head)
	return cm.to_local(skel.to_global(g.origin + Vector3(0, 0.1, 0.1)))


func muzzle_position() -> Vector3:
	var m := gun.get_node_or_null("Muzzle") as Node3D if gun else null
	return m.global_position if m else global_position + Vector3.UP * 1.4


func update(delta: float, vel: Vector3, crouching: bool, on_floor: bool, planting: bool, aim_pitch: float) -> void:
	if _dead:
		return
	var k := 1.0 - exp(-delta * 10.0)
	_crouch = lerpf(_crouch, 1.0 if crouching else 0.0, k)
	_air = lerpf(_air, 0.0 if on_floor else 1.0, 1.0 - exp(-delta * 8.0))
	_plant = lerpf(_plant, 1.0 if planting else 0.0, k)
	var bp := Vector2(vel.x, vel.z)
	tree.set("parameters/stand/blend_position", bp)
	tree.set("parameters/crouch/blend_position", bp)
	tree.set("parameters/crouch_mix/blend_amount", _crouch)
	tree.set("parameters/air/blend_amount", _air)
	tree.set("parameters/plant/blend_amount", _plant)
	tree.set("parameters/hold/blend_amount", _hold * (1.0 - _plant))
	tree.advance(delta)
	# nishonga qarash: tananing yuqori qismi model X o'qi atrofida egiladi (tepaga qarasa — orqaga)
	if absf(aim_pitch) > 0.001 and _plant < 0.5:
		for pair in [[_i_spine1, 0.4], [_i_chest, 0.6]]:
			var i: int = pair[0]
			var par := skel.get_bone_parent(i)
			var pg := skel.get_bone_global_pose(par)
			var g := skel.get_bone_global_pose(i)
			var ng := Basis(Vector3.RIGHT, -aim_pitch * pair[1]) * g.basis
			skel.set_bone_pose_rotation(i, (pg.basis.inverse() * ng).get_rotation_quaternion())
	_aim = aim_pitch
	if _in_hand:
		_place_in_hand()
