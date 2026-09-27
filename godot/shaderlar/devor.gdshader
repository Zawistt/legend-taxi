// Bino devorlari: derazalar, eshik/darvoza, do'kon vitrinasi, g'isht/suvoq/panel
// fakturasi, kir-chang. Hammasi protsedural — GLB'da faqat UV'lar bor:
//   UV  = (u — devor bo'lagi bo'ylab 0..L m, v — eng past yer sathidan balandlik m)
//   UV2 = (±(round(L*100) + urug'), qavat*1000 + round(Hh*10))
//         manfiy x — shu devor bo'lagida eshik bor; Hh — bo'g'otgacha balandlik
shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

global uniform float tun;                         // 0 — kun, 1 — tun

uniform int turi = 0;                             // 0 suvoq, 1 g'isht, 2 panel, 6 obida
uniform vec3 rang_a : source_color = vec3(0.88, 0.83, 0.72);
uniform vec3 rang_b : source_color = vec3(0.92, 0.80, 0.64);
uniform vec3 rang_c : source_color = vec3(0.84, 0.84, 0.82);
uniform bool derazalar = true;
uniform float deraza_eni = 1.3;
uniform float deraza_boyi = 1.5;
uniform float oraliq = 3.4;
uniform float tokcha = 0.85;                      // deraza tagi, qavat polidan
uniform bool dokon_qavat = false;                 // 1-qavat vitrina
uniform bool darvoza = false;                     // hovli darvozasi (keng metall)
uniform bool garaj = false;
uniform int debug = 0;                            // 1 — UV, 2 — UV2 ko'rsatish (sinov)

varying vec2 v_uv;
// flat: UV2 butun devor bo'lagi uchun bir xil; interpolyatsiya xatosi (1 ulp) xesh
// funksiyasida kuchayib, har pikselga boshqa "tasodif" beradi — shuning uchun flat.
varying flat vec2 v_uv2;

