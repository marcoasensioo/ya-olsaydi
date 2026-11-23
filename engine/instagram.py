"""Instagram Reels'e yükleme (Instagram API with Instagram Login — Facebook sayfası gerekmez).
Video, GitHub Release'teki herkese açık bağlantısından Instagram tarafından indirilir.

Gerekenler (GitHub Secrets):
  IG_TOKEN  : Meta panelindeki "Unified login" yapılandırmasından alınan sistem kullanıcısı anahtarı (süresiz).
              Eski "Instagram ile giriş" anahtarları (60 gün) da desteklenir.
İsteğe bağlı (Variables):
  IG_UPLOAD    : "0" yazılırsa Instagram'a yükleme kapanır
  IG_AI_LABEL  : "0" yazılırsa "Yapay zekâ ile üretildi" etiketi eklenmez (varsayılan: ekler)
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

VER = os.environ.get("IG_API_VERSION", "v25.0")
FB_API = "https://graph.facebook.com/" + VER      # Unified login (yeni uygulamalar, süresiz sistem anahtarı)
IG_API = "https://graph.instagram.com/" + VER     # eski "Instagram ile giriş" anahtarları
API = FB_API
_UID = None
MAX_BITRATE = 20_000_000   # Instagram Reels sınırı 25 Mbps; güvenlik payı


def _token():
    return os.environ["IG_TOKEN"]


def _call(method, url, params=None, data=None, headers=None, timeout=120):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    h = {"Authorization": f"Bearer {_token()}"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Instagram {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")


def user_id():
    """Instagram hesap kimliğini bulur. Önce Unified login (graph.facebook.com), olmazsa eski yöntem."""
    global API, _UID
    if _UID:
        return _UID
    if os.environ.get("IG_USER_ID"):
        _UID = os.environ["IG_USER_ID"]
        API = IG_API if _token().startswith("IG") else FB_API
        return _UID
    try:
        hesaplar = _call("GET", f"{FB_API}/me/assigned_instagram_accounts", {"fields": "id,username"})["data"]
        if not hesaplar:
            raise RuntimeError("Anahtara bağlı Instagram hesabı yok")
        isim = os.environ.get("IG_USERNAME", "").lstrip("@").lower()
        sec = next((h for h in hesaplar if h.get("username", "").lower() == isim), hesaplar[0])
        API, _UID = FB_API, sec["id"]
        print("Instagram hesabi (Unified login):", sec.get("username"), sec["id"])
    except RuntimeError as e:
        try:
            API, _UID = IG_API, _call("GET", f"{IG_API}/me", {"fields": "user_id,username"})["user_id"]
        except RuntimeError:
            raise e
    return _UID


def unified():
    user_id()
    return API == FB_API


def _safe_video(path):
    """Bit hızı Instagram sınırını aşıyorsa sınırlı bir kopya üretir."""
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "format=bit_rate", "-of", "default=nw=1:nk=1", path],
                             capture_output=True, text=True).stdout.strip()
        if out and int(out) <= MAX_BITRATE:
            return path
    except Exception:  # noqa — ölçemezsek dönüştürmeyi dene
        pass
    safe = path[:-4] + ".ig.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "22", "-maxrate", "15M", "-bufsize", "30M", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", safe], check=True)
    return safe


def _release_url(video_path, tag):
    """Videonun GitHub Release'teki herkese açık bağlantısı (depo herkese açık olmalı)."""
    repo = os.environ["GITHUB_REPOSITORY"]
    return f"https://github.com/{repo}/releases/download/{tag}/{os.path.basename(video_path)}"


