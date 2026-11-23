"""Senaryo şeması: izin verilen değerler + düzeltme (yapay zekâ hatalı alan yazsa da video bozulmasın)."""
import re

BG = ["night", "day", "sunset", "space", "city", "beach", "desert", "snow", "room", "forest", "red"]
PROPS = ["moon", "earth", "sun", "planet", "asteroid", "meteor", "rocket", "ufo", "alien", "city", "house", "building",
         "car", "plane", "tree", "mountain", "volcano", "cloud", "lightning", "fire", "phone", "laptop", "wifi", "clock",
         "calendar", "money", "lightbulb", "battery", "robot", "dino", "cat", "dog", "heart", "question", "exclamation",
         "text", "sign", "thermometer", "bed", "burger", "ice", "satellite", "arrow_up", "arrow_down", "book", "tv",
         "crowd", "person", "ghost", "water_drop", "star", "gift", "crown", "magnet"]
ANIMS = ["idle", "pop", "grow", "shrink", "approach", "fall", "rise", "fly", "fly_left", "spin", "shake", "float",
         "pulse", "fade", "orbit", "drain", "fill", "off", "break"]
POS = ["sky-left", "sky-center", "sky-right", "left", "center", "right", "ground-left", "ground-center",
       "ground-right", "far-left", "far-right"]
SIZES = ["xs", "s", "m", "l", "xl", "xxl"]
ACTIONS = ["stand", "happy", "shock", "point", "shrug", "sad", "think", "panic", "wave", "celebrate", "phone",
           "facepalm", "sit", "scared", "umbrella", "look_up", "cry", "angry", "sleep", "run", "walk", "run_left",
           "walk_left", "panic_run", "jump", "dance", "fall"]
HERO_POS = ["left", "center", "right", "far_left", "far_right"]
WEATHER = ["rain", "snow", "meteors", "confetti", "wind", "water_rise", "darkness", "heat", "fire", "ice"]
EMOTIONS = ["happy", "sad", "shocked", "scared", "angry", "sleepy", "confused"]
GROUNDED = {"house", "building", "tree", "mountain", "volcano", "car", "city", "bed", "sign", "dino", "cat", "dog",
            "robot", "alien", "crowd", "person", "fire", "rocket", "laptop", "tv", "thermometer", "burger", "ice",
            "gift", "crown"}
ALIAS = {"globe": "earth", "dinosaur": "dino", "computer": "laptop", "money_bag": "money", "coin": "money",
         "bulb": "lightbulb", "skyscraper": "building", "people": "crowd", "human": "person", "fireball": "meteor",
         "comet": "meteor", "saturn": "planet", "mars": "planet", "jupiter": "planet", "storm": "lightning",
         "water": "water_drop", "snowflake": "ice", "question_mark": "question", "warning": "exclamation",
         "television": "tv", "bomb": "fire", "explosion": "fire", "airplane": "plane", "spaceship": "rocket",
         "cactus": "tree", "kitten": "cat", "puppy": "dog", "hamburger": "burger", "food": "burger"}
TIER = {p: ("ground" if p.startswith(("ground", "far")) else "sky" if p.startswith("sky") else "mid") for p in POS}


def _pick(v, allowed, default):
    v = str(v or "").strip().lower().replace(" ", "_")
    v = v.replace("-", "_") if allowed is HERO_POS else v.replace("_", "-") if allowed is POS else v
    return v if v in allowed else default


