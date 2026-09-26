"""O'ynash uchun yengil nusxa (bitta zip, ≤ 30 MB): python3 pack_play.py <chiqish.zip>

Asl loyiha o'zgarmaydi. Nusxada:
  - low-poly ko'rinishda ishlatilmaydigan PBR teksturalar, eski personaj modellari va Godot keshlari yo'q;
  - textures/: rang xaritalari 1024 px JPEG 72%, normal/ORM/relyef 512 px;
  - GLB ichidagi rasmlar: shaffofligi yo'q PNG -> JPEG 85%, personaj teksturalari ≤ 1024 px.
"""
import io, json, os, shutil, struct, sys, tempfile, zipfile
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "godot")
SKIP_DIRS = {".godot", "characters", "textures"}   # low-poly: teksturalar va eski personajlar ishlatilmaydi
SKIP_FILES = {"characters/ct_soldier.glb", "characters/ct_soldier.glb.import", "characters/ct_arms.glb", "characters/ct_arms.glb.import"}


def skip(rel):
    if rel.split("/")[0] in SKIP_DIRS or rel in SKIP_FILES:
        return True
    if rel.startswith(("map/", "characters/")) and rel.endswith((".png", ".jpg", ".png.import", ".jpg.import")):
        return True          # Godot GLB dan ajratib oladigan rasmlar — import paytida qayta yaratiladi
    return False


def recompress_glb(data, max_size, png_to_jpg=True):
    L = struct.unpack("<I", data[12:16])[0]
    j = json.loads(data[20:20 + L])
    binstart = 20 + L + 8
    B = data[binstart:]
    views = [bytes(B[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]]) for v in j["bufferViews"]]
    for im in j.get("images", []):
        if "bufferView" not in im:
            continue
        raw = views[im["bufferView"]]
        img = Image.open(io.BytesIO(raw))
        has_alpha = img.mode in ("RGBA", "LA") and img.getextrema()[-1][0] < 250
        if max(img.size) > max_size:
            img = img.resize((max_size, max_size) if img.size[0] == img.size[1] else
                             tuple(int(x * max_size / max(img.size)) for x in img.size), Image.LANCZOS)
        out = io.BytesIO()
        if has_alpha or (not png_to_jpg and im.get("mimeType") == "image/png"):
            img.save(out, "PNG", optimize=True)
            im["mimeType"] = "image/png"
        else:
            img.convert("RGB").save(out, "JPEG", quality=85)
            im["mimeType"] = "image/jpeg"
        if len(out.getvalue()) < len(raw):
            views[im["bufferView"]] = out.getvalue()
    # buferni qayta yig'ish (4 baytga tekislab)
    nb = bytearray()
    for i, v in enumerate(views):
        while len(nb) % 4:
            nb.append(0)
        j["bufferViews"][i]["byteOffset"] = len(nb)
        j["bufferViews"][i]["byteLength"] = len(v)
        nb += v
    while len(nb) % 4:
        nb.append(0)
    j["buffers"][0]["byteLength"] = len(nb)
    js = json.dumps(j, separators=(",", ":")).encode()
    while len(js) % 4:
        js += b" "
    total = 12 + 8 + len(js) + 8 + len(nb)
    return (b"glTF" + struct.pack("<II", 2, total) + struct.pack("<I", len(js)) + b"JSON" + js +
            struct.pack("<I", len(nb)) + b"BIN\x00" + bytes(nb))


def main(out_zip):
    tmp = tempfile.mkdtemp()
    root = os.path.join(tmp, "qumtepa-5v5", "godot")
    for d, _, files in os.walk(SRC):
        for f in files:
            full = os.path.join(d, f)
            rel = os.path.relpath(full, SRC).replace(os.sep, "/")
            if skip(rel):
                continue
            dst = os.path.join(root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if rel.startswith("textures/") and rel.endswith(".jpg"):
                img = Image.open(full)
                if not rel.endswith("_albedo.jpg"):
                    img = img.resize((512, 512), Image.LANCZOS)
                img.convert("RGB").save(dst, "JPEG", quality=72 if rel.endswith("_albedo.jpg") else 80)
            elif rel.endswith(".glb"):
                big = rel.startswith("characters/")
                open(dst, "wb").write(recompress_glb(open(full, "rb").read(), 1024 if big else 512))
            else:
                shutil.copy(full, dst)
    for f in ("README.md",):
        shutil.copy(os.path.join(HERE, "..", f), os.path.join(tmp, "qumtepa-5v5", f))
    for f in ("YAKUNIY_HISOBOT.md", "STAGE8.md", "STAGE9.md", "STAGE10.md"):
        os.makedirs(os.path.join(tmp, "qumtepa-5v5", "docs"), exist_ok=True)
        shutil.copy(os.path.join(HERE, "..", "docs", f), os.path.join(tmp, "qumtepa-5v5", "docs", f))
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for d, _, files in os.walk(os.path.join(tmp, "qumtepa-5v5")):
            for f in files:
                full = os.path.join(d, f)
                z.write(full, os.path.relpath(full, tmp))
    shutil.rmtree(tmp)
    print(out_zip, f"{os.path.getsize(out_zip) / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "qumtepa_5v5.zip")
