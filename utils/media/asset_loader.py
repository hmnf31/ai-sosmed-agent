"""Pemuat aset branding untuk renderer.

Aset watermark dan logo dibuat oleh `branding.watermark`, lalu disimpan di
`assets/branding/<akun>/`. Modul ini hanya menentukan file mana yang harus
dibaca dan mengembalikan path yang siap dikomposit. Tidak ada gambar yang
dibuat di sini, supaya ada satu tempat yang bertanggung jawab atas pembuatan
aset.
"""
import os

from branding import loader, watermark

BRAND_ROOT = os.getenv("BRANDING_ASSETS_DIR") or watermark.ASSETS_DIR

FORMAT_BY_INTENT = {
    "image": "square",
    "video": "reel",
    "square": "square",
    "portrait": "portrait",
    "reel": "reel",
    "story": "story",
}


def canvas_for(content_format=None, explicit=None):
    """Menentukan nama kanvas dari format yang diminta.

    `explicit` menang, lalu format intent. Nilai yang tidak dikenal turun ke
    `square` supaya render tidak gagal karena salah ketik.
    """
    for candidate in (explicit, content_format):
        if not candidate:
            continue
        key = str(candidate).strip().lower()
        if key in FORMAT_BY_INTENT:
            return FORMAT_BY_INTENT[key]
    return "square"


def brand_of(source):
    """Menerima dict akun, isi brand.json mentah, atau id akun.

    Ketiganya dikembalikan sebagai Brand Profile yang sudah punya `style`.
    Bedanya penting: isi brand.json mentah belum punya blok `style`, sehingga
    kalau salah dikira dict akun, hasilnya profil generik tanpa warna akun.
    """
    if loader.is_profile(source):
        return loader.resolve_brand(brand=source)
    return loader.resolve_brand(account=source)


def account_id_of(source):
    if isinstance(source, dict):
        return loader.brand_id_for(source) or source.get("id") or ""
    return str(source or "")


def watermark_asset(brand, variant, rebuild=False):
    """Path watermark satu varian, dibuat otomatis bila belum ada."""
    account_id = (brand or {}).get("account") or ""
    if not account_id:
        return None
    return watermark.ensure_watermark(account_id, variant, rebuild=rebuild)


def logo_asset(brand, rebuild=False):
    """Path logo akun, dibuat otomatis bila belum ada."""
    account_id = (brand or {}).get("account") or ""
    if not account_id:
        return None
    return watermark.ensure_logo(account_id, rebuild=rebuild)


def list_assets(account_id):
    """Daftar nama aset branding yang sudah ada untuk satu akun."""
    folder = os.path.join(BRAND_ROOT, account_id or "")
    if not os.path.isdir(folder):
        return []
    return sorted(name for name in os.listdir(folder) if name.endswith(".png"))