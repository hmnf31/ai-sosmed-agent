import os
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1080
HEIGHT = 1080
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
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


def render_content_video_frames(content, output_dir=None, footer="AI Sosmed Agent"):
    """Merender frame vertikal 1080x1920 dari konten hasil AI.

    Frame 1 memuat judul, frame 2 daftar poin, frame 3 ajakan bertindak.
    """
    output_dir = output_dir or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    stamp = datetime.now(WIB).strftime("%Y%m%d-%H%M%S")

    accent = (255, 196, 84)
    white = (245, 247, 255)
    muted = (188, 193, 220)

    title = content.get("title") or "Konten Hari Ini"
    subtitle = content.get("subtitle") or ""
    points = [p for p in content.get("points", []) if p]
    cta = content.get("cta") or "Komentari pendapatmu"

    paths = []

    image, draw = _gradient_background(VIDEO_WIDTH, VIDEO_HEIGHT)
    draw.rounded_rectangle([96, 220, 192, 234], radius=7, fill=accent)
    paths.append(
        _save_frame(
            image, draw,
            [
                ("bold", 36, "TREN TERKINI", accent, 0),
                ("bold", 112, title.upper(), white, 110),
                ("regular", 48, subtitle, muted, 80),
                ("regular", 40, datetime.now(WIB).strftime("%d %B %Y, %H:%M WIB"), white, 0),
            ],
            os.path.join(output_dir, f"frame-1-{stamp}.png"), VIDEO_WIDTH, VIDEO_HEIGHT,
        )
    )

    image, draw = _gradient_background(VIDEO_WIDTH, VIDEO_HEIGHT)
    bullet_lines = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(points[:4]))
    paths.append(
        _save_frame(
            image, draw,
            [
                ("bold", 36, "POIN PENTING", accent, 0),
                ("bold", 62, bullet_lines, white, 90),
                ("regular", 44, "Detail lengkap ada di caption.", muted, 90),
                ("bold", 36, footer, accent, 0),
            ],
            os.path.join(output_dir, f"frame-2-{stamp}.png"), VIDEO_WIDTH, VIDEO_HEIGHT,
        )
    )

    image, draw = _gradient_background(VIDEO_WIDTH, VIDEO_HEIGHT)
    paths.append(
        _save_frame(
            image, draw,
            [
                ("bold", 36, "GILIRANMU", accent, 0),
                ("bold", 92, cta.upper(), white, 120),
                ("regular", 46, "Tulis di komentar, jangan cuma diam-diam.", muted, 80),
                ("bold", 40, "#" + footer.replace(" ", ""), accent, 140),
            ],
            os.path.join(output_dir, f"frame-3-{stamp}.png"), VIDEO_WIDTH, VIDEO_HEIGHT,
        )
    )

    print(f"[IMAGE] {len(paths)} frame konten dibuat di {output_dir}")
    return paths


