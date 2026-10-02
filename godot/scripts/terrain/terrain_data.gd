class_name TerrainData
extends RefCounted
## Loads the baked heightmap (float32 metres) + zone control map and answers
## world-space queries (height, normal, buildable...). Pure data, no nodes.
##
## World space: X/Z in [-size/2, +size/2]; sample (col,row) = (+X, +Z).

const HEIGHTMAP_PATH := "res://terrain_data/heightmap.bin"
const ZONEMAP_PATH := "res://terrain_data/zonemap.png"
const META_PATH := "res://terrain_data/terrain_meta.json"

var size_m: float
var cells: int
var grid: int           # vertices per side (cells + 1)
var cell_m: float
var heights: PackedFloat32Array
var zone_image: Image   # R=buildable G=high ground B=valley A=playable
var meta: Dictionary


static func load_default() -> TerrainData:
	var d := TerrainData.new()
	if not d._load():
		return null
	return d


func _load() -> bool:
	var mf := FileAccess.open(META_PATH, FileAccess.READ)
	if mf == null:
		push_error("TerrainData: missing %s - run tools/generate_terrain.py" % META_PATH)
		return false
	meta = JSON.parse_string(mf.get_as_text())
	size_m = meta["size_m"]
	cells = meta["cells"]
	grid = meta["grid"]
	cell_m = meta["cell_m"]

	var hf := FileAccess.open(HEIGHTMAP_PATH, FileAccess.READ)
	if hf == null:
		push_error("TerrainData: missing %s" % HEIGHTMAP_PATH)
		return false
	heights = hf.get_buffer(grid * grid * 4).to_float32_array()
	if heights.size() != grid * grid:
		push_error("TerrainData: heightmap size mismatch")
		return false

	zone_image = Image.load_from_file(ProjectSettings.globalize_path(ZONEMAP_PATH))
	if zone_image == null:
		# exported builds: fall back to the imported texture resource
		zone_image = (load(ZONEMAP_PATH) as Texture2D).get_image()
	return true


func height_at_index(col: int, row: int) -> float:
	col = clampi(col, 0, grid - 1)
	row = clampi(row, 0, grid - 1)
	return heights[row * grid + col]


## Bilinear height in metres at world X/Z.
func height_at(x: float, z: float) -> float:
	var fx := clampf((x + size_m * 0.5) / cell_m, 0.0, grid - 1.001)
	var fz := clampf((z + size_m * 0.5) / cell_m, 0.0, grid - 1.001)
	var c := int(fx)
	var r := int(fz)
	var tx := fx - c
	var tz := fz - r
	var h00 := height_at_index(c, r)
	var h10 := height_at_index(c + 1, r)
	var h01 := height_at_index(c, r + 1)
	var h11 := height_at_index(c + 1, r + 1)
	return lerpf(lerpf(h00, h10, tx), lerpf(h01, h11, tx), tz)


func normal_at(x: float, z: float) -> Vector3:
	var e := cell_m
	var dx := height_at(x + e, z) - height_at(x - e, z)
	var dz := height_at(x, z + e) - height_at(x, z - e)
	return Vector3(-dx, 2.0 * e, -dz).normalized()


func slope_deg_at(x: float, z: float) -> float:
	return rad_to_deg(acos(clampf(normal_at(x, z).y, -1.0, 1.0)))


func _zone(x: float, z: float) -> Color:
	var px := clampi(int((x + size_m * 0.5) / cell_m), 0, grid - 1)
	var pz := clampi(int((z + size_m * 0.5) / cell_m), 0, grid - 1)
	return zone_image.get_pixel(px, pz)


## Gameplay queries used by the (future) building placement / AI systems.
func is_buildable(x: float, z: float) -> bool:
	return _zone(x, z).r > 0.5


func is_high_ground(x: float, z: float) -> bool:
	return _zone(x, z).g > 0.5


func is_valley(x: float, z: float) -> bool:
	return _zone(x, z).b > 0.5


func is_playable(x: float, z: float) -> bool:
	return _zone(x, z).a > 0.5


func base_position(faction: int) -> Vector3:
	var p: Array = meta["base_a"] if faction == 0 else meta["base_b"]
	return Vector3(p[0], meta["base_height_m"], p[1])
