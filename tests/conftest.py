"""Konfigurasi bersama test suite.

Test tidak boleh menyentuh database, .env, atau jaringan milik pengguna.
Setiap test memakai database sementara sendiri lewat monkeypatch.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "12345")


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Database history sementara yang otomatis terhapus setelah test."""
    from utils import history

    target = str(tmp_path / "history.db")
    monkeypatch.setenv("CONTENT_DB_PATH", target)
    history.init_db(target)
    yield target
    for suffix in ("", "-wal", "-shm"):
        candidate = target + suffix
        if os.path.exists(candidate):
            os.remove(candidate)


@pytest.fixture
def fake_notifier(monkeypatch):
    """Menangkap semua pengiriman Telegram tanpa menyentuh jaringan."""
    from utils import telegram_bot, notifier

    sent = []
    media = []
    edited = []
    answered = []

    def _send(text, chat_id=None, parse_mode=None, reply_markup=None):
        sent.append({"text": text, "chat_id": chat_id, "reply_markup": reply_markup})
        return True

    def _send_media(media_path, caption="", chat_id=None):
        media.append({"path": media_path, "caption": caption, "chat_id": chat_id})
        return True

    def _edit(chat_id, message_id, text, reply_markup=None):
        edited.append({"chat_id": chat_id, "message_id": message_id,
                       "text": text, "reply_markup": reply_markup})
        return True

    def _answer(callback_id, text="", show_alert=False):
        answered.append(callback_id)
        return True

    for module in (notifier, telegram_bot):
        monkeypatch.setattr(module, "send_chat_message", _send)
        monkeypatch.setattr(module, "send_telegram_media", _send_media)
        monkeypatch.setattr(module, "edit_chat_message", _edit)
        monkeypatch.setattr(module, "answer_callback", _answer)

    return {"sent": sent, "media": media, "edited": edited, "answered": answered}


@pytest.fixture
def fake_pipeline(monkeypatch):
    """Mengganti riset, AI, dan renderer agar test tidak memanggil layanan luar."""
    from utils import telegram_bot

    calls = {"research": [], "ai": [], "render": []}

    def _topics(account, request):
        calls["research"].append((account["id"], request))
        return [f"{request} (tren)"]

    def _content(request, topics, account, category=None, avoid_topics=None,
                 angle_hint=""):
        calls["ai"].append({
            "request": request,
            "topics": tuple(topics),
            "account": account["id"],
            "category": category,
            "avoid_topics": tuple(avoid_topics or ()),
            "angle_hint": angle_hint,
        })
        return {
            "title": f"Judul {request}",
            "subtitle": "Sub judul",
            "points": ["p1", "p2", "p3"],
            "cta": "CTA",
            "caption": f"Caption untuk {request}",
            "hashtags": ["#Test"],
            "angle": "Sudut pandang uji",
            "source_url": "",
        }

    def _image(content, footer=""):
        calls["render"].append(("image", content.get("title"), footer))
        return "output/test-image.png"

    def _video(content, footer=""):
        calls["render"].append(("video", content.get("title"), footer))
        return "output/test-video.mp4"

    monkeypatch.setattr(telegram_bot, "_collect_topics", _topics)
    monkeypatch.setattr(telegram_bot, "generate_content", _content)
    monkeypatch.setattr(telegram_bot, "render_content_image", _image)
    monkeypatch.setattr(telegram_bot, "render_content_video", _video)
    return calls