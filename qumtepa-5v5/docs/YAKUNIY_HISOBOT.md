# Qumtepa 5v5 — yakuniy hisobot

Qumtepa v2 (2v2, 50×50 m) asosida 5v5 bomba rejimi uchun yangi xarita. O'lchami **110×110 m**, Godot 4.3.
Me'morchiligi o'zbek milliy uslubida. 8 bosqichning hammasi bajarildi: xarita, audit, realistik ko'rinish, T/CT personajlari va animatsiyalar.

![Tepadan](shots/01_umumiy.png)

## Bosqichlar

| # | Bosqich | Asosiy natija | Hisobot |
|---|---|---|---|
| 0 | Konsepsiya | 110 m, 3 yo'lak + mid, vaqt maqsadlari | — |
| 1 | 2D blokaut | 55×55 reja, 88 ta pana, 10 smoke, 34 bot nuqtasi. 2D tahlil 59 testi | [STAGE1](STAGE1.md) |
| 2 | Godot greybox | O'ynaladigan 3D xarita, to'qnashuv, NavMesh, raund. 3D vaqtlar 2D dan 4–5% tezroq | [STAGE2](STAGE2.md) |
| 3 | Balans sinovi | Smoke'lar fizika bilan (10/10), 5v5 botlar, 1080 raund. A/B teng, 2 ta nomutanosiblik tuzatildi | [STAGE3](STAGE3.md) |
| 4 | Arxitektura | 5 hudud uslubi (qal'a, bozor, madrasa, karvonsaroy, masjid), mo'ljal binolari. To'qnashuv o'zgarmagan | [STAGE4](STAGE4.md) |
| 5 | Milliy buyumlar | Girih, majolika, ganch, ayvon, vassa, atlas, so'zana, tandir, so'ri, paxta, chinor, Kalta Minor | [STAGE5](STAGE5.md) |
| 6 | Yorug'lik va tovush | Adolatli quyosh, qorong'i burchaksiz, shom rejimi, 6 xil fon tovushi, aks-sado | [STAGE6](STAGE6.md) |
| 7 | Optimallashtirish | Obyekt va chizish buyruqlari −69%, minimap, F9 ko'rsatkichlari, yakuniy tekshiruv | [STAGE7](STAGE7.md) |
| 8 | Audit, realizm, personajlar | Tirqish, teshik va tiqilish yo'q (audit 6/6); PBR teksturalar, osmon, SDFGI, 558 decal; T/CT skelet, 21 animatsiya, AKM/M416 qo'lda, Shift/o'tirish/sakrash, birinchi shaxs | [STAGE8](STAGE8.md) |

## Xarita haqida qisqacha

- **T shimolda, CT janubda.**
- **A site (madrasa):** ochiq, uzun **Long** (snayper yo'lagi) va **Catwalk** orqali kiriladi.
- **B site (karvonsaroy):** zich, yopiq **Tunnels** va **B window** orqali kiriladi. Qo'shimcha **Mid-window** yo'li ham bor.
- **Markaz:** Top mid (bozor) → Mid → **Mid doors** (asosiy snayper dueli, 8.6 s) → CT mid (masjid).
- **Vaqtlar:**

  | | A | B | Mid doors |
  |---|---|---|---|
  | T | 17–20 s | 17–20 s | 12.3 s |
  | CT | 12 s | 12 s | 9.4 s |

- **Raund:** tayyorgarlik 12 s, raund 1:55, bomba 40 s, zararsizlantirish 10 s (kit bilan 5 s).

## Sonlarda

| | |
|---|---|
| O'lcham | 110 × 110 m, 55 × 55 katak (2 m) |
| Uchburchaklar | 91 ming (optimallashtirilgan kadrda o'rtacha 76 ming, soya bilan birga) |
| Teksturalar | 28 ta 1024 px PBR material (rang, normal, ORM, relyef) + osmon panoramasi + 4 decal |
| Personajlar | T (AKM) va CT (M416): 29 suyak, 21 animatsiya |
| To'qnashuv qutilari | 986 |
| Bot sinovlari | 8 × 360 = 2880 raund |
| Avtomatik tekshiruvlar | 59 + 111 + 10 + 6 + 22 = **208** |

## Qanday ochish

1. **O'rnatish:** Godot 4.3 → Import → `qumtepa-5v5/godot/project.godot`.
2. **O'ynash:** **`main.tscn` → F5.** Boshqaruv:
   - WASD — yurish (qadam eshitiladi), **Shift** — sekin yurish (jim), **Ctrl/C** — o'tirish, Space — sakrash;
   - sichqoncha — qarash va o'q uzish, **R** — qayta o'qlash;
   - E — bomba;
   - G — bombani tashlash;
   - B — sotib olish;
   - M — katta xarita;
   - F1 — zonalar va bot nuqtalari;
   - F2 — jamoani almashtirish;
   - F3 — raundni qayta boshlash;
   - F4 — shom rejimi;
   - F9 — FPS.
3. **Bot o'yinini ko'rish:** **`bots.tscn` → F6.**
   - 1–0 — botni kuzatish;
   - Tab — erkin kamera;
   - Space — pauza;
   - +/− — tezlik.
4. **Greybox'da sinash:** **`main_greybox.tscn`.**

## Qayta yaratish va o'zgartirish

Xaritaning yagona manbasi: `tools/layout5.py`. Uni o'zgartirgach:

```
pip install numpy scipy pillow trimesh      # personajlarni qayta yaratish uchun yana: pip install bpy==4.2.0
cd qumtepa-5v5/tools
GODOT=/yo'l/godot4 ./make_all.sh                  # ~1 daqiqa: 2D tahlil, 3D model, Godot loyihasi, NavMesh, testlar, smoke'lar
SHOTS=1 BOTS=360 GODOT=/yo'l/godot4 ./make_all.sh  # + skrinshotlar, ko'rinish va ishlash o'lchovi, 360 raund bot o'yini
RIG=1 GODOT=/yo'l/godot4 ./make_all.sh             # + personajlar (skelet, animatsiyalar) assets_src/*.glb dan qaytadan
```

Har bir o'zgarishdan keyin testlar balans buzilmaganini darhol ko'rsatadi.

## Ochiq qolgan masalalar (haqiqiy o'yinchilar sinovi kerak)

1. **T umumiy g'alabasi botlarda 55–61%, maqsad 45–55%.** A/B farqi atigi 2.4 foiz, ya'ni site'lar teng.
   Ortiqcha T ustunligi bot mantig'idan kelib chiqadi (CT botlar sekin aylanadi). Haqiqiy o'yinchilar bilan tekshirish kerak.
2. **Mid doors smoke kuchli.** Mid taktikalari botlarda 60–74% natija berdi. CT mid'ga qo'shimcha burchak kerakmi, o'yinda ko'rish kerak.
3. **Platforma duellari (birinchi o'limlar):** B platforma ↔ Lower tunnels dueli T foydasiga (~57%),
   A platforma ↔ Long dueli esa taxminan teng (48–53%). Site umumiy natijasi teng, lekin buni o'yinda kuzatish foydali.
4. **FPS videokartali kompyuterda o'lchanmagan.** F9 bilan tekshiring.
5. **Teksturalar va tovushlar protsedural** (tarmoq cheklovi). Fotosurat asosidagisiga almashtirish uchun `godot/textures/<nom>_albedo.jpg`
   (va `_normal`, `_orm`) hamda `godot/audio/*.wav` ni almashtirish kifoya, kod o'zgarmaydi.
6. **Personaj animatsiyalari kod bilan yozilgan** (mocap emas); o'yinchi o'qi hozircha faqat ko'rinish/tovush (zarar tizimi keyingi ish). Batafsil: [STAGE8](STAGE8.md).
