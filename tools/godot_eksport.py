"""Samarqand ma'lumotidan Godot uchun GLB bo'laklar yasash (2-bosqich: relyef).

Kirish:  samarqand/uylar.json, yollar.json, fon.json (tools/samarqand_tayyorla.py)
         Copernicus DEM GLO-30 (avtomatik yuklanadi, .overture_kesh/ ga)
Chiqish: godot/shahar/bolak_<x>_<z>.glb, indeks.json, yollar.json

Koordinatalar (glTF va Godot bir xil): X — sharq, Y — yuqori, Z — janub, metr.
(0, 0, 0) — Registon yer sathi. Har bir bo'lak o'z burchagiga nisbatan yoziladi.

Nima qilinadi:
  * Relyef: Copernicus DSM -> binolar/daraxtlar olib tashlanadi (morfologik
    ochish) -> silliqlanadi -> 20 m to'r. Hamma narsa shu yuzaga o'tiradi.
  * Yo'llar: har bir bo'lakning kengligi atrofdagi real binolar orasiga
    sig'adigan qilib toraytiriladi, keyin barcha avtomobil yo'llari bitta
    yuzaga birlashtiriladi (chorrahalar toza, ustma-ust tushmaydi).
  * Binolar: yo'l yuzasiga kirib turgan qismi kesiladi; asosan yo'l ustida
    turgan (odatda sun'iy yo'ldosh xatosi) binolar olib tashlanadi.
  * Yo'l chegarasi: avtomobil yo'li yuzasining chetiga ko'rinmas devor
    (`Yol_Chegara-colonly`) — mashina faqat yo'lda yuradi.

    pip install numpy scipy shapely mapbox-earcut rasterio requests
    python3 tools/godot_eksport.py
"""
import json, math, os, sys, time, zlib
import numpy as np
import shapely
import shapely.ops
from shapely import box
from shapely.strtree import STRtree
import mapbox_earcut as earcut
from scipy import ndimage

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAL = os.path.join(REPO, "samarqand")
KESH = os.path.join(REPO, ".overture_kesh")
CHIQ = os.path.join(REPO, "godot", "shahar")

O_LON, O_LAT = 66.9757, 39.6547               # Registon
KX = 111320 * math.cos(math.radians(O_LAT))
KY = 110574
BOLAK = 400                                   # bo'lak, metr
TOR = 20                                      # relyef to'ri, metr
QAVAT_M = 3.2
QADAM = 8.0                                   # chiziqlarni relyefga yotqizish qadami, metr

# ---------------- materiallar ----------------
MAT = {
    "Devor_Suvoq":  ((0.86, 0.80, 0.69), 0.9), "Devor_Gisht":  ((0.72, 0.52, 0.38), 0.9),
    "Devor_Panel":  ((0.80, 0.78, 0.74), 0.85), "Devor_Dokon":  ((0.84, 0.82, 0.78), 0.7),
    "Devor_Jamoat": ((0.88, 0.84, 0.74), 0.85), "Devor_Garaj":  ((0.62, 0.60, 0.57), 0.95),
    "Obida_Gisht":  ((0.84, 0.70, 0.49), 0.9),
    "Tom_Tekis":    ((0.45, 0.44, 0.42), 0.95), "Tom_Shifer":   ((0.60, 0.61, 0.60), 0.8),
    "Tom_Obida":    ((0.72, 0.62, 0.46), 0.9),
    "Balkon":       ((0.80, 0.79, 0.76), 0.85),
    "Trotuar":      ((0.62, 0.60, 0.56), 0.9),
    "Yol_Chiziq":   ((0.92, 0.92, 0.88), 0.7),
    "Ariq":         ((0.45, 0.47, 0.46), 0.3),
    "Yol_Asfalt":   ((0.22, 0.23, 0.24), 0.9), "Yol_Mahalla":  ((0.30, 0.30, 0.30), 0.95),
    "Yol_Piyoda":   ((0.66, 0.60, 0.50), 0.9), "Yol_Tuproq":   ((0.55, 0.47, 0.36), 1.0),
    "Temir_Yol":    ((0.32, 0.28, 0.25), 0.95), "Yol_Chegara": ((1.0, 0.0, 1.0), 1.0),
    "Yer_Tuproq":   ((0.58, 0.52, 0.42), 1.0), "Yer_Maysa":    ((0.36, 0.50, 0.26), 1.0),
    "Yer_Dala":     ((0.50, 0.52, 0.30), 1.0), "Yer_Qabr":     ((0.52, 0.52, 0.42), 1.0),
    "Suv":          ((0.16, 0.34, 0.45), 0.1),
}
# avtomobil yo'llari: odatiy kenglik, eng kam kenglik (m), material
HAYDASA = {
    "motorway": (16, 10, "Yol_Asfalt"), "trunk": (14, 9, "Yol_Asfalt"),
    "primary": (12, 8, "Yol_Asfalt"), "secondary": (10, 7, "Yol_Asfalt"),
    "tertiary": (8, 6, "Yol_Asfalt"), "unclassified": (6, 4.5, "Yol_Mahalla"),
    "residential": (6, 4.5, "Yol_Mahalla"), "living_street": (5, 4, "Yol_Mahalla"),
    "service": (4, 3.2, "Yol_Mahalla"), "unknown": (4, 3.2, "Yol_Mahalla"),
}
# boshqa yo'llar: kenglik, yer ustidan balandlik, material
BOSHQA = {
    "pedestrian": (6, .07, "Yol_Piyoda"), "footway": (2, .06, "Yol_Piyoda"),
    "steps": (2, .06, "Yol_Piyoda"), "path": (1.5, .05, "Yol_Tuproq"),
    "track": (3, .05, "Yol_Tuproq"), "cycleway": (2, .06, "Yol_Piyoda"),
    "bridleway": (2, .05, "Yol_Tuproq"), "rail": (3, .09, "Temir_Yol"), "tram": (2.4, .09, "Temir_Yol"),
}
YOL_Y = 0.12                                   # avtomobil yo'li yuzasi yerdan balandligi
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
    """-> (balandlik m, aniqlik 0/1/2, qavatlar soni)"""
    if h:
        return h, 2, max(1, round((h - 0.8) / QAVAT_M))
    if f:
        return f * QAVAT_M + 1, 1, int(f)
    q = 1
    if sinf in ("apartments", "dormitory"): q = 5
    elif sinf in ("hotel", "hospital", "university", "office"): q = 4
    elif sinf in ("school", "college", "commercial", "civic", "public"): q = 3
    elif sinf in ("garage", "shed", "carport", "greenhouse", "roof", "barn"): q = 1
    elif maydon > 1200: q = 3
    elif maydon > 350: q = 2
    return q * QAVAT_M + (-0.6 if sinf in ("roof", "carport") else 0.8), 0, q


def ochish(kod, o, q):
    """Ixcham koordinatalar -> (N,2) [X sharq, Z janub] metr."""
    a = np.cumsum(np.asarray(kod, dtype=np.int64).reshape(-1, 2), axis=0)
    lon = o[0] + a[:, 0] / q
    lat = o[1] + a[:, 1] / q
    return np.stack([(lon - O_LON) * KX, -(lat - O_LAT) * KY], axis=1)


def vaqt(t0, matn):
    print(f"[{time.time() - t0:5.0f} s] {matn}", flush=True)


