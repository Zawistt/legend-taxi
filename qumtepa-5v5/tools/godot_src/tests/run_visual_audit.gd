extends SceneTree
## Vizual audit (devor va ulanmagan joylar): ko'rinadigan geometriya va to'qnashuv bir-biriga mosmi.
##   godot --headless -s res://tests/run_visual_audit.gd -- <sahna>
## 1) Ko'rinmas devor / teshik: to'qnashuv qutisining ochiq tomonida ko'rinadigan sirt yo'q
##    (o'yinchi ko'rinmas narsaga uriladi yoki devorda tirqish — orqasi ko'rinadi).
## 2) Arvoh devor: ko'rinadigan tik sirt (0.2–2 m balandlikda) yonida to'qnashuv yo'q — o'yinchi ichidan o'tib ketadi.
## Ko'rinadigan meshlar vaqtincha uchburchak to'qnashuvga (20-qatlam) aylantiriladi va nurlar bilan tekshiriladi.

const VIS := 1 << 19
const STEP := 0.9

var total := 0
var fails := 0


func ok(c: bool, msg: String) -> void:
	total += 1
	print(("  [OK]   " if c else "  [XATO] ") + msg)
	if not c:
		fails += 1


func _initialize() -> void:
	_run.call_deferred()


## nuqta ko'rinadigan devor hajmi ichidami (ikki tomonida ham ko'rinadigan sirt bor): u holda teshik emas —
## masalan ravoq bo'laklari orasidagi yuza devor qalinligi ichida yotadi
func _inside_visual(space: PhysicsDirectSpaceState3D, p: Vector3, xf: Transform3D, ax: int) -> bool:
	for k in [(ax + 1) % 3, (ax + 2) % 3]:
		var d: Vector3 = xf.basis[k].normalized()
		var a := space.intersect_ray(PhysicsRayQueryParameters3D.create(p, p + d * 0.8, VIS))
		var b := space.intersect_ray(PhysicsRayQueryParameters3D.create(p, p - d * 0.8, VIS))
		if not a.is_empty() and not b.is_empty():
			return true
	return false


