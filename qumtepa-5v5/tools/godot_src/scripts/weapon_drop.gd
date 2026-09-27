extends RigidBody3D
## Yerga tashlangan qurol (CS2): G bilan tashlanadi yoki o'lganda tushadi. Fizika bilan uchadi va yerda yotadi.
## O'sha turdagi joyi bo'sh o'yinchi/bot ustidan yurib o'tsa — avtomatik oladi; E — qarab turgan qurolni almashtiradi
## (qo'lidagi o'sha turdagi qurol yerga tushadi). O'q-dori (magazin/zaxira) qurol bilan birga saqlanadi.
## Yangi raund boshlanganda yerdagi qurollar yo'qoladi (game_mode.gd).

const CM := preload("res://scripts/character_model.gd")

var weapon: Resource
var ammo: Array = [0, 0]
var dropped_by: Node = null
var age := 0.0


static func spawn(parent: Node, w: Resource, am: Array, pos: Vector3, vel: Vector3, who: Node) -> RigidBody3D:
	var d: RigidBody3D = (load("res://scripts/weapon_drop.gd") as GDScript).new()
	d.weapon = w
	d.ammo = am.duplicate()
	d.dropped_by = who
	parent.add_child(d)
	d.global_position = pos
	d.linear_velocity = vel
	d.angular_velocity = Vector3(randf_range(-2, 2), randf_range(-4, 4), randf_range(-2, 2))
	return d


func _ready() -> void:
	add_to_group("dropped_weapons")
	name = "Drop_" + weapon.weapon_id
	collision_layer = 0
	collision_mask = 1
	mass = 3.0
	angular_damp = 2.0
	linear_damp = 0.3
	var pm := PhysicsMaterial.new()
	pm.bounce = 0.15
	pm.friction = 0.9
	physics_material_override = pm
	var shape: Dictionary = CM.make_weapon_shape(int(weapon.kind), "CT" if weapon.side == "CT" else "T", weapon.weapon_id)
	var g: Node3D = shape.node
	add_child(g)
	g.position = -shape.grip - Vector3(0, 0, 0.15 if int(weapon.kind) != 1 else 0.0)
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	var long := int(weapon.kind) != 1
	bs.size = Vector3(0.08, 0.14, 0.8 if long else 0.22)
	cs.shape = bs
	add_child(cs)


func _physics_process(delta: float) -> void:
	age += delta
	if global_position.y < -20.0:
		queue_free()