# ---------------- relyef ----------------
class Relyef:
    """20 m to'rdagi balandliklar. h() — Godot'dagi uchburchaklar bilan aynan bir xil
    (har bir katak a-c diagonali bo'yicha ikki uchburchak)."""

    def __init__(self, x0, z0, nx, nz):
        self.x0, self.z0, self.nx, self.nz = x0, z0, nx, nz
        X = x0 + TOR * np.arange(nx)
        Z = z0 + TOR * np.arange(nz)
        XX, ZZ = np.meshgrid(X, Z)
        self.H = self._dem(XX, ZZ)

    def _dem(self, XX, ZZ):
        import rasterio
        from rasterio.merge import merge
        os.makedirs(KESH, exist_ok=True)
        lon = O_LON + XX / KX
        lat = O_LAT - ZZ / KY
        yollar = []
        for la in range(int(math.floor(lat.min())), int(math.floor(lat.max())) + 1):
            for lo in range(int(math.floor(lon.min())), int(math.floor(lon.max())) + 1):
                n = f"Copernicus_DSM_COG_10_N{la:02d}_00_E{lo:03d}_00_DEM"
                p = os.path.join(KESH, n + ".tif")
                if not os.path.exists(p):
                    import requests
                    print("  DEM yuklanmoqda:", n)
                    r = requests.get(f"https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif", timeout=300)
                    r.raise_for_status()
                    open(p, "wb").write(r.content)
                yollar.append(p)
        ds = [rasterio.open(p) for p in yollar]
        m = 0.01
        a, tr = merge(ds, bounds=(lon.min() - m, lat.min() - m, lon.max() + m, lat.max() + m))
        a = a[0].astype(np.float64)
        yoq = a < 1                                       # ma'lumotsiz joylar
        if yoq.any():
            idx = ndimage.distance_transform_edt(yoq, return_distances=False, return_indices=True)
            a = a[tuple(idx)]
        # DSM -> taxminiy DTM: binolar va daraxtlarni olib tashlash, keyin silliqlash
        a = ndimage.grey_opening(a, size=(5, 5))
        a = ndimage.gaussian_filter(a, 1.6)
        inv = ~tr
        col, row = inv * (lon, lat)
        H = ndimage.map_coordinates(a, [row - 0.5, col - 0.5], order=1, mode="nearest")
        c0, r0 = inv * (O_LON, O_LAT)
        self.dengiz = float(ndimage.map_coordinates(a, [[r0 - 0.5], [c0 - 0.5]], order=1)[0])
        return H - self.dengiz

    def h(self, X, Z):
        X = np.asarray(X, np.float64); Z = np.asarray(Z, np.float64)
        fx = (X - self.x0) / TOR; fz = (Z - self.z0) / TOR
        i = np.clip(np.floor(fx).astype(int), 0, self.nx - 2)
        k = np.clip(np.floor(fz).astype(int), 0, self.nz - 2)
        u = np.clip(fx - i, 0, 1); v = np.clip(fz - k, 0, 1)
        H = self.H
        a = H[k, i]; b = H[k, i + 1]; c = H[k + 1, i + 1]; d = H[k + 1, i]
        # uchburchak (a, b, c) agar u >= v, aks holda (a, c, d)
        return np.where(u >= v, a + u * (b - a) + v * (c - b), a + v * (d - a) + u * (c - d))

    def bolak_mesh(self, kx, kz):
        """Bo'lak uchun to'r: (verts, uv, faces), bo'lak burchagiga nisbatan."""
        n = BOLAK // TOR
        i0 = (kx * BOLAK - self.x0) // TOR
        k0 = (kz * BOLAK - self.z0) // TOR
        if i0 < 0 or k0 < 0 or i0 + n >= self.nx or k0 + n >= self.nz:
            return None
        H = self.H[k0:k0 + n + 1, i0:i0 + n + 1]
        g = np.arange(n + 1) * TOR
        XX, ZZ = np.meshgrid(g, g)
        v = np.stack([XX.ravel(), H.ravel(), ZZ.ravel()], 1)
        uv = np.stack([XX.ravel() + kx * BOLAK, ZZ.ravel() + kz * BOLAK], 1)
        idx = np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
        a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel()
        c = idx[1:, 1:].ravel(); d = idx[1:, :-1].ravel()
        f = np.concatenate([np.stack([a, c, b], 1), np.stack([a, d, c], 1)])
        return v, uv, f

    def uchburchaklar(self, bx0, bz0, bx1, bz1):
        """Berilgan qutidagi relyef uchburchaklari (shapely) — yuzani relyefga yotqizish uchun."""
        i0 = max(int((bx0 - self.x0) // TOR), 0); i1 = min(int((bx1 - self.x0) // TOR) + 1, self.nx - 1)
        k0 = max(int((bz0 - self.z0) // TOR), 0); k1 = min(int((bz1 - self.z0) // TOR) + 1, self.nz - 1)
        I, K = np.meshgrid(np.arange(i0, i1), np.arange(k0, k1))
        X0 = self.x0 + I.ravel() * TOR; Z0 = self.z0 + K.ravel() * TOR
        X1 = X0 + TOR; Z1 = Z0 + TOR
        t1 = np.stack([np.stack([X0, Z0], 1), np.stack([X1, Z0], 1), np.stack([X1, Z1], 1)], 1)
        t2 = np.stack([np.stack([X0, Z0], 1), np.stack([X1, Z1], 1), np.stack([X0, Z1], 1)], 1)
        t = np.concatenate([t1, t2])
        return shapely.polygons(t)


# ---------------- geometriya yig'uvchi ----------------
class Yiguvchi:
    """Bir material uchun uchburchaklar. uv2 ixtiyoriy (bo'lmagan qismlar uchun 0)."""
    def __init__(self):
        self.v, self.uv, self.uv2, self.f, self.n = [], [], [], [], 0
        self.uv2_bor = False

    def qosh(self, v, uv, f, uv2=None):
        if len(f) == 0:
            return
        self.v.append(np.asarray(v, np.float32)); self.uv.append(np.asarray(uv, np.float32))
        if uv2 is not None:
            self.uv2_bor = True
            self.uv2.append(np.asarray(uv2, np.float32))
        else:
            self.uv2.append(np.zeros((len(v), 2), np.float32))
        self.f.append(np.asarray(f, np.int64) + self.n); self.n += len(v)


def glb_yoz(yol, tugunlar):
    """Minimal GLB yozuvchi. tugunlar: [(tugun_nomi, material_nomi, Yiguvchi)].
    POSITION, TEXCOORD_0, (TEXCOORD_1), indekslar (uint16 yoki uint32). Normal
    yozilmaydi — Godot o'zi hisoblaydi (devorlar tugunlari alohida — tekis soya)."""
    import struct
    bufer = bytearray()
    views, accs, meshes, nodes, mats, mat_ix = [], [], [], [], [], {}

    def qosh_view(data, target):
        while len(bufer) % 4:
            bufer.append(0)
        views.append({"buffer": 0, "byteOffset": len(bufer), "byteLength": len(data), "target": target})
        bufer.extend(data)
        return len(views) - 1

    def qosh_acc(arr, turi, comp, target, minmax=False):
        v = qosh_view(arr.tobytes(), target)
        a = {"bufferView": v, "componentType": comp, "count": int(arr.shape[0]), "type": turi}
        if minmax:
            a["min"] = arr.min(0).tolist(); a["max"] = arr.max(0).tolist()
        accs.append(a)
        return len(accs) - 1

    for tugun, mnom, yg in tugunlar:
        V = np.concatenate(yg.v).astype(np.float32)
        UV = np.concatenate(yg.uv).astype(np.float32)
        F = np.concatenate(yg.f)
        attr = {"POSITION": qosh_acc(V, "VEC3", 5126, 34962, True),
                "TEXCOORD_0": qosh_acc(UV, "VEC2", 5126, 34962)}
        if yg.uv2_bor:
            attr["TEXCOORD_1"] = qosh_acc(np.concatenate(yg.uv2).astype(np.float32), "VEC2", 5126, 34962)
        if len(V) < 65536:
            idx = qosh_acc(F.astype(np.uint16).reshape(-1), "SCALAR", 5123, 34963)
        else:
            idx = qosh_acc(F.astype(np.uint32).reshape(-1), "SCALAR", 5125, 34963)
        if mnom not in mat_ix:
            rang, rough = MAT[mnom]
            mat_ix[mnom] = len(mats)
            mats.append({"name": mnom, "pbrMetallicRoughness": {
                "baseColorFactor": [*rang, 1.0], "metallicFactor": 0.0, "roughnessFactor": rough}})
        meshes.append({"name": mnom, "primitives": [{"attributes": attr, "indices": idx, "material": mat_ix[mnom]}]})
        nodes.append({"name": tugun, "mesh": len(meshes) - 1})
    while len(bufer) % 4:
        bufer.append(0)
    js = {"asset": {"version": "2.0", "generator": "legend-taxi godot_eksport.py"},
          "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes, "meshes": meshes,
          "materials": mats, "accessors": accs, "bufferViews": views, "buffers": [{"byteLength": len(bufer)}]}
    jb = json.dumps(js, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    jami = 12 + 8 + len(jb) + 8 + len(bufer)
    with open(yol, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, jami))
        f.write(struct.pack("<II", len(jb), 0x4E4F534A)); f.write(jb)
        f.write(struct.pack("<II", len(bufer), 0x004E4942)); f.write(bufer)
    return jami


def yuqoriga(p, tri):
    """Uchburchaklar yuqoriga qarasin (Y+). p: (N,2) [X, Z]."""
    a, b, c = p[tri[:, 0]], p[tri[:, 1]], p[tri[:, 2]]
    u = b - a; w = c - a
    y = u[:, 1] * w[:, 0] - u[:, 0] * w[:, 1]
    tri = tri.copy()
    tri[y < 0] = tri[y < 0][:, [0, 2, 1]]
    return tri


def uchburchakla(poly):
    """shapely Polygon -> (nuqtalar (N,2), uchburchaklar)."""
    halqalar = [np.asarray(poly.exterior.coords)[:-1]] + [np.asarray(r.coords)[:-1] for r in poly.interiors]
    halqalar = [h for h in halqalar if len(h) >= 3]
    if not halqalar:
        return None, None
    p = np.concatenate(halqalar)
    oxir = np.cumsum([len(h) for h in halqalar]).astype(np.uint32)
    try:
        tri = earcut.triangulate_float64(p.astype(np.float64), oxir).reshape(-1, 3).astype(np.int64)
    except Exception:
        return None, None
    if not len(tri):
        return None, None
    return p, yuqoriga(p, tri)


def poligonlar(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [x for x in getattr(g, "geoms", []) if x.geom_type == "Polygon" and not x.is_empty]


def chiziqlar(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type in ("LineString", "LinearRing"):
        return [g]
    ro = []
    for x in getattr(g, "geoms", []):
        ro += chiziqlar(x)
    return ro


def yotqiz(yg, geom, yoff, R, bx, bz):
    """Yuzani relyefga yotqizish: relyef uchburchaklari bilan kesib, har bir bo'lagini
    uchburchaklaydi — natija relyefga aynan yopishadi (+ yoff)."""
    geom = shapely.make_valid(geom)
    if geom.is_empty:
        return
    x0, z0, x1, z1 = geom.bounds
    tri = R.uchburchaklar(x0, z0, x1, z1)
    shapely.prepare(geom)
    ich = shapely.contains_properly(geom, tri)
    kes = shapely.intersects(geom, tri) & ~ich
    bolaklar = list(tri[ich]) + list(shapely.intersection(tri[kes], geom))
    for b in bolaklar:
        for p in poligonlar(b):
            if p.area < 0.01:
                continue
            pts, t = uchburchakla(p)
            if pts is None:
                continue
            y = R.h(pts[:, 0], pts[:, 1]) + yoff
            v = np.stack([pts[:, 0] - bx, y, pts[:, 1] - bz], 1)
            yg.qosh(v, pts.copy(), t)


def zichla(p, qadam=QADAM):
    """Chiziqni `qadam` metrdan uzun bo'lmagan bo'laklarga bo'lish."""
    ro = [p[:1]]
    for j in range(1, len(p)):
        L = float(np.hypot(*(p[j] - p[j - 1])))
        n = max(1, int(math.ceil(L / qadam)))
        t = np.arange(1, n + 1)[:, None] / n
        ro.append(p[j - 1] + (p[j] - p[j - 1]) * t)
    return np.concatenate(ro)


def lenta(yg, p, w, yoff, R, bx, bz):
    """Chiziq bo'ylab relyefga yotgan lenta (piyoda yo'lak, temir yo'l, ariq)."""
    p = zichla(p)
    if len(p) < 2:
        return
    d = np.diff(p, axis=0)
    L = np.hypot(d[:, 0], d[:, 1])
    ok = L > 0.01
    if not ok.any():
        return
    p = np.concatenate([p[:1], p[1:][ok]]); d = d[ok]; L = L[ok]
    t = d / L[:, None]
    n = np.stack([-t[:, 1], t[:, 0]], 1)
    nv = np.concatenate([n[:1], n[:-1] + n[1:], n[-1:]])
    nv /= np.maximum(np.hypot(nv[:, 0], nv[:, 1]), 1e-6)[:, None]
    chap = p + nv * w / 2; ong = p - nv * w / 2
    pts = np.concatenate([chap, ong])
    m = len(p)
    y = R.h(pts[:, 0], pts[:, 1]) + yoff
    v = np.stack([pts[:, 0] - bx, y, pts[:, 1] - bz], 1)
    u = np.concatenate([[0], np.cumsum(L)])
    uv = np.concatenate([np.stack([u, np.zeros(m)], 1), np.stack([u, np.full(m, w)], 1)])
    i = np.arange(m - 1)
    tri = np.concatenate([np.stack([i, i + 1, m + i + 1], 1), np.stack([i, m + i + 1, m + i], 1)])
    yg.qosh(v, uv, yuqoriga(pts, tri))


def devor_halqa(yg, h, pastki, yuqori, bx, bz, ikki_tomon=False, v0=0.0):
    """Halqa yoki chiziq bo'ylab vertikal devor. h: (N,2) [X, Z]; pastki/yuqori: (N,) Y.
    Normal: (a->b) yo'nalishiga nisbatan (-dz, dx)."""
    a = h[:-1]; b = h[1:]
    ya0, yb0 = pastki[:-1], pastki[1:]
    ya1, yb1 = yuqori[:-1], yuqori[1:]
    L = np.hypot(*(b - a).T)
    ok = L > 0.01
    if not ok.any():
        return
    a, b, L = a[ok], b[ok], L[ok]
    ya0, yb0, ya1, yb1 = ya0[ok], yb0[ok], ya1[ok], yb1[ok]
    n = len(a)
    u0 = np.concatenate([[0], np.cumsum(L)[:-1]])
    v = np.empty((n, 4, 3))
    v[:, 0] = np.stack([a[:, 0] - bx, ya0, a[:, 1] - bz], 1)
    v[:, 1] = np.stack([b[:, 0] - bx, yb0, b[:, 1] - bz], 1)
    v[:, 2] = np.stack([b[:, 0] - bx, yb1, b[:, 1] - bz], 1)
    v[:, 3] = np.stack([a[:, 0] - bx, ya1, a[:, 1] - bz], 1)
    uv = np.empty((n, 4, 2))
    uv[:, 0] = np.stack([u0, ya0 - v0], 1) if np.ndim(v0) == 0 else np.stack([u0, ya0 - v0[:-1][ok]], 1)
    uv[:, 1] = np.stack([u0 + L, yb0 - (v0 if np.ndim(v0) == 0 else v0[1:][ok])], 1)
    uv[:, 2] = np.stack([u0 + L, yb1 - (v0 if np.ndim(v0) == 0 else v0[1:][ok])], 1)
    uv[:, 3] = np.stack([u0, ya1 - (v0 if np.ndim(v0) == 0 else v0[:-1][ok])], 1)
    k = np.arange(n)[:, None] * 4
    f = np.concatenate([k + [0, 1, 2], k + [0, 2, 3]])
    if ikki_tomon:
        f = np.concatenate([f, f[:, [0, 2, 1]]])
    yg.qosh(v.reshape(-1, 3), uv.reshape(-1, 2), f)


TOM_QIYALIK = math.radians(22)


def bino_devorlari(yg, h, asos, yuqori, ming, bx, bz, qavat, Hh, urug, eshik=-1):
    """Bino halqasi (yopiq, (N,2)) bo'ylab devorlar. UV: (u — devor bo'lagi bo'ylab 0..L,
    v — eng past yer sathidan balandlik). UV2 (shader uchun):
      x = ±(round(L*100) + urug)   (manfiy — shu bo'lakda eshik bor)
      y = qavat*1000 + round(Hh*10) (Hh — eng past yerdan bo'g'otgacha, m)"""
    a = h[:-1]; b = h[1:]
    L = np.hypot(*(b - a).T)
    ok = L > 0.05
    idx = np.nonzero(ok)[0]
    if not len(idx):
        return
    a, b, L = a[ok], b[ok], L[ok]
    n = len(a)
    v = np.empty((n, 4, 3))
    v[:, 0] = np.stack([a[:, 0] - bx, np.full(n, asos), a[:, 1] - bz], 1)
    v[:, 1] = np.stack([b[:, 0] - bx, np.full(n, asos), b[:, 1] - bz], 1)
    v[:, 2] = np.stack([b[:, 0] - bx, np.full(n, yuqori), b[:, 1] - bz], 1)
    v[:, 3] = np.stack([a[:, 0] - bx, np.full(n, yuqori), a[:, 1] - bz], 1)
    uv = np.empty((n, 4, 2))
    uv[:, 0] = np.stack([np.zeros(n), np.full(n, asos - ming)], 1)
    uv[:, 1] = np.stack([L, np.full(n, asos - ming)], 1)
    uv[:, 2] = np.stack([L, np.full(n, yuqori - ming)], 1)
    uv[:, 3] = np.stack([np.zeros(n), np.full(n, yuqori - ming)], 1)
    x = np.round(L * 100) + urug
    x = np.where(idx == eshik, -x, x) if eshik >= 0 else x
    y = np.full(n, qavat * 1000 + round(Hh * 10))
    uv2 = np.repeat(np.stack([x, y], 1)[:, None, :], 4, axis=1)
    k = np.arange(n)[:, None] * 4
    f = np.concatenate([k + [0, 1, 2], k + [0, 2, 3]])
    yg.qosh(v.reshape(-1, 3), uv.reshape(-1, 2), f, uv2.reshape(-1, 2))


def tom_yuzi(yg, pts3, uv, urug, bx, bz):
    """Qavariq ko'pburchak yuz (tom qiyaligi) — yelpig'ich, yuqoriga qaragan."""
    n = len(pts3)
    f = np.array([[0, i, i + 1] for i in range(1, n - 1)])
    p2 = pts3[:, [0, 2]]
    a, b, c = p2[f[:, 0]], p2[f[:, 1]], p2[f[:, 2]]
    y = (b - a)[:, 1] * (c - a)[:, 0] - (b - a)[:, 0] * (c - a)[:, 1]
    f[y < 0] = f[y < 0][:, [0, 2, 1]]
    v = pts3 - np.array([bx, 0, bz])
    yg.qosh(v, uv, f, np.tile([[urug, 0.0]], (n, 1)))


def qiya_tom(yg, p, tepa, urug, bx, bz):
    """To'rtburchakka yaqin uyga to'rt qiyalikli (shifer) tom. True — yasaldi."""
    r = p.minimum_rotated_rectangle
    if r.geom_type != "Polygon" or r.area <= 0 or p.area / r.area < 0.8:
        return False
    c = np.asarray(r.exterior.coords)[:4]
    if np.hypot(*(c[1] - c[0])) < np.hypot(*(c[2] - c[1])):
        c = np.roll(c, -1, axis=0)
    e0 = c[1] - c[0]; e1 = c[3] - c[0]
    L = np.hypot(*e0); W = np.hypot(*e1)
    if W < 3 or L < 3:
        return False
    ax = e0 / L; ay = e1 / W
    o = 0.4                                         # tom chiqib turishi
    A = c[0] - ax * o - ay * o; B = c[1] + ax * o - ay * o
    C = c[2] + ax * o + ay * o; D = c[3] - ax * o + ay * o
    W2 = W + 2 * o; L2 = L + 2 * o
    tg = math.tan(TOM_QIYALIK)
    ye = tepa - o * tg                               # bo'g'ot (chiqib turgan qirra)
    yr = tepa + (W / 2) * tg                         # tizma (ridge)
    if L2 - W2 < 0.2:                                # kvadrat — piramida
        R1 = R2 = (A + C) / 2
    else:
        R1 = A + ay * W2 / 2 + ax * W2 / 2
        R2 = B + ay * W2 / 2 - ax * W2 / 2
    P = lambda q, y: np.array([q[0], y, q[1]])
    kos = math.cos(TOM_QIYALIK)
    def uvlar(nuqtalar, ox, oy, bosh):
        return np.array([[np.dot(q - bosh, ox), np.dot(q - bosh, oy) / kos] for q in nuqtalar])
    # old va orqa trapetsiya, yon uchburchaklar
    yuzlar = [([A, B, R2, R1], [ye, ye, yr, yr], ax, ay, A),
              ([C, D, R1, R2], [ye, ye, yr, yr], -ax, -ay, C),
              ([D, A, R1], [ye, ye, yr], -ay, ax, D),
              ([B, C, R2], [ye, ye, yr], ay, -ax, B)]
    for q2, ys, ox, oy, bosh in yuzlar:
        if len(q2) == 4 and np.allclose(q2[2], q2[3]):
            q2, ys = q2[:3], ys[:3]
        pts3 = np.array([P(q, y) for q, y in zip(q2, ys)])
        tom_yuzi(yg, pts3, uvlar(q2, ox, oy, bosh), urug, bx, bz)
    return True


def balkonlar(ro, tashqi, ming, Hh, qavat, bx, bz, urug):
    """Ko'p qavatli panel uy balkonlari joylashuvi (devor.gdshader bilan bir xil:
    deraza oralig'i 3.0 m), 2-qavatdan, har ikkinchi ustunda. Godot'da MultiMesh
    bilan chiziladi. Yozuv: [x, y, z, burilish, tur] (tur 0 — ochiq, 1 — oynavand)."""
    oraliq = 3.0
    fh = max((Hh - 0.5) / qavat, 2.6)
    for j in range(len(tashqi) - 1):
        a, b = tashqi[j], tashqi[j + 1]
        L = float(np.hypot(*(b - a)))
        if L < 8:
            continue
        ox = (b - a) / L
        nx = np.array([-ox[1], ox[0]])                 # exterior_cw halqada tashqariga
        yaw = math.atan2(nx[0], nx[1])
        n = int((L - 0.6) // oraliq)
        chet = (L - n * oraliq) / 2
        for wi in range(0, n, 2):
            m = a + ox * (chet + (wi + 0.5) * oraliq)
            for fi in range(1, qavat):
                y = ming + 0.3 + fi * fh
                tur = 1 if ((int(urug * 1000) * 7 + wi * 13 + fi * 31) % 10) < 4 else 0
                ro.append([round(float(m[0] - bx), 2), round(y, 2), round(float(m[1] - bz), 2), round(yaw, 3), tur])


def devor_chiziq(yg, hh, pastki, yuqori, bx, bz):
    """Faqat to'qnashuv uchun ingichka devor: har nuqtada 2 ta tugun, ikki tomonlama."""
    n = len(hh)
    v = np.concatenate([np.stack([hh[:, 0] - bx, pastki, hh[:, 1] - bz], 1),
                        np.stack([hh[:, 0] - bx, yuqori, hh[:, 1] - bz], 1)])
    i = np.arange(n - 1)
    f = np.concatenate([np.stack([i, i + 1, n + i + 1], 1), np.stack([i, n + i + 1, n + i], 1)])
    f = np.concatenate([f, f[:, [0, 2, 1]]])
    yg.qosh(v, np.zeros((2 * n, 2)), f)


# ---------------- 4-bosqich: ko'cha ----------------
KATTA_SINF = {"motorway", "trunk", "primary", "secondary", "tertiary"}
HOVLI_UY = {"Devor_Suvoq", "Devor_Gisht", "Devor_Garaj"}


def bolak_boyicha_lenta(yig, kalit, R, p, w, yoff, mat):
    """Uzun chiziqni bo'laklarga (o'rta nuqta bo'yicha) bo'lib, relyefga yotgan lenta."""
    p = zichla(p, 40.0)
    for j in range(1, len(p)):
        k = kalit(*((p[j - 1] + p[j]) / 2))
        lenta(yig(k, mat), p[j - 1:j + 1], w, yoff, R, k[0] * BOLAK, k[1] * BOLAK)


def punktir(line, chiziq=3.0, oraliq=6.0):
    """LineString -> punktir bo'laklari (numpy massivlar)."""
    L = line.length
    ro, t = [], 1.0
    while t + chiziq < L:
        b = shapely.ops.substring(line, t, t + chiziq)
        if b.length > 0.5:
            ro.append(np.asarray(b.coords))
        t += chiziq + oraliq
    return ro


def kocha_jihozlari(R, haydash, kenglik, katta, mayda, yol_yuza, bpoly, olib, binolar, yig, kalit, obyektlar, t0):
    """Trotuar, bordyur, yo'l chiziqlari, zebra va hovli devorlari."""
    tirik = np.array([j not in olib for j in range(len(bpoly))])
    bino_birlash = shapely.union_all(bpoly[tirik])
    vaqt(t0, "binolar birlashtirildi")

    # --- trotuar: katta yo'llar bo'ylab 3 m, 15 sm balandroq ---
    trotuar = shapely.difference(katta.buffer(3.0, quad_segs=2), yol_yuza)
    trotuar = shapely.difference(trotuar, bino_birlash).simplify(0.2)
    tx0, tz0, tx1, tz1 = trotuar.bounds
    for kx in range(math.floor(tx0 / BOLAK), math.floor(tx1 / BOLAK) + 1):
        for kz in range(math.floor(tz0 / BOLAK), math.floor(tz1 / BOLAK) + 1):
            g = shapely.intersection(trotuar, box(kx * BOLAK, kz * BOLAK, (kx + 1) * BOLAK, (kz + 1) * BOLAK))
            if not g.is_empty:
                yotqiz(yig((kx, kz), "Trotuar"), g, YOL_Y + 0.15, R, kx * BOLAK, kz * BOLAK)
    vaqt(t0, "trotuarlar")

    # --- bordyur: katta yo'l va trotuar orasidagi chiziq (MultiMesh) ---
    bordyur = shapely.intersection(shapely.boundary(katta), trotuar.buffer(0.4))
    bordyur = shapely.difference(bordyur, mayda.buffer(0.8)).simplify(0.2)
    nb = 0
    for ch in chiziqlar(bordyur):
        p = zichla(np.asarray(ch.coords), 6.0)
        for j in range(1, len(p)):
            a, b = p[j - 1], p[j]
            L = float(np.hypot(*(b - a)))
            if L < 0.3:
                continue
            m = (a + b) / 2
            k = kalit(*m)
            y = float(min(R.h(a[0], a[1]), R.h(b[0], b[1]))) + YOL_Y - 0.12
            yaw = math.atan2(-(b[1] - a[1]), b[0] - a[0])
            obyektlar.setdefault(k, {}).setdefault("bordyur", []).append(
                [round(float(m[0] - k[0] * BOLAK), 2), round(y, 2), round(float(m[1] - k[1] * BOLAK), 2), round(yaw, 3), round(L + 0.05, 2)])
            nb += 1
    vaqt(t0, f"bordyurlar: {nb}")

    # --- chorrahalar: 3 va undan ko'p yo'l (servis yo'llarsiz) uchrashgan tugunlar ---
    from collections import defaultdict
    daraja = defaultdict(int)
    for sinf, nom, p in haydash:
        if sinf == "service":
            continue
        for j, q in enumerate(p):
            daraja[(round(q[0] * 2), round(q[1] * 2))] += 1 if j in (0, len(p) - 1) else 2
    chorraha = np.array([k for k, v in daraja.items() if v >= 3], dtype=float) / 2
    chorraha_set = {(round(x * 2), round(z * 2)) for x, z in chorraha}
    zona = shapely.union_all(shapely.buffer(shapely.points(chorraha), 9.0, quad_segs=3))
    shapely.prepare(zona)

    # --- yo'l chiziqlari va zebra (katta yo'llar) ---
    ofset = np.concatenate([[0], np.cumsum([len(p) - 1 for _, _, p in haydash])])
    nz = 0
    for r, (sinf, nom, p) in enumerate(haydash):
        if sinf not in KATTA_SINF or len(p) < 2:
            continue
        w = float(np.min(kenglik[ofset[r]:ofset[r + 1]]))
        line = shapely.LineString(p)
        if line.length < 15:
            continue
        chiziqlar_ro = []                               # (offset, punktirmi, eni)
        if w >= 9:
            chiziqlar_ro += [(0.15, False, 0.12), (-0.15, False, 0.12), (w / 2 - 0.45, False, 0.15), (-(w / 2 - 0.45), False, 0.15)]
            if w >= 11:
                chiziqlar_ro += [(w / 4, True, 0.13), (-w / 4, True, 0.13)]
        elif w >= 6:
            chiziqlar_ro += [(0.0, True, 0.13), (w / 2 - 0.4, False, 0.13), (-(w / 2 - 0.4), False, 0.13)]
        for off, pnk, eni in chiziqlar_ro:
            try:
                g = line.offset_curve(off, quad_segs=2) if off else line
            except Exception:
                continue
            g = shapely.difference(g, zona)
            for ch in chiziqlar(g):
                qismlar = punktir(ch) if pnk else [np.asarray(ch.coords)]
                for q in qismlar:
                    if len(q) >= 2:
                        bolak_boyicha_lenta(yig, kalit, R, q, eni, YOL_Y + 0.015, "Yol_Chiziq")
        # zebra: yo'ldagi har bir chorrahadan 11 m narida, ikki tomonga
        if w < 7:
            continue
        for j, q in enumerate(p):
            if (round(q[0] * 2), round(q[1] * 2)) not in chorraha_set:
                continue
            d0 = line.project(shapely.Point(q))
            for d in (d0 - 11.5, d0 + 11.5):
                if d < 2 or d > line.length - 2:
                    continue
                c = np.asarray(line.interpolate(d).coords)[0]
                c2 = np.asarray(line.interpolate(min(d + 1.0, line.length)).coords)[0]
                t = c2 - c
                t = t / max(np.hypot(*t), 1e-6)
                n = np.array([-t[1], t[0]])
                k = kalit(*c)
                for s_ in np.arange(-w / 2 + 0.8, w / 2 - 0.5, 1.0):
                    a = c + n * s_ - t * 1.5
                    b = c + n * s_ + t * 1.5
                    lenta(yig(k, "Yol_Chiziq"), np.array([a, b]), 0.5, YOL_Y + 0.016, R, k[0] * BOLAK, k[1] * BOLAK)
                nz += 1
    vaqt(t0, f"yo'l chiziqlari; zebralar: {nz}")

    # --- hovli devorlari: mahalla ko'chalari bo'ylab, yo'l chetidan 1 m narida ---
    uylar = [bpoly[j] for j in range(len(bpoly)) if tirik[j] and devor_materiali(binolar[j][1], binolar[j][4], 0)[0] in HOVLI_UY]
    uy_daraxt = STRtree(np.array(uylar, dtype=object))
    chiziq = shapely.boundary(yol_yuza.buffer(1.1, quad_segs=2))
    chiziq = shapely.intersection(chiziq, mayda.buffer(2.2))
    chiziq = shapely.difference(chiziq, katta.buffer(6.0))
    chiziq = shapely.difference(chiziq, bino_birlash).simplify(0.3)
    bolaklar_ = []
    for ch in chiziqlar(chiziq):
        p = zichla(np.asarray(ch.coords), 9.0)
        for j in range(1, len(p)):
            bolaklar_.append((p[j - 1], p[j]))
    if bolaklar_:
        ort = np.array([(a + b) / 2 for a, b in bolaklar_])
        _, mas = uy_daraxt.query_nearest(shapely.points(ort), return_distance=True, all_matches=False)
    nd = 0
    rng = np.random.default_rng(7)
    for (a, b), m_ in zip(bolaklar_, mas if bolaklar_ else []):
        L = float(np.hypot(*(b - a)))
        if L < 0.8 or m_ > 16:
            continue
        m = (a + b) / 2
        k = kalit(*m)
        ya, yb = float(R.h(a[0], a[1])), float(R.h(b[0], b[1]))
        y = min(ya, yb) - 0.3
        h = 2.5 + abs(ya - yb)
        yaw = math.atan2(-(b[1] - a[1]), b[0] - a[0])
        darvoza = 1 if (L >= 4.5 and rng.random() < 0.4) else 0
        obyektlar.setdefault(k, {}).setdefault("hovli_devor", []).append(
            [round(float(m[0] - k[0] * BOLAK), 2), round(y, 2), round(float(m[1] - k[1] * BOLAK), 2), round(yaw, 3),
             round(L + 0.2, 2), round(h, 2), round(float(rng.random()), 3), darvoza])
        nd += 1
    vaqt(t0, f"hovli devorlari: {nd}")

    tabiat(R, haydash, kenglik, ofset, katta, mayda, yol_yuza, bino_birlash, bpoly, tirik, uylar, zona,
           yig, kalit, obyektlar, t0)


# ---------------- 5-bosqich: tabiat ----------------
CHINOR, TERAK, MEVA, ARCHA = 0, 1, 2, 3


def tabiat(R, haydash, kenglik, ofset, katta, mayda, yol_yuza, bino_birlash, bpoly, tirik, uylar, zona,
           yig, kalit, obyektlar, t0):
    """Daraxtlar (MultiMesh) va ariqlar. Real OSM daraxtlari + Samarqand ko'chalari
    tuzilishiga mos joylashtirish: katta ko'chada trotuar bo'yida chinor/terak va ariq,
    mahalla ko'chasida devor oldida, hovlilar ichida mevali daraxtlar, bog'larda zich."""
    rng = np.random.default_rng(2026)
    bino_daraxt = STRtree(bpoly[tirik])
    nomzod = []                                     # (x, z, tur, olcham, yerdan_balandlik)

    def qator(line, qadam, tur_fn, olcham_fn, yoff, sakrash=0.0):
        L = line.length
        t = rng.uniform(0, qadam)
        while t < L:
            if rng.random() >= sakrash:
                q = np.asarray(line.interpolate(t).coords)[0]
                nomzod.append((q[0], q[1], tur_fn(), olcham_fn(), yoff))
            t += qadam * rng.uniform(0.85, 1.15)

    # 1) katta ko'chalar: trotuar chetida daraxt qatori, undan narida ariq
    ariq_chiziq = []
    for r, (sinf, nom, p) in enumerate(haydash):
        if sinf not in KATTA_SINF or len(p) < 2:
            continue
        w = float(np.min(kenglik[ofset[r]:ofset[r + 1]]))
        line = shapely.LineString(p)
        if line.length < 20:
            continue
        # ko'cha bo'yicha tur: ko'pchiligi chinor, ba'zi ko'chalar terak
        asosiy = TERAK if (zlib.crc32(str(nom or r).encode()) % 5 == 0) else CHINOR
        for tomon in (1, -1):
            try:
                g = shapely.difference(line.offset_curve(tomon * (w / 2 + 2.3), quad_segs=2), zona)
                a = shapely.difference(line.offset_curve(tomon * (w / 2 + 3.35), quad_segs=2), zona)
            except Exception:
                continue
            for ch in chiziqlar(g):
                qator(ch, 9.0, lambda: asosiy if rng.random() < 0.85 else MEVA,
                      lambda: rng.uniform(0.85, 1.2), YOL_Y + 0.15)
            ariq_chiziq += chiziqlar(a)
    # 2) mahalla ko'chalari: yo'l cheti va hovli devori orasida, siyrak
    for r, (sinf, nom, p) in enumerate(haydash):
        if sinf in KATTA_SINF or sinf == "service" or len(p) < 2:
            continue
        w = float(np.min(kenglik[ofset[r]:ofset[r + 1]]))
        line = shapely.LineString(p)
        for tomon in (1, -1):
            try:
                g = line.offset_curve(tomon * (w / 2 + 0.55), quad_segs=2)
            except Exception:
                continue
            for ch in chiziqlar(g):
                qator(ch, 13.0, lambda: rng.choice([MEVA, MEVA, TERAK, CHINOR]),
                      lambda: rng.uniform(0.75, 1.1), 0.0, sakrash=0.45)
    n_kocha = len(nomzod)
    # 3) hovlilar ichida mevali daraxtlar (uy atrofida 3..12 m)
    for u in uylar:
        k = rng.poisson(1.3)
        if not k:
            continue
        c = u.centroid
        r0 = math.sqrt(u.area) / 2
        for _ in range(k):
            a = rng.uniform(0, 2 * math.pi)
            d = r0 + rng.uniform(3, 10)
            nomzod.append((c.x + math.cos(a) * d, c.y + math.sin(a) * d,
                           MEVA if rng.random() < 0.85 else TERAK, rng.uniform(0.7, 1.15), 0.0))
    n_hovli = len(nomzod) - n_kocha
    # 4) bog'lar, parklar, qabristonlar (fon.json) va real OSM daraxtlari/o'rmonlari
    fon = json.load(open(os.path.join(MAL, "fon.json"), encoding="utf-8"))
    bog = []
    for tur, s_, *hh in fon["yer"]:
        if s_ in ("park", "garden", "forest", "orchard", "cemetery"):
            halqalar = [ochish(x, fon["o"], fon["q"]) for x in hh]
            bog.append((s_, shapely.make_valid(shapely.Polygon(halqalar[0], halqalar[1:]))))
    lp = os.path.join(KESH, "land.parquet")
    if os.path.exists(lp):
        import pyarrow.parquet as pq
        for r_ in pq.read_table(lp).to_pylist():
            g = shapely.from_wkb(r_["geometry"])
            g = shapely.transform(g, lambda xy: np.stack([(xy[:, 0] - O_LON) * KX, -(xy[:, 1] - O_LAT) * KY], 1))
            if r_["subtype"] == "tree" and g.geom_type == "Point":
                nomzod.append((g.x, g.y, CHINOR, rng.uniform(0.9, 1.3), 0.0))
            elif r_["subtype"] == "tree":
                for ch in chiziqlar(g):
                    qator(ch, 6.0, lambda: TERAK, lambda: rng.uniform(0.9, 1.2), 0.0)
            elif r_["subtype"] == "forest":
                bog.append(("forest", shapely.make_valid(g)))
    for s_, g in bog:
        zich = {"forest": 45.0, "orchard": 40.0, "park": 70.0, "garden": 60.0, "cemetery": 110.0}[s_]
        for pg in poligonlar(g):
            n = int(pg.area / zich)
            if n <= 0:
                continue
            x0, z0, x1, z1 = pg.bounds
            xs = rng.uniform(x0, x1, n * 3); zs = rng.uniform(z0, z1, n * 3)
            ich = shapely.contains_xy(pg, xs, zs)
            for x, z in list(zip(xs[ich], zs[ich]))[:n]:
                tur = ARCHA if (s_ == "cemetery" or rng.random() < 0.12) else (MEVA if s_ == "orchard" else
                                                                            rng.choice([CHINOR, CHINOR, TERAK, MEVA]))
                nomzod.append((x, z, tur, rng.uniform(0.8, 1.2), 0.0))
    vaqt(t0, f"daraxt nomzodlari: ko'cha {n_kocha}, hovli {n_hovli}, jami {len(nomzod)}")

    # filtr: yo'lda emas, binoga 1.5 m dan yaqin emas, bir-biriga 2.5 m dan yaqin emas
    X = np.array([n[0] for n in nomzod]); Z = np.array([n[1] for n in nomzod])
    yaxshi = ~shapely.contains_xy(yol_yuza, X, Z)
    _, mas = bino_daraxt.query_nearest(shapely.points(np.stack([X, Z], 1)), return_distance=True, all_matches=False)
    yaxshi &= mas > 1.5
    band = set()
    sanoq = [0, 0, 0, 0]
    for i in np.nonzero(yaxshi)[0]:
        x, z, tur, olcham, yoff = nomzod[i]
        kk = (round(x / 2.5), round(z / 2.5))
        if kk in band:
            continue
        band.add(kk)
        k = kalit(x, z)
        y = float(R.h(x, z)) + yoff
        obyektlar.setdefault(k, {}).setdefault("daraxt", []).append(
            [round(float(x - k[0] * BOLAK), 2), round(y, 2), round(float(z - k[1] * BOLAK), 2),
             round(float(rng.uniform(0, 6.283)), 2), int(tur), round(float(olcham), 2)])
        sanoq[int(tur)] += 1
    vaqt(t0, f"daraxtlar: chinor {sanoq[0]}, terak {sanoq[1]}, mevali {sanoq[2]}, archa {sanoq[3]}")

    # ariqlar: binolar va yo'llardan tozalangan chiziqlar
    ariq = shapely.union_all(ariq_chiziq) if ariq_chiziq else None
    if ariq is not None:
        ariq = shapely.difference(ariq, bino_birlash.buffer(0.6))
        ariq = shapely.difference(ariq, yol_yuza.buffer(0.5))
        n_a = 0
        for ch in chiziqlar(ariq):
            if ch.length < 3:
                continue
            bolak_boyicha_lenta(yig, kalit, R, np.asarray(ch.coords), 0.7, YOL_Y + 0.02, "Ariq")
            n_a += ch.length
        vaqt(t0, f"ariqlar: {n_a / 1000:.0f} km")


# ---------------- asosiy ----------------
def main():
    t0 = time.time()
    U = json.load(open(os.path.join(MAL, "uylar.json"), encoding="utf-8"))
    Y = json.load(open(os.path.join(MAL, "yollar.json"), encoding="utf-8"))
    F = json.load(open(os.path.join(MAL, "fon.json"), encoding="utf-8"))
    o, q = U["o"], U["q"]

    # ---- binolar ----
    binolar = []                                       # [poly, sinf, h, f, t, i]
    for i, (s, h, f, m, n, t, *hh) in enumerate(U["b"]):
        halqalar = [ochish(x, o, q) for x in hh]
        try:
            p = shapely.make_valid(shapely.Polygon(halqalar[0], halqalar[1:]))
        except Exception:
            continue
        p = max(poligonlar(p), key=lambda x: x.area, default=None)
        if p is None or p.area < 4:
            continue
        binolar.append([p, U["sinflar"][s], h / 10, f, t, i, m])
    vaqt(t0, f"binolar: {len(binolar)}")

    # ---- yo'llar ----
    haydash, boshqa = [], []                            # (sinf, nom, koord)
    for s, b, n, k in Y["y"]:
        sinf = Y["sinflar"][s]
        p = ochish(k, o, q)
        nom = Y["nomlar"][n] if n >= 0 else None
        if sinf in HAYDASA:
            haydash.append((sinf, nom, p))
        elif sinf in BOSHQA:
            boshqa.append((sinf, nom, p))

    bpoly = np.array([b[0] for b in binolar], dtype=object)
    daraxt = STRtree(bpoly)

    # 1) yo'l markaz chizig'ini kesib o'tgan binolar: yo'l eng kam kengligida kesiladi
    markaz = np.array([shapely.LineString(p) for _, _, p in haydash], dtype=object)
    kam_buf = shapely.buffer(markaz, [HAYDASA[s][1] / 2 + 0.3 for s, _, _ in haydash], quad_segs=3)
    li, bi = daraxt.query(markaz, predicate="intersects")
    olib = set()
    for bj in np.unique(bi):
        eski = bpoly[bj]
        yangi = eski.difference(shapely.union_all(kam_buf[li[bi == bj]]))
        yangi = max(poligonlar(yangi), key=lambda x: x.area, default=None)
        if yangi is None or yangi.area < 0.5 * eski.area or yangi.area < 6:
            olib.add(bj)
        else:
            bpoly[bj] = yangi
    vaqt(t0, f"yo'l ustidagi binolar: {len(np.unique(bi))} ta, {len(olib)} tasi olib tashlandi")
    daraxt = STRtree(bpoly)

    # 2) har bir yo'l bo'lagining kengligi — atrofdagi binolar orasiga sig'sin
    seg_a, seg_b, seg_w, seg_mat = [], [], [], []
    for sinf, nom, p in haydash:
        w0, wmin, mat = HAYDASA[sinf]
        for j in range(1, len(p)):
            seg_a.append(p[j - 1]); seg_b.append(p[j]); seg_w.append((w0, wmin)); seg_mat.append(mat)
    seg = shapely.linestrings(np.stack([np.array(seg_a), np.array(seg_b)], 1))
    w0 = np.array([w[0] for w in seg_w]); wmin = np.array([w[1] for w in seg_w])
    si, bj = daraxt.query(shapely.buffer(seg, w0 / 2 + 0.5, quad_segs=2), predicate="intersects")
    keep = np.array([b not in olib for b in bj], dtype=bool) if len(bj) else np.zeros(0, bool)
    si, bj = si[keep], bj[keep]
    masofa = shapely.distance(seg[si], bpoly[bj])
    dmin = np.full(len(seg), np.inf)
    np.minimum.at(dmin, si, masofa)
    kenglik = np.clip(2 * dmin - 0.6, wmin, w0)
    vaqt(t0, f"yo'l bo'laklari: {len(seg)}, torayganlari: {(kenglik < w0).sum()}")

    # 3) avtomobil yo'li yuzasi: katta yo'llar + mahalla yo'llari
    asfalt = np.array([m == "Yol_Asfalt" for m in seg_mat])
    buf = shapely.buffer(seg, kenglik / 2, quad_segs=4)
    katta = shapely.union_all(buf[asfalt]).simplify(0.15)
    mayda = shapely.union_all(buf[~asfalt]).simplify(0.15)
    yol_yuza = shapely.union_all([katta, mayda])
    mayda = shapely.difference(mayda, katta)
    shapely.prepare(yol_yuza)
    vaqt(t0, "yo'l yuzasi birlashtirildi")

    # 4) binolarni yo'l yuzasidan kesish
    kesildi = 0
    for j in daraxt.query(yol_yuza, predicate="intersects"):
        if j in olib:
            continue
        eski = bpoly[j]
        yangi = max(poligonlar(eski.difference(yol_yuza)), key=lambda x: x.area, default=None)
        if yangi is None or yangi.area < 0.45 * eski.area or yangi.area < 6:
            olib.add(j)
        else:
            bpoly[j] = yangi
            kesildi += 1
    vaqt(t0, f"binolar kesildi: {kesildi}, jami olib tashlandi: {len(olib)}")

    # ---- relyef ----
    X0, Z0, X1, Z1 = shapely.total_bounds(np.concatenate([bpoly, [yol_yuza]]))
    X0 = math.floor(X0 / BOLAK) * BOLAK - 2 * BOLAK; Z0 = math.floor(Z0 / BOLAK) * BOLAK - 2 * BOLAK
    X1 = math.ceil(X1 / BOLAK) * BOLAK + 2 * BOLAK; Z1 = math.ceil(Z1 / BOLAK) * BOLAK + 2 * BOLAK
    R = Relyef(X0, Z0, int((X1 - X0) / TOR) + 1, int((Z1 - Z0) / TOR) + 1)
    vaqt(t0, f"relyef: {R.nx}x{R.nz} tugun, {R.H.min():.1f}..{R.H.max():.1f} m (Registon = {R.dengiz:.0f} m)")

    # ---- bo'laklarga yig'ish ----
    bolaklar = {}
    obyektlar = {}                                     # (kx, kz) -> {tur: [[x, y, z, burilish, ...]]}

    def yig(k, nom):
        bl = bolaklar.setdefault(k, {})
        if nom not in bl:
            bl[nom] = Yiguvchi()
        return bl[nom]

    def kalit(x, z):
        return (math.floor(x / BOLAK), math.floor(z / BOLAK))


    # binolar — eshik yo'lga eng yaqin devorda
    yol_daraxt = STRtree(seg)
    aniqlik = [0, 0, 0]
    qiya_soni = 0
    PARAPET = ("Devor_Panel", "Devor_Dokon", "Devor_Jamoat", "Obida_Gisht")
    for j, (p0, sinf, h, f, t, i, m) in enumerate(binolar):
        if j in olib:
            continue
        p = shapely.orient_polygons(bpoly[j], exterior_cw=True)
        c = p.centroid
        k = kalit(c.x, c.y)
        bx, bz = k[0] * BOLAK, k[1] * BOLAK
        H, a_, qavat = balandlik(sinf, h, f, p.area)
        aniqlik[a_] += 1
        tashqi = np.asarray(p.exterior.coords)
        yer = R.h(tashqi[:, 0], tashqi[:, 1])
        ming = float(yer.min())
        asos = ming - 0.4
        tepa = float(yer.max()) + H
        Hh = tepa - ming
        xesh = (i * 2654435761) & 0xffffffff
        urug = (xesh % 997) / 1000.0
        dm, tm = devor_materiali(sinf, t, xesh)
        # eshik: o'rta nuqtasi avtomobil yo'liga eng yaqin devor bo'lagi
        orta = (tashqi[:-1] + tashqi[1:]) / 2
        uzun = np.hypot(*(tashqi[1:] - tashqi[:-1]).T)
        _, mas = yol_daraxt.query_nearest(shapely.points(orta), return_distance=True, all_matches=False)
        mas = np.where(uzun >= (3.2 if dm in ("Devor_Suvoq", "Devor_Gisht", "Devor_Garaj") else 1.4), mas, np.inf)
        eshik = int(np.argmin(mas)) if np.isfinite(mas).any() else -1
        qiya = (dm in ("Devor_Suvoq", "Devor_Gisht", "Devor_Garaj") and qavat <= 2 and 25 < p.area < 450
                and qiya_tom(yig(k, tm), p, tepa, urug, bx, bz))
        qiya_soni += qiya
        parapet = 0.7 if (not qiya and dm in PARAPET) else 0.0
        bino_devorlari(yig(k, dm), tashqi, asos, tepa + parapet, ming, bx, bz, qavat, Hh, urug, eshik)
        if dm == "Devor_Panel" and qavat >= 4:
            balkonlar(obyektlar.setdefault(k, {}).setdefault("balkon", []), tashqi, ming, Hh, qavat, bx, bz, urug)
        for r in p.interiors:
            bino_devorlari(yig(k, dm), np.asarray(r.coords), asos, tepa + parapet, ming, bx, bz, qavat, Hh, urug)
        if qiya:
            continue
        tom = p
        if parapet:
            ich = p.buffer(-0.3, join_style="mitre")
            ich = max(poligonlar(ich), key=lambda x: x.area, default=None)
            if ich is not None and ich.area > 0.3 * p.area:
                ich = shapely.orient_polygons(ich, exterior_cw=False)       # normal ichkariga
                ih = np.asarray(ich.exterior.coords)
                bino_devorlari(yig(k, dm), ih, tepa - 0.05, tepa + parapet, ming, bx, bz, 0, 0, urug)
                qopqoq = p.difference(ich)
                for qp in poligonlar(qopqoq):
                    pts, tri = uchburchakla(qp)
                    if pts is not None:
                        v = np.stack([pts[:, 0] - bx, np.full(len(pts), tepa + parapet), pts[:, 1] - bz], 1)
                        yig(k, dm).qosh(v, pts.copy(), tri, np.zeros((len(pts), 2)))
                tom = ich
        pts, tri = uchburchakla(tom)
        if pts is not None:
            v = np.stack([pts[:, 0] - bx, np.full(len(pts), tepa), pts[:, 1] - bz], 1)
            yig(k, tm).qosh(v, pts.copy(), tri, np.tile([[urug, 1.0]], (len(pts), 1)))
    vaqt(t0, f"qiya tomlar: {qiya_soni}")
    vaqt(t0, f"binolar yig'ildi; aniqlik {aniqlik}")

    kocha_jihozlari(R, haydash, kenglik, katta, mayda, yol_yuza, bpoly, olib, binolar,
                    yig, kalit, obyektlar, t0)

    # avtomobil yo'li yuzasi va chegara devorlari — bo'laklarga kesib
    chegara = shapely.simplify(shapely.boundary(yol_yuza), 0.4)
    bx0, bz0, bx1, bz1 = yol_yuza.bounds
    for kx in range(math.floor(bx0 / BOLAK), math.floor(bx1 / BOLAK) + 1):
        for kz in range(math.floor(bz0 / BOLAK), math.floor(bz1 / BOLAK) + 1):
            quti = box(kx * BOLAK, kz * BOLAK, (kx + 1) * BOLAK, (kz + 1) * BOLAK)
            k = (kx, kz); bx, bz = kx * BOLAK, kz * BOLAK
            for geom, nom in ((katta, "Yol_Asfalt"), (mayda, "Yol_Mahalla")):
                g = shapely.intersection(geom, quti)
                if not g.is_empty:
                    yotqiz(yig(k, nom), g, YOL_Y, R, bx, bz)
            for ch in chiziqlar(shapely.intersection(chegara, quti)):
                hh = zichla(np.asarray(ch.coords), 25.0)
                if len(hh) < 2:
                    continue
                y = R.h(hh[:, 0], hh[:, 1])
                devor_chiziq(yig(k, "Yol_Chegara"), hh, y - 0.5, y + 1.6, bx, bz)
    vaqt(t0, "yo'l yuzasi va chegaralar")

    # boshqa yo'llar (piyoda, temir yo'l ...) — lenta
    for sinf, nom, p in boshqa:
        w, yoff, mat = BOSHQA[sinf]
        # uzun chiziqni bo'laklarga bo'lamiz (o'rta nuqta bo'yicha)
        p = zichla(p, 40.0)
        for j in range(1, len(p)):
            mid = (p[j - 1] + p[j]) / 2
            k = kalit(*mid)
            lenta(yig(k, mat), p[j - 1:j + 1], w, yoff, R, k[0] * BOLAK, k[1] * BOLAK)

    # yer qatlamlari va suv
    guruh = {}
    for tur, s, *hh in F["yer"]:
        nom = YER.get(s) or YER.get(tur)
        if nom:
            halqalar = [ochish(x, o, q) for x in hh]
            guruh.setdefault(nom, []).append(shapely.make_valid(shapely.Polygon(halqalar[0], halqalar[1:])))
    for p_ in F["suvP"]:
        halqalar = [ochish(x, o, q) for x in p_]
        guruh.setdefault("Suv", []).append(shapely.make_valid(shapely.Polygon(halqalar[0], halqalar[1:])))
    ybalandlik = {"Yer_Maysa": 0.04, "Yer_Dala": 0.03, "Yer_Qabr": 0.04, "Suv": 0.05}
    for nom, gl in guruh.items():
        g = shapely.union_all(gl)
        gx0, gz0, gx1, gz1 = g.bounds
        for kx in range(math.floor(gx0 / BOLAK), math.floor(gx1 / BOLAK) + 1):
            for kz in range(math.floor(gz0 / BOLAK), math.floor(gz1 / BOLAK) + 1):
                gg = shapely.intersection(g, box(kx * BOLAK, kz * BOLAK, (kx + 1) * BOLAK, (kz + 1) * BOLAK))
                if not gg.is_empty:
                    yotqiz(yig((kx, kz), nom), gg, ybalandlik[nom], R, kx * BOLAK, kz * BOLAK)
    for s, k in F["suvCh"]:
        w = {"river": 14, "canal": 6, "stream": 3, "drain": 2, "ditch": 1.5}.get(s, 2)
        p = zichla(ochish(k, o, q), 40.0)
        for j in range(1, len(p)):
            kk = kalit(*((p[j - 1] + p[j]) / 2))
            lenta(yig(kk, "Suv"), p[j - 1:j + 1], w, 0.05, R, kk[0] * BOLAK, kk[1] * BOLAK)
    vaqt(t0, "yer qatlamlari")

    # relyef — mazmunli bo'laklar va ularning atrofidagi 2 qator
    mazmunli = set(bolaklar)
    for (kx, kz) in list(mazmunli):
        for a in range(-2, 3):
            for c in range(-2, 3):
                k = (kx + a, kz + c)
                if k not in bolaklar or "Yer_Tuproq" not in bolaklar[k]:
                    r = R.bolak_mesh(*k)
                    if r:
                        yig(k, "Yer_Tuproq").qosh(*r)
    vaqt(t0, "relyef bo'laklari")

    # ---- Godot uchun yo'l markaz chiziqlari (qayta tiklash, AI transport, minixarita) ----
    nomlar, nix = [], {}
    yollar_out = []
    for sinf, nom, p in haydash:
        pp = zichla(p, 15.0)
        y = R.h(pp[:, 0], pp[:, 1]) + YOL_Y
        ni = -1
        if nom:
            if nom not in nix:
                nix[nom] = len(nomlar); nomlar.append(nom)
            ni = nix[nom]
        yollar_out.append([sinf, ni, np.round(np.stack([pp[:, 0], y, pp[:, 1]], 1), 1).ravel().tolist()])

    # boshlash: Registon ko'chasi, Registonga eng yaqin nuqta
    boshlash = None
    for sinf, nom, p in haydash:
        if nom != "Registon ko'chasi":
            continue
        for j in range(1, len(p)):
            m = (p[j - 1] + p[j]) / 2
            d = float(np.hypot(*m))
            if d > 60 and (boshlash is None or d < boshlash[0]):
                yon = math.atan2(p[j][0] - p[j - 1][0], -(p[j][1] - p[j - 1][1]))
                boshlash = (d, float(m[0]), float(m[1]), yon)

    # ---- yozish ----
    os.makedirs(CHIQ, exist_ok=True)
    for f in os.listdir(CHIQ):
        if f.startswith("bolak_") and (f.endswith(".glb") or f.endswith(".obyektlar.json")):
            os.remove(os.path.join(CHIQ, f))
    indeks, jami = [], 0
    for (kx, kz), bl in sorted(bolaklar.items()):
        tugunlar = []
        for nom, yg in sorted(bl.items()):
            if not yg.n:
                continue
            if nom == "Yol_Chegara":
                tugun = nom + "-colonly"             # ko'rinmas, faqat to'qnashuv
            elif nom.startswith(("Devor_", "Obida_", "Yer_Tuproq", "Yol_Asfalt", "Yol_Mahalla")):
                tugun = nom + "-col"
            else:
                tugun = nom
            tugunlar.append((tugun, nom, yg))
        fayl = f"bolak_{kx}_{kz}.glb"
        jami += glb_yoz(os.path.join(CHIQ, fayl), tugunlar)
        yozuv = {"fayl": fayl, "x": kx * BOLAK, "z": kz * BOLAK}
        if (kx, kz) in obyektlar:
            of = f"bolak_{kx}_{kz}.obyektlar.json"
            json.dump(obyektlar[(kx, kz)], open(os.path.join(CHIQ, of), "w"), separators=(",", ":"))
            yozuv["obyektlar"] = of
        indeks.append(yozuv)

    _, sx, sz, yon = boshlash
    json.dump({
        "versiya": 2, "bolak": BOLAK,
        "boshlangich": {"lon": O_LON, "lat": O_LAT, "dengiz_satxi": round(R.dengiz, 1),
                        "izoh": "X sharq, Z janub, metr; (0,0,0) = Registon yer sathi"},
        "boshlash": {"x": round(sx, 2), "y": round(float(R.h(sx, sz)) + YOL_Y, 2), "z": round(sz, 2),
                     "yon": round(yon, 4), "izoh": "yon — shimoldan soat mili bo'yicha, radian"},
        "relyef": {"min": round(float(R.H.min()), 1), "max": round(float(R.H.max()), 1)},
        "aniqlik": {"taxminiy": aniqlik[0], "qavatdan": aniqlik[1], "olchangan": aniqlik[2]},
        "manba": U.get("manba") + ", Copernicus DEM GLO-30 (© DLR, © Airbus)",
        "bolaklar": indeks,
    }, open(os.path.join(CHIQ, "indeks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"izoh": "avtomobil yo'llari markaz chizig'i: [sinf, nom indeksi, [x,y,z, ...]]",
               "nomlar": nomlar, "yollar": yollar_out},
              open(os.path.join(CHIQ, "yollar.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    vaqt(t0, f"{len(indeks)} bo'lak, {jami / 1e6:.1f} MB")


if __name__ == "__main__":
    sys.exit(main())
