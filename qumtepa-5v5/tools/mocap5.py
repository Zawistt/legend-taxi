"""Qumtepa 5v5 — haqiqiy odam harakati (CMU motion capture) dan personaj animatsiyalari uchun "treklar".

Manba: CMU Graphics Lab Motion Capture Database (mocap.cs.cmu.edu), BVH ko'rinishi (cgspeed / una-dinosauria/cmu-mocap).
CMU: "This data is free for use in research projects... You may include this data in commercially-sold products".

Har bir trek 30 kadr/s, Blender armatura fazosida (X — chap, −Y — old, Z — tepa, metr):
  hips   (n,3)       son markazi (ikki son bo'g'imi o'rtasi)
  rot[j] (n,3,3)     bo'g'imning dunyo fazosidagi "tinch holatdan burilishi" (retarget: bizning suyak = D @ tinch)
  foot[s], knee[s], toe (n,3)  oyoq to'pig'i, tizza, oyoq barmog'i joylari (IK nishonlari)
Yurish sikllari: joyida (oldinga siljish olib tashlangan), boshi-oxiri tutashtirilgan (halqa), o'yin tezligiga moslangan.
"""
import os, math
import numpy as np
from bvh5 import BVH

HERE = os.path.dirname(os.path.abspath(__file__))
CMU = os.environ.get("CMU_BVH", os.path.join(HERE, "..", "assets_src", "mocap"))
FPS = 30
C = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])      # BVH (Y tepa, +Z old) -> Blender (Z tepa, −Y old)
JMAP = {"hips": "Hips", "spine": "LowerBack", "spine1": "Spine", "chest": "Spine1", "neck": "Neck1", "head": "Head",
        "thigh.L": "LeftUpLeg", "shin.L": "LeftLeg", "foot.L": "LeftFoot", "toe.L": "LeftToeBase",
        "thigh.R": "RightUpLeg", "shin.R": "RightLeg", "foot.R": "RightFoot", "toe.R": "RightToeBase"}


def Rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def q_from_m(M):
    """3x3 -> kvaternion (w,x,y,z)"""
    t = np.trace(M)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        return np.array([0.25 * s, (M[2, 1] - M[1, 2]) / s, (M[0, 2] - M[2, 0]) / s, (M[1, 0] - M[0, 1]) / s])
    i = int(np.argmax(np.diag(M)))
    j, k = (i + 1) % 3, (i + 2) % 3
    s = math.sqrt(1.0 + M[i, i] - M[j, j] - M[k, k]) * 2
    q = np.zeros(4)
    q[0] = (M[k, j] - M[j, k]) / s
    q[1 + i] = 0.25 * s
    q[1 + j] = (M[j, i] + M[i, j]) / s
    q[1 + k] = (M[k, i] + M[i, k]) / s
    return q


