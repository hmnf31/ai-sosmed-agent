"""Test engine per akun: kategori, aturan fact-check, dan dedup context."""
from utils import engines


def test_general_engine_used_for_unknown_account():
    engine = engines.engine_for("tidak-ada")
    assert isinstance(engine, engines.GeneralEngine)


def test_each_account_has_its_own_engine():
    for account_id in ("chess", "wedding", "mlbb", "fashion"):
        assert type(engines.engine_for(account_id)) is not engines.GeneralEngine


def test_mlbb_detects_specific_categories():
    engine = engines.engine_for("mlbb")
    assert engine.detect_category("konten patch terbaru") == "patch"
    assert engine.detect_category("counter hayabusa") == "counter"
    assert engine.detect_category("berita MPL ID") == "mpl"
    assert engine.detect_category("build emblems") == "build"


def test_fashion_detects_affiliate_and_ootd():
    engine = engines.engine_for("fashion")
    assert engine.detect_category("ootd ke kampus") == "ootd"
    assert engine.detect_category("konten affiliate produk") == "affiliate"


def test_chess_detects_opening_and_endgame():
    engine = engines.engine_for("chess")
    assert engine.detect_category("opening untuk pemula") == "opening"
    assert engine.detect_category("tips endgame") == "tips"


def test_mlbb_brief_has_strict_fact_rules():
    account = {"fact_check_rules": ["aturan dasar"]}
    brief = engines.engine_for("mlbb").build_brief("patch terbaru", "patch", account)
    joined = " ".join(brief["extra_rules"])
    assert "statistik pemain tidak boleh dibuat" in joined
    assert "data tidak tersedia" in joined


def test_wedding_brief_forbids_fake_prices():
    account = {"fact_check_rules": []}
    brief = engines.engine_for("wedding").build_brief("tren dekorasi", "dekorasi", account)
    joined = " ".join(brief["extra_rules"])
    assert "harga paket" in joined


def test_wedding_trend_gets_angle_hint():
    account = {"fact_check_rules": []}
    brief = engines.engine_for("wedding").build_brief(
        "tren wedding", "dekorasi minimalis", account
    )
    assert brief["category"] == "tren"
    assert brief["angle_hint"]


def test_affiliate_brief_gets_problem_focus():
    account = {"fact_check_rules": []}
    brief = engines.engine_for("fashion").build_brief(
        "konten affiliate", "tas kerja", account
    )
    assert brief["angle_hint"]


def test_brief_keeps_request_and_topic():
    account = {"fact_check_rules": []}
    brief = engines.engine_for("wedding").build_brief(
        "buat ide", "venue kecil", account, category="ide"
    )
    assert brief["request"] == "buat ide"
    assert brief["topics"] == ["venue kecil"]
    assert brief["category"] == "ide"


def test_extra_instructions_per_category():
    engine = engines.engine_for("wedding")
    assert engine.extra_instructions({"category": "tren"})
    assert engine.extra_instructions({"category": "reels"})
    assert engine.extra_instructions({"category": None}) == ""


def test_extract_links_returns_plain_urls():
    text = "Cek [artikel](https://example.com/a) dan https://example.com/b."
    assert engines.extract_links(text) == ["https://example.com/a", "https://example.com/b"]


def test_extract_links_empty():
    assert engines.extract_links("tidak ada link") == []


def test_category_words_exposed():
    assert "patch" in engines.category_words_for("mlbb")