"""Bot Telegram: social media assistant on-demand.

Alur: pengguna chat bebas ("buatkan 3 konten mlbb tentang counter hayabusa"),
router menentukan akun dan task, sistem riset mengambil topik, AI menulis,
renderer membuat media, hasilnya dikirim ke Telegram untuk diunggah manual.
Tidak ada publikasi otomatis.

Tersedia menu tombol, histori konten, dan pencatatan request untuk penelusuran.
"""
import json
import logging
import os
import re
import sys
import time
import uuid
from logging.handlers import RotatingFileHandler

from branding import loader as brand_mod
from branding import style_registry, validator
from utils import accounts as accounts_mod
from utils import engines
from utils import history as history_mod
from utils import keyboards
from utils import research as research_mod
from utils import router
from utils.chess import arena as chess_arena
from utils.chess import liga as chess_liga
from utils.chess import tco as chess_tco
from utils.content_generator import generate_content
from utils.image_maker import render_content_card, render_content_image
from utils.media import asset_loader, layout_engine
from utils.notifier import (
    answer_callback,
    edit_chat_message,
    get_updates,
    send_chat_message,
    send_telegram_media,
)
from utils.video_maker import render_content_video

LOG_PATH = os.getenv("CONTENT_LOG_PATH") or "output/content-bot.log"
LOG_FORMAT = "%(asctime)s %(levelname)-7s %(message)s"


class _PrintToLog:
    """Mengalihkan print() modul lain ke logger.

    Modul scraper, AI, dan renderer masih memakai print(). Tanpa ini jejaknya
    hanya muncul di konsol dan hilang dari file log.
    """

    def write(self, message):
        text = str(message).rstrip()
        if text:
            logging.getLogger("bot").info("%s", text)

    def flush(self):
        pass


def setup_logging(path=LOG_PATH):
    """Menulis log ke file dan konsol. Error tidak pernah menggagalkan bot."""
    if isinstance(sys.stdout, _PrintToLog):
        return

    console = sys.stdout
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    except OSError as e:
        print(f"[BOT] Gagal menyiapkan file log ({e}), pakai konsol saja.")
        return

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[handler, logging.StreamHandler(console)],
        force=True,
    )
    # Print dari modul lain ikut masuk ke file log yang sama.
    sys.stdout = _PrintToLog()


def log(level, message):
    """Pencatatan yang aman: kegagalan log tidak boleh menghentikan pemrosesan."""
    try:
        logging.log(level, message)
    except Exception:
        pass


def info(message):
    log(logging.INFO, message)


def warn(message):
    log(logging.WARNING, message)


def error(message):
    log(logging.ERROR, message)


HELP_TEXT = """Social Media Assistant. Cukup chat bebas, contoh:

Konten
- buatkan 1 konten tren wedding
- bikin 3 konten mlbb tentang counter hayabusa
- buat 5 konten ootd untuk instagram

Klub catur
- tco minggu ini          (pesan utama, H-2)
- tco h-1                 (pengingat sehari sebelum)
- tco 1 jam lagi          (pengingat satu jam sebelum)
- /liga Liga 1            (klasemen satu liga, tanpa nama = ringkasan season)
- jadwal liga 1           (klasemen + match berikutnya)
- arena kings bulan ini   (pengumuman tetap, dipakai H-14 dan H-7)
- arena kings bulan ini 2 jam lagi
- arena kings bulan ini 1 jam lagi
- /arena link https://www.chess.com/...   (link arena untuk pengingat dekat)

Perintah
/menu - tombol pilih akun
/akun - daftar akun
/riwayat [akun] - konten terbaru
/preview [akun] [image|video|portrait] - contoh tampilan brand akun
/style [akun] - ringkasan warna, template, dan watermark akun
/status - status bot dan jumlah konten
/bantu - panduan ini

Setelah media dikirim, unggah manual ke TikTok. Caption tinggal disalin."""

MAX_TOPICS = int(os.getenv("CONTENT_MAX_TOPICS") or 3)

