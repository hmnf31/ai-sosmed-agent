import os
import shutil
import subprocess

from utils.image_maker import VIDEO_WIDTH, VIDEO_HEIGHT, render_content_video_frames, render_video_frames

FPS = 25
SEGMENT_SECONDS = 4
FFMPEG_CANDIDATES = [
    os.getenv("FFMPEG_PATH"),
    "ffmpeg",
    r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe",
]
OUTPUT_DIR = "output"


def _find_ffmpeg():
    for candidate in FFMPEG_CANDIDATES:
        if not candidate:
            continue
        if os.path.isfile(candidate):
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    raise FileNotFoundError(
        "ffmpeg tidak ditemukan. Pasang ffmpeg (winget install ffmpeg) atau set FFMPEG_PATH."
    )


def _compose(frames, output_path):
    frames_per_segment = FPS * SEGMENT_SECONDS
    zoom = 1.0015

    filters = []
    for i, _ in enumerate(frames):
        fade_out = SEGMENT_SECONDS - 0.4
        filters.append(
            f"[{i}:v]scale={VIDEO_WIDTH * 2}:{VIDEO_HEIGHT * 2},"
            f"zoompan=z='min(zoom+{zoom},1.12)':d={frames_per_segment}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS},"
            f"fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out}:d=0.4,format=yuv420p[v{i}]"
        )
    concat = "".join(f"[v{i}]" for i in range(len(frames)))
    filter_complex = ";".join(filters) + f";{concat}concat=n={len(frames)}:v=1:a=0[vout]"

    inputs = []
    for frame in frames:
        inputs += ["-i", frame]
    inputs += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]

    command = [_find_ffmpeg(), "-y", *inputs, "-filter_complex", filter_complex,
               "-map", "[vout]", "-map", f"{len(frames)}:a",
               "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
               "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", output_path]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal (exit {result.returncode}): {result.stderr[-600:]}")


def _cleanup(frames):
    for frame in frames:
        try:
            os.remove(frame)
        except OSError:
            pass


def render_content_video(content, output_path=None, footer="AI Sosmed Agent"):
    """Menggabungkan frame konten AI menjadi video mp4 vertikal untuk unggah manual."""
    frames = render_content_video_frames(content, output_dir=OUTPUT_DIR, footer=footer)
    if output_path is None:
        stamp = frames[0].split("frame-1-")[1].rsplit(".", 1)[0]
        output_path = os.path.join(OUTPUT_DIR, f"konten-{stamp}.mp4")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    _compose(frames, output_path)
    _cleanup(frames)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[VIDEO] Video konten dibuat: {output_path} ({size_mb:.2f} MB, {len(frames) * SEGMENT_SECONDS} detik)")
    return output_path


def render_trend_video(trends, output_path=None, footer="AI Sosmed Agent"):
    """Menggabungkan frame vertikal menjadi video mp4 (h264 + audio) untuk TikTok/Reels."""
    frames = render_video_frames(trends, footer=footer, output_dir=OUTPUT_DIR)

    if output_path is None:
        stamp = frames[0].split("frame-1-")[1].rsplit(".", 1)[0]
        output_path = os.path.join(OUTPUT_DIR, f"tren-{stamp}.mp4")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    _compose(frames, output_path)
    _cleanup(frames)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[VIDEO] Video tren dibuat: {output_path} ({size_mb:.2f} MB, {len(frames) * SEGMENT_SECONDS} detik)")
    return output_path