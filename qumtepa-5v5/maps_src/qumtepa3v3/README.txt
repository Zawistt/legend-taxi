QUMTEPA v2 — YAKUNIY LOYIHA (Godot 4.3)
50 x 50 m, 5v5 raqobat xaritasi, bomba o'rnatish rejimi
KO'RINISHI: stilizatsiya qilingan low-poly (tekis ranglar, qirrali shakllar)

OCHISH
Godot 4.3 -> Import -> project.godot -> F5. Forward+ rejimida qoldiring.

BOSHQARUV
WASD, Space, sichqoncha, Esc | E — bomba o'rnatish/zararsizlantirish | G — bombani tashlash
B — sotib olish | F1 — zonalar | F2 — jamoa | F3 — raund | F4 — grafika sifati

IKKI USLUB BITTA KODDA
O'yin mexanikasi, to'qnashuv va balans ikkalasida bir xil:
  MAP_STYLE=lowpoly   python build.py && python gen_godot.py   (hozirgi — stilizatsiya)
  MAP_STYLE=realistic python build.py && python gen_godot.py   (PBR — realistik)
Lowpoly'da nima o'zgaradi:
- Tekis rang palitrasi, teksturalar 1024 px -> 128 px, normal va ORM xaritalari yo'q.
- Kir, qum va dog' qatlamlari o'chirilgan.
- Silindr, gumbaz va arkalar kamroq qirrali; palma barglari yo'g'onroq.
- Yassi soyalash: har uchburchak o'z uchlariga ega (faceted shading).
- Uchburchaklar 57 ming -> 46 ming, GLB 7.5 MB -> 5.0 MB, butun loyiha 1.5 MB.
- Yorug'lik: tumansiz, kontrastli, to'yingan ranglar; chang zarralari o'chirilgan.

YORUG'LIKNI SOZLASH
Godot'da soyalar brauzerdagi ko'rinishdan to'qroq chiqadi. Yoritish uchun main.tscn ichida
Fill (yon tomondan) yoki Bounce (tepadan) yorug'ligining energiyasini oshiring, yoxud
WorldEnvironment -> ambient_light_energy. Redaktorda o'zgarish darhol ko'rinadi.

TEKSHIRUVLAR (ikkalasi toza)
  godot --headless --fixed-fps 60 -s res://tests/run_tests.gd   ->  52 / 52
  godot --headless -s res://tests/audit.gd                       ->  0 muammo
Audit: pol teshiklari (5328 nuqta), devor tirqishlari, xaritadan chiqib ketish (200 yo'nalish),
havoda osilgan obyektlar, shiftsiz kataklar, navmesh, sirt turlari, band spawn nuqtalari.

O'YIN BALANSI (haqiqiy fizika bilan, 4.5 m/s)
  A site: T 8.7 s / CT 5.3 s -> CT 3.4 s oldin | B site: T 8.6 s / CT 5.6 s -> CT 3.0 s oldin
  Mid doors: T 6.2 s / CT 4.2 s | Spawn -> spawn ko'rinish: YO'Q
  Raund: tayyorgarlik 5 s, sotib olish 20 s, raund 1:25, bomba 35 s,
         o'rnatish 3 s, zararsizlantirish 7 s (to'plam bilan 3.5 s), 13 raundgacha.

XARITA TUZILISHI
T spawn shimolda, CT janubda, A site g'arbda, B sharqda. A ochiq (25 m ko'rinish),
B yopiq va yaqin jangli (18 m). Har site'ga 3 tadan kirish. Mid burilishli.

TEXNIK TARKIB
- map/desert_map.glb — 46 ming uchburchak, teksturalar ichida.
- map/collision.tscn — ~390 blok + 2 zina qiyaligi; sirt turlari: stone/wood/metal/cloth.
- Fizika qatlamlari: 1 world, 2 player_clip, 3 grenade_clip, 4 players, 5 hitboxes,
  6 grenades, 7 triggers.
- map/navmesh.res — 477 poligon; AIPoints — botlar uchun 22 ta strategik nuqta.
- Audio shinalari: Master, Interior (reverb), Ambience; scripts/audio_zones.gd avtomatik almashtiradi.
- Occlusion culling yoqilgan + 54 ta OccluderInstance3D.

QUROLLAR UCHUN TAYYOR JOYLAR
player.gd: team, has_bomb, ai_move. Sotib olish menyusida AKM / pichoq / granata o'rinlari.
Hitbox uchun 5-qatlam, granata uchun 6-qatlam va grenade_clip tayyor.
AudioZones.current_bus() — qurol ovozi uchun joriy shinani qaytaradi.

QAYTA YARATISH (tools/)
layout.py — reja va o'yin qoidalari | build.py — 3D model (fix_glb.py ORM'ni birlashtiradi)
textures_lowpoly.py — stilizatsiya palitrasi | textures4.py — realistik PBR to'plami
analyze.py / analyze2.py — balans va chizma | gen_godot.py — loyihani qayta yaratadi
bake_nav.gd — navmesh | shot.gd — rasm olish (SHOT_ID=0..6)
