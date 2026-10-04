import os
import requests

API_URL = "https://api.telegram.org/bot{token}/{method}"


def _credentials():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return None, None
    return token, chat_id


def send_telegram_notification(message):
    """Mengirim pesan notifikasi status ke Bot Telegram."""
    token, chat_id = _credentials()
    if not token:
        print("[NOTIFIER] Token/Chat ID Telegram tidak diset. Notifikasi dilewati.")
        return False

    url = API_URL.format(token=token, method="sendMessage")
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            print("[NOTIFIER] Notifikasi Telegram berhasil dikirim.")
            return True

        detail = response.text
        if response.status_code == 400 and "parse entities" in detail:
            print("[NOTIFIER] Format Markdown tidak valid, mengirim ulang sebagai teks biasa...")
            response = requests.post(url, json={**payload, "parse_mode": None}, timeout=30)
            if response.status_code == 200:
                print("[NOTIFIER] Notifikasi Telegram berhasil dikirim (teks biasa).")
                return True
            detail = response.text

        print(f"[NOTIFIER ERROR] Gagal mengirim notifikasi (HTTP {response.status_code}): {str(detail)[:300]}")
    except Exception as e:
        print(f"[NOTIFIER ERROR] Gagal mengirim notifikasi: {e}")

    return False


def _upload_media(method, field, media_path, caption="", mime="application/octet-stream", timeout=300):
    token, chat_id = _credentials()
    if not token:
        print(f"[NOTIFIER] Token/Chat ID Telegram tidak diset. {method} dilewati.")
        return False

    url = API_URL.format(token=token, method=method)
    data = {"chat_id": chat_id}
    caption = (caption or "").strip()
    if caption:
        data["caption"] = caption[:1024]
        data["parse_mode"] = "Markdown"

    def upload(payload):
        with open(media_path, "rb") as media:
            return requests.post(
                url,
                data=payload,
                files={field: (os.path.basename(media_path), media, mime)},
                timeout=timeout,
            )

    try:
        response = upload(data)
        if response.status_code == 200:
            print(f"[NOTIFIER] {method} berhasil dikirim ke Telegram.")
            return True

        detail = response.text
        if response.status_code == 400 and "parse entities" in detail:
            print("[NOTIFIER] Caption Markdown invalid, mengirim ulang tanpa format...")
            data["parse_mode"] = ""
            response = upload(data)
            if response.status_code == 200:
                print(f"[NOTIFIER] {method} berhasil dikirim ke Telegram (caption teks biasa).")
                return True
            detail = response.text

        print(f"[NOTIFIER ERROR] Gagal mengirim {method} (HTTP {response.status_code}): {str(detail)[:300]}")
    except FileNotFoundError:
        print(f"[NOTIFIER ERROR] File tidak ditemukan: {media_path}")
    except Exception as e:
        print(f"[NOTIFIER ERROR] Gagal mengirim {method}: {e}")

    return False


def send_telegram_photo(photo_path, caption=""):
    """Mengirim foto (bersama caption opsional) ke chat Telegram sebagai pratinjau konten."""
    return _upload_media("sendPhoto", "photo", photo_path, caption, mime="image/png", timeout=90)


def send_telegram_video(video_path, caption=""):
    """Mengirim video mp4 ke chat Telegram (batas bot Telegram: 50 MB)."""
    size_mb = os.path.getsize(video_path) / (1024 * 1024) if os.path.exists(video_path) else 0
    if size_mb > 50:
        print(f"[NOTIFIER] Video {size_mb:.1f} MB melebihi batas 50 MB bot Telegram.")
        return False
    return _upload_media("sendVideo", "video", video_path, caption, mime="video/mp4", timeout=300)