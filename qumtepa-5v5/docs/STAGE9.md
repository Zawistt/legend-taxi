# 9-bosqich: stilizatsiya qilingan low-poly ko'rinish

Xarita rejasi, devorlar, panalar, to'qnashuv, NavMesh, bomba nuqtalari va raund qoidalari **o'zgarmadi** — faqat ko'rinish.
Tekshiruvlar: Godot **116/116**, smoke **10/10**, audit **6/6**.

![Long → A](shots/03_long_a_site.png)

![B site — karvonsaroy](shots/09_b_site_karvonsaroy.png)

## Nima qilindi

| | Oldin (8-bosqich, realistik) | Endi (low-poly) |
|---|---|---|
| Materiallar | 1024 px PBR teksturalar (rang, normal, ORM, relyef), 40 material | 38 xil tekis rang (O'zbekiston palitrasi: qum-sariq devorlar, firuza gumbazlar, ko'k koshin, yashil chinor), teksturasiz |
| Soya | silliq normallar | tekis soya (flat shading): har uchburchak o'z normaliga ega, qirralar aniq ko'rinadi |
| Yuzalar | tekstura detallari | vertex rang: qo'shni yuzalar orasida ±4% farq va devor tagida yumshoq qorayish (soxta AO) |
| Daraxtlar | barg kartochkalari (shaffof tekstura) | kam qirrali "bulut" tojlar (ikosaedr, tasodifiy bo'rtiqlar) |
| Gumbaz, ustun, minora | 16 qirra | 8 qirra |
| Decal'lar | 558 ta (kir, yomg'ir izi, yoriq, dog') | yo'q |
| Osmon | bulutli panorama rasmi | gradient osmon (ProceduralSky) |
| Effektlar | SDFGI, SSR, SSIL, hajmli tuman | SSAO + SSIL, yengil tuman, glow; SDFGI/SSR/hajmli tuman o'chirilgan |
| Xarita GLB | 27 MB (+ 28 MB tekstura) | 10.9 MB, teksturasiz |

Qayta yaratish: `tools/make_all.sh` (standart `LOOK=lowpoly`). Eski realistik ko'rinish: `LOOK=pbr ./make_all.sh`.
Ranglar: `tools/build5.py` → `PAL` lug'ati.

## Personajlar

Foydalanuvchi so'rovi bilan eski qahramonlar, ularning animatsiyalari va qurol modellari (AKM, M416) ishlatilmaydi — yangilari beriladi.
Shu vaqtgacha o'yin ishlashi uchun `scripts/character_model.gd` kod bilan **vaqtinchalik low-poly manekin** yig'adi:
qutilardan tana, bosh (T — bosh o'rami va niqob, CT — dubulg'a), oyoqlar, qo'llar va qurol, jamoa rangida.
Oddiy harakatlar: qadam, o'tirish, nishonga qarab egilish, tepki, qayta o'qlash, o'lim.
1-shaxsda faqat qo'llar va qurol ko'rinadi, boshqalarga 3-shaxs tana — render qatlamlari avvalgidek.
Yangi modellar kelganda faqat shu fayl almashtiriladi.

![1-shaxs](shots/24_ozi_1shaxs.png)

![3-shaxs](shots/25_boshqalarga_3shaxs.png)
