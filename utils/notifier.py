import os
import requests


def send_telegram_notification(message):
    """Mengirim pesan notifikasi status ke Bot Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[NOTIFIER] Token/Chat ID Telegram tidak diset. Notifikasi dilewati.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }

    try:
        requests.post(url, json=payload)
        print("[NOTIFIER] Notifikasi Telegram berhasil dikirim.")
    except Exception as e:
        print(f"[NOTIFIER ERROR] Gagal mengirim notifikasi: {e}")