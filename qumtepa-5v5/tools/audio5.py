"""Qumtepa 5v5 — 6-bosqich: hududlarning fon tovushlari (protsedural, 22050 Hz, mono, 20 s halqa).

Qoida: fon tovushlari qadam tovushlarini bosib ketmasligi kerak — ular past chastotali/yumshoq va
o'yinda -18…-24 dB da ijro etiladi (gen_godot5.py). Tovushlar keskin, qadamga o'xshash zarbalarsiz.
Natija: godot/audio/amb_*.wav
"""
import os
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter

SR = 22050
DUR = 20.0
N = int(SR * DUR)
t = np.arange(N) / SR
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "godot", "audio")


def bp(x, lo, hi, order=2):
    b, a = butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    return lfilter(b, a, x)


def lp(x, hi, order=2):
    b, a = butter(order, hi / (SR / 2), btype="low")
    return lfilter(b, a, x)


def loopable(x, fade=1.0):
    """boshi va oxirini ustma-ust qo'yib, choksiz halqa qiladi"""
    k = int(fade * SR)
    w = np.linspace(0, 1, k)
    y = x[:N].copy()
    y[:k] = x[:k] * w + x[N:N + k] * (1 - w)
    return y


def norm(x, peak=0.6):
    return x / (np.abs(x).max() + 1e-9) * peak


def slow(rng, rate=0.2):
    """sekin o'zgaruvchi 0..1 egri chiziq (shamol kuchi, olomon shovqini)"""
    n = int((DUR + 2) * rate) + 4
    pts = rng.random(n)
    xs = np.linspace(0, DUR + 1.5, n)
    return np.interp(np.arange(N + SR) / SR, xs, pts)


def wind(rng, lo=120, hi=900):
    return bp(rng.normal(0, 1, N + SR), lo, hi) * (0.35 + 0.65 * slow(rng, 0.25))


def chirp(f0, f1, dur, rng):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = np.linspace(f0, f1, n) * (1 + 0.04 * np.sin(2 * np.pi * rng.uniform(20, 40) * tt))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.hanning(n)


def place(buf, x, at):
    i = int(at * SR)
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i]


def bozor(rng):
    # olomon g'o'ng'irlashi: bir necha "ovoz" formantli shovqin, amplitudasi so'zlarga o'xshab o'zgaradi
    x = np.zeros(N + SR)
    for k in range(7):
        f = rng.uniform(250, 900)
        syl = (np.sin(2 * np.pi * rng.uniform(2.5, 4.5) * np.arange(N + SR) / SR + rng.uniform(0, 6)) > 0.2).astype(float)
        syl = lp(syl, 8)
        x += bp(rng.normal(0, 1, N + SR), f * 0.8, f * 1.3) * syl * (0.4 + 0.6 * slow(rng, 0.3))
    x = lp(x, 1400)
    # uzoqdagi idish-tovoq jiringlashi (yumshoq)
    for _ in range(10):
        n = int(0.6 * SR)
        tt = np.arange(n) / SR
        ring = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * 6) for f in rng.uniform(1800, 3200, 3)) * 0.05
        place(x, ring, rng.uniform(0, DUR))
    return x


def masjid(rng):
    x = wind(rng, 80, 500) * 0.5
    # kaptarlar: past "g'u-g'u"
    for _ in range(9):
        at = rng.uniform(0, DUR - 2)
        for k in range(3):
            n = int(0.35 * SR)
            tt = np.arange(n) / SR
            coo = np.sin(2 * np.pi * (330 - 60 * tt / 0.35) * tt) * np.hanning(n) * (1 + 0.5 * np.sin(2 * np.pi * 28 * tt))
            place(x, coo * 0.35, at + k * 0.45)
    return x


def madrasa(rng):
    x = wind(rng, 100, 600) * 0.4
    # chumchuqlar
    for _ in range(40):
        at = rng.uniform(0, DUR)
        for k in range(int(rng.integers(2, 5))):
            f0 = rng.uniform(3200, 4800)
            place(x, chirp(f0, f0 * rng.uniform(0.7, 1.2), rng.uniform(0.05, 0.12), rng) * 0.25, at + k * 0.13)
    return x


