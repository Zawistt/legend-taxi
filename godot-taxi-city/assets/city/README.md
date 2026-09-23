# Shahar modelini shu yerga qo'ying

1. Shahar modelini (`.glb` tavsiya etiladi, past-poli/1K teksturali versiya) shu papkaga (`assets/city/`) tashlang.
2. Godot muharririda `scenes/Main.tscn` ni oching.
3. Faylni loyiha panelidan tortib olib, sahnadagi `City` tugunining ichiga tashlang (`City` bo'sh Node3D, faqat shahar modelini joylashtirish uchun).
4. Model juda katta/kichik bo'lsa `City` yoki modelning `Scale` qiymatini sozlang, `Taxi` (0,1,0) koordinatasida boshlanadi — shaharning yer sathi shu balandlikda bo'lishi kerak.
5. Taksi haqiqiy bino/yo'llarga urilishi uchun: model tugunini tanlang -> sichqoncha o'ng tugmasi -> **Mesh -> Create Trimesh Static Body**. Shundan keyin `Ground` placeholder tekisligini o'chirib tashlashingiz mumkin.

Ishlash tezligi bo'yicha eslatma: import qilingandan so'ng har bir teksturani `.import` sozlamalarida **VRAM Compressed** qilib, `Limit` (masalan 1024–2048px) qo'ying — bu build hajmi va yuklash vaqtini sezilarli kamaytiradi.
