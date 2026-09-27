extends RefCounted
## O'yinchi yoki botning jihozlari va statistikasi (CS2): pul, qurollar, o'qlar, zirh, kaska, kit, granatalar, Zeus;
## o'ldirish/o'lish/assist, boshga tegish, zarar (ADR uchun).

const Rules := preload("res://scripts/cs_rules.gd")

var name := ""
var money := Rules.START_MONEY
var primary: Resource = null
var secondary: Resource = null
var zeus := false
var zeus_ready_at := 0.0
var grenades: Array = []                ## ["flash", "smoke", ...] — tashlash tartibida
var armor := 0.0
var helmet := false
var kit := false
var ammo := {}                          ## weapon_id -> [magazin, zaxira]
var kills := 0
var deaths := 0
var assists := 0
var hs := 0
var damage := 0.0
var rounds := 0
var round_damage := {}                  ## shu raundda kimga qancha zarar (assist uchun)
var round_kills := 0


func reset_match() -> void:
	money = Rules.START_MONEY
	strip_all()
	kills = 0
	deaths = 0
	assists = 0
	hs = 0
	damage = 0.0
	rounds = 0


## o'lganda (yoki yarim vaqtda): hamma narsa yo'qoladi; keyingi raundda standart to'pponcha
func strip_all() -> void:
	primary = null
	secondary = null
	zeus = false
	grenades = []
	armor = 0.0
	helmet = false
	kit = false
	ammo = {}


func add_money(v: int) -> void:
	money = clampi(money + v, 0, Rules.MAX_MONEY)


## raund boshida: standart to'pponcha (bo'lmasa), hamma qurollarga o'q to'ladi (CS2 dagidek)
func round_start(team: String) -> void:
	round_damage = {}
	round_kills = 0
	rounds += 1
	if secondary == null:
		secondary = Rules.weapon(Rules.DEFAULT_PISTOL[team])
	if not team == "CT":
		kit = false
	for w in [primary, secondary]:
		if w:
			ammo[w.weapon_id] = [w.magazine_size, w.reserve_ammo]


func give(w: Resource) -> void:
	if w.slot == 1:
		primary = w
	else:
		secondary = w
	ammo[w.weapon_id] = [w.magazine_size, w.reserve_ammo]


func grenade_count(type: String) -> int:
	return grenades.count(type)


func can_take_grenade(type: String) -> bool:
	var g: Dictionary = Rules.GRENADES[type]
	if grenades.size() >= Rules.MAX_GRENADES:
		return false
	# molotov va yondiruvchi — bitta o'rin
	if type in ["molotov", "incendiary"] and (grenade_count("molotov") + grenade_count("incendiary")) > 0:
		return false
	return grenade_count(type) < int(g.max)


func hs_pct() -> int:
	return int(round(100.0 * hs / kills)) if kills > 0 else 0


func adr() -> int:
	return int(round(damage / maxi(1, rounds)))


## narx (CS2): qurol, granata yoki jihoz; −1 — bunday narsa yo'q
func price_of(item: String) -> int:
	match item:
		"kevlar":
			return Rules.KEVLAR
		"vesthelm":
			return Rules.HELMET if armor >= 100.0 and not helmet else Rules.KEVLAR_HELMET
		"kit":
			return Rules.KIT
	if Rules.GRENADES.has(item):
		return int(Rules.GRENADES[item].price)
	var w: Resource = Rules.weapon(item)
	return int(w.price) if w else -1


## sotib olish mumkinmi (pul, tomon, cheklovlar) — sabab matni (bo'sh — mumkin)
func buy_block_reason(item: String, team: String) -> String:
	var p := price_of(item)
	if p < 0:
		return "yo'q"
	match item:
		"kevlar":
			if armor >= 100.0:
				return "bor"
		"vesthelm":
			if armor >= 100.0 and helmet:
				return "bor"
		"kit":
			if team != "CT":
				return "faqat CT"
			if kit:
				return "bor"
		"zeus":
			if zeus:
				return "bor"
	if Rules.GRENADES.has(item):
		var g: Dictionary = Rules.GRENADES[item]
		if g.side != "both" and g.side != team:
			return "faqat " + g.side
		if not can_take_grenade(item):
			return "joy yo'q"
	else:
		var w: Resource = Rules.weapon(item)
		if w and item != "zeus":
			if w.side != "both" and w.side != team:
				return "faqat " + w.side
			if (w.slot == 1 and primary == w) or (w.slot == 2 and secondary == w):
				return "bor"
	if p > money:
		return "pul yetmaydi"
	return ""


## sotib olish: pul yechiladi va narsa beriladi. Qurol bo'lsa — qaytaradi (qo'lga olish uchun)
func try_buy(item: String, team: String) -> bool:
	if buy_block_reason(item, team) != "":
		return false
	money -= price_of(item)
	match item:
		"kevlar":
			armor = 100.0
		"vesthelm":
			armor = 100.0
			helmet = true
		"kit":
			kit = true
		"zeus":
			zeus = true
		_:
			if Rules.GRENADES.has(item):
				grenades.append(item)
			else:
				give(Rules.weapon(item))
	return true
