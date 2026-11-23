# Ya Olsaydı? — Kurulum (bir kez, ~30-40 dk)

Kurulumdan sonra GitHub her gün **17:37'de** (Türkiye saati) kendiliğinden yeni bir senaryo yazar, videoyu
üretir ve YouTube Shorts + Instagram Reels + Hikâye olarak yükler. Bilgisayarının açık olması gerekmez.
Her şey ücretsiz, kart gerekmez.

---

## 1) GitHub deposu
1. github.com → sağ üst **+** → **New repository** → ad: `ya-olsaydi` → **Public** → **Create repository**.
2. Açılan sayfada **uploading an existing file** bağlantısına tıkla.
3. Zip'i bilgisayarında çıkar. `ya-olsaydi` klasörünü aç, **içindeki her şeyi** (`.github` klasörü dahil) seç
   ve sayfaya sürükle → aşağıda **Commit changes**.
   - Windows'ta `.github` görünmüyorsa: Gezgin → **Görünüm → Göster → Gizli öğeler**.
   - Kontrol: depoda `.github/workflows/video.yml` dosyası görünmeli.
4. Depoda **Settings → Actions → General** → en altta **Workflow permissions** →
   **Read and write permissions** → **Save**.

## 2) Gemini anahtarı (senaryo + seslendirme)
1. aistudio.google.com → **Get API key** → **Create API key** → **yeni proje oluştur** seçeneğiyle oluştur.
   (Eski kanalın anahtarından ayrı bir proje olsun; ücretsiz kota proje başına ayrı sayılır.)
2. GitHub deposu → **Settings → Secrets and variables → Actions → New repository secret**:
   - Name: `GEMINI_API_KEY` — Secret: anahtarın → **Add secret**.

## 3) İlk deneme (hiçbir yere yüklemez)
1. Depoda **Actions** sekmesi → solda **Ya Olsaydi** → sağda **Run workflow** →
   "Sadece önizleme" işaretli kalsın → yeşil **Run workflow**.
2. 5-10 dk sonra çalışmaya tıkla → en altta **Artifacts** → **onizleme-video** → indir, zip'ten mp4 çıkar.
3. Beğendiysen devam. (Sıradaki video zaten hazır olan "Ay Dünya'ya çarpsaydı" senaryosu.)

## 4) YouTube bağlantısı
**Kolay yol: eski kanalın Google Cloud projesini kullan.** Eski projen YouTube denetiminden
(audit) geçtiyse yeni projeye gerek yok. Aynı Client ID / Client secret ile sadece yeni kanal için
yeni bir yenileme anahtarı alırsın:

1. developers.google.com/oauthplayground → sağ üst ⚙️ → **Use your own OAuth credentials** →
   eski projenin Client ID ve Client secret'ını yapıştır.
2. Soldaki kutuya şu iki satırı **ayrı ayrı** yazıp ekle:
   `https://www.googleapis.com/auth/youtube.upload`
   `https://www.googleapis.com/auth/youtube.force-ssl`
   → **Authorize APIs** → **yaolsaydiiofficial@gmail.com** hesabını ve **Ya Olsaydı?** kanalını seç →
   "doğrulanmamış uygulama" uyarısında **Gelişmiş → devam et** → izinleri ver.
3. **Exchange authorization code for tokens** → **Refresh token**'ı kopyala.
4. GitHub → Settings → Secrets and variables → Actions → **Secrets** sekmesine üç tane ekle:
   `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
5. Aynı sayfada **Variables** sekmesi → **New repository variable** → `YT_UPLOAD` = `1`.

Eski proje denetimden geçmediyse yeni bir Google Cloud projesi aç. Adımlar eski kurulumla aynı:
YouTube Data API v3'ü etkinleştir, OAuth ekranında uygulamayı **yayınla**, Web istemcisi oluştur,
yönlendirme adresi olarak `https://developers.google.com/oauthplayground` gir. Sonra ücretsiz denetim formunu doldur:
https://support.google.com/youtube/contact/yt_api_form (Gizlilik politikası için depodaki `PRIVACY.md`
bağlantısını ver.) Onay gelene kadar `YT_UPLOAD` değişkenini ekleme, çünkü onaysız projenin videoları gizli kalır.

## 5) Instagram bağlantısı
Eski kanalda kullandığın **işletme portföyü** ve **sistem kullanıcısı** burada da kullanılabilir:
1. business.facebook.com → **Ayarlar → Hesaplar → Instagram hesapları → Ekle** → yeni hesabı bağla.
2. **Kullanıcılar → Sistem kullanıcıları** → eski sistem kullanıcını seç → **Varlık ata** →
   Instagram hesapları → yeni hesap → **tam kontrol** → Kaydet.
3. GitHub → Secrets → `IG_TOKEN` = eski kanalda kullandığın **aynı sistem kullanıcısı anahtarı**.
   (Bu anahtar çalışmazsa aynı sistem kullanıcısında **Anahtar oluştur** ile yenisini al:
   `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`,
   `pages_show_list`, `business_management` izinleriyle.)
4. GitHub → **Variables** → `IG_USERNAME` = yeni Instagram kullanıcı adın (başında @ olmadan).
   (Anahtar birden fazla hesaba bağlı olduğu için doğru hesap bu ada göre seçilir.)

## 6) Bitti!
- Gerçek bir test için: Actions → Run workflow → **"Sadece önizleme" işaretini kaldır** → Run.
- Bundan sonra her gün kendiliğinden çalışır.

---

## Günlük kullanım
- **Konu eklemek:** depoda `topics_queue.txt` → kalem simgesi → her satıra bir konu yaz → Commit.
  Biçim: `bilim: Ya ... olsaydı?` / `hikaye: ...` / `secim: A mı, B mi?`. Liste bitince yapay zekâ konuyu kendisi seçer.
- **Hemen belirli bir konu:** Actions → Run workflow → "konu" kutusuna yaz.
- **Claude'dan hazır senaryo:** Claude'a "Ya Olsaydı kanalı için şu konuda senaryo JSON'u yaz" de, gelen
  dosyayı `topics/` klasörüne yükle. Hazır senaryolar sırayla önce kullanılır.
- **Videoları görmek:** depoda sağda **Releases**.

## İsteğe bağlı ayarlar (Variables)
| Ad | Ne işe yarar | Varsayılan |
|---|---|---|
| `GEMINI_TTS_VOICE` | Ses: `Puck` (neşeli), `Fenrir` (heyecanlı), `Charon` (belgesel), kadın: `Leda`, `Aoede` | Puck |
| `SES_HIZI` | Konuşma hızı (ör. `1.1`) | 1.06 |
| `IG_UPLOAD` | `0` = Instagram'a yükleme | açık |
| `IG_STORY` | `0` = hikâye paylaşma | açık |
| `IG_COMMENT` / `YT_COMMENT` | `0` = videonun altına kanal yorumu yazma | açık |
| `IG_CEVAP` | `0` = Instagram yorumlarına otomatik cevap verme | açık |
| `IG_KAPAK_MS` | Reels kapağı için kare (milisaniye) | 1500 |

## Saat
GitHub'ın zamanlanmış çalışmaları bazen 1-2 saat gecikebilir. Saati değiştirmek için
`.github/workflows/video.yml` dosyasındaki `cron: "37 14 * * *"` satırını değiştir (saat UTC, Türkiye = UTC+3).
