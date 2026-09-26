"""3v3 xaritasi: foydalanuvchi bergan Qumtepa v2 low-poly loyihasini (50×50 m) 5v5 Godot loyihasiga ikkinchi xarita qilib qo'shadi.

Manba: maps_src/qumtepa3v3/ (foydalanuvchining qumtepa_lowpoly.zip — o'zgartirilmagan nusxa).
Natija: godot/maps/qumtepa3v3/ (xarita, to'qnashuv, NavMesh, skriptlar, tovushlar) va godot/main_3v3.tscn.

O'zgartirishlar (faqat nusxada):
  - res:// yo'llari maps/qumtepa3v3/ ga ko'chiriladi (5v5 skriptlari bilan to'qnashmaydi);
  - o'yinchi — 5v5 dagi scenes/player.tscn (qurol tizimi, 1-/3-shaxs, o'q zonalari);
  - 3v3: har jamoaga 3 ta spawn (T4, T5, CT4, CT5 olib tashlanadi);
  - F7 mashq nishonlari (scripts/practice.gd); sotib olish — scripts/buy_menu.gd;
  - tovush shinalari 5v5 nomlariga: Interior -> Reverb, Ambience -> Ambient.
Ishlatish: python3 gen_3v3.py   (make_all.sh buni avtomatik chaqiradi)
"""
import os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "maps_src", "qumtepa3v3")
GODOT = os.path.join(HERE, "..", "godot")
DST = os.path.join(GODOT, "maps", "qumtepa3v3")
RES = "res://maps/qumtepa3v3"
SCRIPTS = ("map_data.gd", "game_mode.gd", "hud.gd", "graphics.gd", "audio_zones.gd", "input_setup.gd")
AUDIO = ("amb_wind.wav", "amb_town.wav", "amb_bird.wav")
DROP_SPAWNS = ("T4", "T5", "CT4", "CT5")


def fix_paths(t):
    for fn in SCRIPTS:
        t = t.replace(f"res://scripts/{fn}", f"{RES}/scripts/{fn}")
    for fn in AUDIO:
        t = t.replace(f"res://audio/{fn}", f"{RES}/audio/{fn}")
    return t.replace("res://map/", f"{RES}/map/")


def main():
    for d in ("map", "scripts", "audio", "tests"):
        os.makedirs(os.path.join(DST, d), exist_ok=True)
    for fn in ("desert_map.glb", "collision.tscn", "navmesh.res"):
        dst = os.path.join(DST, "map", fn)
        if fn.endswith(".tscn"):
            open(dst, "w").write(fix_paths(open(os.path.join(SRC, "map", fn)).read()))
        else:
            shutil.copy(os.path.join(SRC, "map", fn), dst)
    for fn in AUDIO:
        shutil.copy(os.path.join(SRC, "audio", fn), os.path.join(DST, "audio", fn))
    for fn in SCRIPTS:
        t = fix_paths(open(os.path.join(SRC, "scripts", fn)).read())
        if fn == "audio_zones.gd":
            t = t.replace('const INSIDE_BUS := "Interior"', 'const INSIDE_BUS := "Reverb"')
        if fn == "hud.gd":
            old = "buy_panel.visible = _buy_open and can_buy"
            assert old in t
            t = t.replace(old, "buy_panel.visible = false   # sotib olish menyusi — scripts/buy_menu.gd")
            t = t.replace("F3 — raund   F4 — grafika sifati\"",
                          "F3 — raund   F4 — grafika sifati   F7 — mashq nishonlari\\n"
                          "Shift — sekin yurish (jim)   Ctrl/C — o'tirish   Space — sakrash   Sichqoncha — o'q, o'ng tugma — nishonga olish\\n"
                          "1/2/3 — asosiy qurol / to'pponcha / pichoq   R — qayta o'qlash   X — o'q rejimi   B — sotib olish (5 ta qurol)\"")
            assert "F7 — mashq" in t
        open(os.path.join(DST, "scripts", fn), "w").write(t)
    # xaritaning o'z testlari (52 ta) va auditi — 3v3 sahnasida
    for fn in ("run_tests.gd", "audit.gd"):
        t = fix_paths(open(os.path.join(SRC, "tests", fn)).read()).replace("res://main.tscn", "res://main_3v3.tscn")
        t = t.replace('ok(sp.size() == 5, "%s: 5 ta spawn nuqtasi" % team)', 'ok(sp.size() == 3, "%s: 3 ta spawn nuqtasi (3v3)" % team)')
        open(os.path.join(DST, "tests", fn), "w").write(t)
    # sahna
    t = fix_paths(open(os.path.join(SRC, "main.tscn")).read())
    t = t.replace('bus = &"Ambience"', 'bus = &"Ambient"')
    blocks = re.split(r"\n(?=\[)", t)
    out = []
    skip_player = False
    for b in blocks:
        head = b.split("\n", 1)[0]
        m = re.match(r'\[node name="([^"]+)" type="[^"]+" parent="([^"]+)"', head) or re.match(r'\[node name="([^"]+)" parent="([^"]+)"', head)
        if m:
            name, parent = m.groups()
            if parent == "Spawns" and name in DROP_SPAWNS or parent.split("/")[-1] in DROP_SPAWNS and parent.startswith("Spawns/"):
                continue
            if name == "Player" and parent == ".":
                xf = re.search(r"transform = (Transform3D\([^)]*\))", b).group(1)
                out.append(f'[node name="Player" parent="." instance=ExtResource("20_pl")]\ntransform = {xf}\n')
                skip_player = True
                continue
            if parent == "Player":
                continue
        if head.startswith('[ext_resource type="Script" path="res://scripts/player.gd"'):
            out.append('[ext_resource type="PackedScene" path="res://scenes/player.tscn" id="20_pl"]\n\n'
                       '[ext_resource type="Script" path="res://scripts/practice.gd" id="21_pr"]\n')
            continue
        out.append(b)
    t = "\n".join(out).rstrip() + '\n\n[node name="Practice" type="Node3D" parent="."]\nscript = ExtResource("21_pr")\n'
    assert skip_player and "20_pl" in t
    open(os.path.join(GODOT, "main_3v3.tscn"), "w").write(t)
    spawns = {k: len(re.findall(rf'groups=\["spawn_{k}"\]', t)) for k in ("T", "CT")}
    print(f"3v3: {DST}, main_3v3.tscn, spawn T {spawns['T']} / CT {spawns['CT']}")


if __name__ == "__main__":
    main()
