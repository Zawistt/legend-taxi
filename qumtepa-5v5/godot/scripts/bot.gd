extends CharacterBody3D
## Bot: NavMesh bo'ylab yuradi. Ko'rish, otish va qarorlar bot_match.gd da (hamma botlar bir joydan,
## bir xil tartibda boshqariladi — natija seed bo'yicha takrorlanadi).
## Fizika: qatlam 4 (players), niqob 1+2 (world + player_clip); botlar bir-biridan o'tib ketadi.

const SPEED := 4.5
const EYE := 1.6
const T_COLOR := Color(0.9, 0.45, 0.15)
const CT_COLOR := Color(0.2, 0.45, 0.9)

var team := "T"
var idx := 0
var hp := 100.0
var alive := true
var nav_map: RID

var goal := Vector3.ZERO
var has_goal := false
var path := PackedVector3Array()
var path_i := 0
var _repath_t := 0.0
var _last_pos := Vector3.ZERO
var _unstick_left := 0.0
var _unstick_dir := Vector3.ZERO

var look_dir := Vector3(0, 0, 1)
var hold_look := Vector3.ZERO      ## to'xtab turganda shu nuqtaga qaraydi (nol — qarash yo'q)

## jang holati (bot_match to'ldiradi)
var visible_enemies: Array = []    ## [[bot, faqat_bosh_ko'rinadi], ...]
var target: Node = null
var react_at := 0.0
var next_shot := 0.0
var fight_until := 0.0

## vazifa (bot_match to'ldiradi)
var role := ""                     ## guruh nomi yoki CT joyi
var plan: Array = []               ## yo'l nuqtalari
var plan_i := 0
var entry: Array = []
var entry_i := 0
var post_spot := Vector3.ZERO
var post_look := Vector3.ZERO
var carrier := false
var busy := ""                     ## "plant" / "defuse"
var busy_until := 0.0
var has_kit := false
var mode := ""                     ## "route", "stage", "entry", "site", "post", "hold", "rotate", "retake", "pickup"
## sezgi va xotira (bot_play.gd): eshitilgan tovush / oxirgi ko'rilgan dushman tomonga qarash
var alert_look := Vector3.ZERO
var alert_until := 0.0
var last_attacker: Node3D = null
var show_label := true             ## o'yinchi bilan o'yinda dushman yozuvi yashiriladi (devor orqali ko'rinmasin)
var burst := 0                     ## ketma-ket o'qlar (tarqalish o'sadi)
var clock := 0.0                   ## bot_play vaqti (alert uchun)
var weapon: Resource = null        ## qurol ma'lumoti (weapons/*.tres); bot_play tanlaydi

var _label: Label3D
var model: Node3D = null            ## personaj modeli (faqat ko'rinadigan rejimda)
var _steps: AudioStreamPlayer3D
var _gun: AudioStreamPlayer3D
var _step_t := 0.0
const CharacterModel := preload("res://scripts/character_model.gd")
const STEP_SOUNDS := [preload("res://audio/step_stone.wav")]


func setup(t: String, i: int, pos: Vector3, map_rid: RID, visual: bool) -> void:
	team = t
	idx = i
	nav_map = map_rid
	collision_layer = 8
	collision_mask = 1 | 2
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3              # NavMesh agent radiusidan kichik — burchaklarga ilinmaydi
	cap.height = 1.8
	cs.shape = cap
	cs.position = Vector3(0, 0.9, 0)
	add_child(cs)
	if visual:
		# personaj modeli: skelet, qurol (T — AKM, CT — M416) va animatsiyalar; +Z — oldinga (bot ham shunday buriladi)
		model = CharacterModel.new()
		model.team = t
		add_child(model)
		_steps = AudioStreamPlayer3D.new()
		_steps.unit_size = 4.0
		_steps.volume_db = -8.0
		_steps.max_distance = 40.0
		_steps.position = Vector3(0, 0.1, 0)
		add_child(_steps)
		_gun = AudioStreamPlayer3D.new()
		_gun.stream = load("res://audio/shot_%s.wav" % ("akm" if t == "T" else "m416"))
		_gun.unit_size = 10.0
		_gun.volume_db = -4.0
		_gun.max_distance = 90.0
		_gun.position = Vector3(0, 1.4, 0)
		add_child(_gun)
		_label = Label3D.new()
		_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		_label.no_depth_test = true
		_label.font_size = 36
		_label.outline_size = 8
		_label.position = Vector3(0, 2.3, 0)
		add_child(_label)
	reset(pos)


