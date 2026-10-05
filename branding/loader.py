"""Pembaca Brand Profile dan style preset per akun.

Satu akun = satu Brand Profile. Profile berisi identitas, warna, tipografi,
aturan watermark, dan daftar template; style preset berisi cara memakainya
(kanvas, skala huruf, jarak, bayangan). Warna tetap milik profile supaya ada
satu sumber kebenaran, sedangkan style preset boleh dipakai ulang antar akun.

Kalau sebuah akun belum punya file profile, loader tidak menggagalkan render:
ia membuat profile generik dari data akun dan menandainya `synthetic` supaya QA
bisa memberi tahu, bukan diam-diam memakai gaya default.
"""
import json
import os

BRANDING_DIR = os.getenv("BRANDING_DIR") or "branding"
STYLES_DIR = os.getenv("STYLES_DIR") or "styles"

PROFILE_NAME = "brand.json"

#: Gaya penulisan konten. Ini masuk ke prompt AI, bukan ke renderer.
DEFAULT_GENERATION_STYLE = {
    "tone": "",
    "sentence_style": "natural_indonesian",
    "hook_style": "clear_value",
    "cta_style": "direct_cta",
    "emoji_level": "low",
    "vocabulary": "",
}

#: Warna netral untuk profile sintetis. Dipakai hanya bila file profile hilang.
NEUTRAL_COLORS = {
    "background": "#1B1D23",
    "background_alt": "#2C3038",
    "surface": "#24272F",
    "primary": "#3A3F4B",
    "secondary": "#7C8494",
    "accent": "#C8CDD6",
    "text": "#F2F3F5",
    "muted": "#A7AEBB",
    "on_primary": "#1B1D23",
}

NEUTRAL_STYLE = {
    "id": "generic_card",
    "canvas": {"background": "gradient_vertical", "accent_bar": "medium",
               "panel": "soft", "rule": "medium", "texture": "none"},
    "typography": {"heading": "bold", "heading_scale": 0.074, "heading_line_spacing": 1.16,
                   "heading_max_lines": 4, "body": "regular", "body_scale": 0.034,
                   "body_line_spacing": 1.38, "body_max_lines": 2, "label": "bold",
                   "label_scale": 0.028, "label_caps": True, "cta_scale": 0.042},
    "spacing": {"margin": 0.082, "gap": 0.026, "corner_radius": 20, "panel_padding": 0.036},
    "shadow": {"enabled": True, "opacity": 0.2, "offset": 5, "blur": 14},
    "overlay": {"scrim": 0.0, "vignette": 0.0},
    "icon_style": "line",
    "point_marker": "dash",
    "watermark": {"position": "bottom_right", "opacity": 0.8, "scale": 0.12,
                  "margin": 56, "safe_area": True},
}

_PROFILE_CACHE = {}
_STYLE_CACHE = {}


def clear_cache():
    """Mengosongkan cache. Dipakai test dan setelah config berubah."""
    _PROFILE_CACHE.clear()
    _STYLE_CACHE.clear()


def list_profile_ids():
    """Daftar akun yang punya file Brand Profile di repository."""
    ids = []
    for entry in sorted(os.listdir(BRANDING_DIR)) if os.path.isdir(BRANDING_DIR) else []:
        folder = os.path.join(BRANDING_DIR, entry)
        if os.path.isdir(folder) and os.path.exists(os.path.join(folder, PROFILE_NAME)):
            ids.append(entry)
    return ids


def profile_path(account_id):
    """Lokasi file Brand Profile satu akun."""
    return os.path.join(BRANDING_DIR, account_id or "", PROFILE_NAME)


def style_path(preset_id):
    return os.path.join(STYLES_DIR, f"{preset_id}.json")


def load_style(preset_id):
    """Membaca style preset. Falls back ke gaya netral bila file tidak ada."""
    if not preset_id:
        return dict(NEUTRAL_STYLE)
    cached = _STYLE_CACHE.get(preset_id)
    if cached is not None:
        return cached
    path = style_path(preset_id)
    if not os.path.exists(path):
        _STYLE_CACHE[preset_id] = dict(NEUTRAL_STYLE)
        return dict(NEUTRAL_STYLE)
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    _STYLE_CACHE[preset_id] = data
    return data


def _merge(base, override):
    """Menggabungkan dict dangkal; nilai override menang."""
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_profile_file(account_id):
    path = profile_path(account_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_profile(account_id, account=None):
    """Brand Profile satu akun, sudah digabung dengan style presetnya.

    Mengembalikan dict berisi `colors`, `typography`, `watermark`, `templates`,
    dan `style`. Field `synthetic` menandai profile yang dibuat di memori karena
    file-nya tidak ada. Setiap pemanggil mendapat salinan sendiri, jadi
    penyesuaian lokal tidak mencemari cache.
    """
    account_id = (account_id or "").strip()
    cache_key = (account_id, (account or {}).get("label"), (account or {}).get("handle"))
    cached = _PROFILE_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)

    raw = _read_profile_file(account_id)
    synthetic = raw is None
    if synthetic:
        raw = _synthetic_profile(account_id, account)

    profile = hydrate_profile(raw)
    profile["templates"] = dict(raw.get("templates") or {})
    profile["generation_style"] = _merge(
        DEFAULT_GENERATION_STYLE, raw.get("generation_style") or {}
    )
    profile["synthetic"] = synthetic

    _PROFILE_CACHE[cache_key] = profile
    return profile


