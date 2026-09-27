"""Samarqand ma'lumotidan Godot uchun GLB bo'laklar yasash.

Kirish:  samarqand/uylar.json, yollar.json, fon.json (tools/samarqand_tayyorla.py)
Chiqish: godot/shahar/bolak_<x>_<z>.glb + godot/shahar/indeks.json

Koordinatalar (glTF va Godot bir xil): X — sharq, Y — yuqori, Z — janub, metr.
Boshlang'ich nuqta — Registon. Har bir bo'lak o'z burchagiga nisbatan yoziladi
(uzoqda float aniqligi yo'qolmasin), joyi indeks.json da.

Material nomlari barqaror: Godot'dagi shahar.gd ularni nomi bo'yicha
real PBR materiallarga almashtiradi (godot/materiallar/).

    pip install numpy trimesh mapbox-earcut
    python3 tools/godot_eksport.py
"""
import json, math, os, sys, time
import numpy as np
import mapbox_earcut as earcut
import trimesh
from trimesh.visual.material import PBRMaterial
from trimesh.visual import TextureVisuals

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAL = os.path.join(REPO, "samarqand")
CHIQ = os.path.join(REPO, "godot", "shahar")

O_LON, O_LAT = 66.9757, 39.6547               # Registon
KX = 111320 * math.cos(math.radians(O_LAT))
KY = 110574
BOLAK = 400                                   # metr
QAVAT_M = 3.2

# ---------------- materiallar ----------------
# nom: (rang sRGB, g'adir-budurlik) — Godot'da real teksturalar bilan almashtiriladi
MAT = {
    "Devor_Suvoq":  ((0.86, 0.80, 0.69), 0.9),
    "Devor_Gisht":  ((0.72, 0.52, 0.38), 0.9),
    "Devor_Panel":  ((0.80, 0.78, 0.74), 0.85),
    "Devor_Dokon":  ((0.84, 0.82, 0.78), 0.7),
    "Devor_Jamoat": ((0.88, 0.84, 0.74), 0.85),
    "Devor_Garaj":  ((0.62, 0.60, 0.57), 0.95),
    "Obida_Gisht":  ((0.84, 0.70, 0.49), 0.9),
    "Tom_Tekis":    ((0.45, 0.44, 0.42), 0.95),
    "Tom_Shifer":   ((0.60, 0.61, 0.60), 0.8),
    "Tom_Obida":    ((0.18, 0.52, 0.76), 0.5),
    "Yol_Asfalt":   ((0.22, 0.23, 0.24), 0.9),
    "Yol_Mahalla":  ((0.30, 0.30, 0.30), 0.95),
    "Yol_Piyoda":   ((0.66, 0.60, 0.50), 0.9),
    "Yol_Tuproq":   ((0.55, 0.47, 0.36), 1.0),
    "Temir_Yol":    ((0.32, 0.28, 0.25), 0.95),
    "Yer_Maysa":    ((0.36, 0.50, 0.26), 1.0),
    "Yer_Dala":     ((0.50, 0.52, 0.30), 1.0),
    "Yer_Qabr":     ((0.52, 0.52, 0.42), 1.0),
    "Suv":          ((0.16, 0.34, 0.45), 0.1),
}
_mat_kesh = {}
def material(nom):
    if nom not in _mat_kesh:
        rang, rough = MAT[nom]
        _mat_kesh[nom] = PBRMaterial(name=nom, baseColorFactor=[*rang, 1.0],
                                     metallicFactor=0.0, roughnessFactor=rough)
    return _mat_kesh[nom]

YOL = {  # kenglik (m), balandlik (m), material
    "motorway": (16, .12, "Yol_Asfalt"), "trunk": (14, .12, "Yol_Asfalt"),
    "primary": (12, .11, "Yol_Asfalt"), "secondary": (10, .10, "Yol_Asfalt"),
    "tertiary": (8, .09, "Yol_Asfalt"), "unclassified": (6, .08, "Yol_Mahalla"),
    "residential": (6, .08, "Yol_Mahalla"), "living_street": (5, .08, "Yol_Mahalla"),
    "service": (4, .07, "Yol_Mahalla"), "unknown": (4, .07, "Yol_Mahalla"),
    "pedestrian": (6, .08, "Yol_Piyoda"), "footway": (2, .06, "Yol_Piyoda"),
    "steps": (2, .06, "Yol_Piyoda"), "path": (1.5, .06, "Yol_Tuproq"),
    "track": (3, .07, "Yol_Tuproq"), "cycleway": (2, .06, "Yol_Piyoda"),
    "bridleway": (2, .06, "Yol_Tuproq"), "rail": (3, .13, "Temir_Yol"),
    "tram": (2.4, .13, "Temir_Yol"),
}
HAYDASA = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
           "residential", "living_street", "service", "unknown"}
