extends Node3D
## Birinchi shaxs: qo'llar va qurol (hozircha low-poly o'rinbosar — character_model.gd) va QUROL TIZIMI.
## Qurol tizimi Legend Tactical FPS loyihasidan olingan g'oyalar asosida Qumtepa uchun qayta yozilgan:
##   - ma'lumotga asoslangan qurollar (res://weapons/*.tres, scripts/weapon_data.gd): 1 — asosiy qurol
##     (LAR-01; sotib olish menyusida (B) AR-44, Spectre-9 SMG, Longbow-50 snayper, Breacher-12 drobovik),
##     2 — Apex-9 to'pponcha, 3 — pichoq. Almashtirish: 1/2/3 yoki sichqoncha g'ildiragi.
##   - o'q rejimlari (X): avtomat / 3 talik / bittalik; magazin, zaxira, qayta o'qlash (bo'sh magazin — uzoqroq);
##   - snayper: zatvor (har o'qdan keyin 1.1 s), ADS da optik nishon; drobovik: bir otishda 8 ta sochma;
##   - tepki naqshi (har o'q oldindan belgilangan yo'nalishga), otish to'xtaganda nishon joyiga qaytadi;
##   - tarqalish: har o'qda kengayadi, harakat / sakrash / o'tirish / ADS ga qarab o'zgaradi;
##   - ADS (sichqoncha o'ng tugmasi): FOV kichrayadi, qurol markazga keladi, sezgirlik va tarqalish kamayadi;
##   - o'q (hitscan): tana qismlari bo'yicha zarar (bosh / tana / qo'l / oyoq), uzoqda zarar kamayadi;
##   - o'q izi, devorga tegish izi, HUD: tarqalishga mos nishon belgisi, tegish belgisi (boshga — qizil).
## Ko'z nuqtasi doim kamerada turadi. Model 0.6 marta kichraytirilgan va kameraga yaqinlashtirilgan —
## ko'rinishi aynan bir xil, lekin devorga kirib ketmaydi. Soya tashlamaydi.

const CharacterModel := preload("res://scripts/character_model.gd")
const CombatHud := preload("res://scripts/combat_hud.gd")
const WeaponData := preload("res://scripts/weapon_data.gd")
const BuyMenu := preload("res://scripts/buy_menu.gd")
const WEAPON_FILES := ["res://weapons/rifle.tres", "res://weapons/vanguard.tres", "res://weapons/smg.tres",
	"res://weapons/sniper.tres", "res://weapons/shotgun.tres", "res://weapons/pistol.tres", "res://weapons/knife.tres"]
const START_PRIMARY := "lar_01"
const SCALE := 0.6
## qurol ekranda o'ng pastda: kameraga nisbatan siljish (m, kichraytirishdan oldin), og'ish °, ko'tarilish °
const TUNE := {
	"T": [Vector3(0.16, 0.05, -0.2), 3.0, 0.0],
	"CT": [Vector3(0.16, 0.05, -0.2), 3.0, 0.0],
}
## ADS: qurol ekran markaziga (qurol turi bo'yicha)
const ADS_TUNE := {0: Vector3(-0.13, 0.215, -0.14), 1: Vector3(-0.05, 0.245, -0.1), 3: Vector3(-0.13, 0.225, -0.12),
	4: Vector3(-0.13, 0.2, -0.14), 5: Vector3(-0.13, 0.215, -0.14)}
const MODE_NAMES := ["BITTALIK", "3 TALIK", "AVTOMAT"]
const RAY_MASK := 1 | CharacterModel.LAYER_HITBOX

signal hit_confirmed(zone: String, damage: float, killed: bool)

var player: CharacterBody3D
var ch: Node3D
var hud: Control
var weapons: Array = []                ## hamma WeaponData (weapons/*.tres)
var owned := {}                        ## slot -> WeaponData (o'yinchi qo'lidagi qurollar)
var buy_menu: Control
var current: Resource                  ## hozirgi qurol
var ammo := 0
var reserve := 0
var shots_fired := 0
var fire_mode := 2
var ads := false                       ## sichqoncha o'ng tugmasi bosilganmi
var ads_amt := 0.0
var force_ads := false                 ## testlar uchun
var no_spread := false                 ## testlar uchun: aniq otish
var bloom := 0.0
var last_hit := {}
var last_shot := {}                    ## oxirgi otish: sochmalar soni, tekkanlari, jami zarar
var _ammo_of := {}                     ## weapon_id -> [magazin, zaxira]
var _next_shot := 0.0
var _equip_end := 0.0
var _last_shot_t := -10.0
var _shot_idx := 0
var _recoil := Vector2.ZERO            ## hozircha qaytarilmagan tepki (radian): x — tepaga, y — o'ngga
var _burst_left := 0
var _eye_s := Vector3.ZERO
var _team := ""
var _flash: OmniLight3D
var _shot: AudioStreamPlayer
var _reload_snd: AudioStreamPlayer
var _label: Label
var _t := 0.0
var _reload_end := -1.0
var _base_fov := 80.0
var _impacts: Array = []
## CS2 uslubidagi tabiiy harakat: yurganda qadam tebranishi, sichqoncha burilganda qurolning biroz kechikishi
var _bob_t := 0.0
var _sway := Vector2.ZERO
var _last_look := Vector2.ZERO


