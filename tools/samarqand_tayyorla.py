"""Samarqand shahri ma'lumotini Overture Maps'dan tayyorlash.

Natija `samarqand/` papkasidagi ixcham JSON fayllar. Ularni 2D xarita
(samarqand.html) va 3D o'yin prototipi (samarqand3d.html) ishlatadi.

Ishga tushirish:
    pip install pyarrow fsspec aiohttp requests shapely
    python3 tools/samarqand_tayyorla.py            # Overture'dan yuklab, keyin o'giradi
    python3 tools/samarqand_tayyorla.py --kesh DIR # oldin yuklangan parquet'lar bilan

Koordinatalar formati: [lon, lat] gradus * 1e6, `o` nuqtasiga nisbatan butun son.
Har bir halqa yoki chiziq tekis massiv: [x0, y0, dx1, dy1, dx2, dy2, ...]
(birinchi nuqta o'zi, keyingilari oldingisidan farq). Yopiq halqaning oxirgi
takroriy nuqtasi saqlanmaydi.
"""
import argparse, json, os, subprocess, sys
import pyarrow.parquet as pq
import shapely
from shapely.geometry import Point

BU_YER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BU_YER)
CHIQISH = os.path.join(REPO, "samarqand")

Q = 1_000_000
O = (66.81, 39.61)                        # [lon, lat] boshlang'ich nuqta

# Tarixiy obidalar — shu nuqtalar atrofidagi binolar "tarixiy" deb belgilanadi
OBIDALAR = [
    ("Registon", 39.6547, 66.9757, 80), ("Go'ri Amir", 39.6484, 66.9691, 45),
    ("Bibixonim masjidi", 39.6607, 66.9797, 90), ("Hazrati Xizr masjidi", 39.6621, 66.9860, 30),
    ("Shohi Zinda", 39.6632, 66.9881, 110), ("Ulug'bek rasadxonasi", 39.6747, 67.0058, 40),
    ("Ruhobod maqbarasi", 39.6493, 66.9701, 20), ("Oqsaroy maqbarasi", 39.6479, 66.9676, 20),
]
# obida yonidagi bo'lsa ham tarixiy emas
YANGI_SOZLAR = ("hotel", "mehmonxona", "гостиниц", "bazaar", "bozor", "рынок", "cafe", "kafe", "shop", "do'kon")
TARIXIY_SINF = {"mosque", "church", "cathedral", "synagogue", "temple", "shrine", "chapel"}

YOL_SINF = ["motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
            "residential", "living_street", "service", "pedestrian", "footway", "steps",
            "path", "track", "cycleway", "bridleway", "unknown", "rail", "tram"]
SUV_SINF_CHIZIQ = {"river", "canal", "stream", "drain", "ditch"}


def kodla_halqa(koord, yopiq):
    k = list(koord)
    if yopiq and len(k) > 1 and tuple(k[0]) == tuple(k[-1]):
        k = k[:-1]
    ro, px, py = [], None, None
    for lon, lat in k:
        x, y = round((lon - O[0]) * Q), round((lat - O[1]) * Q)
        if px is None:
            ro += [x, y]
        elif x != px or y != py:
            ro += [x - px, y - py]
        else:
            continue
        px, py = x, y
    return ro


def poligonlar(g):
    if g.geom_type == "Polygon":
        return [g]
    if g.geom_type in ("MultiPolygon", "GeometryCollection"):
        return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
    return []


def chiziqlar(g):
    if g.geom_type == "LineString":
        return [g]
    if g.geom_type in ("MultiLineString", "GeometryCollection"):
        return [p for p in g.geoms if p.geom_type == "LineString"]
    return []


def poligon_kodla(p):
    halqalar = [kodla_halqa(p.exterior.coords, True)]
    halqalar += [kodla_halqa(i.coords, True) for i in p.interiors]
    return [h for h in halqalar if len(h) >= 6]


class Nomlar:
    def __init__(self):
        self.ro, self.ix = [], {}

    def __call__(self, names):
        n = (names or {}).get("primary")
        if not n:
            return -1
        if n not in self.ix:
            self.ix[n] = len(self.ro)
            self.ro.append(n)
        return self.ix[n]


