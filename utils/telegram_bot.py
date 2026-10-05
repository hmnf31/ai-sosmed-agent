"""Bot Telegram=on-demand content generator.

Alur: pengguna chat "buatkan 1 konten trend wedding", bot mencari akun yang cocok
dari accounts.json, mengambil topik terpanas, meminta caption + teks visual ke
OpenRouter, merender video/gambar, lalu mengirim media dan captionnya. Tidak ada
publikasi otomatis; unggah ke TikTok dikerjakan manual oleh pengguna.
"""
import os
import re
import time

from utils import accounts as accounts_mod
from utils.content_generator import generate_content
from utils.image_maker import render_content_image
from utils.notifier import (
    get_updates,
    send_chat_message,
    send_telegram_media,
)
from utils.scraper import get_topic_trends
from utils.video_maker import render_content_video

HELP_TEXT = """Bot pembuat konten. Cukup chat bebas, contoh:

- buatkan 1 konten trend wedding
- bikin konten mlbb minggu ini
- konten kuliner jajanan pasar

Perintah:
/akun - daftar akun yang tersedia
/bantu - tampilkan panduan ini
/status - cek koneksi

Setelah media dikirim, unggah manual ke TikTok. Caption tinggal disalin."""

MAX_TOPICS = int(os.getenv("CONTENT_MAX_TOPICS") or 3)


def _clean_text(text):
    return " ".join((text or "").split())


def _requested_format(text):
    low = (text or "").lower()
    if any(word in low for word in ("gambar", "foto", "image", "ig", "instagram")):
        return "image"
    if any(word in low for word in ("video", "mp4", "tiktok", "reels")):
        return "video"
    return os.getenv("DEFAULT_CONTENT_FORMAT", "video").strip().lower()


def _resolve_request(text):
    """Pisahkan perintah menjadi (akun, permintaan sisa).

    Kata kerja dan kata umum dibuang supaya yang tersisa adalah topik yang
    benar-benar diminta pengguna.
    """
    account, keyword = accounts_mod.match_account(text)
    request = _clean_text(text)

    if keyword:
        pattern = re.compile(re.escape(keyword), re.I)
        request = _clean_text(pattern.sub(" ", request))

    # Buang kata kerja di depan.
    request = re.sub(
        r"\b(buatkan|bikin|buat|generate|create|tolong|dong|donk|bisa|tolong)\b\s*",
        " ",
        request,
        flags=re.I,
    )
    # Buang penyebut format dan penanda tren di mana pun posisinya.
    request = re.sub(
        r"\b(konten|content|video|gambar|foto|post|unggahan)\b\s*",
        " ",
        request,
        flags=re.I,
    )
    request = re.sub(r"\b(tren|trend|terkini|terbaru|hari ini|minggu ini)\b\s*", " ", request, flags=re.I)
    # Buang angka di depan.
    request = re.sub(r"\b\d+\b\s*", " ", request)
    request = re.sub(r"\s{2,}", " ", request).strip(" -")

    # Kata kunci niche dipakai untuk memilih akun, tapi kalau masih ada sisa
    # kata lain maka gabungkan supaya topik tidak terpotong.
    if keyword:
        topic = _clean_text(keyword)
        request = f"{topic} {request}".strip() if request else topic

    return account, (request or "tren terbaru")


def _collect_topics(account, request):
    query = f"{account.get('source_query') or account['niche']} {request}".strip()
    topics = get_topic_trends(
        query,
        keywords=account.get("keywords", []),
        seed_topics=account.get("seed_topics", []),
        max_results=MAX_TOPICS,
    )
    if not topics:
        topics = [request]
    return topics


def build_package(request, account):
    """Menggabungkan riset, teks AI, dan render media menjadi satu paket."""
    topics = _collect_topics(account, request)
    content = generate_content(request, topics, account)
    fmt = _requested_format(request)

    if fmt == "image":
        media = render_content_image(content, footer=account.get("label", ""))
    else:
        media = render_content_video(content, footer=account.get("handle") or account.get("label", ""))

    return {
        "media": media,
        "format": fmt,
        "content": content,
        "topics": topics,
        "account": account,
    }