float xesh(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float xesh1(float p) { return fract(sin(p * 91.345) * 47453.5453); }
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
// ichida < 0 bo'lgan to'rtburchak masofasi
float quti(vec2 p, vec2 markaz, vec2 yarim) {
	vec2 d = abs(p - markaz) - yarim;
	return max(d.x, d.y);
}
// aa — piksel o'lchami (metrda). U fragment() boshida, bir xil boshqaruv oqimida hisoblanadi:
// fwidth() ni if ichida chaqirish aniqlanmagan natija beradi (sepkil).
float ichida(float d, float aa) { return 1.0 - smoothstep(-aa, aa, d); }

void vertex() {
	v_uv = UV;
	v_uv2 = UV2;
}

void fragment() {
	float u = v_uv.x, v = v_uv.y;
	float AA = max(max(fwidth(u), fwidth(v)), 1e-4);
	float FW_V = fwidth(v);
	float ax = abs(v_uv2.x);
	float L = floor(ax) / 100.0;
	float urug = floor(fract(ax) * 1000.0 + 0.5) / 1000.0;
	bool eshik = v_uv2.x < 0.0;
	float qavat = floor(v_uv2.y / 1000.0 + 0.0001);
	float Hh = mod(v_uv2.y, 1000.0) / 10.0;
	float s1 = xesh1(urug * 97.0 + 1.0), s2 = xesh1(urug * 57.0 + 3.0), s3 = xesh1(urug * 13.0 + 7.0);

	// ---- devor fakturasi ----
	vec3 asos = s1 < 0.45 ? mix(rang_a, rang_b, s2) : mix(rang_a, rang_c, s2);
	vec3 alb = asos;
	float rough = 0.9;
	float n1 = fbm(vec2(u, v) * 0.7 + urug * 50.0);
	float n2 = mix(fbm(vec2(u, v) * 6.0), 0.5, smoothstep(0.05, 0.2, FW_V));
	if (turi == 1 || turi == 6) {
		// g'isht: 25 x 6.5 sm (obida: 27 x 5.5 sm, sarg'ish)
		vec2 gs = turi == 6 ? vec2(0.27, 0.06) : vec2(0.25, 0.075);
		float qator = floor(v / gs.y);
		float gu = u + mod(qator, 2.0) * gs.x * 0.5;
		vec2 id = vec2(floor(gu / gs.x), qator);
		vec2 f = vec2(fract(gu / gs.x) * gs.x, fract(v / gs.y) * gs.y);
		float chok = 1.0 - ichida(quti(f, gs * 0.5, gs * 0.5 - 0.008), AA);
		vec3 g = asos * (0.82 + 0.3 * xesh(id + urug * 13.0));
		// uzoqda (bitta pikselga bir nechta g'isht) naqsh o'rtacha rangga o'tadi — miltillamasin
		float uzoq = smoothstep(0.25, 0.7, FW_V / gs.y);
		vec3 ortacha = mix(asos * 0.97, vec3(0.72, 0.69, 0.63), 0.18);
		alb = mix(mix(g, vec3(0.72, 0.69, 0.63), chok), ortacha, uzoq);
		rough = mix(mix(0.85, 0.95, chok), 0.88, uzoq);
	} else if (turi == 2) {
		// panel uy: 3 m lik plitalar choklari
		float cu = abs(fract(u / 3.0 + 0.5) - 0.5) * 3.0;
		float cv = abs(fract((v - 0.3) / max(Hh / max(qavat, 1.0), 2.6) + 0.5) - 0.5);
		float chok = max(1.0 - smoothstep(0.015, 0.035, cu), 1.0 - smoothstep(0.004, 0.01, cv));
		alb = asos * (0.88 + 0.2 * n1) * (1.0 - 0.25 * chok);
	} else {
		alb = asos * (0.86 + 0.22 * n1) * (0.97 + 0.06 * n2);
	}
	// yer yonida kir-chang, pastdan tepaga yo'qoladi; devor tepasida yomg'ir izlari
	alb *= mix(0.72, 1.0, smoothstep(0.0, 1.1, v));
	alb *= 1.0 - 0.12 * smoothstep(0.55, 0.9, fbm(vec2(u * 3.0, v * 0.25) + urug * 7.0)) * smoothstep(1.0, 3.0, v);

	float metall = 0.0;
	float specular = 0.5;
	vec3 nur = vec3(0.0);

	// ---- derazalar ----
	float fh = qavat > 0.5 ? max((Hh - 0.5) / qavat, 2.6) : 3.2;
	float vv = v - 0.3;
	float fi = floor(vv / fh);
	float fv = vv - fi * fh;
	bool vitrina = dokon_qavat && fi < 0.5;
	if (derazalar && !garaj && L > 1.8 && fi >= 0.0 && fi < qavat && v < Hh - 0.2) {
		float sp = vitrina ? 4.2 : (turi == 2 ? oraliq : oraliq * (0.9 + 0.2 * s3));   // panel: balkonlar bilan mos
		float n = floor((L - 0.6) / sp);
		if (n >= 1.0) {
			float chet = (L - n * sp) * 0.5;
			float lu = u - chet;
			float wi = floor(lu / sp);
			if (wi >= 0.0 && wi < n) {
				float cx = lu - (wi + 0.5) * sp;
				float ww = vitrina ? sp - 0.5 : deraza_eni;
				float wh = vitrina ? 2.5 : deraza_boyi;
				float tag = vitrina ? 0.25 : tokcha;
				// hovli uylarida 1-qavat derazalari ko'chaga kamroq qaraydi
				bool bor = vitrina || fi > 0.5 || xesh(vec2(wi, urug)) > 0.25;
				if (eshik && fi < 0.5 && abs(u - L * 0.5) < (darvoza ? 2.2 : 1.2)) bor = false;
				if (bor) {
					float d = quti(vec2(cx, fv), vec2(0.0, tag + wh * 0.5), vec2(ww, wh) * 0.5);
					float rom = ichida(d, AA);
					float oyna = ichida(d + 0.07, AA);
					// o'rta ustun
					float ustun = 1.0 - smoothstep(0.02, 0.035, abs(cx));
					oyna *= 1.0 - ustun * (vitrina ? 0.0 : 1.0);
					vec3 rom_rang = s2 < 0.6 ? vec3(0.9, 0.9, 0.88) : vec3(0.35, 0.22, 0.14);
					float wid = xesh(vec2(wi + urug * 31.0, fi));
					// oyna: qorong'i, yaltiroq; ba'zan parda
					vec3 oyna_rang = mix(vec3(0.04, 0.05, 0.06), vec3(0.45, 0.40, 0.33), step(0.65, wid) * 0.5);
					alb = mix(alb, rom_rang, rom - oyna);
					rough = mix(rough, 0.4, rom - oyna);
					alb = mix(alb, oyna_rang, oyna);
					rough = mix(rough, 0.14, oyna);
					specular = mix(specular, 0.75, oyna);
					metall = mix(metall, 0.1, oyna);
					// deraza tokchasi soyasi
					float tokcha_soya = ichida(quti(vec2(cx, fv), vec2(0.0, tag - 0.06), vec2(ww * 0.5 + 0.08, 0.04)), AA);
					alb *= 1.0 - 0.35 * tokcha_soya;
					// tunda chiroq
					float yongan = step(wid, vitrina ? 0.85 : 0.42);
					vec3 chiroq = mix(vec3(1.0, 0.72, 0.42), vec3(0.85, 0.9, 1.0), step(0.8, xesh(vec2(fi, wi))));
					nur += oyna * yongan * chiroq * tun * (vitrina ? 4.0 : 2.2);
				}
			}
		}
	}
	// do'kon peshtaxtasi (vivid reklama taxtasi, tunda yonadi)
	if (vitrina && fv > 2.85 && fv < 3.35 && L > 3.0) {
		vec3 rr = vec3(xesh1(urug * 3.1), xesh1(urug * 5.7), xesh1(urug * 9.3));
		rr = normalize(rr + 0.05) * 0.9;
		alb = rr;
		rough = 0.35;
		nur += rr * tun * 3.0;
	}

	// ---- eshik yoki darvoza ----
	if (eshik) {
		float ew = garaj ? min(L - 0.6, 2.6) : (darvoza ? 3.0 : 1.0);
		float eh = garaj || darvoza ? 2.4 : 2.2;
		float d = quti(vec2(u, v), vec2(L * 0.5, eh * 0.5), vec2(ew, eh) * 0.5);
		float e = ichida(d, AA);
		if (e > 0.0) {
			vec3 er;
			if (darvoza || garaj) {
				// metall darvoza: ko'k, yashil yoki jigarrang; vertikal qovurg'alar
				er = s3 < 0.33 ? vec3(0.12, 0.3, 0.55) : (s3 < 0.66 ? vec3(0.12, 0.38, 0.25) : vec3(0.38, 0.22, 0.12));
				float qovurga = 0.85 + 0.15 * step(0.5, fract((u - L * 0.5) / 0.12));
				er *= qovurga;
				metall = mix(metall, 0.5, e);
				rough = mix(rough, 0.45, e);
			} else {
				er = s3 < 0.5 ? vec3(0.32, 0.19, 0.1) : vec3(0.55, 0.55, 0.55);
				rough = mix(rough, 0.6, e);
			}
			float chiziq = ichida(d + 0.05, AA);
			alb = mix(alb, er * mix(0.7, 1.0, chiziq), e);
		}
		// eshik tepasida chiroq (tunda)
		float lamp = ichida(quti(vec2(u, v), vec2(L * 0.5, eh + 0.35), vec2(0.12, 0.08)), AA);
		nur += lamp * vec3(1.0, 0.8, 0.5) * tun * 6.0;
	}

	if (debug == 1) { alb = vec3(fract(u), fract(v), 0.0); nur = vec3(0.0); }
	if (debug == 2) { alb = vec3(fract(L * 0.1), urug, fract(Hh * 0.1)); nur = vec3(0.0); }
	ALBEDO = alb;
	ROUGHNESS = rough;
	METALLIC = metall;
	SPECULAR = specular;
	EMISSION = nur;
}
