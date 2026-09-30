"""Godot loyihasidan brauzer (web/) yoki Windows (oyin/) versiyasini yasash.

Brauzer uchun shaharning markaziy qismi olinadi (Registon atrofida RADIUS metr),
aks holda birinchi yuklash juda og'ir bo'ladi. Natija: web/index.html va yonidagi
.wasm, .pck, .js fayllar — istalgan statik hostingda ochiladi (bitta oqimli
eksport, maxsus COOP/COEP sarlavhalari kerak emas).

    python3 tools/web_eksport.py [--radius 1600] [--godot /yo'l/Godot]
    python3 tools/web_eksport.py --platforma windows --radius 3000   # oyin/LegendTaxi_Windows.zip

Godot 4.7 va uning web eksport shabloni (web_nothreads_release.zip) o'rnatilgan
bo'lishi kerak: ~/.local/share/godot/export_templates/4.7.stable/
"""
import argparse, json, math, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOYIHA = os.path.join(REPO, "godot")
CHIQ = os.path.join(REPO, "web")

PRESET = """[preset.0]

name="Web"
platform="Web"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter="*.json"
exclude_filter=""
export_path="{yol}"
encryption_include_filters=""
encryption_exclude_filters=""
seed=0
encrypt_pck=false
encrypt_directory=false
script_export_mode=2

[preset.0.options]

custom_template/debug=""
custom_template/release=""
variant/extensions_support=false
variant/thread_support=false
vram_texture_compression/for_desktop=true
vram_texture_compression/for_mobile=false
html/export_icon=true
html/custom_html_shell=""
html/head_include="<style>body{{background:#0E1621}}</style>"
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
html/experimental_virtual_keyboard=false
progressive_web_app/enabled=false
"""


WIN_PRESET = """[preset.0]

name="Windows"
platform="Windows Desktop"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter="*.json"
exclude_filter=""
export_path="{yol}"
encryption_include_filters=""
encryption_exclude_filters=""
seed=0
encrypt_pck=false
encrypt_directory=false
script_export_mode=2

[preset.0.options]

custom_template/debug=""
custom_template/release=""
debug/export_console_wrapper=0
binary_format/embed_pck=true
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
binary_format/architecture="x86_64"
codesign/enable=false
application/modify_resources=false
application/product_name="Legend Taxi: Samarqand"
application/company_name="Legend Taxi"
application/export_angle=0
application/export_d3d12=0
"""

OQING = """LEGEND TAXI: SAMARQAND (sinov versiyasi)

Ishga tushirish: LegendTaxi.exe ni oching.
Talab: Windows 10/11, 64-bit, Vulkan qo'llaydigan videokarta, 8 GB RAM tavsiya.
Bu versiyada shaharning markazi bor (Registon atrofida {r:.1f} km).

Boshqaruv:
  W / Yuqori strelka   - gaz
  S / Pastki strelka   - tormoz, orqaga
  A D / Strelkalar     - rul
  Probel               - qo'l tormozi (drift)
  C                    - kamera: orqadan -> tepadan -> erkin uchish
  R                    - mashinani eng yaqin yo'lga qaytarish
  Erkin kamerada: sichqoncha + WASD, Shift - tez, E/Q - yuqoriga/pastga
  Alt+F4               - chiqish

Windows "noma'lum dastur" deb ogohlantirsa: "Batafsil" -> "Baribir ishga tushirish".

Xarita ma'lumotlari: (c) OpenStreetMap hissadorlari (ODbL), Overture Maps Foundation,
Microsoft Building Footprints, Copernicus DEM GLO-30 ((c) DLR, (c) Airbus).
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radius", type=float, default=1600.0)
    ap.add_argument("--godot", default="/opt/godot/Godot_v4.7-stable_linux.x86_64")
    ap.add_argument("--platforma", choices=["web", "windows"], default="web")
    a = ap.parse_args()
    win = a.platforma == "windows"

    ish = tempfile.mkdtemp(prefix="samarqand_web_")
    print("Ish papkasi:", ish)
    shutil.copytree(LOYIHA, ish, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".godot", "bolak_*"))
    ind = json.load(open(os.path.join(LOYIHA, "shahar", "indeks.json"), encoding="utf-8"))
    b = ind["boshlash"]
    qoldi = []
    for bl in ind["bolaklar"]:
        cx, cz = bl["x"] + ind["bolak"] / 2, bl["z"] + ind["bolak"] / 2
        if math.hypot(cx - b["x"], cz - b["z"]) <= a.radius:
            qoldi.append(bl)
            for f in [bl["fayl"], bl["fayl"] + ".import", bl.get("obyektlar")]:
                if f and os.path.exists(os.path.join(LOYIHA, "shahar", f)):
                    shutil.copy2(os.path.join(LOYIHA, "shahar", f), os.path.join(ish, "shahar", f))
    ind["bolaklar"] = qoldi
    ind["web_radius"] = a.radius
    json.dump(ind, open(os.path.join(ish, "shahar", "indeks.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"Bo'laklar: {len(qoldi)} ta (radius {a.radius:.0f} m)")

    chiq = os.path.join(REPO, "oyin") if win else CHIQ
    if os.path.exists(chiq):
        shutil.rmtree(chiq)
    os.makedirs(chiq)
    if win:
        vaqtincha = os.path.join(ish, "_chiqish")
        os.makedirs(vaqtincha)
        maqsad = os.path.join(vaqtincha, "LegendTaxi.exe")
        open(os.path.join(ish, "export_presets.cfg"), "w").write(WIN_PRESET.format(yol=maqsad))
    else:
        maqsad = os.path.join(chiq, "index.html")
        open(os.path.join(ish, "export_presets.cfg"), "w").write(PRESET.format(yol=maqsad))
    subprocess.run([a.godot, "--headless", "--import", "--path", ish], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run([a.godot, "--headless", "--path", ish, "--export-release", "Windows" if win else "Web",
                        maqsad], capture_output=True, text=True)
    print(r.stdout[-1500:], r.stderr[-1500:])
    if win:
        import zipfile
        if not os.path.exists(maqsad):
            sys.exit("Eksport muvaffaqiyatsiz")
        zp = os.path.join(chiq, "LegendTaxi_Windows.zip")
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.write(maqsad, "LegendTaxi/LegendTaxi.exe")
            z.writestr("LegendTaxi/O'QING.txt", OQING.format(r=a.radius / 1000))
    shutil.rmtree(ish, ignore_errors=True)
    for f in sorted(os.listdir(chiq)):
        print(f"  {f}: {os.path.getsize(os.path.join(chiq, f)) / 1e6:.1f} MB")
    if not win and not os.path.exists(os.path.join(chiq, "index.pck")):
        sys.exit("Eksport muvaffaqiyatsiz")


if __name__ == "__main__":
    main()
