// Mahalla hovli devorlari (MultiMesh). Mesh: x -0.5..0.5, y 0..1, z ±0.13.
// INSTANCE_CUSTOM = (uzunlik L, balandlik h, urug', darvoza 0/1)
shader_type spatial;
render_mode cull_back;

varying vec3 v_lp;
varying flat vec4 v_c;

float xesh(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float shovqin(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(xesh(i), xesh(i + vec2(1, 0)), u.x), mix(xesh(i + vec2(0, 1)), xesh(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 4; i++) { s += a * shovqin(p); p *= 2.03; a *= 0.5; }
	return s;
}

void vertex() {
	v_lp = VERTEX;
	v_c = INSTANCE_CUSTOM;
}

void fragment() {
	float L = v_c.x, h = v_c.y, urug = v_c.z;
	bool darvoza = v_c.w > 0.5;
	float u = (v_lp.x + 0.5) * L;
	float v = v_lp.y * h;
	float AA = max(max(fwidth(u), fwidth(v)), 1e-4);
	float FW_V = fwidth(v);
	float s1 = fract(urug * 7.13), s2 = fract(urug * 13.7);
	// tur: suvoq (oq/sarg'ish) yoki g'isht; qo'shni bo'laklar bir hovliga o'xshasin deb
	// urug' mahalliy joylashuvdan ham olinadi
	vec3 asos;
	bool gisht = s1 < 0.35;
	if (gisht) {
		vec2 gs = vec2(0.25, 0.075);
		float qator = floor(v / gs.y);
		float gu = u + mod(qator, 2.0) * gs.x * 0.5;
		vec2 f = vec2(fract(gu / gs.x) * gs.x, fract(v / gs.y) * gs.y);
		vec2 d = abs(f - gs * 0.5) - (gs * 0.5 - 0.008);
		float chok = 1.0 - (1.0 - smoothstep(-AA, AA, max(d.x, d.y)));
		float uzoq = smoothstep(0.25, 0.7, FW_V / gs.y);
		vec3 g = vec3(0.66, 0.42, 0.29) * (0.82 + 0.3 * xesh(vec2(floor(gu / gs.x), qator) + urug));
		asos = mix(mix(g, vec3(0.7, 0.67, 0.6), chok), vec3(0.64, 0.46, 0.34), uzoq);
	} else {
		asos = mix(vec3(0.92, 0.88, 0.8), vec3(0.9, 0.8, 0.64), s2) * (0.86 + 0.22 * fbm(vec2(u, v) * 0.8 + urug * 30.0));
	}
	// tepadagi qator (qopqoq) va pastdagi kir
	asos *= mix(0.7, 1.0, smoothstep(0.0, 0.9, v));
	if (v > h - 0.12) asos *= 0.78;
	float metall = 0.0, rough = 0.9;
	// darvoza: metall, ko'k/yashil/jigarrang, vertikal qovurg'alar, 3.2 m
	if (darvoza) {
		vec2 dd = abs(vec2(u - L * 0.5, v - 1.25)) - vec2(1.6, 1.25);
		float e = 1.0 - smoothstep(-AA, AA, max(dd.x, dd.y));
		if (e > 0.0) {
			float s3 = fract(urug * 29.3);
			vec3 er = s3 < 0.33 ? vec3(0.1, 0.28, 0.55) : (s3 < 0.66 ? vec3(0.1, 0.36, 0.22) : vec3(0.36, 0.2, 0.1));
			float qovurga = 0.82 + 0.18 * smoothstep(0.45, 0.55, fract((u - L * 0.5) / 0.14));
			float rom = 1.0 - (1.0 - smoothstep(-AA, AA, max(dd.x + 0.06, dd.y + 0.06)));
			er *= qovurga * (1.0 - 0.25 * rom);
			// o'rtadagi ikki tavaqa chizig'i
			er *= 1.0 - 0.5 * (1.0 - smoothstep(0.0, AA * 2.0 + 0.01, abs(u - L * 0.5)));
			asos = mix(asos, er, e);
			metall = mix(0.0, 0.55, e);
			rough = mix(0.9, 0.4, e);
		}
	}
	ALBEDO = asos;
	METALLIC = metall;
	ROUGHNESS = rough;
}
