"""Test menu tombol: isi tombol dan teks permintaan yang dihasilkan."""
from utils import keyboards


def test_home_has_one_button_per_account():
    rows = keyboards.home_markup()["inline_keyboard"]
    assert len(rows) == 4
    assert rows[0][0]["callback_data"] == "menu:account:chess"


def test_account_menu_has_action_rows():
    rows = keyboards.account_markup("mlbb")["inline_keyboard"]
    assert len(rows) >= 4
    assert rows[-1][0]["text"] == "🕘 Riwayat"
    assert rows[-1][1]["callback_data"] == "menu:back"


def test_unknown_account_falls_back_to_generic_menu():
    rows = keyboards.account_markup("tidak-ada")["inline_keyboard"]
    assert rows


def test_unknown_account_text_falls_back_to_home():
    assert "SOCIAL MEDIA ASSISTANT" in keyboards.account_text("tidak-ada")


def test_home_text_lists_accounts():
    text = keyboards.home_text()
    for label in ("Klub Catur", "Wedding", "MLBB", "Fashion"):
        assert label in text


def test_task_request_operational_tasks():
    assert keyboards.task_request("chess", "tco_weekly", "") == "tco minggu ini"
    assert keyboards.task_request("chess", "league_standing", "") == "liga klasemen terbaru"
    assert keyboards.task_request("chess", "arena_schedule", "") == "arena kings minggu ini"


def test_task_request_content_mentions_niche():
    request = keyboards.task_request("mlbb", "content", "counter")
    assert request.startswith("buatkan konten")
    assert "counter" in request
    assert "mlbb" in request


def test_task_request_does_not_duplicate_keyword():
    request = keyboards.task_request("mlbb", "content", "mlbb")
    assert request.lower().count("mlbb") == 1


def test_task_request_plan_uses_resolved_account():
    assert "fashion" in keyboards.task_request("fashion", "plan", "")


def test_task_request_unknown_account_still_builds_text():
    assert keyboards.task_request("tidak-ada", "content", "ide")