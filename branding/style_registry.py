"""Registry template visual.

Template menghubungkan lima hal sekaligus: akun, jenis konten, format kanvas,
gaya, dan watermark. Urutan pemilihan penting karena beberapa kategori tidak
punya template khusus. Rantai fallback:

    template kategori + format
        -> template kategori saja
        -> template default akun untuk format itu
        -> template milik akun yang mana saja
        -> template generik yang aman

Template generik boleh dipakai semua akun. Selain itu, template harus memiliki
`account` yang sama dengan akun pemanggil; kalau tidak, render dihentikan lewat
`branding.validator.assert_same_account`.
"""
import json
import os

REGISTRY_PATH = os.getenv("TEMPLATE_REGISTRY_PATH") or os.path.join("templates", "registry.json")

#: Beberapa kategori punya dua nama yang sering tertukar di bahasa sehari-hari.
SYNONYMS = {
    "tren": {"tren", "trend"},
    "tips": {"tip", "tips", "trik"},
    "ootd": {"ootd", "outfit"},
    "reels": {"reel", "reels"},
    "carousel": {"carousel", "slide"},
    "news": {"news", "berita"},
    "event": {"event", "acara", "pengumuman"},
    "analisis": {"analisis", "match_analysis", "matchup"},
}

_CACHE = {}


def load_registry(path=None):
    """Membaca registry template. File hilang berarti tidak ada template khusus."""
    target = path or REGISTRY_PATH
    key = os.path.abspath(target)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    if not os.path.exists(target):
        data = {
            "schema_version": "1.0",
            "generic": {"id": "generic_card", "account": None, "layout": "standard"},
            "defaults": {},
            "templates": [],
        }
    else:
        with open(target, encoding="utf-8") as handle:
            data = json.load(handle)

    _CACHE[key] = data
    return data


def clear_cache():
    """Mengosongkan cache registry. Dipakai saat file registry diubah."""
    _CACHE.clear()


def generic_template():
    """Template cadangan yang tidak punya pemilik akun."""
    generic = dict(load_registry().get("generic") or {})
    generic.setdefault("id", "generic_card")
    generic.setdefault("account", None)
    return generic


def _index(registry):
    """Petakan id template ke definisinya.

    Id seharusnya unik. Kalau ada duplikat, definisi pertama yang dipakai supaya
    `defaults` yang menyebut id itu tetap punya satu jawaban yang jelas.
    """
    index = {}
    for template in registry.get("templates") or []:
        template_id = template.get("id")
        if template_id and template_id not in index:
            index[template_id] = dict(template)
    return index


def duplicate_ids(registry=None):
    """Id template yang muncul lebih dari sekali. Kosong berarti registry rapi."""
    registry = registry or load_registry()
    seen, duplicates = set(), set()
    for template in registry.get("templates") or []:
        template_id = template.get("id")
        if not template_id:
            continue
        if template_id in seen:
            duplicates.add(template_id)
        seen.add(template_id)
    return sorted(duplicates)


def templates_for(account_id, registry=None):
    """Semua template milik satu akun."""
    registry = registry or load_registry()
    return [t for t in registry.get("templates") or [] if t.get("account") == account_id]


def _synonyms(text):
    for values in SYNONYMS.values():
        if text in values:
            return values
    return {text}


def _matches(template_type, wanted):
    if not wanted or not template_type:
        return False
    template_type = template_type.strip().lower()
    wanted = wanted.strip().lower()
    if template_type == wanted:
        return True
    return wanted in _synonyms(template_type) or template_type in _synonyms(wanted)


def _format_ok(template, fmt):
    """Template tanpa daftar format berlaku untuk semua format."""
    if not fmt:
        return True
    formats = template.get("formats")
    if not formats:
        return True
    return fmt in formats


def select_template(account_id, content_type=None, fmt=None, registry=None):
    """Memilih template untuk akun + kategori + format.

    Mengembalikan dict template dengan kunci tambahan `fallback` berisi nama
    tahap yang dipakai, supaya log bisa menjelaskan kenapa template tertentu
    terpilih.
    """
    registry = registry or load_registry()
    account_id = (account_id or "").strip()
    index = _index(registry)
    owned = templates_for(account_id, registry)

    def pick(candidates, step):
        # Definisi template dipakai langsung, bukan dicari lewat id, supaya dua
        # template dengan kategori berbeda tidak saling menggantikan.
        for template in candidates:
            result = dict(template)
            result["fallback"] = step
            return result
        return None

    wanted = (content_type or "").strip().lower()

    found = pick(
        [t for t in owned if _matches(t.get("content_type"), wanted) and _format_ok(t, fmt)],
        "kategori+format",
    )
    if found:
        return found

    found = pick([t for t in owned if _matches(t.get("content_type"), wanted)], "kategori")
    if found:
        return found

    defaults = (registry.get("defaults") or {}).get(account_id) or {}
    default_id = defaults.get(fmt)
    if default_id and default_id in index:
        found = dict(index[default_id])
        found["fallback"] = "default-akun"
        return found

    found = pick(owned, "milik-akun")
    if found:
        return found

    found = generic_template()
    found["fallback"] = "generic"
    return found