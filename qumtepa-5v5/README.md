# Qumtepa 5v5

Qumtepa v2 (2v2, 50×50 m) asosida 5v5 uchun yangi xarita: **110×110 m**, 55×55 katak (har biri 2 m).
Godot 4.3, bomba rejimi (T hujum qiladi, CT himoya qiladi).

![1-bosqich chizmasi](docs/blueprint_stage1.png)

## Bosqichlar

| # | Bosqich | Holat |
|---|---|---|
| 0 | Konsepsiya: yo'llar sxemasi, vaqt maqsadlari | ✅ |
| 1 | 2D blokaut: yakuniy reja, panalar, ko'rish chiziqlari, smoke rejasi, callout'lar | ✅ ([hisobot](docs/STAGE1.md)) |
| 2 | Godot greybox: qutilardan 3D, collision, NavMesh, spawn, zonalar, raund, testlar | ⏳ |
| 3 | Balans sinovi: 5v5 botlar, hujum/qaytarib olish stsenariylari, tuzatishlar | — |
| 4 | Arxitektura: binolar, arkalar, derazalar, tomlar, hudud uslublari | — |
| 5 | Props va teksturalar, sirt turlari | — |
| 6 | Yorug'lik, osmon, atmosfera, tovush zonalari | — |
| 7 | Optimallashtirish (occlusion, LOD, MultiMesh), minimap, yakuniy testlar | — |

## Tuzilma

```
qumtepa-5v5/
├── tools/
│   ├── layout5.py    # xarita rejasi: kataklar, zonalar, panalar, spawn, bomba/sotib olish zonalari,
│   │                 # raund qoidalari, smoke rejasi, bot nuqtalari, vaqt maqsadlari
│   └── analyze5.py   # tahlil va avtomatik tekshiruvlar, chizmalarni yaratadi
└── docs/
    ├── STAGE1.md               # 1-bosqich hisoboti
    ├── blueprint_stage1.png    # reja, yo'llar, panalar, smoke nishonlari, bot nuqtalari
    ├── contact_stage1.png      # birinchi to'qnashuv xaritasi
    ├── analysis_stage1.json    # barcha o'lchovlar (2-bosqich generatori shuni o'qiydi)
    └── layout_stage1.txt       # kataklar (ASCII)
```

## Tahlilni ishga tushirish

```
pip install numpy scipy pillow
cd qumtepa-5v5/tools
python3 analyze5.py        # ~25 s; natija: "Tekshiruvlar: 59 / 59", xato bo'lsa chiqish kodi 1
```

`layout5.py` o'zgartirilgandan keyin har safar `analyze5.py` ni ishga tushiring. U vaqt, muvozanat
va ko'rish chiziqlari maqsadlardan chiqib ketganini darhol ko'rsatadi.
