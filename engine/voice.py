"""Seslendirme: Gemini TTS (ücretsiz, tek istek) → yedek: Microsoft Edge nöral ses → son yedek: gTTS.

Akış:
  1) Her anlatım parçası için Google TTS'ten mp3 alınır (önbelleğe yazılır).
  2) Baş/son sessizlik kırpılır, uzun duraklar kısaltılır, tempo artırılır (perde korunur).
  3) Türkçede her hecede tam bir ünlü olduğu için, kelime süreleri ünlü sayısına göre
     dağıtılır; noktalama ile ayrılmış öbekler, sesteki gerçek duraklarla eşleştirilir.
     Böylece TTS zaman damgası vermese de karaoke altyazı senkronu tutarlı olur.
"""
import base64
import json
import os
import re
import subprocess

import numpy as np

SR = 48000
VOWELS = set("aeıioöuüâîûAEIİOÖUÜÂÎÛ")

# ---------------------------------------------------------------- sayı -> yazı
_ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
_TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]


def tr_number(n: int) -> str:
    if n == 0:
        return "sıfır"
    parts = []
    for div, name in ((10**9, "milyar"), (10**6, "milyon"), (1000, "bin")):
        q, n = divmod(n, div)
        if q:
            parts.append(name if (q == 1 and name == "bin") else f"{tr_number(q)} {name}")
    h, n = divmod(n, 100)
    if h:
        parts.append("yüz" if h == 1 else f"{_ONES[h]} yüz")
    t, o = divmod(n, 10)
    if t:
        parts.append(_TENS[t])
    if o:
        parts.append(_ONES[o])
    return " ".join(parts)


def syllables(word: str) -> int:
    w = re.sub(r"\d+", lambda m: tr_number(int(m.group())), word)
    return max(1, sum(c in VOWELS for c in w))


# ---------------------------------------------------------------- TTS motorları
def synth_gtts(text, lang, path):
    from gtts import gTTS
    gTTS(text, lang=lang).save(path)


CHIRP_VOICE = "tr-TR-Chirp3-HD-Charon"   # erkek; kadın için ör. tr-TR-Chirp3-HD-Kore
CHIRP_MONTHLY_CAP = 800_000
CHIRP_TEMPO = float(os.environ.get("CHIRP_TEMPO") or "1.06")  # Shorts için biraz hızlandırma                # ücretsiz kota ayda 1 milyon karakter; güvenlik payı bırakıldı
USAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "tts_usage.json")


def _usage():
    import datetime
    month = datetime.datetime.utcnow().strftime("%Y-%m")
    u = json.load(open(USAGE)) if os.path.exists(USAGE) else {}
    return u, month


def chirp_allowed(n_chars):
    u, month = _usage()
    return u.get(month, 0) + n_chars <= CHIRP_MONTHLY_CAP


def chirp_count(n_chars):
    u, month = _usage()
    u[month] = u.get(month, 0) + n_chars
    os.makedirs(os.path.dirname(USAGE), exist_ok=True)
    json.dump(u, open(USAGE, "w"), indent=1)


