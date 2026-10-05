"""Entry point bot Telegram pembuat konten.

Jalankan:
  .venv\\Scripts\\python.exe bot.py
"""
from dotenv import load_dotenv

from utils.telegram_bot import run

load_dotenv()

if __name__ == "__main__":
    run()