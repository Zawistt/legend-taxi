#!/usr/bin/env python3
"""Legend RTS - base terrain generator (2 km x 2 km).

Outputs (into godot/terrain_data/):
  heightmap.bin      float32 little-endian, GRID x GRID samples, metres (row = +Z, col = +X)
  heightmap16.png    16-bit preview/import copy (0..MAX_H metres mapped to 0..65535)
  zonemap.png        RGBA8 control map: R=buildable, G=high ground, B=valley, A=playable area
  terrain_meta.json  grid size, cell size, base positions, stats

World space: X/Z in [-1000, 1000], Y = height. Faction A base at (-640, -640),
faction B base at (+640, +640). Fully deterministic (fixed seed).
"""
import json
import os
import numpy as np
from scipy.ndimage import gaussian_filter, sobel
from PIL import Image

SIZE = 2000.0          # metres
CELLS = 512            # 4x4 chunks of 128 cells each
GRID = CELLS + 1       # vertices per side
CELL = SIZE / CELLS    # 3.906 m
MAX_H = 160.0
SEED = 20240611

OUT = os.path.join(os.path.dirname(__file__), "..", "godot", "terrain_data")
os.makedirs(OUT, exist_ok=True)

ax = np.linspace(-SIZE / 2, SIZE / 2, GRID)
X, Z = np.meshgrid(ax, ax)  # X varies along columns, Z along rows


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def blob(cx, cz, rx, rz, rot=0.0, power=2.0):
    """Smooth 0..1 bump with flat-ish top. power>2 => broader plateau."""
    c, s = np.cos(rot), np.sin(rot)
    dx, dz = X - cx, Z - cz
    u = (dx * c + dz * s) / rx
    v = (-dx * s + dz * c) / rz
    d = np.sqrt(u * u + v * v)
    return np.exp(-(d ** power))


def plateau(cx, cz, r_flat, r_blend, rx_scale=1.0):
    d = np.sqrt(((X - cx) / rx_scale) ** 2 + (Z - cz) ** 2)
    return 1.0 - smoothstep(r_flat, r_flat + r_blend, d)  # 1 inside flat area


rng = np.random.default_rng(SEED)


def fbm(wavelength, octaves=4, gain=0.5):
    out = np.zeros((GRID, GRID))
    amp, total = 1.0, 0.0
    wl = wavelength
    for _ in range(octaves):
        n = rng.standard_normal((GRID, GRID))
        sigma = wl / CELL / 2.2
        n = gaussian_filter(n, sigma, mode="reflect")
        n /= n.std() + 1e-9
        out += n * amp
        total += amp
        amp *= gain
        wl *= 0.5
    return out / total


# --- layout ---------------------------------------------------------------
BASE_A = (-640.0, -640.0)
BASE_B = (640.0, 640.0)
BASE_H = 22.0
CENTER_H = 12.0

# Large elevated areas (gentle rolling uplands) - flank + mid-field
h = np.full((GRID, GRID), 14.0)
h += 24 * blob(-600, 100, 360, 280, 0.4, 2.2)      # west upland
h += 24 * blob(600, -100, 360, 280, 0.4, 2.2)      # east upland (mirrored)
h += 18 * blob(-120, -560, 300, 220, -0.3, 2.4)    # south shelf
h += 18 * blob(120, 560, 300, 220, -0.3, 2.4)      # north shelf (mirrored)

# Strategic high ground: broad flat-topped hills with gentle flanks
HIGH = [(-300, 290), (300, -290), (-110, -230), (110, 230)]
for i, (cx, cz) in enumerate(HIGH):
    amp = 30 if i < 2 else 24
    h += amp * blob(cx, cz, 185, 185, 0, 2.5)

# Low valleys (wide, shallow, army-sized)
VALLEYS = [(-560, 640, 230, 150, -0.5), (560, -640, 230, 150, -0.5), (0, 0, 0, 0, 0)]
for cx, cz, rx, rz, rot in VALLEYS[:2]:
    h -= 16 * blob(cx, cz, rx + 60, rz + 50, rot, 2.2)
# Two shallow lanes funnelling into the centre
h -= 6 * blob(-330, -60, 260, 90, 0.9, 2.2)
h -= 6 * blob(330, 60, 260, 90, 0.9, 2.2)

# Subtle rolling variation (strongest in the open field, fades on bases)
rolling = fbm(300, 4) * 6.5 + fbm(70, 3) * 0.9
h += rolling

