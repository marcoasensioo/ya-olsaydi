"""Senaryo + ses zamanlamasından: sahne zamanları, altyazı öbekleri, ses efekti olayları, SRT."""
import re

SIZE_W = {"xs": .1, "s": .17, "m": .28, "l": .42, "xl": .62, "xxl": .85}


def caption_chunks(words, max_words=3, max_chars=20):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        txt = " ".join(x["w"] for x in cur)
        if len(cur) >= max_words or len(txt) >= max_chars or re.search(r"[,.:;!?…]$", w["w"]):
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        t1 = chunks[i + 1][0]["t0"] if i + 1 < len(chunks) else c[-1]["t1"] + 0.25
        t1 = min(t1, c[-1]["t1"] + 0.45)
        out.append({"t0": c[0]["t0"], "t1": round(t1, 3),
                    "words": [{"w": re.sub(r"[,.:;…]+$", "", x["w"]), "t0": x["t0"], "t1": x["t1"]} for x in c]})
    return out


def srt(chunks):
    def ts(t):
        h, r = divmod(t, 3600); m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    lines = []
    for i, c in enumerate(chunks, 1):
        lines += [str(i), f"{ts(c['t0'])} --> {ts(c['t1'])}", " ".join(w["w"] for w in c["words"]), ""]
    return "\n".join(lines)


def _scene_fx(sc, s0, D, events):
    """Sahnedeki nesne animasyonlarına göre ses efekti + sarsıntı/flaş zamanları."""
    shakes, flashes = [], []
    for p in sc.get("props", []):
        a, d0 = p.get("anim", "pop"), p.get("delay", 0)
        t = s0 + d0
        if a in ("pop", "spin", "pulse", "float", "shake", "drain", "fill"):
            events.append({"t": t + .05, "type": "pop", "gain": .45, "args": {"pitch": 1.1}})
        if a == "shake":
            events.append({"t": t + .1, "type": "impact", "gain": .4})
        elif a == "fall":
            hit = min(1.2, D * .4)
            events += [{"t": t, "type": "whoosh", "gain": .6}, {"t": t + hit, "type": "impact", "gain": .9}]
            shakes.append(d0 + hit)
        elif a == "approach":
            events.append({"t": t, "type": "riser", "gain": .55, "args": {"d": round(max(1.0, min(3.5, D * .85)), 2)}})
        elif a == "break":
            bt = D * .45
            events += [{"t": t + max(0, bt - 1.3), "type": "riser", "gain": .6, "args": {"d": 1.3}},
                       {"t": t + bt, "type": "boom", "gain": 1.0}, {"t": t + bt + .02, "type": "impact", "gain": .9}]
            shakes.append(d0 + bt); flashes.append(d0 + bt)
        elif a in ("fly", "fly_left"):
            events.append({"t": t + D * .35, "type": "whoosh", "gain": .7})
        elif a == "grow":
            events.append({"t": t + D * .8, "type": "shimmer", "gain": .4, "args": {"base": 660}})
        elif a == "off":
            events.append({"t": t + D * .4, "type": "impact", "gain": .6})
        if p["type"] == "lightning":
            events.append({"t": t + .1, "type": "boom", "gain": .6}); flashes.append(d0 + .1)
    w = sc.get("weather")
    if w == "meteors":
        events += [{"t": s0 + .4 + i * .9, "type": "whoosh", "gain": .45, "args": {"up": i % 2 == 0}} for i in range(int(D / .9))]
    elif w == "water_rise":
        events.append({"t": s0 + .3, "type": "riser", "gain": .5, "args": {"d": round(max(1.0, D * .8), 2)}})
    elif w == "confetti":
        events += [{"t": s0 + .1, "type": "shimmer", "gain": .6, "args": {"base": 990}}, {"t": s0 + .15, "type": "pop", "gain": .6}]
    elif w == "darkness":
        events.append({"t": s0 + .2, "type": "impact", "gain": .5})
    act = sc.get("hero", {}).get("action")
    if act in ("shock", "jump", "celebrate"):
        events.append({"t": s0 + .08, "type": "pop", "gain": .5, "args": {"pitch": 1.3}})
    if act == "fall":
        events.append({"t": s0 + .5, "type": "impact", "gain": .6}); shakes.append(.5)
    cn = sc.get("counter")
    if cn:
        c0, c1 = s0 + .2, s0 + max(.8, D * .7)
        for j in range(14):
            u = j / 14
            events.append({"t": c0 + (c1 - c0) * (1 - (1 - u) ** 2), "type": "tick", "gain": .3, "args": {"pitch": round(.9 + .4 * u, 2)}})
        events.append({"t": c1, "type": "shimmer", "gain": .5, "args": {"base": 880}})
    if sc.get("label"):
        events.append({"t": s0 + .15, "type": "pop", "gain": .35, "args": {"pitch": 1.0}})
    if sc.get("choices"):
        events += [{"t": s0 + .1, "type": "pop", "gain": .5}, {"t": s0 + .35, "type": "pop", "gain": .5, "args": {"pitch": 1.2}}]
    return shakes, flashes


def build(spec, segs, words, channel="YA OLSAYDI?"):
    sc = spec["scenes"]
    n = len(sc)
    LEAD = 0.2
    starts = [segs[k + 1]["t0"] - LEAD for k in range(n)]
    outro_start = segs[n + 1]["t0"] - LEAD
    end = segs[n + 1]["t1"] + 1.4
    hook = dict(spec["hook"], kind="hook", t0=0.0, t1=starts[0], title=spec["hook"]["text"])
    events = [{"t": 0.0, "type": "impact", "gain": .8}, {"t": .12, "type": "pop", "gain": .6, "args": {"pitch": 1.2}},
              {"t": .3, "type": "whoosh", "gain": .4}]
    hook["shakes"], hook["flashes"] = _scene_fx(hook, 0.0, starts[0], events)
    scenes = [hook]
    for k, s in enumerate(sc):
        s0, s1 = starts[k], (starts[k + 1] if k + 1 < n else outro_start)
        ent = dict(s, kind="scene", t0=round(s0, 3), t1=round(s1, 3))
        events += [{"t": s0 - .3, "type": "whoosh", "gain": .55, "args": {"up": k % 2 == 0}}]
        ent["shakes"], ent["flashes"] = _scene_fx(s, s0, s1 - s0, events)
        scenes.append(ent)
    outro = dict(spec["outro"], kind="outro", t0=round(outro_start, 3), t1=round(end, 3))
    events += [{"t": outro_start - .3, "type": "whoosh", "gain": .6}, {"t": outro_start + .12, "type": "pop", "gain": .5},
               {"t": outro_start + 1.0, "type": "pop", "gain": .45, "args": {"pitch": 1.2}},
               {"t": outro_start + 1.1, "type": "shimmer", "gain": .45, "args": {"base": 990}}]
    outro["shakes"], outro["flashes"] = _scene_fx(outro, outro_start, end - outro_start, events)
    scenes.append(outro)

    def intensity(t):
        if t < starts[0]:
            return .45
        if t >= outro_start:
            return max(0.0, .45 - (t - outro_start) * .12)
        k = max(i for i in range(n) if starts[i] <= t)
        return min(1.0, .35 + .5 * k / max(1, n - 1))

    chunks = []
    for w in words:
        chunks += caption_chunks(w)
    tl = {"fps": 30, "W": 1080, "H": 1920, "duration": round(end, 3), "channel": channel,
          "title": spec["title"], "scenes": scenes, "captions": chunks}
    return tl, [e for e in events if e["t"] >= 0], intensity, end