def m_from_q(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(q0, q1, t):
    if np.dot(q0, q1) < 0:
        q1 = -q1
    d = np.clip(np.dot(q0, q1), -1, 1)
    if d > 0.9995:
        q = q0 + t * (q1 - q0)
        return q / np.linalg.norm(q)
    th = math.acos(d)
    return (math.sin((1 - t) * th) * q0 + math.sin(t * th) * q1) / math.sin(th)


class Clip:
    """bitta BVH: Blender fazosiga o'tkazilgan joylar va burilishlar"""
    cache = {}

    def __init__(self, name, leg_len):
        key = (name, round(leg_len, 4))
        s = name.split("_")[0]
        path = os.path.join(CMU, f"{int(s):03d}", f"{name}.bvh")
        b = BVH(path)
        Rg, Pg = b.fk()
        self.dt = b.dt
        self.n = b.nframes
        rp = b.rest_positions()
        i = b.idx
        src_leg = ((rp[i["LeftUpLeg"], 1] - rp[i["LeftFoot"], 1]) + (rp[i["RightUpLeg"], 1] - rp[i["RightFoot"], 1])) / 2
        self.s = leg_len / src_leg
        P = np.einsum("ij,fkj->fki", C, Pg) * self.s
        R = np.einsum("ij,fkjl,ml->fkim", C, Rg, C)
        self.P, self.R, self.i = P, R, i
        # pol: tayanchdagi to'piq balandligi (5-persentil) = 0.085 m
        ank = np.minimum(P[:, i["LeftFoot"], 2], P[:, i["RightFoot"], 2])
        self.ground = np.percentile(ank, 5) - 0.085

    def joint(self, name):
        return self.P[:, self.i[name]]

    def rot(self, name):
        return self.R[:, self.i[name]]

    def hips_mid(self):
        return (self.joint("LeftUpLeg") + self.joint("RightUpLeg")) / 2

    def facing(self, f0, f1):
        """o'rtacha yuz yo'nalishi (son burilishidan), Blender XY da"""
        # son bo'g'imlari chizig'idan (chap - o'ng): ba'zi kliplarda "Hips" burilishi tanaga mos emas
        lr = (self.joint("LeftUpLeg") - self.joint("RightUpLeg"))[f0:f1, :2].mean(0)
        v = np.array([lr[1], -lr[0]])
        return math.atan2(v[1], v[0])


def track_from(clip, f0, f1, align="facing", keep_drift=False, loop=True, speed=None, stride_max=1.25, face=None, zfix=None):
    """[f0, f1) oraliqdan trek. align: yuz -Y ga buriladi. loop: boshi-oxiri tutashtiriladi.
    speed: o'yindagi tezlik (m/s) — qadam uzunligi (≤ stride_max) va vaqt birga o'zgartiriladi."""
    c = clip
    idx = np.arange(f0, f1)
    ang = c.facing(*(face or (f0, f1)))
    Q = Rz(-math.pi / 2 - ang)            # yuz -> -Y
    def pos(name):
        p = c.joint(name)[idx].copy()
        p[:, 2] -= c.ground
        return p @ Q.T
    hips = (pos("LeftUpLeg") + pos("RightUpLeg")) / 2
    if zfix is not None:                   # sakrash: havodagi ko'tarilish o'yin fizikasiga qoldiriladi
        zf = np.asarray(zfix)[idx]
    tr = {"hips": hips, "foot.L": pos("LeftFoot"), "foot.R": pos("RightFoot"), "knee.L": pos("LeftLeg"), "knee.R": pos("RightLeg"),
          "toe.L": pos("LeftToeBase"), "toe.R": pos("RightToeBase")}
    if zfix is not None:
        hips = hips.copy(); hips[:, 2] -= zf
        tr["hips"] = hips
        for kk in tr:
            if kk != "hips":
                tr[kk][:, 2] -= zf
    rot = {k: np.einsum("ij,fjk->fik", Q, c.rot(v)[idx]) @ Q.T for k, v in JMAP.items()}
    T = (f1 - f0) * c.dt
    t = np.arange(len(idx)) * c.dt
    v = (hips[-1, :2] - hips[0, :2]) / T if len(idx) > 1 else np.zeros(2)
    src_speed = float(np.linalg.norm(v))
    if not keep_drift:
        drift = np.zeros((len(idx), 3))
        drift[:, :2] = hips[0, :2] + t[:, None] * v[None]
        for k in tr:
            tr[k] = tr[k] - drift
    # qadam uzunligi: oyoqlar son atrofida harakat yo'nalishi bo'ylab a marta cho'ziladi
    a, k_time = 1.0, 1.0
    if speed and src_speed > 0.2:
        a = min(stride_max, math.sqrt(speed / src_speed))
        k_time = speed / (src_speed * a)
        d = np.array([v[0], v[1], 0]) / src_speed
        for kk in ("foot.L", "foot.R", "knee.L", "knee.R", "toe.L", "toe.R"):
            rel = tr[kk] - tr["hips"]
            along = rel @ d
            tr[kk] = tr[kk] + (a - 1) * along[:, None] * d[None]
    # halqa: oxirgi kadr birinchisiga tutashadi (farq vaqt bo'yicha teng taqsimlanadi)
    n = len(idx)
    if loop and n > 2:
        w = np.linspace(0, 1, n)[:, None]
        for kk in tr:
            tr[kk] = tr[kk] + w * (tr[kk][0] - tr[kk][-1])
        for kk in rot:
            q0 = q_from_m(rot[kk][0])
            qn = q_from_m(rot[kk][-1])
            corr = q_from_m(rot[kk][0] @ rot[kk][-1].T)
            ident = np.array([1.0, 0, 0, 0])
            for f in range(n):
                cq = slerp(ident, corr, f / (n - 1))
                rot[kk][f] = m_from_q(cq) @ rot[kk][f]
    # 30 kadr/s ga (o'yin tezligi uchun vaqt k_time marta tezlashadi)
    dur = T / k_time
    nout = max(2, int(round(dur * FPS)))
    src_t = np.linspace(0, n - 1, nout + 1)          # halqada oxirgi kadr = birinchi (Godot silliq aylanadi)
    fi = np.clip(np.round(src_t).astype(int), 0, n - 1)
    out = {k: v2[fi] for k, v2 in tr.items()}
    out["rot"] = {k: v2[fi] for k, v2 in rot.items()}
    out["n"] = len(fi)
    out["speed"] = src_speed * a * k_time
    out["stride_scale"] = a
    out["time_scale"] = k_time
    return out


def reverse(tr):
    o = {k: (v[::-1].copy() if isinstance(v, np.ndarray) else v) for k, v in tr.items() if k != "rot"}
    o["rot"] = {k: v[::-1].copy() for k, v in tr["rot"].items()}
    return o


def cycle_bounds(clip, f0, f1):
    """[f0,f1) ichida bitta oyoqning ikki ketma-ket "eng oldinda" momenti orasidagi to'liq qadam sikli.
    Ikkala oyoqdan qidiriladi; klip o'rtasiga eng yaqin sikl olinadi. (CMU BVH 0-kadri — T-poza, tashlanadi.)"""
    f0 = max(f0, 1)
    ang = clip.facing(f0, f1)
    fwd = np.array([math.cos(ang), math.sin(ang)])
    best = None
    for foot in ("LeftFoot", "RightFoot"):
        rel = (clip.joint(foot) - clip.hips_mid())[f0:f1, :2] @ fwd
        k = 9
        peaks = [i for i in range(k, len(rel) - k) if rel[i] == rel[i - k:i + k + 1].max() and rel[i] > np.percentile(rel, 60)]
        for p, q in zip(peaks, peaks[1:]):
            c = abs((p + q) / 2 - len(rel) / 2)
            if best is None or c < best[0]:
                best = (c, f0 + p, f0 + q)
    if best is None:
        return f0, f1
    return best[1], best[2]


def strafe(tr, side):
    """oldinga sikldan yonga: butun pastki tana (son, oyoqlar, qadam yo'nalishi) harakat tomoniga 75° buriladi —
    odam yonga qarab yuguradi; umurtqa qarama-qarshi buriladi — ko'krak, qurol va bosh oldinga (nishonga) qaraydi.
    side: +1 — chapga (+X), −1 — o'ngga (−X)."""
    th = math.radians(75) * side
    RL = Rz(th)
    o = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in tr.items() if k != "rot"}
    o["rot"] = {k: v.copy() for k, v in tr["rot"].items()}
    hips = tr["hips"]
    for kk in ("foot.L", "foot.R", "knee.L", "knee.R", "toe.L", "toe.R"):
        o[kk] = hips + (tr[kk] - hips) @ RL.T
    for k in ("hips", "thigh.L", "shin.L", "foot.L", "toe.L", "thigh.R", "shin.R", "foot.R", "toe.R"):
        o["rot"][k] = np.einsum("ij,fjk->fik", RL, tr["rot"][k])
    for k, share in (("spine", 0.6), ("spine1", 0.25)):
        o["rot"][k] = np.einsum("ij,fjk->fik", Rz(th * share), tr["rot"][k])
    return o


def still(tr, f):
    """bitta kadrdan harakatsiz trek (n=2)"""
    o = {k: (v[[f, f]].copy() if isinstance(v, np.ndarray) else v) for k, v in tr.items() if k != "rot"}
    o["rot"] = {k: v[[f, f]].copy() for k, v in tr["rot"].items()}
    o["n"] = 2
    return o
