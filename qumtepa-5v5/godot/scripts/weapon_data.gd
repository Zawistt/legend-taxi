extends Resource
## Qurol ma'lumotlari (Legend Tactical FPS loyihasidagi LegendWeaponData asosida, Qumtepa uchun soddalashtirilgan).
## Hamma ko'rsatkichlar shu yerda — o'yin kodida qurol raqamlari yozilmaydi. Godot inspektorida tahrirlash mumkin.
## Birliklar: tarqalish — radian; tepki naqshi — gradus (har o'q uchun: v — tepaga, h — o'ngga).

enum Kind { RIFLE, PISTOL, KNIFE, SMG, SNIPER, SHOTGUN, MG, GRENADE, ZEUS, C4 }
enum FireMode { SEMI, BURST, AUTO }

@export_group("Nomi")
@export var weapon_id := "lar_01"
@export var weapon_name := "LAR-01"
@export var kind: Kind = Kind.RIFLE
@export var slot := 1                             ## 1 — asosiy, 2 — to'pponcha, 3 — pichoq
@export var category_name := "Avtomat"           ## sotib olish menyusida
@export var buy_category := "rifle"               ## pistol / smg / rifle / heavy (sotib olish menyusidagi bo'lim)
@export var side := "both"                        ## T / CT / both — kim sotib ola oladi (CS2 dagidek)
@export var price := 2700
@export var kill_reward := 300                    ## shu qurol bilan o'ldirgani uchun pul
@export var move_speed := 1.0                     ## ma'lumot (CS2 dagi tezlik ko'paytuvchisi)
@export var origin := "cs2"                        ## cs2 — o'yinda sotiladi; zaxira — eski (Legend) qurollar; pubg — PUBG Mobile (faqat inventarda)

@export_group("Zarar")
@export var base_damage := 34.0
@export var headshot_multiplier := 2.5
@export var arm_multiplier := 0.85
@export var legshot_multiplier := 0.85
@export var effective_range := 55.0               ## shundan uzoqda zarar kamayadi (o'q baribir uchadi)
@export var damage_falloff_multiplier := 0.65     ## effective_range dan uzoqda zarar shu songa ko'paytiriladi
@export var max_range := 200.0
@export var projectile_count := 1                 ## bir otishdagi o'qlar (drobovik — 8 ta sochma)
## CS2 zarar modeli (range_modifier > 0 bo'lsa): zarar = asos × range_modifier^(masofa / 12.7 m) × zona,
## zona: bosh ×headshot (4), qorin ×1.25, oyoq ×0.75; zirh: tana/qo'l/qorin (kaska bo'lsa bosh ham) — armor_pen ulushi o'tadi
@export var range_modifier := 0.0
@export var stomach_multiplier := 1.25
@export var armor_pen := 0.775

@export_group("Otish")
@export var fire_rate := 600.0                    ## o'q/daqiqa
@export var fire_modes: Array[FireMode] = [FireMode.AUTO, FireMode.BURST, FireMode.SEMI]
@export var burst_count := 3
@export var burst_delay := 0.075
@export var magazine_size := 30
@export var reserve_ammo := 90
@export var reload_time := 2.2
@export var empty_reload_time := 2.85
@export var melee_swing_time := 0.35              ## pichoq: zarbalar orasidagi vaqt
@export var bolt_cycle_time := 0.0                ## snayper/drobovik: har o'qdan keyin zatvor (o'q oralig'idan uzun bo'lsa)

@export_group("Tepki")
@export var recoil_pattern_v := PackedFloat32Array([1.2, 1.35, 1.45, 1.55, 1.6, 1.65, 1.7, 1.75, 1.8, 1.85, 1.8, 1.75])
@export var recoil_pattern_h := PackedFloat32Array([0, 0.2, -0.25, 0.35, -0.4, 0.45, -0.5, 0.55, -0.6, 0.6, -0.55, 0.5])
@export var recoil_scale := 0.4                   ## naqsh qiymati × shu = gradus
@export var recoil_random_h := Vector2.ZERO       ## naqsh o'rniga: gorizontal tepki [min, max] oralig'ida tasodifiy (AR-44)
@export var recoil_reset_time := 0.22             ## shuncha vaqt otilmasa, naqsh boshidan boshlanadi
@export var recoil_recovery_speed := 8.5          ## otish to'xtaganda nishon joyiga qaytish tezligi

@export_group("Tarqalish")
@export var base_spread := 0.012
@export var spread_bloom_per_shot := 0.006
@export var max_spread := 0.055
@export var spread_recovery_speed := 12.0
@export var spread_walk_mult := 1.6               ## oddiy harakat (4.5 m/s)
@export var spread_slow_mult := 1.15              ## Shift bilan sekin yurish
@export var spread_crouch_mult := 0.7
@export var spread_air_mult := 3.5

@export_group("Nishonga olish (ADS)")
@export var ads_ready := true
@export var ads_fov_ratio := 0.77                 ## ADS FOV = oddiy FOV × shu
@export var ads_sensitivity_multiplier := 0.65
@export var ads_spread_multiplier := 0.35
@export var ads_recoil_multiplier := 0.75
@export var ads_transition_speed := 11.0
@export var scope := false                        ## snayper: ADS da optik nishon (qurol ko'rinmaydi, qora ramka)

@export_group("Almashtirish")
@export var equip_time := 0.55


func shot_interval() -> float:
	return maxf(60.0 / maxf(fire_rate, 1.0), bolt_cycle_time)


func zone_multiplier(zone: String) -> float:
	match zone:
		"head":
			return headshot_multiplier
		"arm":
			return arm_multiplier
		"leg":
			return legshot_multiplier
		"stomach":
			return stomach_multiplier if range_modifier > 0.0 else 1.0      # Legend qurollarida qorin — tana
	return 1.0


func damage_at(distance: float, zone: String) -> float:
	var d := base_damage * zone_multiplier(zone)
	if range_modifier > 0.0:
		return d * pow(range_modifier, distance / 12.7)
	if distance > effective_range:
		d *= damage_falloff_multiplier
	return d


## zirhni hisobga olgan zarar: [sog'liqqa, zirhga] (CS2 formulasi: zirhga (zarar − sog'liqqa) × 0.5)
func damage_vs_armor(raw: float, zone: String, armor: float, helmet: bool) -> Array:
	var covered := armor > 0.0 and (zone != "leg") and (zone != "head" or helmet)
	if not covered:
		return [raw, 0.0]
	var hp := raw * armor_pen
	var ad := (raw - hp) * 0.5
	if ad > armor:
		ad = armor
		hp = raw - armor * 2.0
	return [hp, ad]