func reset(pos: Vector3) -> void:
	hp = 100.0
	alive = true
	visible = true
	collision_layer = 8
	global_position = pos
	velocity = Vector3.ZERO
	has_goal = false
	path = PackedVector3Array()
	visible_enemies = []
	target = null
	react_at = 0.0
	next_shot = 0.0
	fight_until = 0.0
	plan = []
	plan_i = 0
	entry = []
	entry_i = 0
	carrier = false
	busy = ""
	mode = ""
	hold_look = Vector3.ZERO
	look_dir = Vector3(0, 0, 1) if team == "T" else Vector3(0, 0, -1)
	alert_until = 0.0
	last_attacker = null
	burst = 0
	if model:
		model.revive()
	if _label:
		_label.visible = show_label
	_update_label()


func eye() -> Vector3:
	return global_position + Vector3.UP * EYE


## jamoani almashtirish (o'yinchi jamoasi o'zgarganda): model rangi, qurol tovushi
func set_team(t: String) -> void:
	if t == team:
		return
	team = t
	if model:
		model.load_model(t)
	if _gun:
		_gun.stream = load("res://audio/shot_%s.wav" % ("akm" if t == "T" else "m416"))
	_update_label()


func set_goal(p: Vector3) -> void:
	if has_goal and goal.distance_to(p) < 0.3 and not path.is_empty():
		return
	goal = p
	has_goal = true
	path = NavigationServer3D.map_get_path(nav_map, global_position, p, true)
	path_i = 1
	_repath_t = 0.0
	_last_pos = global_position


func clear_goal() -> void:
	has_goal = false
	path = PackedVector3Array()


func at(p: Vector3, tol := 0.7) -> bool:
	return Vector2(p.x - global_position.x, p.z - global_position.z).length() < tol


func moving() -> bool:
	return Vector2(velocity.x, velocity.z).length() > 1.0


