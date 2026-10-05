"""Registry akun: satu file JSON mendefinisikan semua akun yang dikelola.

Schema v2 menambah mode kerja (content / club_operations / affiliate), kategori
konten, aturan fact-check, dan template default per akun. Schema v3 menambah
`brand_profile` dan `generation_style`, yang menautkan akun ke identitas visual
dan gaya tulisnya di folder `branding/`. Field baru selalu opsional supaya file
schema lama tetap bisa dibaca.
"""
import json
import os
import re

DEFAULT_PATH = "accounts.json"

REQUIRED_FIELDS = ("id", "label", "niche")

# Field opsional yang selalu punya nilai default supaya pemanggil tidak perlu
# memeriksa keberadaan kunci.
DEFAULTS = {
    "mode": ["content"],
    "keywords": [],
    "hashtags": [],
    "avoid": [],
    "fact_check_rules": [],
    "content_categories": [],
    "default_templates": [],
    "research_sources": ["youtube"],
    "seed_topics": [],
    "emoji": "",
    "audience": "",
    "tone": "",
    "handle": "",
    "source_query": "",
    # Nama file Brand Profile di folder branding/. Kosong berarti pakai id akun.
    "brand_profile": "",
    # Gaya menulis per akun; boleh menimpa sebagian nilai dari brand profile.
    "generation_style": {},
}


def accounts_path():
    return os.getenv("ACCOUNTS_FILE") or DEFAULT_PATH


def _normalize(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def load(path=None):
    """Membaca accounts.json. Melempar pesan jelas bila file tidak ada/ rusak."""
    target = path or accounts_path()
    if not os.path.exists(target):
        raise FileNotFoundError(
            f"File akun tidak ditemukan: {target}. Salin accounts.example.json menjadi accounts.json."
        )
    try:
        with open(target, encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as e:
        raise ValueError(f"File akun {target} bukan JSON yang valid: {e}")

    accounts = data.get("accounts") or []
    if not accounts:
        raise ValueError(f"File akun {target} tidak memuat daftar akun.")

    seen = set()
    for account in accounts:
        missing = [f for f in REQUIRED_FIELDS if not account.get(f)]
        if missing:
            raise ValueError(
                f"Akun '{account.get('id', '?')}' di {target} kehilangan field: {', '.join(missing)}"
            )
        account_id = _normalize(account["id"])
        if account_id in seen:
            raise ValueError(f"Akun dengan id '{account['id']}' muncul lebih dari sekali di {target}.")
        seen.add(account_id)
        _apply_defaults(account)

    data.setdefault("schema_version", 1)
    return data


def _apply_defaults(account):
    """Melengkapi field opsional yang kosong supaya pemanggil aman.

    Nilai default yang berupa dict/list disalin per akun, supaya satu akun yang
    diisi tidak mengubah akun lain.
    """
    for key, fallback in DEFAULTS.items():
        if account.get(key) in (None, "", []):
            account[key] = dict(fallback) if isinstance(fallback, dict) else (
                list(fallback) if isinstance(fallback, list) else fallback
            )
    return account


def list_accounts(path=None):
    return load(path).get("accounts", [])


def find_account(account_id, path=None):
    wanted = _normalize(account_id)
    for account in list_accounts(path):
        if _normalize(account["id"]) == wanted:
            return account
    return None


def default_account(path=None):
    data = load(path)
    wanted = _normalize(data.get("default_account", ""))
    accounts = data.get("accounts", [])
    for account in accounts:
        if _normalize(account["id"]) == wanted:
            return account
    return accounts[0] if accounts else None


def has_mode(account, mode):
    """True bila akun mendukung mode kerja tertentu."""
    return mode in (account or {}).get("mode", [])


def brand(account):
    """Brand Profile milik satu akun.

    Import dilakukan di dalam fungsi supaya modul ini tetap bisa dipakai tanpa
    mengunduh paket `branding` saat registry akun dibaca.
    """
    from branding import loader

    return loader.brand_for(account)


def operational_accounts(path=None):
    """Akun yang punya mode club_operations, mis. klub catur."""
    return [a for a in list_accounts(path) if has_mode(a, "club_operations")]


def schema_version(path=None):
    return load(path).get("schema_version", 1)


def match_account(text, path=None, fallback=True):
    """Mencari akun dari teks bebas, contoh: 'buatkan konten trend wedding'.

    Mengembalikan (account, keyword_yang_cocok). Cocokkan berdasarkan kata kunci
    paling panjang supaya 'wedding day' menang lebih dulu dari 'wedding'.

    Dengan fallback=False, teks yang tidak memuat kata kunci akun menghasilkan
    (None, None). Router memakai ini supaya bisa membedakan 'akun tidak disebut'
    dari 'akun disebut'.
    """
    haystack = _normalize(text)
    if not haystack:
        return (default_account(path) if fallback else None), None

    best = None
    for account in list_accounts(path):
        for keyword in account.get("keywords", []):
            needle = _normalize(keyword)
            if needle and needle in haystack and (best is None or len(needle) > len(best[1])):
                best = (account, keyword)

    if best:
        return best
    return (default_account(path) if fallback else None), None