func _ready() -> void:
	player = get_parent().get_parent() as CharacterBody3D
	_base_fov = (get_parent() as Camera3D).fov          # o'yinchining @onready cam hali tayyor emas
	_ensure_input()
	for f in WEAPON_FILES:
		var w: Resource = load(f)
		weapons.append(w)
		_ammo_of[w.weapon_id] = [w.magazine_size, w.reserve_ammo]
		if w.slot != 1 or w.weapon_id == START_PRIMARY:
			owned[w.slot] = w
	ch = CharacterModel.new()
	ch.first_person = true
	ch.team = player.team
	_team = player.team
	add_child(ch)
	_flash = OmniLight3D.new()
	_flash.light_color = Color(1.0, 0.75, 0.4)
	_flash.omni_range = 6.0
	_flash.light_energy = 0.0
	_flash.shadow_enabled = false
	_flash.position = Vector3(0.12, -0.12, -0.9)
	add_child(_flash)
	_shot = AudioStreamPlayer.new()
	_shot.volume_db = -6.0
	add_child(_shot)
	_reload_snd = AudioStreamPlayer.new()
	_reload_snd.stream = load("res://audio/reload.wav")
	_reload_snd.volume_db = -8.0
	add_child(_reload_snd)
	var layer := CanvasLayer.new()
	layer.layer = 4
	add_child(layer)
	hud = CombatHud.new()
	hud.fpv = self
	layer.add_child(hud)
	buy_menu = BuyMenu.new()
	buy_menu.fpv = self
	layer.add_child(buy_menu)
	_label = Label.new()
	_label.anchor_left = 1.0
	_label.anchor_top = 1.0
	_label.anchor_right = 1.0
	_label.anchor_bottom = 1.0
	_label.offset_left = -420
	_label.offset_top = -70
	_label.offset_right = -20
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_label.add_theme_font_size_override("font_size", 30)
	_label.add_theme_color_override("font_outline_color", Color.BLACK)
	_label.add_theme_constant_override("outline_size", 6)
	layer.add_child(_label)
	equip(1, true)


static func _ensure_input() -> void:
	var keys := {"weapon_1": KEY_1, "weapon_2": KEY_2, "weapon_3": KEY_3, "fire_mode": KEY_X}
	for a in keys:
		if not InputMap.has_action(a):
			InputMap.add_action(a)
			var ev := InputEventKey.new()
			ev.physical_keycode = keys[a]
			InputMap.action_add_event(a, ev)
	if not InputMap.has_action("aim"):
		InputMap.add_action("aim")
		var mb := InputEventMouseButton.new()
		mb.button_index = MOUSE_BUTTON_RIGHT
		InputMap.action_add_event("aim", mb)


# ------------------------------------------------------------------ qurollar
func equip(slot: int, instant := false) -> void:
	var w: Resource = owned.get(slot)
	if w == null or (w == current and not instant):
		return
	if current:
		_ammo_of[current.weapon_id] = [ammo, reserve]
	current = w
	ammo = _ammo_of[w.weapon_id][0]
	reserve = _ammo_of[w.weapon_id][1]
	fire_mode = int(w.fire_modes[0]) if w.fire_modes.size() else 0
	_reload_end = -1.0
	_burst_left = 0
	_shot_idx = 0
	bloom = 0.0
	_equip_end = _t + (0.0 if instant else w.equip_time)
	ch.set_weapon(w.kind)
	if player.body and player.body.has_method("set_weapon"):
		player.body.set_weapon(w.kind)
	_update_sound()


