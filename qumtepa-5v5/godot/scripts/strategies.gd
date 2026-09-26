extends RefCounted
## AVTOMATIK YARATILGAN (tools/gen_godot5.py, layout5.py dagi 3-bosqich taktikalaridan). Qo'lda o'zgartirmang.

const PLANT := {"A": Vector3(-40, 0, 13), "B": Vector3(40, 0, 13)}
const SMOKE_R := 2.6
const SMOKE_TIME := 15.0
## callout -> hudud (CT lar qaysi site'da T ko'rganini bilishi uchun)
const REGION := {"A site": "A", "A platforma": "A", "A default": "A", "A short chiqishi": "A", "A long chiqishi": "A", "A ramp": "A", "A CT": "A", "Long": "A", "Long pit": "A", "Catwalk": "A", "B site": "B", "B platforma": "B", "B default": "B", "B window chiqishi": "B", "B tunnel chiqishi": "B", "B ramp": "B", "B doors": "B", "Lower tunnels": "B", "Tunnel cho'ntagi": "B", "B window": "B", "Mid doors": "M", "CT mid": "M", "Mid": "M", "Mid-window": "M"}
const T_ROUTES := {
	"LONG": [Vector3(-20, 0, -42), Vector3(-31, 0, -38), Vector3(-32, 0, -22), Vector3(-40, 0, -17), Vector3(-44, 0, -8)],
	"SHORT": [Vector3(-7, 0, -37), Vector3(-12, 0, -26), Vector3(-18, 0, -21), Vector3(-22, 0, -14), Vector3(-22, 0, -3)],
	"TUNNELS": [Vector3(20, 0, -42), Vector3(31, 0, -38), Vector3(32, 0, -22), Vector3(40, 0, -17), Vector3(44, 0, -8)],
	"WINDOW": [Vector3(7, 0, -37), Vector3(12, 0, -26), Vector3(18, 0, -21), Vector3(22, 0, -14), Vector3(22, 0, -3)],
	"MID": [Vector3(-7, 0, -37), Vector3(-9, 0, -31), Vector3(0, 0, -21), Vector3(0, 0, -12), Vector3(0, 0, -5)],
	"MIDWIN": [Vector3(7, 0, -37), Vector3(9, 0, -31), Vector3(0, 0, -21), Vector3(3, 0, -7), Vector3(12, 0, -6), Vector3(21, 0, -5)],
}
const T_ENTRY := {
	"LONG": [Vector3(-44, 0, 6)],
	"SHORT": [Vector3(-23.5, 0, 6.5)],
	"TUNNELS": [Vector3(44, 0, 6)],
	"WINDOW": [Vector3(23.5, 0, 6.5)],
	"MID_A": [Vector3(0, 0, 7), Vector3(-8, 0, 9), Vector3(-15, 0, 15)],
	"MID_B": [Vector3(0, 0, 7), Vector3(8, 0, 7), Vector3(15, 0, 15)],
	"MIDWIN": [Vector3(23.5, 0, 6.5)],
}
const T_POSTPLANT := {
	"A": [[Vector3(-44, 0, 8), Vector3(-28, 0, 32)], [Vector3(-30, 0, 9), Vector3(-14, 0, 15)], [Vector3(-36, 0, 24.5), Vector3(-28, 0, 32)], [Vector3(-47.5, 0, 22.5), Vector3(-28, 0, 30)], [Vector3(-25, 0, 11), Vector3(-14, 0, 15)]],
	"B": [[Vector3(44, 0, 8), Vector3(28, 0, 32)], [Vector3(30, 0, 9), Vector3(14, 0, 15)], [Vector3(36, 0, 24.5), Vector3(28, 0, 32)], [Vector3(47.5, 0, 22.5), Vector3(28, 0, 30)], [Vector3(25, 0, 11), Vector3(14, 0, 15)]],
}
## [nom, site, [[yo'l, kirish, odam, bomba], ...], [smoke'lar], [hujum vaqti dan, gacha]]
const T_STRATS := [
	["A split (Long + Short)", "A", [["LONG", "LONG", 2, true], ["SHORT", "SHORT", 2, false], ["MID", "MID_A", 1, false]], ["A CT", "A ramp", "A platforma"], [28.0, 40.0]],
	["A rush (Long)", "A", [["LONG", "LONG", 4, true], ["SHORT", "SHORT", 1, false]], ["A platforma"], [17.0, 19.0]],
	["B split (Tunnels + Window)", "B", [["TUNNELS", "TUNNELS", 2, true], ["WINDOW", "WINDOW", 2, false], ["MID", "MID_B", 1, false]], ["B doors", "B ramp", "B platforma"], [28.0, 40.0]],
	["B rush (Tunnels)", "B", [["TUNNELS", "TUNNELS", 4, true], ["WINDOW", "WINDOW", 1, false]], ["B platforma"], [17.0, 19.0]],
	["Mid → B (Mid-window)", "B", [["MIDWIN", "MIDWIN", 2, true], ["TUNNELS", "TUNNELS", 2, false], ["MID", "MID_B", 1, false]], ["Mid doors", "B doors", "B ramp"], [26.0, 36.0]],
	["Mid → A (Mid doors, A CT)", "A", [["MID", "MID_A", 3, true], ["SHORT", "SHORT", 2, false]], ["Mid doors", "A ramp", "A platforma"], [24.0, 34.0]],
	["Mid → B (Mid doors, B doors)", "B", [["MID", "MID_B", 3, true], ["WINDOW", "WINDOW", 2, false]], ["Mid doors", "B ramp", "B platforma"], [24.0, 34.0]],
	["Default → A (kech)", "A", [["LONG", "LONG", 1, true], ["SHORT", "SHORT", 1, false], ["MID", "MID_A", 1, false], ["TUNNELS", "LONG", 1, false], ["WINDOW", "SHORT", 1, false]], ["A CT", "A ramp"], [50.0, 65.0]],
	["Default → B (kech)", "B", [["TUNNELS", "TUNNELS", 1, true], ["WINDOW", "WINDOW", 1, false], ["MID", "MID_B", 1, false], ["LONG", "TUNNELS", 1, false], ["SHORT", "WINDOW", 1, false]], ["B doors", "B ramp"], [50.0, 65.0]],
]
## nom -> [joy, qaraydigan nuqta, hudud]
const CT_SPOTS := {
	"A platforma": [Vector3(-47.5, 0, 22.5), Vector3(-44, 0, 3), "A"],
	"A CT tomoni": [Vector3(-19.5, 0, 25), Vector3(-22, 0, 6), "A"],
	"A default": [Vector3(-31.5, 0, 22), Vector3(-40, 0, 4), "A"],
	"Mid doors": [Vector3(-4, 0, 7.5), Vector3(0, 0, 4), "M"],
	"CT mid": [Vector3(6, 0, 7.5), Vector3(0, 0, 4), "M"],
	"B platforma": [Vector3(47.5, 0, 22.5), Vector3(44, 0, 3), "B"],
	"B CT tomoni": [Vector3(19.5, 0, 25), Vector3(22, 0, 6), "B"],
	"B default": [Vector3(31.5, 0, 22), Vector3(40, 0, 4), "B"],
}
const CT_SETUPS := [
	["2-1-2", ["A platforma", "A CT tomoni", "Mid doors", "B platforma", "B CT tomoni"]],
	["3-1-1 (A kuchli)", ["A platforma", "A CT tomoni", "A default", "Mid doors", "B platforma"]],
	["1-1-3 (B kuchli)", ["A platforma", "Mid doors", "B platforma", "B CT tomoni", "B default"]],
	["2-2-1 (mid kuchli)", ["A platforma", "A CT tomoni", "Mid doors", "CT mid", "B platforma"]],
	["1-2-2 (mid kuchli)", ["A platforma", "Mid doors", "CT mid", "B platforma", "B CT tomoni"]],
]
## aylanib kelgan CT lar turadigan joylar
const ROTATE_SPOT := {
	"A": [[Vector3(-47.5, 0, 22.5), Vector3(-44, 0, 3)], [Vector3(-19.5, 0, 25), Vector3(-22, 0, 6)], [Vector3(-31.5, 0, 22), Vector3(-40, 0, 4)]],
	"B": [[Vector3(47.5, 0, 22.5), Vector3(44, 0, 3)], [Vector3(19.5, 0, 25), Vector3(22, 0, 6)], [Vector3(31.5, 0, 22), Vector3(40, 0, 4)]],
}
## smoke: nom -> [jamoa, nishon, uchish vaqti (s, fizika bilan topilgan lineup'dan)]
const SMOKES := {
	"A CT": ["T", Vector3(-18.5, 0, 15), 3.94],
	"A ramp": ["T", Vector3(-28, 0, 30), 1.6],
	"A platforma": ["T", Vector3(-44, 0, 20), 3.9],
	"B doors": ["T", Vector3(18.5, 0, 15), 1.26],
	"B ramp": ["T", Vector3(28, 0, 30), 1.6],
	"B platforma": ["T", Vector3(44, 0, 20), 1.38],
	"Mid doors": ["T", Vector3(0, 0, 7.5), 3.7],
	"Long chiqishi": ["CT", Vector3(-44, 0, 5.5), 3.76],
	"Tunnel chiqishi": ["CT", Vector3(44, 0, 5.5), 3.88],
	"Top mid": ["CT", Vector3(0, 0, -21), 3.76],
}
