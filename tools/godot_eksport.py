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

    pip install numpy scipy shapely trimesh mapbox-earcut rasterio requests
    python3 tools/godot_eksport.py
"""
import json, math, os, sys, time
import numpy as np
import shapely
from shapely import box
from shapely.strtree import STRtree
import mapbox_earcut as earcut
import trimesh
from trimesh.visual.material import PBRMaterial
from trimesh.visual import TextureVisuals
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
    "Tom_Obida":    ((0.18, 0.52, 0.76), 0.5),
    "Yol_Asfalt":   ((0.22, 0.23, 0.24), 0.9), "Yol_Mahalla":  ((0.30, 0.30, 0.30), 0.95),
    "Yol_Piyoda":   ((0.66, 0.60, 0.50), 0.9), "Yol_Tuproq":   ((0.55, 0.47, 0.36), 1.0),
    "Temir_Yol":    ((0.32, 0.28, 0.25), 0.95), "Yol_Chegara": ((1.0, 0.0, 1.0), 1.0),
    "Yer_Tuproq":   ((0.58, 0.52, 0.42), 1.0), "Yer_Maysa":    ((0.36, 0.50, 0.26), 1.0),
    "Yer_Dala":     ((0.50, 0.52, 0.30), 1.0), "Yer_Qabr":     ((0.52, 0.52, 0.42), 1.0),
    "Suv":          ((0.16, 0.34, 0.45), 0.1),
}
_mat_kesh = {}
def material(nom):
    if nom not in _mat_kesh:
        rang, rough = MAT[nom]
        _mat_kesh[nom] = PBRMaterial(name=nom, baseColorFactor=[*rang, 1.0],
                                     metallicFactor=0.0, roughnessFactor=rough)
    return _mat_kesh[nom]

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
    def __init__(self):
        self.v, self.uv, self.f, self.n = [], [], [], 0

    def qosh(self, v, uv, f):
        if len(f) == 0:
            return
        self.v.append(np.asarray(v, np.float32)); self.uv.append(np.asarray(uv, np.float32))
        self.f.append(np.asarray(f, np.int64) + self.n); self.n += len(v)

    def mesh(self, nom):
        return trimesh.Trimesh(vertices=np.concatenate(self.v), faces=np.concatenate(self.f), process=False,
                               visual=TextureVisuals(uv=np.concatenate(self.uv), material=material(nom)))


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


def devor_chiziq(yg, hh, pastki, yuqori, bx, bz):
    """Faqat to'qnashuv uchun ingichka devor: har nuqtada 2 ta tugun, ikki tomonlama."""
    n = len(hh)
    v = np.concatenate([np.stack([hh[:, 0] - bx, pastki, hh[:, 1] - bz], 1),
                        np.stack([hh[:, 0] - bx, yuqori, hh[:, 1] - bz], 1)])
    i = np.arange(n - 1)
    f = np.concatenate([np.stack([i, i + 1, n + i + 1], 1), np.stack([i, n + i + 1, n + i], 1)])
    f = np.concatenate([f, f[:, [0, 2, 1]]])
    yg.qosh(v, np.zeros((2 * n, 2)), f)


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

    def yig(k, nom):
        bl = bolaklar.setdefault(k, {})
        if nom not in bl:
            bl[nom] = Yiguvchi()
        return bl[nom]

    def kalit(x, z):
        return (math.floor(x / BOLAK), math.floor(z / BOLAK))


    # binolar
    aniqlik = [0, 0, 0]
    for j, (p0, sinf, h, f, t, i, m) in enumerate(binolar):
        if j in olib:
            continue
        p = shapely.orient_polygons(bpoly[j], exterior_cw=True)
        c = p.centroid
        k = kalit(c.x, c.y)
        bx, bz = k[0] * BOLAK, k[1] * BOLAK
        H, a = balandlik(sinf, h, f, p.area)
        aniqlik[a] += 1
        tashqi = np.asarray(p.exterior.coords)
        yer = R.h(tashqi[:, 0], tashqi[:, 1])
        asos = float(yer.min()) - 0.4
        tepa = float(yer.max()) + H
        dm, tm = devor_materiali(sinf, t, (i * 2654435761) & 0xffffffff)
        for r in [p.exterior, *p.interiors]:
            hh = np.asarray(r.coords)
            n = len(hh)
            devor_halqa(yig(k, dm), hh, np.full(n, asos), np.full(n, tepa), bx, bz, v0=asos + 0.4)
        pts, tri = uchburchakla(p)
        if pts is not None:
            v = np.stack([pts[:, 0] - bx, np.full(len(pts), tepa), pts[:, 1] - bz], 1)
            yig(k, tm).qosh(v, pts.copy(), tri)
    vaqt(t0, f"binolar yig'ildi; aniqlik {aniqlik}")

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
        if f.startswith("bolak_") and f.endswith(".glb"):
            os.remove(os.path.join(CHIQ, f))
    indeks, jami = [], 0
    for (kx, kz), bl in sorted(bolaklar.items()):
        sahna = trimesh.Scene()
        for nom, yg in sorted(bl.items()):
            if not yg.n:
                continue
            if nom == "Yol_Chegara":
                tugun = nom + "-colonly"             # ko'rinmas, faqat to'qnashuv
            elif nom.startswith(("Devor_", "Obida_", "Yer_Tuproq", "Yol_Asfalt", "Yol_Mahalla")):
                tugun = nom + "-col"
            else:
                tugun = nom
            sahna.add_geometry(yg.mesh(nom), node_name=tugun, geom_name=nom)
        fayl = f"bolak_{kx}_{kz}.glb"
        data = sahna.export(file_type="glb")
        open(os.path.join(CHIQ, fayl), "wb").write(data)
        jami += len(data)
        indeks.append({"fayl": fayl, "x": kx * BOLAK, "z": kz * BOLAK})

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