## asosiy qurolni sotib olish (sotib olish zonasi va vaqti buy_menu.gd da tekshiriladi): to'liq magazin bilan qo'lga
func buy(weapon_id: String) -> bool:
	for w in weapons:
		if w.weapon_id == weapon_id and w.slot == 1:
			owned[1] = w
			_ammo_of[w.weapon_id] = [w.magazine_size, w.reserve_ammo]
			if current and current.slot == 1:
				current = null
			equip(1)
			return true
	return false


func weapon_by_id(weapon_id: String) -> Resource:
	for w in weapons:
		if w.weapon_id == weapon_id:
			return w
	return null


func scoped() -> bool:
	return current != null and current.scope and ads_amt > 0.6


func _update_sound() -> void:
	if current == null:
		return
	_shot.stream = load("res://audio/shot_%s.wav" % ("akm" if _team == "T" else "m416"))
	_shot.pitch_scale = 1.3 if current.kind == WeaponData.Kind.PISTOL else 1.0


func cycle_mode() -> void:
	if current and current.fire_modes.size() > 1:
		var i: int = current.fire_modes.find(fire_mode)
		fire_mode = int(current.fire_modes[(i + 1) % current.fire_modes.size()])


func is_knife() -> bool:
	return current != null and current.kind == WeaponData.Kind.KNIFE


func is_reloading() -> bool:
	return _reload_end > _t


## hozirgi tarqalish (radian): asos + to'plangan tarqalish, holatga ko'paytiriladi
func current_spread() -> float:
	if current == null or is_knife():
		return 0.0
	var m := 1.0
	var hs := Vector2(player.velocity.x, player.velocity.z).length()
	if not player.is_on_floor():
		m *= current.spread_air_mult
	elif player.crouching:
		m *= current.spread_crouch_mult
	elif hs > 3.0:
		m *= current.spread_walk_mult
	elif hs > 0.5:
		m *= current.spread_slow_mult
	m *= lerpf(1.0, current.ads_spread_multiplier, ads_amt)
	return clampf((current.base_spread + bloom) * m, 0.0, current.max_spread * current.spread_air_mult)


## o'q uzish (tugma, testlar va boshqalar uchun): qurol tayyor bo'lsa true
func fire() -> bool:
	if current == null or player.busy or _t < _equip_end or is_reloading() or _t < _next_shot:
		return false
	if is_knife():
		_next_shot = _t + current.melee_swing_time
		ch.fire()
		_hitscan(current.max_range, 0.0)
		return true
	if ammo <= 0:
		return false
	ammo -= 1
	shots_fired += 1
	_next_shot = _t + current.shot_interval()
	if _t - _last_shot_t > current.recoil_reset_time:
		_shot_idx = 0
	_last_shot_t = _t
	ch.fire()
	if player.body:
		player.body.fire()
	_shot.pitch_scale = randf_range(0.96, 1.04) * (1.3 if current.kind == WeaponData.Kind.PISTOL else 1.0)
	_shot.play()
	_flash.light_energy = 3.0
	var spread := 0.0 if no_spread else current_spread()
	last_shot = {"pellets": current.projectile_count, "hits": 0, "damage": 0.0}
	for i in current.projectile_count:
		var r := _hitscan(current.max_range, spread)
		if r.has("damage"):
			last_shot.hits += 1
			last_shot.damage += r.damage
	_apply_recoil()
	bloom = minf(bloom + current.spread_bloom_per_shot, current.max_spread)
	_shot_idx += 1
	return true


func _apply_recoil() -> void:
	var n: int = current.recoil_pattern_v.size()
	if n == 0:
		return
	var i := mini(_shot_idx, n - 1)
	var k: float = current.recoil_scale * lerpf(1.0, current.ads_recoil_multiplier, ads_amt)
	var h: float = current.recoil_pattern_h[mini(i, current.recoil_pattern_h.size() - 1)] if current.recoil_pattern_h.size() else \
		randf_range(current.recoil_random_h.x, current.recoil_random_h.y)
	var kick := Vector2(deg_to_rad(current.recoil_pattern_v[i] * k), deg_to_rad(h * k))
	player.cam.rotation.x = clampf(player.cam.rotation.x + kick.x, -1.45, 1.45)
	player.rotation.y -= kick.y
	_recoil += kick


