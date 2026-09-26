QUMTEPA v2 — 3-bosqich: arxitektura detallari (Godot 4.3)

OCHISH: Godot 4.3 -> Import -> project.godot -> F5.
BOSHQARUV: WASD, Space, sichqoncha, Esc | E — bomba o'rnatish/zararsizlantirish | G — bombani tashlash
           B — sotib olish | F1 — zonalar | F2 — jamoa almashtirish | F3 — raundni qayta boshlash

3-BOSQICHDA QO'SHILDI
- Burchak toshlari (quoins) — ochiq maydonga qaragan bino burchaklarida.
- Qavat chizig'i — 3 m balandlikda bo'rtiq tosh tasma.
- Chuqur derazalar: tosh ramka, ustki to'sin, tokcha; 3 uslub — darchali, temir panjarali, yog'och xochli.
- Arkali eshiklar kalit toshi bilan; yog'och balkonlar (tayanchlar, panjara, eshik).
- Chiqib turgan yog'och to'sinlar, tomlarda tishli devorlar, arkalar ostida ustunlar (pilastrlar).
- To'qnashuv yangilandi: ustunlar va balkon pollari qo'shildi; balkonlar ustida player clip bor
  (ular faqat ko'rinish uchun — tomga yoki balkonga chiqib, balansni buzib bo'lmaydi).
- Tashqi zinapoyalar ataylab qo'shilmadi: ular baland pozitsiya ochib, balansni o'zgartiradi.
- Uchburchaklar: ~50 ming (avval ~34 ming).

TEKSHIRUV: godot --headless --fixed-fps 60 -s res://tests/run_tests.gd  ->  52 / 52
Vaqtlar (fizika bilan): T->A 7.5 s, CT->A 4.5 s; T->B 7.5 s, CT->B 4.8 s.

2-BOSQICH TIZIMLARI (o'zgarmagan)
Raund: tayyorgarlik 5 s, sotib olish 20 s, raund 1:25, bomba 35 s, o'rnatish 3 s, zararsizlantirish 7 s.
Zonalar, 5+5 spawn, sirt turlari (stone/wood/metal/cloth), fizika qatlamlari, NavMesh, 22 bot nuqtasi.

QAYTA YARATISH (tools/): build.py -> analyze.py -> analyze2.py -> gen_godot.py; bake_nav.gd.