# Permintaan kurang dari ini kata dianggap belum jelas dan tidak dikirim ke AI.
MIN_REQUEST_WORDS = 2
SHORT_REQUESTS = {
    "ya", "iya", "ok", "oke", "okay", "sip", "siap", "makasih", "terima kasih", "thanks",
    "tes", "tes cek", "test", "test bot", "halo", "hai", "hello", "hi", "bro", "bang",
    "halo bot", "hai bot", "bot", "tren terbaru", "konten tren terbaru", "terbaru",
}


def _clean_text(text):
    return " ".join((text or "").split())


def _requested_format(intent):
    """Format dari intent router, falling back ke preferensi lingkungan."""
    chosen = intent.get("format") if intent else None
    if chosen:
        return chosen
    return os.getenv("DEFAULT_CONTENT_FORMAT", "video").strip().lower()


def _build_research(request, account):
    """Paket riset sumber untuk satu permintaan konten (multi-sumber + fallback)."""
    return research_mod.build_research(request, account=account, top_n=MAX_TOPICS)


def _collect_topics(account, request, pack=None):
    """Topik untuk prompt AI: judul dari paket riset, fallback ke request.

    Bila `pack` tidak diberikan (dipanggil berdiri sendiri), riset dijalankan
    di sini. Kegagalan riset di urut langkah sebelumnya, jadi di sini `pack`
    bisa kosong dan topik tetap dihasilkan.
    """
    if pack is None:
        pack = _build_research(request, account)
    topics = research_mod.topics_from_pack(pack, max_results=MAX_TOPICS)
    if not topics:
        topics = [request]
    return topics


def build_package(intent, account, chat_id="", request_id=None):
    """Menggabungkan riset, teks AI, render media, dan histori menjadi satu paket.

    Semua konten dicatat lebih dulu supaya histori tetap ada walau render gagal.
    """
    started = time.time()
    label = account.get("label", account.get("id", "?"))
    request = intent.get("topic") or "tren terbaru"

    engine = engines.engine_for(account["id"])
    similar = []
    try:
        similar = history_mod.duplicate_candidates(account["id"], request, limit=5)
    except Exception as e:  # histori tidak boleh menghentikan produksi konten
        warn(f"cek histori gagal: {e}")

    category = intent.get("category") or engine.detect_category(intent.get("raw", ""))
    brief = engine.build_brief(intent.get("raw", "") or request, request, account,
                               category=category)
    if similar:
        brief["avoid_topics"] = [
            row.get("topic") or row.get("title") or "" for row in similar
        ]
    if intent.get("url"):
        brief["extra_rules"] = brief.get("extra_rules", []) + [
            f"URL produk/jcob yang diberikan: {intent['url']}"
        ]

    # Riset sumber (multi-sumber + fallback). Kegagalan riset diteruskan ke
    # error handling supaya request dicatat sebagai gagal, seperti perilaku
    # lama ketika scraping YouTube gagal.
    research_pack = _build_research(request, account)
    research_block = research_mod.to_content_plan_research(
        research_pack,
        required=bool(account.get("fact_check_rules")),
    )

    topics = _collect_topics(account, request, pack=research_pack)
    info(f"[{_stamp(chat_id)}] topik {label}: {'; '.join(topics)}")

    # Brand Profile dibaca sekali lalu dipakai bersama: prompt AI, renderer, dan
    # QA. Dengan begitu satu konten tidak mungkin punya gaya dan tanda tangan
    # dari dua akun berbeda.
    brand = brand_mod.brand_for(account)
    if brand.get("synthetic"):
        warn(f"akun {label} belum punya brand.json, memakai gaya generik")

    content = generate_content(
        request, topics, account,
        category=brief.get("category"),
        avoid_topics=brief.get("avoid_topics"),
        angle_hint=brief.get("angle_hint", ""),
        brand=brand,
        sources=research_pack.get("items"),
    )
    content["instructions"] = engine.extra_instructions(brief)
    content["research"] = research_block
    if not content.get("source_url"):
        for item in research_pack.get("items", []):
            if item.get("url"):
                content["source_url"] = item["url"]
                break
    fmt = _requested_format(intent)

    record = history_mod.record_content(
        account["id"],
        topic=request,
        title=content.get("title") or request,
        task=intent.get("task"),
        content_type=fmt,
        category=brief.get("category"),
        source_url=content.get("source_url"),
        caption=content.get("caption"),
        angle=content.get("angle"),
        platform=intent.get("platform"),
        request_id=request_id,
    )
    content_id = record["id"]

    if fmt == "image":
        media = render_content_image(content, footer=account.get("label", ""),
                                     brand=brand, category=brief.get("category"))
    else:
        media = render_content_video(content,
                                     footer=account.get("handle") or account.get("label", ""),
                                     brand=brand, category=brief.get("category"))

    template = style_registry.select_template(account["id"],
                                              content_type=brief.get("category"), fmt=fmt)
    qa = _check_branding(media, account, brand, template, fmt)
    for problem in qa:
        warn(f"[{_stamp(chat_id)}] branding: {problem}")

    history_mod.set_file(content_id, media, caption=content.get("caption"))

    package = {
        "media": media,
        "format": fmt,
        "content": content,
        "topics": topics,
        "account": account,
        "content_id": content_id,
        "request_id": request_id,
        "brand": brand,
        "template": template,
        "branding_problems": qa,
        "research": research_block,
        "research_summary": research_mod.summarize(research_pack),
    }
    info(
        f"[{_stamp(chat_id)}] {label} selesai: {content_id} {fmt} {os.path.basename(media)} "
        f"({time.time() - started:.1f}s)"
    )
    return package


