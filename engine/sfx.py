"""Ses tasarımı: tüm efektler ve atmosfer numpy ile sıfırdan sentezlenir (hazır örnek yok).

Efektler: whoosh (geçiş), impact (vurgu), riser (gerilim), tick (sayaç), shimmer (zirve),
pop (yazı), boom (final). Atmosfer: rüzgâr + drone pad + nabız (perküsyon), sesle ducking.
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(d * SR)) / SR


def env_adsr(n, a, d, s, r):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    sus = max(0, n - a - d - r)
    e = np.concatenate([np.linspace(0, 1, a, False), np.linspace(1, s, d, False),
                        np.full(sus, s), np.linspace(s, 0, r)])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), x)


def sweep_filter(x, f0, f1, q=1.5, blocks=64):
    """Zamanla değişen band geçiren filtre (blok blok, çapraz geçişli)."""
    out = np.zeros_like(x)
    n = len(x)
    edges = np.linspace(0, n, blocks + 1).astype(int)
    for i in range(blocks):
        a, b = edges[i], edges[i + 1]
        fc = f0 * (f1 / f0) ** (i / (blocks - 1))
        lo, hi = max(30, fc / (1 + 1 / q)), min(SR / 2 - 100, fc * (1 + 1 / q))
        pad = min(a, 2048)
        seg = bp(x[a - pad:b], lo, hi)[pad:]
        out[a:b] = seg
    return out


_IR = None


def reverb(x, wet=0.3, length=2.2):
    global _IR
    if _IR is None:
        n = int(length * SR)
        dec = np.exp(-np.linspace(0, 7, n))
        L = lp(rng.standard_normal(n), 7000) * dec
        R = lp(rng.standard_normal(n), 7000) * dec
        _IR = np.stack([L, R], 1) / np.sqrt(np.sum(L ** 2))
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    y = np.stack([fftconvolve(x[:, c], _IR[:, c])[: len(x) + len(_IR)] for c in range(2)], 1)
    dry = np.pad(x, ((0, len(y) - len(x)), (0, 0)))
    return dry * (1 - wet) + y * wet


def pan(x, p):
    """p: -1..1 sabit ya da dizi."""
    p = np.asarray(p)
    l, r = np.cos((p + 1) * np.pi / 4), np.sin((p + 1) * np.pi / 4)
    return np.stack([x * l, x * r], 1)


# ------------------------------------------------------------------ efektler
def whoosh(d=0.7, up=True):
    n = int(d * SR)
    x = rng.standard_normal(n)
    x = sweep_filter(x, 300, 5000, q=1.2) if up else sweep_filter(x, 5000, 250, q=1.2)
    t = np.linspace(0, 1, n)
    e = np.sin(np.pi * t ** 0.7) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(np.linspace(180, 700 if up else 90, n)) / SR) * 0.15
    y = (x * 0.9 + tone) * e
    return reverb(pan(y / (np.max(np.abs(y)) + 1e-9), np.linspace(-0.7, 0.7, n)), 0.25)


def impact(strength=1.0):
    d = 1.6
    t = t_(d)
    f = 95 * np.exp(-t * 9) + 38
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.0)
    click = hp(rng.standard_normal(len(t)), 1500) * np.exp(-t * 60) * 0.5
    crunch = bp(rng.standard_normal(len(t)), 200, 2000) * np.exp(-t * 14) * 0.35
    y = (body + click + crunch) * strength
    y = np.tanh(y * 1.6) / np.tanh(1.6)
    return reverb(pan(y, 0), 0.22)


def boom():
    d = 3.5
    t = t_(d)
    f = 70 * np.exp(-t * 5) + 30
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.4)
    noise = lp(rng.standard_normal(len(t)), 900) * np.exp(-t * 3) * 0.6
    y = np.tanh((sub + noise) * 2.2)
    return reverb(pan(y, 0), 0.4, )


def riser(d=3.0):
    t = t_(d)
    p = t / d
    f = 110 * (2 ** (3 * p ** 1.6))
    saw = sum(np.sin(2 * np.pi * np.cumsum(f * k * (1 + 0.003 * j)) / SR) / k
              for k in range(1, 6) for j in (-1, 1))
    nz = sweep_filter(rng.standard_normal(len(t)), 400, 9000, q=1.0)
    y = (lp(saw, 4000) * 0.35 + nz * 0.6) * (p ** 2.2)
    y[-int(0.015 * SR):] *= np.linspace(1, 0, int(0.015 * SR))
    return reverb(pan(y / (np.max(np.abs(y)) + 1e-9), np.sin(t * 9) * 0.4), 0.2)


def tick(pitch=1.0):
    t = t_(0.06)
    y = np.sin(2 * np.pi * 2400 * pitch * t) * np.exp(-t * 90) + hp(rng.standard_normal(len(t)), 4000) * np.exp(-t * 200) * 0.3
    return pan(y * 0.6, 0.15)


def pop(pitch=1.0):
    t = t_(0.18)
    f = 600 * pitch * np.exp(-t * 18) + 300 * pitch
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 26)
    return reverb(pan(y * 0.7, -0.1), 0.15)


def shimmer(base=880):
    t = t_(2.6)
    parts = [(1, 1), (2.01, .5), (2.76, .35), (4.07, .22), (5.4, .12)]
    y = sum(a * np.sin(2 * np.pi * base * r * t) * np.exp(-t * (1.6 + r * .5)) for r, a in parts)
    y *= np.minimum(1, t / 0.004)
    return reverb(pan(y * 0.35, 0.2), 0.45)


# ------------------------------------------------------------------ atmosfer
def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def pad_chord(notes, d):
    t = t_(d)
    y = np.zeros(len(t))
    for n in notes:
        for det in (-0.07, 0.0, 0.08):
            f = midi(n + det)
            ph = rng.uniform(0, 2 * np.pi)
            y += sum(np.sin(2 * np.pi * f * k * t + ph) / k ** 1.3 for k in range(1, 7))
    y = lp(y, 1400)
    return y * env_adsr(len(t), min(1.2, d / 3), 0.5, 0.85, min(1.5, d / 3))


def ambience(T, intensity_curve):
    """Rüzgâr + akor pad + nabız. intensity_curve(t)->0..1 enerjiyi belirler."""
    n = int(T * SR)
    tt = np.arange(n) / SR
    # rüzgâr: kahverengi gürültü, yavaş modüle edilen süpürme
    w = np.cumsum(rng.standard_normal(n)); w = hp(w - np.convolve(w, np.ones(4800) / 4800, "same"), 60)
    w /= np.max(np.abs(w)) + 1e-9
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * 0.11 * tt + 1) * np.sin(2 * np.pi * 0.037 * tt)
    wind = sweep_filter(w, 250, 900, q=0.8, blocks=96) * gust
    windL = np.stack([wind, np.roll(wind, 2400)], 1) * 0.5
    # akor ilerlemesi (La minör: Am - F - C - G), her akor 4 sn
    prog = [[45, 52, 57, 60, 64], [41, 48, 53, 57, 60], [36, 48, 52, 55, 60], [43, 50, 55, 59, 62]]
    padL = np.zeros((n + SR * 3, 2))
    cd = 4.0
    k, start = 0, 0.0
    while start < T:
        ch = pad_chord(prog[k % 4], cd + 1.5)
        a = int(start * SR)
        padL[a:a + len(ch)] += pan(ch, 0.25 * (-1) ** k)[: len(padL) - a]
        k += 1; start += cd
    padL = padL[:n]
    padL /= np.max(np.abs(padL)) + 1e-9
    # nabız: 96 BPM kalp atışı tadında düşük perküsyon, yoğunluğa bağlı
    beat = 60 / 96
    pulse = np.zeros((n, 2))
    hit = impact(0.5)[: int(0.5 * SR)]
    hit = hit * np.linspace(1, 0, len(hit))[:, None]
    b = 0.0
    while b < T:
        g = intensity_curve(b)
        if g > 0.05:
            a = int(b * SR)
            m = min(len(hit), n - a)
            pulse[a:a + m] += hit[:m] * g
        b += beat
    pulse = lp(pulse.T, 220).T
    return windL * 0.32 + padL * 0.42 + pulse * 0.5


def duck_env(voice, depth_db=-9, attack=0.03, release=0.35):
    n = len(voice)
    win = int(0.02 * SR)
    m = n // win
    rms = np.sqrt(np.mean(voice[: m * win].reshape(m, win) ** 2, 1))
    on = (rms > 0.02).astype(float)
    g = np.ones(m)
    lo = 10 ** (depth_db / 20)
    a_c, r_c = np.exp(-0.02 / attack), np.exp(-0.02 / release)
    cur = 1.0
    for i in range(m):
        target = lo if on[i] else 1.0
        c = a_c if target < cur else r_c
        cur = target + (cur - target) * c
        g[i] = cur
    g = np.repeat(g, win)
    return np.pad(g, (0, n - len(g)), constant_values=1.0)


SFX = {"whoosh": whoosh, "impact": impact, "boom": boom, "riser": riser,
       "tick": tick, "pop": pop, "shimmer": shimmer}


def mix(voice_mono, T, events, intensity_curve):
    """events: [{t, type, gain, args{}}]. Döner: stereo float dizi."""
    n = int(T * SR)
    voice = np.pad(voice_mono, (0, max(0, n - len(voice_mono))))[:n]
    bed = ambience(T, intensity_curve)[:n]
    fx = np.zeros((n + SR * 6, 2))
    cache = {}
    for e in events:
        key = (e["type"], tuple(sorted(e.get("args", {}).items())))
        if key not in cache:
            s = SFX[e["type"]](**e.get("args", {}))
            cache[key] = s / (np.max(np.abs(s)) + 1e-9)
        s = cache[key]
        a = int(max(0, e["t"]) * SR)
        fx[a:a + len(s)] += s * e.get("gain", 1.0)
    fx = fx[:n]
    g = duck_env(voice)[:, None]
    out = np.stack([voice, voice], 1) * 1.0 + bed * 0.30 * g + fx * 0.55 * (0.55 + 0.45 * g)
    # yumuşak sınırlayıcı
    out = np.tanh(out * 1.1) / np.tanh(1.1)
    fade = int(0.6 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    out[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
    return out
