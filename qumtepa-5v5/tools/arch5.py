"""Qumtepa 5v5 — 4-bosqich: arxitektura bezaklari (build5.py STYLE=arch da chaqiriladi).

MUHIM QOIDA: bu yerdagi hamma narsa faqat ko'rinish uchun. To'qnashuv (COL), clip'lar va NavMesh
greybox bilan aynan bir xil qoladi — 3-bosqichdagi balans (vaqtlar, ko'rish chiziqlari, bot natijalari)
o'zgarmasligi uchun. Devordan chiqib turgan detallar ≤ 0.25 m; balkon, soyabon, gilam va chiroqlar
ko'z balandligidan (1.6 m) ancha yuqorida; mo'ljal binolari o'yin maydonidan tashqarida, 12 m clip ustida.

Uslublar (layout5.DISTRICT): qala, bozor, madrasa, karvon, masjid.
"""
import math
import numpy as np

# uslub -> devor, bezak (trim), pol materiallari va facade elementlari ehtimollari
STYLE = {
    "qala":    {"wall": "sandstone_dk", "trim": "sandstone", "floor": "flagstone", "door": 0.10, "win": 0.55, "slit": True,
                "balcony": 0.0, "awning": 0.0, "carpet": 0.0, "pishtoq": 0.0, "pilaster": 0.0, "beams": 0.2, "crenel": 0.95,
                "roof": ("none", 0.0), "frieze": None, "ceiling": "vassa"},
    "bozor":   {"wall": "plaster", "trim": "sandstone", "floor": "cobble", "door": 0.5, "win": 0.3, "slit": False,
                "balcony": 0.08, "awning": 0.85, "carpet": 0.5, "pishtoq": 0.0, "pilaster": 0.0, "beams": 0.5, "crenel": 0.0,
                "roof": ("shed", 0.35), "frieze": None, "ceiling": "vassa", "ayvon": 0.12, "lagan": 0.14},
    "madrasa": {"wall": "plaster_w", "trim": "sandstone", "floor": "flagstone", "door": 0.12, "win": 0.4, "slit": False,
                "balcony": 0.0, "awning": 0.0, "carpet": 0.0, "pishtoq": 0.22, "pilaster": 0.0, "beams": 0.0, "crenel": 0.0,
                "roof": ("dome_small", 0.25), "frieze": "girih", "ceiling": "plaster", "ayvon": 0.08},
    "karvon":  {"wall": "brick", "trim": "sandstone", "floor": "flagstone", "door": 0.12, "win": 0.4, "slit": False,
                "balcony": 0.22, "awning": 0.1, "carpet": 0.0, "pishtoq": 0.0, "pilaster": 0.0, "beams": 0.8, "crenel": 0.0,
                "roof": ("pergola", 0.3), "frieze": None, "ceiling": "vassa"},
    "masjid":  {"wall": "plaster_w", "trim": "sandstone", "floor": "flagstone", "door": 0.12, "win": 0.45, "slit": False,
                "balcony": 0.0, "awning": 0.0, "carpet": 0.0, "pishtoq": 0.12, "pilaster": 0.45, "beams": 0.0, "crenel": 0.0,
                "roof": ("dome", 0.45), "frieze": "majolica", "ceiling": "plaster_w", "ayvon": 0.12, "lagan": 0.1},
}
OPEN = set(".AB")
AWNINGS = ["awning_r", "awning_b", "awning_g", "atlas_1", "atlas_2", "atlas_1"]


