"""Bantu OAuth TikTok: tampilkan URL otorisasi lalu tukar authorization code jadi refresh token.

Jalankan:
  .venv\\Scripts\\python.exe scripts\\tiktok_oauth.py

Skrip ini menulis TIKTOK_REFRESH_TOKEN ke .env secara otomatis sehingga tidak perlu
menyalin nilai token secara manual.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv

from utils.tiktok import (
    TikTokError,
    build_authorize_url,
    exchange_authorization_code,
    get_user_info,
    refresh_access_token,
)

load_dotenv(os.path.join(ROOT, ".env"))

ENV_PATH = os.path.join(ROOT, ".env")


def save_refresh_token(refresh_token):
    """Mengganti nilai TIKTOK_REFRESH_TOKEN di .env tanpa merusak baris lain."""
    with open(ENV_PATH, encoding="utf-8") as handle:
        lines = handle.read().splitlines()

    updated = []
    replaced = False
    for line in lines:
        if line.startswith("TIKTOK_REFRESH_TOKEN="):
            updated.append("TIKTOK_REFRESH_TOKEN=" + refresh_token)
            replaced = True
        elif line.startswith("TIKTOK_ACCESS_TOKEN="):
            updated.append("TIKTOK_ACCESS_TOKEN=")
        else:
            updated.append(line)

    if not replaced:
        updated.append("TIKTOK_REFRESH_TOKEN=" + refresh_token)

    with open(ENV_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(updated) + "\n")


print("=== Langkah 1: buka URL ini di browser (login ke akun TikTok tujuan) ===\n")
print(build_authorize_url())
print("\nSetelah menyetujui, browser diarahkan ke redirect URL milik Anda.")
print("Salin parameter 'code' dari alamat tujuan itu.\n")

code = input("Masukkan code otorisasi: ").strip()
if not code:
    print("Code kosong, dibatalkan.")
    sys.exit(1)

try:
    tokens = exchange_authorization_code(code)
except TikTokError as e:
    print(f"\nGAGAL: {e}")
    sys.exit(1)

print(f"\nTukar kode berhasil. scope: {tokens.get('scope') or '(tidak dilaporkan)'}")
print(f"open_id akun tujuan: {tokens.get('open_id') or '(tidak ada)'}")

refresh_token = (tokens.get("refresh_token") or "").strip()
if not refresh_token:
    print("TikTok tidak mengembalikan refresh token. Periksa scope yang disetujui.")
    sys.exit(1)

save_refresh_token(refresh_token)
print("\nTIKTOK_REFRESH_TOKEN sudah tersimpan di .env (nilainya tidak ditampilkan).")

try:
    again = refresh_access_token()
    print(f"Verifikasi refresh grant: OK, berlaku {again.get('expires_in')} detik.")
except TikTokError as e:
    print(f"Tidak bisa memverifikasi refresh grant: {e}")

try:
    info = get_user_info()
    print(f"Akun terhubung: {info.get('display_name', '?')} (open_id {info.get('open_id', '?')})")
except TikTokError as e:
    print(f"Tidak bisa membaca info akun: {e}")

print("\nSisa langkah: set TIKTOK_ENABLED=true bila scope video.publish sudah disetujui.")