def yoz(nom, obj):
    yol = os.path.join(CHIQISH, nom)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  {nom}: {os.path.getsize(yol) / 1e6:.2f} MB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kesh", help="parquet fayllar turgan papka (bo'lmasa yuklanadi)")
    a = ap.parse_args()
    kesh = a.kesh or os.path.join(REPO, ".overture_kesh")
    os.makedirs(kesh, exist_ok=True)
    olish = os.path.join(BU_YER, "overture_olish.py")
    mavzular = {
        "div": ("theme=divisions/type=division_area", "id,geometry,bbox,names,subtype,class"),
        "bino": ("theme=buildings/type=building",
                 "id,geometry,bbox,subtype,class,height,num_floors,min_height,roof_shape,roof_color,facade_color,names,sources"),
        "yol": ("theme=transportation/type=segment", "id,geometry,bbox,subtype,class,names,road_flags"),
        "suv": ("theme=base/type=water", "id,geometry,bbox,subtype,class,names"),
        "yer": ("theme=base/type=land_use", "id,geometry,bbox,subtype,class,names"),
    }
    for k, (t, ust) in mavzular.items():
        f = os.path.join(kesh, k + ".parquet")
        if not os.path.exists(f):
            print("Yuklanmoqda:", t)
            subprocess.run([sys.executable, olish, t, f, ust], check=True)

    os.makedirs(CHIQISH, exist_ok=True)
    jadval = lambda k: pq.read_table(os.path.join(kesh, k + ".parquet")).to_pylist()

    # --- chegara ---
    chegara = None
    for r in jadval("div"):
        if (r["names"] or {}).get("primary") == "Samarqand shahri":
            chegara = shapely.from_wkb(r["geometry"])
    if chegara is None:
        sys.exit("Samarqand shahri chegarasi topilmadi")
    shapely.prepare(chegara)
    kesish = chegara.buffer(0.001)
    shapely.prepare(kesish)
    print("Chegara:", chegara.bounds)

    # --- binolar ---
    nom = Nomlar()
    sinflar, sinf_ix = [], {}
    obida_nuqtalar = [(n, Point(lon, lat).buffer(r / 111_000)) for n, lat, lon, r in OBIDALAR]
    binolar, statistika = [], {"jami": 0, "balandlik": 0, "qavat": 0, "osm": 0, "ms": 0}
    for r in jadval("bino"):
        g = shapely.from_wkb(r["geometry"])
        if not chegara.intersects(g):
            continue
        sinf = r["class"] or r["subtype"] or ""
        if sinf not in sinf_ix:
            sinf_ix[sinf] = len(sinflar)
            sinflar.append(sinf)
        manba = ((r["sources"] or [{}])[0] or {}).get("dataset", "")
        m = 0 if manba == "OpenStreetMap" else 1 if "Microsoft" in manba else 2
        h = round(r["height"] * 10) if r["height"] else 0          # detsimetr
        f = int(r["num_floors"]) if r["num_floors"] else 0
        nom_matn = ((r["names"] or {}).get("primary") or "").lower()
        obida_yonida = (any(b.intersects(g) for _, b in obida_nuqtalar)
                        and not any(s in nom_matn for s in YANGI_SOZLAR)
                        and r["subtype"] not in ("commercial", "residential"))
        tarixiy = 1 if (r["class"] in TARIXIY_SINF or r["subtype"] == "religious" or obida_yonida) else 0
        for p in poligonlar(g):
            halqalar = poligon_kodla(p)
            if halqalar:
                binolar.append([sinf_ix[sinf], h, f, m, nom(r["names"]), tarixiy] + halqalar)
        statistika["jami"] += 1
        statistika["balandlik"] += bool(h)
        statistika["qavat"] += bool(f)
        statistika["osm" if m == 0 else "ms"] += 1
    print("Binolar:", statistika)

    # --- yo'llar ---
    yollar = []
    for r in jadval("yol"):
        g = shapely.from_wkb(r["geometry"])
        if not kesish.intersects(g):
            continue
        sinf = r["class"] if r["subtype"] == "road" else ("tram" if r["class"] == "tram" else "rail")
        if sinf not in YOL_SINF:
            sinf = "unknown"
        bayroq = set()
        for fl in r["road_flags"] or []:
            bayroq.update(fl.get("values") or [])
        b = (1 if "is_bridge" in bayroq else 0) | (2 if "is_tunnel" in bayroq else 0) | (4 if "is_link" in bayroq else 0)
        for c in chiziqlar(g):
            yollar.append([YOL_SINF.index(sinf), b, nom(r["names"]), kodla_halqa(c.coords, False)])

    # --- suv va yer ---
    suv_p, suv_ch, yer = [], [], []
    for r in jadval("suv"):
        g = shapely.from_wkb(r["geometry"])
        if not kesish.intersects(g):
            continue
        g = g.intersection(kesish)
        if r["class"] in SUV_SINF_CHIZIQ and g.geom_type in ("LineString", "MultiLineString"):
            for c in chiziqlar(g):
                suv_ch.append([r["class"], kodla_halqa(c.coords, False)])
        else:
            for p in poligonlar(g):
                suv_p.append(poligon_kodla(p))
            for c in chiziqlar(g):
                suv_ch.append([r["class"], kodla_halqa(c.coords, False)])
    for r in jadval("yer"):
        g = shapely.from_wkb(r["geometry"])
        if not kesish.intersects(g):
            continue
        for p in poligonlar(g.intersection(kesish)):
            h = poligon_kodla(p)
            if h:
                yer.append([r["subtype"], r["class"]] + h)

    chegara_kod = [poligon_kodla(p) for p in poligonlar(chegara)]
    minx, miny, maxx, maxy = chegara.bounds
    umumiy = {"v": 1, "o": list(O), "q": Q,
              "manba": "© OpenStreetMap hissadorlari (ODbL), Overture Maps Foundation, Microsoft Building Footprints",
              "chegaraQuti": [[miny, minx], [maxy, maxx]]}

    print("Yozilmoqda:", CHIQISH)
    yoz("uylar.json", dict(umumiy, sinflar=sinflar, nomlar=nom.ro, b=binolar,
                           statistika=statistika))
    yoz("yollar.json", dict(umumiy, sinflar=YOL_SINF, nomlar=nom.ro, y=yollar))
    yoz("fon.json", dict(umumiy, chegara=chegara_kod, suvP=suv_p, suvCh=suv_ch, yer=yer))


if __name__ == "__main__":
    main()