def decorate(ctx):
    """ctx: build5 dan yordamchilar va ma'lumotlar (box, quad, lathe, arch_wall, grid, H, DIST, cx, cz, ctype, COVER, ...)"""
    box, quad, lathe, arch_wall = ctx["box"], ctx["quad"], ctx["lathe"], ctx["arch_wall"]
    grid, H, DIST, G = ctx["grid"], ctx["H"], ctx["DIST"], ctx["G"]
    cx, cz, ctype, COVER, BID = ctx["cx"], ctx["cz"], ctx["ctype"], ctx["COVER"], ctx["BID"]
    rng = np.random.default_rng(7)
    stats = {"eshik": 0, "deraza": 0, "balkon": 0, "soyabon": 0, "gilam": 0, "peshtoq": 0, "gumbaz": 0, "ayvon": 0, "lagan": 0}

    # ------------------------------------------------------------------ facade yordamchilari (v2 dan, uslubga moslangan)
    def quoins(ax, fx, out, end, s2, hh, mat):
        k, y = 0, 0.55
        while y + 0.5 < hh - 0.35:
            l1, l2 = (0.62, 0.34) if k % 2 == 0 else (0.34, 0.62)
            n0, n1 = sorted((fx - out * l1, fx + out * 0.07))
            e0, e1 = sorted((end - s2 * l2, end + s2 * 0.07))
            if ax == "x":
                box("Decor", mat, e0, y, n0, e1, y + 0.5, n1)
            else:
                box("Decor", mat, n0, y, e0, n1, y + 0.5, e1)
            y += 0.56
            k += 1

    def window(fbox, m, wy, trim, kind):
        fbox("Decor", "dark", m - 0.5, m + 0.5, wy, wy + 1.3, 0.0, 0.03)
        fbox("Decor", trim, m - 0.66, m - 0.5, wy - 0.1, wy + 1.3, 0, 0.17)
        fbox("Decor", trim, m + 0.5, m + 0.66, wy - 0.1, wy + 1.3, 0, 0.17)
        fbox("Decor", trim, m - 0.74, m + 0.74, wy + 1.3, wy + 1.52, 0, 0.21)
        fbox("Decor", trim, m - 0.72, m + 0.72, wy - 0.24, wy - 0.1, 0, 0.25)
        if kind == "shutters":
            fbox("Decor", "beam", m - 0.5, m + 0.5, wy + 0.62, wy + 0.68, 0.03, 0.08, scale=1)
            fbox("Decor", "door", m - 0.98, m - 0.68, wy, wy + 1.3, 0.02, 0.07, unit=True)
            fbox("Decor", "door", m + 0.68, m + 0.98, wy, wy + 1.3, 0.02, 0.07, unit=True)
        elif kind == "grille":
            for k in range(5):
                xs = m - 0.4 + k * 0.2
                fbox("Decor", "metal", xs - 0.015, xs + 0.015, wy, wy + 1.3, 0.1, 0.13)
            for yy in (wy + 0.35, wy + 0.95):
                fbox("Decor", "metal", m - 0.5, m + 0.5, yy, yy + 0.03, 0.1, 0.13)
        else:
            fbox("Decor", "beam", m - 0.5, m + 0.5, wy + 0.62, wy + 0.7, 0.03, 0.09, scale=1)
            fbox("Decor", "beam", m - 0.04, m + 0.04, wy, wy + 1.3, 0.03, 0.09, scale=1)
        stats["deraza"] += 1

    def slit(fbox, m, wy, trim):
        fbox("Decor", "dark", m - 0.12, m + 0.12, wy, wy + 1.2, 0.0, 0.03)
        fbox("Decor", trim, m - 0.3, m - 0.12, wy - 0.15, wy + 1.35, 0, 0.12)
        fbox("Decor", trim, m + 0.12, m + 0.3, wy - 0.15, wy + 1.35, 0, 0.12)
        fbox("Decor", trim, m - 0.3, m + 0.3, wy + 1.2, wy + 1.35, 0, 0.12)
        stats["deraza"] += 1

    def arched_door(fbox, ax, fx, out, m, trim, door="carved_wood"):
        fbox("Decor", door, m - 0.62, m + 0.62, 0.02, 2.4, 0.0, 0.05, unit=True)
        fbox("Decor", "dark", m - 0.62, m + 0.62, 2.4, 3.0, 0.0, 0.02)
        for sgn in (-1, 1):
            a, b = sorted((m + sgn * 0.62, m + sgn * 0.86))
            fbox("Decor", trim, a, b, 0, 3.3, 0, 0.16)
        arch_wall("Decor", ax, fx + out * 0.08, 0.16, m - 0.62, m + 0.62, 3.3, 3.0, mat=trim, seg=12, col=False)
        fbox("Decor", trim, m - 0.11, m + 0.11, 2.88, 3.42, 0, 0.24)
        fbox("Decor", trim, m - 0.95, m + 0.95, 3.3, 3.42, 0, 0.2)
        stats["eshik"] += 1

    def awning(fbox, ax, fx, out, m, mat):
        # qiya mato: devordan 1.0 m chiqadi, 2.7–3.5 m balandlikda (ko'z chizig'idan yuqori)
        y0, y1, d = 3.5, 2.75, 1.0
        a0, a1 = m - 0.95, m + 0.95
        if ax == "x":
            p = [(a0, y0, fx), (a1, y0, fx), (a1, y1, fx + out * d), (a0, y1, fx + out * d)]
        else:
            p = [(fx, y0, a0), (fx, y0, a1), (fx + out * d, y1, a1), (fx + out * d, y1, a0)]
        quad("Decor", mat, p, [(0, 0), (1, 0), (1, 1), (0, 1)], np.array((0, 1, 0)))
        quad("Decor", mat, p[::-1], [(0, 0), (1, 0), (1, 1), (0, 1)][::-1], np.array((0, -1, 0)))
        # osilgan chekka
        for k in range(8):
            s0, s1 = a0 + k * 0.2375, a0 + (k + 1) * 0.2375
            fbox("Decor", mat, s0, s1 - 0.02, y1 - 0.18, y1, d - 0.01, d, scale=1)
        stats["soyabon"] += 1

    def carpet(fbox, m):
        fbox("Decor", "suzani" if rng.random() < 0.6 else "carpet", m - 0.7, m + 0.7, 2.7, 4.9, 0.0, 0.04, unit=True)
        fbox("Decor", "beam", m - 0.85, m + 0.85, 4.9, 5.0, 0.0, 0.08, scale=1)
        stats["gilam"] += 1

    def balcony(fbox, a0, a1):
        y = 3.9
        s0, s1 = a0 + 0.15, a1 - 0.15
        m = (a0 + a1) / 2
        fbox("Decor", "dark", m - 0.45, m + 0.45, y, y + 2.0, 0, 0.02)
        fbox("Decor", "plaster", m - 0.6, m + 0.6, y + 2.0, y + 2.15, 0, 0.12)
        fbox("Decor", "wood_light", s0, s1, y - 0.14, y, 0, 1.0, scale=1.2)
        for p in (s0 + 0.12, m, s1 - 0.12):
            fbox("Decor", "beam", p - 0.07, p + 0.07, y - 0.55, y - 0.14, 0, 0.22, scale=1)
            fbox("Decor", "beam", p - 0.07, p + 0.07, y - 0.34, y - 0.14, 0.22, 0.6, scale=1)
        for p in np.linspace(s0 + 0.05, s1 - 0.05, 9):
            fbox("Decor", "wood_light", p - 0.025, p + 0.025, y, y + 0.9, 0.93, 0.98, scale=1)
        fbox("Decor", "wood_light", s0, s1, y + 0.9, y + 0.98, 0.9, 1.0, scale=1)
        for sx in (s0, s1 - 0.06):
            fbox("Decor", "wood_light", sx, sx + 0.06, y + 0.9, y + 0.98, 0, 1.0, scale=1)
            for dd in (0.33, 0.66):
                fbox("Decor", "wood_light", sx, sx + 0.06, y, y + 0.9, dd - 0.025, dd + 0.025, scale=1)
        stats["balkon"] += 1

    def pishtoq(fbox, ax, fx, out, m, hh, frieze):
        # peshtoq: koshin ramka (0.3 m tasmalar), ichida oq suvoq, pastda ko'k koshinli chuqurcha-arka
        top = min(hh - 0.8, 6.0)
        fbox("Decor", "plaster_w", m - 0.95, m + 0.95, 0.55, top, 0.0, 0.03)
        for a0_, a1_ in ((m - 0.95, m - 0.68), (m + 0.68, m + 0.95)):
            fbox("Decor", frieze, a0_, a1_, 0.55, top, 0.03, 0.09, scale=1.0)
        fbox("Decor", frieze, m - 0.95, m + 0.95, top - 0.35, top, 0.03, 0.09, scale=1.0)
        ntop = min(top - 0.9, 3.6)
        fbox("Decor", "dark_tile", m - 0.42, m + 0.42, 0.6, ntop, 0.03, 0.05, scale=0.8)
        arch_wall("Decor", ax, fx + out * 0.06, 0.06, m - 0.42, m + 0.42, ntop + 0.35, ntop, mat="plaster_w", seg=12, col=False)
        fbox("Decor", "sandstone", m - 1.0, m + 1.0, top, top + 0.15, 0, 0.14)
        stats["peshtoq"] += 1

    def ayvon(fbox, a0, a1, hh):
        # ayvon: devorga yopishgan ikki o'ymakor yarim ustun va 3.3 m balandlikdagi vassa soyabon (ko'z chizig'idan yuqori)
        for p in (a0 + 0.3, a1 - 0.3):
            fbox("Decor", "carved_wood", p - 0.11, p + 0.11, 0.0, 3.05, 0.0, 0.14, unit=True)
            fbox("Decor", "carved_wood", p - 0.2, p + 0.2, 3.05, 3.3, 0.0, 0.2, unit=True)
        fbox("Decor", "vassa", a0 - 0.05, a1 + 0.05, 3.3, 3.42, 0.0, 1.3, scale=1.2)
        fbox("Decor", "beam", a0 - 0.08, a1 + 0.08, 3.42, 3.6, 1.18, 1.34, scale=1)
        fbox("Decor", "ganch", a0 + 0.45, a1 - 0.45, 0.55, 3.0, 0.0, 0.03, scale=1.2)
        stats["ayvon"] += 1

    def lagans(fbox, a0, a1, ax, fx, out):
        # Rishton laganlari devorda (disklar, 0.02 m chiqadi)
        for k, (p, y, r) in enumerate(((a0 + 0.5, 3.1, 0.28), (a0 + 1.0, 3.35, 0.34), (a1 - 0.5, 3.1, 0.28))):
            n = 16
            ctr = (p, y, fx + out * 0.03) if ax == "x" else (fx + out * 0.03, y, p)
            for i in range(n):
                t0, t1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
                def P(t):
                    return (p + r * math.cos(t), y + r * math.sin(t), fx + out * 0.03) if ax == "x" else (fx + out * 0.03, y + r * math.sin(t), p + r * math.cos(t))
                uv = lambda t: (0.5 + 0.5 * math.cos(t), 0.5 - 0.5 * math.sin(t))
                nrm = np.array((0, 0, out)) if ax == "x" else np.array((out, 0, 0))
                quad("Decor", "lagan", [ctr, P(t0), P(t1), ctr], [(0.5, 0.5), uv(t0), uv(t1), (0.5, 0.5)], nrm)
        stats["lagan"] += 1

    # ------------------------------------------------------------------ facade'lar
    QUO = set()
    for r in range(G):
        for c in range(G):
            if grid[r][c] != "#":
                continue
            st = STYLE[DIST[r][c]]
            for dr, dc, nm in ((0, 1, "E"), (0, -1, "W"), (1, 0, "S"), (-1, 0, "N")):
                nt = ctype(r + dr, c + dc)
                if nt == "#":
                    continue
                if nm == "E":
                    fx = cx(c + 1); ax = "z"; a0, a1 = cz(r), cz(r + 1); out = 1
                elif nm == "W":
                    fx = cx(c); ax = "z"; a0, a1 = cz(r), cz(r + 1); out = -1
                elif nm == "S":
                    fx = cz(r + 1); ax = "x"; a0, a1 = cx(c), cx(c + 1); out = 1
                else:
                    fx = cz(r); ax = "x"; a0, a1 = cx(c), cx(c + 1); out = -1

                def fbox(group, mat, s0, s1, y0, y1, d0, d1, **kw):
                    lo, hi = sorted((fx + out * d0, fx + out * d1))
                    bb = (s0, y0, lo, s1, y1, hi) if ax == "x" else (lo, y0, s0, hi, y1, s1)
                    if group:
                        box(group, mat, *bb, **kw)
                    return bb

                hh = H[r, c]
                trim = st["trim"]
                fbox("Decor", trim, a0, a1, 0, 0.55, 0, 0.1)          # poydevor
                m = (a0 + a1) / 2
                if nt in OPEN:
                    for end, (ddr, ddc), s2 in ((a0, (-1, 0) if ax == "z" else (0, -1), -1), (a1, (1, 0) if ax == "z" else (0, 1), 1)):
                        if ctype(r + ddr, c + ddc) in OPEN and DIST[r][c] in ("qala", "karvon", "bozor"):
                            key = (round(fx, 2), round(end, 2), ax)
                            if key not in QUO:
                                QUO.add(key)
                                quoins(ax, fx, out, end, s2, hh, "sandstone")
                    if hh > 6:
                        if st["frieze"]:
                            fbox("Decor", st["frieze"], a0, a1, 2.85, 3.3, 0, 0.08, scale=1.0)
                        else:
                            fbox("Decor", trim, a0, a1, 3.05, 3.2, 0, 0.09)
                    if st["beams"] and hh >= 7 and rng.random() < st["beams"]:
                        for sb in (a0 + 0.5, a0 + 1.5):
                            fbox("Decor", "beam", sb - 0.08, sb + 0.08, hh - 1.05, hh - 0.89, 0, 0.38, scale=1)
                    if st["pilaster"] and (r + c) % 2 == 0 and rng.random() < st["pilaster"]:
                        fbox("Decor", trim, a0, a0 + 0.22, 0.55, hh - 0.4, 0, 0.14)
                    roll = rng.random()
                    if st.get("ayvon") and rng.random() < st["ayvon"] and hh > 6.4:
                        ayvon(fbox, a0, a1, hh)
                    elif roll < st["pishtoq"] and hh > 6.4:
                        pishtoq(fbox, ax, fx, out, m, hh, st["frieze"] or "tile_blue")
                    elif roll < st["pishtoq"] + st["door"]:
                        arched_door(fbox, ax, fx, out, m, trim, "door" if DIST[r][c] == "qala" else "carved_wood")
                        if rng.random() < st["awning"]:
                            awning(fbox, ax, fx, out, m, AWNINGS[int(rng.integers(3))])
                    elif hh > 6.4 and roll < st["pishtoq"] + st["door"] + st["balcony"]:
                        balcony(fbox, a0, a1)
                    elif hh > 6 and roll < st["pishtoq"] + st["door"] + st["balcony"] + st["win"]:
                        wy = 3.6 + (rng.random() < 0.4) * 1.1
                        if st["slit"]:
                            slit(fbox, m, wy, trim)
                        else:
                            window(fbox, m, wy, trim, ["shutters", "grille", "cross"][int(rng.integers(3))])
                        if st["awning"] and rng.random() < 0.3:
                            fbox("Decor", AWNINGS[int(rng.integers(3))], m - 0.75, m + 0.75, wy + 1.55, wy + 1.62, 0, 0.7, scale=2)
                    elif rng.random() < st["carpet"]:
                        carpet(fbox, m)
                    elif st.get("lagan") and rng.random() < st["lagan"] / 0.5:
                        lagans(fbox, a0, a1, ax, fx, out)
                elif nt in COVER:
                    # yopiq yo'lak devori: suvoq tasma; masjid hududida ganch panel
                    if DIST[r][c] == "masjid":
                        fbox("Decor", "ganch", a0, a1, 2.3, 3.6, 0, 0.03, scale=1.2)
                        fbox("Decor", "sandstone", a0, a1, 2.2, 2.3, 0, 0.06)
                    else:
                        fbox("Decor", "plaster", a0, a1, 2.2, 2.3, 0, 0.06)

    # ------------------------------------------------------------------ tomlar: tishli devorlar, gumbazlar, soyabonlar
    done = set()
    for r in range(G):
        for c in range(G):
            b = BID[r][c]
            if grid[r][c] != "#" or b == 0 or b in done:
                continue
            done.add(b)
            cells = [(rr, cc) for rr in range(r, min(G, r + 4)) for cc in range(c, min(G, c + 4)) if BID[rr][cc] == b]
            r1 = max(rr for rr, _ in cells) + 1
            c1 = max(cc for _, cc in cells) + 1
            x0, z0, x1, z1 = cx(c), cz(r), cx(c1), cz(r1)
            hh = H[r, c]
            st = STYLE[DIST[r][c]]
            if hh <= 6.0:
                continue
            if rng.random() < st["crenel"]:
                for xx in np.arange(x0 + 0.25, x1 - 0.35, 0.8):
                    for za, zb in ((z0, z0 + 0.3), (z1 - 0.3, z1)):
                        box("Decor", st["wall"], xx, hh + 0.55, za, xx + 0.4, hh + 0.95, zb, scale=2.4)
                for zz in np.arange(z0 + 0.25, z1 - 0.35, 0.8):
                    for xa, xb in ((x0, x0 + 0.3), (x1 - 0.3, x1)):
                        box("Decor", st["wall"], xa, hh + 0.55, zz, xb, hh + 0.95, zz + 0.4, scale=2.4)
            kind, p = st["roof"]
            w, d = x1 - x0, z1 - z0
            if kind in ("dome", "dome_small") and w * d >= 16 and rng.random() < p:
                dx, dz = (x0 + x1) / 2, (z0 + z1) / 2
                rad = min(w, d) * (0.34 if kind == "dome" else 0.26)
                drum = 1.2 if kind == "dome" else 0.6
                box("Decor", st["wall"], dx - rad - .3, hh, dz - rad - .3, dx + rad + .3, hh + drum, dz + rad + .3, scale=2.4)
                prof = [(rad * math.cos(a), hh + drum + rad * 1.1 * math.sin(a)) for a in np.linspace(0, math.pi / 2, 10)]
                prof[-1] = (0.0, prof[-1][1])
                lathe("Decor", "dome" if kind == "dome" else "tile_turq", dx, 0, dz, prof, 24, 3)
                lathe("Decor", "metal", dx, 0, dz, [(0.08, hh + drum + rad * 1.1), (0.05, hh + drum + rad * 1.1 + 0.8), (0.0, hh + drum + rad * 1.1 + 0.85)], 8)
                stats["gumbaz"] += 1
            elif kind == "shed" and rng.random() < p:
                sx0, sz0 = x0 + 0.6, z0 + 0.6
                sx1, sz1 = sx0 + min(3, w - 1.2), sz0 + min(3, d - 1.2)
                box("Decor", "plaster", sx0, hh, sz0, sx1, hh + 2.2, sz1, scale=3)
                box("Decor", "roof", sx0 - .2, hh + 2.2, sz0 - .2, sx1 + .2, hh + 2.45, sz1 + .2, scale=2)
            elif kind == "pergola" and rng.random() < p:
                for xx in np.arange(x0 + 0.6, x1 - 0.4, 1.4):
                    box("Decor", "beam", xx, hh + 0.55, z0 + 0.4, xx + 0.12, hh + 2.4, z0 + 0.52, scale=1)
                    box("Decor", "beam", xx, hh + 0.55, z1 - 0.52, xx + 0.12, hh + 2.4, z1 - 0.4, scale=1)
                box("Decor", AWNINGS[int(rng.integers(3))], x0 + 0.5, hh + 2.4, z0 + 0.3, x1 - 0.4, hh + 2.45, z1 - 0.3, scale=2)

    # ------------------------------------------------------------------ yopiq yo'laklarda qovurg'a arkalar (v2 dan)
    for t in ",m":
        h = COVER[t]
        for r in range(1, G - 1):
            c = 0
            while c < G:
                if grid[r][c] == t:
                    c0 = c
                    while c < G and grid[r][c] == t:
                        c += 1
                    c1 = c - 1
                    if (c1 - c0 < 3 and ctype(r, c0 - 1) == "#" and ctype(r, c1 + 1) == "#" and r % 2 == 0
                            and all(ctype(r - 1, k) == t and ctype(r + 1, k) == t for k in range(c0, c1 + 1))):
                        arch_wall("Decor", "x", cz(r) + 1, 0.45, cx(c0), cx(c1 + 1), h, h - 0.25, mat="sandstone", col=False)
                else:
                    c += 1
        for c in range(1, G - 1):
            r = 0
            while r < G:
                if grid[r][c] == t:
                    r0 = r
                    while r < G and grid[r][c] == t:
                        r += 1
                    r1 = r - 1
                    if (r1 - r0 < 3 and ctype(r0 - 1, c) == "#" and ctype(r1 + 1, c) == "#" and c % 2 == 0
                            and all(ctype(k, c - 1) == t and ctype(k, c + 1) == t for k in range(r0, r1 + 1))):
                        arch_wall("Decor", "z", cx(c) + 1, 0.45, cz(r0), cz(r1 + 1), h, h - 0.25, mat="sandstone", col=False)
                else:
                    r += 1

    # spawn'lar shiftida yog'och to'sinlar
    for t in "TC":
        cells = [(r, c) for r in range(G) for c in range(G) if grid[r][c] == t]
        r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
        c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
        h = COVER[t]
        x = cx(c0) + 0.9
        while x < cx(c1 + 1) - 0.5:
            box("Decor", "beam", x - 0.14, h - 0.32, cz(r0), x + 0.14, h, cz(r1 + 1), scale=1.2)
            x += 1.6

    # ------------------------------------------------------------------ mo'ljal binolari
    for kind, x, z in ctx["LANDMARKS"]:
        base = H[int((z - ctx["ORIGIN"]) // ctx["CELL"]), int((x - ctx["ORIGIN"]) // ctx["CELL"])]
        if kind == "minora":
            prof = [(2.2, 0), (2.2, base + 1), (1.9, base + 1.2), (1.6, base + 14), (1.5, base + 16)]
            lathe("Decor", "brick", x, 0, z, prof, 24, 1.6)
            for yb in (base + 4, base + 8, base + 12):
                lathe("Decor", "tile_blue", x, 0, z, [(1.62 - (yb - base) * 0.017, yb), (1.62 - (yb - base) * 0.017, yb + 0.9)], 24, 1.0)
            y = base + 16
            lathe("Decor", "wood_light", x, 0, z, [(1.5, y), (2.4, y + 0.3), (2.4, y + 0.5), (1.5, y + 0.6)], 24, 1.2)
            lathe("Decor", "plaster_w", x, 0, z, [(1.3, y + 0.6), (1.3, y + 3.4), (1.45, y + 3.6), (0.0, y + 3.6)], 20, 2)
            for k in range(8):
                a = k / 8 * 2 * math.pi
                box("Decor", "dark", x + 1.31 * math.cos(a) - 0.2, y + 1.2, z + 1.31 * math.sin(a) - 0.2,
                    x + 1.31 * math.cos(a) + 0.2, y + 2.8, z + 1.31 * math.sin(a) + 0.2)
            lathe("Decor", "dome", x, 0, z, [(1.45, y + 3.6), (1.2, y + 4.6), (0.6, y + 5.4), (0.0, y + 5.8)], 20, 2)
        elif kind == "kalta_minor":
            # Kalta Minor (Xiva): yo'g'on, qisqa, tugallanmagan minora, butunlay sirli koshin tasmalar bilan qoplangan
            H0 = base + 12
            prof = [(3.4, 0), (3.4, base + 0.5), (3.1, base + 0.8), (2.6, H0)]
            lathe("Decor", "brick", x, 0, z, prof, 32, 1.6)
            bands = ["tile_turq", "majolica", "girih", "tile_turq", "majolica", "dome"]
            for i, mat in enumerate(bands):
                y0 = base + 1.4 + i * 1.75
                r0 = 3.1 - (y0 - base - 0.8) / (H0 - base - 0.8) * 0.5 + 0.02
                r1 = 3.1 - (y0 + 1.1 - base - 0.8) / (H0 - base - 0.8) * 0.5 + 0.02
                lathe("Decor", mat, x, 0, z, [(r0, y0), (r1, y0 + 1.1)], 32, 1.0)
            lathe("Decor", "sandstone", x, 0, z, [(2.62, H0), (2.8, H0 + 0.25), (2.3, H0 + 0.3), (0.0, H0 + 0.3)], 32, 2)
        elif kind == "gumbaz":
            rad = 5.5
            lathe("Decor", "plaster_w", x, 0, z, [(rad + 0.4, base), (rad + 0.4, base + 2.6), (rad + 0.7, base + 2.8), (rad, base + 3.0)], 32, 3)
            lathe("Decor", "tile_turq", x, 0, z, [(rad + 0.42, base + 1.2), (rad + 0.42, base + 2.2)], 32, 1.0)
            prof = [(rad * math.cos(a), base + 3.0 + rad * 1.15 * math.sin(a)) for a in np.linspace(0, math.pi / 2, 14)]
            prof[-1] = (0.0, prof[-1][1])
            lathe("Decor", "dome", x, 0, z, prof, 36, 3)
            top = base + 3.0 + rad * 1.15
            lathe("Decor", "metal", x, 0, z, [(0.2, top), (0.12, top + 1.4), (0.0, top + 1.6)], 10)
            stats["gumbaz"] += 1
        elif kind == "burj":
            s = 2.4
            box("Decor", "sandstone_dk", x - s, 0, z - s, x + s, base + 6, z + s, scale=2.4)
            box("Decor", "sandstone", x - s - 0.3, base + 6, z - s - 0.3, x + s + 0.3, base + 6.4, z + s + 0.3, scale=2.4)
            for xx in np.arange(x - s, x + s - 0.2, 0.9):
                for za, zb in ((z - s - 0.3, z - s + 0.1), (z + s - 0.1, z + s + 0.3)):
                    box("Decor", "sandstone_dk", xx, base + 6.4, za, xx + 0.45, base + 7.2, zb, scale=2.4)
            for zz in np.arange(z - s, z + s - 0.2, 0.9):
                for xa, xb in ((x - s - 0.3, x - s + 0.1), (x + s - 0.1, x + s + 0.3)):
                    box("Decor", "sandstone_dk", xa, base + 6.4, zz, xb, base + 7.2, zz + 0.45, scale=2.4)
            for side in (-1, 1):
                box("Decor", "dark", x - 0.12, base + 2.5, z + side * s - 0.02, x + 0.12, base + 4.0, z + side * s + 0.02)
    return stats