def _stamp(chat_id):
    """Label singkat untuk correlating log."""
    return f"chat {chat_id}" if chat_id else "klien"


def _check_branding(media, account, brand, template, fmt):
    """QA branding untuk satu file hasil render.

    Yang dicek hanya hal yang bisa dipastikan tanpa menebak: file ada, ukuran
    kanvas sesuai format, template milik akun, dan varian watermark tersedia.
    Daftar kosong berarti aman dikirim.
    """
    canvas = asset_loader.canvas_for(fmt)
    return validator.verify_render(
        media, account["id"], template=template, brand=brand,
        expected_size=layout_engine.canvas_size(canvas),
    )


def _reply(chat_id, package):
    account = package["account"]
    content = package["content"]

    sent = send_telegram_media(package["media"], chat_id=chat_id)

    content_id = package.get("content_id")
    template = package.get("template") or {}
    problems = package.get("branding_problems") or []
    lines = [
        f"Selesai untuk {account.get('label')} ({account.get('handle')})",
        f"ID: {content_id or '-'}",
        f"Topik: {'; '.join(package['topics'])}",
    ]
    if template.get("id"):
        lines.append(f"Template: {template['id']}")
    if content.get("angle"):
        lines.append(f"Sudut pandang: {content['angle']}")
    # URL dikirim polos supaya bisa langsung disalin dan diklik.
    if content.get("source_url"):
        lines.append(f"Sumber: {content['source_url']}")
    research = package.get("research") or {}
    if research.get("sources"):
        lines.append(
            f"Riset: {len(research['sources'])} sumber — status {research['fact_check_status']}"
        )
    if problems:
        lines.append("Catatan branding: " + "; ".join(problems))
    lines.extend(["", "Caption (salin manual):", content["caption"]])

    send_chat_message("\n".join(lines), chat_id=chat_id)

    if not sent:
        warn(f"[chat {chat_id}] media gagal terkirim: {package['media']}")
        send_chat_message(
            f"Media gagal terkirim. File ada di: {package['media']}", chat_id=chat_id
        )


