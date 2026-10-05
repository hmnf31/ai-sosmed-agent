"""Pembuat logo dan watermark per akun.

Watermark bukan sekadar menulis handle di pojok gambar. Tiap akun punya satu
Watermark Profile: bentuk mark, warna, posisi, opacity, dan ukuran relatif.
Semua itu dibaca dari `branding/<akun>/brand.json`, jadi mengganti gaya cukup
dengan mengubah config, bukan kode.

Aset dibuat sebagai PNG di `assets/branding/<akun>/`:

    logo.png                 mark + monogram, untuk keperluan identitas
    watermark_<varian>.png   mark + handle, siap dikomposit ke frame

Varian yang tersedia:

- `primary`   tanda tangan akun (ada plat berwarna).
- `on_light`  tanpa plat, tinta gelap; untuk latar terang.
- `on_dark`   tanpa plat, tinta terang; untuk latar gelap.

Renderer memakai file yang sudah dibuat ini, bukan menggambar ulang tiap frame,
supaya hasil antar frame konsisten dan bisa diinspeksi.
"""
import os

from PIL import Image, ImageDraw

from branding import loader

ASSETS_DIR = os.getenv("BRANDING_ASSETS_DIR") or os.path.join("assets", "branding")

#: Ukuran kerja aset. Dijaga besar supaya tetap tajam setelah dikecilkan.
LOGO_SIZE = 1024
WATERMARK_WIDTH = 1200
WATERMARK_HEIGHT = 300
WATERMARK_PAD = 40

MARK_DRAWERS = ("ring", "bolt", "pawn", "hanger", "crown")


def asset_dir(account_id):
    return os.path.join(ASSETS_DIR, account_id or "")


def asset_path(account_id, name):
    return os.path.join(asset_dir(account_id), name)


def logo_path(account_id):
    return asset_path(account_id, "logo.png")


def watermark_path(account_id, variant):
    return asset_path(account_id, f"watermark_{variant or 'primary'}.png")


def _rgba(hex_color, alpha=255):
    """Ubah hex ke tuple RGBA. Nilai kosong berarti transparan."""
    text = str(hex_color or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return None
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16), alpha)
    except ValueError:
        return None


def _font(kind, size):
    from utils.image_maker import _load_font

    return _load_font(kind, int(size))


# ---------------------------------------------------------------------------
# Bentuk mark
# ---------------------------------------------------------------------------

def _draw_ring(draw, box, color, width):
    draw.ellipse(box, outline=color, width=width)


def _draw_bolt(draw, box, color, width):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    points = [
        (x0 + 0.58 * w, y0 + 0.04 * h),
        (x0 + 0.22 * w, y0 + 0.56 * h),
        (x0 + 0.44 * w, y0 + 0.56 * h),
        (x0 + 0.38 * w, y0 + 0.96 * h),
        (x0 + 0.78 * w, y0 + 0.44 * h),
        (x0 + 0.56 * w, y0 + 0.44 * h),
    ]
    draw.polygon(points, fill=color)


def _draw_pawn(draw, box, color, width):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    draw.ellipse([x0 + 0.32 * w, y0, x0 + 0.68 * w, y0 + 0.30 * h], fill=color)
    draw.polygon(
        [
            (x0 + 0.40 * w, y0 + 0.30 * h),
            (x0 + 0.60 * w, y0 + 0.30 * h),
            (x0 + 0.78 * w, y0 + 0.68 * h),
            (x0 + 0.22 * w, y0 + 0.68 * h),
        ],
        fill=color,
    )
    draw.rounded_rectangle(
        [x0 + 0.10 * w, y0 + 0.76 * h, x0 + 0.90 * w, y0 + 0.98 * h],
        radius=int(h * 0.08),
        fill=color,
    )


def _draw_hanger(draw, box, color, width):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    hook_r = 0.09 * w
    hook_cx = x0 + 0.5 * w
    hook_cy = y0 + 0.11 * h
    draw.arc(
        [hook_cx - hook_r, hook_cy - hook_r, hook_cx + hook_r, hook_cy + hook_r],
        start=180,
        end=20,
        fill=color,
        width=width,
    )
    draw.line([(hook_cx, hook_cy), (x0 + 0.5 * w, y0 + 0.28 * h)], fill=color, width=width)
    draw.line(
        [(x0 + 0.10 * w, y0 + 0.90 * h), (x0 + 0.5 * w, y0 + 0.28 * h)],
        fill=color,
        width=width,
    )
    draw.line(
        [(x0 + 0.90 * w, y0 + 0.90 * h), (x0 + 0.5 * w, y0 + 0.28 * h)],
        fill=color,
        width=width,
    )
    draw.line(
        [(x0 + 0.10 * w, y0 + 0.90 * h), (x0 + 0.90 * w, y0 + 0.90 * h)],
        fill=color,
        width=width,
    )


