extends Node
## Realistik materiallar kutubxonasi: GLB ichidagi oddiy materiallarni nomi bo'yicha
## res://textures/<nom>_albedo/_normal/_orm(/_height).jpg dan yig'ilgan PBR materialga almashtiradi.
##   ORM: R — soyalanish (AO), G — g'adir-budurlik, B — metall.
##   Tosh, g'isht, yo'lak toshi va ganchda relyef (parallax) bor.
## Fayl bo'lmasa GLB materiali o'z holicha qoladi. Shaffof (alfa) materiallarga tegilmaydi.
## Teksturani fotosuratga almashtirish uchun: shu nomli jpg faylni textures/ ga qo'ying — kod o'zgarmaydi.
## To'qnashuv, panalar va NavMesh'ga hech qanday ta'sir yo'q — faqat ko'rinish.

const DIR := "res://textures/"
const PARALLAX := {"sandstone": 0.035, "sandstone_dk": 0.035, "brick": 0.03, "flagstone": 0.03, "cobble": 0.04, "ganch": 0.02}
const SPECULAR := {"tile_blue": 0.6, "tile_turq": 0.6, "girih": 0.6, "majolica": 0.6, "dome": 0.7}

@export var map_path: NodePath = ^"../Map"
@export var enabled := true
var lib := {}
var replaced := 0


func _ready() -> void:
	if not enabled:
		return
	var m := get_node_or_null(map_path)
	if m:
		_walk(m)


func material_for(name: String) -> Material:
	if lib.has(name):
		return lib[name]
	var mat: StandardMaterial3D = null
	var alb := DIR + name + "_albedo.jpg"
	if ResourceLoader.exists(alb):
		mat = StandardMaterial3D.new()
		mat.resource_name = name
		mat.albedo_texture = load(alb)
		var nrm := DIR + name + "_normal.jpg"
		if ResourceLoader.exists(nrm):
			mat.normal_enabled = true
			mat.normal_texture = load(nrm)
			mat.normal_scale = 1.0
		var orm := DIR + name + "_orm.jpg"
		if ResourceLoader.exists(orm):
			var t: Texture2D = load(orm)
			mat.ao_enabled = true
			mat.ao_texture = t
			mat.ao_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_RED
			mat.ao_light_affect = 0.6
			mat.roughness = 1.0
			mat.roughness_texture = t
			mat.roughness_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_GREEN
			mat.metallic = 1.0
			mat.metallic_texture = t
			mat.metallic_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_BLUE
		var hgt := DIR + name + "_height.jpg"
		if PARALLAX.has(name) and ResourceLoader.exists(hgt):
			mat.heightmap_enabled = true
			mat.heightmap_texture = load(hgt)
			mat.heightmap_scale = PARALLAX[name]
			mat.heightmap_deep_parallax = false
		mat.metallic_specular = SPECULAR.get(name, 0.35)
		mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	lib[name] = mat
	return mat


func _walk(n: Node) -> void:
	if n is MeshInstance3D and n.mesh:
		var mi := n as MeshInstance3D
		for i in mi.mesh.get_surface_count():
			var old := mi.mesh.surface_get_material(i)
			if old == null or (old is BaseMaterial3D and old.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED):
				continue
			var nm := old.resource_name
			var hq := material_for(nm)
			if hq:
				if old is BaseMaterial3D:
					hq.cull_mode = old.cull_mode
				mi.set_surface_override_material(i, hq)
				replaced += 1
	for c in n.get_children():
		_walk(c)