def _handle_command(chat_id, text):
    command = text.split()[0].lower() if text.startswith("/") else ""

    if command.startswith("/start") or command.startswith("/menu"):
        send_chat_message(keyboards.home_text(), chat_id=chat_id,
                          reply_markup=keyboards.home_markup())
        return True
    if command.startswith("/bantu") or command.startswith("/help"):
        send_chat_message(HELP_TEXT, chat_id=chat_id)
        return True
    if command.startswith("/akun"):
        lines = ["Akun yang dikelola:"]
        for account in accounts_mod.list_accounts():
            modes = ", ".join(account.get("mode", []))
            lines.append(f"- {account.get('emoji','')} {account['id']} ({modes}): {account.get('niche', '')}")
        lines.append("")
        lines.append(f"Default: {accounts_mod.default_account()['id']}")
        send_chat_message("\n".join(lines), chat_id=chat_id)
        return True
    if command.startswith("/status"):
        stats = history_mod.account_stats(days=7)
        recent_requests = history_mod.requests_recent(limit=5)
        failed = [r for r in recent_requests if r.get("status") not in ("ok",)]
        lines = [
            "Bot aktif dan terhubung.",
            f"Konten 7 hari: {stats or 'belum ada'}",
            f"Request terakhir: {len(recent_requests)}"
            + (f" ({len(failed)} bermasalah)" if failed else ""),
        ]
        send_chat_message("\n".join(lines), chat_id=chat_id)
        return True
    if command.startswith("/riwayat") or command.startswith("/recent"):
        account = accounts_mod.default_account()
        args = text.split(None, 1)
        if len(args) > 1:
            found = accounts_mod.find_account(args[1].strip().lower())
            account = found or account
        _reply_history(chat_id, account)
        return True
    if command.startswith("/preview"):
        _handle_preview(chat_id, text)
        return True
    if command.startswith("/style"):
        _handle_style(chat_id, text)
        return True
    return False


#: Contoh isi untuk preview. Menentukan tampilan tanpa memanggil AI, supaya
#: gaya bisa dicek kapan saja tanpa memakai kuota.
PREVIEW_CONTENT = {
    "title": "Contoh judul konten",
    "subtitle": "Sub judul satu kalimat penjelas",
    "points": [
        "Poin pertama yang selalu terbaca",
        "Poin kedua yang tidak melebihi batas baris",
        "Poin ketiga yang menutup daftar",
    ],
    "cta": "Simpan dan cek lagi nanti",
    "caption": "Caption contoh untuk preview.",
    "hashtags": ["#Preview"],
}


def _account_and_format(text, default=None):
    """Ambil akun dan format dari argumen perintah, tanpa router."""
    parts = text.split()[1:]
    fmt = default
    words = []
    for part in parts:
        lowered = part.lower()
        if lowered in ("image", "gambar", "square"):
            fmt = "image"
        elif lowered in ("video", "reel", "story"):
            fmt = "video"
        elif lowered == "portrait":
            fmt = "portrait"
        else:
            words.append(part)
    account = accounts_mod.find_account(" ".join(words)) if words else None
    return account or accounts_mod.default_account(), fmt


def _handle_preview(chat_id, text):
    """Kirim contoh render sesuai brand akun, tanpa memanggil AI."""
    account, requested = _account_and_format(text, default="image")
    fmt = requested if requested != "portrait" else "square"
    brand = brand_mod.brand_for(account)
    template = style_registry.select_template(account["id"], fmt=fmt)

    try:
        if requested == "portrait":
            from utils.media import template_engine

            result = template_engine.render_card(PREVIEW_CONTENT, brand,
                                                 output_dir=layout_engine.output_dir(),
                                                 fmt="portrait")
        else:
            result = render_content_card(PREVIEW_CONTENT, brand=brand,
                                         account=account, category=None, fmt=fmt)
    except Exception as e:
        error(f"preview gagal: {e}")
        send_chat_message(f"Preview gagal: {e}", chat_id=chat_id)
        return

    problems = validator.verify_render(result["path"], account["id"], template=template,
                                       brand=brand, expected_size=result["size"])
    lines = [
        f"Preview {account.get('label')} ({fmt})",
        f"Template: {template.get('id')} | style: {result['brand'].get('style_preset')}",
        f"Ukuran: {result['size'][0]}x{result['size'][1]} | "
        f"watermark: {result['watermark'].get('variant')}",
    ]
    masalah = problems + result.get("problems", [])
    if masalah:
        lines.append("Catatan: " + "; ".join(masalah))
    send_telegram_media(result["path"], caption="\n".join(lines), chat_id=chat_id)