def _monogram(label):
    """Dua huruf pertama dari label, dipakai profile sintetis."""
    words = [w for w in str(label or "").split() if w]
    if not words:
        return "??"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def _synthetic_profile(account_id, account):
    """Profile cadangan dari data akun, supaya render tidak berhenti total."""
    account = account or {}
    label = account.get("label") or account_id or "Akun"
    handle = account.get("handle") or ""
    mono = _monogram(label)
    colors = dict(NEUTRAL_COLORS)
    return {
        "account": account_id,
        "label": label,
        "handle": handle,
        "mark": "crown",
        "monogram": mono,
        "style_preset": "generic_card",
        "identity": {"style": "generic_neutral", "visual_mood": ["netral"],
                     "design_density": "medium", "image_style": "plain"},
        "colors": colors,
        "typography": {},
        "watermark": {
            "variants": {
                "primary": {"plate": colors["accent"], "logo": colors["background"],
                            "text": colors["background"]},
                "on_light": {"plate": None, "logo": colors["background"],
                             "text": colors["background"]},
                "on_dark": {"plate": None, "logo": colors["text"], "text": colors["text"]},
            }
        },
        "templates": {"square": [], "portrait": [], "reel": [], "story": []},
        "default_template": None,
    }


def brand_id_for(account):
    """Menentukan id profil yang dipakai sebuah akun.

    Akun boleh menunjuk profil lain lewat `brand_profile`; kalau tidak diisi,
    id akunnya sendiri yang dipakai. String biasa diperlakukan sebagai id akun.
    """
    if isinstance(account, str):
        return account.strip()
    account = account or {}
    return (account.get("brand_profile") or account.get("id") or "").strip()


def brand_for(account):
    """Brand Profile lengkap untuk satu akun dari `accounts.json`.

    `account` boleh dict akun, isi brand.json mentah, atau id akun sebagai
    string. Yang penting: `account_id` selalu terisi supaya QA dan log tahu
    konten ini milik akun mana.
    """
    account_id = brand_id_for(account)
    profile = load_profile(account_id, account=account if isinstance(account, dict) else None)
    # generation_style milik akun (gaya menulis) lebih spesifik daripada yang
    # ada di file profile, jadi digabung di sini.
    overrides = account.get("generation_style") or {} if isinstance(account, dict) else {}
    profile["generation_style"] = _merge(profile.get("generation_style") or {}, overrides)
    profile["account_id"] = account.get("id") if isinstance(account, dict) else account_id
    return profile


def generation_style(brand):
    """Blok gaya menulis yang dikirim ke prompt AI."""
    return dict((brand or {}).get("generation_style") or DEFAULT_GENERATION_STYLE)


def is_profile(value):
    """True bila dict ini Brand Profile, bukan dict akun.

    Isi mentah `brand.json` hanya punya `colors` dan `style_preset`. Tanpa
    pengecekan ini, file itu terbaca sebagai dict akun dan berakhir jadi profil
    generik berwarnaAbu-abu, tanpa satu pun ciri visual akun.
    """
    if not isinstance(value, dict):
        return False
    if "colors" in value:
        return "style" in value or "style_preset" in value
    return False


def hydrate_profile(raw):
    """Lengkapi isi mentah brand.json dengan style preset dan warna default."""
    profile = dict(raw)
    style = load_style(raw.get("style_preset"))
    profile["style"] = style
    profile["style_preset"] = raw.get("style_preset") or style.get("id")
    profile["colors"] = _merge(NEUTRAL_COLORS, raw.get("colors"))
    profile["typography"] = _merge(style.get("typography") or {},
                                   raw.get("typography") or {})
    profile["watermark"] = _merge(style.get("watermark") or {},
                                  raw.get("watermark") or {})
    return profile


def resolve_brand(account=None, brand=None):
    """Brand Profile dari sumber mana pun yang praktis.

    `brand` yang sudah berupa profile dipakai langsung. Selain itu `account`
    boleh dict akun, id akun, atau None (dipakai test dan skrip terpisah).
    """
    if is_profile(brand):
        return hydrate_profile(brand) if "style" not in brand else brand
    if isinstance(brand, dict):
        return brand_for(brand)
    if isinstance(account, dict):
        return brand_for(account)
    if account:
        return brand_for(account)
    return load_profile("")


def visual_style(brand):
    """Style preset yang dipakai renderer."""
    return dict((brand or {}).get("style") or NEUTRAL_STYLE)