# Qumtepa 5v5 — 1-bosqich: 2D blokaut (yakuniy reja).
# 55 x 55 katak, har biri 2 m  ->  110 m x 110 m  (Qumtepa v2: 25 x 25, 50 m x 50 m).
# Koordinatalar metrda: x — g'arb(-) / sharq(+), z — shimol(-, T) / janub(+, CT). Markaz (0, 0).
# Katak turlari (v2 bilan bir xil):
#   '#' bino   '.' ochiq osmon   ',' yopiq yo'lak (4.2 m)   'm' yopiq mid (5.2 m)
#   'T' / 'C' spawn   'A' / 'B' bomba maydonlari (ochiq osmon)
G = 55
CELL = 2.0
ORIGIN = -55.0
grid = [["#"] * G for _ in range(G)]

# (nom, c0, r0, c1, r1, tur) — kataklar, chegaralar kiradi; keyingisi oldingisini ustidan yozadi
ZONES = [
    # --- T tomoni
    ("T spawn",            20, 2, 34, 7, "T"),
    ("Long doors",         15, 5, 19, 7, ","),
    ("Outside long",        9, 5, 14, 11, "."),
    ("Long konnektor",     15, 10, 18, 11, "."),
    ("Long",                9, 12, 13, 19, "."),
    ("Long pit",           11, 20, 13, 24, "."),
    ("Long ",               3, 18, 7, 29, "."),
    ("Long corner ",        3, 18, 13, 19, "."),
    ("T ramp g'arb",       23, 8, 24, 9, "."),
    ("T ramp sharq",       30, 8, 31, 9, "."),
    ("Top mid",            19, 10, 35, 17, "."),
    ("Short yo'li",        18, 16, 18, 17, ","),
    ("Catwalk",            15, 16, 17, 29, ","),
    ("Upper tunnels yo'li", 35, 5, 39, 7, ","),
    ("Upper tunnels",      40, 5, 45, 11, ","),
    ("Tunnel konnektor",   36, 12, 40, 13, ","),
    ("Lower tunnels",      41, 12, 45, 19, ","),
    ("Tunnel cho'ntagi",   41, 20, 43, 24, ","),
    ("Lower tunnels ",     47, 18, 51, 29, ","),
    ("Tunnel burchagi",    41, 18, 51, 19, ","),
    ("Mid",                25, 18, 29, 29, "m"),
    ("Window yo'li",       36, 16, 36, 17, ","),
    ("B window",           37, 16, 39, 29, ","),
    ("Mid-window yo'li",   30, 23, 36, 25, ","),
    # --- bomba maydonlari
    ("A site",              3, 30, 18, 41, "A"),
    ("B site",             36, 30, 51, 41, "B"),
    # --- CT tomoni
    ("CT mid",             22, 30, 32, 38, "."),
    ("A CT",               19, 33, 21, 36, "."),
    ("B doors",            33, 33, 35, 36, "."),
    ("CT mid g'arb",       22, 39, 23, 44, "."),
    ("CT mid sharq",       31, 39, 32, 44, "."),
    ("CT mid g'arb og'zi", 20, 43, 25, 44, "."),
    ("CT mid sharq og'zi", 29, 43, 34, 44, "."),
    ("A ramp",             12, 42, 17, 47, "."),
    ("B ramp",             37, 42, 42, 47, "."),
    ("CT spawn",           19, 45, 35, 51, "C"),
    ("A ramp yo'li",       15, 46, 18, 49, ","),
    ("B ramp yo'li",       36, 46, 39, 49, ","),
]
for _n, c0, r0, c1, r1, ch in ZONES:
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            grid[r][c] = ch
LAYOUT = "\n".join("".join(row) for row in grid)
COVER = {",": 4.2, "m": 5.2, "T": 5.0, "C": 5.0}


def m(c, r):
    """katak markazi -> metr (x, z)"""
    return (ORIGIN + CELL * c + 1.0, ORIGIN + CELL * r + 1.0)


