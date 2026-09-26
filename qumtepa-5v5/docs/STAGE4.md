# 4-bosqich: arxitektura — hisobot

> Eslatma: 5-bosqichda badgir Kalta Minor'ga, palmalar chinorga almashtirildi; skrinshotlar yangilangan.

**Natija:** greybox qutilari o'rniga 5 ta hudud uslubidagi arxitektura qurildi. O'yin geometriyasi
**aynan bir xil** qoldi. Buning isboti: 3-bosqichdagi 360 raundlik bot sinovi xuddi shu seed bilan qayta o'ynaldi
va natija raqamma-raqam bir xil chiqdi (T 57.8%, A 56.9%, B 58.5%). Testlar: 2D 59/59, Godot 79/79, smoke 10/10.

![B site — karvonsaroy](shots/09_b_site_karvonsaroy.png)

## Asosiy qoida: arxitektura balansni buzmasligi kerak

- **To'qnashuv, clip'lar va NavMesh greybox bilan bir xil.** `build5.py` arch modelini yig'ayotganda to'qnashuv
  qutilari greybox'nikiga tengligini o'zi tekshiradi, farq bo'lsa to'xtaydi.
- **Bezaklar faqat ko'rinish uchun.** Devordan chiqib turgan detallar (poydevor, ramka, derazalar) ≤ 0.25 m.
  Balkon, soyabon, gilam va chiroqlar ko'z balandligidan (1.6 m) yuqorida, 2.7 m dan baland.
- **Mo'ljal binolari o'yin maydonidan tashqarida.** Minora, badgir, gumbaz va burjlar binolar ustida, 12 m lik clip'dan yuqorida.
- **Greybox saqlanib qoldi.** U sinovlar uchun `main_greybox.tscn` sahnasida turibdi.

## Hudud uslublari

O'yinchi atrofga qarab qayerda turganini bilishi uchun har bir hudud o'z uslubida:

| Uslub | Qayerda | Devorlar | Xususiyatlari |
|---|---|---|---|
| **Qal'a** | T spawn, Long doors, Outside long, Upper tunnels | To'q qumtosh | Tishli devorlar, tor tuynuklar, T spawn yonida 2 ta darvoza burji |
| **Bozor** | Top mid, Mid, Catwalk, B window | Suvoq, toshloq pol | Do'kon eshiklari, rangli soyabonlar, osilgan gilamlar, tomda chaylalar |
| **Madrasa** | A site, Long, A ramp | Oq suvoq, ko'k koshin | Peshtoqlar (koshin ramkali chuqurcha-arkalar), koshin friz, kichik gumbazlar, **minora** |
| **Karvonsaroy** | B site, Lower tunnels, B ramp, B doors | Qizil g'isht | Yog'och balkonlar, chiqib turgan to'sinlar, tomda so'rilar, **badgir** (shamol minorasi) |
| **Masjid** | CT spawn, CT mid, CT yo'llari | Oq suvoq, firuza koshin | Firuza gumbazlar, pilyastrlar, **katta gumbaz** (CT mid ortida) |

Hamma joyda umumiy detallar bor:
- **Devorlar:** poydevor, burchak toshlari, qavat chizig'i.
- **Oyna va eshiklar:** derazalar (darchali, panjarali, xochli) va arkali eshiklar.
- **Yopiq yo'laklar:** qovurg'a arkalar va chiroqlar. Spawn shiftlarida yog'och to'sinlar bor.

Panalar ham haqiqiy ko'rinishga ega bo'ldi:
- **Oddiy panalar:** yog'och qutilar, temir halqali bochkalar, sopol ko'zalar, qum qoplari.
- **Xarobalar:** tepasi notekis, sinib tushgan toshlar bilan.
- **Quduqlar:** tepasida kichik gumbaz bor.
- **Palmalar:** barglari bilan.
- **Eshik o'rinlari:** Mid doors va B doors'da devorga ochib qo'yilgan yog'och eshik tavaqalari.

## Raqamlar

| | Greybox | Arxitektura |
|---|---|---|
| Uchburchaklar | 21 ming | 93 ming |
| Model hajmi | 2.6 MB | 13.3 MB |
| Teksturalar | rangli to'r | 21 ta (12 tasi yangi: koshin ×2, g'isht, toshloq, soyabon ×3, gilam, gumbaz, oq suvoq, to'q qumtosh, och yog'och) |
| Bezak elementlari | — | 46 eshik, 127 deraza, 16 balkon, 34 peshtoq, 10 soyabon, 15 gumbaz, 5 mo'ljal binosi |
| To'qnashuv qutilari | 986 | 986 (bir xil) |

93 ming uchburchak zamonaviy kompyuter uchun kam. 7-bosqichda baribir occlusion, LOD va MultiMesh bilan optimallashtiriladi.

## Skrinshotlar

| | |
|---|---|
| ![](shots/03_long_a_site.png) Long → A site, orqada minora | ![](shots/12_a_site_minora.png) A site: madrasa peshtoqi va minora |
| ![](shots/10_top_mid_bozor.png) Top mid: bozor | ![](shots/05_mid_doors.png) Top mid → Mid doors |
| ![](shots/04_tunnels_b_site.png) Lower tunnels (g'isht) | ![](shots/06_ct_mid.png) CT mid: masjid uslubi |
| ![](shots/02_t_spawn_top_mid.png) T spawn: qal'a | ![](shots/11_ct_spawn.png) CT spawn: yog'och to'sinlar |

![Tepadan](shots/01_umumiy.png)

## Qanday ochish

- **O'ynash:** `main.tscn` (arxitektura) → F5.
- **Bot o'yinini kuzatish:** `bots.tscn` → F6.
- **Greybox'da sinov:** `main_greybox.tscn`, rangli panalar va 1 m to'r bilan.
- **Qayta yaratish:** `GODOT=... ./tools/make_all.sh`. U ikkala modelni ham yig'adi, testlar va smoke'larni tekshiradi.

## Cheklovlar va keyingi bosqichlar

- **Teksturalar protsedural (kod bilan yaratilgan, 512 px).** 5-bosqichda sifatini oshirish,
  tafsilot qo'shish va kerak bo'lsa tayyor PBR teksturalar (masalan, Poly Haven) qo'shish mumkin.
- **Skrinshotlar serverda Compatibility renderida olingan.** Godot'da Forward+ bilan soyalar, SSAO va yorug'lik
  yaxshiroq ko'rinadi. Yorug'lik va atmosfera 6-bosqichda sozlanadi.
- **FPS o'lchanmagan,** chunki serverda videokarta yo'q. Iltimos, o'zingizda tekshirib ko'ring: Godot'da Debugger → Monitors → FPS.
- **Palma barglari va yopiq yo'lak shiftlari oddiy.** 5-bosqichda yaxshilanadi.