def _handle_style(chat_id, text):
    """Ringkasan brand profile satu akun: warna, template, watermark."""
    account, _ = _account_and_format(text)
    brand = brand_mod.brand_for(account)
    colors = brand.get("colors") or {}
    watermark = brand.get("watermark") or {}
    voice = brand.get("generation_style") or {}

    lines = [
        f"Brand {account.get('label')} ({brand.get('handle')})",
        f"Profil: {brand.get('account')} | style: {brand.get('style_preset')}"
        + (" (SINTETIS, belum ada brand.json)" if brand.get("synthetic") else ""),
        f"Mark: {brand.get('mark')} | monogram: {brand.get('monogram')}",
        "Warna: " + ", ".join(f"{k} {v}" for k, v in colors.items() if k != "on_primary"),
        f"Watermark: {watermark.get('position')} skala {watermark.get('scale')} "
        f"opasitas {watermark.get('opacity')} varian "
        + ", ".join(sorted((watermark.get("variants") or {}))),
        "Gaya tulis: " + ", ".join(f"{k}={v}" for k, v in voice.items() if v),
    ]
    problems = validator.validate_profile(brand)
    lines.append("Validasi: " + ("lengkap" if not problems else "; ".join(problems)))
    send_chat_message("\n".join(lines), chat_id=chat_id)


def handle_callback(chat_id, message_id, callback_id, data):
    """Menjalankan aksi dari tombol inline.

    Tombol hanya menyusun teks permintaan; logika tetap milik router dan
    build_package supaya tidak ada dua jalur kebenaran.
    """
    answer_callback(callback_id)
    info(f"[{_stamp(chat_id)}] tombol ditekan: {data}")

    if data == keyboards.BACK_PREFIX:
        edit_chat_message(chat_id, message_id, keyboards.home_text(),
                          reply_markup=keyboards.home_markup())
        return True

    if data.startswith(keyboards.HISTORY_PREFIX):
        account_id = data[len(keyboards.HISTORY_PREFIX):]
        account = accounts_mod.find_account(account_id)
        if account:
            _reply_history(chat_id, account)
        return True

    if data.startswith(keyboards.STYLE_PREFIX):
        account_id = data[len(keyboards.STYLE_PREFIX):]
        _handle_style(chat_id, f"/style {account_id}")
        return True

    if data.startswith(keyboards.PREVIEW_PREFIX):
        payload = data[len(keyboards.PREVIEW_PREFIX):]
        account_id, _, fmt = payload.partition(":")
        account = accounts_mod.find_account(account_id)
        if not account:
            send_chat_message("Akun tidak dikenal.", chat_id=chat_id)
            return True
        if not fmt:
            edit_chat_message(chat_id, message_id,
                              f"Preview tampilan {account.get('label')}:",
                              reply_markup=keyboards.preview_markup(account_id))
            return True
        edit_chat_message(chat_id, message_id, f"Diproses: preview {account_id} {fmt}",
                          reply_markup=None)
        _handle_preview(chat_id, f"/preview {account_id} {fmt}")
        return True

    if data.startswith(keyboards.ACCOUNT_PREFIX):
        account_id = data[len(keyboards.ACCOUNT_PREFIX):]
        account = accounts_mod.find_account(account_id)
        if not account:
            send_chat_message("Akun tidak dikenal.", chat_id=chat_id)
            return True
        edit_chat_message(chat_id, message_id, keyboards.account_text(account_id),
                          reply_markup=keyboards.account_markup(account_id))
        return True

    if data.startswith(keyboards.TASK_PREFIX):
        payload = data[len(keyboards.TASK_PREFIX):]
        parts = payload.split(":", 2)
        if len(parts) < 2:
            return True
        account_id, task = parts[0], parts[1]
        arg = parts[2] if len(parts) > 2 else ""

        # Menu pengingat hanya menampilkan tombol tahap, belum menjalankan apa pun.
        if arg == keyboards.STAGE_MENU_MARKER:
            stages = keyboards.stage_markup(account_id, task)
            if stages:
                edit_chat_message(
                    chat_id, message_id,
                    f"Pilih tahap pengingat untuk {keyboards.task_request(account_id, task, '')}:",
                    reply_markup=stages,
                )
            return True

        request = keyboards.task_request(account_id, task, arg)

        edit_chat_message(chat_id, message_id, f"Diproses: {request}", reply_markup=None)
        handle_message(chat_id, request)
        return True

    return False