def zone_rect_m(name):
    for n, c0, r0, c1, r1, _ in ZONES:
        if n == name:
            return (ORIGIN + CELL * c0, ORIGIN + CELL * r0, ORIGIN + CELL * (c1 + 1), ORIGIN + CELL * (r1 + 1))
    raise KeyError(name)


# ------------------------------------------------------------------ callout'lar
# Har bir yuriladigan katakka nom. Asosiy manba — ZONES; quyidagilar katta hududlarni bo'ladi.
CALLOUT_SPLITS = [
    # (nom, x0, z0, x1, z1) metrda — ZONES nomining ustidan yoziladi
    ("A platforma", -49, 17, -44, 29),
    ("A default", -38, 13, -28, 23),
    ("A short chiqishi", -25, 5, -17, 11),
    ("A long chiqishi", -49, 5, -39, 11),
    ("B platforma", 44, 17, 49, 29),
    ("B default", 28, 13, 38, 23),
    ("B window chiqishi", 17, 5, 25, 11),
    ("B tunnel chiqishi", 39, 5, 49, 11),
    ("Mid doors", -5, 1, 5, 9),
    ("Long corner", -39, -31, -29, -23),
]
ALIASES = {"Mid-window yo'li": "Mid-window", "CT mid g'arb og'zi": "CT spawn", "CT mid sharq og'zi": "CT spawn", "Long corner ": "Long", "Tunnel burchagi": "Lower tunnels", "Long ": "Long", "Lower tunnels ": "Lower tunnels", "T ramp g'arb": "T ramp", "T ramp sharq": "T ramp",
           "Short yo'li": "Catwalk", "Long konnektor": "Outside long", "Tunnel konnektor": "Upper tunnels",
           "Upper tunnels yo'li": "Upper tunnels", "Window yo'li": "B window", "CT mid g'arb": "CT mid",
           "CT mid sharq": "CT mid", "A ramp yo'li": "A ramp", "B ramp yo'li": "B ramp"}

# ------------------------------------------------------------------ o'yin hajmlari (metr)
T_SPAWN = (0.0, -47.0)
CT_SPAWN = (0.0, 42.0)
A_PLANT = (-40.0, 13.0)
B_PLANT = (40.0, 13.0)
MID_DOORS = (0.0, 4.0)

# 5 tadan spawn joyi; T janubga (+z), CT shimolga (-z) qaraydi
SPAWNS = {
    "T": [(-4.0, -47.0), (-2.0, -47.0), (0.0, -47.0), (2.0, -47.0), (4.0, -47.0)],
    "CT": [(-4.0, 42.0), (-2.0, 42.0), (0.0, 42.0), (2.0, 42.0), (4.0, 42.0)],
}
BOMB_ZONES = {"A": (-45.0, 8.0, -21.0, 27.0), "B": (21.0, 8.0, 45.0, 27.0)}
BUY_ZONES = {"T": (-15.0, -51.0, 15.0, -43.5), "CT": (-17.0, 35.0, 17.0, 49.0)}

# Raund qoidalari (soniya) — 110 m xarita uchun: T site'ga 17–20 s, CT 12 s da yetadi.
ROUND = {"freeze": 12.0, "buy_time": 25.0, "round_time": 115.0, "bomb_timer": 40.0,
         "plant_time": 3.0, "defuse_time": 10.0, "defuse_time_kit": 5.0, "round_end": 6.0, "win_rounds": 13}

