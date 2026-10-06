"""Membuat aset placeholder untuk komposisi Remotion dummy.

Dijalankan sekali saat setup atau bila aset perlu dibuat ulang:
    .venv\\Scripts\\python.exe remotion/scripts/generate_placeholders.py

File hasilnya ada di remotion/public/ dan ikut di-commit karena ukurannya kecil.
"""
import os
import wave

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(HERE, "public")

WIDTH, HEIGHT = 1080, 1920
AUDIO_SECONDS = 20
AUDIO_RATE = 8000

SCENES = [
    ("placeholder-1.png", (10, 14, 23), (0, 184, 212), "SCENE 01 - HOOK"),
    ("placeholder-2.png", (24, 33, 64), (255, 45, 111), "SCENE 02 - ISI"),
    ("placeholder-3.png", (10, 14, 23), (0, 229, 255), "SCENE 03 - CTA"),
]


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow lama tidak menerima argumen size
        return ImageFont.load_default()


def make_scene(path, top, bottom, label):
    image = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = image.load()
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        row = tuple(
            int(top[ch] + (bottom[ch] - top[ch]) * t) for ch in range(3)
        )
        for x in range(WIDTH):
            pixels[x, y] = row

    draw = ImageDraw.Draw(image)
    font = _font(72)
    box = draw.textbbox((0, 0), label, font=font)
    text_w = box[2] - box[0]
    text_h = box[3] - box[1]
    draw.text(
        ((WIDTH - text_w) / 2, (HEIGHT - text_h) / 2),
        label,
        fill=(242, 247, 255),
        font=font,
    )
    image.save(path, "PNG")


def make_audio(path):
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(AUDIO_RATE)
        handle.writeframes(b"\x00\x00" * (AUDIO_RATE * AUDIO_SECONDS))


def main():
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    for name, top, bottom, label in SCENES:
        target = os.path.join(PUBLIC_DIR, name)
        make_scene(target, top, bottom, label)
        print(f"[placeholder] {target}")
    audio_path = os.path.join(PUBLIC_DIR, "placeholder-audio.wav")
    make_audio(audio_path)
    print(f"[placeholder] {audio_path}")


if __name__ == "__main__":
    main()
