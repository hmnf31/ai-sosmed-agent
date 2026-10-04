import os
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1080
HEIGHT = 1080
WIB = timezone(timedelta(hours=7))
OUTPUT_DIR = "output"

FONT_DIRS = [
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
]
FONT_FILES = {
    "bold": ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf"],
    "regular": ["segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf"],
}


def _load_font(kind, size):
    for name in FONT_FILES[kind]:
        for folder in FONT_DIRS:
            path = os.path.join(folder, name)
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except OSError:
                    continue
    return ImageFont.load_default(size=size)


def _wrap(draw, text, font, max_width, max_lines=None):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(0, len(lines[-1]) - 3)] + "..."
    return lines


def _draw_paragraph(draw, lines, font, x, y, fill, line_spacing=1.35):
    step = int(font.size * line_spacing)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += step
    return y


def render_trend_image(trends, output_path=None, footer="AI Sosmed Agent"):
    """Merender kartu 1080x1080 berisi tren utama, siap dikirim ke Telegram/Instagram."""
    trends = list(trends) or ["Tren Terkini"]
    headline = trends[0].upper()
    others = ", ".join(trends[1:]) or "Ringkasan topik pilihan"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if output_path is None:
        stamp = datetime.now(WIB).strftime("%Y%m%d-%H%M")
        output_path = os.path.join(OUTPUT_DIR, f"tren-{stamp}.png")

    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    top, bottom = (16, 23, 61), (92, 44, 147)
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line([(0, y), (WIDTH, y)], fill=color)

    margin = 90
    accent = (255, 196, 84)
    white = (245, 247, 255)
    muted = (188, 193, 220)

    draw.rounded_rectangle([margin, 120, margin + 96, 134], radius=7, fill=accent)

    label_font = _load_font("bold", 34)
    label = "TREN HARI INI"
    draw.text((margin, 74), label, font=label_font, fill=accent)

    title_font = _load_font("bold", 96)
    y = _draw_paragraph(draw, _wrap(draw, headline, title_font, WIDTH - 2 * margin, 3), title_font, margin, 200, white, 1.2)

    sub_font = _load_font("regular", 44)
    y = _draw_paragraph(draw, _wrap(draw, others, sub_font, WIDTH - 2 * margin, 3), sub_font, margin, y + 30, muted, 1.35)

    body_font = _load_font("regular", 40)
    now = datetime.now(WIB).strftime("%d %B %Y, %H:%M WIB")
    _draw_paragraph(draw, [now], body_font, margin, HEIGHT - 250, white, 1.4)

    footer_font = _load_font("bold", 34)
    draw.line([(margin, HEIGHT - 200), (WIDTH - margin, HEIGHT - 200)], fill=(255, 255, 255, 60), width=2)
    _draw_paragraph(draw, [footer], footer_font, margin, HEIGHT - 160, accent, 1.4)

    image.save(output_path, "PNG")
    print(f"[IMAGE] Kartu tren dibuat: {output_path}")
    return output_path