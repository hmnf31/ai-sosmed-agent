"""Pemeriksa Brand Profile dan penjaga branding silang.

Dua pekerjaan berbeda:

1. `validate_profile()` memastikan profil sebuah akun punya semua field wajib,
   sehingga renderer tidak pernah menebak nilai yang tidak ada.
2. `assert_same_account()` memastikan template dan watermark yang dipakai render
   memang milik akun tersebut. Ini yang mencegah bug "mlbb memakai template
   wedding" berhenti lebih awal, bukan setelah file terkirim ke Telegram.
"""
import os
import re

HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

#: Field yang wajib ada di setiap Brand Profile.
REQUIRED_TOP_LEVEL = ("account", "label", "handle", "mark", "monogram",
                       "style_preset", "identity", "colors", "typography",
                       "watermark", "templates")

#: Warna yang selalu dibutuhkan renderer.
REQUIRED_COLORS = ("background", "background_alt", "surface", "primary", "accent",
                   "text", "muted")

#: Varian watermark minimal: tanda tangan akun dan dua versi keterbacaan.
REQUIRED_WATERMARK_VARIANTS = ("primary", "on_light", "on_dark")

KNOWN_MARKS = ("ring", "bolt", "pawn", "hanger", "crown")

CANVAS_SIZES = {
    "square": (1080, 1080),
    "portrait": (1080, 1350),
    "reel": (1080, 1920),
    "story": (1080, 1920),
}


class BrandingMismatch(Exception):
    """Template atau watermark dipakai untuk akun yang salah."""


def _is_color(value):
    """Warna harus hex agar bisa diurai tanpa pustaka warna tambahan."""
    return isinstance(value, str) and bool(HEX_RE.match(value.strip()))


def validate_profile(profile):
    """Mengembalikan daftar masalah pada satu Brand Profile.

    Daftar kosong berarti profil aman dipakai. Fungsi ini tidak melempar
    exception supaya pemanggil bisa melaporkan semua masalah sekaligus.
    """
    problems = []
    if not isinstance(profile, dict):
        return ["Brand Profile bukan objek JSON."]

    for field in REQUIRED_TOP_LEVEL:
        if not profile.get(field):
            problems.append(f"field wajib '{field}' kosong")

    account = profile.get("account")
    if not isinstance(account, str) or not re.match(r"^[a-z0-9_]+$", account):
        problems.append(f"account '{account}' harus huruf kecil, angka, dan garis bawah")

    mark = profile.get("mark")
    if mark and mark not in KNOWN_MARKS:
        problems.append(f"mark '{mark}' tidak dikenal. Pilihan: {', '.join(KNOWN_MARKS)}")

    colors = profile.get("colors") or {}
    for key in REQUIRED_COLORS:
        value = colors.get(key)
        if not value:
            problems.append(f"warna wajib '{key}' kosong")
        elif not _is_color(value):
            problems.append(f"warna '{key}' bukan hex: {value!r}")

    watermark = profile.get("watermark") or {}
    variants = watermark.get("variants") or {}
    for name in REQUIRED_WATERMARK_VARIANTS:
        if name not in variants:
            problems.append(f"watermark varian '{name}' belum ada")
            continue
        variant = variants[name] or {}
        if not _is_color(variant.get("logo")):
            problems.append(f"wermark '{name}' butuh warna logo hex")
        if not _is_color(variant.get("text")):
            problems.append(f"watermark '{name}' butuh warna teks hex")
        if "plate" in variant and variant["plate"] is not None and not _is_color(variant["plate"]):
            problems.append(f"watermark '{name}' plate harus hex atau null")

    opacity = watermark.get("opacity", 0.8)
    try:
        value = float(opacity)
    except (TypeError, ValueError):
        problems.append("watermark opacity harus angka")
    else:
        if not 0 < value <= 1:
            problems.append("watermark opacity harus di antara 0 dan 1")

    scale = watermark.get("scale", 0.12)
    try:
        value = float(scale)
    except (TypeError, ValueError):
        problems.append("watermark scale harus angka")
    else:
        # Batas 8%-14% lebar canvas supaya logo tidak menutupi isi frame.
        if not 0.08 <= value <= 0.14:
            problems.append("watermark scale harus di antara 0.08 dan 0.14")

    templates = profile.get("templates") or {}
    if not isinstance(templates, dict) or not templates:
        problems.append("templates harus memuat minimal satu format")
    else:
        for fmt in templates:
            if fmt not in CANVAS_SIZES:
                problems.append(f"format template '{fmt}' tidak dikenal")
            if not isinstance(templates[fmt], list):
                problems.append(f"templates.{fmt} harus berisi daftar nama template")
        # Daftar kosong itu sah: artinya akun mengandalkan template default.

    identity = profile.get("identity") or {}
    if not identity.get("style"):
        problems.append("identity.style kosong")

    return problems