def _is_unclear(keyword, topic):
    """Permintaan terlalu pendek atau cuma sapaan tidak layak jadi konten.

    'tco' atau 'liga A' tetap dianggap jelas karena task-nya memang jelas.
    """
    if keyword:
        return False
    topic = _clean_text(topic)
    if len(topic.split()) < MIN_REQUEST_WORDS:
        return True
    return topic.lower() in SHORT_REQUESTS


def handle_message(chat_id, text, request_id=None):
    text = _clean_text(text)
    if not text:
        return

    request_id = request_id or uuid.uuid4().hex[:8]
    started = time.time()
    info(f"[{_stamp(chat_id)}] pesan masuk: {text}")

    if _handle_command(chat_id, text):
        return

    try:
        intent = router.parse(text)
    except FileNotFoundError as e:
        error(f"[{_stamp(chat_id)}] file akun bermasalah: {e}")
        send_chat_message(f"File akun belum ada: {e}", chat_id=chat_id)
        history_mod.log_request(request_id, text, status="config_error", error=str(e))
        return
    except ValueError as e:
        error(f"[{_stamp(chat_id)}] file akun rusak: {e}")
        send_chat_message(f"Konfigurasi akun bermasalah: {e}", chat_id=chat_id)
        history_mod.log_request(request_id, text, status="config_error", error=str(e))
        return

    info(f"[{_stamp(chat_id)}] intent {router.describe(intent)}")

    account = accounts_mod.find_account(intent["account"])
    if account is None:
        # accounts.json tidak punya akun sama sekali: jangan crash diam-diam.
        error("Tidak ada akun yang bisa dipakai. Periksa accounts.json.")
        send_chat_message(
            "Belum ada akun terdaftar. Isi accounts.json lalu jalankan ulang.", chat_id=chat_id
        )
        history_mod.log_request(request_id, text, status="config_error",
                                error="tidak ada akun terdaftar")
        return

    topic = intent.get("topic") or "tren terbaru"

    if intent["task"] == "history":
        _reply_history(chat_id, account)
        history_mod.log_request(request_id, text, account["id"], "history", "ok",
                                int((time.time() - started) * 1000))
        return

    if intent["task"] == "plan":
        # Plan mingguan belum punya pembuat sendiri, jadi topik diperjelas dan
        # jumlah konten mengikuti angka di permintaan.
        send_chat_message(
            "Plan mingguan belum punya mode terpisah. Yang bisa diproses sekarang "
            f"sebagai daftar ide: {intent.get('quantity', 7)} konten untuk "
            f"{account.get('label')}.",
            chat_id=chat_id,
        )
        intent["task"] = "content"
        intent["topic"] = "ide konten mingguan"

    # Task operasional klub catur memakai data spreadsheet, bukan riset tren.
    if intent["task"] in ("tco_weekly", "league_standing", "arena_schedule"):
        _handle_club_task(chat_id, intent, account, request_id)
        return

    if _is_unclear(intent.get("keyword"), intent.get("topic")):
        info(f"[{_stamp(chat_id)}] permintaan tidak jelas, dibalas dengan panduan: {text!r}")
        send_chat_message(
            "Pesannya belum jelas. Sebutkan niche dan колиaknya, contoh:\n"
            "buatkan 1 konten tren wedding\n"
            "bikin 3 konten mlbb tentang counter hayabusa\n"
            "buat pengumuman liga B\n"
            "tco minggu ini\n"
            "arena kings bulan ini\n\n"
            "Ketik /bantu untuk panduan lengkap.",
            chat_id=chat_id,
            reply_markup=keyboards.home_markup(),
        )
        return

    # Peringatan duplikasi: beri tahu, tapi jangan pernah memblokir permintaan.
    duplicate_note = _duplicate_note(account["id"], topic)
    if duplicate_note:
        info(f"[{_stamp(chat_id)}] {duplicate_note}")
        send_chat_message(f"Catatan: {duplicate_note}", chat_id=chat_id)

    send_chat_message(
        f"Sedang membuat konten untuk {account.get('label')}... ({topic})", chat_id=chat_id
    )

    try:
        package = build_package(intent, account, chat_id=chat_id, request_id=request_id)
        _reply(chat_id, package)
        history_mod.log_request(request_id, text, account["id"], intent["task"], "ok",
                                int((time.time() - started) * 1000))
    except Exception as e:
        error(f"[{_stamp(chat_id)}] gagal membuat konten: {e}")
        send_chat_message(f"Gagal membuat konten: {e}", chat_id=chat_id)
        history_mod.log_request(request_id, text, account["id"], intent["task"], "error",
                                int((time.time() - started) * 1000), str(e))