YER = {"park": "Yer_Maysa", "grass": "Yer_Maysa", "garden": "Yer_Maysa", "pitch": "Yer_Maysa",
       "forest": "Yer_Maysa", "stadium": "Yer_Maysa", "cemetery": "Yer_Qabr",
       "farmland": "Yer_Dala", "orchard": "Yer_Dala", "vineyard": "Yer_Dala"}


def devor_materiali(sinf, tarixiy, xesh):
    if tarixiy:
        return "Obida_Gisht", "Tom_Obida"
    if sinf in ("apartments", "dormitory", "hotel", "office"):
        return "Devor_Panel", "Tom_Tekis"
    if sinf in ("commercial", "retail", "supermarket", "service", "industrial", "warehouse"):
        return "Devor_Dokon", "Tom_Tekis"
    if sinf in ("school", "college", "university", "kindergarten", "hospital", "civic", "public",
                "education", "medical", "library", "train_station", "post_office", "fire_station"):
        return "Devor_Jamoat", "Tom_Tekis"
    if sinf in ("garage", "garages", "shed", "roof", "carport", "barn", "greenhouse", "outbuilding", "parking"):
        return "Devor_Garaj", "Tom_Shifer"
    return ("Devor_Gisht" if xesh % 3 == 0 else "Devor_Suvoq"), "Tom_Shifer"


def balandlik(sinf, h, f, maydon):
    if h:
        return h, 2
    if f:
        return f * QAVAT_M + 1, 1
    q = 1
    if sinf in ("apartments", "dormitory"): q = 5
    elif sinf in ("hotel", "hospital", "university", "office"): q = 4
    elif sinf in ("school", "college", "commercial", "civic", "public"): q = 3
    elif sinf in ("garage", "shed", "carport", "greenhouse", "roof", "barn"): q = 1
    elif maydon > 1200: q = 3
    elif maydon > 350: q = 2
    return q * QAVAT_M + (-0.6 if sinf in ("roof", "carport") else 0.8), 0


# ---------------- ma'lumotni o'qish ----------------
def ochish(kod, o, q):
    a = np.cumsum(np.asarray(kod, dtype=np.int64).reshape(-1, 2), axis=0)
    lon = o[0] + a[:, 0] / q
    lat = o[1] + a[:, 1] / q
    return np.stack([(lon - O_LON) * KX, (lat - O_LAT) * KY], axis=1)   # [x sharq, y shimol]


