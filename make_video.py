#!/usr/bin/env python3
"""Ya Olsaydı? — senaryo dosyasından (topics/<id>.json) yayına hazır dikey video.

Kullanım:
  python make_video.py topics/ay-dunyaya-carpsaydi.json
  python make_video.py topics/x.json --snap 1 6 12     # sadece kontrol kareleri
  TTS_ENGINE=sessiz python make_video.py ...           # seslendirmesiz deneme
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "engine"))
import render  # noqa: E402
import sfx  # noqa: E402
import spec as specmod  # noqa: E402
import timeline  # noqa: E402
import voice  # noqa: E402

CHANNEL = os.environ.get("KANAL_ADI") or "Ya Olsaydı?"


def log(*a):
    print(*a, flush=True)


def silent_voice(texts, out_wav, lead=0.25, gap=0.22):
    """Ses servisi olmadan deneme: hece sayısına göre süre, sessiz ses."""
    segs, words, t = [], [], lead
    for i, txt in enumerate(texts):
        ws = txt.split()
        syl = [voice.syllables(w) + .35 for w in ws]
        dur = sum(syl) / 6.0
        acc, ww = t, []
        for w, s in zip(ws, syl):
            d = dur * s / sum(syl)
            ww.append({"w": w, "t0": round(acc, 3), "t1": round(acc + d, 3)}); acc += d
        segs.append({"i": i, "t0": round(t, 3), "t1": round(t + dur, 3)}); words.append(ww)
        t += dur + gap
    sf.write(out_wav, np.zeros(int(t * voice.SR), np.float32), voice.SR, subtype="FLOAT")
    return segs, words, t


def make(spec_path, snap=None, workers=2):
    spec = specmod.normalize(json.load(open(spec_path, encoding="utf-8")))
    vid = spec["id"]
    cache = os.path.join(ROOT, "cache", vid)
    outdir = os.path.join(ROOT, "out", vid)
    os.makedirs(outdir, exist_ok=True); os.makedirs(cache, exist_ok=True)
    texts = specmod.narration(spec)

    log("1/5 Seslendirme…")
    voice_wav = os.path.join(cache, "voice.wav")
    if os.environ.get("TTS_ENGINE") == "sessiz":
        segs, words, vdur = silent_voice(texts, voice_wav)
    else:
        mp3s = voice.fetch_segments(texts, os.path.join(cache, "tts"), spec.get("voice", {}))
        segs, words, vdur = voice.build_voice(texts, mp3s, 1.15, 0.2, 0.25, voice_wav)

    log("2/5 Zaman çizelgesi + altyazı…")
    tl, events, intensity, T = timeline.build(spec, segs, words, CHANNEL)
    tl_path = os.path.join(cache, "timeline.json")
    json.dump(tl, open(tl_path, "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(outdir, f"{vid}.srt"), "w", encoding="utf-8").write(timeline.srt(tl["captions"]))
    log(f"   süre: {T:.1f} sn, {len(tl['scenes'])} sahne")

    if snap:
        return render.snapshot(tl_path, snap, os.path.join(cache, "snaps"))

    log("3/5 Ses tasarımı…")
    v, _ = sf.read(voice_wav, dtype="float32")
    mix = sfx.mix(v, T, events, intensity)
    mix_wav = os.path.join(cache, "mix.wav")
    sf.write(mix_wav, mix, sfx.SR, subtype="FLOAT")
    aac = os.path.join(cache, "mix.m4a")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mix_wav, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ar", "48000", "-c:a", "aac", "-b:a", "192k", aac], check=True)

    log("4/5 Animasyon çizimi…")
    cuts = [(s["t0"] + s["t1"]) / 2 for s in tl["scenes"]]
    silent = render.render_video(tl_path, T, tl["fps"], os.path.join(cache, "frames"), workers=workers,
                                 cut_points=cuts, log=log)

    log("5/5 Birleştirme…")
    final = os.path.join(outdir, f"{vid}.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", aac, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", final], check=True)
    meta = spec["meta"]
    open(os.path.join(outdir, "paylasim.txt"), "w", encoding="utf-8").write(
        f"{meta['title']}\n\n{meta.get('caption', '')}\n\n{' '.join(meta['hashtags'])}\n")
    log(f"Hazır: {final}")
    return final


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--snap", nargs="*", type=float)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    a = ap.parse_args()
    make(a.spec, a.snap, a.workers)