def render_content_image(content, output_path=None, footer="AI Sosmed Agent"):
    """Merender kartu 1080x1080 dari konten hasil AI (untuk Instagram atau feed)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if output_path is None:
        stamp = datetime.now(WIB).strftime("%Y%m%d-%H%M%S")
        output_path = os.path.join(OUTPUT_DIR, f"konten-{stamp}.png")

    title = content.get("title") or "Konten Hari Ini"
    subtitle = content.get("subtitle") or ""
    points = [p for p in content.get("points", []) if p]
    cta = content.get("cta") or ""

    image, draw = _gradient_background(WIDTH, HEIGHT)

    margin = 90
    accent = (255, 196, 84)
    white = (245, 247, 255)
    muted = (188, 193, 220)

    draw.rounded_rectangle([margin, 120, margin + 96, 134], radius=7, fill=accent)
    label_font = _load_font("bold", 34)
    draw.text((margin, 74), "TREN TERKINI", font=label_font, fill=accent)

    y = _draw_paragraph(
        draw, _wrap(draw, title.upper(), _load_font("bold", 84), WIDTH - 2 * margin, 3),
        _load_font("bold", 84), margin, 200, white, 1.2,
    )
    if subtitle:
        sub_font = _load_font("regular", 40)
        y = _draw_paragraph(draw, _wrap(draw, subtitle, sub_font, WIDTH - 2 * margin, 3),
                            sub_font, margin, y + 26, muted, 1.35)

    if points:
        point_font = _load_font("regular", 38)
        y += 40
        for point in points[:3]:
            y = _draw_paragraph(draw, _wrap(draw, f"- {point}", point_font, WIDTH - 2 * margin, 2),
                                point_font, margin, y, white, 1.3)
            y += 8

    body_font = _load_font("regular", 36)
    _draw_paragraph(draw, [datetime.now(WIB).strftime("%d %B %Y, %H:%M WIB")],
                    body_font, margin, HEIGHT - 250, white, 1.4)
    draw.line([(margin, HEIGHT - 200), (WIDTH - margin, HEIGHT - 200)], fill=(255, 255, 255), width=2)
    _draw_paragraph(draw, [cta or footer], _load_font("bold", 34), margin, HEIGHT - 160, accent, 1.4)

    image.save(output_path, "PNG")
    print(f"[IMAGE] Kartu konten dibuat: {output_path}")
    return output_path


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


def _gradient_background(width, height):
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    top, bottom = (16, 23, 61), (92, 44, 147)
    for y in range(height):
        ratio = y / (height - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)
    return image, draw


def _save_frame(image, draw, text_blocks, path, width, height, margin=96):
    """text_blocks: list of (font_kind, size, text, fill, space_before)."""
    y = margin
    for kind, size, text, fill, space_before in text_blocks:
        if not text:
            continue
        y += space_before
        font = _load_font(kind, size)
        lines = _wrap(draw, text, font, width - 2 * margin)
        y = _draw_paragraph(draw, lines, font, margin, y, fill, 1.3)
    image.save(path, "PNG")
    return path


def render_video_frames(trends, footer="AI Sosmed Agent", output_dir=None):
    """Merender 3 frame vertikal 1080x1920 sebagai bahan video TikTok/Reels."""
    trends = list(trends) or ["Tren Terkini"]
    headline = trends[0]
    others = [t for t in trends[1:] if t]

    output_dir = output_dir or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    stamp = datetime.now(WIB).strftime("%Y%m%d-%H%M%S")

    accent = (255, 196, 84)
    white = (245, 247, 255)
    muted = (188, 193, 220)

    paths = []

    image, draw = _gradient_background(VIDEO_WIDTH, VIDEO_HEIGHT)
    draw.rounded_rectangle([96, 220, 192, 234], radius=7, fill=accent)
    paths.append(
        _save_frame(
            image,
            draw,
            [
                ("bold", 36, "TREN HARI INI", accent, 0),
                ("bold", 108, headline.upper(), white, 90),
                ("regular", 46, ", ".join(others) if others else "Ringkasan topik pilihan", muted, 70),
                ("regular", 42, datetime.now(WIB).strftime("%d %B %Y, %H:%M WIB"), white, 0),
            ],
            os.path.join(output_dir, f"frame-1-{stamp}.png"),
            VIDEO_WIDTH,
            VIDEO_HEIGHT,
        )
    )

    image, draw = _gradient_background(VIDEO_WIDTH, VIDEO_HEIGHT)
    points = [f"{i + 1}. {t.capitalize()}" for i, t in enumerate(others[:3])]
    paths.append(
        _save_frame(
            image,
            draw,
            [
                ("bold", 36, "JUGA TRENDING", accent, 0),
                ("regular", 62, "\n".join(points) if points else "Belum ada tren lain hari ini", white, 80),
                ("regular", 44, "Baca caption lengkap di Telegram untuk konteks tiap topik.", muted, 80),
                ("bold", 36, footer, accent, 0),
            ],
            os.path.join(output_dir, f"frame-2-{stamp}.png"),
            VIDEO_WIDTH,
            VIDEO_HEIGHT,
        )
    )

    image, draw = _gradient_background(VIDEO_WIDTH, VIDEO_HEIGHT)
    paths.append(
        _save_frame(
            image,
            draw,
            [
                ("bold", 36, "GILIRANMU", accent, 0),
                ("bold", 92, "KOMENTARI\nPENDAPATMU", white, 120),
                ("regular", 48, "Pilih topik yang paling menarik dan tulis alasannya di komentar.", muted, 80),
                ("bold", 44, "#" + footer.replace(" ", ""), accent, 140),
            ],
            os.path.join(output_dir, f"frame-3-{stamp}.png"),
            VIDEO_WIDTH,
            VIDEO_HEIGHT,
        )
    )

    print(f"[IMAGE] {len(paths)} frame video dibuat di {output_dir}")
    return paths
