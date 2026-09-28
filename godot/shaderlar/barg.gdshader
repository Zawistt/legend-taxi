// Daraxt shox-shabbasi: dunyo koordinatasidagi shovqindan barg to'dalari, tirqishlar
// (alpha scissor), rang farqi, orqadan yorug'lik o'tishi va shamolda tebranish.
// INSTANCE_CUSTOM.x — daraxt urug'i (rang farqi uchun).
shader_type spatial;
render_mode cull_disabled, diffuse_burley;

uniform vec3 rang_a : source_color = vec3(0.24, 0.38, 0.12);
uniform vec3 rang_b : source_color = vec3(0.42, 0.52, 0.18);
uniform float tirqish = 0.32;          // bargsiz joylar ulushi
uniform float shamol = 1.0;
uniform float barg_olchami = 2.6;      // to'da chastotasi (1/m)

varying vec3 v_dunyo;
varying flat float v_urug;

float xesh3(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
float shovqin3(vec3 p) {
	vec3 i = floor(p), f = fract(p);
	vec3 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(xesh3(i), xesh3(i + vec3(1, 0, 0)), u.x), mix(xesh3(i + vec3(0, 1, 0)), xesh3(i + vec3(1, 1, 0)), u.x), u.y),
	           mix(mix(xesh3(i + vec3(0, 0, 1)), xesh3(i + vec3(1, 0, 1)), u.x), mix(xesh3(i + vec3(0, 1, 1)), xesh3(i + vec3(1, 1, 1)), u.x), u.y), u.z);
}

void vertex() {
	v_urug = INSTANCE_CUSTOM.x;
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float k = smoothstep(1.0, 6.0, VERTEX.y) * shamol;
	float faza = w.x * 0.21 + w.z * 0.17;
	VERTEX.x += (sin(TIME * 1.3 + faza) * 0.10 + sin(TIME * 3.7 + w.y) * 0.025) * k;
	VERTEX.z += (cos(TIME * 1.1 + faza * 1.3) * 0.08) * k;
	v_dunyo = w;
}

void fragment() {
	vec3 p = v_dunyo * barg_olchami;
	float n1 = shovqin3(p);
	float n2 = shovqin3(p * 2.7 + 11.0);
	float n = n1 * 0.65 + n2 * 0.35;
	// tirqishlar: uzoqdan kamroq (piksel katta — miltillamasin)
	float fw = fwidth(p.x) + fwidth(p.y);
	float t = tirqish * (1.0 - smoothstep(0.6, 2.5, fw));
	ALPHA = step(t, n);
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	vec3 c = mix(rang_a, rang_b, smoothstep(0.25, 0.8, n2));
	c *= 0.85 + 0.3 * v_urug;
	// ichki qism qorong'iroq (o'z-o'ziga soya)
	c *= mix(0.55, 1.0, smoothstep(0.2, 0.75, n1));
	ALBEDO = c;
	ROUGHNESS = 0.75;
	SPECULAR = 0.35;
	BACKLIGHT = c * 0.6;
	// barglar notekis: normalni shovqin bilan buramiz
	vec3 g = vec3(shovqin3(p + 3.0), shovqin3(p + 7.0), shovqin3(p + 13.0)) - 0.5;
	NORMAL = normalize(NORMAL + g * 1.2);
}
