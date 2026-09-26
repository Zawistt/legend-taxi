extends SceneTree
## Smoke granatalari: har bir smoke uchun otish joyi va burchagini (lineup) topadi.
## Granata ko'z balandligidan (1.6 m) otiladi, havo qarshiligisiz ballistik yo'l bilan uchadi;
## yo'l devor, tom, bino va grenade clip'ga urilmasdan nishondan ≤ 1.8 m ga tushishi kerak.
## Ishga tushirish (godot/ papkasida): godot --headless -s res://tests/run_grenades.gd
## Natija: docs/smokes_stage3.json

const D := preload("res://tests/test_data.gd")
const MapData := preload("res://scripts/map_data.gd")
const G := 9.8
const SPEEDS := [11.0, 14.0, 17.0, 20.0]
const LAND_TOL := 1.8

var space: PhysicsDirectSpaceState3D
var nav_map: RID


func _initialize() -> void:
	_run.call_deferred()


## p0 dan v tezlik va (yaw, pitch) bilan otilgan granata qayerga tushadi: [nuqta, normal, vaqt] yoki []
func fly(p0: Vector3, vel: Vector3) -> Array:
	var p := p0
	var t := 0.0
	var dt := 0.02
	while t < 6.0:
		var np := p + vel * dt
		vel.y -= G * dt
		var q := PhysicsRayQueryParameters3D.create(p, np, 1 | 4)
		var h := space.intersect_ray(q)
		if h:
			return [h.position, h.normal, t]
		p = np
		t += dt
	return []


## Nishonga tushadigan (pastki va yuqori) burchaklar
func angles(dx: float, dy: float, v: float) -> Array:
	var out := []
	var disc := v * v * v * v - G * (G * dx * dx + 2.0 * dy * v * v)
	if disc < 0.0:
		return out
	for sgn in [-1.0, 1.0]:
		out.append(atan((v * v + sgn * sqrt(disc)) / (G * dx)))
	return out


func solve(origin: Vector3, target: Vector3) -> Dictionary:
	var eye := origin + Vector3.UP * 1.6
	var flat := Vector2(target.x - eye.x, target.z - eye.z)
	var dx := flat.length()
	var yaw := atan2(flat.x, flat.y)
	var best := {}
	for v in SPEEDS:
		for a in angles(dx, target.y - eye.y, v):
			# nishon atrofida kichik tuzatishlar: devor chetiga urilsa, yaqin burchak ishlashi mumkin
			for dp in [0.0, -0.03, 0.03, -0.06, 0.06]:
				var pitch: float = a + dp
				if pitch > 1.35 or pitch < -0.3:
					continue
				var dir := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch))
				var r := fly(eye, dir * v)
				if r.is_empty() or r[1].y < 0.7:
					continue
				var miss := Vector2(r[0].x - target.x, r[0].z - target.z).length()
				if miss <= LAND_TOL and (best.is_empty() or miss < best.miss):
					best = {"origin": [snappedf(origin.x, 0.1), snappedf(origin.z, 0.1)], "yaw_deg": snappedf(rad_to_deg(yaw), 0.1),
						"pitch_deg": snappedf(rad_to_deg(pitch), 0.1), "speed": v, "flight_s": snappedf(r[2], 0.01),
						"land": [snappedf(r[0].x, 0.1), snappedf(r[0].z, 0.1)], "miss_m": snappedf(miss, 0.01)}
	return best


func side_at(p: Vector3) -> int:
	var c := int(floor((p.x - D.MAP_MIN) / 2.0))
	var r := int(floor((p.z - D.MAP_MIN) / 2.0))
	if r < 0 or c < 0 or r >= D.SIDE_GRID.size() or c >= D.SIDE_GRID.size():
		return 9
	return D.SIDE_GRID[r][c]


func _run() -> void:
	var main: Node = load("res://main.tscn").instantiate()
	root.add_child(main)
	for i in 5:
		await physics_frame
	var pl: Node3D = main.get_node("Player")
	space = pl.get_world_3d().direct_space_state
	nav_map = pl.get_world_3d().navigation_map
	NavigationServer3D.map_force_update(nav_map)
	var results := []
	var found := 0
	print("\nSMOKE LINEUP'LARI (granata fizikasi bilan)")
	for s in D.SMOKES:
		var tgt: Vector3 = s[2]
		var base: Vector3 = s[3]
		# nomzodlar: 1 m to'rda, nishondan 6–36 m, o'z jamoasi hududida yoki talashuvli joyda;
		# rejadagi otish joyiga eng yaqinlaridan boshlab tekshiriladi
		var cands := []
		var own := 1 if s[1] == "T" else -1
		for gx in range(-36, 37):
			for gz in range(-36, 37):
				var c := Vector3(tgt.x + gx, 0, tgt.z + gz)
				var d := Vector2(gx, gz).length()
				if d < 6.0 or d > 36.0 or side_at(c) not in [own, 0]:
					continue
				cands.append(c)
		cands.sort_custom(func(a, b): return a.distance_squared_to(base) < b.distance_squared_to(base))
		var sol := {}
		var tried := 0
		for c in cands:
			var on := NavigationServer3D.map_get_closest_point(nav_map, c)
			if Vector2(on.x - c.x, on.z - c.z).length() > 0.3 or on.y > 1.5:
				continue
			# navmesh tom ustida ham orolchalar hosil qiladi — o'yinchi yetib boradigan joy bo'lishi shart
			var spawn: Vector3 = D.T_SPAWN if s[1] == "T" else D.CT_SPAWN
			var path := NavigationServer3D.map_get_path(nav_map, spawn, on, true)
			if path.is_empty() or path[-1].distance_to(on) > 0.5:
				continue
			tried += 1
			if tried > 500:
				break
			sol = solve(on, tgt)
			if not sol.is_empty():
				sol["moved_m"] = snappedf(Vector2(on.x - base.x, on.z - base.z).length(), 0.1)
				sol["callout"] = MapData.callout_at(on)
				break
		var ok := not sol.is_empty()
		if ok:
			found += 1
			print("  [OK]   %-16s %-3s %s (%.1f, %.1f), yo'nalish %.0f°, ko'tarish %.0f°, %d m/s, uchish %.1f s, xato %.1f m, rejadan %.0f m" % [
				s[0], s[1], sol.callout, sol.origin[0], sol.origin[1], sol.yaw_deg, sol.pitch_deg, int(sol.speed), sol.flight_s, sol.miss_m, sol.moved_m])
		else:
			print("  [XATO] %-16s %-3s otish joyi topilmadi" % [s[0], s[1]])
		results.append({"name": s[0], "team": s[1], "target": [tgt.x, tgt.z], "lineup": sol})
	print("\nNATIJA: %d / %d smoke uchun lineup topildi" % [found, D.SMOKES.size()])
	var f := FileAccess.open(ProjectSettings.globalize_path("res://../docs/smokes_stage3.json"), FileAccess.WRITE)
	f.store_string(JSON.stringify(results, "  "))
	f.close()
	quit(0 if found == D.SMOKES.size() else 1)
