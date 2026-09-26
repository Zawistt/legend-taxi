# CT qahramon — `idle` (tik turish): tuzatish hisoboti

Manba: `original/ct_idle_v2.glb` (asl fayl o'zgarmagan). Natija: `fixed/ct_idle.glb` + `fixed/ct_idle.json`.
Hammasi Blender Python (bpy 4.2, fon rejimi) orqali: `tools/fix_anim.py` (tuzatish), `tools/anim_audit.py` (o'lchov va render).
Qurol: **M416** (AKM emas).

```
python3 tools/fix_anim.py assets_src/ct_hero/original/ct_idle_v2.glb assets_src/ct_hero/fixed/ct_idle.glb idle --checks assets_src/ct_hero/report/tekshiruv
python3 tools/anim_audit.py assets_src/ct_hero/fixed/ct_idle.glb assets_src/ct_hero/report/keyin --fps 30
```

## O'lchovlar: oldin → keyin

| O'lchov | Oldin | Keyin | Talab | Holat |
|---|---|---|---|---|
| Animatsiyalar | 2 ta (asosiy + 2 kadrlik T-poza) | 1 ta: `idle` | faqat `idle` | ✅ |
| FPS / kadr | 24 kadr/s, 85 kadr | 30 kadr/s, 105 kadr (3.47 s, takroriy oxirgi kadr olib tashlangan) | 30 kadr/s, bake | ✅ |
| Bo'y | 1.70 m | 1.80 m (skelet); turgan holatda 1.78 m — tizzalar sal bukik | 1.80 m | ✅ |
| Yo'nalish | 14.9° burilgan | 1.9° | 0° | ✅ |
| Origin | oyoqlar markazidan 8.3 sm chetda | oyoqlar orasida, polda (0, 0, 0) | oyoqlar orasida | ✅ |
| Pol (eng past nuqta) | −5.5…−6.1 sm (botgan) | −0.08 sm | 0 ± 1 sm | ✅ |
| Chap oyoq tovon / uch | −5.6 / +0.1 sm | −0.06…+0.06 / ±0.01 sm | polda ±1 sm | ✅ |
| O'ng oyoq tovon / uch | −5.2 / −6.0 sm | +0.03 / −0.07 sm | polda ±1 sm | ✅ |
| Oyoq sirpanishi | chap 1.34, o'ng 1.77 sm | chap 0.47, o'ng 0.14 sm | ≤ 1 sm | ✅ |
| Root motion | 1.61 sm | 0.09 sm | joyida | ✅ |
| Loop (1-kadr ↔ oxirgi) | 1.45°, son 1.61 sm | 0.36°, son 0.11 sm | silliq | ✅ |
| Titrash | 0 keskin sakrash | 0 | yo'q | ✅ |
| Umurtqa (son→bo'yin) | 10.1…10.4° oldinga | 3.3…3.4° | ±5° | ✅ |
| Bel (pastki umurtqa) | 7.8…8.0° oldinga | 4.9…5.0° oldinga (orqaga emas) | orqaga egilmagan | ✅ |
| Yelkalar | 3.7…4.2° qiyshiq | 0.0° | ±3° | ✅ |
| Tizzalar | chap 23–24°, o'ng 26–27° | chap 27–29°, o'ng 32–33°, teskari 0 kadr | teskari emas | ✅ |
| Qo'llar orasi | 31 sm | 39.5 sm | 35–45 sm | ✅ |
| Qo'llar balandlik farqi | 13 sm | 3.2 sm | bitta chiziq | ✅ |
| Qo'llar chizig'i (son chizig'i oldiga nisbatan) | 32–33° | 32° | oldinga | ⚠️ izoh pastda |
| Qo'l tanaga kirgan | 0 | 0 kadr | yo'q | ✅ |

**Qo'llar chizig'i haqida (halol):** qo'llar orasidagi chiziq qurol stvoli bo'ylab yotadi va stvolga nisbatan 0° (ikkala qo'l bitta to'g'ri chiziqda). 32° — bu tananing **o'q otish holati** (o'ng yelka orqada, chap oldinda; CS2 va haqiqiy otishmachilar ham shunday turadi): ko'krak 36° burilgan, qurol og'zi esa ko'krak yo'nalishidan ~4° o'ngga. Qo'llarni oyoqlar yo'nalishiga to'liq burish uchun ko'krakni to'g'rilash kerak — unda M416 qo'ndog'i jiletga kirib ketadi yoki chap qo'l yetmaydi (qo'l uzunligi chegarasi).

## Nima o'zgartirildi

1. **Tozalash:** 2 kadrlik T-poza action o'chirildi; faqat `idle` qoldi, NLA va qo'shimcha xususiyatlar tozalandi.
2. **O'lcham / yo'nalish / origin:** ×1.0587 (1.70 → 1.80 m), 0.2° burildi (son va yelka chizig'i bo'yicha), pol 6.1 sm ko'tarildi; oxirida origin to'piqlar o'rtasiga, polga; transformlar qo'llangan.
3. **Root motion:** sonning 1.70 sm siljishi va o'rtacha surilishi olib tashlandi — qahramon joyida.
4. **30 FPS:** har kadr 24 → 30 ga qayta namunalandi (kasr kadrlar), hamma suyaklar bake qilindi.
5. **Loop:** oxirgi va birinchi poza farqi butun klip bo'ylab yumshoq taqsimlandi, takroriy oxirgi kadr olib tashlandi.
6. **Titrash:** yengil 1-2-1 silliqlash (siklik, kvaternion slerp) — harakatning o'zi saqlangan.
7. **Qaddi-qomat:** umurtqa 10° → 3.4° (Spine/Spine1/Spine2 bo'ylab taqsimlab), yelkalar 4° → 0°, bosh o'z yo'nalishini saqlaydi (bo'yin + bosh qoplaydi). Har bir qadam o'lchab tekshirilgan — hamma kadrlarda bir xil.
8. **Qurol va qo'llar (M416):** qo'ndoq o'ng yelka cho'ntagida, jilet sirtida; o'ng qo'l dastani musht bilan ushlaydi, chap qo'l stvol ostini (dasta ↔ chap qo'l 39.5 sm). IK + barmoq suyaklari (musht), qo'llar tanaga kirmaydi. Qurol og'zi 28° chapga (tana burilishi bilan), 10° pastga — "ready" holat.
9. **Oyoqlar:** har bir oyoq uchun IK nishoni (hamma kadrlarda harakatsiz). Botinka tagi gorizontal qilindi (chap oyoq +15° qiyshiq edi), deformatsiyalangan botinka o'lchanib 4 marta aniqlandi → tovon ham, uch ham polda (±0.1 sm). Chap oyoq suyagi o'ngdan 4 sm kalta bo'lgani uchun oyoq to'liq cho'zilib qolardi — son 2.6 sm pastga tushirildi, endi ikkala tizza tabiiy sal bukik (27–33°).
10. **WeaponSocket:** `mixamorig:RightHand` suyagiga bog'langan bo'sh nuqta, GLB ichida eksport qilingan (Godot'da `WeaponSocket` tuguni).
11. **Eksport:** GLB, +Y yuqoriga, animatsiya nomi `idle` (GLB ichida tekshirildi), faqat skelet + model + WeaponSocket; kamera, chiroq, qurol yo'q; material ikki tomonlama.

## WeaponSocket offset (M416, o'ng qo'l suyagiga nisbatan)

Qurol modelining o'z origini (dasta nuqtasi) `mixamorig:RightHand` suyagi boshiga nisbatan:

| | Qiymat |
|---|---|
| Joy (m) | x = −0.0454, y = 0.0848, z = −0.0094 |
| Burilish (XYZ Eyler, °) | −19.29, 64.54, −180.00 |
| Kvaternion (w, x, y, z) | 0.08946, 0.52639, 0.14166, −0.83357 |

Qiymatlar Blender suyak fazosida (Y — suyak bo'ylab). GLB ichidagi `WeaponSocket` tuguni allaqachon shu joyda turadi — Godot'da M416'ni shu tugunga bola qilib qo'yish yetarli (offset 0).

## Rasmlar

- `report/idle_oldin_keyin.jpg` — oldidan / yonidan / tepadan, 0–25–50–75%, oldin va keyin.
- `report/idle_keyin_yaqin.jpg` — 3/4 ko'rinish, yondan, qo'llar yaqindan (ikki tomondan), oyoqlar.
