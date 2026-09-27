## Shahar bo'laklarini (shahar/bolak_X_Z.glb) o'yinchi atrofida oqim bilan
## yuklaydi va uzoqlashganda xotiradan o'chiradi.
class_name Shahar
extends Node3D

const INDEKS := "res://shahar/indeks.json"
@export var korish_radiusi := 900.0      ## shu masofadagi bo'laklar yuklanadi
@export var ochirish_radiusi := 1200.0   ## bundan uzoqlari o'chiriladi
@export var bir_vaqtda := 6              ## parallel yuklanadigan fayllar soni

var malumot: Dictionary
var _bolaklar: Array = []
var _yuklangan: Dictionary = {}          # fayl -> Node3D
var _kutilmoqda: Dictionary = {}         # yo'l -> bo'lak ma'lumoti
var _bolak_olchami := 400.0


func _init() -> void:
	name = "Shahar"
	var matn := FileAccess.get_file_as_string(INDEKS)
	malumot = JSON.parse_string(matn)
	_bolaklar = malumot["bolaklar"]
	_bolak_olchami = float(malumot["bolak"])


func yuklangan_soni() -> int:
	return _yuklangan.size()


func kutilayotgan_soni() -> int:
	return _kutilmoqda.size()


func _markaz(b: Dictionary) -> Vector2:
	return Vector2(float(b["x"]) + _bolak_olchami / 2, float(b["z"]) + _bolak_olchami / 2)


## Bir zumda (sinxron) yuklash — boshlanishda mashina ostidagi bo'laklar uchun.
func darhol_yukla(pos: Vector3, radius: float) -> void:
	var p := Vector2(pos.x, pos.z)
	for b in _bolaklar:
		if _markaz(b).distance_to(p) < radius and not _yuklangan.has(b["fayl"]):
			var ps := load("res://shahar/" + b["fayl"]) as PackedScene
			_qosh(b, ps)


func yangila(pos: Vector3) -> void:
	var p := Vector2(pos.x, pos.z)
	# kerakli bo'laklar — yaqinidan boshlab
	var kerak: Array = []
	for b in _bolaklar:
		var d := _markaz(b).distance_to(p)
		var f: String = b["fayl"]
		if d < korish_radiusi and not _yuklangan.has(f):
			kerak.append([d, b])
		elif d > ochirish_radiusi and _yuklangan.has(f):
			_yuklangan[f].queue_free()
			_yuklangan.erase(f)
	kerak.sort_custom(func(a, c): return a[0] < c[0])
	for x in kerak:
		if _kutilmoqda.size() >= bir_vaqtda:
			break
		var yol: String = "res://shahar/" + x[1]["fayl"]
		if not _kutilmoqda.has(yol):
			ResourceLoader.load_threaded_request(yol, "PackedScene")
			_kutilmoqda[yol] = x[1]
	# tayyor bo'lganlarini sahnaga qo'shish (kadrda ko'pi bilan 2 ta — qotib qolmasin)
	var qoshildi := 0
	for yol in _kutilmoqda.keys():
		var holat := ResourceLoader.load_threaded_get_status(yol)
		if holat == ResourceLoader.THREAD_LOAD_LOADED:
			var b: Dictionary = _kutilmoqda[yol]
			_kutilmoqda.erase(yol)
			if not _yuklangan.has(b["fayl"]):
				_qosh(b, ResourceLoader.load_threaded_get(yol))
				qoshildi += 1
			if qoshildi >= 2:
				break
		elif holat == ResourceLoader.THREAD_LOAD_FAILED or holat == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
			push_warning("Bo'lak yuklanmadi: " + yol)
			_kutilmoqda.erase(yol)


func _qosh(b: Dictionary, ps: PackedScene) -> void:
	if ps == null:
		return
	var n := ps.instantiate() as Node3D
	n.position = Vector3(float(b["x"]), 0.0, float(b["z"]))
	Materiallar.qoy(n)
	if b.has("obyektlar"):
		var d = JSON.parse_string(FileAccess.get_file_as_string("res://shahar/" + b["obyektlar"]))
		if d is Dictionary:
			Obyektlar.qosh(n, d)
	add_child(n)
	_yuklangan[b["fayl"]] = n
