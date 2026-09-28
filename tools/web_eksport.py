"""Godot loyihasidan brauzer versiyasini yasash (web/ papkaga).

Brauzer uchun shaharning markaziy qismi olinadi (Registon atrofida RADIUS metr),
aks holda birinchi yuklash juda og'ir bo'ladi. Natija: web/index.html va yonidagi
.wasm, .pck, .js fayllar — istalgan statik hostingda ochiladi (bitta oqimli
eksport, maxsus COOP/COEP sarlavhalari kerak emas).

    python3 tools/web_eksport.py [--radius 1600] [--godot /yo'l/Godot]

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radius", type=float, default=1600.0)
    ap.add_argument("--godot", default="/opt/godot/Godot_v4.7-stable_linux.x86_64")
    a = ap.parse_args()

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

    if os.path.exists(CHIQ):
        shutil.rmtree(CHIQ)
    os.makedirs(CHIQ)
    open(os.path.join(ish, "export_presets.cfg"), "w").write(PRESET.format(yol=os.path.join(CHIQ, "index.html")))
    subprocess.run([a.godot, "--headless", "--import", "--path", ish], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run([a.godot, "--headless", "--path", ish, "--export-release", "Web",
                        os.path.join(CHIQ, "index.html")], capture_output=True, text=True)
    print(r.stdout[-2000:], r.stderr[-2000:])
    shutil.rmtree(ish, ignore_errors=True)
    for f in sorted(os.listdir(CHIQ)):
        print(f"  {f}: {os.path.getsize(os.path.join(CHIQ, f)) / 1e6:.1f} MB")
    if not os.path.exists(os.path.join(CHIQ, "index.pck")):
        sys.exit("Eksport muvaffaqiyatsiz")


if __name__ == "__main__":
    main()
