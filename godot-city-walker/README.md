# Ajdaho — Shahar Bo'ylab (City Walker)

Ajdaho qahramon shahar bo'ylab erkin kezib yuradigan oddiy 3D o'yin. Godot 4.3
uchun tayyorlangan loyiha.

## Qanday ochish kerak

1. [Godot Engine 4.3](https://godotengine.org/download) (yoki undan keyingi 4.x
   versiya) ni o'rnating.
2. Godot'ni oching -> **Import** -> ushbu papkadagi `project.godot` faylini
   tanlang.
3. Loyiha birinchi marta ochilganda Godot ikkita `.glb` modelni (`assets/`
   papkasida) avtomatik import qiladi — bu bir necha soniya vaqt oladi va
   internet talab qilmaydi.
4. Yuqoridagi **▶ (Run Project)** tugmasini bosing.

## Boshqaruv

| Tugma | Amal |
|---|---|
| `W` / `↑` | Oldinga yurish |
| `S` / `↓` | Orqaga yurish |
| `A` / `←` | Chapga |
| `D` / `→` | O'ngga |
| `Shift` | Yugurish |
| `Space` | Sakrash |
| Sichqoncha | Kamerani aylantirish |
| `Esc` | Sichqonchani ushlab turishni yoqish/o'chirish |

## Loyiha tuzilishi

```
CityWalker/
├── project.godot
├── icon.svg
├── assets/
│   ├── dragon_character.glb   # qahramon (animatsiyali skelet bilan)
│   └── city_scene.glb         # shahar sahnasi (statik geometriya)
├── scenes/
│   └── Main.tscn              # asosiy sahna
└── scripts/
    ├── main.gd                # shaharni yuklaydi, kolliziya yaratadi, spawn joyini hisoblaydi
    └── player.gd              # yurish, kamera, animatsiya mantig'i
```

## Texnik izohlar

- **Kolliziya**: shahar modeli qo'lda kolliziya shakllariga ega emas, shuning
  uchun o'yin ishga tushganda `main.gd` har bir bino/yo'l meshi uchun avtomatik
  trimesh kolliziyasini yaratadi (`create_trimesh_collision()`). Shu tufayli
  qahramon binolarga kirib ketmaydi va yo'l sathida to'g'ri yuradi.
- **O'lcham**: qahramon modeli sahnaga qo'shilganda avtomatik o'lchanadi va
  balandligi ~2.6 metrga moslashtiriladi (`player.gd` ichidagi
  `target_height`ni o'zgartirib buni sozlash mumkin).
- **Animatsiya**: `dragon_character.glb` faylida bitta uzun "MOTION" nomli
  animatsiya klipi bor (~21 soniya, alohida "idle/walk/run" holatlarga
  ajratilmagan). Skript uni doimiy tsiklda ijro etadi va yurish tezligiga
  qarab ijro tezligini (speed_scale) moslaydi. Agar animatsiyani aniq
  bo'laklarga (masalan, faqat yurish qismi) bo'lib ishlatmoqchi bo'lsangiz,
  Godot'ning Animation panelida `MOTION` klipini ochib, kerakli oraliqni
  alohida animatsiya sifatida ajratib olishingiz mumkin.
- **Shahar modelining yo'nalishi**: `city_scene.glb` fayli standart Y-up
  tuzatishisiz eksport qilingani uchun `main.gd` uni -90° X o'qi bo'yicha
  avtomatik aylantiradi (`CITY_UP_AXIS_FIX_DEGREES`). Agar shahar modelini
  boshqa fayl bilan almashtirsangiz, ushbu qiymatni moslashingiz kerak
  bo'lishi mumkin.
- **Render usuli**: keng qamrovli moslik uchun `GL Compatibility` rendering
  usuli tanlangan (eski GPU'larda ham ishlaydi). Agar zamonaviy videokartangiz
  bo'lsa, Project Settings -> Rendering -> Renderer bo'limidan `Forward+`ga
  o'tkazib, sifatni oshirishingiz mumkin.

## Litsenziya haqida eslatma

`assets/dragon_character.glb` — Sketchfab'dagi "Dragon Character 3d by Oscar
Creativo" modeli, **CC-BY-NC-4.0** (faqat notijorat maqsadlarda, muallifga
ishora qilingan holda) litsenziyasi ostida tarqatiladi. Batafsil ma'lumot
`assets/CREDITS.md` faylida. Agar o'yinni tijorat maqsadida chiqarmoqchi
bo'lsangiz, ushbu modelni boshqa (tijorat uchun ruxsat etilgan) model bilan
almashtirishingiz kerak bo'ladi.