def _handle_club_task(chat_id, intent, account, request_id):
    """Menjalankan TCO, Liga, atau Arena Kings dari data spreadsheet."""
    started = time.time()
    task = intent["task"]

    if task == "tco_weekly":
        # Tahap pengingat H-2 dan H-1 diambil dari intent; tanpa tahap, pesan utama.
        package = chess_tco.build_tco_package(stage=intent.get("stage") or "pengumuman")
    elif task == "league_standing":
        package = chess_liga.build_league_package(
            intent.get("league"),
            with_schedule=bool(intent.get("jadwal")),
        )
    else:
        # Tanpa url dari user, link diambil dari sheet Arena. URL dari
        # "/arena link <url>" menang kalau ada, jadi perintah manual tetap jalan
        # walau sheet belum diisi.
        package = chess_arena.build_arena_package(
            stage=intent.get("stage") or "pengumuman",
            link=intent.get("url"),
        )

    info(
        f"[{_stamp(chat_id)}] {task} {account['id']} "
        f"tahap={package.get('stage', '-')} "
        f"tersedia={package.get('available')} alasan={package.get('reason', '-')}"
    )

    if not package.get("available"):
        # Tidak ada data berarti bot mengatakannya terus terang, bukan mengarang.
        send_chat_message(package["wa"], chat_id=chat_id)
        history_mod.log_request(request_id, intent.get("raw"), account["id"], task, "no_data",
                                int((time.time() - started) * 1000),
                                package.get("reason", "data tidak tersedia"))
        return

    # Tahap ikut masuk ke judul supaya histori bisa membedakan pengumuman H-14,
    # H-7, dan pengingat dekat yang isinya sama-sama pesan yang sama.
    stage = package.get("stage")
    title = f"{task}:{stage}" if stage else task

    record = history_mod.record_content(
        account["id"],
        topic=intent.get("topic") or task,
        title=title,
        task=task,
        content_type="text",
        category=task,
        request_id=request_id,
    )
    content_id = record["id"]

    blocks = [package["wa"]]
    if package.get("table") and package["table"] != package["wa"]:
        blocks.append(package["table"])
    send_chat_message(f"ID: {content_id}\n\n" + "\n\n".join(blocks), chat_id=chat_id)

    media = None
    try:
        media = _render_club_poster(package, account)
    except Exception as e:
        warn(f"[{_stamp(chat_id)}] poster gagal dibuat: {e}")

    if media:
        send_telegram_media(media, chat_id=chat_id)
        history_mod.set_file(content_id, media, caption=package.get("caption"))
    else:
        history_mod.set_file(content_id, "", caption=package.get("caption"))

    history_mod.log_request(request_id, intent.get("raw"), account["id"], task, "ok",
                            int((time.time() - started) * 1000))


def _render_club_poster(package, account):
    """Membuat poster dari baris teks yang sudah disiapkan modul catur."""
    points = package.get("poster") or []
    if not points:
        return None
    title = points[0]
    content = {
        "title": title,
        "subtitle": account.get("label", ""),
        "points": points[1:],
        "cta": "TCO - Klub Catur Indonesia",
        "caption": package.get("caption") or "",
        "hashtags": account.get("hashtags", [])[:3],
    }
    category = package.get("category") or "tco_weekly"
    return render_content_image(content, footer=account.get("label", ""),
                                brand=brand_mod.brand_for(account), category=category)


