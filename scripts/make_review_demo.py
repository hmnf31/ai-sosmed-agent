"""Membuat video demo untuk pengajuan App Review TikTok.

Video ini Replacement dari rekaman layar manual: setiap slide dirender sebagai
frame dengan Pillow, lalu disusun dengan ffmpeg. Isinya menuntun dari sumber tren,
caption AI, render video, lalu pemanggilan API TikTok.

Jalankan: .venv\\Scripts\\python.exe scripts\\make_review_demo.py
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.image_maker import _gradient_background, _load_font, _wrap
from utils.video_maker import _find_ffmpeg

WIDTH, HEIGHT = 1280, 720
FPS = 25
SEGMENT_SECONDS = 4
OUTPUT_DIR = "output"

SLIDES = [
    (
        "Tren Esports ID - App Review Demo",
        ["Content Posting API  |  video.publish  |  user.info.basic",
         "",
         "Scheduled job: GitHub Actions cron, 01:00 UTC",
         "Server-side service, no end-user accounts"],
    ),
    (
        "Step 1 - Riset tren (Playwright)",
        ["Membuka pencarian YouTube:",
         '  query = "Mobile Legends Indonesia"',
         "  filter: upload terbaru",
         "",
         "Membaca judul video publik, lalu_membersihkan",
         "emoji dan badge LIVE, lalu diurutkan",
         "berdasarkan skor relevansi.",
         "",
         "Output: RRQ vs EVOS ... | ASIAN GAMES 2026 ..."],
    ),
    (
        "Step 2 - Caption AI (OpenRouter)",
        ["POST https://openrouter.ai/api/v1/chat/completions",
         "",
         "Model  : nvidia/nemotron-3-ultra-550b-a55b:free",
         "Prompt : niche esports MLBB, bahasa Indonesia,",
         "          wajib CTA tanya balik + 5-8 hashtag",
         "",
         "Output: caption siap tayang, contoh:",
         '"RRQ vs EVOS bukan cuma klasmen, tapi"',
         '"pertarungan Draft Mental! ... Komen prediksi!"'],
    ),
    (
        "Step 3 - Render video vertikal",
        ["Pillow   : 3 frame 1080x1920 (gradient, judul tren)",
         "ffmpeg   : zoom Ken Burns + fade per segmen",
         "           h264 High / yuv420p / 25 fps",
         "           audio aac 44100 Hz stereo (wajib TikTok)",
         "",
         "Output: tren-20261005-114152.mp4  (0.36 MB, 12 detik)"],
    ),
    (
        "Step 4 - Autentikasi (user.info.basic)",
        ["POST /v2/oauth/token/   grant_type=refresh_token",
         "  -> access_token",
         "",
         "GET  /v2/user/info/?fields=open_id,display_name",
         "  -> open_id akun tujuan (milik pemilik app)",
         "",
         "Hanya open_id yang dibaca, untuk memastikan",
         "video dikirim ke akun yang benar."],
    ),
    (
        "Step 5 - Content Posting API (video.publish)",
        ["POST /v2/post/publish/video/init/",
         "  post_info  : title=caption, privacy_level",
         "  source_info: source=UPLOAD, chunk_size,",
         "                total_chunk_count",
         "  -> publish_id + upload_url",
         "",
         "PUT upload_url  (mp4 per chunk, Content-Range)",
         "POST /v2/post/publish/status/fetch/",
         "  -> PUBLISH_COMPLETE"],
    ),
    (
        "Step 6 - Laporan & bukti di akun",
        ["Telegram  : " +
         "[TIKTOK] Sukses! Publish ID + status",
         "",
         "Bukti unggahan nyata (akun MLBB):",
         "  - caption AI tertayang dengan hashtag",
         "  - video vertikal 12 detik, h264, 1080x1920",
         "",
         "Tidak ada Login Kit, Share Kit, shop,",
         "voucher, atau akun pengguna end-user."],
    ),
]


def _render_slide(index, title, lines):
    image, draw = _gradient_background(WIDTH, HEIGHT)
    accent = (255, 196, 84)
    white = (245, 247, 255)
    muted = (188, 193, 220)

    draw.rectangle([0, 0, WIDTH, 8], fill=accent)
    draw.rounded_rectangle([60, 58, 60 + 46, 58 + 12], radius=6, fill=accent)

    step_font = _load_font("bold", 26)
    draw.text((60, 28), f"{index} / {len(SLIDES)}", font=step_font, fill=accent)

    title_font = _load_font("bold", 44)
    y = 96
    for line in _wrap(draw, title, title_font, WIDTH - 120):
        draw.text((60, y), line, font=title_font, fill=white)
        y += 56

    body_font = _load_font("regular", 25)
    y += 18
    for line in lines:
        color = white if line.strip().startswith(("POST", "GET", "PUT", "Output", "Telegram", "Pillow", "Model")) else muted
        draw.text((60, y), line, font=body_font, fill=color)
        y += 34

    footer = _load_font("bold", 22)
    draw.text((60, HEIGHT - 54), "developer.tiktok.com/app  -  Tren Esports ID", font=footer, fill=accent)
    return image


def build_demo(output_path=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = output_path or os.path.join(OUTPUT_DIR, "app-review-demo.mp4")

    frame_paths = []
    for i, (title, lines) in enumerate(SLIDES, start=1):
        path = os.path.join(OUTPUT_DIR, f"demo-frame-{i}.png")
        _render_slide(i, title, lines).save(path, "PNG")
        frame_paths.append(path)

    filters, total = [], len(frame_paths)
    for i in range(total):
        start = i * SEGMENT_SECONDS
        zoom = "min(zoom+0.0009,1.08)"
        filters.append(
            f"[{i}:v]scale={WIDTH * 2}:{HEIGHT * 2},"
            f"zoompan=z='{zoom}':d={FPS * SEGMENT_SECONDS}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={WIDTH}x{HEIGHT}:fps={FPS},"
            f"fade=t=in:st=0:d=0.4,fade=t=out:st={SEGMENT_SECONDS - 0.4}:d=0.4,"
            f"format=yuv420p[v{i}]"
        )
    concat = "".join(f"[v{i}]" for i in range(total))
    filter_complex = ";".join(filters) + f";{concat}concat=n={total}:v=1:a=0[vout]"

    command = [_find_ffmpeg(), "-y"]
    for path in frame_paths:
        command += ["-i", path]
    command += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    command += [
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", f"{total}:a", "-shortest",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal: {result.stderr[-500:]}")

    for path in frame_paths:
        try:
            os.remove(path)
        except OSError:
            pass

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[DEMO] {output_path} ({size_mb:.2f} MB, {total * SEGMENT_SECONDS} detik, {WIDTH}x{HEIGHT})")
    return output_path


if __name__ == "__main__":
    build_demo()