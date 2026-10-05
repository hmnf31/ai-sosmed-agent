"""Membangun aset logo dan watermark setiap akun dari Brand Profile.

Jalankan sekali setelah `branding/<akun>/brand.json` dibuat atau diubah:

    .venv\\Scripts\\python.exe scripts\\build_branding_assets.py
    .venv\\Scripts\\python.exe scripts\\build_branding_assets.py chess mlbb
    .venv\\Scripts\\python.exe scripts\\build_branding_assets.py --check

Aset ditulis ke `assets/branding/<akun>/`. Renderer memakainya apa adanya, jadi
gambar ulang hanya perlu dilakukan kalau warnanya di brand.json yang berubah.

`--check` hanya memvalidasi profile tanpa menulis file: berguna untuk CI dan
untuk memastikan config tidak salah ketik sebelum aset dibangun.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from branding import loader, style_registry, validator, watermark  # noqa: E402


def _report(account_id, profile, problems):
    status = "OK " if not problems else "GAGAL"
    print(f"[{status}] {account_id} ({profile.get('label', '?')})")
    for problem in problems:
        print(f"         - {problem}")


def check(account_ids=None):
    """Validasi profile, template, dan style tanpa membuat file."""
    total = 0
    for account_id in account_ids or loader.list_profile_ids():
        problems = validator.validate_profile(loader.load_profile(account_id))
        for fmt in ("square", "portrait", "reel", "story"):
            template = style_registry.select_template(account_id, fmt=fmt)
            try:
                validator.assert_same_account(account_id, template=template,
                                              brand=loader.load_profile(account_id))
            except validator.BrandingMismatch as e:
                problems.append(str(e))
        _report(account_id, loader.load_profile(account_id), problems)
        total += len(problems)
    duplikat = style_registry.duplicate_ids()
    if duplikat:
        print(f"[GAGAL] id template duplikat: {', '.join(duplikat)}")
        total += len(duplikat)
    return total


def build(account_ids=None):
    """Buat logo dan ketiga varian watermark."""
    targets = account_ids or loader.list_profile_ids()
    created = watermark.build_all(targets)
    for path in created:
        print(f"[BRAND] {path} ({os.path.getsize(path)} bytes)")
    return created


def main():
    parser = argparse.ArgumentParser(description="Bangun aset branding per akun")
    parser.add_argument("accounts", nargs="*", help="id akun (default: semua yang punya brand.json)")
    parser.add_argument("--check", action="store_true", help="validasi config tanpa menulis aset")
    args = parser.parse_args()

    if args.check:
        problems = check(args.accounts)
        print(f"{'Semua brand valid' if not problems else f'{problems} masalah ditemukan'}")
        return 1 if problems else 0

    build(args.accounts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())