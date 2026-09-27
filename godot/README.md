# Legend Taxi: Samarqand — Godot loyihasi

Samarqandning real ma'lumotlari (OpenStreetMap + Overture Maps + Microsoft
Building Footprints) asosidagi ochiq dunyo o'yini uchun Godot 4.7 loyihasi.

## Ochish

1. [Godot 4.7](https://godotengine.org/download) ni yuklab oling (Forward+ uchun Vulkan kerak).
2. Godot → **Import** → shu `godot/` papkadagi `project.godot` ni tanlang.
3. Birinchi ochilishda 1084 ta GLB import qilinadi (~1 daqiqa).
4. **F5** — o'yin boshlanadi, mashina Registon ko'chasida turadi.

## Boshqaruv

| Tugma | Vazifa |
|---|---|
| W / ↑ | gaz |
| S / ↓ | tormoz, orqaga |
| A D / ← → | rul |
| Probel | qo'l tormozi (drift) |
| C | kamera: orqadan → tepadan → erkin uchish |
| R | mashinani to'g'rilash |
| Erkin kamerada | sichqoncha + WASD, Shift — tez, E/Q — yuqoriga/pastga |

## Tuzilishi

```
godot/
  project.godot, asosiy.tscn
  shahar/bolak_X_Z.glb   — 400×400 m lik shahar bo'laklari (1084 ta)
  shahar/indeks.json     — bo'laklar joyi, boshlash nuqtasi, statistika
  skriptlar/
    asosiy.gd       — muhit (osmon, quyosh, tuman), yer, HUD
    shahar.gd       — bo'laklarni mashina atrofida oqim bilan yuklash
    materiallar.gd  — GLB material nomlarini Godot materiallariga almashtirish
    mashina.gd      — VehicleBody3D taksi
    kamera.gd       — 3 rejimli kamera
```

**Koordinatalar:** X — sharq, Y — yuqori, Z — janub, metr. (0, 0, 0) — Registon.
Har bir GLB o'z burchagiga nisbatan; joyi `indeks.json` da (`x`, `z`).

**GLB ichida:** har bir material alohida tugun. `Devor_*` va `Obida_*`
tugunlari `-col` qo'shimchasi bilan — Godot ularga avtomatik to'qnashuv yasaydi.
UV metrda (1 birlik = 1 m), shuning uchun istalgan tayllanadigan tekstura
to'g'ri o'lchamda tushadi.

| Material | Nima |
|---|---|
| `Devor_Suvoq`, `Devor_Gisht` | hovli uylar |
| `Devor_Panel` | ko'p qavatli uylar, mehmonxona, idora |
| `Devor_Dokon` | do'kon, savdo, sanoat |
| `Devor_Jamoat` | maktab, shifoxona, universitet |
| `Devor_Garaj` | garaj, omborxona |
| `Obida_Gisht`, `Tom_Obida` | tarixiy obidalar (masjid, madrasa, maqbara) |
| `Tom_Tekis`, `Tom_Shifer` | tomlar |
| `Yol_Asfalt`, `Yol_Mahalla`, `Yol_Piyoda`, `Yol_Tuproq`, `Temir_Yol` | yo'llar |
| `Yer_Maysa`, `Yer_Dala`, `Yer_Qabr`, `Suv` | yer qatlamlari |

## Ma'lumotni qayta yasash

```
pip install pyarrow fsspec aiohttp requests shapely numpy trimesh mapbox-earcut
python3 tools/samarqand_tayyorla.py   # Overture'dan -> samarqand/*.json
python3 tools/godot_eksport.py        # samarqand/*.json -> godot/shahar/*.glb
```

## Aniqlik

- Uylar shakli va joylashuvi — real (87 316 ta uy).
- Balandlik: 123 tasi o'lchangan, 2 248 tasi qavatlar sonidan, qolgani uy turi
  va maydoniga qarab taxmin. Qavatlar soni OpenStreetMap'ga kiritilgani sari
  qayta eksportda aniqlashadi.

Litsenziya: xarita ma'lumotlari © OpenStreetMap hissadorlari (ODbL),
Overture Maps Foundation, Microsoft Building Footprints (ODbL). O'yinda
shu yozuv ko'rsatilishi shart.
