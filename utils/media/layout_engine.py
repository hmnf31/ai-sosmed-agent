"""Mesin tampilan: kanvas, palet, dan primitif gambar.

Modul ini tidak tahu apa pun soal AI maupun Telegram. Yang dia terima hanyalah
Brand Profile dan style preset, lalu menggambarnya. Dengan begitu renderer tidak
perlu menebak gaya: warna, skala huruf, jarak, dan bentuk panel semuanya datang
dari config.

Istilah penting:

- **canvas**  ukuran gambar dan margin aman untuk format tertentu.
- **palette** warna yang sudah diurai ke RGB, siap dipakai Pillow.
- **layout** susunan elemen: `standard` untuk konten, `table` untuk klasemen.
"""
import os

from PIL import Image, ImageDraw

#: Ukuran tiap format. Angka ini yang dipakai QA sebelum file dikirim.
CANVASES = {
    "square": {"width": 1080, "height": 1080, "margin_ratio": 0.082},
    "portrait": {"width": 1080, "height": 1350, "margin_ratio": 0.076},
    "reel": {"width": 1080, "height": 1920, "margin_ratio": 0.068},
    "story": {"width": 1080, "height": 1920, "margin_ratio": 0.068},
}

DEFAULT_CANVAS = "square"

#: Perlakuan latar yang dipahami mesin. Style preset hanya boleh memakai salah satu.
BACKGROUND_TREATMENTS = ("solid", "gradient_vertical", "gradient_diagonal", "band_top")

#: Bentuk panel yang dipahami mesin.
PANEL_STYLES = ("soft", "solid", "outline")

#: Tekstur latar yang dipahami mesin. `board` dipakai akun catur supaya pola
#: papan catur langsung terbaca tanpa membaca teks.
TEXTURES = ("none", "grid", "board", "diagonal_hatch")


def resolve_canvas(fmt=None):
    """Mengembalikan spec kanvas untuk format tertentu."""
    key = (fmt or DEFAULT_CANVAS).strip().lower()
    spec = CANVASES.get(key) or CANVASES[DEFAULT_CANVAS]
    result = dict(spec)
    result["name"] = key if key in CANVASES else DEFAULT_CANVAS
    result["margin"] = int(result["width"] * result["margin_ratio"])
    result["content_width"] = result["width"] - 2 * result["margin"]
    return result


def canvas_size(fmt=None):
    spec = resolve_canvas(fmt)
    return spec["width"], spec["height"]