def _draw_crown(draw, box, color, width):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    points = [
        (x0 + 0.04 * w, y0 + 0.86 * h),
        (x0 + 0.14 * w, y0 + 0.20 * h),
        (x0 + 0.34 * w, y0 + 0.54 * h),
        (x0 + 0.50 * w, y0 + 0.10 * h),
        (x0 + 0.66 * w, y0 + 0.54 * h),
        (x0 + 0.86 * w, y0 + 0.20 * h),
        (x0 + 0.96 * w, y0 + 0.86 * h),
    ]
    draw.polygon(points, fill=color)
    draw.rounded_rectangle(
        [x0 + 0.06 * w, y0 + 0.90 * h, x0 + 0.94 * w, y0 + 0.99 * h],
        radius=int(h * 0.04),
        fill=color,
    )


MARK_FUNCTIONS = {
    "ring": _draw_ring,
    "bolt": _draw_bolt,
    "pawn": _draw_pawn,
    "hanger": _draw_hanger,
    "crown": _draw_crown,
}


def draw_mark(draw, mark, box, color, stroke=None):
    """Menggambar bentuk mark satu akun di dalam kotak."""
    function = MARK_FUNCTIONS.get(mark or "crown", _draw_crown)
    x0, y0, x1, y1 = box
    stroke = stroke or max(2, int((x1 - x0) * 0.07))
    function(draw, box, color, stroke)


# ---------------------------------------------------------------------------
# Bangun aset
# ---------------------------------------------------------------------------

def build_logo(account_id, account=None, size=LOGO_SIZE):
    """Membuat logo akun: mark di atas, monogram di bawah, latar transparan."""
    brand = loader.load_profile(account_id, account=account)
    color = _rgba((brand.get("watermark") or {}).get("variants", {})
                  .get("primary", {}).get("logo")) or (255, 255, 255, 255)

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw_mark(draw, brand.get("mark"), [size * 0.16, size * 0.10, size * 0.84, size * 0.62],
              color)

    font = _font("bold", size * 0.16)
    mono = str(brand.get("monogram") or "")[:4]
    box = draw.textbbox((0, 0), mono, font=font)
    draw.text(((size - (box[2] - box[0])) / 2, size * 0.68), mono, font=font, fill=color)

    target = logo_path(brand.get("account") or account_id)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    image.save(target, "PNG")
    return target


def build_watermark(account_id, variant="primary", account=None,
                    width=WATERMARK_WIDTH, height=WATERMARK_HEIGHT):
    """Membuat satu varian watermark: plat + mark + handle."""
    brand = loader.load_profile(account_id, account=account)
    watermark = brand.get("watermark") or {}
    colors = (watermark.get("variants") or {}).get(variant) or {}
    if not colors:
        raise ValueError(f"Varian watermark '{variant}' tidak ada untuk akun '{account_id}'")

    plate = _rgba(colors.get("plate"))
    logo_color = _rgba(colors.get("logo")) or (255, 255, 255, 255)
    text_color = _rgba(colors.get("text")) or logo_color

    radius = int(height * 0.22)
    if plate:
        image = Image.new("RGBA", (width, height), plate)
        ImageDraw.Draw(image).rounded_rectangle([0, 0, width - 1, height - 1],
                                                radius=radius, fill=plate)
        draw = ImageDraw.Draw(image)
    else:
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

    mark_size = int(height * 0.62)
    top = (height - mark_size) / 2
    draw_mark(draw, brand.get("mark"),
              [WATERMARK_PAD, top, WATERMARK_PAD + mark_size, top + mark_size], logo_color)

    handle = str(brand.get("handle") or "").lstrip("@")
    if handle:
        font = _font("bold", height * 0.26)
        x = WATERMARK_PAD + mark_size + int(height * 0.16)
        box = draw.textbbox((0, 0), handle, font=font)
        draw.text((x, (height - (box[3] - box[1])) / 2 - box[1]), handle, font=font,
                  fill=text_color)

    target = watermark_path(brand.get("account") or account_id, variant)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    image.save(target, "PNG")
    return target


def ensure_logo(account_id, account=None, rebuild=False):
    """Logo siap pakai; hanya digambar ulang bila file belum ada."""
    target = logo_path(account_id)
    if rebuild or not os.path.exists(target):
        return build_logo(account_id, account=account)
    return target


def ensure_watermark(account_id, variant="primary", account=None, rebuild=False):
    """Watermark siap pakai; hanya digambar ulang bila file belum ada."""
    target = watermark_path(account_id, variant)
    if rebuild or not os.path.exists(target):
        return build_watermark(account_id, variant, account=account)
    return target


def build_all(account_ids=None, account=None, rebuild=True):
    """Membangun logo dan ketiga varian watermark untuk beberapa akun."""
    targets = account_ids or loader.list_profile_ids()
    created = []
    for account_id in targets:
        created.append(build_logo(account_id, account=account))
        for variant in ("primary", "on_light", "on_dark"):
            created.append(build_watermark(account_id, variant, account=account))
    if rebuild:
        print(f"[BRAND] {len(created)} aset branding dibuat di {ASSETS_DIR}")
    return created