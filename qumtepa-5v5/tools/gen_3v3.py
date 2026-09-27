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


def patch_game_mode(path):
    """gen_godot5.patch_game_mode bilan bir xil (o'lgan o'yinchi bomba bilan ishlamaydi)"""
    g = open(path).read()
    for a, b in (('return phase == Phase.LIVE and player.team == "T" and player.has_bomb',
                  'return player.alive and phase == Phase.LIVE and player.team == "T" and player.has_bomb'),
                 ('return phase == Phase.PLANTED and player.team == "CT" and bomb != null',
                  'return player.alive and phase == Phase.PLANTED and player.team == "CT" and bomb != null'),
                 ('if bomb_state != "dropped" or bomb == null or player.team != "T" or _pickup_cooldown > 0.0:',
                  'if bomb_state != "dropped" or bomb == null or player.team != "T" or not player.alive or _pickup_cooldown > 0.0:')):
        assert a in g, a
        g = g.replace(a, b)
    open(path, "w").write(g)


def fix_arches(t):
    """ravoq ustidagi 5 bo'lakli to'qnashuv (build.py: pastki qirra = bo'lak o'rtasidagi egri nuqta) ravoq ochig'iga
    pog'ona bo'lib chiqib turardi (o'q/granata ko'rinmas narsaga urilardi). Har bo'lakning pastki qirrasi o'rtaga
    qarab qo'shni bo'lakniki bilan tenglashtiriladi — to'qnashuv egri chiziqdan pastga tushmaydi."""
    sizes = {m.group(1): [float(v) for v in m.group(2).split(",")]
             for m in re.finditer(r'\[sub_resource type="BoxShape3D" id="([^"]+)"\]\nsize = Vector3\(([^)]*)\)', t)}
    nodes = []
    for m in re.finditer(r'(\[node name="[^"]+" type="CollisionShape3D" parent="[^"]+"\]\ntransform = Transform3D\(1, 0, 0, 0, 1, 0, 0, 0, 1, ([^)]*)\)\nshape = SubResource\("([^"]+)"\))', t):
        c = [float(v) for v in m.group(2).split(",")]
        sz = sizes.get(m.group(3))
        if sz:
            nodes.append({"text": m.group(1), "c": c, "s": sz, "id": m.group(3)})
    def lo(n, a): return n["c"][a] - n["s"][a] / 2
    def hi(n, a): return n["c"][a] + n["s"][a] / 2
    cand = [n for n in nodes if lo(n, 1) > 2.0 and n["s"][1] < 4.0]
    fixed = 0
    for ax in (0, 2):
        other = 2 - ax
        rows = {}
        for n in cand:
            key = (round(n["c"][other], 3), round(n["s"][other], 3), round(hi(n, 1), 3))
            rows.setdefault(key, []).append(n)
        for row in rows.values():
            row.sort(key=lambda n: n["c"][ax])
            i = 0
            while i + 5 <= len(row):
                g = row[i:i + 5]
                cont = all(abs(hi(g[k], ax) - lo(g[k + 1], ax)) < 1e-3 for k in range(4))
                ys = [lo(n, 1) for n in g]
                if cont and ys[2] >= max(ys) - 1e-6 and ys[0] < ys[2] and abs(ys[0] - ys[4]) < 1e-3:
                    newy = [max(ys[0], ys[1]), max(ys[1], ys[2]), ys[2], max(ys[3], ys[2]), max(ys[4], ys[3])]
                    for n, y0 in zip(g, newy):
                        if y0 > lo(n, 1) + 1e-6:
                            top = hi(n, 1)
                            n["s"][1] = top - y0
                            n["c"][1] = (top + y0) / 2
                            n["fix"] = True
                            fixed += 1
                    i += 5
                else:
                    i += 1
    # egilgan palma tanalari: to'qnashuv 6 m tik quti, vizual tana yuqorida egiladi -> 2.6 m gacha (o'yinchi yetadigan qism)
    palms = 0
    for n in nodes:
        if abs(n["s"][0] - 0.44) < 1e-3 and abs(n["s"][2] - 0.44) < 1e-3 and n["s"][1] > 5.0 and lo(n, 1) < 0.1:
            y0 = lo(n, 1)
            n["s"][1] = 2.6 - y0
            n["c"][1] = y0 + n["s"][1] / 2
            n["fix"] = True
            palms += 1
    # qum qoplari: to'qnashuv qutisi qoplardan uchlarida 0.3 m uzun edi (ko'rinmas to'siq) -> qoplar uzunligiga qisqartiriladi
    bags = 0
    for n in nodes:
        if abs(n["s"][1] - 0.78) < 1e-3 and lo(n, 1) < 0.01 and "World_cloth" in n["text"]:
            ax = 0 if n["s"][0] > n["s"][2] else 2
            if n["s"][ax] > 1.0:
                n["s"][ax] -= 0.5
                n["fix"] = True
                bags += 1
    print(f"3v3: qum qoplari to'qnashuvi qisqartirildi — {bags} ta")
    for n in nodes:
        if n.get("fix"):
            old_sub = re.search(rf'\[sub_resource type="BoxShape3D" id="{n["id"]}"\]\nsize = Vector3\([^)]*\)', t).group(0)
            t = t.replace(old_sub, f'[sub_resource type="BoxShape3D" id="{n["id"]}"]\nsize = Vector3({n["s"][0]:g}, {n["s"][1]:.4f}, {n["s"][2]:g})')
            new_text = re.sub(r"Transform3D\(1, 0, 0, 0, 1, 0, 0, 0, 1, [^)]*\)",
                              f"Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, {n['c'][0]:g}, {n['c'][1]:.4f}, {n['c'][2]:g})", n["text"])
            t = t.replace(n["text"], new_text)
    print(f"3v3: ravoq to'qnashuvi tuzatildi — {fixed} ta bo'lak; egilgan palma tanasi — {palms} ta")
    return t