def _duplicate_note(account_id, topic):
    """Pesan singkat bila topik mirip riwayat, dengan saran angle lain."""
    try:
        exact = history_mod.is_duplicate(account_id, topic)
        similar = history_mod.duplicate_candidates(account_id, topic, limit=3)
    except Exception as e:  # histori tidak boleh menghentikan produksi konten
        warn(f"cek histori gagal: {e}")
        return None

    if not similar:
        return None
    if exact:
        return (
            f"Topik '{topic}' sudah pernah dibuat ({similar[0]['id']}). "
            "Sedang dibuat versi dengan angle berbeda."
        )
    ids = ", ".join(item["id"] for item in similar)
    return f"Topik mirip sudah ada: {ids}. Bot akan cari angle berbeda."


def _reply_history(chat_id, account):
    """Menampilkan konten terakhir untuk satu akun."""
    rows = history_mod.recent(account["id"], limit=10)
    header = f"🕘 Riwayat {account.get('label')}"
    if not rows:
        send_chat_message(f"{header}\n\nBelum ada konten tersimpan.", chat_id=chat_id)
        return
    lines = [header, ""]
    for row in rows:
        status = row.get("status") or "-"
        lines.append(f"{row['id']} | {row.get('topic') or row.get('title') or '-'} | {status}")
    send_chat_message("\n".join(lines), chat_id=chat_id)


def authorized_chat():
    allowed = {os.getenv("TELEGRAM_CHAT_ID")}
    extra = os.getenv("TELEGRAM_ALLOWED_CHATS") or ""
    allowed.update(part.strip() for part in extra.split(",") if part.strip())
    return {a for a in allowed if a}


def run(poll_timeout=30):
    """Long polling: bot berjalan permanen sampai proses dihentikan."""
    info("=== [BOT PEMBUAT KONTEN AKTIF] ===")
    try:
        for account in accounts_mod.list_accounts():
            info(f"  - {account['id']}: {account.get('niche', '')}")
    except (FileNotFoundError, ValueError) as e:
        error(f"Gagal memuat akun: {e}")
        return

    allowed = authorized_chat()
    if not allowed:
        error("TELEGRAM_CHAT_ID belum diset, bot tidak bisa memproses pesan.")
        return

    info(f"Chat diizinkan: {sorted(allowed)}")
    info(f"Log ditulis ke: {LOG_PATH}")

    offset = None
    while True:
        updates = get_updates(
            offset=offset, timeout=poll_timeout, allowed_updates=["message", "callback_query"]
        )
        if not updates:
            continue

        for update in updates:
            offset = update["update_id"] + 1

            callback = update.get("callback_query")
            if callback:
                chat = (callback.get("message") or {}).get("chat") or {}
                chat_id = str(chat.get("id") or "")
                if not chat_id or chat_id not in allowed:
                    answer_callback(callback.get("id"), text="Tidak diizinkan.", show_alert=True)
                    continue
                try:
                    handle_callback(
                        chat_id,
                        callback["message"].get("message_id"),
                        callback.get("id"),
                        callback.get("data") or "",
                    )
                except Exception as e:
                    error(f"[chat {chat_id}] tombol gagal: {e}")
                    send_chat_message(f"Tombol gagal diproses: {e}", chat_id=chat_id)
                time.sleep(1)
                continue

            message = update.get("message") or {}
            chat = (message.get("chat") or {}).get("id")
            text = message.get("text")

            if not chat or not text:
                continue
            if str(chat) not in allowed:
                warn(f"Chat {chat} tidak diizinkan, pesan diabaikan.")
                continue

            try:
                handle_message(str(chat), text)
            except Exception as e:
                error(f"[chat {chat}] kesalahan tak terduga: {e}")
                send_chat_message(f"Terjadi kesalahan: {e}", chat_id=str(chat))
            time.sleep(1)


if __name__ == "__main__":
    setup_logging()
    run()