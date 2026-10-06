"""Test alur bot: parsing pesan, tombol menu, dan pencatatan histori."""
from utils import history


def test_menu_command_sends_home_with_buttons(fake_notifier):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "/menu")
    last = fake_notifier["sent"][-1]
    assert "SOCIAL MEDIA ASSISTANT" in last["text"]
    assert len(last["reply_markup"]["inline_keyboard"]) == 4


def test_account_callback_switches_to_account_menu(fake_notifier):
    from utils import telegram_bot

    telegram_bot.handle_callback("123", 5, "cb", "menu:account:mlbb")
    edit = fake_notifier["edited"][-1]
    assert edit["message_id"] == 5
    assert "MLBB" in edit["text"]
    assert edit["reply_markup"]["inline_keyboard"]


def test_task_callback_runs_content_pipeline(fake_notifier, fake_pipeline, db_path):
    from utils import telegram_bot

    telegram_bot.handle_callback("123", 5, "cb", "menu:task:mlbb:content:counter")
    assert fake_pipeline["ai"], "AI harus dipanggil"
    assert fake_pipeline["render"], "renderer harus dipanggil"
    assert fake_notifier["media"], "media harus dikirim"
    assert fake_notifier["answered"] == ["cb"], "callback harus dijawab"


def test_content_is_recorded_with_id(fake_notifier, fake_pipeline, db_path):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "buatkan konten mlbb tentang counter hayabusa")
    rows = history.recent("mlbb", path=db_path)
    assert len(rows) == 1
    assert rows[0]["id"] == "2026-001"
    assert rows[0]["file_path"] == "output/test-video.mp4"
    assert rows[0]["status"] == "generated"


def test_duplicate_topic_sends_warning(fake_notifier, fake_pipeline, db_path):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "buatkan konten mlbb counter hayabusa")
    telegram_bot.handle_message("123", "buatkan konten mlbb counter hayabusa")
    warnings = [m for m in fake_notifier["sent"] if m["text"].startswith("Catatan:")]
    assert warnings, "peringatan duplikasi harus dikirim"
    assert "sudah pernah dibuat" in warnings[-1]["text"]


def test_duplicate_does_not_block_creation(fake_notifier, fake_pipeline, db_path):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "buatkan konten mlbb counter hayabusa")
    telegram_bot.handle_message("123", "buatkan konten mlbb counter hayabusa")
    assert len(history.recent("mlbb", path=db_path)) == 2


def test_brand_dikirim_ke_ai_dan_renderer(fake_notifier, fake_pipeline, db_path):
    """Satu akun = satu brand, dari prompt sampai gambar."""
    from utils import telegram_bot

    telegram_bot.handle_message("123", "buatkan konten mlbb counter hayabusa")
    assert fake_pipeline["ai"][0]["brand_account"] == "mlbb"
    assert fake_pipeline["render"][0][4] == "mlbb"


def test_template_dipilih_sesuai_kategori(fake_notifier, fake_pipeline, db_path):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "buatkan konten mlbb counter hayabusa")
    template = fake_pipeline["render"][0][3]
    assert template == "counter"


def test_pesan_menyebut_template_dan_catatan_branding(fake_notifier, fake_pipeline,
                                                        db_path):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "buatkan 1 konten tren wedding")
    teks = "\n".join(m["text"] for m in fake_notifier["sent"])
    assert "Template: wedding_trend" in teks


def test_perintah_style_menampilkan_ringkasan_brand(fake_notifier):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "/style mlbb")
    teks = fake_notifier["sent"][-1]["text"]
    assert "Brand" in teks and "mlbb" in teks
    assert "Watermark:" in teks
    assert "SINTETIS" not in teks


