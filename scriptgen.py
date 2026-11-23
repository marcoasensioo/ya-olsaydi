#!/usr/bin/env python3
"""Yeni "Ya Olsaydı?" senaryosu yazar → topics/<id>.json

Sıra: topics_queue.txt'deki ilk konu. Kuyruk boşsa yapay zekâ konuyu kendisi seçer (eski konuları tekrarlamaz).
Yapay zekâ: Gemini (ücretsiz, GEMINI_API_KEY) → olmazsa GitHub Models (Actions içinde ücretsiz).
Kullanım:
  python scriptgen.py                         # kuyruktan/otomatik
  python scriptgen.py "bilim: Ya güneş sönseydi?"
"""
import datetime
import glob
import gzip
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "engine"))
import spec as specmod  # noqa: E402

QUEUE = os.path.join(ROOT, "topics_queue.txt")
DONE = os.path.join(ROOT, "state", "done.json")
MODELS = [m for m in [os.environ.get("GEMINI_TEXT_MODEL"), "gemini-flash-latest", "gemini-2.5-flash",
                      "gemini-2.5-flash-lite"] if m]
FORMATS = ["bilim", "hikaye", "bilim", "secim", "bilim", "hikaye", "bilim"]

FORMAT_TARIF = {
    "bilim": ("BİLİM 'YA OLSAYDI': Gerçek bilimsel/tarihsel bir 'ya şöyle olsaydı' senaryosu. Adım adım ne olacağını "
              "anlat (önce, sonra, en sonunda...). Bilgiler bilim insanlarının genel kabulüne uygun olmalı; emin "
              "olmadığın kesin rakam verme, rakam verirsen çok bilinen ve doğru olsun. Esprili bir dil kullan."),
    "hikaye": ("KOMİK MİNİ HİKÂYE: Çöp adam kahramanımızın başından geçen kısa, komik, sürprizli bir 'ya olsaydı' "
               "hikâyesi (ör. 'Ya bir sabah kedin konuşmaya başlasaydı?'). Gerekirse arkadaşı (friend) da sahnede olsun, "
               "kısa konuşma balonları (hero.say / friend.say, en fazla 4 kelime) kullan. Sonunda beklenmedik bir espri olsun."),
    "secim": ("SEÇİM ('Hangisini seçerdin?'): Kanca 'Ya sadece birini seçebilseydin?' tarzında. 1. sahnede iki seçenek "
              "'choices' ile gösterilir (A ve B, kısa). Sonraki sahnelerde önce A'nın, sonra B'nin komik/şaşırtıcı "
              "sonuçları anlatılır. Kapanış: 'Sen olsan hangisini seçerdin? A mı, B mi?'"),
}

