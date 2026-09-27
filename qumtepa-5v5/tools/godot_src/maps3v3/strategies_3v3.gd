extends RefCounted
## 3v3 (Qumtepa v2 low-poly, 50×50 m) — botlar taktikasi. Nuqtalar xaritaning AIPoints belgilaridan olingan
## (A plant, A long exit, Catwalk, Top mid, Upper/Lower tunnels, B doors, CT mid, ...). Format — strategies.gd (5v5) bilan bir xil.
## T spawn shimolda (z −20), CT janubda (z 18), A g'arbda (x −15), B sharqda (x 16).

const PLANT := {"A": Vector3(-15, 0, 8), "B": Vector3(16, 0, 7)}
const SMOKE_R := 2.4
const SMOKE_TIME := 15.0
const REGION := {"Long doors": "A", "Long": "A", "Short (catwalk)": "A", "A site": "A", "A ramp": "A",
	"B doors": "B", "Upper tunnels": "B", "Lower tunnels": "B", "B site": "B", "B ramp": "B",
	"Top mid": "M", "Mid": "M", "Mid doors": "M", "CT mid": "M"}
const T_ROUTES := {
	"LONG": [Vector3(-14, 0, -22), Vector3(-21, 0, -10.5)],
	"SHORT": [Vector3(0, 0, -11), Vector3(-10, 0, -8)],
	"TUNNELS": [Vector3(16.2, 0, -14.5), Vector3(13, 0, -7.5)],
	"MID": [Vector3(0, 0, -11), Vector3(-2, 0, -2)],
}
const T_ENTRY := {
	"LONG": [Vector3(-20, 0, -2.2)],
	"SHORT": [Vector3(-11, 0, -2.2)],
	"TUNNELS": [Vector3(13, 0, -2.2)],
	"MID_A": [Vector3(0, 0, 8), Vector3(-10.6, 0, 12.3)],
	"MID_B": [Vector3(0, 0, 8), Vector3(9.3, 0, 6)],
}
## o'rnatilgandan keyin: [joy, qaraydigan nuqta]
const T_POSTPLANT := {
	"A": [[Vector3(-17.6, 0, 6.4), Vector3(-14, 0, 14)], [Vector3(-21.8, 1.3, 10), Vector3(-10.6, 0, 12.3)], [Vector3(-20, 0, -2.2), Vector3(-15, 0, 8)]],
	"B": [[Vector3(17, 0, 2.9), Vector3(14, 0, 14)], [Vector3(22, 1.3, 6.5), Vector3(9.3, 0, 6)], [Vector3(13, 0, -2.2), Vector3(16, 0, 7)]],
}
## [nom, site, [[yo'l, kirish, odam, bomba], ...], [smoke'lar], [hujum vaqti dan, gacha]]
const T_STRATS := [
	["A split (Long + Short)", "A", [["LONG", "LONG", 2, true], ["SHORT", "SHORT", 1, false]], ["A CT"], [9.0, 16.0]],
	["A rush (Long)", "A", [["LONG", "LONG", 3, true]], ["A ramp"], [4.0, 6.0]],
	["B split (Tunnels + Mid)", "B", [["TUNNELS", "TUNNELS", 2, true], ["MID", "MID_B", 1, false]], ["B ramp"], [9.0, 16.0]],
	["B rush (Tunnels)", "B", [["TUNNELS", "TUNNELS", 3, true]], ["B ramp"], [4.0, 6.0]],
	["Mid → A", "A", [["MID", "MID_A", 2, true], ["SHORT", "SHORT", 1, false]], ["CT mid", "A ramp"], [8.0, 14.0]],
	["Mid → B", "B", [["MID", "MID_B", 2, true], ["TUNNELS", "TUNNELS", 1, false]], ["CT mid", "B ramp"], [8.0, 14.0]],
	["Default → A (kech)", "A", [["LONG", "LONG", 1, true], ["SHORT", "SHORT", 1, false], ["MID", "MID_A", 1, false]], ["A CT"], [22.0, 32.0]],
	["Default → B (kech)", "B", [["TUNNELS", "TUNNELS", 1, true], ["MID", "MID_B", 1, false], ["SHORT", "LONG", 1, false]], ["B ramp"], [22.0, 32.0]],
]
## nom -> [joy, qaraydigan nuqta, hudud]
const CT_SPOTS := {
	"A platforma": [Vector3(-21.8, 1.3, 10), Vector3(-20, 0, -2.2), "A"],
	"A CT tomoni": [Vector3(-10.6, 0, 12.3), Vector3(-11, 0, -2.2), "A"],
	"A ramp": [Vector3(-14, 0, 14), Vector3(-15, 0, 4), "A"],
	"CT mid": [Vector3(0, 0, 8), Vector3(-2, 0, -2), "M"],
	"B platforma": [Vector3(22, 1.3, 6.5), Vector3(13, 0, -2.2), "B"],
	"B doors": [Vector3(9.3, 0, 6), Vector3(13, 0, -2.2), "B"],
	"B ramp": [Vector3(14, 0, 14), Vector3(16, 0, 3), "B"],
}
const CT_SETUPS := [
	["1-1-1", ["A platforma", "CT mid", "B platforma"]],
	["2-0-1 (A kuchli)", ["A platforma", "A CT tomoni", "B platforma"]],
	["1-0-2 (B kuchli)", ["A platforma", "B platforma", "B doors"]],
	["1-1-1 (orqada)", ["A ramp", "CT mid", "B ramp"]],
]
## aylanib kelgan CT lar turadigan joylar
const ROTATE_SPOT := {
	"A": [[Vector3(-14, 0, 14), Vector3(-15, 0, 4)], [Vector3(-10.6, 0, 12.3), Vector3(-15, 0, 6)]],
	"B": [[Vector3(14, 0, 14), Vector3(16, 0, 3)], [Vector3(9.3, 0, 6), Vector3(16, 0, 3)]],
}
## smoke: nom -> [jamoa, nishon, uchish vaqti (s)]
const SMOKES := {
	"A CT": ["T", Vector3(-10.6, 0, 12.3), 1.4],
	"A ramp": ["T", Vector3(-14, 0, 14), 1.6],
	"B ramp": ["T", Vector3(14, 0, 14), 1.6],
	"CT mid": ["T", Vector3(0, 0, 8), 1.3],
}