def hex_to_rgb(value, default=(0, 0, 0)):
    """Ubah `#RRGGBB` atau `#RGB` menjadi tuple RGB."""
    text = str(value or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return default
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return default


def relative_luminance(rgb):
    """Kecerahan 0-1. Dipakai untuk memilih versi watermark yang terbaca."""
    channels = []
    for value in (rgb or (0, 0, 0))[:3]:
        ratio = value / 255
        channels.append(ratio / 12.92 if ratio <= 0.03928 else ((ratio + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def is_light_background(brand):
    """True bila latar akun cenderung terang."""
    colors = (brand or {}).get("colors") or {}
    top = hex_to_rgb(colors.get("background"), (0, 0, 0))
    bottom = hex_to_rgb(colors.get("background_alt"), top)
    return (relative_luminance(top) + relative_luminance(bottom)) / 2 >= 0.45


def palette(brand):
    """Warna brand yang sudah diurai ke RGB."""
    colors = (brand or {}).get("colors") or {}
    names = ("background", "background_alt", "surface", "primary", "secondary",
             "accent", "text", "muted", "on_primary")
    result = {name: hex_to_rgb(colors.get(name)) for name in names}
    result["surface"] = result.get("surface") or result["background"]
    return result


def _font(kind, size):
    from utils.image_maker import _load_font

    return _load_font(kind, max(8, int(size)))


def _wrap(draw, text, font, max_width, max_lines=None):
    from utils.image_maker import _wrap

    return _wrap(draw, text, font, max_width, max_lines)


def _wrap_checked(draw, text, font, max_width, max_lines, label, issues):
    """Bungkus teks dan catat kalau ada bagian yang terpotong.

    Pemotongan diam-diam adalah kesalahan yang paling sering Luput di render:
    kalimat benar, tapi poin terakhir hilang. Jadi ini dilaporkan, bukan
    disembunyikan.
    """
    lines = _wrap(draw, text, font, max_width, max_lines)
    if max_lines:
        penuh = _wrap(draw, text, font, max_width, None)
        if len(penuh) > max_lines:
            message = f"{label} terpotong ({len(penuh)} baris jadi {max_lines})"
            if issues is not None:
                issues.append(message)
    return lines


def point_block_height(brand, style, points, width, limit=None, in_panel=True):
    """Tinggi blok poin dalam piksel. Dipakai untuk menyisakan ruang CTA."""
    typo = (style or {}).get("typography") or {}
    spacing = (style or {}).get("spacing") or {}
    size = int(width * (typo.get("body_scale") or 0.034))
    spacing_line = int(size * (typo.get("body_line_spacing") or 1.38))
    gap = int(width * (spacing.get("gap") or 0.028))
    items = list(points or [])[:limit or len(points or [])]
    if not items:
        return 0

    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    indent = int(size * 0.42) + int(gap * 1.6)
    height = 0
    for item in items:
        wrapped = _wrap(draw, str(item), font=_font(typo.get("body") or "regular", size),
                        max_width=width - indent, max_lines=typo.get("body_max_lines") or 2)
        height += len(wrapped) * spacing_line
    height += gap * (len(items) - 1)
    if in_panel:
        pad = int(width * (spacing.get("panel_padding") or 0.036))
        height += pad
    return height


def fit_point_limit(brand, style, points, width, available, hard_limit, in_panel=True):
    """Jumlah poin yang muat di ruang tersisa.

    Kalau tidak semua muat, hasilnya dikurangi dan pemanggil bisa melaporkannya
    ke QA. Lebih baik satu poin hilang dengan laporan jelas daripada seluruh
    blok menimpa CTA atau tepi kanvas.
    """
    if not points or available <= 0:
        return 0
    chosen = min(len(points), hard_limit)
    while chosen > 1 and point_block_height(brand, style, points, width, chosen,
                                            in_panel=in_panel) > available:
        chosen -= 1
    return chosen


def _paragraph(draw, lines, font, x, y, fill, line_spacing=1.35):
    from utils.image_maker import _draw_paragraph

    return _draw_paragraph(draw, lines, font, x, y, fill, line_spacing)


# ---------------------------------------------------------------------------
# Latar
# ---------------------------------------------------------------------------

#: Pita warna di atas kanvas untuk gaya editorial. Nilainya dikirim ke
#: template_engine supaya teks tidak pernah mulai di dalam pita.
BAND_RATIO = 0.12


def top_inset(brand, style, canvas=None):
    """Tinggi area yang harus dikosongkan di atas konten."""
    treatment = ((style or {}).get("canvas") or {}).get("background")
    if treatment != "band_top":
        return 0
    return int(resolve_canvas(canvas)["height"] * BAND_RATIO)


def paint_background(brand, style, canvas):
    """Menggambar latar sesuai style preset dan mengembalikan (image, draw)."""
    spec = resolve_canvas(canvas)
    colors = palette(brand)
    treatment = ((style or {}).get("canvas") or {}).get("background") or "gradient_vertical"

    image = Image.new("RGB", (spec["width"], spec["height"]), colors["background"])
    draw = ImageDraw.Draw(image)
    top, bottom = colors["background"], colors["background_alt"]

    if treatment == "solid":
        pass
    elif treatment == "gradient_diagonal":
        height, width = spec["height"], spec["width"]
        for y in range(height):
            ratio = y / (height - 1)
            row = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
            draw.line([(0, y), (int(width * ratio), y)], fill=row)
            draw.line([(int(width * ratio), y), (width, y)],
                      fill=tuple(int(bottom[i] + (top[i] - bottom[i]) * ratio) for i in range(3)))
    else:
        for y in range(spec["height"]):
            ratio = y / (spec["height"] - 1)
            draw.line(
                [(0, y), (spec["width"], y)],
                fill=tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3)),
            )

    if treatment == "band_top":
        band = top_inset(brand, style, canvas)
        draw.rectangle([0, 0, spec["width"], band], fill=colors["accent"])
        draw.line([(0, band), (spec["width"], band)], fill=colors["primary"],
                  width=max(4, int(spec["height"] * 0.006)))

    texture = ((style or {}).get("canvas") or {}).get("texture") or "none"
    if texture == "grid":
        _paint_grid(draw, spec, colors)
    elif texture == "board":
        _paint_board(draw, spec, colors)
    elif texture == "diagonal_hatch":
        _paint_hatch(draw, spec, colors)
    if ((style or {}).get("overlay") or {}).get("vignette"):
        _paint_vignette(image, colors, ((style["overlay"].get("vignette"))))
    return image, draw


def _paint_grid(draw, spec, colors, step=90):
    """Grid tipis di atas latar gelap; ciri visual gaya esports."""
    line = tuple(int(colors["accent"][i] * 0.18) for i in range(3))
    for x in range(0, spec["width"] + 1, step):
        draw.line([(x, 0), (x, spec["height"])], fill=line, width=1)
    for y in range(0, spec["height"] + 1, step):
        draw.line([(0, y), (spec["width"], y)], fill=line, width=1)


def _paint_board(draw, spec, colors, cell=None):
    """Pola papan catur samar. Ciri visual akun catur.

    Kotak gelap dibuat dari warna surface, bukan hitam, supaya tetap satu keluarga
    dengan palet akun dan tidak menabrak teks di atasnya.
    """
    cell = cell or max(60, int(spec["width"] / 12))
    dark = tuple(int(colors["surface"][i] * 0.85) for i in range(3))
    for row in range(-1, spec["height"] // cell + 2):
        for column in range(-1, spec["width"] // cell + 2):
            if (row + column) % 2:
                continue
            x0, y0 = column * cell, row * cell
            draw.rectangle([x0, y0, x0 + cell, y0 + cell], fill=dark)


def _paint_hatch(draw, spec, colors, gap=54):
    """Garis diagonal tipis; dipakai gaya editorial agar tidak terasa polos."""
    line = tuple(int(colors["muted"][i] * 0.16) for i in range(3))
    for offset in range(-spec["height"], spec["width"] + spec["height"], gap):
        draw.line([(offset, 0), (offset + spec["height"], spec["height"])], fill=line, width=1)


def _paint_vignette(image, colors, strength):
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    alpha = int(max(0.0, min(1.0, float(strength))) * 110)
    width, height = image.size
    for step in range(12):
        inset = int(step * min(width, height) * 0.03)
        draw.rectangle([inset, inset, width - inset, height - inset],
                       outline=(0, 0, 0, max(0, alpha - step * (alpha // 14))),
                       width=max(2, int(min(width, height) * 0.02)))
    image.paste(overlay, (0, 0), overlay)


# ---------------------------------------------------------------------------
# Elemen
# ---------------------------------------------------------------------------

def accent_bar(draw, brand, style, x, y, width=None):
    """Garis aksen di bawah label. Bentuknya mengikuti style preset."""
    colors = palette(brand)
    canvas_style = (style or {}).get("canvas") or {}
    kind = canvas_style.get("accent_bar") or "medium"
    width = width or 110
    if kind == "thin":
        height, radius = 5, 3
    elif kind == "block":
        height, radius = 18, 6
    else:
        height, radius = 11, 5
    draw.rounded_rectangle([x, y, x + width, y + height], radius=radius, fill=colors["accent"])
    return y + height


def panel(draw, brand, style, box, radius=None):
    """Panel latar untuk daftar poin: tipis, solid, atau garis saja."""
    colors = palette(brand)
    kind = ((style or {}).get("canvas") or {}).get("panel") or "soft"
    radius = radius if radius is not None else int(((style or {}).get("spacing") or {}).get(
        "corner_radius", 20))
    if kind == "solid":
        draw.rounded_rectangle(box, radius=radius, fill=colors["surface"])
    elif kind == "outline":
        draw.rounded_rectangle(box, radius=radius, outline=colors["accent"], width=3)
    else:
        draw.rounded_rectangle(box, radius=radius, fill=colors["surface"])


def divider(draw, brand, style, x, y, width):
    colors = palette(brand)
    thickness = {"hairline": 1, "medium": 3, "thick": 5}.get(
        ((style or {}).get("canvas") or {}).get("rule") or "medium", 2
    )
    draw.line([(x, y), (x + width, y)], fill=colors["muted"], width=thickness)


def draw_label(draw, brand, style, text, x, y, width):
    """Label kecil kapital di atas judul, mis. 'TREN TERKINI'."""
    colors = palette(brand)
    typo = (style or {}).get("typography") or {}
    size = int(width * (typo.get("label_scale") or 0.028))
    font = _font(typo.get("label") or "bold", size)
    label = str(text or "").strip()
    if typo.get("label_caps", True):
        label = label.upper()
    if not label:
        return y
    draw.text((x, y), label, font=font, fill=colors["accent"])
    return accent_bar(draw, brand, style, x, y + size + int(size * 0.55))


def draw_title(draw, brand, style, text, x, y, width, issues=None):
    """Judul besar, dipecah otomatis sesuai lebar kanvas."""
    colors = palette(brand)
    typo = (style or {}).get("typography") or {}
    size = int(width * (typo.get("heading_scale") or 0.072))
    font = _font(typo.get("heading") or "bold", size)
    lines = _wrap_checked(draw, str(text or "").upper(), font, width,
                          typo.get("heading_max_lines") or 4, "judul", issues)
    return _paragraph(draw, lines, font, x, y, colors["text"],
                      typo.get("heading_line_spacing") or 1.16)


def draw_subtitle(draw, brand, style, text, x, y, width, issues=None):
    colors = palette(brand)
    typo = (style or {}).get("typography") or {}
    size = int(width * (typo.get("body_scale") or 0.034))
    font = _font(typo.get("body") or "regular", size)
    lines = _wrap_checked(draw, str(text or ""), font, width,
                          typo.get("body_max_lines") or 2, "subjudul", issues)
    if not lines:
        return y
    return _paragraph(draw, lines, font, x, y, colors["muted"],
                      typo.get("body_line_spacing") or 1.38)


def point_marker(size, marker, color):
    """Bentuk penanda tiap poin, mengikuti gaya akun."""
    from PIL import Image as _Image

    box = int(size)
    layer = _Image.new("RGBA", (box + 4, box + 4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    if marker == "square":
        draw.rectangle([0, 0, box, box], fill=color)
    elif marker == "dot":
        draw.ellipse([0, 0, box, box], fill=color)
    elif marker == "rank":
        draw.ellipse([0, 0, box, box], fill=color)
        draw.ellipse([2, 2, box - 2, box - 2], outline=(255, 255, 255), width=2)
    else:
        draw.rounded_rectangle([0, box // 3, box, box - box // 3], radius=3, fill=color)
    return layer


def draw_points(draw, brand, style, points, x, y, width, limit=3, in_panel=True):
    """Daftar poin dengan penanda kiri. Mengembalikan posisi y berikutnya."""
    colors = palette(brand)
    typo = (style or {}).get("typography") or {}
    spacing = (style or {}).get("spacing") or {}
    marker = (style or {}).get("point_marker") or "dash"

    items = [str(p) for p in (points or []) if str(p).strip()][:limit]
    if not items:
        return y

    size = int(width * (typo.get("body_scale") or 0.034))
    font = _font(typo.get("body") or "regular", size)
    spacing_line = int(size * (typo.get("body_line_spacing") or 1.38))
    marker_size = int(size * 0.42)
    gap = int(width * (spacing.get("gap") or 0.028))
    indent = marker_size + int(gap * 1.6)

    wrapped = []
    for item in items:
        lines = _wrap(draw, item, font, width - indent, typo.get("body_max_lines") or 2)
        wrapped.append(lines or [item])

    total_height = sum(len(lines) * spacing_line for lines in wrapped)
    total_height += gap * (len(wrapped) - 1)
    pad = int(width * (spacing.get("panel_padding") or 0.036))
    box = [x - pad, y - pad // 2, x + width + pad, y + total_height + pad]
    if in_panel:
        panel(draw, brand, style, box)

    cursor = y
    for index, lines in enumerate(wrapped):
        draw.bitmap((x, cursor + (spacing_line - marker_size) // 2),
                    point_marker(marker_size, marker, colors["accent"]))
        _paragraph(draw, lines, font, x + indent, cursor, colors["text"],
                   typo.get("body_line_spacing") or 1.38)
        cursor += len(lines) * spacing_line + gap
    return cursor - gap


def draw_cta(draw, brand, style, text, x, y, width, issues=None):
    """Ajakan bertindak di bagian bawah."""
    colors = palette(brand)
    typo = (style or {}).get("typography") or {}
    size = int(width * (typo.get("cta_scale") or 0.042))
    font = _font("bold", size)
    lines = _wrap_checked(draw, str(text or "").upper(), font, width, 2, "CTA", issues)
    if not lines:
        return y
    return _paragraph(draw, lines, font, x, y, colors["accent"], 1.24)


def draw_table(draw, brand, style, rows, x, y, width, limit=6):
    """Tabel singkat untuk klasemen: baris per pemain, bukan daftar poin."""
    colors = palette(brand)
    typo = (style or {}).get("typography") or {}
    spacing = (style or {}).get("spacing") or {}
    marker = (style or {}).get("point_marker") or "rank"

    items = [r for r in (rows or []) if any(str(c).strip() for c in r)][:limit]
    if not items:
        return y

    size = int(width * ((typo.get("body_scale") or 0.034) * 0.95))
    font = _font(typo.get("body") or "bold", size)
    rank_font = _font("bold", int(size * 0.85))
    step = int(size * 2.0)
    chip = int(size * 1.25)
    pad = int(width * (spacing.get("panel_padding") or 0.036))
    columns = max(len(r) for r in items)
    name_width = int(width * 0.56)

    panel(draw, brand, style,
          [x - pad, y - pad // 2, x + width + pad, y + step * len(items) + pad // 2])

    cursor = y
    for index, row in enumerate(items):
        draw.bitmap((x, cursor + (step - chip) / 2), point_marker(chip, marker, colors["accent"]))
        rank = str(index + 1)
        rbox = draw.textbbox((0, 0), rank, font=rank_font)
        draw.text((x + (chip - (rbox[2] - rbox[0])) / 2, cursor + (step - (rbox[3] - rbox[1])) / 2
                   - rbox[1]), rank, font=rank_font, fill=colors["background"])
        name = str(row[0]) if row else ""
        draw.text((x + chip + int(size * 0.7), cursor + (step - (rbox[3] - rbox[1])) / 2 - rbox[1]),
                  name, font=font, fill=colors["text"])
        if columns > 1:
            value = str(row[1]) if len(row) > 1 else ""
            vbox = draw.textbbox((0, 0), value, font=font)
            draw.text((x + width - (vbox[2] - vbox[0]), cursor
                       + (step - (rbox[3] - rbox[1])) / 2 - rbox[1]),
                      value, font=font, fill=colors["accent"])
        cursor += step
    return cursor


def stamp(text=None):
    """Stempel waktu untuk pojok bawah."""
    from datetime import datetime, timedelta, timezone

    wib = timezone(timedelta(hours=7))
    return text or datetime.now(wib).strftime("%d %B %Y, %H:%M WIB")


def media_size_ok(path, fmt=None):
    """Cek cepat ukuran file terhadap format yang diharapkan."""
    expected = canvas_size(fmt)
    try:
        with Image.open(path) as image:
            return image.size == expected, image.size, expected
    except OSError:
        return False, None, expected


def output_dir():
    return os.getenv("CONTENT_OUTPUT_DIR") or "output"