def _scene(s, kind):
    s = dict(s or {})
    out = {"say": re.sub(r"\s+", " ", str(s.get("say", "")).strip())}
    out["bg"] = _pick(s.get("bg"), BG, "night")
    props = []
    for p in (s.get("props") or [])[:3]:
        if not isinstance(p, dict):
            continue
        t = str(p.get("type", "")).lower().strip()
        t = ALIAS.get(t, t)
        if t not in PROPS:
            continue
        q = {"type": t, "anim": _pick(p.get("anim"), ANIMS, "pop"), "size": _pick(p.get("size"), SIZES, "m"),
             "pos": _pick(p.get("pos"), POS, "ground-right" if t in GROUNDED else "sky-right")}
        for k in ("text", "color", "off", "level", "delay", "pose"):
            if p.get(k) not in (None, ""):
                q[k] = p[k]
        if "text" in q:
            q["text"] = str(q["text"])[:16]
        if "delay" in q:
            try:
                q["delay"] = max(0.0, min(3.0, float(q["delay"])))
            except (TypeError, ValueError):
                del q["delay"]
        props.append(q)
    # aynı konumdaki nesneleri ayır
    used = set()
    for q in props:
        if q["pos"] in used:
            free = [p for p in POS if TIER[p] == TIER[q["pos"]] and p not in used]
            if free:
                q["pos"] = free[0]
        used.add(q["pos"])
    out["props"] = props
    h = s.get("hero") if isinstance(s.get("hero"), dict) else {}
    hero = {"action": _pick(h.get("action"), ACTIONS, "shock" if kind == "hook" else "shrug" if kind == "outro" else "stand"),
            "pos": _pick(h.get("pos"), HERO_POS, "center")}
    if h.get("emotion") in EMOTIONS:
        hero["emotion"] = h["emotion"]
    if h.get("say"):
        hero["say"] = str(h["say"])[:28]
    if h.get("hidden"):
        hero["hidden"] = True
    # kahraman, ortadaki büyük nesnelerle çakışmasın
    big_mid = [q for q in props if q["pos"] in ("center", "ground-center") and q["size"] in ("m", "l", "xl", "xxl")]
    if hero["pos"] == "center" and big_mid and not hero.get("hidden") and out["bg"] != "space":
        hero["pos"] = "left" if not any(q["pos"] in ("left", "ground-left") for q in props) else "right"
    out["hero"] = hero
    f = s.get("friend")
    if isinstance(f, dict) and kind == "scene":
        fr = {"action": _pick(f.get("action"), ACTIONS, "stand"), "pos": _pick(f.get("pos"), HERO_POS, "right")}
        if f.get("say"):
            fr["say"] = str(f["say"])[:28]
        if fr["pos"] == hero["pos"]:
            fr["pos"] = "right" if hero["pos"] != "right" else "left"
        out["friend"] = fr
    w = _pick(s.get("weather"), WEATHER, None)
    if w:
        out["weather"] = w
    cam = str(s.get("camera", "")).lower()
    if cam in ("zoom", "zoom_out"):
        out["camera"] = cam
    if s.get("label"):
        out["label"] = str(s["label"])[:28]
    cn = s.get("counter")
    if isinstance(cn, dict):
        try:
            out["counter"] = {"from": float(cn.get("from", 0)), "to": float(cn["to"]),
                              "unit": str(cn.get("unit", ""))[:12], "label": str(cn.get("label", ""))[:24]}
        except (KeyError, TypeError, ValueError):
            pass
    ch = s.get("choices")
    if isinstance(ch, list) and len(ch) >= 2:
        out["choices"] = [str(c)[:40] for c in ch[:2]]
    return out


def normalize(d):
    """Senaryoyu doğrular ve eksik/hatalı alanları düzeltir. Ciddi sorun varsa ValueError."""
    if not isinstance(d, dict):
        raise ValueError("JSON nesnesi değil")
    raw_hook = d.get("hook") if isinstance(d.get("hook"), dict) else {}
    d["hook"] = _scene(raw_hook, "hook")
    d["hook"]["text"] = str(raw_hook.get("text") or d.get("title") or d["hook"]["say"])[:60]
    sc = [s for s in (d.get("scenes") or []) if isinstance(s, dict) and str(s.get("say", "")).strip()]
    if not 3 <= len(sc) <= 8:
        raise ValueError(f"sahne sayısı 3-8 olmalı ({len(sc)})")
    d["scenes"] = [_scene(s, "scene") for s in sc]
    o = d.get("outro") or {}
    d["outro"] = _scene(o, "outro")
    d["outro"]["question"] = str(o.get("question") or "SEN OLSAN NE YAPARDIN?")[:40]
    for part in [d["hook"], *d["scenes"], d["outro"]]:
        if not part["say"]:
            raise ValueError("boş anlatım")
    words = sum(len(p["say"].split()) for p in [d["hook"], *d["scenes"], d["outro"]])
    if not 55 <= words <= 135:
        raise ValueError(f"anlatım uzunluğu uygun değil ({words} kelime, hedef 75-110)")
    if len(d["hook"]["say"].split()) > 12:
        raise ValueError("kanca çok uzun")
    d.setdefault("title", d["hook"]["text"])
    d.setdefault("format", "bilim")
    m = d.get("meta") if isinstance(d.get("meta"), dict) else {}
    m.setdefault("title", f"{d['title']} #shorts")
    if "#shorts" not in m["title"].lower():
        m["title"] = m["title"][:90] + " #shorts"
    m.setdefault("caption", d["title"])
    tags = [t if t.startswith("#") else "#" + t for t in (m.get("hashtags") or []) if isinstance(t, str)]
    for t in ("#yaolsaydı", "#shorts"):
        if t not in [x.lower() for x in tags]:
            tags.append(t)
    m["hashtags"] = tags[:10]
    d["meta"] = m
    return d


def narration(d):
    return [d["hook"]["say"]] + [s["say"] for s in d["scenes"]] + [d["outro"]["say"]]
