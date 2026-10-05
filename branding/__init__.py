"""Brand system: identitas visual per akun.

Tujuan modul ini: setiap akun punya identitas sendiri yang bisa dibaca dari
config, sehingga renderer tidak perlu menebak gaya dan tidak ada akun yang
secara visual tertukar dengan akun lain.

Isi paket:

- `loader`        membaca Brand Profile + style preset per akun.
- `validator`     memeriksa field wajib dan mencegah branding silang.
- `style_registry` memilih template dari akun + kategori + format.
- `watermark`     membangun logo dan watermark tiap akun dari config.

Aturan penting: warna, font, tata letak, dan watermark berasal dari config.
Model AI hanya menulis teks, tidak pernah menentukan tampilan.
"""
from branding.loader import (
    brand_for,
    brand_id_for,
    clear_cache,
    generation_style,
    list_profile_ids,
    load_profile,
    load_style,
    profile_path,
    resolve_brand,
    visual_style,
)
from branding.style_registry import (
    clear_cache as clear_registry_cache,
    duplicate_ids,
    generic_template,
    load_registry,
    select_template,
    templates_for,
)
from branding.validator import (
    BrandingMismatch,
    assert_same_account,
    template_account,
    validate_profile,
    verify_render,
)

__all__ = [
    "BrandingMismatch",
    "assert_same_account",
    "brand_for",
    "brand_id_for",
    "clear_cache",
    "clear_registry_cache",
    "duplicate_ids",
    "generation_style",
    "generic_template",
    "list_profile_ids",
    "load_profile",
    "load_registry",
    "load_style",
    "profile_path",
    "resolve_brand",
    "select_template",
    "template_account",
    "templates_for",
    "validate_profile",
    "verify_render",
    "visual_style",
]