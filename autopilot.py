#!/usr/bin/env python3
"""Tam otomatik döngü (GitHub Actions'ta çalışır):
bekleyen senaryo yoksa yapay zekâ yazar → video üretilir → GitHub Release → YouTube → Instagram (Reels + Hikâye).
ONIZLEME=1 ise sadece video üretilir (hiçbir yere yüklenmez, Actions'tan indirilebilir).
"""
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "engine"))
import make_video  # noqa: E402

STATE = os.path.join(ROOT, "state", "done.json")
done = json.load(open(STATE)) if os.path.exists(STATE) else []
ONIZLEME = os.environ.get("ONIZLEME") == "1"


def pending():
    for p in sorted(glob.glob(os.path.join(ROOT, "topics", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        if d["id"] not in done:
            return p


def build_comment(d):
    meta = d.get("meta", {})
    if meta.get("comment"):
        return meta["comment"]
    soru = d.get("outro", {}).get("question") or "Sen olsan ne yapardın?"
    return f"💭 {soru}\n\n👇 Cevabını yorumlara yaz! Bir sonraki 'Ya olsaydı?' konusu ne olsun? Önerini bırak."


def ig_caption(d):
    meta = d.get("meta", {})
    tags = [t for t in meta.get("hashtags", []) if t.lower() not in ("#shorts", "#short")]
    tags = (tags + ["#reels"])[:6]
    soru = d.get("outro", {}).get("question") or "Sen olsan ne yapardın?"
    return "\n\n".join([meta.get("caption") or d["title"], f"💬 {soru} Yorumlara yaz!",
                        "🔔 Her gün yeni bir 'Ya olsaydı?' için takip et.", " ".join(tags)])


spec = pending()
if not spec:
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scriptgen.py")], text=True)
    spec = pending()
    if not spec:
        sys.exit("Yeni senaryo üretilemedi (Gemini/GitHub Models hatası). Ayrıntı yukarıda.")

d = json.load(open(spec, encoding="utf-8"))
print("Konu:", d["title"])
video = make_video.make(spec)
if ONIZLEME:
    sys.exit(print("Önizleme modu: video üretildi, yükleme yapılmadı.") or 0)

d = make_video.specmod.normalize(d)
meta = d["meta"]
title = meta["title"]
desc = f"{meta.get('caption', d['title'])}\n\n{' '.join(meta['hashtags'])}"
srt = video[:-4] + ".srt"

if os.environ.get("GITHUB_ACTIONS"):
    subprocess.run(["gh", "release", "create", d["id"], video, srt, "--title", d["title"], "--notes", desc], check=False)

if os.environ.get("YT_UPLOAD") == "1" and os.environ.get("YT_REFRESH_TOKEN"):
    try:
        import youtube
        vid = youtube.upload(video, title, desc, [h.lstrip("#") for h in meta["hashtags"]])
        print("YouTube:", f"https://youtube.com/shorts/{vid}")
        if os.environ.get("YT_COMMENT", "1") != "0":
            try:
                print("Yorum yazildi:", youtube.comment(vid, build_comment(d)))
            except Exception as e:  # noqa
                print("UYARI - yorum yazilamadi:", e)
        if os.environ.get("YT_CAPTION", "1") != "0" and os.path.exists(srt):
            try:
                print("Altyazi yuklendi:", youtube.caption(vid, srt))
            except Exception as e:  # noqa
                print("UYARI - altyazi yuklenemedi:", e)
    except Exception as e:  # YouTube hatası Instagram'ı engellemesin
        print("HATA - YouTube'a yuklenemedi:", e)
else:
    print("YouTube yüklemesi kapalı (YT_UPLOAD=1 değil ya da YT_REFRESH_TOKEN yok).")

if os.environ.get("IG_TOKEN") and os.environ.get("IG_UPLOAD", "1") != "0" and os.environ.get("GITHUB_ACTIONS"):
    try:
        import instagram
        ig_id = instagram.publish_reel(video, ig_caption(d), d["id"])
        print("Instagram:", ig_id)
        if os.environ.get("IG_COMMENT", "1") != "0":
            try:
                print("Instagram yorum:", instagram.comment(ig_id, build_comment(d)))
            except Exception as e:  # noqa
                print("UYARI - Instagram yorumu yazilamadi:", e)
        if os.environ.get("IG_STORY", "1") != "0":
            try:
                print("Instagram hikaye:", instagram.publish_story(video, d["id"]))
            except Exception as e:  # noqa
                print("UYARI - Instagram hikayesi paylasilamadi:", e)
    except Exception as e:  # noqa
        print("UYARI - Instagram'a yuklenemedi:", e)

done += [d["id"], d["title"]]
os.makedirs(os.path.dirname(STATE), exist_ok=True)
json.dump(done, open(STATE, "w"), indent=1, ensure_ascii=False)