## Bir fizika qadami. can_move=false — to'xtab turadi (jang, o'rnatish, zararsizlantirish).
func step(delta: float, can_move: bool) -> void:
	if not alive:
		return
	var dir := Vector3.ZERO
	if can_move and has_goal and path_i < path.size():
		var tp := path[path_i]
		var d := Vector2(tp.x - global_position.x, tp.z - global_position.z)
		while d.length() < 0.35 and path_i < path.size() - 1:
			path_i += 1
			tp = path[path_i]
			d = Vector2(tp.x - global_position.x, tp.z - global_position.z)
		if d.length() >= 0.35 or path_i < path.size() - 1:
			dir = Vector3(d.x, 0, d.y).normalized()
		else:
			path_i = path.size()
		# tiqilib qolsa — yo'lni qayta hisoblash va burchakdan chiqish uchun 0.45 s yon tomonga/orqaga qadam
		_repath_t += delta
		if _repath_t > 1.5:
			if global_position.distance_to(_last_pos) < 0.5:
				path = NavigationServer3D.map_get_path(nav_map, global_position, goal, true)
				path_i = 1
				_unstick_left = 0.45
				var side := Vector3(-dir.z, 0, dir.x) * (1.0 if randf() < 0.5 else -1.0)
				_unstick_dir = (side - dir * 0.6).normalized() if dir != Vector3.ZERO else side
			_repath_t = 0.0
			_last_pos = global_position
		if _unstick_left > 0.0:
			_unstick_left -= delta
			if _unstick_dir != Vector3.ZERO:
				dir = _unstick_dir
	velocity.x = dir.x * SPEED
	velocity.z = dir.z * SPEED
	if not is_on_floor():
		velocity.y -= 9.8 * delta
	else:
		velocity.y = 0.0
	move_and_slide()
	# zinapoya/do'nglik (≤ 0.4 m): NavMesh undan o'tadi, CharacterBody3D esa o'zi chiqmaydi — yuqoriga ko'tarib o'tkazamiz
	if dir != Vector3.ZERO and is_on_wall() and is_on_floor():
		var up := Vector3.UP * 0.4
		var fwd := dir * 0.25
		if not test_move(global_transform, up) and not test_move(global_transform.translated(up), fwd):
			global_position += up + fwd
			velocity.y = 0.0
	# qarash: nishon > eshitilgan/oxirgi ko'rilgan joy > harakat yo'nalishi > turish joyidagi yo'nalish
	if target and is_instance_valid(target) and target.alive:
		var to: Vector3 = target.global_position - global_position
		look_dir = Vector3(to.x, 0, to.z).normalized()
	elif alert_until > clock and Vector2(alert_look.x - global_position.x, alert_look.z - global_position.z).length() > 0.5:
		var ta := alert_look - global_position
		look_dir = Vector3(ta.x, 0, ta.z).normalized()
	elif dir != Vector3.ZERO:
		look_dir = dir
	elif hold_look != Vector3.ZERO:
		var to2 := hold_look - global_position
		if Vector2(to2.x, to2.z).length() > 0.3:
			look_dir = Vector3(to2.x, 0, to2.z).normalized()
	if look_dir != Vector3.ZERO:
		rotation.y = atan2(look_dir.x, look_dir.z)
	if model:
		var v := global_transform.basis.inverse() * velocity
		model.velocity_local = Vector3(v.x, 0, v.z)
		model.on_floor = is_on_floor()
		model.planting = busy != ""
		# qadam tovushi: botlar doim oddiy tezlikda yuradi — qadamlari eshitiladi (yugurish siklining yarmi)
		if moving() and is_on_floor():
			_step_t -= delta
			if _step_t <= 0.0:
				_step_t = 0.3
				_steps.stream = STEP_SOUNDS[0]
				_steps.pitch_scale = randf_range(0.9, 1.1)
				_steps.play()
		else:
			_step_t = 0.0


## o'yinchi o'qi tekkanda (fp_view.gd, tana zonasi bo'yicha zarar): true — o'ldi.
## O'z jamoasiga zarar yo'q. Otilgan bot otuvchi tomonga buriladi.
func take_hit(amount: float, _zone: String, from: Node) -> bool:
	if not alive or (from and "team" in from and from.team == team):
		return false
	if from is Node3D:
		last_attacker = from
		alert_look = from.global_position
		alert_until = clock + 3.0
	return damage(amount)


func damage(amount: float) -> bool:
	hp -= amount
	_update_label()
	if hp <= 0.0:
		die()
		return true
	return false


func on_shot() -> void:
	if model:
		model.fire()
		_gun.pitch_scale = randf_range(0.95, 1.05)
		_gun.play()


func die() -> void:
	alive = false
	hp = 0.0
	# model bo'lsa — o'lim animatsiyasi, jasad raund oxirigacha yotadi; bo'lmasa (sinov rejimi) yashiriladi
	if model:
		model.die()
		if _label:
			_label.visible = false
	else:
		visible = false
	collision_layer = 0
	velocity = Vector3.ZERO
	busy = ""


func _update_label() -> void:
	if _label:
		_label.text = "%s%d %d" % [team, idx + 1, int(max(hp, 0.0))]
		_label.modulate = T_COLOR if team == "T" else CT_COLOR
