"""Test router: dari chat bebas menjadi intent terstruktur."""
import pytest

from utils import router


def test_content_request_with_niche():
    intent = router.parse("buatkan konten mlbb tentang counter hayabusa")
    assert intent["account"] == "mlbb"
    assert intent["task"] == "content"
    assert "hayabusa" in intent["topic"]


def test_chess_weekly_tco():
    intent = router.parse("tco minggu ini")
    assert intent["account"] == "chess"
    assert intent["task"] == "tco_weekly"
    assert intent["period"] == "current_week"


def test_league_command_extracts_league():
    intent = router.parse("/liga A")
    assert intent["task"] == "league_standing"
    assert intent["league"] == "A"


def test_league_free_text_also_detected():
    intent = router.parse("liga a update klasemen")
    assert intent["task"] == "league_standing"
    assert intent["league"] == "A"


def test_league_announcement_is_content_not_standing():
    intent = router.parse("buat pengumuman liga B")
    assert intent["task"] == "content"
    assert intent["league"] == "B"


def test_arena_with_link():
    intent = router.parse("/arena link https://www.chess.com/abc123")
    assert intent["task"] == "arena_schedule"
    assert intent["url"] == "https://www.chess.com/abc123"


def test_operational_task_uses_image_format():
    assert router.parse("tco minggu ini")["format"] == "image"
    assert router.parse("liga a klasemen")["format"] == "image"


def test_quantity_detected():
    assert router.parse("buat 3 konten fashion affiliate")["quantity"] == 3


def test_quantity_out_of_range_ignored():
    assert router.parse("buat 99 konten drip kopi")["quantity"] == 1


def test_format_detection():
    assert router.parse("buat gambar ootd")["format"] == "image"
    assert router.parse("buat video reels ootd")["format"] == "video"


def test_platform_detection():
    intent = router.parse("buat konten ootd untuk instagram dan tiktok")
    assert set(intent["platform"]) == {"instagram", "tiktok"}


def test_history_task():
    assert router.parse("riwayat mlbb")["task"] == "history"
    assert router.parse("/history")["task"] == "history"


def test_plan_task():
    assert router.parse("/plan")["task"] == "plan"
    assert router.parse("buatkan plan konten mingguan")["task"] == "plan"


def test_plan_quantity_defaults_to_week():
    assert router.parse("/plan")["quantity"] == 7


def test_no_keyword_falls_back_to_default_account():
    assert router.parse("drip kopi")["account"] == "chess"


def test_is_operational_and_is_content():
    assert router.is_operational(router.parse("tco minggu ini"))
    assert router.is_content(router.parse("buatkan konten mlbb"))


@pytest.mark.parametrize(
    "text,expected_account",
    [
        ("buat konten wedding", "wedding"),
        ("bikin konten mlbb", "mlbb"),
        ("ootd hari ini", "fashion"),
        ("turnamen catur", "chess"),
    ],
)
def test_account_routing(text, expected_account):
    assert router.parse(text)["account"] == expected_account


def test_describe_contains_key_fields():
    described = router.describe(router.parse("/liga A"))
    assert "league_standing" in described
    assert "league=A" in described


def test_empty_text_does_not_crash():
    intent = router.parse("")
    assert intent["task"] == "content"
    assert intent["account"] == "chess"