def template_account(template):
    """Akun pemilik sebuah template. Template generik tidak punya akun."""
    return (template or {}).get("account")


def assert_same_account(account_id, template=None, watermark=None, brand=None):
    """Menjaga render tetap milik satu akun.

    `template` dan `watermark` boleh berupa dict atau string id. Template
    generik (tanpa `account`) boleh dipakai semua akun; selain itu harus cocok.
    Watermark harus punya akun yang sama, dan harus ada di brand profil itu.
    """
    account_id = (account_id or "").strip()
    problems = []

    if template:
        owner = template_account(template) if isinstance(template, dict) else _id_owner(template)
        if owner and owner != account_id:
            problems.append(f"template '{template_id(template)}' milik '{owner}', bukan '{account_id}'")
        if isinstance(template, dict):
            style = template.get("style")
            if style and brand and brand.get("style", {}).get("id") not in (None, style):
                problems.append(
                    f"template memakai style '{style}' tapi brand '{account_id}' memakai "
                    f"'{brand.get('style', {}).get('id')}'"
                )

    if watermark:
        if isinstance(watermark, dict):
            mark_account = watermark.get("account")
            variant = watermark.get("variant")
        else:
            # String berarti nama varian (kalau dikenal) atau id aset watermark.
            mark_account = None
            variant = watermark if str(watermark) in REQUIRED_WATERMARK_VARIANTS else None

        if mark_account and mark_account != account_id:
            problems.append(
                f"watermark '{watermark_id(watermark)}' milik '{mark_account}', bukan '{account_id}'"
            )
        if brand:
            variants = (brand.get("watermark") or {}).get("variants") or {}
            if variant:
                if variants and variant not in variants:
                    problems.append(
                        f"varian watermark '{variant}' tidak ada di brand '{account_id}'"
                    )
            elif not mark_account:
                # Bukan varian yang dikenal dan bukan dict bertuan: perlakukan
                # sebagai id aset, dan harus disiapkan oleh akun ini.
                identifier = watermark_id(watermark)
                if brand and account_id not in str(identifier):
                    problems.append(
                        f"watermark '{identifier}' bukan milik akun '{account_id}'"
                    )

    if problems:
        raise BrandingMismatch(" | ".join(problems))
    return True


def template_id(template):
    if isinstance(template, dict):
        return template.get("id") or "?"
    return str(template)


def watermark_id(watermark):
    if isinstance(watermark, dict):
        return watermark.get("id") or watermark.get("variant") or "?"
    return str(watermark)


def watermark_variant(watermark):
    """Nama varian dari dict atau string.

    String hanya dianggap varian kalau namanya dikenal, supaya id aset seperti
    'mlbb_watermark' tidak salah dibaca sebagai varian.
    """
    if isinstance(watermark, dict):
        return watermark.get("variant")
    text = str(watermark or "")
    return text if text in REQUIRED_WATERMARK_VARIANTS else None


_ID_OWNERS = {
    # Template yang namanya diawali nama akun tidak boleh dipakai akun lain.
    "wedding_": "wedding",
    "mlbb_": "mlbb",
    "chess_": "chess",
    "fashion_": "fashion",
}


def _id_owner(identifier):
    """Menebak pemilik dari id template: 'mlbb_patch' -> 'mlbb'."""
    text = str(identifier or "")
    for prefix, owner in _ID_OWNERS.items():
        if text.startswith(prefix):
            return owner
    return None


def verify_render(path, account_id, template=None, watermark=None, brand=None,
                  expected_size=None):
    """Memeriksa satu file hasil render sebelum dikirim ke pengguna.

    Mengembalikan daftar masalah. Daftar kosong berarti aman dikirim. Fungsi ini
    sengaja hanya memeriksa yang bisa dipastikan tanpa menebak: keberadaan file,
    ukuran kanvas, kecocokan akun, dan keberadaan varian watermark.
    """
    problems = []
    if not path or not os.path.exists(path):
        return [f"file hasil render tidak ada: {path}"]

    # Ukuran hanya diperiksa kalau pemanggil tahu format yang diharapkan, supaya
    # render reel tidak salah dianggap salah karena default kartu.
    if expected_size:
        size = tuple(expected_size)
        try:
            from PIL import Image

            with Image.open(path) as image:
                if image.size != size:
                    problems.append(
                        f"ukuran render {image.size[0]}x{image.size[1]} "
                        f"harapan {size[0]}x{size[1]}"
                    )
        except OSError as e:
            problems.append(f"file hasil render tidak bisa dibaca: {e}")

    if brand:
        variants = (brand.get("watermark") or {}).get("variants") or {}
        if not variants:
            problems.append(f"brand '{account_id}' tidak punya varian watermark")

    try:
        assert_same_account(account_id, template=template, watermark=watermark, brand=brand)
    except BrandingMismatch as e:
        problems.append(str(e))

    return problems