# ------------------------------------------------------------------ panalar (Qumtepa v2 build.py funksiyalari bilan bir xil)
# ("stack", x, z, [(dx, dz, y, o'lcham, yashil)], yaw) — qutilar; 2 qavat (≥ 2.3 m) ko'rishni to'sadi
# ("crate", x, z, o'lcham, yaw)  ("barrel", x, z)  ("urn", x, z)  ("sandbags", x0, z0, x1, z1)
# ("platform", x0, z0, x1, z1, balandlik, zinapoya_tomoni)  ("wall", x0, z0, x1, z1, balandlik)
# ("palm", x, z, balandlik)  ("decal", x, z, harf)
S1 = lambda s=1.2: [(0, 0, 0, s, False)]                                   # 1 quti
S2 = lambda s=1.2: [(0, 0, 0, s, False), (0, 0, s, s, False)]              # 2 qavat
W2 = lambda s=1.2: [(0, 0, 0, s, False), (s, 0, 0, s, False)]              # 2 quti yonma-yon
L3 = lambda s=1.2: [(0, 0, 0, s, False), (s, 0, 0, s, False), (s / 2, 0, s, s, False)]  # 2 + tepada 1
Q4 = lambda s=1.2: [(-s / 2, -s / 2, 0, s, False), (s / 2, -s / 2, 0, s, False), (-s / 2, s / 2, 0, s, False), (s / 2, s / 2, 0, s, False),
                   (-s / 2, -s / 2, s, s, False), (s / 2, -s / 2, s, s, False), (-s / 2, s / 2, s, s, False), (s / 2, s / 2, s, s, False)]  # 2x2 qutilar, 2 qavat
T3 = lambda s=1.2: [(0, 0, 0, s, False), (0, s + .05, 0, s, False), (0, s / 2, s, s, False)]

