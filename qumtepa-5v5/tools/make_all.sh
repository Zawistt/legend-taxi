#!/usr/bin/env bash
# Butun zanjir: 2D tahlil -> 3D geometriya -> Godot loyihasi -> NavMesh -> testlar.
# Ishlatish: GODOT=/yo'l/godot4 ./make_all.sh   (GODOT berilmasa, "godot" PATH dan olinadi)
set -euo pipefail
cd "$(dirname "$0")"
GODOT="${GODOT:-godot}"
python3 analyze5.py
python3 build5.py
rm -f ../godot/map/navmesh.res
# Godot GLB dan ajratib olgan eski teksturalarni o'chiramiz (aks holda materiallar aralashib ketadi)
rm -rf ../godot/.godot ../godot/map/qumtepa5v5_greybox_*.png ../godot/map/*.import
python3 gen_godot5.py
(cd ../godot && "$GODOT" --headless --import >/dev/null 2>&1 || true)
(cd ../godot && "$GODOT" --headless -s res://tools/bake_nav.gd 2>&1 | grep -i "poligon")
python3 gen_godot5.py
(cd ../godot && "$GODOT" --headless --fixed-fps 60 -s res://tests/run_tests.gd 2>&1 | grep -v "^$" | grep -v "mesh_get_surface_count\|Parameter \"m\"\|ObjectDB\|resources still in use\|at: " )