PROMPT = """Sen "Ya Olsaydı?" adlı Türkçe YouTube Shorts / Instagram Reels animasyon kanalının baş senaristisin.
Videolarda kendi özgün çöp adam karakterimiz var (beyaz çizgi adam). Telifli karakter, marka, ünlü kişi YOK.

Bu videonun türü: {tarif}
Konu: {konu}

KURALLAR
- Dil: doğal, akıcı, esprili Türkçe; 12-16 yaş üstü herkese uygun. Korkutucu/kanlı/siyasi/dini içerik yok.
- hook.say: İLK 2 SANİYE. Merak uyandıran tek bir "Ya ... olsaydı?" sorusu, en fazla 7 kelime.
- hook.text: ekranda yazacak başlık (hook.say ile aynı ya da daha kısa).
- scenes: 4-6 sahne. Her sahnenin "say" metni 1-2 kısa cümle (10-20 kelime).
- outro.say: izleyiciye "Sen olsan ne yapardın?" (seçim türünde "Sen olsan hangisini seçerdin?") diye soran 1-2 cümle + "Yorumlara yaz!".
- outro.question: ekranda yazacak kısa soru (en fazla 30 harf).
- TOPLAM anlatım 80-105 kelime (30-45 saniye). Rakamları yazıyla değil rakamla yazabilirsin ama az kullan.
- Her sahne farklı görünsün: arka planı (bg), nesneleri ve kahramanın hareketini anlatılana uygun ve çeşitli seç.

GÖRSEL ALANLAR (sadece bu değerler, İngilizce yaz):
- bg: {bg}
- props: en fazla 3 nesne. type: {props}
  anim: {anims}
  ("break" = nesne çatlar ve parçalanır; "off" = ışığı/ekranı söner; "drain"/"fill" = pil/termometre azalır/dolar;
   "approach" = uzaktan yaklaşır; "fall" = yukarıdan düşer; "fly" = ekranı soldan sağa geçer)
  pos: {pos}  (sky-* gökyüzü, ground-* yerde, left/center/right ortada havada)
  size: {sizes}
  isteğe bağlı: "text" (tabela/takvim/telefon/yazı nesnesinde en fazla 12 harf), "color" (#rrggbb), "delay" (sn).
- hero (çöp adam): action: {actions}
  pos: {hero_pos}; isteğe bağlı "say" (konuşma balonu, en fazla 4 kelime), "emotion": {emotions}, "hidden": true.
- friend (isteğe bağlı ikinci karakter, mavi şapkalı arkadaş): action, pos, say.
- weather (isteğe bağlı): {weather}
- label (isteğe bağlı): ekranda kısa etiket, ör. "1. GÜN", "10 YIL SONRA" (en fazla 20 harf).
- counter (isteğe bağlı): sayaç, {{"from": 0, "to": 50, "unit": "m", "label": "DALGA"}} — anlatımla tutarlı olmalı.
- choices (sadece seçim türünde, bir sahnede): ["A seçeneği", "B seçeneği"].
- camera (isteğe bağlı): "zoom" ya da "zoom_out".
- Kahraman ile büyük nesneler aynı konumda olmasın (ör. kahraman "left", nesne "ground-right").

META
- meta.title: merak uyandıran YouTube başlığı, en fazla 60 harf, 1 emoji, sonunda #shorts.
- meta.caption: 1-2 cümlelik açıklama (emoji serbest).
- meta.hashtags: 6-8 Türkçe etiket (#yaolsaydı dahil).
- meta.comment: videonun altına kanal olarak yazılacak, izleyiciyi yoruma çağıran 1-2 cümle + emoji.
- id: Türkçe karaktersiz kebab-case. title: Türkçe başlık.

{kacin}
Aşağıdaki örnekle AYNI şemada, sadece geçerli JSON döndür (örneğin konusunu ve cümlelerini kopyalama):
{ornek}
"""


def slug(s):
    s = s.replace("ı", "i").replace("İ", "i")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


def ask_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY yok")
    last = None
    for model in MODELS:
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.95, "responseMimeType": "application/json"}}
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                txt = json.load(r)["candidates"][0]["content"]["parts"][0]["text"]
            print("Senaryo modeli: Gemini", model)
            return txt
        except (urllib.error.HTTPError, KeyError, IndexError, ValueError, OSError) as e:
            last = f"{model}: {getattr(e, 'code', '')} {str(e)[:200]}"
    raise RuntimeError(last)