def _reply(chat_id, package):
    account = package["account"]
    content = package["content"]
    caption = content["caption"]

    sent = send_telegram_media(package["media"], chat_id=chat_id)

    header = (
        f"Selesai untuk {account.get('label')} ({account.get('handle')})\n"
        f"Topik: {'; '.join(package['topics'])}\n\n"
        "Caption (salin manual):\n"
    )
    send_chat_message(f"{header}{caption}", chat_id=chat_id)

    if not sent:
        send_chat_message(
            f"Media gagal terkirim. File ada di: {package['media']}", chat_id=chat_id
        )


def _handle_command(chat_id, text):
    command = text.split()[0].lower() if text.startswith("/") else ""

    if command.startswith("/start") or command.startswith("/bantu") or command.startswith("/help"):
        send_chat_message(HELP_TEXT, chat_id=chat_id)
        return True
    if command.startswith("/akun"):
        lines = ["Akun yang dikelola:"]
        for account in accounts_mod.list_accounts():
            lines.append(f"- {account['id']}: {account.get('niche', '')}")
        lines.append("")
        lines.append(f"Default: {accounts_mod.default_account()['id']}")
        send_chat_message("\n".join(lines), chat_id=chat_id)
        return True
    if command.startswith("/status"):
        send_chat_message("Bot aktif dan terhubung.", chat_id=chat_id)
        return True
    return False


def handle_message(chat_id, text):
    text = _clean_text(text)
    if not text:
        return

    if _handle_command(chat_id, text):
        return

    try:
        account, request = _resolve_request(text)
    except FileNotFoundError as e:
        send_chat_message(f"File akun belum ada: {e}", chat_id=chat_id)
        return

    send_chat_message(
        f"Sedang membuat konten untuk {account.get('label')}... ({request})", chat_id=chat_id
    )

    try:
        package = build_package(request, account)
        _reply(chat_id, package)
    except Exception as e:
        print(f"[BOT ERROR] {e}")
        send_chat_message(f"Gagal membuat konten: {e}", chat_id=chat_id)


def authorized_chat():
    allowed = {os.getenv("TELEGRAM_CHAT_ID")}
    extra = os.getenv("TELEGRAM_ALLOWED_CHATS") or ""
    allowed.update(part.strip() for part in extra.split(",") if part.strip())
    return {a for a in allowed if a}


def run(poll_timeout=30):
    """Long polling: bot berjalan permanen sampai proses dihentikan."""
    print("=== [BOT PEMBUAT KONTEN AKTIF] ===")
    try:
        for account in accounts_mod.list_accounts():
            print(f"  - {account['id']}: {account.get('niche', '')}")
    except (FileNotFoundError, ValueError) as e:
        print(f"[BOT] Gagal memuat akun: {e}")
        return

    allowed = authorized_chat()
    if not allowed:
        print("[BOT] TELEGRAM_CHAT_ID belum diset, bot tidak bisa memproses pesan.")
        return

    offset = None
    while True:
        updates = get_updates(offset=offset, timeout=poll_timeout, allowed_updates=["message"])
        if not updates:
            continue

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message") or {}
            chat = (message.get("chat") or {}).get("id")
            text = message.get("text")

            if not chat or not text:
                continue
            if str(chat) not in allowed:
                print(f"[BOT] Chat {chat} tidak diizinkan, pesan diabaikan.")
                continue

            try:
                handle_message(str(chat), text)
            except Exception as e:
                print(f"[BOT ERROR] {e}")
                send_chat_message(f"Terjadi kesalahan: {e}", chat_id=str(chat))
            time.sleep(1)


if __name__ == "__main__":
    run()