PROPS = [
    # --- A site: ochiq, katta masofa (Long dan snayper), kam lekin katta panalar
    ("decal", -40.0, 13.0, "A"),
    ("stack", -32.0, 19.5, L3(), 0.0),                     # A default (plant panasi)
    ("stack", -37.5, 8.0, S1(1.1), 0.1),                   # Long chiqishi
    ("sandbags", -31.5, 7.8, -29.5, 7.8),                  # Long chiqishi (egilib)
    ("barrel", -23.0, 7.2),                                # Short chiqishi
    ("wall", -21.5, 5.5, -17.0, 7.5, 3.0),                 # Short chiqishi devori (catwalk <-> A CT chizig'ini kesadi)
    ("platform", -49.0, 18.0, -46.0, 27.0, 1.3, "+x"),      # A platforma (goose)
    ("stack", -20.5, 23.0, S2(), 0.0),                     # A CT tomoni (short'ga qarshi)
    ("stack", -26.5, 13.0, T3(), 0.0),                     # A o'rtasi (short <-> ramp chizig'ini bo'ladi)
    ("sandbags", -42.0, 12.0, -39.0, 12.0),                # A g'arbiy qism (egilib)
    ("crate", -30.0, 26.5, 1.1, 0.2),                      # Ramp tepasi
    ("barrel", -38.0, 27.5),                               # Ramp tepasi
    ("palm", -47.5, 7.0, 8.0), ("palm", -18.5, 27.5, 7.5),
    # --- Long, Outside long, Long doors
    ("wall", -21.0, -45.0, -19.0, -43.5, 4.2),              # Long doors (eshik o'rni 3 m)
    ("wall", -21.0, -40.5, -19.0, -39.0, 4.2),
    ("stack", -35.0, -43.0, W2(1.1), 0.0),                 # Outside long
    ("barrel", -27.0, -33.5),
    ("stack", -36.5, -27.0, S2(1.1), 0.0),                 # Long corner
    ("palm", -47.5, -8.0, 8.0),
    ("barrel", -45.0, -2.0),                               # Long pastki qismi
    ("crate", -29.8, -6.0, 1.1, 0.2),                      # Long pit ichi
    ("urn", -44.0, -9.5), ("crate", -43.8, 1.8, 1.0, 0.1), # Long pit (yashirinish)
    # --- Top mid (katta ochiq maydon)
    ("stack", -10.0, -25.0, S2(), 0.0),                    # Top mid chap
    ("stack", 9.5, -31.0, W2(), 0.1),                      # Top mid o'ng
    ("barrel", 13.5, -22.5), ("urn", -14.5, -33.0),
    ("wall", -7.5, -30.0, 7.5, -27.5, 3.2),                # Top mid xarobasi: T spawn <-> mid doors chizig'ini kesadi
    ("palm", -15.5, -20.5, 7.5), ("palm", 15.5, -33.5, 7.5),
    # --- Mid va Mid doors
    ("crate", -3.6, -12.0, 0.9, 0.2), ("urn", 3.8, -4.0),
    ("wall", -5.0, 3.0, -1.5, 5.0, 5.2),                   # Mid doors (o'tish 3 m)
    ("wall", 1.5, 3.0, 5.0, 5.0, 5.2),
    # --- CT mid va konnektorlar
    ("wall", -5.0, 11.0, 5.0, 19.0, 6.0),                  # CT mid binosi (mid doors va A CT <-> B doors chiziqlarini kesadi)
    ("stack", 8.0, 9.5, S2(1.1), 0.0),                     # CT mid cho'ntagi
    ("stack", -8.5, 19.5, S1(1.1), 0.1),
    ("barrel", -9.0, 8.0), ("urn", 9.0, 21.0),
    ("wall", 13.0, 11.0, 15.0, 13.5, 4.5),                 # B doors (o'tish 3 m)
    ("wall", 13.0, 16.5, 15.0, 19.0, 4.5),
    # --- B site: zich, yaqin jang, ko'p kichik panalar
    ("decal", 40.0, 13.0, "B"),
    ("stack", 30.8, 19.5, L3(), 0.0),                      # B default (A default ning ko'zgu nusxasi)
    ("stack", 32.0, 8.5, W2(1.1), 0.1),                    # Tunnel chiqishi
    ("crate", 22.0, 9.5, 1.1, 0.2),                        # Window chiqishi
    ("wall", 17.0, 5.5, 21.5, 7.5, 3.0),                   # Window chiqishi devori
    ("platform", 46.0, 18.0, 49.0, 27.0, 1.3, "-x"),        # B platforma
    ("stack", 39.4, 10.5, W2(), 0.0),                      # B o'rtasi (past: 3-bosqichda baland ustun T ga xavfsiz joy bergani uchun)
    ("barrel", 19.5, 21.0), ("urn", 19.5, 9.0),            # B doors yonlari
    ("sandbags", 27.0, 26.0, 30.0, 26.0),                  # Ramp tepasi
    ("barrel", 37.5, 27.5), ("crate", 44.0, 8.0, 1.1, 0.0), ("crate", 25.5, 21.5, 1.1, 0.3),
    ("palm", 47.5, 7.0, 8.0), ("palm", 18.5, 27.5, 7.5),
    # --- Tunnels
    ("barrel", 36.5, -24.0), ("crate", 31.5, -10.0, 0.9, 0.3), ("barrel", 45.0, -2.0), ("stack", 35.0, -43.0, W2(1.1), 0.0),
    ("barrel", 27.0, -33.5), ("crate", 15.0, -7.5, 0.9, 0.2),   # Mid-window
    # --- Ramp'lar
    ("wall", -26.0, 29.0, -19.0, 31.0, 4.5),               # A ramp tepasi: catwalk <-> ramp chizig'ini kesadi
    ("wall", 19.0, 29.0, 26.0, 31.0, 4.5),                 # B ramp tepasi
    ("wall", -29.0, 18.5, -17.0, 20.0, 3.0),               # A xarobasi (catwalk <-> ramp diagonallari)
    ("wall", 17.0, 18.5, 29.0, 20.0, 3.0),                 # B xarobasi
    ("wall", -33.5, 23.0, -30.0, 26.0, 2.5),               # A quduq (long <-> ramp diagonali, pana)
    ("wall", 30.0, 23.0, 33.5, 26.0, 2.5),                 # B quduq
    ("stack", -25.8, 35.5, Q4(), 0.0),                     # A ramp qutilari (long <-> ramp chizig'i)
    ("stack", 25.8, 35.5, Q4(), 0.0),                      # B ramp qutilari
    ("crate", -22.0, 36.0, 1.1, 0.2), ("barrel", -29.5, 39.5),
    ("crate", 22.0, 36.0, 1.1, -0.2), ("barrel", 29.5, 39.5),
    # --- Spawn'lar
    ("stack", -12.5, -49.0, W2(1.1), 0.0), ("stack", 12.5, -49.0, [(0, 0, 0, 1.2, True)], 0.0), ("urn", 0.0, -50.0),
    ("barrel", -13.5, -41.0), ("barrel", 13.5, -41.0),
    ("wall", -10.0, -45.0, -1.25, -43.5, 3.0),             # T spawn: top mid dan spawn ko'rinmasin (ramp oldida 4.5 m o'tish)
    ("wall", 1.25, -45.0, 10.0, -43.5, 3.0),
    ("wall", -13.0, 33.0, -6.0, 35.0, 3.0),                # CT mid yo'li og'zi: CT mid dan spawn ko'rinmasin
    ("wall", 6.0, 33.0, 13.0, 35.0, 3.0),
    ("stack", -15.0, 47.0, S1(1.2), 0.0), ("stack", 14.0, 47.0, W2(1.1), 0.0),
    ("barrel", -4.0, 47.5), ("urn", 4.0, 47.5),
]