# Flat buildable platforms (bases) and central battlefield
base_a = plateau(*BASE_A, 135, 150)
base_b = plateau(*BASE_B, 135, 150)
# forward expansion pads (secondary base sites)
pads = [(-640, -250), (-250, -640), (640, 250), (250, 640)]
pad_w = [plateau(px, pz, 70, 110) for px, pz in pads]
center = plateau(0, 0, 150, 200)

h = h * (1 - base_a) + BASE_H * base_a
h = h * (1 - base_b) + BASE_H * base_b
for (px, pz), w in zip(pads, pad_w):
    h = h * (1 - w) + (BASE_H - 3) * w
h = h * (1 - center) + (CENTER_H + rolling * 0.15) * center

# Edge boundary: smooth rise into mountains outside the playable area
edge_d = np.minimum(1000 - np.abs(X), 1000 - np.abs(Z))   # distance to border
edge = 1.0 - smoothstep(0, 160, edge_d)                  # rim starts at the playable limit
ridge = fbm(180, 3) * 0.5 + 0.5
h += edge * (48 + 24 * ridge)  # eased rim, ~55-80 m

# Thermal relaxation: cap slope so units never meet a cliff in the playable area.
# Playable area: max ~15 deg (tan = 0.27); rim outside may be steeper (~28 deg).
inside = (np.abs(X) <= 840) & (np.abs(Z) <= 840)
talus = np.where(inside, 0.27, 0.53) * CELL
for _ in range(120):
    for ax_ in (0, 1):
        for sh in (1, -1):
            n = np.roll(h, sh, axis=ax_)
            d = h - n
            m = np.clip(d - talus, 0, None) * 0.25
            h = h - m
            h = h + np.roll(m, -sh, axis=ax_)
h = gaussian_filter(h, 1.0, mode="nearest")
# Final gentle smoothing keeps navmesh slopes clean
h = gaussian_filter(h, 1.2, mode="nearest")
h = np.clip(h - min(h.min(), 0.0), 0, MAX_H)

# Re-flatten base platforms exactly after smoothing (perfectly flat for building)
for w in (base_a, base_b):
    h = h * (1 - w) + BASE_H * w
# --- analysis ---------------------------------------------------------------
gx = sobel(h, axis=1) / (8 * CELL)
gz = sobel(h, axis=0) / (8 * CELL)
slope = np.degrees(np.arctan(np.hypot(gx, gz)))
playable = (np.abs(X) <= 840) & (np.abs(Z) <= 840)

from scipy.ndimage import label
buildable = (slope < 3.0) & playable
buildable = gaussian_filter(buildable.astype(float), 3.0) > 0.8
lab, n = label(buildable)
sizes = np.bincount(lab.ravel())
keep = np.isin(lab, np.nonzero(sizes > 6000)[0]) & (lab > 0)
buildable = keep
high = (h > 38) & playable & (slope < 14)
valley = (h < 12) & playable

zone = np.zeros((GRID, GRID, 4), np.uint8)
zone[..., 0] = buildable * 255
zone[..., 1] = high * 255
zone[..., 2] = valley * 255
zone[..., 3] = playable * 255

# --- export -----------------------------------------------------------------
h.astype("<f4").tofile(os.path.join(OUT, "heightmap.bin"))
Image.fromarray((h / MAX_H * 65535).astype(np.uint16)).save(os.path.join(OUT, "heightmap16.png"))
Image.fromarray(zone, "RGBA").save(os.path.join(OUT, "zonemap.png"))

meta = {
    "size_m": SIZE, "cells": CELLS, "grid": GRID, "cell_m": CELL,
    "chunks_per_side": 4, "cells_per_chunk": CELLS // 4, "max_height_m": MAX_H,
    "base_a": BASE_A, "base_b": BASE_B, "base_height_m": BASE_H,
    "stats": {
        "min_h": float(h.min()), "max_h": float(h.max()),
        "max_slope_playable_deg": float(slope[playable].max()),
        "p95_slope_playable_deg": float(np.percentile(slope[playable], 95)),
        "buildable_pct_playable": float(buildable[playable].mean() * 100),
        "high_ground_pct": float(high[playable].mean() * 100),
    },
}
with open(os.path.join(OUT, "terrain_meta.json"), "w") as f:
    json.dump(meta, f, indent=2)
print(json.dumps(meta["stats"], indent=2))
