extends Resource
## Qurol ma'lumotlari (Legend Tactical FPS loyihasidagi LegendWeaponData asosida, Qumtepa uchun soddalashtirilgan).
## Hamma ko'rsatkichlar shu yerda — o'yin kodida qurol raqamlari yozilmaydi. Godot inspektorida tahrirlash mumkin.
## Birliklar: tarqalish — radian; tepki naqshi — gradus (har o'q uchun: v — tepaga, h — o'ngga).

enum Kind { RIFLE, PISTOL, KNIFE }
enum FireMode { SEMI, BURST, AUTO }

@export_group("Nomi")
@export var weapon_id := "lar_01"
@export var weapon_name := "LAR-01"
@export var kind: Kind = Kind.RIFLE
@export var slot := 1                             ## 1 — asosiy, 2 — to'pponcha, 3 — pichoq

@export_group("Zarar")
@export var base_damage := 34.0
@export var headshot_multiplier := 2.5
@export var arm_multiplier := 0.85
@export var legshot_multiplier := 0.85
@export var effective_range := 55.0               ## shundan uzoqda zarar kamayadi (o'q baribir uchadi)
@export var damage_falloff_multiplier := 0.65     ## effective_range dan uzoqda zarar shu songa ko'paytiriladi
@export var max_range := 200.0

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

@export_group("Tepki")
@export var recoil_pattern_v := PackedFloat32Array([1.2, 1.35, 1.45, 1.55, 1.6, 1.65, 1.7, 1.75, 1.8, 1.85, 1.8, 1.75])
@export var recoil_pattern_h := PackedFloat32Array([0, 0.2, -0.25, 0.35, -0.4, 0.45, -0.5, 0.55, -0.6, 0.6, -0.55, 0.5])
@export var recoil_scale := 0.4                   ## naqsh qiymati × shu = gradus
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

@export_group("Almashtirish")
@export var equip_time := 0.55


func shot_interval() -> float:
	return 60.0 / maxf(fire_rate, 1.0)


func zone_multiplier(zone: String) -> float:
	match zone:
		"head":
			return headshot_multiplier
		"arm":
			return arm_multiplier
		"leg":
			return legshot_multiplier
	return 1.0


func damage_at(distance: float, zone: String) -> float:
	var d := base_damage * zone_multiplier(zone)
	if distance > effective_range:
		d *= damage_falloff_multiplier
	return d