func _all(n: Node, cls: String, out: Array) -> Array:
	if n.is_class(cls):
		out.append(n)
	for c in n.get_children():
		_all(c, cls, out)
	return out


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var scene := args[0] if args.size() > 0 else "res://main.tscn"
	var main: Node = load(scene).instantiate()
	if main.get_node_or_null("Bots"):
		main.get_node("Bots").enabled = false
	root.add_child(main)
	for i in 3:
		await physics_frame
	print("\nVizual audit: %s" % scene)
	var mapn: Node = main.get_node("Map")
	var meshes := _all(mapn, "MeshInstance3D", [])
	var faces_by_mesh := {}
	for mi in meshes:
		var m: Mesh = (mi as MeshInstance3D).mesh
		if m == null:
			continue
		var sh := m.create_trimesh_shape()
		if sh == null:
			continue
		var sb := StaticBody3D.new()
		sb.collision_layer = VIS
		sb.collision_mask = 0
		var cs := CollisionShape3D.new()
		cs.shape = sh
		sb.add_child(cs)
		main.add_child(sb)
		sb.global_transform = (mi as Node3D).global_transform
		faces_by_mesh[mi] = [sh.get_faces(), (mi as Node3D).global_transform]
	for i in 3:
		await physics_frame
	var space: PhysicsDirectSpaceState3D = main.get_world_3d().direct_space_state
	var col_root: Node = main.get_node("Navigation/Collision")
	var boxes: Array = []
	var floor_half := 0.0
	for cs in _all(col_root, "CollisionShape3D", []):
		var body := cs.get_parent() as CollisionObject3D
		if body == null or (body.collision_layer & 1) == 0 or not (cs.shape is BoxShape3D):
			continue
		var sz: Vector3 = (cs.shape as BoxShape3D).size
		boxes.append([cs.global_transform, sz])
		floor_half = maxf(floor_half, maxf(sz.x, sz.z) * 0.5)
	var half := floor_half - 0.2
	# 1) to'qnashuv yuzalarida ko'rinadigan sirt bormi
	var pq := PhysicsPointQueryParameters3D.new()
	pq.collision_mask = 1
	var samples := 0
	var bad := []
	for bx in boxes:
		var xf: Transform3D = bx[0]
		var sz: Vector3 = bx[1]
		if sz.x > 50.0 or sz.z > 50.0:
			continue                              # butun xarita poli — alohida tekshiriladi (pol teshiklari: run_audit)
		for ax in 3:
			for sg in [-1.0, 1.0]:
				var n_local := Vector3.ZERO
				n_local[ax] = sg
				if ax == 1 and sg < 0.0:
					continue                      # pastki tomon ko'rinmaydi
				var n: Vector3 = (xf.basis * n_local).normalized()
				var u_ax := (ax + 1) % 3
				var v_ax := (ax + 2) % 3
				var nu := maxi(1, int(sz[u_ax] / STEP))
				var nv := maxi(1, int(sz[v_ax] / STEP))
				var miss := 0
				var cnt := 0
				var first := Vector3.ZERO
				for iu in nu:
					for iv in nv:
						var lp := Vector3.ZERO
						lp[ax] = sg * sz[ax] * 0.5
						lp[u_ax] = (-0.5 + (iu + 0.5) / nu) * (sz[u_ax] - 0.3)
						lp[v_ax] = (-0.5 + (iv + 0.5) / nv) * (sz[v_ax] - 0.3)
						var p: Vector3 = xf * lp
						if absf(p.x) > half or absf(p.z) > half or p.y > 6.0 or p.y < -0.2:
							continue
						pq.position = p + n * 0.12
						if not space.intersect_point(pq, 1).is_empty():
							continue              # ichki tomon (boshqa quti bilan yopishgan)
						cnt += 1
						var q := PhysicsRayQueryParameters3D.create(p + n * 0.45, p - n * 0.45, VIS)
						if space.intersect_ray(q).is_empty() and not _inside_visual(space, p, xf, ax):
							miss += 1
							if first == Vector3.ZERO:
								first = p
				samples += cnt
				if cnt >= 2 and miss * 3 >= cnt:
					bad.append([first, n, miss, cnt, sz])
	print("  to'qnashuv yuzalaridan %d nuqta tekshirildi" % samples)
	# o'yinchi yetadigan balandlik (≤ 3 m: bo'y 1.8 + sakrash) — xato; undan baland (eshik tepasi) — ma'lumot uchun
	var low := bad.filter(func(b): return b[0].y <= 3.0)
	for b in bad.slice(0, 25):
		print("    ko'rinmas%s: %s normal %s  (%d/%d nuqta), quti %s" % ["" if b[0].y <= 3.0 else " (> 3 m)", b[0].snapped(Vector3.ONE * 0.1), b[1].snapped(Vector3.ONE * 0.1), b[2], b[3], b[4]])
	ok(low.is_empty(), "o'yinchi yetadigan balandlikda ko'rinmas devor / teshik yo'q: %d ta yuza (3 m dan baland: %d)" % [low.size(), bad.size() - low.size()])
	# 2) ko'rinadigan tik sirtlar yonida to'qnashuv bormi (0.2–2.0 m)
	var ghosts := {}
	var gs := 0
	for mi in faces_by_mesh:
		var nm := str(mi.name)
		var f: PackedVector3Array = faces_by_mesh[mi][0]
		var gx: Transform3D = faces_by_mesh[mi][1]
		for i in range(0, f.size(), 3):
			var a: Vector3 = gx * f[i]
			var b: Vector3 = gx * f[i + 1]
			var c: Vector3 = gx * f[i + 2]
			var cr := (b - a).cross(c - a)
			var area := cr.length() * 0.5
			if area < 0.08:
				continue
			var n := cr.normalized()
			if absf(n.y) > 0.3:
				continue
			var ctr := (a + b + c) / 3.0
			if ctr.y < 0.2 or ctr.y > 2.0 or absf(ctr.x) > half or absf(ctr.z) > half:
				continue
			gs += 1
			var q1 := PhysicsRayQueryParameters3D.create(ctr + n * 0.4, ctr - n * 0.6, 1 | 2)
			var q2 := PhysicsRayQueryParameters3D.create(ctr - n * 0.4, ctr + n * 0.6, 1 | 2)
			if space.intersect_ray(q1).is_empty() and space.intersect_ray(q2).is_empty():
				pq.position = ctr
				pq.collision_mask = 1 | 2
				if space.intersect_point(pq, 1).is_empty():
					if not ghosts.has(nm):
						ghosts[nm] = [0, ctr, area]
					ghosts[nm][0] += 1
					ghosts[nm][2] = maxf(ghosts[nm][2], area)
				pq.collision_mask = 1
	print("  ko'rinadigan tik sirtlardan %d ta uchburchak tekshirildi" % gs)
	var big := []
	for nm in ghosts:
		print("    arvoh: %-40s %3d uchburchak, masalan %s, eng katta %.2f m²" % [nm, ghosts[nm][0], ghosts[nm][1].snapped(Vector3.ONE * 0.1), ghosts[nm][2]])
		if ghosts[nm][2] >= 0.5:
			big.append(nm)
	ok(big.is_empty(), "arvoh devor (ko'rinadi, lekin ichidan o'tib bo'ladi, ≥ 0.5 m² yuza): %d ta mesh" % big.size())
	print("\nNATIJA: %d / %d tekshiruv o'tdi" % [total - fails, total])
	quit(1 if fails else 0)