def fix_lighting(t):
    """3v3 da yurganda ekran qorayishi va ortiqcha yorug'lik:
    - ReflectionProbe'lar (spawn, mid, tunnel...) interior + ambient_mode=1 (o'z rangi, 0.5) edi: ichkariga kirganda atrof
      yorug'ligi 2.6 dan ~0.3 ga tushib, ekran keskin qorayardi -> ambient_mode=0 (muhit yorug'ligi), soyasiz aks;
    - atrof yorug'ligi 2.6 va tonemap_white 1.0 — Forward+ da oqarib ketadi -> 1.15 va 4.0; yon/pastdan yorug'lik kamaytirildi;
    - 49 ta chiroq: uzoqda so'nadi (optimizatsiya)."""
    reps = [("ambient_mode = 1\n", "ambient_mode = 0\n"), ("enable_shadows = true\n", "enable_shadows = false\n"),
            ("ambient_light_energy = 2.6\n", "ambient_light_energy = 1.15\n"), ("tonemap_white = 1.0\n", "tonemap_white = 4.0\n"),
            ("omni_attenuation = 1.7\n", "omni_attenuation = 1.7\ndistance_fade_enabled = true\ndistance_fade_begin = 28.0\ndistance_fade_length = 6.0\n")]
    for a, b in reps:
        assert a in t, a
        t = t.replace(a, b)
    for name, e0, e1 in (("Fill", "1.15", "0.6"), ("Bounce", "0.85", "0.45")):
        i = t.index(f'[node name="{name}" type="DirectionalLight3D"')
        j = t.index("light_energy = ", i)
        k = t.index("\n", j)
        assert t[j:k] == f"light_energy = {e0}", t[j:k]
        t = t[:j] + f"light_energy = {e1}" + t[k:]
    return t


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
            open(dst, "w").write(fix_arches(fix_paths(open(os.path.join(SRC, "map", fn)).read())))
        else:
            shutil.copy(os.path.join(SRC, "map", fn), dst)
    for fn in AUDIO:
        shutil.copy(os.path.join(SRC, "audio", fn), os.path.join(DST, "audio", fn))
    # 3v3 botlar taktikasi (tools/godot_src/maps3v3/)
    shutil.copy(os.path.join(HERE, "godot_src", "maps3v3", "strategies_3v3.gd"), os.path.join(DST, "scripts", "strategies_3v3.gd"))
    for fn in SCRIPTS:
        t = fix_paths(open(os.path.join(SRC, "scripts", fn)).read())
        if fn == "graphics.gd":
            # SDFGI va hajmli tuman: harakatda yorug'lik kaskadlari qayta hisoblanadi — ekran qorayib-yorishadi
            for a in ("_env.sdfgi_enabled = high", "_env.volumetric_fog_enabled = high"):
                assert a in t, a
                t = t.replace(a, a.replace("= high", "= false   # ekran qorayishining sababi — o'chirilgan (gen_3v3.py)"))
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
        if fn == "game_mode.gd":
            patch_game_mode(os.path.join(DST, "scripts", fn))
    # xaritaning o'z testlari (52 ta) va auditi — 3v3 sahnasida
    for fn in ("run_tests.gd", "audit.gd"):
        t = fix_paths(open(os.path.join(SRC, "tests", fn)).read()).replace("res://main.tscn", "res://main_3v3.tscn")
        t = t.replace('ok(sp.size() == 5, "%s: 5 ta spawn nuqtasi" % team)', 'ok(sp.size() == 3, "%s: 3 ta spawn nuqtasi (3v3)" % team)')
        t = t.replace('main = load("res://main_3v3.tscn").instantiate()\n',
                      'main = load("res://main_3v3.tscn").instantiate()\n\tmain.get_node("Bots").enabled = false      # botlarsiz: xarita sinovi\n')
        assert 'get_node("Bots").enabled = false' in t
        open(os.path.join(DST, "tests", fn), "w").write(t)
    # sahna
    t = fix_paths(open(os.path.join(SRC, "main.tscn")).read())
    t = t.replace('bus = &"Ambience"', 'bus = &"Ambient"')
    t = fix_lighting(t)
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
                       '[ext_resource type="Script" path="res://scripts/practice.gd" id="21_pr"]\n\n'
                       '[ext_resource type="Script" path="res://scripts/bot_play.gd" id="22_bp"]\n')
            continue
        out.append(b)
    t = "\n".join(out).rstrip() + ('\n\n[node name="Practice" type="Node3D" parent="."]\nscript = ExtResource("21_pr")\n'
         '\n[node name="Bots" type="Node3D" parent="."]\nscript = ExtResource("22_bp")\nteam_size = 3\n'
         f'strategies_path = "{RES}/scripts/strategies_3v3.gd"\nmap_data_path = "{RES}/scripts/map_data.gd"\n')
    assert skip_player and "20_pl" in t
    open(os.path.join(GODOT, "main_3v3.tscn"), "w").write(t)
    spawns = {k: len(re.findall(rf'groups=\["spawn_{k}"\]', t)) for k in ("T", "CT")}
    print(f"3v3: {DST}, main_3v3.tscn, spawn T {spawns['T']} / CT {spawns['CT']}")


if __name__ == "__main__":
    main()
