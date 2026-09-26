#!/usr/bin/env bash
# Butun zanjir: 2D tahlil -> 3D geometriya -> Godot loyihasi -> NavMesh -> testlar.
# Ishlatish: GODOT=/yo'l/godot4 ./make_all.sh   (GODOT berilmasa, "godot" PATH dan olinadi)
#           BOTS=360 ... — qo'shimcha ravishda 5v5 bot o'yinlari (~8 daqiqa)
set -euo pipefail
cd "$(dirname "$0")"
GODOT="${GODOT:-godot}"
python3 analyze5.py
python3 audio5.py
STYLE=greybox python3 build5.py
STYLE=arch python3 build5.py
rm -f ../godot/map/navmesh.res
# Godot GLB dan ajratib olgan eski teksturalarni o'chiramiz (aks holda materiallar aralashib ketadi)
rm -rf ../godot/.godot ../godot/map/*.png ../godot/map/*.import
python3 gen_godot5.py
(cd ../godot && "$GODOT" --headless --import >/dev/null 2>&1 || true)
(cd ../godot && "$GODOT" --headless -s res://tools/bake_nav.gd 2>&1 | grep -i "poligon")
python3 gen_godot5.py
(cd ../godot && "$GODOT" --headless --fixed-fps 60 -s res://tests/run_tests.gd 2>&1 | grep -v "^$" | grep -v "mesh_get_surface_count\|Parameter \"m\"\|ObjectDB\|resources still in use\|at: " )
# smoke lineup'lari (granata fizikasi)
(cd ../godot && "$GODOT" --headless -s res://tests/run_grenades.gd 2>&1 | grep "NATIJA\|XATO")
# skrinshotlar va ko'rinish tekshiruvi (ekran kerak: xvfb-run bo'lsa ishlatiladi). SHOTS=1 ./make_all.sh
if [ -n "${SHOTS:-}" ]; then
  (cd ../godot && xvfb-run -a -s "-screen 0 1600x900x24" "$GODOT" --rendering-method gl_compatibility --rendering-driver opengl3 -s res://tools/screenshots.gd 2>&1 | grep -c saqlandi)
  python3 check_shots.py | tail -1
fi
# 5v5 bot o'yinlari (uzoq: ~1.3 s / raund). BOTS=360 ./make_all.sh
if [ -n "${BOTS:-}" ]; then
  (cd ../godot && "$GODOT" --headless --fixed-fps 60 -s res://tests/run_bots.gd -- "$BOTS" 1 2>&1 | grep -v "mesh_get_surface\|Parameter \"m\"\|^$\|at: ")
  python3 report_bots.py
fi
