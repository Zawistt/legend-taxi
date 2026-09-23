# Legend Taxi City (Godot 4.3+)

Shahar ichida taksi bilan kezib yuriladigan 3D o'yin uchun boshlang'ich skelet.

## Ochish

Godot 4.3 (yoki yangi 4.x) bilan `godot-taxi-city/project.godot` faylini oching.

## Boshqarish

- **W / A / S / D** yoki **strelkalar** — yurish, orqaga, o'ngga-chapga burilish
- **Space** — tormoz

## Tuzilma

- `scenes/Main.tscn` — asosiy sahna: yorug'lik, `City` (bo'sh, shahar modeli shu yerga qo'shiladi), placeholder `Ground` tekisligi, `Taxi`, kamera.
- `scenes/Taxi.tscn` — hozircha sariq quti (placeholder taksi). Keyinchalik `Body` mesh'ini haqiqiy mashina modeliga almashtirish mumkin.
- `scripts/taxi_controller.gd` — oddiy arcade uslubidagi harakat (tezlashish, tormoz, burilish, tortishish kuchi).
- `scripts/camera_follow.gd` — taksi orqasidan yumshoq kuzatib boruvchi kamera.
- `assets/city/` — shahar 3D modelini shu yerga joylashtiring (batafsil: `assets/city/README.md`).

## Shahar modelini qo'shish

`assets/city/README.md` faylida qadamlar yozilgan: modelni joylashtirish, `City` tuguniga ulash, collision qo'shish.

## Hajm va performance bo'yicha tavsiyalar

- Format: **GLB** (bitta faylda mesh + teksturalar, Godotda eng yaxshi ishlaydi).
- Yuqori-poli/4K teksturali modellar o'rniga kichikroq (1K–2K) teksturali versiyani tanlang — build hajmi va yuklash tezligiga bevosita ta'sir qiladi.
- Import qilingandan keyin har bir teksturaga `.import` sozlamalarida **VRAM Compressed** va **Limit** (1024–2048px) qo'llang.
- Katta shaharda ko'p takrorlanuvchi obyektlar (daraxt, ustun, chiroq) uchun `MultiMeshInstance3D` ishlatish drawcall/hajmni kamaytiradi.
- Uzoqdagi obyektlar uchun soyalarni o'chirish yoki LOD ishlatish performance'ni yaxshilaydi.