## kameradan o'q: devor (1-qatlam) yoki tana zonasi (10-qatlam, Area3D). Tegsa — zarar, iz, HUD belgisi.
func _hitscan(max_range: float, spread: float) -> Dictionary:
	var cam: Camera3D = player.cam
	var from := cam.global_position
	var basis := cam.global_transform.basis
	var dir := -basis.z
	if spread > 0.0:
		var a := randf() * TAU
		var r := sqrt(randf()) * spread
		dir = (dir + basis.x * cos(a) * r + basis.y * sin(a) * r).normalized()
	var q := PhysicsRayQueryParameters3D.create(from, from + dir * max_range, RAY_MASK, [player.get_rid()])
	q.collide_with_areas = true
	var hit := player.get_world_3d().direct_space_state.intersect_ray(q)
	var end := from + dir * max_range
	var res := {}
	if not hit.is_empty():
		end = hit.position
		var col: Object = hit.collider
		if col is Area3D and col.has_meta("zone"):
			var zone: String = col.get_meta("zone")
			var owner_model = col.get_meta("owner_model")
			var rcv: Node = owner_model.receiver() if is_instance_valid(owner_model) else null
			var dist := from.distance_to(hit.position)
			var dmg: float = current.damage_at(dist, zone)
			var killed := false
			if rcv:
				killed = bool(rcv.take_hit(dmg, zone, player))
			res = {"zone": zone, "damage": dmg, "killed": killed, "distance": dist, "target": rcv}
			last_hit = res
			hit_confirmed.emit(zone, dmg, killed)
		else:
			res = {"zone": "world", "position": hit.position}
			_impact(hit.position, hit.normal)
	if not is_knife():
		_tracer(ch.muzzle_position(), end)
	return res


func _fx_parent() -> Node:
	return player.get_parent() if player.get_parent() else player


func _tracer(a: Vector3, b: Vector3) -> void:
	if DisplayServer.get_name() == "headless" or a.distance_to(b) < 1.0:
		return
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.012, 0.012, a.distance_to(b))
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(1.0, 0.85, 0.45)
	bm.material = m
	mi.mesh = bm
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_fx_parent().add_child(mi)
	mi.global_transform = Transform3D(Basis.looking_at(b - a, Vector3.UP if absf((b - a).normalized().y) < 0.99 else Vector3.RIGHT), (a + b) * 0.5)
	get_tree().create_timer(0.04).timeout.connect(mi.queue_free)


## devorga tegish izi: kichik qora low-poly bo'lak (ko'pi bilan 40 ta, eskisi o'chadi)
func _impact(p: Vector3, n: Vector3) -> void:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.05, 0.05, 0.012)
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.12, 0.1, 0.09)
	bm.material = m
	mi.mesh = bm
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_fx_parent().add_child(mi)
	mi.global_transform = Transform3D(Basis.looking_at(-n, Vector3.UP if absf(n.y) < 0.99 else Vector3.RIGHT), p + n * 0.006)
	_impacts.append(mi)
	while _impacts.size() > 40:
		var old = _impacts.pop_front()
		if is_instance_valid(old):
			old.queue_free()


func reload() -> void:
	if current == null or is_knife() or ammo >= current.magazine_size or reserve <= 0 or is_reloading():
		return
	ch.reload()
	if player.body:
		player.body.reload()
	_reload_snd.play()
	_reload_end = _t + (current.empty_reload_time if ammo == 0 else current.reload_time)


func _unhandled_input(event: InputEvent) -> void:
	if not player or not player.local_player or Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		return
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP or event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			var s: int = current.slot if current else 1
			s = wrapi(s + (1 if event.button_index == MOUSE_BUTTON_WHEEL_DOWN else -1), 1, 4)
			equip(s)


