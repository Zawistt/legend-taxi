// Tomlar. UV — metr (qiya tomda u — bo'g'ot bo'ylab, v — qiyalik bo'ylab),
// UV2.x — binoning urug'i (rang tanlash uchun).
shader_type spatial;
render_mode cull_back;

uniform int turi = 0;                   // 0 — shifer (to'lqinli), 1 — tekis bitum, 2 — obida
uniform vec3 rang : source_color = vec3(0.6, 0.61, 0.6);

varying vec2 v_uv;
varying flat float v_urug;

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
	v_uv = UV;
	v_urug = UV2.x;
}

// GLB'da tangent yo'q: tangent fazosini ekran hosilalaridan hisoblaymiz
// (fragment boshida — bir xil boshqaruv oqimida).
mat3 tbn(vec3 N, vec3 pos, vec2 uv) {
	vec3 dp1 = dFdx(pos), dp2 = dFdy(pos);
	vec2 du1 = dFdx(uv), du2 = dFdy(uv);
	vec3 p2 = cross(dp2, N), p1 = cross(N, dp1);
	vec3 T = p2 * du1.x + p1 * du2.x;
	vec3 B = p2 * du1.y + p1 * du2.y;
	float k = inversesqrt(max(max(dot(T, T), dot(B, B)), 1e-12));
	return mat3(T * k, B * k, N);
}

void fragment() {
	vec2 p = v_uv;
	mat3 TBN = tbn(NORMAL, VERTEX, p);
	float FW_T = fwidth(p.x / 0.175 * 6.2831);
	float s = fract(sin(v_urug * 91.3) * 4375.5);
	float n = fbm(p * 0.8 + v_urug * 40.0);
	vec3 alb;
	float rough;
	if (turi == 0) {
		// shifer: kulrang asbest, ba'zan bo'yalgan (qizg'ish, yashil) yoki zanglagan tunuka
		vec3 r = rang;
		if (s > 0.72) r = vec3(0.55, 0.22, 0.16);
		else if (s > 0.6) r = vec3(0.2, 0.36, 0.28);
		else if (s > 0.5) r = vec3(0.62, 0.64, 0.66);
		// to'lqinlar (17.5 sm) — normal xaritasi
		float t = p.x / 0.175 * 6.2831;
		float kuch = 0.45 * (1.0 - smoothstep(0.8, 2.5, FW_T));   // uzoqda moire bo'lmasin
		NORMAL = normalize(TBN * vec3(cos(t) * kuch, 0.0, 1.0));
		// varaqlar choki (1.75 m) va mox/chang
		float varaq = 1.0 - 0.18 * (1.0 - smoothstep(0.0, 0.03, abs(fract(p.y / 1.75) - 0.5) * 1.75 - 0.84));
		alb = r * (0.75 + 0.35 * n) * varaq;
		alb = mix(alb, vec3(0.32, 0.3, 0.24), smoothstep(0.6, 0.85, fbm(p * 0.3 + 11.0)) * 0.5);
		rough = 0.7;
	} else {
		// tekis tom: bitum, yamoqlar, shag'al
		alb = rang * (0.7 + 0.45 * n);
		float yamoq = smoothstep(0.55, 0.6, fbm(p * 0.15 + v_urug * 9.0));
		alb = mix(alb, alb * 0.6, yamoq);
		rough = 0.95;
	}
	ALBEDO = alb;
	ROUGHNESS = rough;
}