def test_perintah_preview_mengirim_media(fake_notifier, tmp_path, monkeypatch):
    from utils import telegram_bot
    from utils.media import layout_engine

    monkeypatch.setenv("CONTENT_OUTPUT_DIR", str(tmp_path))
    telegram_bot.handle_message("123", "/preview wedding image")
    assert fake_notifier["media"], "preview harus mengirim media"
    caption = fake_notifier["media"][-1]["caption"]
    assert "Template:" in caption
    assert "watermark:" in caption
    assert layout_engine.media_size_ok(fake_notifier["media"][-1]["path"], "square")[0]


def test_tombol_preview_membuka_pilihan_format(fake_notifier):
    from utils import telegram_bot

    telegram_bot.handle_callback("123", 5, "cb", "menu:preview:chess")
    edit = fake_notifier["edited"][-1]
    data = [b["callback_data"] for row in edit["reply_markup"]["inline_keyboard"] for b in row]
    assert "menu:preview:chess:portrait" in data


def test_tombol_style_menampilkan_ringkasan(fake_notifier):
    from utils import telegram_bot

    telegram_bot.handle_callback("123", 5, "cb", "menu:style:fashion")
    assert "Fashion" in fake_notifier["sent"][-1]["text"]


def test_greeting_gets_guide_with_buttons(fake_notifier, fake_pipeline, db_path):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "halo")
    last = fake_notifier["sent"][-1]
    assert "belum jelas" in last["text"]
    assert last["reply_markup"]["inline_keyboard"]


def test_tco_weekly_records_operational_task(fake_notifier, fake_pipeline, db_path, monkeypatch):
    """Task TCO memakai data spreadsheet, bukan jalur riset tren."""
    from utils import telegram_bot

    event = {
        "tanggal": "2026-10-07", "tanggal_teks": "2026-10-07", "waktu": "20:00",
        "format": "Blitz", "lokasi": "Online", "link": "https://chess.com/tco",
        "keterangan": "", "source": "csv", "found": True,
    }
    monkeypatch.setattr(telegram_bot.chess_tco.spreadsheet, "get_tco_schedule",
                        lambda when=None: event)

    telegram_bot.handle_message("123", "tco minggu ini")
    rows = history.recent("chess", path=db_path)
    assert rows[0]["task"] == "tco_weekly"
    assert rows[0]["content_type"] == "text"
    assert rows[0]["file_path"]
    assert fake_notifier["media"], "poster harus dikirim"
    # Jalur konten/tren tidak boleh dipakai untuk task operasional.
    assert fake_pipeline["ai"] == []


def test_tco_without_sheet_data_does_not_fabricate(fake_notifier, fake_pipeline, db_path):
    """Tanpa spreadsheet, bot bilang data belum ada dan tidak membuat konten."""
    from utils import telegram_bot

    telegram_bot.handle_message("123", "tco minggu ini")
    last = fake_notifier["sent"][-1]["text"]
    assert "belum tersedia" in last
    assert fake_notifier["media"] == []
    assert history.recent("chess", path=db_path) == []
    assert history.requests_recent(path=db_path)[0]["status"] == "no_data"


def test_history_command_lists_rows(fake_notifier, fake_pipeline, db_path):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "buatkan konten mlbb counter hayabusa")
    telegram_bot.handle_message("123", "riwayat mlbb")
    last = fake_notifier["sent"][-1]
    assert "Riwayat" in last["text"]
    assert "2026-001" in last["text"]


def test_history_command_when_empty(fake_notifier, fake_pipeline, db_path):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "riwayat wedding")
    assert "Belum ada konten" in fake_notifier["sent"][-1]["text"]


def test_history_callback_button(fake_notifier, fake_pipeline, db_path):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "buatkan konten fashion ootd")
    telegram_bot.handle_callback("123", 9, "cb", "menu:history:fashion")
    assert "2026-001" in fake_notifier["sent"][-1]["text"]


def test_back_button_returns_home(fake_notifier):
    from utils import telegram_bot

    telegram_bot.handle_callback("123", 7, "cb", "menu:back")
    edit = fake_notifier["edited"][-1]
    assert edit["message_id"] == 7
    assert "SOCIAL MEDIA ASSISTANT" in edit["text"]