# ------------------------------------------------------------------ yo'nalishlar (vaqt tekshiruvi uchun)
ROUTES = [
    ("T → A (Long)",          "T",  [T_SPAWN, (-30.0, -38.0), (-32.0, -20.0), (-40.0, -10.0), A_PLANT]),
    ("T → A (Short)",         "T",  [T_SPAWN, (-10.0, -30.0), (-22.0, -8.0), A_PLANT]),
    ("T → B (Tunnels)",       "T",  [T_SPAWN, (31.0, -38.0), (32.0, -20.0), (40.0, -10.0), B_PLANT]),
    ("T → B (Window)",  "T",  [T_SPAWN, (20.0, -20.0), (22.0, 0.0), B_PLANT]),
    ("T → Mid doors",         "T",  [T_SPAWN, (0.0, -14.0), MID_DOORS]),
    ("CT → A (Ramp)",         "CT", [CT_SPAWN, (-28.0, 38.0), A_PLANT]),
    ("CT → A (CT mid)",       "CT", [CT_SPAWN, (-9.0, 28.0), (-14.0, 15.0), A_PLANT]),
    ("CT → B (Ramp)",         "CT", [CT_SPAWN, (28.0, 38.0), B_PLANT]),
    ("CT → B (B doors)",      "CT", [CT_SPAWN, (9.0, 28.0), (14.0, 15.0), B_PLANT]),
    ("CT → Mid doors",        "CT", [CT_SPAWN, (7.0, 20.0), MID_DOORS]),
]
ROTATIONS = [
    ("CT rotatsiya A → B",          "CT", [A_PLANT, B_PLANT]),
    ("T rotatsiya Long → Tunnels",  "T",  [(-44.0, -5.0), (44.0, -5.0)]),
]
# Maqsadlar (sekund) — analyze5.py shularni tekshiradi
TARGETS = {
    "t_lane": (16.0, 20.5),        # har bir T hujum yo'li
    "t_lane_spread": 3.0,          # eng tez va eng sekin T yo'li farqi
    "ct_site": (10.0, 13.5),       # CT spawn -> site
    "ct_ab_diff": 0.6,             # CT uchun A va B farqi
    "ct_lead": 4.5,                # CT site'ga T dan kamida shuncha oldin yetadi
    "mid_gap": (1.5, 3.0),         # mid doors'ga CT T dan shuncha oldin yetadi
    "first_contact": 8.5,          # dushmanlar bir-birini ko'ra oladigan eng erta vaqt
    "spawn_safe": 15.0,            # spawn (sotib olish) zonasini dushman eng erta ko'rishi
    "max_sightline": 60.0,         # eng uzun ko'rish chizig'i (m)
    "spawn_exit_spread": 0.6,      # 5 spawn joyidan eng yaqin chiqishgacha farq
}

