# Overture Maps'dan Samarqand hududini HTTP range so'rovlari bilan olish
import sys, re, requests, fsspec, pyarrow.parquet as pq, pyarrow as pa
from concurrent.futures import ThreadPoolExecutor
B = "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com"
REL = "release/2026-09-23.1"
XMIN, XMAX, YMIN, YMAX = 66.81, 67.07, 39.61, 39.73
fs = fsspec.filesystem("https", block_size=2**20)

def fayllar(t):
    r = requests.get(f"{B}/?list-type=2&prefix={REL}/{t}/").text
    return [f"{B}/{k}" for k in re.findall(r"<Key>([^<]+)</Key>", r)]

def stat(md, rg, nom):
    g = md.row_group(rg)
    for i in range(g.num_columns):
        c = g.column(i)
        if c.path_in_schema == nom and c.statistics and c.statistics.has_min_max:
            return c.statistics.min, c.statistics.max
    return None

def tekshir(url):
    try:
        f = fs.open(url, "rb"); pf = pq.ParquetFile(f); md = pf.metadata
        rgs = []
        for rg in range(md.num_row_groups):
            xa = stat(md, rg, "bbox.xmin"); xb = stat(md, rg, "bbox.xmax")
            ya = stat(md, rg, "bbox.ymin"); yb = stat(md, rg, "bbox.ymax")
            if not (xa and xb and ya and yb): rgs.append(rg); continue
            if xa[0] > XMAX or xb[1] < XMIN or ya[0] > YMAX or yb[1] < YMIN: continue
            rgs.append(rg)
        return url, rgs, md.num_row_groups
    except Exception as e:
        return url, None, str(e)

def ol(t, ustunlar, chiqish):
    fl = fayllar(t)
    with ThreadPoolExecutor(16) as ex: natija = list(ex.map(tekshir, fl))
    kerak = [(u, r) for u, r, _ in natija if r]
    xato = [(u, n) for u, r, n in natija if r is None]
    print(t, "fayl:", len(fl), "mos:", len(kerak), "rg:", sum(len(r) for _, r in kerak), "xato:", len(xato), file=sys.stderr)
    def oqi(ur):
        u, rgs = ur
        pf = pq.ParquetFile(fs.open(u, "rb"))
        cols = [c for c in ustunlar if c in pf.schema_arrow.names]
        tb = pf.read_row_groups(rgs, columns=cols)
        bb = tb.column("bbox").combine_chunks()
        import pyarrow.compute as pc
        m = pc.and_(pc.and_(pc.less_equal(bb.field("xmin"), XMAX), pc.greater_equal(bb.field("xmax"), XMIN)),
                    pc.and_(pc.less_equal(bb.field("ymin"), YMAX), pc.greater_equal(bb.field("ymax"), YMIN)))
        return tb.filter(m)
    with ThreadPoolExecutor(8) as ex: qismlar = [x for x in ex.map(oqi, kerak) if x.num_rows]
    tb = pa.concat_tables(qismlar, promote_options="permissive") if qismlar else None
    if tb is not None: pq.write_table(tb, chiqish)
    print(t, "qator:", tb.num_rows if tb is not None else 0, file=sys.stderr)

if __name__ == "__main__":
    t, chiqish, ustunlar = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
    ol(t, ustunlar, chiqish)