def karvon(rng):
    x = wind(rng, 100, 700) * 0.7
    # uzoqdagi tuya qo'ng'iroqchasi (qo'ng'iroq harmonikalari, sekin so'nadi)
    for _ in range(6):
        n = int(2.5 * SR)
        tt = np.arange(n) / SR
        f = rng.uniform(600, 800)
        bell = sum(a * np.sin(2 * np.pi * f * m * tt) for a, m in ((1, 1), (0.5, 2.76), (0.3, 5.4))) * np.exp(-tt * 1.6) * 0.18
        place(x, bell, rng.uniform(0, DUR - 3))
    # yog'och g'ichirlashi
    for _ in range(4):
        n = int(0.8 * SR)
        tt = np.arange(n) / SR
        creak = bp(np.sign(np.sin(2 * np.pi * (70 + 40 * tt) * tt)) * rng.normal(1, 0.3, n), 200, 1200) * np.hanning(n) * 0.2
        place(x, creak, rng.uniform(0, DUR - 1))
    return x


def qala(rng):
    x = wind(rng, 60, 1200) * 1.0
    # bayroq hilpirashi: tez modulyatsiyalangan shovqin portlashlari
    for _ in range(5):
        n = int(rng.uniform(1.0, 2.2) * SR)
        tt = np.arange(n) / SR
        flap = bp(rng.normal(0, 1, n), 300, 2500) * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(7, 12) * tt)) * np.hanning(n) * 0.25
        place(x, flap, rng.uniform(0, DUR - 2.5))
    return x


def tunnel(rng):
    # yopiq yo'lak: past gumburlash + suv tomchilari
    x = lp(rng.normal(0, 1, N + SR), 90) * 3.0
    for _ in range(14):
        n = int(0.25 * SR)
        tt = np.arange(n) / SR
        f = rng.uniform(900, 1600)
        drop = np.sin(2 * np.pi * (f + 900 * tt / 0.25) * tt) * np.exp(-tt * 30) * 0.3
        place(x, drop, rng.uniform(0, DUR))
    return x


def gunshot(rng, body_hz, crack_amt, tail):
    """o'q ovozi: keskin portlash (shovqin zarbasi) + past chastotali "gumburlash" + devorlardan aks-sado dumi"""
    n = int(tail * SR)
    tt = np.arange(n) / SR
    crack = rng.normal(0, 1, n) * np.exp(-tt * 90) * crack_amt
    boom = bp(rng.normal(0, 1, n), 60, body_hz) * np.exp(-tt * 18) * 2.5
    thump = np.sin(2 * np.pi * 70 * tt * (1 - tt)) * np.exp(-tt * 30) * 1.2
    echo = np.zeros(n)
    for d, g in ((0.07, 0.35), (0.13, 0.22), (0.21, 0.12)):
        k = int(d * SR)
        echo[k:] += (boom[: n - k] + crack[: n - k] * 0.3) * g
    x = crack + boom + thump + lp(echo, 1800)
    x[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    return norm(x, 0.85)


def reload_sound(rng):
    """qayta o'qlash: magazin chiqishi, yangisi kirishi, zatvor tortilishi (qisqa metall chertishlar)"""
    n = int(2.6 * SR)
    x = np.zeros(n)
    def click(at, f, dur, g):
        m = int(dur * SR)
        tt = np.arange(m) / SR
        c = (bp(rng.normal(0, 1, m), f * 0.6, min(f * 1.6, SR / 2 - 100)) + 0.5 * np.sin(2 * np.pi * f * tt)) * np.exp(-tt * 60) * g
        place(x, c, at)
    for at, f, dur, g in ((0.55, 2400, 0.08, 0.8), (0.62, 900, 0.1, 0.6), (1.5, 1800, 0.06, 0.5), (1.95, 2600, 0.09, 1.0),
                          (2.02, 1100, 0.12, 0.8), (2.25, 3000, 0.05, 0.6), (2.32, 1500, 0.08, 0.7)):
        click(at, f, dur, g)
    return norm(x, 0.7)


SOUNDS = {"bozor": bozor, "masjid": masjid, "madrasa": madrasa, "karvon": karvon, "qala": qala, "tunnel": tunnel}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for i, (name, fn) in enumerate(SOUNDS.items()):
        rng = np.random.default_rng(600 + i)
        x = norm(loopable(fn(rng)))
        wavfile.write(os.path.join(OUT, f"amb_{name}.wav"), SR, (x * 32767).astype(np.int16))
    print("fon tovushlari:", ", ".join(f"amb_{n}.wav" for n in SOUNDS))
    # qurol tovushlari (birinchi shaxs)
    rng = np.random.default_rng(700)
    for name, hz, cr, tail in (("akm", 380, 1.3, 0.9), ("m416", 520, 1.0, 0.8)):
        wavfile.write(os.path.join(OUT, f"shot_{name}.wav"), SR, (gunshot(rng, hz, cr, tail) * 32767).astype(np.int16))
    wavfile.write(os.path.join(OUT, "reload.wav"), SR, (reload_sound(rng) * 32767).astype(np.int16))
    print("qurol tovushlari: shot_akm.wav, shot_m416.wav, reload.wav")
