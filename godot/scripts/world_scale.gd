class_name WorldScale
extends RefCounted
## Single source of truth for proportions (1 Godot unit = 1 metre). Future unit/building
## content must be authored to these sizes. Nothing here spawns objects.

# Map
const MAP_SIZE := 428.57            # full mesh, incl. mountain rim
const PLAYABLE_SIZE := 360.0        # playable square (|x|,|z| <= 180)

# Characters (small but readable at the default RTS zoom)
const WORKER_HEIGHT := 1.2
const WORKER_RADIUS := 0.35
const SOLDIER_HEIGHT := 1.5
const SOLDIER_RADIUS := 0.4
const HEAVY_UNIT_RADIUS := 0.7      # cavalry / siege footprint
const FORMATION_SPACING := 1.1      # centre-to-centre in a formation

# Buildings: 2-5x worker height; Main Base clearly dominant
const BUILDING_HEIGHT_MIN := 2.4    # 2x worker
const BUILDING_HEIGHT_MAX := 6.0    # 5x worker
const BUILDING_FOOTPRINT_MIN := 3.0
const BUILDING_FOOTPRINT_MAX := 6.0
const MAIN_BASE_HEIGHT := 10.0
const MAIN_BASE_FOOTPRINT := 12.0
const DEFENSE_TOWER_HEIGHT := 7.0

# Navigation / movement
const NAV_AGENT_RADIUS := 0.5
const NAV_AGENT_HEIGHT := 1.5
const MIN_CORRIDOR_WIDTH := 12.0    # narrowest allowed attack route (~10 soldiers abreast)
const UNIT_SPEED_WORKER := 3.5      # m/s -> base-to-base (~390 m) in about 1 min
const UNIT_SPEED_SOLDIER := 5.0

# Camera
const CAM_ZOOM_MIN := 12.0
const CAM_ZOOM_MAX := 330.0
