# Qumtepa v2 layout — 25 x 25 cells, 2 m each (50 m x 50 m)
# '#' building   '.' open sky   ',' covered corridor (4.2 m)
# 'm' covered mid (5.2 m)   'T' T spawn   'C' CT spawn   'A' / 'B' bomb sites (open sky)
#            0         1         2
#            0123456789012345678901234
LAYOUT = """
#########################
##,,,,,,,TTTTTTT,,,,,####
##,,,#,,,TTTTTTT,,,,,####
##..#####TTTTTTT####,,###
#...#######,,,######,,###
#...#####.......####,,###
#...##,,,.......###,,,###
#...##,,#.......,,,,,,###
#...##,,#.......##,,#####
#...##,,##mmm#####,,#####
#...##,,##mmm#####,,#####
#...##,,##mmm#####,,#####
#AAAAAAAA#mmm###BBBBBBBB#
#AAAAAAAA#mmmmm#BBBBBBBB#
#AAAAAAAA#####m#BBBBBBBB#
#AAAAAAAA##.....BBBBBBBB#
#AAAAAAAA##..#.#BBBBBBBB#
#AAAAAAAA##..#.#BBBBBBBB#
#AAAAAAAA##...##BBBBBBBB#
####...####,,,####...####
####,,,,CCCCCCCCC,,,,####
####,,,,CCCCCCCCC,,,,####
########CCCCCCCCC########
#########################
#########################
"""
GRID = [list(r) for r in LAYOUT.strip("\n").split("\n")]
assert len(GRID) == 25 and all(len(r) == 25 for r in GRID), [len(r) for r in GRID]

COVER = {",": 4.2, "m": 5.2, "T": 5.0, "C": 5.0}


def cell_center(c, r):
    return (-24.0 + 2 * c, -24.0 + 2 * r)


# callout names: (col0, col1, row0, row1) inclusive
CALLOUTS = {
    "T spawn": (9, 15, 1, 3),
    "Long doors": (2, 8, 1, 2),
    "Long": (1, 3, 3, 11),
    "Short (catwalk)": (6, 7, 6, 11),
    "Top mid": (9, 15, 4, 8),
    "Mid": (10, 12, 9, 13),
    "Mid doors": (13, 14, 13, 14),
    "CT mid": (11, 14, 15, 18),
    "B doors": (15, 15, 15, 15),
    "Upper tunnels": (16, 21, 1, 5),
    "Lower tunnels": (16, 21, 6, 11),
    "A site": (1, 8, 12, 18),
    "B site": (16, 23, 12, 18),
    "A ramp": (4, 7, 19, 21),
    "B ramp": (17, 20, 19, 21),
    "CT spawn": (8, 16, 20, 22),
}

T_SPAWN = (0.0, -20.0)
CT_SPAWN = (0.0, 18.0)
A_PLANT = (-15.0, 8.0)
B_PLANT = (16.0, 7.0)
MID_DOORS = (4.0, 4.0)

# routes: name, team, list of waypoints (start, via..., end)
ROUTES = [
    ("T → A (Long)", "T", [T_SPAWN, (-14.0, -22.0), (-20.0, -6.0), A_PLANT]),
    ("T → A (Short)", "T", [T_SPAWN, (0.0, -12.0), (-11.0, -4.0), A_PLANT]),
    ("T → B (Tunnels)", "T", [T_SPAWN, (12.0, -21.0), (13.0, -5.0), B_PLANT]),
    ("T → B (Mid → Lower)", "T", [T_SPAWN, (0.0, -12.0), (10.0, -10.0), (13.0, -5.0), B_PLANT]),
    ("T → Mid doors", "T", [T_SPAWN, (-2.0, -2.0), MID_DOORS]),
    ("CT → A", "CT", [CT_SPAWN, (-14.0, 17.0), A_PLANT]),
    ("CT → B (Ramp)", "CT", [CT_SPAWN, (14.0, 17.0), B_PLANT]),
    ("CT → B (B doors)", "CT", [CT_SPAWN, (2.0, 10.0), (6.5, 6.0), B_PLANT]),
    ("CT → Mid doors", "CT", [CT_SPAWN, (2.0, 10.0), MID_DOORS]),
]
ROTATIONS = [
    ("CT rotatsiya A → B", "CT", [A_PLANT, B_PLANT]),
    ("T rotatsiya Long → Tunnels", "T", [(-20.0, -8.0), (13.0, -5.0)]),
]

# ---------------------------------------------------------------- stage 2: gameplay volumes (meters: x0, z0, x1, z1)
BOMBSITES = {"A": (-23.0, -1.0, -7.0, 13.0), "B": (7.0, -1.0, 23.0, 13.0)}
BUYZONES = {"T": (-7.0, -23.0, 7.0, -15.0), "CT": (-9.0, 13.0, 9.0, 21.0)}

