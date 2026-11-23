#!/usr/bin/env python3
"""Instagram'daki yeni yorumlara Gemini (ücretsiz) ile kısa, konuya uygun cevap yazar.
- Son 10 gönderinin yorumlarını okur; daha önce cevaplananları ve kendi yorumlarımızı atlar.
- Bağlantı/reklam/hakaret içeren ya da anlamsız yorumları atlar.
- Tüm yorumlar TEK Gemini isteğiyle cevaplanır (ücretsiz kota az harcanır).
- Günlük üst sınır: IG_CEVAP_LIMIT (varsayılan 20). Kapatmak için IG_CEVAP=0.
"""
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "engine"))
STATE = os.path.join(ROOT, "state", "cevaplanan.json")
LIMIT = int(os.environ.get("IG_CEVAP_LIMIT") or 20)
MODELS = [m for m in [os.environ.get("GEMINI_TEXT_MODEL"), "gemini-flash-latest", "gemini-2.5-flash",
                      "gemini-2.5-flash-lite"] if m]
KOTU = re.compile(r"(https?://|www\.|\.com\b|t\.me|dm at|takip et.*takip|kazan[cç]|bahis|bet\b|casino|kripto)", re.I)

if os.environ.get("IG_CEVAP", "1") == "0" or not os.environ.get("IG_TOKEN") or not os.environ.get("GEMINI_API_KEY"):
    sys.exit(print("Yorum cevaplama kapali (IG_CEVAP=0 ya da IG_TOKEN/GEMINI_API_KEY yok).") or 0)
import instagram  # noqa: E402

st = json.load(open(STATE)) if os.path.exists(STATE) else {"ids": [], "gun": {}}
bugun = datetime.date.today().isoformat()
kalan = LIMIT - st["gun"].get(bugun, 0)
if kalan <= 0:
    sys.exit(print("Bugunku cevap siniri doldu.") or 0)

ben = instagram.username().lower()
adaylar = []
for m in instagram.recent_media(10):
    konu = (m.get("caption") or "").split("\n")[0][:200]
    for c in instagram.comments(m["id"]):
        metin = (c.get("text") or "").strip()
        if c["id"] in st["ids"] or (c.get("username") or "").lower() == ben:
            continue
        if any((r.get("username") or "").lower() == ben for r in (c.get("replies") or {}).get("data", [])):
            st["ids"].append(c["id"])
            continue
        if len(re.sub(r"\W", "", metin)) < 2 or KOTU.search(metin) or metin.count("@") > 2:
            st["ids"].append(c["id"])  # spam/boş: bir daha bakma
            continue
        adaylar.append({"id": c["id"], "konu": konu, "yorum": metin[:400], "kisi": c.get("username", "")})
adaylar = adaylar[:kalan]
print("Cevaplanacak yorum:", len(adaylar))


def gemini(prompt):
    son = None
    for model in MODELS:
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"}}
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                out = json.load(r)["candidates"][0]["content"]["parts"][0]["text"]
            print("Gemini modeli:", model)
            return json.loads(out)
        except (urllib.error.HTTPError, KeyError, ValueError) as e:
            son = f"{model}: {getattr(e, 'code', '')} {e}"
    raise RuntimeError(son)


if adaylar:
    prompt = (
        "Sen 'Ya Olsaydı?' adlı, çöp adam karakterli Türkçe 'ya şöyle olsaydı' animasyon kanalının esprili ve samimi yöneticisisin. Aşağıdaki Instagram "
        "yorumlarına cevap yaz.\nKurallar:\n"
        "- Her cevap Türkçe, en fazla 2 kısa cümle, sıcak ve doğal olsun; uygunsa 1 emoji kullan.\n"
        "- Sadece videonun konusuyla ilgili konuş. Emin olmadığın bilgi, rakam ya da tıbbi/hukuki tavsiye verme.\n"
        "- Soru soran olursa kısaca cevapla; bilmiyorsan 'güzel soru, belki ayrı bir video yaparız' de.\n"
        "- Konu önerisi gelirse teşekkür et. Övgüye teşekkür et.\n"
        "- Hakaret, siyaset, din tartışması, kişisel bilgi, cinsellik ya da anlamsız yorumlarda cevap yerine \"ATLA\" yaz.\n"
        "- Kişinin kullanıcı adını yazma, @ kullanma, bağlantı verme.\n"
        'Çıktı: {"cevaplar": [{"id": "...", "cevap": "..."}]} biçiminde JSON.\n\nYorumlar:\n'
        + json.dumps([{k: a[k] for k in ("id", "konu", "yorum")} for a in adaylar], ensure_ascii=False))
    try:
        sonuc = {x["id"]: x.get("cevap", "").strip() for x in gemini(prompt).get("cevaplar", [])}
    except Exception as e:  # noqa
        sys.exit(print("UYARI - Gemini cevap uretemedi:", e) or 0)
    for a in adaylar:
        cevap = sonuc.get(a["id"], "")
        st["ids"].append(a["id"])
        if not cevap or cevap.upper().startswith("ATLA") or KOTU.search(cevap):
            print("Atlandi:", a["yorum"][:60])
            continue
        try:
            instagram.reply(a["id"], cevap[:300])
            st["gun"][bugun] = st["gun"].get(bugun, 0) + 1
            print(f"Cevaplandi: {a['yorum'][:60]!r} -> {cevap!r}")
        except Exception as e:  # noqa
            print("UYARI - cevap yazilamadi:", e)

st["ids"] = st["ids"][-3000:]
st["gun"] = {k: v for k, v in st["gun"].items() if k >= (datetime.date.today() - datetime.timedelta(days=7)).isoformat()}
os.makedirs(os.path.dirname(STATE), exist_ok=True)
json.dump(st, open(STATE, "w"), indent=1)
