**Ya Olsaydı? YouTube kanalı için video üretme ve yükleme aracı (YouTube API Servisleri kullanır).** [Gizlilik Politikası](PRIVACY.md)

# Ya Olsaydı? — otomatik çöp adam animasyonu fabrikası

Konu → senaryo (Gemini) → seslendirme (Gemini TTS, yedek Edge) → çöp adam animasyonu (Canvas, headless Chrome) →
sentezlenmiş ses efektleri + müzik → karaoke altyazı → 1080×1920 MP4 → YouTube Shorts + Instagram Reels/Hikâye.

Kurulum: [KURULUM.md](KURULUM.md)

| Dosya | Görev |
|---|---|
| `autopilot.py` | Günlük döngü: senaryo → video → yükleme |
| `scriptgen.py` | Gemini ile yeni senaryo (kuyruk: `topics_queue.txt`) |
| `make_video.py` | Senaryodan video |
| `render/engine.js` | Çizim motoru: 11 arka plan, 50+ nesne, 25+ çöp adam hareketi |
| `engine/spec.py` | Senaryo şeması ve otomatik düzeltme |
| `engine/timeline.py` | Sahne zamanları, altyazı, ses efekti olayları |
| `engine/voice.py`, `sfx.py` | Seslendirme, ses tasarımı |
| `engine/youtube.py`, `instagram.py`, `cevaplar.py` | Yükleme, yorum, cevap |
