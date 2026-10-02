shader_type spatial;
// Procedural RTS terrain: grass / dry grass / dirt / rock blended by slope, height
// and low-frequency noise. No textures required (swap in texture arrays later).
// Cheap: one vertex-stage world pos, one fragment pass, no extra samplers except
// the 1 zone control map (only read when show_zones is on).

uniform sampler2D zone_map : filter_linear, repeat_disable;
uniform float map_size = 428.57;
// Design-space metres per real metre; keeps texture/noise detail identical to the
// original layout after the world was shrunk.
uniform float world_scale = 4.667;
uniform bool show_zones = false;

// --- movement structure (roads / lanes / blocked terrain) ---
uniform sampler2D road_map : filter_linear, repeat_disable;   // R alpha, G wear, B lane id * 32
uniform sampler2D block_map : filter_linear, repeat_disable;  // R forest, G rock, A choke highlight
uniform bool show_paths = false;                              // debug: colour roads by lane, show chokes
uniform vec3 road_col : source_color = vec3(0.40, 0.31, 0.20);
uniform vec3 road_light : source_color = vec3(0.50, 0.41, 0.29);
uniform vec3 forest_col : source_color = vec3(0.07, 0.16, 0.06);
uniform vec3 rock_zone_col : source_color = vec3(0.34, 0.31, 0.28);

uniform vec3 grass_light : source_color = vec3(0.30, 0.45, 0.16);
uniform vec3 grass_dark : source_color = vec3(0.20, 0.32, 0.11);
uniform vec3 grass_dry : source_color = vec3(0.46, 0.45, 0.22);
uniform vec3 dirt_col : source_color = vec3(0.45, 0.36, 0.24);
uniform vec3 rock_col : source_color = vec3(0.50, 0.47, 0.43);

uniform float dirt_slope_start = 9.0;
uniform float rock_slope_start = 17.0;
uniform float rock_height_start = 21.0;   // metres (world units)

varying vec3 v_world;
varying vec3 v_world_normal;

float hash21(vec2 p) {
	p = fract(p * vec2(123.34, 456.21));
	p += dot(p, p + 45.32);
	return fract(p.x * p.y);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash21(i), hash21(i + vec2(1, 0)), f.x),
			mix(hash21(i + vec2(0, 1)), hash21(i + vec2(1, 1)), f.x), f.y);
}

float fbm(vec2 p) {
	return vnoise(p) * 0.55 + vnoise(p * 2.13) * 0.30 + vnoise(p * 4.7) * 0.15;
}

void vertex() {
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec2 wp = v_world.xz * world_scale;
	float slope = degrees(acos(clamp(v_world_normal.y, 0.0, 1.0)));

	float n_large = fbm(wp * 0.006);
	float n_mid = fbm(wp * 0.03 + 17.0);
	float n_fine = fbm(wp * 0.35);

	vec3 col = mix(grass_dark, grass_light, clamp(n_large * 0.9 + v_world.y * world_scale * 1.2 / 140.0, 0.0, 1.0));
	col = mix(col, grass_dry, smoothstep(0.55, 0.85, n_mid) * 0.8);
	float dirt = clamp((slope - dirt_slope_start) / 8.0 * 0.9 + smoothstep(0.78, 0.95, n_mid) * 0.7, 0.0, 1.0);
	col = mix(col, dirt_col, dirt);
	float rock = clamp((slope - rock_slope_start) / 8.0 + (v_world.y - rock_height_start) / 7.5, 0.0, 1.0);
	col = mix(col, rock_col, rock);
	col *= 0.92 + 0.16 * n_fine; // subtle micro variation

	// ---- blocked terrain: dense vegetation / rock formations (purely visual, nav is carved by polygons)
	vec2 uv = v_world.xz / map_size + 0.5;
	vec4 blk = texture(block_map, uv);
	float forest = smoothstep(0.25, 0.75, blk.r);
	float rockz = smoothstep(0.25, 0.75, blk.g);
	float canopy = fbm(wp * 0.9) * 0.6 + fbm(wp * 2.6) * 0.4;
	vec3 fcol = forest_col * (0.65 + 0.9 * canopy);
	vec3 rcol = rock_zone_col * (0.6 + 0.9 * fbm(wp * 1.7)) ;
	col = mix(col, fcol, forest);
	col = mix(col, rcol, rockz);
	float rough_extra = max(forest, rockz);

	// ---- roads: packed earth, lighter and cleaner on the main routes, worn edges
	vec4 rd = texture(road_map, uv);
	float road = smoothstep(0.35, 0.85, rd.r);
	float rim = smoothstep(0.35, 0.6, rd.r) * (1.0 - smoothstep(0.7, 0.98, rd.r));
	vec3 rcol2 = mix(road_col, road_light, rd.g) * (0.88 + 0.22 * fbm(wp * 1.3));
	rcol2 = mix(rcol2, rcol2 * 0.72, rim * 0.8);                // darker worn verge
	col = mix(col, rcol2, road * (1.0 - 0.0 * rough_extra));

	if (show_paths) {
		int lane = int(rd.b * 255.0 / 32.0 + 0.5);
		vec3 lc = vec3(0.7);
		if (lane == 1) lc = vec3(1.0, 0.82, 0.2);
		else if (lane == 2) lc = vec3(0.25, 0.65, 1.0);
		else if (lane == 3) lc = vec3(1.0, 0.33, 0.33);
		else if (lane == 4) lc = vec3(1.0);
		else if (lane == 5) lc = vec3(1.0, 0.6, 0.12);
		else if (lane == 6) lc = vec3(0.78, 0.47, 1.0);
		col = mix(col, lc, road * 0.75);
		col = mix(col, vec3(0.05, 0.35, 0.1), forest * 0.5);
		col = mix(col, vec3(0.25, 0.25, 0.28), rockz * 0.5);
		col = mix(col, vec3(1.0, 0.0, 1.0), blk.a * 0.18 * (1.0 - road));
	}

	if (show_zones) {
		vec4 z = texture(zone_map, uv);
		vec3 tint = col;
		if (z.r > 0.5) tint = mix(col, vec3(0.25, 0.55, 1.0), 0.55);
		else if (z.g > 0.5) tint = mix(col, vec3(1.0, 0.75, 0.15), 0.5);
		else if (z.b > 0.5) tint = mix(col, vec3(0.7, 0.3, 0.8), 0.45);
		col = tint;
	}

	ALBEDO = col;
	ROUGHNESS = 0.95;
	METALLIC = 0.0;
	SPECULAR = 0.15;
}