def _resolve(url):
    """GitHub indirme bağlantısı başka adrese yönlendirir; Instagram için doğrudan adresi bulur."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url, method="HEAD"), timeout=60)
        return url
    except urllib.error.HTTPError as e:
        return e.headers.get("Location") or url


def _try_publish(uid, video_url, caption, wait_s, story=False):
    if story:
        params = {"media_type": "STORIES", "video_url": video_url}
    else:
        params = {"media_type": "REELS", "video_url": video_url, "caption": caption[:2200], "share_to_feed": "true",
                  # kapak: videonun ilk karesi siyah; başlığın göründüğü kareyi kullan (milisaniye)
                  "thumb_offset": os.environ.get("IG_KAPAK_MS") or "1500"}
    if os.environ.get("IG_AI_LABEL", "1") != "0":
        params["is_ai_generated"] = "true"
    cid = _call("POST", f"{API}/{uid}/media", params, data=b"")["id"]
    t0 = time.time()
    while True:  # Instagram videoyu indirip işleyene kadar bekle
        time.sleep(20)
        st = _call("GET", f"{API}/{cid}", {"fields": "status_code,status"})
        code = st.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram videoyu işleyemedi: {st}")
        if time.time() - t0 > wait_s:
            raise RuntimeError(f"Instagram işleme zaman aşımı: {st}")
    return _call("POST", f"{API}/{uid}/media_publish", {"creation_id": cid}, data=b"")["id"]


def publish_reel(video_path, caption, tag, wait_s=420, story=False):
    """Videoyu Reels (story=True ise Hikâye) olarak yayınlar, yayın kimliğini döndürür.
    Video önce GitHub Release'e konmuş olmalı."""
    safe = _safe_video(video_path) if os.path.exists(video_path) else video_path
    if safe != video_path:  # bit hızı düşürülmüş kopyayı da Release'e ekle
        subprocess.run(["gh", "release", "upload", tag, safe, "--clobber"], check=True)
    url = _release_url(safe, tag)
    uid = user_id()
    son_hata = None
    for u in (_resolve(url), url):  # önce doğrudan adres, olmazsa GitHub bağlantısı
        try:
            return _try_publish(uid, u, caption, wait_s, story)
        except RuntimeError as e:
            son_hata = e
            if "not an Instagram Business" in str(e) or '"code":10' in str(e).replace(" ", ""):
                break  # hesap türü sorunu: tekrar denemenin anlamı yok
            print("Instagram denemesi basarisiz, tekrar deneniyor:", str(e)[:200])
    if story and son_hata and "Business" in str(son_hata):
        raise RuntimeError("Hikaye icin Instagram hesabi 'Isletme' turunde olmali "
                           "(Ayarlar > Hesap turu > Isletme hesabina gec). " + str(son_hata)[:200])
    raise son_hata


def publish_story(video_path, tag, wait_s=420):
    """Aynı videoyu 24 saatlik Hikâye olarak paylaşır (yalnızca İşletme hesaplarında çalışır)."""
    return publish_reel(video_path, "", tag, wait_s, story=True)


def refresh_token():
    """Uzun ömürlü anahtarı 60 gün daha uzatır (anahtar en az 24 saatlik olmalı). Yeni anahtarı döndürür."""
    url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
        {"grant_type": "ig_refresh_token", "access_token": _token()})
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Instagram anahtar yenileme {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    return d["access_token"], int(d.get("expires_in", 0))


def build_caption(d):
    """Instagram açıklaması: konu cümlesi + kapanış sorusu + en fazla 5 etiket."""
    meta = d.get("meta", {})
    text = meta.get("caption") or d["title"]
    say = d.get("outro", {}).get("say", "")
    soru = next((s.strip() + "?" for s in say.split("?") if s.strip() and say.find(s) < say.rfind("?")), "")
    tags = [t for t in meta.get("hashtags", []) if t.lower() not in ("#shorts", "#short")]
    tags = (tags + ["#reels"])[:5]
    parts = [text]
    if soru:
        parts.append(f"💬 {soru} Yorumlara yaz!")
    parts.append("🔔 Her gün yeni bir 'Ya olsaydı?' için takip et.")
    parts.append(" ".join(tags))
    return "\n\n".join(parts)


# ---------------------------------------------------------------- yorumlar
def comment(media_id, text):
    """Kendi gönderimize yorum yazar."""
    return _call("POST", f"{API}/{media_id}/comments", {"message": text[:2200]}, data=b"")["id"]


def reply(comment_id, text):
    """Bir yoruma cevap yazar."""
    return _call("POST", f"{API}/{comment_id}/replies", {"message": text[:2200]}, data=b"")["id"]


def username():
    user_id()
    if API == FB_API:
        return _call("GET", f"{API}/{_UID}", {"fields": "username"}).get("username", "")
    return _call("GET", f"{API}/me", {"fields": "username"}).get("username", "")


def recent_media(limit=10):
    uid = user_id()
    return _call("GET", f"{API}/{uid}/media", {"fields": "id,caption,timestamp", "limit": limit}).get("data", [])


def comments(media_id):
    return _call("GET", f"{API}/{media_id}/comments",
                 {"fields": "id,text,username,timestamp,replies{username}", "limit": 50}).get("data", [])
