"""CS2 uslubidagi qurollar ro'yxati -> godot_src/weapons/*.tres (weapon_data.gd resurslari).
Raqamlar CS2 ga yaqin: zarar, zirh teshish, o'q/daqiqa, magazin/zaxira, narx, o'ldirish mukofoti, masofa ko'paytuvchisi,
tezlik (250 = 1.0). Bosh ×4, qorin ×1.25, oyoq ×0.75 (CS2). Tarqalish (radian) va tepki naqshi — o'yin uchun moslangan.
Legend Tactical FPS qurollari (rifle, vanguard, smg, sniper, shotgun, pistol, knife) saqlanadi — ularga narx/tomon qo'shiladi.
Ishlatish: python3 gen_weapons.py  (gen_godot5.py weapons/ ni Godot loyihasiga ko'chiradi)"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "godot_src", "weapons")
KIND = {"rifle": 0, "pistol": 1, "smg": 3, "sniper": 4, "shotgun": 5, "mg": 6}
HEAD = """[gd_resource type="Resource" load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/weapon_data.gd" id="1"]

[resource]
script = ExtResource("1")
"""
AK_V = [1.5, 1.9, 2.3, 2.6, 2.7, 2.5, 2.2, 1.8, 1.4, 1.0, 0.8, 0.6, 0.5, 0.4, 0.4, 0.3, 0.3, 0.3, 0.3, 0.3]
AK_H = [0, 0.1, 0.25, 0.4, 0.2, -0.5, -1.2, -1.7, -1.9, -1.4, -0.6, 0.6, 1.6, 2.1, 1.8, 0.8, -0.8, -1.6, -1.2, 0.5]
M4_V = [1.2, 1.5, 1.8, 2.0, 2.1, 2.0, 1.8, 1.5, 1.2, 0.9, 0.7, 0.5, 0.4, 0.4, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3]
M4_H = [0, -0.1, 0.2, 0.35, 0.1, -0.4, -0.9, -1.3, -1.4, -1.0, -0.3, 0.6, 1.3, 1.6, 1.2, 0.4, -0.6, -1.2, -0.8, 0.4]
SMG_V = [1.0, 1.2, 1.35, 1.45, 1.5, 1.4, 1.2, 1.0, 0.8, 0.6, 0.5, 0.4, 0.4, 0.3, 0.3]
SMG_H = [0, 0.15, -0.2, 0.3, -0.35, 0.4, -0.5, 0.6, -0.6, 0.5, -0.4, 0.3, -0.3, 0.3, -0.3]
PIS_V = [1.4, 1.7, 2.0, 2.2, 2.3, 2.3]
PIS_H = [0, 0.2, -0.25, 0.3, -0.3, 0.3]
# id, nom, sinf, tomon, narx, mukofot, zarar, bosh, zirh%, o'q/daq, magazin, zaxira, qayta o'qlash, masofa, tezlik,
#   tarqalish, yurishda ×, rejimlar, tepki (v,h), qo'shimcha
W = [
    ("glock", "Glock-18", "pistol", "T", 200, 300, 30, 4.0, 0.47, 400, 20, 120, 2.3, 0.85, 0.96, 0.012, 3.0, [0, 1], (PIS_V, PIS_H), {}),
    ("usp", "USP-S", "pistol", "CT", 200, 300, 35, 4.0, 0.505, 352, 12, 24, 2.2, 0.91, 0.96, 0.009, 3.0, [0], (PIS_V, PIS_H), {}),
    ("p250", "P250", "pistol", "both", 300, 300, 38, 4.0, 0.64, 400, 13, 26, 2.2, 0.85, 0.96, 0.012, 3.2, [0], (PIS_V, PIS_H), {}),
    ("tec9", "Tec-9", "pistol", "T", 500, 300, 33, 4.0, 0.906, 500, 18, 90, 2.5, 0.83, 0.96, 0.014, 2.6, [0], (PIS_V, PIS_H), {}),
    ("fiveseven", "Five-SeveN", "pistol", "CT", 500, 300, 32, 4.0, 0.911, 400, 20, 100, 2.2, 0.81, 0.96, 0.011, 2.8, [0], (PIS_V, PIS_H), {}),
    ("deagle", "Desert Eagle", "pistol", "both", 700, 300, 53, 4.0, 0.932, 267, 7, 35, 2.2, 0.81, 0.92, 0.008, 4.5, [0], ([3.2, 3.6, 3.8, 4.0], [0, 0.6, -0.6, 0.8]), {}),
    ("mac10", "MAC-10", "smg", "T", 1050, 600, 29, 4.0, 0.575, 800, 30, 100, 2.6, 0.8, 0.96, 0.016, 2.0, [2], (SMG_V, SMG_H), {}),
    ("mp9", "MP9", "smg", "CT", 1250, 600, 26, 4.0, 0.6, 857, 30, 120, 2.1, 0.87, 0.96, 0.014, 2.0, [2], (SMG_V, SMG_H), {}),
    ("ump45", "UMP-45", "smg", "both", 1200, 600, 35, 4.0, 0.65, 666, 25, 100, 3.5, 0.75, 0.92, 0.015, 2.2, [2], (SMG_V, SMG_H), {}),
    ("p90", "P90", "smg", "both", 2350, 300, 26, 4.0, 0.69, 857, 50, 100, 3.3, 0.86, 0.92, 0.015, 2.2, [2], (SMG_V, SMG_H), {}),
    ("galil", "Galil AR", "rifle", "T", 1800, 300, 30, 4.0, 0.775, 666, 35, 90, 3.0, 0.98, 0.86, 0.008, 7.0, [2], (M4_V, M4_H), {}),
    ("famas", "FAMAS", "rifle", "CT", 2050, 300, 30, 4.0, 0.7, 666, 25, 90, 3.3, 0.96, 0.88, 0.008, 7.0, [2, 1], (M4_V, M4_H), {}),
    ("ak47", "AK-47", "rifle", "T", 2700, 300, 36, 4.0, 0.775, 600, 30, 90, 2.5, 0.98, 0.86, 0.007, 8.0, [2], (AK_V, AK_H), {}),
    ("m4a4", "M4A4", "rifle", "CT", 3100, 300, 33, 4.0, 0.7, 666, 30, 90, 3.1, 0.97, 0.9, 0.006, 8.0, [2], (M4_V, M4_H), {}),
    ("ssg08", "SSG 08", "sniper", "both", 1700, 300, 88, 4.0, 0.85, 48, 10, 90, 3.7, 0.98, 0.92, 0.05, 1.6, [0], ([3.0], [0]),
     {"scope": "true", "ads_fov_ratio": 0.44, "ads_spread_multiplier": 0.04, "ads_sensitivity_multiplier": 0.44, "bolt_cycle_time": 1.25}),
    ("awp", "AWP", "sniper", "both", 4750, 100, 115, 4.0, 0.975, 41, 5, 30, 3.7, 0.99, 0.8, 0.08, 2.5, [0], ([5.0], [0]),
     {"scope": "true", "ads_fov_ratio": 0.4, "ads_spread_multiplier": 0.02, "ads_sensitivity_multiplier": 0.4, "bolt_cycle_time": 1.46}),
    ("nova", "Nova", "shotgun", "both", 1050, 900, 26, 4.0, 0.5, 68, 8, 32, 4.0, 0.7, 0.88, 0.05, 1.3, [0], ([3.0], [0]), {"projectile_count": 9}),
    ("xm1014", "XM1014", "shotgun", "both", 2000, 600, 20, 4.0, 0.8, 171, 7, 32, 4.0, 0.7, 0.86, 0.055, 1.3, [0], ([2.6], [0]), {"projectile_count": 6}),
    ("m249", "M249", "mg", "both", 5200, 300, 32, 4.0, 0.8, 750, 100, 200, 5.7, 0.97, 0.78, 0.012, 6.0, [2], (M4_V, M4_H), {}),    # CS2 ning qolgan qurollari (2024-2025 raqobat rejimi)
    ("p2000", "P2000", "pistol", "CT", 200, 300, 35, 4.0, 0.505, 352, 13, 52, 2.2, 0.91, 0.96, 0.010, 3.0, [0], (PIS_V, PIS_H), {}),
    ("elite", "Dual Berettas", "pistol", "both", 300, 300, 38, 4.0, 0.575, 500, 30, 120, 3.8, 0.79, 0.96, 0.014, 3.0, [0], (PIS_V, PIS_H), {}),
    ("cz75", "CZ75-Auto", "pistol", "both", 500, 100, 31, 4.0, 0.776, 600, 12, 12, 2.7, 0.85, 0.96, 0.013, 2.8, [2], (SMG_V, SMG_H), {}),
    ("revolver", "R8 Revolver", "pistol", "both", 600, 300, 86, 4.0, 0.932, 120, 8, 8, 2.3, 0.94, 0.9, 0.010, 4.5, [0], ([3.6, 3.9, 4.1, 4.3], [0, 0.6, -0.6, 0.8]), {}),
    ("mp7", "MP7", "smg", "both", 1500, 600, 29, 4.0, 0.625, 800, 30, 120, 3.1, 0.85, 0.88, 0.013, 2.0, [2], (SMG_V, SMG_H), {}),
    ("mp5sd", "MP5-SD", "smg", "both", 1500, 600, 27, 4.0, 0.625, 750, 30, 120, 3.0, 0.85, 0.94, 0.013, 2.0, [2], (SMG_V, SMG_H), {}),
    ("bizon", "PP-Bizon", "smg", "both", 1400, 600, 27, 4.0, 0.575, 750, 64, 120, 2.4, 0.8, 0.96, 0.016, 2.0, [2], (SMG_V, SMG_H), {}),
    ("m4a1s", "M4A1-S", "rifle", "CT", 2900, 300, 38, 4.0, 0.7, 600, 20, 80, 3.1, 0.99, 0.9, 0.005, 8.0, [2], (M4_V, M4_H), {}),
    ("sg553", "SG 553", "rifle", "T", 3000, 300, 30, 4.0, 1.0, 545, 30, 90, 2.8, 0.98, 0.84, 0.006, 8.0, [2], (AK_V, AK_H), {"ads_ready": "true", "ads_fov_ratio": 0.55, "ads_spread_multiplier": 0.55, "ads_sensitivity_multiplier": 0.6}),
    ("aug", "AUG", "rifle", "CT", 3300, 300, 28, 4.0, 0.9, 600, 30, 90, 3.8, 0.98, 0.88, 0.006, 8.0, [2], (M4_V, M4_H), {"ads_ready": "true", "ads_fov_ratio": 0.55, "ads_spread_multiplier": 0.55, "ads_sensitivity_multiplier": 0.6}),
    ("g3sg1", "G3SG1", "sniper", "T", 5000, 300, 80, 4.0, 0.825, 240, 20, 90, 4.7, 0.98, 0.86, 0.04, 2.5, [0], ([2.2], [0.3]), {"scope": "true", "ads_fov_ratio": 0.4, "ads_spread_multiplier": 0.05, "ads_sensitivity_multiplier": 0.45}),
    ("scar20", "SCAR-20", "sniper", "CT", 5000, 300, 80, 4.0, 0.825, 240, 20, 90, 3.1, 0.98, 0.86, 0.04, 2.5, [0], ([2.2], [-0.3]), {"scope": "true", "ads_fov_ratio": 0.4, "ads_spread_multiplier": 0.05, "ads_sensitivity_multiplier": 0.45}),
    ("sawedoff", "Sawed-Off", "shotgun", "T", 1100, 900, 32, 4.0, 0.75, 71, 7, 32, 4.0, 0.45, 0.84, 0.07, 1.3, [0], ([3.0], [0]), {"projectile_count": 8}),
    ("mag7", "MAG-7", "shotgun", "CT", 1300, 900, 30, 4.0, 0.75, 71, 5, 32, 2.5, 0.45, 0.9, 0.04, 1.3, [0], ([3.0], [0]), {"projectile_count": 8}),
    ("negev", "Negev", "mg", "both", 1700, 300, 35, 4.0, 0.71, 800, 150, 300, 5.7, 0.97, 0.78, 0.014, 6.0, [2], (SMG_V, SMG_H), {}),
]
# PUBG Mobile — eng mashhur 10 ta qurol (faqat inventarda: narxi yo'q, o'yinda sotilmaydi). Bosh ×2.35 (avtomat), ×2.5 (snayper)
PUBG = [
    ("pubg_m416", "M416", "rifle", 41, 2.35, 0.8, 700, 30, 120, 2.1, 0.975, 0.95, 0.006, 6.0, [2, 0], (M4_V, M4_H), {}),
    ("pubg_akm", "AKM", "rifle", 47, 2.35, 0.8, 600, 30, 120, 2.4, 0.97, 0.93, 0.008, 7.0, [2, 0], (AK_V, AK_H), {}),
    ("pubg_m762", "M762", "rifle", 44, 2.35, 0.8, 700, 30, 120, 2.4, 0.97, 0.93, 0.008, 7.0, [2, 1, 0], (AK_V, AK_H), {}),
    ("pubg_scarl", "SCAR-L", "rifle", 41, 2.35, 0.8, 625, 30, 120, 2.2, 0.975, 0.95, 0.006, 6.0, [2, 0], (M4_V, M4_H), {}),
    ("pubg_groza", "Groza", "rifle", 47, 2.35, 0.8, 750, 30, 120, 3.0, 0.97, 0.93, 0.008, 7.0, [2, 0], (AK_V, AK_H), {}),
    ("pubg_awm", "AWM", "sniper", 105, 2.5, 1.0, 32, 5, 20, 4.2, 0.995, 0.85, 0.06, 2.5, [0], ([5.5], [0]), {**{"scope": "true", "ads_fov_ratio": 0.4, "ads_spread_multiplier": 0.05, "ads_sensitivity_multiplier": 0.45}, "bolt_cycle_time": 1.85}),
    ("pubg_kar98k", "Kar98k", "sniper", 79, 2.5, 0.9, 32, 5, 20, 4.0, 0.99, 0.9, 0.06, 2.5, [0], ([4.5], [0]), {**{"scope": "true", "ads_fov_ratio": 0.4, "ads_spread_multiplier": 0.05, "ads_sensitivity_multiplier": 0.45}, "bolt_cycle_time": 1.9}),
    ("pubg_ump45", "UMP45", "smg", 41, 2.1, 0.65, 650, 25, 100, 3.1, 0.88, 0.95, 0.012, 2.0, [2, 1, 0], (SMG_V, SMG_H), {}),
    ("pubg_vector", "Vector", "smg", 31, 2.1, 0.6, 1090, 25, 100, 2.2, 0.85, 0.96, 0.012, 2.0, [2, 1, 0], (SMG_V, SMG_H), {}),
    ("pubg_dp28", "DP-28", "mg", 51, 2.35, 0.85, 550, 47, 94, 4.4, 0.97, 0.85, 0.012, 6.0, [2], (M4_V, M4_H), {}),
]
CAT_NAME = {"pistol": "To'pponcha", "smg": "SMG", "rifle": "Avtomat", "sniper": "Snayper", "shotgun": "Drobovik", "mg": "Pulemyot"}
BUY_CAT = {"pistol": "pistol", "smg": "smg", "rifle": "rifle", "sniper": "rifle", "shotgun": "heavy", "mg": "heavy"}


def arr(v):
    return "PackedFloat32Array(" + ", ".join(f"{x:g}" for x in v) + ")"


def main():
    rows = [(r, "cs2") for r in W] + [((r[0], r[1], r[2], "both", 0, 0) + r[3:], "pubg") for r in PUBG]
    for (wid, name, cls, side, price, rew, dmg, hs, ap, rpm, mag, res, rel, rm, spd, spread, walk, modes, (rv, rh), extra), origin in rows:
        slot = 2 if cls == "pistol" else 1
        lines = [f'weapon_id = "{wid}"', f'weapon_name = "{name}"', f"kind = {KIND[cls]}", f"slot = {slot}",
                 f'category_name = "{CAT_NAME[cls]}"', f'buy_category = "{BUY_CAT[cls] if origin == "cs2" else ""}"', f'side = "{side}"',
                 f'origin = "{origin}"', f"price = {price}",
                 f"kill_reward = {rew}", f"move_speed = {spd}", f"base_damage = {float(dmg)}", f"headshot_multiplier = {hs}",
                 "arm_multiplier = 1.0", "legshot_multiplier = 0.75", "stomach_multiplier = 1.25", f"armor_pen = {ap}",
                 f"range_modifier = {rm}", "max_range = 250.0", f"fire_rate = {float(rpm)}", f"fire_modes = Array[int]({modes})",
                 f"magazine_size = {mag}", f"reserve_ammo = {res}", f"reload_time = {rel}", f"empty_reload_time = {rel + 0.4:.1f}",
                 f"recoil_pattern_v = {arr(rv)}", f"recoil_pattern_h = {arr(rh)}", "recoil_reset_time = 0.3",
                 f"base_spread = {spread}", f"spread_bloom_per_shot = {spread * 0.45:.4f}", f"max_spread = {spread * 6:.4f}",
                 f"spread_walk_mult = {walk}", f"spread_slow_mult = {max(1.3, walk * 0.35):.2f}", "spread_crouch_mult = 0.7",
                 f"spread_air_mult = {max(4.0, walk * 2.5):.1f}", f"equip_time = {0.9 if cls in ('sniper', 'mg') else 0.6}"]
        extra = dict(extra)
        if "scope" not in extra and "ads_ready" not in extra:
            lines.append("ads_ready = false")       # CS2: avtomat/to'pponchada nishonga olish (ADS) yo'q
        for k, v in extra.items():
            lines.append(f"{k} = {v}")
        open(os.path.join(OUT, f"{wid}.tres"), "w").write(HEAD + "\n".join(lines) + "\n")
    # Legend qurollari (o'zimiz yasagan) — sotib olish menyusidan olindi, "Zaxira" sifatida inventarda saqlanadi
    for fn in ("rifle", "vanguard", "smg", "sniper", "shotgun", "pistol"):
        p = os.path.join(OUT, f"{fn}.tres")
        t = open(p).read()
        keep = [l for l in t.rstrip().split("\n") if not l.split(" = ")[0] in ("buy_category", "side", "price", "kill_reward", "move_speed", "origin")]
        open(p, "w").write("\n".join(keep) + '\nbuy_category = ""\nside = "both"\nprice = 0\nkill_reward = 300\nmove_speed = 0.9\norigin = "zaxira"\n')
    kp = os.path.join(OUT, "knife.tres")
    t = open(kp).read()
    if "kill_reward" not in t:
        open(kp, "w").write(t.rstrip() + '\nbuy_category = ""\nprice = 0\nkill_reward = 1500\nmove_speed = 1.0\n')
    zp = os.path.join(OUT, "zeus.tres")
    open(zp, "w").write(HEAD + "\n".join([
        'weapon_id = "zeus"', 'weapon_name = "Zeus x27"', "kind = 8", "slot = 3", 'category_name = "Zeus"', 'buy_category = "gear"',
        'side = "both"', "price = 200", "kill_reward = 100", "move_speed = 0.88", "base_damage = 500.0", "headshot_multiplier = 1.0",
        "legshot_multiplier = 1.0", "armor_pen = 1.0", "effective_range = 4.6", "damage_falloff_multiplier = 0.0", "max_range = 4.6",
        "fire_rate = 30.0", "fire_modes = Array[int]([0])", "magazine_size = 1", "reserve_ammo = 0", "reload_time = 30.0",
        "empty_reload_time = 30.0", "recoil_pattern_v = PackedFloat32Array()", "recoil_pattern_h = PackedFloat32Array()",
        "base_spread = 0.0", "spread_bloom_per_shot = 0.0", "max_spread = 0.0", "ads_ready = false", "equip_time = 0.5"]) + "\n")
    print(f"{len(W)} ta CS2 quroli + Zeus, {len(PUBG)} ta PUBG Mobile quroli -> {OUT}")


if __name__ == "__main__":
    main()
