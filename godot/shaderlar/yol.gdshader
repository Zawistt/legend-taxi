// Yo'l yuzalari. UV — dunyo koordinatasi (X, Z) metrda.
//   turi 0 — asfalt (katta yo'l), 1 — mahalla yo'li (eskirgan asfalt, chang),
//   2 — trotuar plitkasi, 3 — yo'l chizig'i bo'yog'i
shader_type spatial;
render_mode cull_back;

uniform int turi = 0;
uniform vec3 rang : source_color = vec3(0.2, 0.21, 0.22);

varying vec2 v_uv;

float xesh(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float shovqin(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(xesh(i), xesh(i + vec2(1, 0)), u.x), mix(xesh(i + vec2(0, 1)), xesh(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 5; i++) { s += a * shovqin(p); p *= 2.03; a *= 0.5; }
	return s;
}
// yoriqlar: shovqinning 0.5 sathi atrofidagi ingichka chiziqlar
float yoriq(vec2 p, float en) {
	float n = fbm(p);
	return 1.0 - smoothstep(0.0, en, abs(n - 0.5));
}

void vertex() {
	v_uv = UV;
}

void fragment() {
	vec2 p = v_uv;
	float fw = max(fwidth(p.x), fwidth(p.y));
	float uzoq = smoothstep(0.02, 0.12, fw);          // uzoqda mayda detallar so'nadi
	vec3 alb;
	float rough;
	if (turi == 0 || turi == 1) {
		float don = mix(shovqin(p * 18.0), 0.5, uzoq);           // shag'al donalari
		float katta_dog = fbm(p * 0.08);
		alb = rang * (0.82 + 0.28 * katta_dog) * (0.92 + 0.16 * don);
		// yamoqlar (ta'mirlangan joylar) — to'q to'rtburchaklar
		vec2 yc = floor(p / 7.0);
		float yamoq = step(0.86, xesh(yc)) * step(abs(fract(p.x / 7.0) - 0.5), 0.3) * step(abs(fract(p.y / 7.0) - 0.5), 0.22);
		alb *= 1.0 - 0.25 * yamoq;
		// yoriqlar
		float yr = yoriq(p * 0.35 + 3.1, 0.012) * (1.0 - uzoq);
		alb *= 1.0 - 0.45 * yr;
		rough = 0.86 - 0.1 * yamoq;
		if (turi == 1) {
			// mahalla yo'li: chang, qum, ko'proq yamoq
			float chang = smoothstep(0.45, 0.75, fbm(p * 0.12 + 7.0));
			alb = mix(alb, vec3(0.55, 0.48, 0.38), chang * 0.55);
			rough = 0.93;
		}
	} else if (turi == 2) {
		// trotuar: 40x40 sm beton plitka, choklar, rang farqi
		vec2 id = floor(p / 0.4);
		vec2 f = fract(p / 0.4) * 0.4;
		float chok = 1.0 - smoothstep(0.006, 0.014, min(min(f.x, 0.4 - f.x), min(f.y, 0.4 - f.y)));
		chok *= 1.0 - uzoq;
		alb = rang * (0.88 + 0.18 * xesh(id)) * (0.9 + 0.2 * fbm(p * 0.3));
		alb = mix(alb, alb * 0.55, chok);
		rough = 0.9;
	} else {
		// bo'yoq: oq, eskirgan (asfalt ko'rinib turadi)
		float eskirgan = smoothstep(0.35, 0.65, fbm(p * 1.5));
		alb = mix(rang, vec3(0.3, 0.3, 0.31), eskirgan * 0.55);
		rough = 0.6;
	}
	ALBEDO = alb;
	ROUGHNESS = rough;
}