func _process(delta: float) -> void:
	_t += delta
	if player.team != _team:
		_team = player.team
		ch.load_model(_team)
		if current:
			ch.set_weapon(current.kind)
		_update_sound()
	if _reload_end > 0.0 and _t >= _reload_end:
		var need: int = mini(current.magazine_size - ammo, reserve)
		ammo += need
		reserve -= need
		_reload_end = -1.0
	var captured := Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
	if captured and not buy_menu.visible:
		for i in 3:
			if Input.is_action_just_pressed("weapon_%d" % (i + 1)):
				equip(i + 1)
		if Input.is_action_just_pressed("fire_mode"):
			cycle_mode()
		if Input.is_action_just_pressed("reload") or (ammo == 0 and not is_knife() and Input.is_action_just_pressed("fire")):
			reload()
		# o'q rejimi: avtomat — bosib turish; 3 talik — bir bosishda 3 o'q; bittalik — har bosishda bitta
		if current:
			if fire_mode == WeaponData.FireMode.AUTO and Input.is_action_pressed("fire"):
				fire()
			elif Input.is_action_just_pressed("fire"):
				if fire_mode == WeaponData.FireMode.BURST:
					_burst_left = current.burst_count
				else:
					fire()
	if _burst_left > 0 and _t >= _next_shot:
		if fire():
			_burst_left -= 1
			_next_shot = maxf(_next_shot, _t + current.burst_delay)
		elif ammo <= 0 or is_reloading():
			_burst_left = 0
	ads = force_ads or (captured and Input.is_action_pressed("aim"))
	var ads_on: bool = ads and current != null and current.ads_ready and not is_reloading() and _t >= _equip_end
	var sp: float = current.ads_transition_speed if current else 10.0
	ads_amt = lerpf(ads_amt, 1.0 if ads_on else 0.0, 1.0 - exp(-delta * sp))
	if current:
		player.cam.fov = _base_fov * lerpf(1.0, current.ads_fov_ratio, ads_amt)
		player.look_scale = lerpf(1.0, current.ads_sensitivity_multiplier, ads_amt)
		# tarqalish va tepki asta qaytadi (otish to'xtaganda)
		bloom *= exp(-current.spread_recovery_speed * 0.35 * delta)
		if _t - _last_shot_t > current.shot_interval() * 1.5 and _recoil.length() > 0.00001:
			var back := _recoil * (1.0 - exp(-current.recoil_recovery_speed * delta))
			player.cam.rotation.x -= back.x
			player.rotation.y += back.y
			_recoil -= back
	_flash.light_energy = maxf(0.0, _flash.light_energy - delta * 60.0)
	# harakat -> animatsiya (o'yinchi fazosida: -Z oldinga)
	var v: Vector3 = player.global_transform.basis.inverse() * player.velocity
	ch.velocity_local = Vector3(-v.x, 0, -v.z)
	ch.crouching = player.crouching
	ch.on_floor = player.is_on_floor()
	ch.planting = player.busy
	# ko'z nuqtasi kameraga: sekin o'zgarishlar (o'tirish) to'liq qoplanadi, tez tebranish qoladi
	var e: Vector3 = ch.eye_point()
	_eye_s = e if _eye_s == Vector3.ZERO else _eye_s.lerp(e, 1.0 - exp(-delta * 4.0))
	var tn: Array = TUNE.get(_team, TUNE["T"])
	var off: Vector3 = tn[0]
	if current and ADS_TUNE.has(int(current.kind)):
		off = off.lerp(ADS_TUNE[int(current.kind)], ads_amt)
	# qadam tebranishi (tezlikka mos), sichqoncha kechikishi (burilishga teskari, silliq qaytadi); ADS da deyarli yo'q
	var hs := Vector2(player.velocity.x, player.velocity.z).length()
	var k := clampf(hs / 4.5, 0.0, 1.0) if player.is_on_floor() else 0.0
	_bob_t += delta * (6.0 + 4.0 * k) * (1.0 if k > 0.05 else 0.3)
	var bob := Vector3(sin(_bob_t) * 0.006, -absf(cos(_bob_t)) * 0.007, 0.0) * (0.25 + k) * (1.0 - 0.8 * ads_amt)
	var look := Vector2(player.rotation.y, player.cam.rotation.x)
	var dl := look - _last_look
	_last_look = look
	if dl.length() < 0.5:
		_sway = (_sway + Vector2(dl.x, dl.y) * 0.8).clamp(Vector2(-0.06, -0.04), Vector2(0.06, 0.04))
	_sway = _sway.lerp(Vector2.ZERO, 1.0 - exp(-delta * 8.0))
	var yaw := deg_to_rad(tn[1]) * (1.0 - ads_amt)
	var r := Basis(Vector3.UP, yaw + _sway.x) * Basis(Vector3.RIGHT, deg_to_rad(tn[2]) + _sway.y)
	var b := (r * Basis(Vector3.UP, PI)).scaled(Vector3.ONE * SCALE)
	ch.transform = Transform3D(b, -(b * _eye_s) + (off + bob) * SCALE)
	if current:
		if is_knife():
			_label.text = current.weapon_name
		else:
			var mode: String = MODE_NAMES[fire_mode] if current.fire_modes.size() > 1 else current.category_name
			_label.text = "%s  %s   %d / %d" % [current.weapon_name, mode, ammo, reserve]
	# 1-shaxs faqat o'yinchining o'z kamerasi faol bo'lganda (boshqa kamerada o'yinchi 3-shaxs tana bo'lib ko'rinadi)
	_label.visible = player.cam.current
	hud.visible = player.cam.current
	ch.visible = player.cam.current and not scoped()