def ask_github_models(prompt):
    if not os.environ.get("GITHUB_TOKEN"):
        raise RuntimeError("GITHUB_TOKEN yok")
    errors = []
    for model in [os.environ.get("GH_MODEL"), "openai/gpt-4.1", "openai/gpt-4o", "openai/gpt-4.1-mini"]:
        if not model:
            continue
        req = urllib.request.Request(
            "https://models.github.ai/inference/chat/completions",
            data=json.dumps({"model": model, "temperature": 0.9, "max_tokens": 4000,
                             "response_format": {"type": "json_object"},
                             "messages": [{"role": "user", "content": prompt}]}).encode(),
            headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json",
                     "Accept-Encoding": "identity", "User-Agent": "ya-olsaydi"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            print("Senaryo modeli: GitHub", model)
            return json.loads(raw)["choices"][0]["message"]["content"]
        except Exception as e:  # noqa
            errors.append(f"{model}: {str(e)[:150]}")
    raise RuntimeError(" | ".join(errors))


def ask(prompt):
    try:
        return ask_gemini(prompt)
    except Exception as e:  # noqa
        print("Gemini olmadı, GitHub Models deneniyor:", e)
        return ask_github_models(prompt)


def used_titles():
    titles = []
    for p in glob.glob(os.path.join(ROOT, "topics", "*.json")):
        try:
            titles.append(json.load(open(p, encoding="utf-8")).get("title", ""))
        except Exception:  # noqa
            pass
    if os.path.exists(DONE):
        titles += [d for d in json.load(open(DONE)) if isinstance(d, str)]
    return [t for t in titles if t][-80:]


def generate(line=None):
    done_n = len(glob.glob(os.path.join(ROOT, "topics", "*.json")))
    fmt = FORMATS[done_n % len(FORMATS)]
    konu = None
    if line:
        m = re.match(r"\s*(bilim|hikaye|hikâye|secim|seçim)\s*:\s*(.+)", line, re.I)
        if m:
            fmt = {"hikâye": "hikaye", "seçim": "secim"}.get(m.group(1).lower(), m.group(1).lower())
            konu = m.group(2).strip()
        else:
            konu = line.strip()
    eski = used_titles()
    kacin = ("Daha önce yapılan videolar (bunları ve çok benzerlerini TEKRARLAMA):\n- " + "\n- ".join(eski)) if eski else ""
    ornek = json.load(open(sorted(glob.glob(os.path.join(ROOT, "ornek", "*.json")))[0], encoding="utf-8"))
    prompt = PROMPT.format(
        tarif=FORMAT_TARIF[fmt], konu=konu or "KENDİN SEÇ: viral olabilecek, merak uyandıran, özgün bir konu bul.",
        bg=", ".join(specmod.BG), props=", ".join(specmod.PROPS), anims=", ".join(specmod.ANIMS),
        pos=", ".join(specmod.POS), sizes=", ".join(specmod.SIZES), actions=", ".join(specmod.ACTIONS),
        hero_pos=", ".join(specmod.HERO_POS), emotions=", ".join(specmod.EMOTIONS), weather=", ".join(specmod.WEATHER),
        kacin=kacin, ornek=json.dumps(ornek, ensure_ascii=False))
    for attempt in range(3):
        try:
            txt = ask(prompt)
            m = re.search(r"\{.*\}", txt, re.S)
            d = specmod.normalize(json.loads(m.group()))
            d["format"] = fmt
            d["id"] = f"{datetime.date.today():%Y%m%d}-{slug(d.get('id') or d['title'])}"
            path = os.path.join(ROOT, "topics", f"{d['id']}.json")
            json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("Yeni senaryo:", d["title"], "→", path)
            return path
        except Exception as e:  # noqa
            print(f"deneme {attempt + 1} geçersiz: {e}")
            prompt += f"\n\nÖNCEKİ DENEMEDE HATA: {e}. Kurallara tam uy."
    raise SystemExit("Geçerli senaryo üretilemedi.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(generate(" ".join(sys.argv[1:])))
        sys.exit(0)
    lines = [l for l in open(QUEUE, encoding="utf-8").read().splitlines()
             if l.strip() and not l.lstrip().startswith("#")] if os.path.exists(QUEUE) else []
    if lines:
        path = generate(lines[0])
        rest = [l for l in open(QUEUE, encoding="utf-8").read().splitlines() if l != lines[0]]
        open(QUEUE, "w", encoding="utf-8").write("\n".join(rest) + "\n")
    else:
        path = generate(None)
    print(path)
