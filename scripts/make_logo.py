"""Membuat logo aplikasi untuk form developer.tiktok.com.

Jalankan: .venv\\Scripts\\python.exe scripts\\make_logo.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.image_maker import _load_font

BRANDING_DIR = "branding"
WORDMARK = os.getenv("LOGO_WORDMARK", "TREN")


def _gradient(size, top=(16, 23, 61), bottom=(92, 44, 147)):
    image = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(image)
    for y in range(size):
        ratio = y / (size - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line([(0, y), (size, y)], fill=color)
    return image


def _bolt(size, color):
    scale = size / 512
    points = [
        (0.58, 0.10), (0.26, 0.55), (0.45, 0.55),
        (0.38, 0.90), (0.74, 0.44), (0.54, 0.44),
    ]
    polygon = [(x * size, y * size) for x, y in points]
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(layer).polygon(polygon, fill=color)
    return layer


def build_logo(size=512):
    base = _gradient(size).convert("RGBA")

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=255)
    base.putalpha(mask)

    accent = (255, 196, 84, 255)
    base.alpha_composite(_bolt(size, accent))

    draw = ImageDraw.Draw(base)
    font = _load_font("bold", int(size * 0.13))
    text = WORDMARK.upper()
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(
        ((size - (box[2] - box[0])) / 2, size * 0.66),
        text,
        font=font,
        fill=(245, 247, 255, 255),
    )

    os.makedirs(BRANDING_DIR, exist_ok=True)
    path = os.path.join(BRANDING_DIR, f"logo-{size}.png")
    base.convert("RGB").save(path, "PNG")
    print(f"[LOGO] {path} ({os.path.getsize(path)} bytes, {size}x{size})")
    return path


if __name__ == "__main__":
    for size in (512, 1024):
        build_logo(size)