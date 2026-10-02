class_name TerrainData
extends RefCounted
## Loads the baked heightmap (float32 metres) + zone control map and answers
## world-space queries (height, normal, buildable...). Pure data, no nodes.
##
## World space: X/Z in [-size/2, +size/2]; sample (col,row) = (+X, +Z).

const HEIGHTMAP_PATH := "res://terrain_data/heightmap.bin"
const ZONEMAP_PATH := "res://terrain_data/zonemap.png"
const META_PATH := "res://terrain_data/terrain_meta.json"
const ROADMAP_PATH := "res://terrain_data/roadmap.png"
const BLOCKMAP_PATH := "res://terrain_data/blockmap.png"

## Lane ids stored in the roadmap blue channel (value * 32).
enum Lane { NONE = 0, CENTER = 1, LEFT = 2, RIGHT = 3, LINK = 4, RAMP = 5, WORK = 6 }

var size_m: float
var cells: int
var grid: int           # vertices per side (cells + 1)
var cell_m: float
var heights: PackedFloat32Array
var zone_image: Image   # R=buildable G=high ground B=valley A=playable
var road_image: Image   # R=road alpha G=class wear B=lane id*32   (1024^2)
var block_image: Image  # R=forest G=rock A=choke highlight        (1024^2)
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

	zone_image = _load_image(ZONEMAP_PATH)
	road_image = _load_image(ROADMAP_PATH)
	block_image = _load_image(BLOCKMAP_PATH)
	return zone_image != null and road_image != null and block_image != null


func _load_image(path: String) -> Image:
	var img := Image.load_from_file(ProjectSettings.globalize_path(path))
	if img == null:
		# exported builds: fall back to the imported (lossless) texture resource
		var tex := load(path) as Texture2D
		img = tex.get_image() if tex != null else null
	return img


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


func _px(img: Image, x: float, z: float) -> Color:
	var s := img.get_width()
	var px := clampi(int((x + size_m * 0.5) / size_m * s), 0, s - 1)
	var pz := clampi(int((z + size_m * 0.5) / size_m * s), 0, s - 1)
	return img.get_pixel(px, pz)


## Road coverage 0..1 at a world position (soft edge).
func road_alpha_at(x: float, z: float) -> float:
	return _px(road_image, x, z).r


func is_on_road(x: float, z: float) -> bool:
	return road_alpha_at(x, z) > 0.5


## Lane id (Lane enum) of the road at this position, Lane.NONE if off-road.
func lane_at(x: float, z: float) -> int:
	var c := _px(road_image, x, z)
	return int(round(c.b * 255.0 / 32.0)) if c.r > 0.5 else Lane.NONE


## Dense vegetation / rock formation: impassable terrain (carved out of the navmesh).
func is_blocked(x: float, z: float) -> bool:
	var c := _px(block_image, x, z)
	return c.r > 0.5 or c.g > 0.5


func is_forest(x: float, z: float) -> bool:
	return _px(block_image, x, z).r > 0.5


func is_rock(x: float, z: float) -> bool:
	return _px(block_image, x, z).g > 0.5


## True where units can stand (flat enough and not carved out). Cliffs use the navmesh slope limit.
func is_walkable(x: float, z: float) -> bool:
	return is_playable(x, z) and not is_blocked(x, z) and slope_deg_at(x, z) < float(meta.get("nav_max_slope_deg", 18.0))


## Gameplay queries used by the (future) building placement / AI systems.
## Buildable = flat plateau terrain that is not a road and not blocked.
func is_buildable(x: float, z: float) -> bool:
	return _zone(x, z).r > 0.5 and not is_on_road(x, z) and not is_blocked(x, z)


func is_high_ground(x: float, z: float) -> bool:
	return _zone(x, z).g > 0.5


func is_valley(x: float, z: float) -> bool:
	return _zone(x, z).b > 0.5


func is_playable(x: float, z: float) -> bool:
	return _zone(x, z).a > 0.5


func base_position(faction: int) -> Vector3:
	var p: Array = meta["base_a"] if faction == 0 else meta["base_b"]
	return Vector3(p[0], meta["base_height_m"], p[1])
