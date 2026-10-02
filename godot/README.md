# Legend RTS – Terrain Foundation (Godot 4.4+)

Base terrain only: **no props, buildings, units, resources, trees, rocks or rivers.**

![RTS overview](../docs/preview/02_rts_overview_zones.png)

| | |
|---|---|
| Map | 2000 m × 2000 m, world X/Z ∈ [-1000, 1000] |
| Heightmap | 513×513 float32 (3.9 m/cell), 0 – ~105 m |
| Chunks | 4×4 modular chunks (500 m, 128 cells each) |
| Factions | A base (-640, -640) · B base (+640, +640), perfectly flat plateaus at 22 m |
| Centre | open battlefield, r≈150 m flat/rolling, lowered between two high-ground masses |
| High ground | 4 flat-topped hills + two large uplands (yellow in zone view) |
| Valleys | 2 shallow flank valleys (purple), reachable by gentle slopes |
| Slopes | playable area max ≈ 19°, p95 ≈ 12° (nav agent limit 35°); rim ≤ ~28° keeps units inside |

## Run
Open `godot/` in Godot 4.4+, press F5. WASD/edge pan, Q/E or MMB rotate, wheel zoom, **Z** toggles the zone overlay
(blue = buildable, yellow = high ground, purple = valley).

## Layout
- `terrain_data/` – baked data: `heightmap.bin`, `heightmap16.png`, `zonemap.png` (R buildable, G high ground, B valley, A playable), `terrain_meta.json`
- `scripts/terrain/terrain_data.gd` – height/normal/slope + `is_buildable/is_high_ground/is_valley/is_playable` queries
- `scripts/terrain/terrain_manager.gd` – chunk meshes, LODs, collision, per-chunk `NavigationRegion3D`
- `shaders/terrain.gdshader` – procedural grass/dry grass/dirt/rock by slope+height (no textures needed yet)
- `scripts/camera/rts_camera.gd` – RTS camera rig, `scripts/main.gd` – sun, fog, sky
- `../tools/generate_terrain.py` – deterministic generator (`pip install numpy scipy pillow`); re-run to change the layout

## Performance design
- 3 LODs per chunk (128², 64², 32² quads) via visibility ranges with fade; skirts hide LOD cracks; only LOD0 casts shadows.
- Full map ≈ 16 chunks × 33 k tris at LOD0; typical RTS view draws ~3–5 chunks at LOD0/1.
- One `HeightMapShape3D` per chunk (7.8 m samples, layer 1 "terrain") – no trimesh collision.
- Depth fog + aerial perspective only (no volumetric fog), works on Forward+, Mobile and Compatibility.

## Navigation
`terrain.bake_navigation()` bakes one `NavigationMesh` tile per chunk (cell 1.0 m, agent radius 2 m, max slope 35°).
Project settings already match (`navigation/3d/default_cell_size=1.0`, `default_cell_height=0.5`).
Validate headless (also reports a path between the two bases):

    godot --headless --path godot --script res://scripts/terrain/bake_navigation.gd

Verified on Godot 4.4.1: 16 regions, path base A → base B = 1895 m across chunk borders.
`scripts/terrain/capture_preview.gd` renders engine screenshots (needs a GL context, e.g. `xvfb-run`).

## Preview images
`docs/preview/` were rendered with three.js from the same heightmap/zonemap (stand-in render, not the Godot shader).