# strategic points for bots: name, kind, team, x, y, z
STRATEGIC = [
    ("A plant", "plant", "T", -15.0, 0.0, 8.0),
    ("A default orqasi", "hold", "CT", -17.0, 0.0, 6.2),
    ("A platforma", "hold", "CT", -21.7, 1.3, 10.0),
    ("A CT tomoni", "hold", "CT", -9.4, 0.0, 12.4),
    ("Long chiqishi", "entry", "T", -20.0, 0.0, -1.5),
    ("Short chiqishi", "entry", "T", -11.0, 0.0, -1.5),
    ("A ramp", "entry", "CT", -14.0, 0.0, 14.0),
    ("Long burchagi", "lurk", "T", -18.2, 0.0, -10.6),
    ("B plant", "plant", "T", 16.0, 0.0, 7.0),
    ("B platforma", "hold", "CT", 21.9, 1.3, 6.5),
    ("B quti orqasi", "hold", "CT", 10.6, 0.0, 5.2),
    ("B doors ichi", "hold", "CT", 9.3, 0.0, 6.0),
    ("Tunnel chiqishi", "entry", "T", 13.0, 0.0, -1.5),
    ("B doors", "entry", "CT", 6.0, 0.0, 6.0),
    ("B ramp", "entry", "CT", 14.0, 0.0, 14.0),
    ("Lower tunnels", "lurk", "T", 13.0, 0.0, -6.0),
    ("Top mid quti", "hold", "T", 5.4, 0.0, -11.6),
    ("Mid doors", "hold", "CT", 4.0, 0.0, 4.8),
    ("CT mid cho'ntagi", "hold", "CT", 4.0, 0.0, 8.4),
    ("Mid yo'lak", "entry", "T", -2.0, 0.0, -3.0),
]

# ======================================================= STAGE 2: gameplay data
# 5 spawn slots per team: (x, z); T faces south (+z), CT faces north (-z)
SPAWNS = {
    "T": [(-4.0, -20.0), (-2.0, -20.0), (0.0, -20.0), (2.0, -20.0), (4.0, -20.0)],
    "CT": [(-4.0, 18.0), (-2.0, 18.0), (0.0, 18.0), (2.0, 18.0), (4.0, 18.0)],
}
# bomb plant zones: name -> (x0, z0, x1, z1)
BOMB_ZONES = {"A": (-21.5, 1.5, -9.5, 12.5), "B": (10.0, 1.5, 21.5, 12.0)}
# buy zones: team -> (x0, z0, x1, z1)
BUY_ZONES = {"T": (-7.0, -23.0, 7.0, -17.0), "CT": (-9.0, 15.0, 9.0, 21.0)}
# round rules (seconds) — tuned for a 50 m map (sites reached in 5–9 s)
ROUND = {"freeze": 5.0, "buy_time": 20.0, "round_time": 85.0, "bomb_timer": 35.0,
         "plant_time": 3.0, "defuse_time": 7.0, "defuse_time_kit": 3.5, "round_end": 5.0, "win_rounds": 13}
# strategic points for bots: (label, type, team, x, z)
AI_POINTS = [
    ("A plant", "plant", "T", -15.0, 8.0),
    ("A back platform", "hold", "CT", -21.8, 10.0),
    ("A default box", "hold", "CT", -17.6, 6.4),
    ("A CT side", "hold", "CT", -10.6, 12.3),
    ("A long exit", "entry", "T", -20.0, -2.2),
    ("A short exit", "entry", "T", -11.0, -2.2),
    ("A ramp", "retake", "CT", -14.0, 14.0),
    ("B plant", "plant", "T", 16.0, 7.0),
    ("B back platform", "hold", "CT", 22.0, 6.5),
    ("B doors", "hold", "CT", 9.3, 6.0),
    ("B tunnel box", "hold", "CT", 17.0, 2.9),
    ("B tunnel exit", "entry", "T", 13.0, -2.2),
    ("B ramp", "retake", "CT", 14.0, 14.0),
    ("Top mid", "hold", "T", 0.0, -11.0),
    ("Mid corridor", "hold", "T", -2.0, -2.0),
    ("CT mid", "hold", "CT", 0.0, 8.0),
    ("Catwalk", "rotate", "T", -10.0, -8.0),
    ("Lower tunnels", "rotate", "T", 13.0, -7.5),
    ("Upper tunnels", "rotate", "T", 16.2, -14.5),
    ("Long corner", "hold", "T", -21.0, -10.5),
    ("Long doors", "entry", "T", -14.0, -22.0),
    ("CT spawn", "rotate", "CT", 0.0, 18.0),
]
