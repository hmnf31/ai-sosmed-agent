"""Registry akun: satu file JSON mendefinisikan semua akun yang dikelola.

Setiap akun punya niche, nada bicara, kata kunci untuk mengenali permintaan, dan
daftar hashtag. Bot memakai ini untuk tahu konten harus dibuat untuk akun mana.
"""
import json
import os
import re

DEFAULT_PATH = "accounts.json"

REQUIRED_FIELDS = ("id", "label", "niche")


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

    for account in accounts:
        missing = [f for f in REQUIRED_FIELDS if not account.get(f)]
        if missing:
            raise ValueError(
                f"Akun '{account.get('id', '?')}' di {target} kehilangan field: {', '.join(missing)}"
            )
    return data


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


def match_account(text, path=None):
    """Mencari akun dari teks bebas, contoh: 'buatkan konten trend wedding'.

    Mengembalikan (account, keyword_yang_cocok). Cocokkan berdasarkan kata kunci
    paling panjang supaya 'wedding day' menang lebih dulu dari 'wedding'.
    """
    haystack = _normalize(text)
    if not haystack:
        return None, None

    best = None
    for account in list_accounts(path):
        for keyword in account.get("keywords", []):
            needle = _normalize(keyword)
            if needle and needle in haystack and (best is None or len(needle) > len(best[1])):
                best = (account, keyword)

    if best:
        return best
    return default_account(path), None