# ------------------------------------------------------------------ smoke rejasi
# (nom, jamoa, nishon (x, z), otish joyi (x, z), to'sishi kerak bo'lgan ko'rish chiziqlari [(dan, gacha)])
# Otish joylari 3-bosqichda Godot fizikasi bilan topilgan (tests/run_grenades.gd, docs/smokes_stage3.json).
SMOKE_R = 2.6
SMOKES = [
    ("A CT",          "T",  (-18.5, 15.0), (-31.5, -9.0), [((-13.0, 16.0), A_PLANT), ((-13.0, 17.0), (-38.0, 14.0))]),
    ("A ramp",        "T",  (-28.0, 30.0), (-21.0, -1.0), [((-30.5, 37.0), (-24.8, 21.0)), ((-27.0, 33.0), (-30.0, 20.8))]),
    ("A platforma",   "T",  (-44.0, 20.0), (-31.0, -8.0), [((-47.5, 22.0), (-34.0, 6.0)), ((-47.5, 25.0), (-30.0, 8.0))]),
    ("B doors",       "T",  (18.5, 15.0), (19.8, -1.0),    [((13.0, 15.0), B_PLANT), ((13.0, 15.0), (30.0, 9.0))]),
    ("B ramp",        "T",  (28.0, 30.0), (21.0, -1.0), [((30.5, 37.0), (24.8, 21.0)), ((27.0, 33.0), (30.0, 20.8))]),
    ("B platforma",   "T",  (44.0, 20.0), (42.0, -8.0),  [((47.5, 22.0), (34.0, 6.0)), ((47.5, 25.0), (30.0, 8.0))]),
    ("Mid doors",     "T",  (0.0, 7.5), (-4.0, -26.5),     [((-1.0, -20.0), (1.0, 9.0)), ((1.0, -24.0), (-1.0, 10.0))]),
    ("Long chiqishi", "CT", (-44.0, 5.5), (-29.0, 37.5),  [((-44.0, 20.0), (-44.0, -12.0)), ((-47.0, 20.0), (-41.0, -10.0))]),
    ("Tunnel chiqishi", "CT", (44.0, 5.5), (30.0, 34.5),  [((44.0, 20.0), (44.0, -12.0)), ((47.0, 20.0), (41.0, -10.0))]),
    ("Top mid",       "CT", (0.0, -21.0), (6.0, 11.0),     [((0.0, 7.0), (0.0, -25.0))]),
]

# ------------------------------------------------------------------ botlar uchun strategik nuqtalar (nom, tur, jamoa, x, z)
AI_POINTS = [
    ("A plant", "plant", "T", -40.0, 13.0),
    ("A platforma", "hold", "CT", -47.5, 22.5),
    ("A default orqasi", "hold", "CT", -31.5, 22.0),
    ("A CT tomoni", "hold", "CT", -19.5, 25.0),
    ("A CT yo'li", "retake", "CT", -14.0, 15.0),
    ("A ramp", "retake", "CT", -28.0, 38.0),
    ("Long chiqishi", "entry", "T", -44.0, 3.0),
    ("Short chiqishi", "entry", "T", -22.0, 3.0),
    ("Long corner", "hold", "T", -34.0, -24.0),
    ("Long pit", "lurk", "T", -32.0, -10.0),
    ("Outside long", "rotate", "T", -31.0, -38.0),
    ("Long doors", "entry", "T", -20.0, -42.0),
    ("Catwalk", "rotate", "T", -22.0, -10.0),
    ("B plant", "plant", "T", 40.0, 13.0),
    ("B platforma", "hold", "CT", 47.5, 22.5),
    ("B default orqasi", "hold", "CT", 34.0, 22.0),
    ("B o'rtasi", "hold", "CT", 40.0, 14.0),
    ("B doors ichi", "hold", "CT", 20.0, 15.0),
    ("B doors", "retake", "CT", 14.0, 15.0),
    ("B ramp", "retake", "CT", 28.0, 38.0),
    ("Tunnel chiqishi", "entry", "T", 44.0, 3.0),
    ("Window chiqishi", "entry", "T", 22.0, 3.0),
    ("Tunnel cho'ntagi", "lurk", "T", 29.5, -12.0),
    ("Upper tunnels", "rotate", "T", 31.0, -38.0),
    ("Mid-window", "rotate", "T", 12.0, -6.0),
    ("Top mid chap", "hold", "T", -10.0, -22.5),
    ("Top mid o'ng", "hold", "T", 10.0, -28.0),
    ("Mid", "entry", "T", 0.0, -6.0),
    ("Mid doors", "hold", "CT", 0.0, 8.0),
    ("CT mid cho'ntagi", "hold", "CT", 7.0, 14.5),
    ("CT mid g'arb", "rotate", "CT", -9.0, 30.0),
    ("CT mid sharq", "rotate", "CT", 9.0, 30.0),
    ("CT spawn", "rotate", "CT", 0.0, 42.0),
    ("T spawn", "rotate", "T", 0.0, -47.0),
]

