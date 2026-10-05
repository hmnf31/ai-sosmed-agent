"""Bantu OAuth TikTok: tampilkan URL otorisasi lalu tukar authorization code jadi refresh token.

Jalankan:
  .venv\\Scripts\\python.exe scripts\\tiktok_oauth.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from utils.tiktok import (
    TikTokError,
    build_authorize_url,
    exchange_authorization_code,
    get_user_info,
)

load_dotenv()

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

print("\n=== Langkah 2: simpan nilai berikut ke .env ===")
print(f"TIKTOK_REFRESH_TOKEN={tokens.get('refresh_token', '')}")
print(f"TIKTOK_ENABLED=true")
print(f"open_id akun tujuan: {tokens.get('open_id', '(tidak ada, minta scope user.info.basic)')}")
print(f"scope diberikan: {tokens.get('scope', '(tidak ada)')}")

try:
    info = get_user_info(tokens.get("access_token"))
    print(f"akun terhubung: @{info.get('display_name', '?')} (open_id {info.get('open_id', '?')})")
except TikTokError as e:
    print(f"tidak bisa membaca info akun: {e}")