def synth_gcloud(text, lang, path, voice_name=None):
    """Google Cloud Text-to-Speech (Chirp 3 HD). GOOGLE_TTS_API_KEY gerekir."""
    import urllib.request
    key = os.environ["GOOGLE_TTS_API_KEY"]
    name = voice_name or os.environ.get("GOOGLE_TTS_VOICE") or CHIRP_VOICE
    body = {
        "input": {"text": text},
        "voice": {"languageCode": "tr-TR", "name": name},
        "audioConfig": {"audioEncoding": "MP3"},
    }
    req = urllib.request.Request(
        "https://texttospeech.googleapis.com/v1/text:synthesize",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": key})
    with urllib.request.urlopen(req, timeout=60) as r:
        audio = json.load(r)["audioContent"]
    open(path, "wb").write(base64.b64decode(audio))
    chirp_count(len(text))
    open(path + ".chirp", "w").write(name)


# ---------------------------------------------------------------- Gemini TTS (ücretsiz, kartsız)
GEMINI_MODELS = ["gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"]
GEMINI_VOICE = "Puck"   # neşeli erkek; alternatif: "Fenrir" (heyecanlı), kadın: "Leda", "Aoede"
GEMINI_STYLE = ("Read the following Turkish text aloud as the narrator of a funny animated YouTube Shorts series "
                "called 'Ya Olsaydı?' (What if?). Sound like a real, warm, playful storyteller: expressive, curious, "
                "lively and slightly fast pace, dramatic at surprising moments, with good comedic timing. "
                "Ask the questions with genuine curiosity. Pronounce everything in native Turkish. "
                "Make a clear one-second pause between paragraphs. Only read the Turkish text, never read these instructions.")


def _gemini_request(text, voice):
    import time
    import urllib.error
    import urllib.request
    key = os.environ["GEMINI_API_KEY"]
    last = None
    for model in GEMINI_MODELS:
        for attempt in range(3):
            body = {"contents": [{"parts": [{"text": GEMINI_STYLE + "\n\n" + text}]}],
                    "generationConfig": {"responseModalities": ["AUDIO"],
                                         "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "x-goog-api-key": key})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    res = json.load(r)
                part = res["candidates"][0]["content"]["parts"][0]["inlineData"]
                pcm = np.frombuffer(base64.b64decode(part["data"]), dtype="<i2").astype(np.float32) / 32768
                rate = int(re.search(r"rate=(\d+)", part.get("mimeType", "")).group(1)) \
                    if "rate=" in part.get("mimeType", "") else 24000
                print("Gemini TTS modeli:", model)
                return pcm, rate
            except urllib.error.HTTPError as e:
                last = f"{model}: {e.code} {e.read().decode('utf-8', 'replace')[:300]}"
                if e.code == 429 and attempt < 2:
                    time.sleep(40)
                    continue
                break  # bu model olmadı, sıradakini dene
            except Exception as e:  # noqa
                last = f"{model}: {e}"
                break
    raise RuntimeError(last)


def _split_by_pauses(x, sr, texts):
    """Tek parça anlatımı segmentlere böler: her cümle/öbek (noktalama) sesteki bir durağa eşlenir,
    öbek süreleri hece sayılarına en iyi uyan durak dizisi seçilir (dinamik programlama)."""
    mask, n = speech_mask_sr(x, sr)
    regs = regions_sr(mask, n, sr, min_gap=0.12)
    phrases, seg_end = [], []
    for t in texts:
        cur = 0
        ws = t.split()
        for j, w in enumerate(ws):
            cur += syllables(w)
            if re.search(r"[,.:;!?…]$", w) or j == len(ws) - 1:
                phrases.append(cur); seg_end.append(j == len(ws) - 1); cur = 0
    if len(regs) < len(texts):
        raise RuntimeError("durak sayısı yetersiz")
    gaps = [((regs[i][1] + regs[i + 1][0]) / 2, regs[i + 1][0] - regs[i][1]) for i in range(len(regs) - 1)]
    pos = [regs[0][0]] + [g[0] for g in gaps] + [regs[-1][1]]   # olası öbek sınırları
    glen = [0.0] + [g[1] for g in gaps] + [0.0]
    P, M = len(phrases), len(pos)
    if M - 1 < len(texts):
        raise RuntimeError("durak sayısı yetersiz")
    rate = (pos[-1] - pos[0]) / sum(phrases)
    INF = 1e18
    # f[k][m]: ilk k öbek bitti, son sınır pos[m]. Öbekler birleştirilebilir (durak olmayabilir),
    # ama segment sonları mutlaka bir durağa denk gelmeli.
    f = np.full((P + 1, M), INF); bk = np.full((P + 1, M, 2), -1, int)
    f[0][0] = 0
    for k in range(P):
        for m in range(M):
            if f[k][m] >= INF:
                continue
            syl = 0
            for k2 in range(k, min(P, k + 4)):          # en fazla 4 öbek birleşebilir
                syl += phrases[k2]
                exp = syl * rate
                for m2 in range(m + 1, M):
                    d = pos[m2] - pos[m]
                    if d > exp * 2.2 + 1:
                        break
                    if k2 == P - 1 and m2 != M - 1:
                        continue
                    if any(seg_end[k:k2]):          # segment sonu birleştirilemez
                        continue
                    c = (d - exp) ** 2 / (exp + 0.3) - (0.6 if seg_end[k2] else 0.25) * glen[m2] \
                        + 0.15 * (k2 - k)
                    if f[k][m] + c < f[k2 + 1][m2]:
                        f[k2 + 1][m2] = f[k][m] + c; bk[k2 + 1][m2] = (k, m)
    if f[P][M - 1] >= INF:
        raise RuntimeError("bölme bulunamadı")
    k, m, ends = P, M - 1, []
    while k > 0:
        pk, pm = bk[k][m]
        if seg_end[k - 1]:
            ends.append(pos[m])
        k, m = pk, pm
    ends = sorted(ends)[:-1]
    b = [0.0, *ends, len(x) / sr]
    return [x[int(b[i] * sr):int(b[i + 1] * sr)] for i in range(len(texts))]


def speech_mask_sr(x, sr, thresh_db=-42, win=0.02):
    n = int(sr * win)
    m = len(x) // n
    rms = np.sqrt(np.mean(x[: m * n].reshape(m, n) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-12) > thresh_db, n


def regions_sr(mask, n, sr, min_gap):
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append([start, i]); start = None
    if start is not None:
        out.append([start, len(mask)])
    merged = []
    for r in out:
        if merged and (r[0] - merged[-1][1]) * n / sr < min_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [(a * n / sr, b * n / sr) for a, b in merged if (b - a) * n / sr > 0.06]


def synth_gemini_all(texts, paths, voice=None):
    """Bütün anlatımı TEK istekle seslendirir (ücretsiz katmanın günlük istek sınırı düşük), sonra böler."""
    import soundfile as sf
    voice = voice or os.environ.get("GEMINI_TTS_VOICE") or GEMINI_VOICE
    x, sr = _gemini_request("\n\n".join(texts), voice)
    dur = len(x) / sr
    expected = sum(syllables(w) for t in texts for w in t.split()) / 6.5
    if not (0.5 * expected < dur < 1.9 * expected):
        raise RuntimeError(f"ses süresi beklenmedik ({dur:.1f} sn, beklenen ~{expected:.1f} sn)")
    parts = _split_by_pauses(x, sr, texts)
    for y, p in zip(parts, paths):
        tmp = p + ".wav"
        sf.write(tmp, y, sr)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-b:a", "192k", p], check=True)
        os.remove(tmp)
        open(p + ".chirp", "w").write("gemini:" + voice)


EDGE_VOICE = "tr-TR-AhmetNeural"   # kadın ses için: tr-TR-EmelNeural


def synth_edge(text, path, voice=None, rate="+8%", pitch="+0Hz"):
    """Edge nöral TTS: mp3 + kelime sınırları (path + '.words.json')."""
    import asyncio
    import edge_tts

    async def run():
        kw = dict(rate=rate, pitch=pitch)
        try:
            com = edge_tts.Communicate(text, voice or EDGE_VOICE, boundary="WordBoundary", **kw)
        except TypeError:
            com = edge_tts.Communicate(text, voice or EDGE_VOICE, **kw)
        audio, words = bytearray(), []
        async for ch in com.stream():
            if ch["type"] == "audio":
                audio.extend(ch["data"])
            elif ch["type"] == "WordBoundary":
                t0 = ch["offset"] / 1e7
                words.append({"w": ch["text"], "t0": round(t0, 3), "t1": round(t0 + ch["duration"] / 1e7, 3)})
        if not audio:
            raise RuntimeError("Edge TTS ses döndürmedi")
        open(path, "wb").write(audio)
        json.dump(words, open(path + ".words.json", "w", encoding="utf-8"), ensure_ascii=False)
    asyncio.run(run())


def _edge_or_gtts(t, p, voice_cfg):
    try:
        synth_edge(t, p, voice_cfg.get("edge_voice"), voice_cfg.get("edge_rate", "+8%"),
                   voice_cfg.get("edge_pitch", "+0Hz"))
        return "edge"
    except Exception as e:  # noqa — ağ/servis sorunu: Google TTS'e düş
        print("Edge TTS başarısız, gTTS kullanılıyor:", e)
        synth_gtts(t, voice_cfg.get("lang", "tr"), p)
        return "gtts"


def fetch_segments(texts, cache_dir, voice_cfg):
    os.makedirs(cache_dir, exist_ok=True)
    engine = os.environ.get("TTS_ENGINE", voice_cfg.get("engine", "edge"))
    if engine == "gtts" and not voice_cfg.get("force_gtts"):
        engine = "edge"  # eski senaryolar da yeni sesi kullansın
    # Chirp 3 HD anahtarı varsa ve ayın ücretsiz kotası yetiyorsa bütün video onunla seslendirilir
    if os.environ.get("GOOGLE_TTS_API_KEY") and engine != "edge-only" and not voice_cfg.get("force_gtts"):
        if chirp_allowed(sum(len(t) for t in texts)):
            engine = "gcloud"
        else:
            print("Chirp aylık güvenlik sınırına ulaştı, bu ay Edge sesi kullanılıyor.")
    if engine != "gcloud" and os.environ.get("GEMINI_API_KEY") and engine != "edge-only" \
            and not voice_cfg.get("force_gtts"):
        engine = "gemini"
    print("Ses motoru:", engine)
    if engine == "gemini":
        paths = [os.path.join(cache_dir, f"seg{i:02d}.mp3") for i in range(len(texts))]
        tags = [f"gemini|{t}" for t in texts]
        cached = all(os.path.exists(p) and os.path.exists(p + ".txt")
                     and open(p + ".txt", encoding="utf-8").read() == tg for p, tg in zip(paths, tags))
        if not cached:
            try:
                for p in paths:
                    for ext in (".words.json", ".chirp"):
                        if os.path.exists(p + ext):
                            os.remove(p + ext)
                # uzun belgesel: istek başına en fazla 6 parça (çok uzun ses tek seferde kesilebilir)
                for a in range(0, len(texts), 6):
                    synth_gemini_all(texts[a:a + 6], paths[a:a + 6], voice_cfg.get("gemini_voice"))
                for p, tg in zip(paths, tags):
                    open(p + ".txt", "w", encoding="utf-8").write(tg)
            except Exception as e:  # noqa — sınır/servis sorunu: Edge'e düş
                print("Gemini TTS başarısız, Edge sesine geçiliyor:", e)
                return fetch_segments(texts, cache_dir, {**voice_cfg, "engine": "edge-only"})
        return paths
    paths = []
    for i, t in enumerate(texts):
        p = os.path.join(cache_dir, f"seg{i:02d}.mp3")
        meta = p + ".txt"
        tag = f"{engine}|{t}"
        if not (os.path.exists(p) and os.path.exists(meta) and open(meta, encoding="utf-8").read() in (t, tag)):
            if os.path.exists(p) and not os.path.exists(meta):
                pass  # önceden indirilmiş (ör. tarayıcıdan) dosya: olduğu gibi kullan
            else:
                for ext in (".words.json", ".chirp"):
                    if os.path.exists(p + ext):
                        os.remove(p + ext)
                if engine == "gcloud":
                    try:
                        synth_gcloud(t, voice_cfg.get("lang", "tr"), p, voice_cfg.get("gcloud_voice"))
                    except Exception as e:  # noqa — anahtar/kota/servis sorunu: Edge'e düş
                        print("Chirp 3 HD başarısız, Edge sesine geçiliyor:", e)
                        # tüm parçaları Edge ile baştan üret (videoda iki farklı ses olmasın)
                        return fetch_segments(texts, cache_dir, {**voice_cfg, "engine": "edge-only"})
                elif engine in ("edge", "edge-only"):
                    if _edge_or_gtts(t, p, voice_cfg) == "gtts":
                        engine = "gtts"
                else:
                    synth_gtts(t, voice_cfg.get("lang", "tr"), p)
            open(meta, "w", encoding="utf-8").write(tag)
        paths.append(p)
    return paths


# ---------------------------------------------------------------- ses işleme
def decode(path, tempo=1.0):
    af = f"atempo={tempo}" if abs(tempo - 1) > 1e-3 else "anull"
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-af", af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def speech_mask(x, thresh_db=-42, win=0.02):
    n = int(SR * win)
    m = len(x) // n
    rms = np.sqrt(np.mean(x[: m * n].reshape(m, n) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    return db > thresh_db, n


def regions(mask, n, min_gap=0.11):
    """Konuşma bölgeleri (saniye), min_gap'ten kısa sessizlikler birleştirilir."""
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append([start, i]); start = None
    if start is not None:
        out.append([start, len(mask)])
    merged = []
    for r in out:
        if merged and (r[0] - merged[-1][1]) * n / SR < min_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [(a * n / SR, b * n / SR) for a, b in merged if (b - a) * n / SR > 0.06]


def tighten(x, max_pause=0.13, pad=0.03):
    mask, n = speech_mask(x)
    regs = regions(mask, n, min_gap=0.05)
    if not regs:
        return x
    pieces = []
    for i, (a, b) in enumerate(regs):
        a = max(0, int((a - pad) * SR)); b = min(len(x), int((b + pad) * SR))
        pieces.append(x[a:b])
        if i < len(regs) - 1:
            gap = regs[i + 1][0] - regs[i][1]
            pieces.append(np.zeros(int(min(gap, max_pause) * SR), np.float32))
    y = np.concatenate(pieces)
    fade = int(0.008 * SR)
    y[:fade] *= np.linspace(0, 1, fade); y[-fade:] *= np.linspace(1, 0, fade)
    return y


def word_timings(text, x, offset):
    """Metni öbeklere böler, sesteki duraklarla eşler, kelimeye zaman verir."""
    words = text.split()
    phrases, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[,.:;!?]$", w):
            phrases.append(cur); cur = []
    if cur:
        phrases.append(cur)
    mask, n = speech_mask(x)
    regs = regions(mask, n, min_gap=0.09)
    # öbek sayısı kadar bölgeye indir: hece oranlarına en iyi uyan durak kombinasyonunu seç
    if len(regs) > len(phrases) and len(phrases) > 1:
        from itertools import combinations
        syl = np.array([sum(syllables(w) for w in p) for p in phrases], float)
        exp = syl / syl.sum()
        span = regs[-1][1] - regs[0][0]
        best, best_err = None, 1e9
        cands = list(range(1, len(regs)))
        if len(cands) <= 14:
            for cut in combinations(cands, len(phrases) - 1):
                b = [0, *cut, len(regs)]
                durs = np.array([regs[b[k + 1] - 1][1] - regs[b[k]][0] for k in range(len(phrases))])
                gapw = sum(regs[c][0] - regs[c - 1][1] for c in cut)  # uzun duraklar tercih edilir
                err = np.sum((durs / span - exp) ** 2) - 0.02 * gapw
                if err < best_err:
                    best, best_err = b, err
            regs = [(regs[best[k]][0], regs[best[k + 1] - 1][1]) for k in range(len(phrases))]
    while len(regs) > len(phrases):
        gaps = [regs[i + 1][0] - regs[i][1] for i in range(len(regs) - 1)]
        i = int(np.argmin(gaps))
        regs[i] = (regs[i][0], regs[i + 1][1]); del regs[i + 1]
    if len(regs) < len(phrases):  # eşleşmedi: tüm konuşmayı tek bölge say, hecelerle böl
        total = regs[0][0] if regs else 0, regs[-1][1] if regs else len(x) / SR
        syl = [sum(syllables(w) for w in p) + 1.5 for p in phrases]
        acc, regs = total[0], []
        span = total[1] - total[0]
        for s in syl:
            d = span * s / sum(syl); regs.append((acc, acc + d)); acc += d
    out = []
    for p, (a, b) in zip(phrases, regs):
        wts = [syllables(w) + 0.35 for w in p]
        acc = a
        for w, wt in zip(p, wts):
            d = (b - a) * wt / sum(wts)
            out.append({"w": w, "t0": round(offset + acc, 3), "t1": round(offset + acc + d, 3)})
            acc += d
    return out


def build_voice(texts, mp3s, tempo, gap, lead_in, out_wav):
    """Parçaları birleştirir. Döner: segment zamanları + kelime zamanları."""
    import soundfile as sf
    track, segs, words, t = [np.zeros(int(lead_in * SR), np.float32)], [], [], lead_in
    for i, (txt, p) in enumerate(zip(texts, mp3s)):
        wj = p + ".words.json"
        if os.path.exists(wj):  # nöral ses: tempo değiştirme, kelime zamanlarını aynen kullan
            y = decode(p, 1.0)
            mask, n = speech_mask(y)
            idx = np.nonzero(mask)[0]
            a = max(0, int(idx[0] * n - 0.03 * SR)) if len(idx) else 0
            b = min(len(y), int((idx[-1] + 1) * n + 0.06 * SR)) if len(idx) else len(y)
            y = y[a:b].copy()
            shift = a / SR
            bw = json.load(open(wj, encoding="utf-8"))
            toks = txt.split()
            if len(bw) == len(toks):
                ww = [{"w": tk, "t0": round(t + max(0, x["t0"] - shift), 3), "t1": round(t + max(0, x["t1"] - shift), 3)}
                      for tk, x in zip(toks, bw)]
            else:
                ww = word_timings(txt, y, t)
        else:
            tp = CHIRP_TEMPO if os.path.exists(p + ".chirp") else tempo
            y = tighten(decode(p, tp))
            ww = word_timings(txt, y, t)
        segs.append({"i": i, "t0": round(t, 3), "t1": round(t + len(y) / SR, 3)})
        words.append(ww)
        track.append(y)
        g = gap[i] if isinstance(gap, list) else gap
        track.append(np.zeros(int(g * SR), np.float32))
        t += len(y) / SR + g
    v = np.concatenate(track)
    v = v / (np.max(np.abs(v)) + 1e-9) * 0.89
    sf.write(out_wav, v, SR, subtype="FLOAT")
    return segs, words, len(v) / SR
