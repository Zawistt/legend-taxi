extends RefCounted
## CS2 qoidalari (iqtisod, raund, zirh, granatalar) — hamma raqamlar shu yerda.
## Manba: CS2 raqobat rejimi (MR12, 13 g'alabagacha; 12:12 da qo'shimcha vaqt MR3, $12500).
## 3v3 xaritasi CS2 "Wingman" qoidalarida (MR8, 9 g'alabagacha) — raund vaqtlari map_data.gd dagi ROUND da.

const START_MONEY := 800
const MAX_MONEY := 16000
const OT_MONEY := 12500
const OT_HALF := 3                      ## qo'shimcha vaqtning yarmi (raund)
## raund g'alabasi uchun jamoaga
const WIN_REWARD := {"elim": 3250, "time": 3250, "bomb": 3500, "defuse": 3500}
## ketma-ket mag'lubiyat bonusi (CS2: yutqazganda +1, yutganda −1; birinchi raund yutqazilsa $1900)
const LOSS_BONUS := [1400, 1900, 2400, 2900, 3400]
const START_LOSS := 1
const PLANT_TEAM_BONUS := 800           ## T yutqazdi, lekin bomba o'rnatilgan — har bir T ga
const PLANT_REWARD := 300               ## bombani o'rnatganga
const DEFUSE_REWARD := 300              ## zararsizlantirganga
const ASSIST_DAMAGE := 41               ## shuncha zarar bergan (o'ldirmagan) — assist
## jihozlar
const KEVLAR := 650
const KEVLAR_HELMET := 1000
const HELMET := 350
const KIT := 400
const MAX_GRENADES := 4
## granatalar: nom, narx, o'ldirish mukofoti, kim oladi, ko'pi bilan
const GRENADES := {
	"he": {"name": "HE granata", "price": 300, "reward": 300, "side": "both", "max": 1},
	"flash": {"name": "Flesh", "price": 200, "reward": 300, "side": "both", "max": 2},
	"smoke": {"name": "Tutun", "price": 300, "reward": 300, "side": "both", "max": 1},
	"molotov": {"name": "Molotov", "price": 400, "reward": 300, "side": "T", "max": 1},
	"incendiary": {"name": "Yondiruvchi", "price": 500, "reward": 300, "side": "CT", "max": 1},
}
const DEFAULT_PISTOL := {"T": "glock", "CT": "usp"}
const PLANT_RADIUS := 2.8               ## bomba faqat belgilangan aylana ichiga (site markazidagi doira)
const BOMB_DAMAGE := 500.0
const BOMB_SIGMA := 14.8                ## CS2: 1750 birlik radius / 3 ≈ 14.8 m (Gauss so'nishi)
const BOMB_RADIUS := 44.0
const BOMB_CODE := "7355608"
const ZEUS_RECHARGE := 30.0
## qurollar (weapons/*.tres) — eksport qilingan o'yinda papkani o'qib bo'lmaydi, ro'yxat shu yerda
const WEAPON_IDS := ["glock", "usp", "p250", "tec9", "fiveseven", "deagle", "pistol",
	"mac10", "mp9", "ump45", "p90", "smg",
	"galil", "famas", "ak47", "m4a4", "ssg08", "awp", "rifle", "vanguard", "sniper",
	"nova", "xm1014", "m249", "shotgun", "knife", "zeus"]
const WEAPON_FILE := {"pistol": "pistol", "smg": "smg", "rifle": "rifle", "vanguard": "vanguard", "sniper": "sniper",
	"shotgun": "shotgun", "knife": "knife"}

static var _cat := {}


## id -> WeaponData (bir marta yuklanadi). Legend qurollari ichki id si bilan ham topiladi (lar_01, spectre_smg, ...).
static func catalog() -> Dictionary:
	if _cat.is_empty():
		for f in WEAPON_IDS:
			var w: Resource = load("res://weapons/%s.tres" % f)
			_cat[w.weapon_id] = w
	return _cat


static func weapon(id: String) -> Resource:
	return catalog().get(id)


static func loss_bonus(count: int) -> int:
	return LOSS_BONUS[clampi(count, 0, LOSS_BONUS.size() - 1)]


## bomba portlashi zarari (masofa bo'yicha, zirhsiz)
static func bomb_damage(dist: float) -> float:
	if dist > BOMB_RADIUS:
		return 0.0
	return BOMB_DAMAGE * exp(-(dist * dist) / (2.0 * BOMB_SIGMA * BOMB_SIGMA))