def maydon2(h):
    x, y = h[:, 0], h[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


# ---------------- geometriya yig'uvchi ----------------
class Yiguvchi:
    """Bir material uchun uchburchaklar. Koordinata: bo'lak burchagiga nisbatan."""
    def __init__(self):
        self.v, self.uv, self.f, self.n = [], [], [], 0

    def qosh(self, v, uv, f):
        self.v.append(v); self.uv.append(uv); self.f.append(f + self.n); self.n += len(v)

    def mesh(self, nom):
        v = np.concatenate(self.v).astype(np.float32)
        uv = np.concatenate(self.uv).astype(np.float32)
        f = np.concatenate(self.f).astype(np.int64)
        m = trimesh.Trimesh(vertices=v, faces=f, process=False,
                            visual=TextureVisuals(uv=uv, material=material(nom)))
        return m


def devorlar(y, h, H, bx, bz, y0=0.0):
    """Halqa (N,2) [x, shimol] -> devor to'rtburchaklari. UV: metrda (u — devor bo'ylab, v — balandlik)."""
    a = h
    b = np.roll(h, -1, axis=0)
    L = np.hypot(*(b - a).T)
    ok = L > 0.01
    a, b, L = a[ok], b[ok], L[ok]
    n = len(a)
    if not n:
        return
    u0 = np.concatenate([[0], np.cumsum(L)[:-1]])
    # 4 ta nuqta: a0, b0, b1, a1 ; Z = -shimol
    v = np.empty((n, 4, 3), np.float32)
    v[:, 0] = np.stack([a[:, 0] - bx, np.full(n, y0), -(a[:, 1]) - bz], 1)
    v[:, 1] = np.stack([b[:, 0] - bx, np.full(n, y0), -(b[:, 1]) - bz], 1)
    v[:, 2] = np.stack([b[:, 0] - bx, np.full(n, H), -(b[:, 1]) - bz], 1)
    v[:, 3] = np.stack([a[:, 0] - bx, np.full(n, H), -(a[:, 1]) - bz], 1)
    uv = np.empty((n, 4, 2), np.float32)
    uv[:, 0] = np.stack([u0, np.full(n, y0)], 1)
    uv[:, 1] = np.stack([u0 + L, np.full(n, y0)], 1)
    uv[:, 2] = np.stack([u0 + L, np.full(n, H)], 1)
    uv[:, 3] = np.stack([u0, np.full(n, H)], 1)
    k = np.arange(n)[:, None] * 4
    # glTF: old tomon — soat miliga teskari (tashqi halqa CCW bo'lsa normal tashqariga)
    f = np.concatenate([k + [0, 1, 2], k + [0, 2, 3]])
    y.qosh(v.reshape(-1, 3), uv.reshape(-1, 2), f)


def tekis(y, halqalar, Y, bx, bz):
    """Ko'pburchak (teshiklari bilan) -> yuqoriga qaragan tekislik. UV: metrda (x, shimol)."""
    hamma = np.concatenate(halqalar)
    oxir = np.cumsum([len(h) for h in halqalar]).astype(np.uint32)
    try:
        tri = earcut.triangulate_float64(hamma.astype(np.float64), oxir).reshape(-1, 3)
    except Exception:
        return
    if not len(tri):
        return
    p = hamma[tri]
    kr = (p[:, 1, 0] - p[:, 0, 0]) * (p[:, 2, 1] - p[:, 0, 1]) - (p[:, 1, 1] - p[:, 0, 1]) * (p[:, 2, 0] - p[:, 0, 0])
    tri[kr < 0] = tri[kr < 0][:, [0, 2, 1]]     # hammasi CCW (x, shimol) -> yuqoriga qaraydi
    v = np.stack([hamma[:, 0] - bx, np.full(len(hamma), Y), -hamma[:, 1] - bz], 1)
    y.qosh(v, hamma.copy(), tri.astype(np.int64))


def lenta(y, a, b, w, Y, bx, bz, uzaytir=None, u0=0.0):
    d = b - a
    L = float(np.hypot(*d))
    if L < 0.01:
        return 0.0
    d = d / L
    e = w * 0.45 if uzaytir is None else uzaytir
    a = a - d * e; b = b + d * e
    nrm = np.array([-d[1], d[0]]) * w / 2
    p = np.array([a - nrm, b - nrm, b + nrm, a + nrm])
    v = np.stack([p[:, 0] - bx, np.full(4, Y), -p[:, 1] - bz], 1)
    uv = np.array([[0, u0 - e], [0, u0 + L + e], [w, u0 + L + e], [w, u0 - e]], np.float32)
    y.qosh(v, uv, np.array([[0, 1, 2], [0, 2, 3]]))
    return L


# ---------------- asosiy ----------------
def main():
    t0 = time.time()
    U = json.load(open(os.path.join(MAL, "uylar.json"), encoding="utf-8"))
    Y = json.load(open(os.path.join(MAL, "yollar.json"), encoding="utf-8"))
    F = json.load(open(os.path.join(MAL, "fon.json"), encoding="utf-8"))
    o, q = U["o"], U["q"]
    bolaklar = {}

    def bolak(x, yy):
        k = (math.floor(x / BOLAK), math.floor(-yy / BOLAK))       # (X, Z) bo'yicha
        if k not in bolaklar:
            bolaklar[k] = {}
        return bolaklar[k], k

    def yig(bl, nom):
        if nom not in bl:
            bl[nom] = Yiguvchi()
        return bl[nom]

    aniqlik = [0, 0, 0]
    for i, (s, h, f, m, n, t, *hh) in enumerate(U["b"]):
        sinf = U["sinflar"][s]
        halqalar = [ochish(x, o, q) for x in hh]
        if maydon2(halqalar[0]) < 0:
            halqalar[0] = halqalar[0][::-1]
        for k in range(1, len(halqalar)):
            if maydon2(halqalar[k]) > 0:
                halqalar[k] = halqalar[k][::-1]
        ar = maydon2(halqalar[0])
        if ar < 4:
            continue
        H, a = balandlik(sinf, h / 10, f, ar)
        aniqlik[a] += 1
        c = halqalar[0].mean(axis=0)
        bl, (kx, kz) = bolak(c[0], c[1])
        bx, bz = kx * BOLAK, kz * BOLAK
        dm, tm = devor_materiali(sinf, t, (i * 2654435761) & 0xffffffff)
        for hl in halqalar:
            devorlar(yig(bl, dm), hl, H, bx, bz)
        tekis(yig(bl, tm), halqalar, H, bx, bz)

    boshlash = None
    for s, b, n, k in Y["y"]:
        sinf = Y["sinflar"][s]
        w, yy, mt = YOL.get(sinf, YOL["unknown"])
        p = ochish(k, o, q)
        u = 0.0
        for j in range(1, len(p)):
            mid = (p[j - 1] + p[j]) / 2
            bl, (kx, kz) = bolak(mid[0], mid[1])
            u += lenta(yig(bl, mt), p[j - 1], p[j], w, yy, kx * BOLAK, kz * BOLAK, u0=u)
        # boshlash nuqtasi: Registon ko'chasi (katta yo'l), Registonga eng yaqin
        if sinf in ("primary", "secondary", "tertiary") and n >= 0 and Y["nomlar"][n] == "Registon ko'chasi":
            for j in range(1, len(p)):
                m = (p[j - 1] + p[j]) / 2
                d = float(np.hypot(*m))
                if d > 60 and (boshlash is None or d < boshlash[0]):
                    yon = math.atan2(p[j][0] - p[j - 1][0], p[j][1] - p[j - 1][1])
                    boshlash = (d, float(m[0]), float(-m[1]), yon)

    for tur, s, *hh in F["yer"]:
        nom = YER.get(s) or YER.get(tur)
        if not nom:
            continue
        halqalar = [ochish(x, o, q) for x in hh]
        c = halqalar[0].mean(axis=0)
        bl, (kx, kz) = bolak(c[0], c[1])
        tekis(yig(bl, nom), halqalar, 0.02, kx * BOLAK, kz * BOLAK)
    for p_ in F["suvP"]:
        halqalar = [ochish(x, o, q) for x in p_]
        c = halqalar[0].mean(axis=0)
        bl, (kx, kz) = bolak(c[0], c[1])
        tekis(yig(bl, "Suv"), halqalar, 0.04, kx * BOLAK, kz * BOLAK)
    for s, k in F["suvCh"]:
        w = {"river": 14, "canal": 6, "stream": 3, "drain": 2, "ditch": 1.5}.get(s, 2)
        p = ochish(k, o, q)
        for j in range(1, len(p)):
            mid = (p[j - 1] + p[j]) / 2
            bl, (kx, kz) = bolak(mid[0], mid[1])
            lenta(yig(bl, "Suv"), p[j - 1], p[j], w, 0.04, kx * BOLAK, kz * BOLAK)

    # ---------------- yozish ----------------
    os.makedirs(CHIQ, exist_ok=True)
    for f in os.listdir(CHIQ):
        if f.startswith("bolak_") and f.endswith(".glb"):
            os.remove(os.path.join(CHIQ, f))
    indeks, jami = [], 0
    for (kx, kz), bl in sorted(bolaklar.items()):
        sahna = trimesh.Scene()
        for nom, yg in sorted(bl.items()):
            # uylar devorlari to'qnashuv oladi (-col: Godot StaticBody yasaydi)
            tugun = nom + ("-col" if nom.startswith(("Devor_", "Obida_")) else "")
            sahna.add_geometry(yg.mesh(nom), node_name=tugun, geom_name=nom)
        fayl = f"bolak_{kx}_{kz}.glb"
        data = sahna.export(file_type="glb")
        with open(os.path.join(CHIQ, fayl), "wb") as fh:
            fh.write(data)
        jami += len(data)
        indeks.append({"fayl": fayl, "x": kx * BOLAK, "z": kz * BOLAK})

    _, sx, sz, yon = boshlash
    json.dump({
        "versiya": 1, "bolak": BOLAK,
        "boshlangich": {"lon": O_LON, "lat": O_LAT, "izoh": "X sharq, Z janub, metr; (0,0) = Registon"},
        "boshlash": {"x": round(sx, 2), "z": round(sz, 2), "yon": round(yon, 4),
                     "izoh": "yon — shimoldan soat mili bo'yicha, radian"},
        "aniqlik": {"taxminiy": aniqlik[0], "qavatdan": aniqlik[1], "olchangan": aniqlik[2]},
        "manba": U.get("manba"),
        "bolaklar": indeks,
    }, open(os.path.join(CHIQ, "indeks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(indeks)} bo'lak, {jami / 1e6:.1f} MB, {time.time() - t0:.0f} s; aniqlik {aniqlik}")


if __name__ == "__main__":
    sys.exit(main())