# ================================================================== 3-bosqich: bot o'yinlari uchun taktikalar
# Yo'llar (metr). Oxirgi nuqta — "kutish joyi": guruh shu yerda hujum vaqtini kutadi.
T_ROUTES = {
    "LONG":    [(-20.0, -42.0), (-31.0, -38.0), (-32.0, -22.0), (-40.0, -17.0), (-44.0, -8.0)],
    "SHORT":   [(-7.0, -37.0), (-12.0, -26.0), (-18.0, -21.0), (-22.0, -14.0), (-22.0, -3.0)],
    "TUNNELS": [(20.0, -42.0), (31.0, -38.0), (32.0, -22.0), (40.0, -17.0), (44.0, -8.0)],
    "WINDOW":  [(7.0, -37.0), (12.0, -26.0), (18.0, -21.0), (22.0, -14.0), (22.0, -3.0)],
    "MID":     [(-7.0, -37.0), (-9.0, -31.0), (0.0, -21.0), (0.0, -12.0), (0.0, -5.0)],
    "MIDWIN":  [(7.0, -37.0), (9.0, -31.0), (0.0, -21.0), (3.0, -7.0), (12.0, -6.0), (21.0, -5.0)],
}
# Hujum boshlanganda kutish joyidan site'gacha: (kirish nuqtalari)
T_ENTRY = {
    "LONG": [(-44.0, 6.0)], "SHORT": [(-23.5, 6.5)], "TUNNELS": [(44.0, 6.0)], "WINDOW": [(23.5, 6.5)],
    "MID_A": [(0.0, 7.0), (-8.0, 9.0), (-15.0, 15.0)], "MID_B": [(0.0, 7.0), (8.0, 7.0), (15.0, 15.0)],
    "MIDWIN": [(23.5, 6.5)],
}
# Bomba o'rnatilgandan keyin T lar turadigan joylar: (joy, qaraydigan nuqta)
T_POSTPLANT = {
    "A": [((-44.0, 8.0), (-28.0, 32.0)), ((-30.0, 9.0), (-14.0, 15.0)), ((-36.0, 24.5), (-28.0, 32.0)),
          ((-47.5, 22.5), (-28.0, 30.0)), ((-25.0, 11.0), (-14.0, 15.0))],
    "B": [((44.0, 8.0), (28.0, 32.0)), ((30.0, 9.0), (14.0, 15.0)), ((36.0, 24.5), (28.0, 32.0)),
          ((47.5, 22.5), (28.0, 30.0)), ((25.0, 11.0), (14.0, 15.0))],
}
# T taktikalari: nom, site, guruhlar [(yo'l, kirish, odam soni, bomba shu guruhdami)], smoke'lar, hujum vaqti (s, oraliq)
T_STRATS = [
    ("A split (Long + Short)", "A", [("LONG", "LONG", 2, True), ("SHORT", "SHORT", 2, False), ("MID", "MID_A", 1, False)],
     ["A CT", "A ramp", "A platforma"], (28.0, 40.0)),
    ("A rush (Long)", "A", [("LONG", "LONG", 4, True), ("SHORT", "SHORT", 1, False)], ["A platforma"], (17.0, 19.0)),
    ("B split (Tunnels + Window)", "B", [("TUNNELS", "TUNNELS", 2, True), ("WINDOW", "WINDOW", 2, False), ("MID", "MID_B", 1, False)],
     ["B doors", "B ramp", "B platforma"], (28.0, 40.0)),
    ("B rush (Tunnels)", "B", [("TUNNELS", "TUNNELS", 4, True), ("WINDOW", "WINDOW", 1, False)], ["B platforma"], (17.0, 19.0)),
    ("Mid → B (Mid-window)", "B", [("MIDWIN", "MIDWIN", 2, True), ("TUNNELS", "TUNNELS", 2, False), ("MID", "MID_B", 1, False)],
     ["Mid doors", "B doors", "B ramp"], (26.0, 36.0)),
    ("Mid → A (Mid doors, A CT)", "A", [("MID", "MID_A", 3, True), ("SHORT", "SHORT", 2, False)],
     ["Mid doors", "A ramp", "A platforma"], (24.0, 34.0)),
    ("Mid → B (Mid doors, B doors)", "B", [("MID", "MID_B", 3, True), ("WINDOW", "WINDOW", 2, False)],
     ["Mid doors", "B ramp", "B platforma"], (24.0, 34.0)),
    ("Default → A (kech)", "A", [("LONG", "LONG", 1, True), ("SHORT", "SHORT", 1, False), ("MID", "MID_A", 1, False),
                               ("TUNNELS", "LONG", 1, False), ("WINDOW", "SHORT", 1, False)], ["A CT", "A ramp"], (50.0, 65.0)),
    ("Default → B (kech)", "B", [("TUNNELS", "TUNNELS", 1, True), ("WINDOW", "WINDOW", 1, False), ("MID", "MID_B", 1, False),
                               ("LONG", "TUNNELS", 1, False), ("SHORT", "WINDOW", 1, False)], ["B doors", "B ramp"], (50.0, 65.0)),
]
# CT turish joylari: nom -> (joy, qaraydigan nuqta, qaysi site/hudud)
CT_SPOTS = {
    "A platforma": ((-47.5, 22.5), (-44.0, 3.0), "A"),
    "A CT tomoni": ((-19.5, 25.0), (-22.0, 6.0), "A"),
    "A default": ((-31.5, 22.0), (-40.0, 4.0), "A"),
    "Mid doors": ((-4.0, 7.5), (0.0, 4.0), "M"),      # eshikka qiyshiq burchakda: mid dan to'g'ri ko'rinmaydi
    "CT mid": ((6.0, 7.5), (0.0, 4.0), "M"),
    "B platforma": ((47.5, 22.5), (44.0, 3.0), "B"),
    "B CT tomoni": ((19.5, 25.0), (22.0, 6.0), "B"),
    "B default": ((31.5, 22.0), (40.0, 4.0), "B"),
}
CT_SETUPS = [
    ("2-1-2", ["A platforma", "A CT tomoni", "Mid doors", "B platforma", "B CT tomoni"]),
    ("3-1-1 (A kuchli)", ["A platforma", "A CT tomoni", "A default", "Mid doors", "B platforma"]),
    ("1-1-3 (B kuchli)", ["A platforma", "Mid doors", "B platforma", "B CT tomoni", "B default"]),
    ("2-2-1 (mid kuchli)", ["A platforma", "A CT tomoni", "Mid doors", "CT mid", "B platforma"]),
    ("1-2-2 (mid kuchli)", ["A platforma", "Mid doors", "CT mid", "B platforma", "B CT tomoni"]),
]
