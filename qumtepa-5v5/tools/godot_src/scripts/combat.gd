extends RefCounted
## Zarar berish (CS2): xom zarar -> zirh/kaska (qurolning zirh teshishi) -> sog'liq; statistikani o'yin rejimiga yozadi.
## Hamma o'q, pichoq, Zeus, granata shu yerdan o'tadi (o'yinchi ham, botlar ham).

## victim: o'yinchi yoki bot (hp, alive, team, loadout, damage()); true — o'ldi
static func hit(victim: Node, raw: float, zone: String, attacker: Node, weapon: Resource, tree: SceneTree = null) -> bool:
	if victim == null or not victim.alive or raw <= 0.0:
		return false
	if attacker and "team" in attacker and attacker != victim and attacker.team == victim.team:
		return false                                    # o'z jamoasiga zarar yo'q
	var hp_dmg := raw
	var lo = victim.get("loadout")
	if lo and weapon and weapon.has_method("damage_vs_armor"):
		var r: Array = weapon.damage_vs_armor(raw, zone, lo.armor, lo.helmet)
		hp_dmg = r[0]
		lo.armor = maxf(0.0, lo.armor - r[1])
	var before: float = victim.hp
	var from_pos: Vector3 = attacker.global_position if attacker is Node3D else Vector3.ZERO
	var killed: bool = victim.damage(hp_dmg, from_pos)
	var t := tree if tree else victim.get_tree()
	var gm := t.get_first_node_in_group("game_mode") if t else null
	if gm and gm.has_method("record_damage"):
		gm.record_damage(attacker, victim, minf(before, hp_dmg), weapon, zone, killed)
	return killed
