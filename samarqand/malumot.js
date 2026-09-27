// Samarqand ma'lumotini o'qish (tools/samarqand_tayyorla.py yaratgan JSON'lar).
// 2D (samarqand.html) va 3D (samarqand3d.html) sahifalar umumiy ishlatadi.
//
// Natijadagi koordinatalar: Float64Array [lon0, lat0, lon1, lat1, ...].
(function(){
'use strict';

function ochish(kod, o, q){
  const n = kod.length / 2;
  const ro = new Float64Array(n * 2);
  let x = 0, y = 0;
  for (let i = 0; i < n; i++){
    x += kod[i*2]; y += kod[i*2+1];
    ro[i*2] = o[0] + x / q;
    ro[i*2+1] = o[1] + y / q;
  }
  return ro;
}
function quti(halqalar){
  let a = Infinity, b = Infinity, c = -Infinity, d = -Infinity;
  for (const h of halqalar) for (let i = 0; i < h.length; i += 2){
    if (h[i] < a) a = h[i]; if (h[i] > c) c = h[i];
    if (h[i+1] < b) b = h[i+1]; if (h[i+1] > d) d = h[i+1];
  }
  return [a, b, c, d];                          // [minLon, minLat, maxLon, maxLat]
}

async function json(yol){
  const j = await fetch(yol);
  if (!j.ok) throw new Error(yol + ': HTTP ' + j.status);
  return j.json();
}

// Fazoviy katak indeksi: har bir ob'ekt qutisi tegadigan barcha kataklarga yoziladi
class Katak {
  constructor(olcham){ this.o = olcham; this.m = new Map(); }
  kalit(x, y){ return x + ':' + y; }
  qosh(ob){
    const [a,b,c,d] = ob.bb, o = this.o;
    for (let y = Math.floor(b/o); y <= Math.floor(d/o); y++)
      for (let x = Math.floor(a/o); x <= Math.floor(c/o); x++){
        const k = this.kalit(x, y);
        let r = this.m.get(k); if (!r) this.m.set(k, r = []);
        r.push(ob);
      }
  }
  // quti bilan kesishadiganlar (takrorsiz)
  izla(a, b, c, d, natija){
    const o = this.o, korildi = new Set();
    natija = natija || [];
    for (let y = Math.floor(b/o); y <= Math.floor(d/o); y++)
      for (let x = Math.floor(a/o); x <= Math.floor(c/o); x++){
        const r = this.m.get(this.kalit(x, y));
        if (!r) continue;
        for (const ob of r){
          if (korildi.has(ob)) continue;
          korildi.add(ob);
          if (ob.bb[0] <= c && ob.bb[2] >= a && ob.bb[1] <= d && ob.bb[3] >= b) natija.push(ob);
        }
      }
    return natija;
  }
}

function ichidami(lon, lat, h){
  let ich = false;
  for (let i = 0, j = h.length - 2; i < h.length; j = i, i += 2){
    const xi = h[i], yi = h[i+1], xj = h[j], yj = h[j+1];
    if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) ich = !ich;
  }
  return ich;
}

// Uy balandligi: o'lchangan > qavatlar soni > taxmin (turi va maydoni bo'yicha)
const QAVAT_M = 3.2;
function balandlik(b, maydonM2){
  if (b.h) return { m:b.h, aniq:2 };                       // o'lchangan
  if (b.f) return { m:b.f * QAVAT_M + 1, aniq:1 };         // qavatlardan
  const s = b.s;
  let f = 1;
  if (s === 'apartments' || s === 'dormitory') f = 5;
  else if (s === 'hotel' || s === 'hospital' || s === 'university' || s === 'office') f = 4;
  else if (s === 'school' || s === 'college' || s === 'commercial' || s === 'civic' || s === 'public') f = 3;
  else if (s === 'garage' || s === 'shed' || s === 'carport' || s === 'greenhouse' || s === 'roof' || s === 'barn') f = 1;
  else if (maydonM2 > 1200) f = 3;
  else if (maydonM2 > 350) f = 2;
  return { m:f * QAVAT_M + (s === 'roof' || s === 'carport' ? -0.6 : 0.8), aniq:0 };
}

async function yukla(asos, qismlar){
  asos = asos || 'samarqand/';
  qismlar = qismlar || ['fon', 'yollar', 'uylar'];
  const ro = {};
  const va = await Promise.all(qismlar.map(q => json(asos + ({fon:'fon.json', yollar:'yollar.json', uylar:'uylar.json'}[q]))));
  qismlar.forEach((q, i) => ro[q] = va[i]);

  const natija = {};
  if (ro.fon){
    const d = ro.fon, o = d.o, q = d.q;
    natija.chegaraQuti = d.chegaraQuti;
    natija.manba = d.manba;
    natija.chegara = d.chegara.map(p => p.map(h => ochish(h, o, q)));
    natija.suvP = d.suvP.map(p => { const r = p.map(h => ochish(h, o, q)); return {r, bb:quti(r)}; });
    natija.suvCh = d.suvCh.map(([s, k]) => { const kk = ochish(k, o, q); return {s, k:kk, bb:quti([kk])}; });
    natija.yer = d.yer.map(([tur, s, ...h]) => { const r = h.map(x => ochish(x, o, q)); return {tur, s, r, bb:quti(r)}; });
  }
  if (ro.yollar){
    const d = ro.yollar, o = d.o, q = d.q;
    natija.yollar = d.y.map(([s, b, n, k]) => {
      const kk = ochish(k, o, q);
      return {s:d.sinflar[s], b, nom: n >= 0 ? d.nomlar[n] : null, k:kk, bb:quti([kk])};
    });
  }
  if (ro.uylar){
    const d = ro.uylar, o = d.o, q = d.q;
    natija.statistika = d.statistika;
    natija.uylar = d.b.map(([s, h, f, m, n, t, ...hh]) => {
      const r = hh.map(x => ochish(x, o, q));
      return {s:d.sinflar[s], h:h / 10, f, m, nom: n >= 0 ? d.nomlar[n] : null, t, r, bb:quti(r)};
    });
  }
  return natija;
}

window.SamarqandMalumot = { yukla, Katak, ichidami, balandlik, QAVAT_M };
})();
