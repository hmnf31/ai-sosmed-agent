"""Mesin watermark: menempelkan tanda tangan akun ke hasil render.

Aturan yang dijaga modul ini:

- Varian dipilih otomatis dari latar, bukan ditebak pemanggil. Latar terang
  memakai tinta gelap, latar gelap memakai tinta terang.
- Ukuran memakai skala relatif terhadap lebar kanvas, jadi proporsinya sama di
  kartu 1080x1080 maupun di frame 1080x1920.
- Margin dihitung dari safe area, dan kotak penempatan dikembalikan supaya QA
  bisa memastikan watermark tidak menimpa tepi kanvas.
- Identitas akun diambil dari Brand Profile, bukan dari argumen bebas, jadi
  watermark akun lain tidak bisa terpakai untuk render ini.
"""
import os

from PIL import Image

from utils.media import asset_loader, layout_engine

POSITIONS = ("top_left", "top_right", "bottom_left", "bottom_right")

DEFAULT_MARGIN = 56
DEFAULT_SCALE = 0.12
DEFAULT_OPACITY = 0.8


def choose_variant(brand):
    """Varian watermark yang terbaca di latar akun ini."""
    watermark = (brand or {}).get("watermark") or {}
    variants = watermark.get("variants") or {}
    forced = watermark.get("variant")
    if forced and variants.get(forced):
        return forced
    return "on_light" if layout_engine.is_light_background(brand) else "on_dark"


def box_for(brand, canvas, width, height):
    """Kotak penempatan watermark di dalam kanvas."""
    spec = layout_engine.resolve_canvas(canvas)
    watermark = (brand or {}).get("watermark") or {}
    position = watermark.get("position") or "bottom_right"
    if position not in POSITIONS:
        position = "bottom_right"
    margin = int(watermark.get("margin") or DEFAULT_MARGIN)
    if watermark.get("safe_area", True):
        # Safe area: jarak dari tepi tidak boleh lebih kecil dari margin konten.
        margin = max(margin, int(spec["margin"] * 0.6))

    # Nama posisi dibaca vertikal-dulu: 'top_left' -> atas, kiri.
    vertical, horizontal = position.split("_")
    x = margin if horizontal == "left" else spec["width"] - margin - width
    y = margin if vertical == "top" else spec["height"] - margin - height
    return int(x), int(y)


def _resized_asset(path, target_width, opacity):
    with Image.open(path) as source:
        mark = source.convert("RGBA")
        ratio = target_width / mark.width
        mark = mark.resize((target_width, max(1, int(mark.height * ratio))), Image.LANCZOS)
    if opacity < 1:
        alpha = mark.getchannel("A").point(lambda value: int(value * opacity))
        mark.putalpha(alpha)
    return mark


def apply(image, brand, canvas="square", variant=None):
    """Menempelkan watermark ke gambar dan mengembalikan detail penempatannya.

    Mengembalikan dict berisi `variant`, `box`, `asset`, dan `applied`. Aset
    yang gagal dibuat tidak menggagalkan render: `applied` menjadi False dan
    QA bisa melaporkan masalahnya.
    """
    spec = layout_engine.resolve_canvas(canvas)
    chosen = variant or choose_variant(brand)

    account_id = (brand or {}).get("account") or ""
    if not account_id:
        return {"variant": chosen, "box": None, "asset": None, "applied": False,
                "error": "Brand Profile tidak punya id akun"}

    try:
        path = asset_loader.watermark_asset(brand, chosen)
    except Exception as e:  # aset gagal bukan alasan menggagalkan konten
        return {"variant": chosen, "box": None, "asset": None, "applied": False,
                "error": str(e)}

    if not path or not os.path.exists(path):
        return {"variant": chosen, "box": None, "asset": path, "applied": False,
                "error": f"aset watermark tidak ditemukan: {path}"}

    watermark = (brand or {}).get("watermark") or {}
    target_width = max(1, int(spec["width"] * float(watermark.get("scale") or DEFAULT_SCALE)))
    opacity = float(watermark.get("opacity") or DEFAULT_OPACITY)
    mark = _resized_asset(path, target_width, opacity)
    x, y = box_for(brand, canvas, mark.width, mark.height)

    canvas_image = image if image.mode == "RGBA" else image.convert("RGBA")
    canvas_image.paste(mark, (x, y), mark)
    if canvas_image is not image:
        image.paste(canvas_image.convert(image.mode), (0, 0))

    return {
        "variant": chosen,
        "box": (x, y, mark.width, mark.height),
        "asset": path,
        "applied": True,
    }


def audit(image, result, brand=None):
    """Memastikan watermark berada di dalam kanvas dan tidak keluar area."""
    if not result or not result.get("applied") or not result.get("box"):
        return []

    problems = []
    x, y, width, height = result["box"]
    if x < 0 or y < 0:
        problems.append(f"watermark keluar dari kanvas di ({x}, {y})")
    if x + width > image.size[0]:
        problems.append(f"watermark melewati tepi kanan kanvas ({x + width} > {image.size[0]})")
    if y + height > image.size[1]:
        problems.append(f"watermark melewati tepi bawah kanvas ({y + height} > {image.size[1]})")
    if problems and ((brand or {}).get("watermark") or {}).get("safe_area"):
        problems.append("safe area: watermark harus di dalam kanvas")
    return problems