"""Entry point bot Telegram pembuat konten.

Jalankan:
  .venv\\Scripts\\python.exe bot.py
"""
from dotenv import load_dotenv

from utils.telegram_bot import run, setup_logging

load_dotenv()


if __name__ == "__main__":
    setup_logging()
    run()