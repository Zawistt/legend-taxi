# Legend Taxi: Samarqand — Godot loyihasi

Samarqandning real ma'lumotlari (OpenStreetMap + Overture Maps + Microsoft
Building Footprints) asosidagi ochiq dunyo o'yini uchun Godot 4.7 loyihasi.

## Ochish

1. [Godot 4.7](https://godotengine.org/download) ni yuklab oling (Forward+ uchun Vulkan kerak).
2. Godot → **Import** → shu `godot/` papkadagi `project.godot` ni tanlang.
3. Birinchi ochilishda 1893 ta GLB import qilinadi (bir necha daqiqa).
4. **F5** — o'yin boshlanadi, mashina Registon ko'chasida turadi.

## Boshqaruv

| Tugma | Vazifa |
|---|---|
| W / ↑ | gaz |
| S / ↓ | tormoz, orqaga |
| A D / ← → | rul |
| Probel | qo'l tormozi (drift) |
| C | kamera: orqadan → tepadan → erkin uchish |
| R | mashinani eng yaqin yo'lga qaytarish |
| Erkin kamerada | sichqoncha + WASD, Shift — tez, E/Q — yuqoriga/pastga |

## Tuzilishi

```
godot/
  project.godot, asosiy.tscn
  shahar/bolak_X_Z.glb   — 400×400 m lik shahar bo'laklari (1893 ta)
  shahar/indeks.json     — bo'laklar joyi, boshlash nuqtasi, statistika
  shahar/yollar.json     — avtomobil yo'llari markaz chiziqlari (3D)
  skriptlar/
    asosiy.gd       — muhit (osmon, quyosh, tuman), yer, HUD
    shahar.gd       — bo'laklarni mashina atrofida oqim bilan yuklash
    materiallar.gd  — GLB material nomlarini Godot materiallariga almashtirish
    mashina.gd      — VehicleBody3D taksi
    kamera.gd       — 3 rejimli kamera
    yollar.gd       — eng yaqin yo'l, ko'cha nomi
```

**Koordinatalar:** X — sharq, Y — yuqori, Z — janub, metr. (0, 0, 0) — Registon
yer sathi (dengizdan 714 m).
Har bir GLB o'z burchagiga nisbatan; joyi `indeks.json` da (`x`, `z`).

**GLB ichida:** har bir material alohida tugun. `-col` qo'shimchali tugunlarga
Godot avtomatik to'qnashuv yasaydi (devorlar, relyef, avtomobil yo'li).
`Yol_Chegara-colonly` — avtomobil yo'li chetidagi ko'rinmas devor: mashina
faqat yo'lda yuradi (4-bosqichda uning o'rnida bordyur ko'rinadi).
UV metrda (1 birlik = 1 m), shuning uchun istalgan tayllanadigan tekstura
to'g'ri o'lchamda tushadi.

**Relyef:** Copernicus DEM (30 m) → binolar va daraxtlar olib tashlangan →
silliqlangan → 20 m to'r. Uylar, yo'llar va bog'lar shu yuzaga o'tiradi.

**Yo'l va uylar:** avtomobil yo'lining kengligi atrofdagi real binolar orasiga
sig'adigan qilib toraytiriladi; barcha avtomobil yo'llari bitta yuzaga
birlashtiriladi (chorrahalar toza). Yo'lga kirib turgan uy qismlari yo'l
chetidan kesiladi, asosan yo'l ustidagi noto'g'ri aniqlangan "uylar" olib
tashlanadi.

| Material | Nima |
|---|---|
| `Devor_Suvoq`, `Devor_Gisht` | hovli uylar |
| `Devor_Panel` | ko'p qavatli uylar, mehmonxona, idora |
| `Devor_Dokon` | do'kon, savdo, sanoat |
| `Devor_Jamoat` | maktab, shifoxona, universitet |
| `Devor_Garaj` | garaj, omborxona |
| `Obida_Gisht`, `Tom_Obida` | tarixiy obidalar (masjid, madrasa, maqbara) |
| `Tom_Tekis`, `Tom_Shifer` | tomlar |
| `Yol_Asfalt`, `Yol_Mahalla` | avtomobil yo'li yuzasi (katta / mahalla) |
| `Yol_Piyoda`, `Yol_Tuproq`, `Temir_Yol` | piyoda yo'lak, tuproq yo'l, temir yo'l |
| `Yer_Tuproq` | relyef |
| `Yer_Maysa`, `Yer_Dala`, `Yer_Qabr`, `Suv` | yer qatlamlari |

## Ma'lumotni qayta yasash

```
pip install pyarrow fsspec aiohttp requests shapely numpy scipy trimesh mapbox-earcut rasterio
python3 tools/samarqand_tayyorla.py   # Overture'dan -> samarqand/*.json
python3 tools/godot_eksport.py        # samarqand/*.json + DEM -> godot/shahar/*.glb (~4 daqiqa)
```

## Aniqlik

- Uylar shakli va joylashuvi — real (87 316 ta uy).
- Balandlik: 123 tasi o'lchangan, 2 248 tasi qavatlar sonidan, qolgani uy turi
  va maydoniga qarab taxmin. Qavatlar soni OpenStreetMap'ga kiritilgani sari
  qayta eksportda aniqlashadi.

Litsenziya: xarita ma'lumotlari © OpenStreetMap hissadorlari (ODbL),
Overture Maps Foundation, Microsoft Building Footprints (ODbL), Copernicus
DEM GLO-30 (© DLR e.V. 2010-2014, © Airbus Defence and Space GmbH 2014-2018,
Yevropa Ittifoqi Copernicus dasturi). O'yinda
shu yozuv ko'rsatilishi shart.
