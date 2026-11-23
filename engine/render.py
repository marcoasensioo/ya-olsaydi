"""Headless Chrome (WebGL/SwiftShader veya GPU) ile kareleri çizer, ffmpeg'e akıtır.

Her işçi kendi kare aralığını ayrı bir mp4'e yazar; sonra concat ile birleştirilir.
"""
import base64
import functools
import http.server
import os
import shutil
import subprocess
import threading
import time

from playwright.sync_api import sync_playwright

RENDER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "render")
# GPU'lu bilgisayarda RENDER_GPU=1 ile çok daha hızlı (ekran kartı kullanılır)
CHROME_ARGS = (["--ignore-gpu-blocklist", "--enable-gpu-rasterization", "--disable-gpu-vsync"]
               if os.environ.get("RENDER_GPU") == "1" else
               ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                "--ignore-gpu-blocklist", "--disable-gpu-vsync"])


def chrome_path():
    for p in (os.environ.get("CHROME_PATH"), "/usr/bin/google-chrome",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if p and os.path.exists(p):
            return p
    return None  # Playwright'in kendi Chromium'u


def serve(directory, timeline_path):
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def translate_path(self, path):
            if path.split("?")[0] == "/timeline.json":
                return timeline_path
            return super().translate_path(path)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=directory))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def render_range(url, f0, f1, fps, out_mp4, log=print):
    tmp = out_mp4[:-4] + ".part.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg",
                           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
                           "-r", str(fps), "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome_path(), args=CHROME_ARGS, headless=True)
        pg = b.new_page(viewport={"width": 400, "height": 600})
        pg.on("console", lambda m: m.type == "error" and log("[chrome]", m.text))
        pg.on("pageerror", lambda e: log("[pageerror]", e))
        pg.goto(url)
        pg.wait_for_function("window.READY === true", timeout=180000)
        if f0 > 0:  # hareket bulanıklığı geçmişi için ısınma karesi
            pg.evaluate(f"window.renderFrame({(f0 - 1) / fps})")
        t0 = time.time()
        for f in range(f0, f1):
            data = pg.evaluate(f"window.renderFrame({f / fps})")
            ff.stdin.write(base64.b64decode(data.split(",", 1)[1]))
            if (f - f0) % 150 == 0:
                log(f"  kare {f}/{f1}  ({(time.time() - t0) / max(1, f - f0 + 1):.2f} sn/kare)")
        b.close()
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg hata verdi")
    os.replace(tmp, out_mp4)


def render_video(timeline_path, duration, fps, work_dir, workers=2, cut_points=None, log=print, page="index.html"):
    srv = serve(RENDER_DIR, os.path.abspath(timeline_path))
    url = f"http://127.0.0.1:{srv.server_address[1]}/{page}"
    total = int(round(duration * fps))
    # parça sınırları: geçişlerden uzak noktalar (cut_points, saniye)
    cuts = sorted({0, total, *[int(c * fps) for c in (cut_points or [])]})
    ranges = [(a, b) for a, b in zip(cuts, cuts[1:]) if b > a]
    os.makedirs(work_dir, exist_ok=True)
    parts = [os.path.join(work_dir, f"part{i:02d}.mp4") for i in range(len(ranges))]
    todo = [(r, p) for r, p in zip(ranges, parts) if not os.path.exists(p)]
    threads, errors = [], []
    q = list(todo)
    lock = threading.Lock()

    def worker():
        while True:
            with lock:
                if not q:
                    return
                (a, b), p = q.pop(0)
            try:
                log(f"render {os.path.basename(p)}: kare {a}-{b}")
                render_range(url, a, b, fps, p, log)
            except Exception as e:  # noqa
                errors.append(e)
    for _ in range(max(1, workers)):
        th = threading.Thread(target=worker); th.start(); threads.append(th)
    for th in threads:
        th.join()
    srv.shutdown()
    if errors:
        raise errors[0]
    lst = os.path.join(work_dir, "parts.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in parts))
    silent = os.path.join(work_dir, "video_silent.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent], check=True)
    return silent


def snapshot(timeline_path, times, out_dir, page="index.html"):
    """Belirli anların tam boy karelerini JPEG olarak kaydeder (kontrol için)."""
    srv = serve(RENDER_DIR, os.path.abspath(timeline_path))
    url = f"http://127.0.0.1:{srv.server_address[1]}/{page}"
    os.makedirs(out_dir, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome_path(), args=CHROME_ARGS, headless=True)
        pg = b.new_page()
        pg.on("console", lambda m: m.type == "error" and print("[chrome]", m.text))
        pg.on("pageerror", lambda e: print("[pageerror]", e))
        pg.goto(url)
        pg.wait_for_function("window.READY === true", timeout=180000)
        paths = []
        for t in times:
            st = time.time()
            data = pg.evaluate(f"window.renderFrame({t})")
            path = os.path.join(out_dir, f"snap_{t:06.2f}.jpg")
            open(path, "wb").write(base64.b64decode(data.split(",", 1)[1]))
            print(f"{path}  {time.time() - st:.2f}s")
            paths.append(path)
        b.close()
    srv.shutdown()
    return paths
