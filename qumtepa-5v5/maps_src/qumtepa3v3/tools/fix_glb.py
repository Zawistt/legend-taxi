"""Post-process the exported GLB so Godot recognises ORM textures.

Godot only builds an ORM material when occlusionTexture and metallicRoughnessTexture
resolve to the SAME texture index. trimesh writes the same image twice, so Godot drops
the metallic-roughness texture and leaves metallicFactor = 1.0 — every surface turns
into a mirror. This merges the duplicates and garbage-collects the orphaned image data.
"""
import json, struct, sys, hashlib


def read_glb(path):
    d = open(path, "rb").read()
    jlen = struct.unpack("<I", d[12:16])[0]
    j = json.loads(d[20:20 + jlen])
    bstart = 20 + jlen
    blen = struct.unpack("<I", d[bstart:bstart + 4])[0]
    return j, d[bstart + 8:bstart + 8 + blen]


def write_glb(path, j, bin_data):
    jb = json.dumps(j, separators=(",", ":")).encode()
    jb += b" " * ((4 - len(jb) % 4) % 4)
    bb = bin_data + b"\0" * ((4 - len(bin_data) % 4) % 4)
    total = 12 + 8 + len(jb) + 8 + len(bb)
    out = b"glTF" + struct.pack("<II", 2, total)
    out += struct.pack("<I", len(jb)) + b"JSON" + jb
    out += struct.pack("<I", len(bb)) + b"BIN\0" + bb
    open(path, "wb").write(out)


def fix(path):
    j, bin_data = read_glb(path)
    bv = j["bufferViews"]

    def img_hash(i):
        b = bv[j["images"][i]["bufferView"]]
        o = b.get("byteOffset", 0)
        return hashlib.md5(bin_data[o:o + b["byteLength"]]).hexdigest()

    # 1) point occlusion at the metallic-roughness texture when they share an image
    merged = 0
    for m in j.get("materials", []):
        occ = m.get("occlusionTexture")
        mr = m.get("pbrMetallicRoughness", {}).get("metallicRoughnessTexture")
        if not occ or not mr or occ["index"] == mr["index"]:
            continue
        if img_hash(j["textures"][occ["index"]]["source"]) == img_hash(j["textures"][mr["index"]]["source"]):
            occ["index"] = mr["index"]
            merged += 1

    # 2) drop textures/images nothing references any more
    used_tex = set()
    for m in j.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        for slot in (pbr.get("baseColorTexture"), pbr.get("metallicRoughnessTexture"),
                     m.get("normalTexture"), m.get("occlusionTexture"), m.get("emissiveTexture")):
            if slot:
                used_tex.add(slot["index"])
    tex_map = {}
    new_tex = []
    for i, t in enumerate(j.get("textures", [])):
        if i in used_tex:
            tex_map[i] = len(new_tex)
            new_tex.append(t)
    for m in j.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        for slot in (pbr.get("baseColorTexture"), pbr.get("metallicRoughnessTexture"),
                     m.get("normalTexture"), m.get("occlusionTexture"), m.get("emissiveTexture")):
            if slot:
                slot["index"] = tex_map[slot["index"]]
    j["textures"] = new_tex

    used_img = {t["source"] for t in new_tex}
    img_map = {}
    new_img = []
    for i, im in enumerate(j.get("images", [])):
        if i in used_img:
            img_map[i] = len(new_img)
            new_img.append(im)
    for t in new_tex:
        t["source"] = img_map[t["source"]]
    dropped_images = len(j["images"]) - len(new_img)
    j["images"] = new_img

    # 3) rebuild the binary chunk with only the buffer views still in use
    used_bv = {im["bufferView"] for im in new_img}
    for a in j.get("accessors", []):
        if "bufferView" in a:
            used_bv.add(a["bufferView"])
    for mesh in j.get("meshes", []):
        for p in mesh["primitives"]:
            pass  # primitives reference accessors, already covered

    out = bytearray()
    bv_map = {}
    new_bv = []
    for i, b in enumerate(bv):
        if i not in used_bv:
            continue
        o = b.get("byteOffset", 0)
        chunk = bin_data[o:o + b["byteLength"]]
        while len(out) % 4:
            out.append(0)
        nb = dict(b)
        nb["byteOffset"] = len(out)
        bv_map[i] = len(new_bv)
        new_bv.append(nb)
        out += chunk
    for im in new_img:
        im["bufferView"] = bv_map[im["bufferView"]]
    for a in j.get("accessors", []):
        if "bufferView" in a:
            a["bufferView"] = bv_map[a["bufferView"]]
    j["bufferViews"] = new_bv
    j["buffers"] = [{"byteLength": len(out)}]

    write_glb(path, j, bytes(out))
    return merged, dropped_images, len(out)


if __name__ == "__main__":
    print("ORM merged: %d materials, %d duplicate images dropped, bin %.1f MB" %
          fix(sys.argv[1] if len(sys.argv) > 1 else "desert_map.glb"))