def test_status_reports_counts(fake_notifier, fake_pipeline, db_path):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "buatkan konten mlbb patch terbaru")
    telegram_bot.handle_message("123", "/status")
    assert "mlbb" in fake_notifier["sent"][-1]["text"]


def test_request_logged_with_duration(fake_notifier, fake_pipeline, db_path):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "buatkan konten mlbb patch terbaru")
    rows = history.requests_recent(path=db_path)
    assert rows
    assert rows[0]["status"] == "ok"
    assert rows[0]["duration_ms"] is not None


def test_research_sources_wired_into_content(fake_notifier, fake_pipeline, db_path, monkeypatch):
    """Sumber riset mengalir ke prompt AI, ditanam ke content, dan tampil di balasan."""
    from utils import telegram_bot

    pack = {
        "build_at": "2026-10-06T09:00:00+07:00",
        "items": [{
            "source_id": "src_abc",
            "url": "https://contoh.id/mlbb-patch",
            "title": "Patch Note Resmi",
            "publisher": "contoh.id",
            "published_date": "2026-10-05",
            "retrieved_at": "2026-10-06T09:00:00+07:00",
            "claim": "Patch terbaru MLBB",
            "status": "verified",
        }],
    }
    monkeypatch.setattr(telegram_bot, "_build_research", lambda request, account: pack)
    telegram_bot.handle_message("123", "buatkan konten mlbb patch terbaru")

    assert fake_pipeline["ai"][-1]["sources"][0]["url"] == "https://contoh.id/mlbb-patch"
    last = fake_notifier["sent"][-1]["text"]
    assert "Riset: 1 sumber" in last
    assert "verified" in last
    # source_url hasil AI kosong -> diisi dari sumber riset, lalu dikirim.
    assert "Sumber: https://contoh.id/mlbb-patch" in last


def test_research_empty_still_produces_content(fake_notifier, fake_pipeline, db_path, monkeypatch):
    """Paket riset kosong (mis. seed gagal) tidak menghentikan produksi konten."""
    from utils import telegram_bot

    monkeypatch.setattr(
        telegram_bot, "_build_research",
        lambda request, account: {"items": [], "build_at": None, "used_fallback": True},
    )
    telegram_bot.handle_message("123", "buatkan konten mlbb counter hayabusa")
    assert fake_pipeline["ai"], "AI tetap harus dipanggil walau riset kosong"
    assert fake_notifier["media"]


def test_failure_is_logged_as_error(fake_notifier, db_path, monkeypatch):
    from utils import telegram_bot

    def _boom(*args, **kwargs):
        raise RuntimeError("riset gagal")

    monkeypatch.setattr(telegram_bot, "_build_research", _boom)
    telegram_bot.handle_message("123", "buatkan konten mlbb patch terbaru")
    assert any("riset gagal" in m["text"] for m in fake_notifier["sent"])
    assert history.requests_recent(path=db_path)[0]["status"] == "error"


def test_history_failure_does_not_stop_creation(fake_notifier, fake_pipeline, db_path, monkeypatch):
    """Histori bermasalah tidak boleh memblokir pembuatan konten."""
    from utils import telegram_bot

    monkeypatch.setattr(history, "is_duplicate", lambda *a, **k: (_ for _ in ()).throw(OSError("db locked")))
    telegram_bot.handle_message("123", "buatkan konten mlbb patch terbaru")
    assert len(history.recent("mlbb", path=db_path)) == 1
    assert fake_notifier["media"]


def test_help_and_account_commands(fake_notifier):
    from utils import telegram_bot

    telegram_bot.handle_message("123", "/bantu")
    assert "Social Media Assistant" in fake_notifier["sent"][-1]["text"]

    telegram_bot.handle_message("123", "/akun")
    listing = fake_notifier["sent"][-1]["text"]
    for account_id in ("chess", "wedding", "mlbb", "fashion"):
        assert account_id in listing