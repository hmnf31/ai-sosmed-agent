"""Test menu tombol: isi tombol dan teks permintaan yang dihasilkan."""
import pytest

from utils import keyboards, router


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
    assert keyboards.task_request("chess", "arena_schedule", "") == "arena kings bulan ini"


@pytest.mark.parametrize("tahap,harapan", [
    ("h7", "arena kings bulan ini h-7"),
    ("h14", "arena kings bulan ini h-14"),
    ("h2_jam", "arena kings bulan ini 2 jam lagi"),
    ("h1_jam", "arena kings bulan ini 1 jam lagi"),
])
def test_task_request_stage_menambah_pengingat(tahap, harapan):
    assert keyboards.task_request("chess", "arena_schedule", tahap) == harapan


def test_task_request_tco_stages():
    assert keyboards.task_request("chess", "tco_weekly", "h1_hari") == "tco minggu ini h-1"
    assert keyboards.task_request("chess", "tco_weekly", "h1_jam") == "tco minggu ini 1 jam lagi"


def test_task_request_league_schedule():
    assert keyboards.task_request("chess", "league_standing", "jadwal") == "jadwal liga berikutnya"


def test_stage_markup_only_for_multi_stage_tasks():
    assert keyboards.stage_markup("chess", "arena_schedule") is not None
    assert keyboards.stage_markup("chess", "tco_weekly") is not None
    assert keyboards.stage_markup("chess", "content") is None


def test_stage_markup_callbacks_round_trip_through_router():
    markup = keyboards.stage_markup("chess", "arena_schedule")
    seen = set()
    for row in markup["inline_keyboard"]:
        for button in row:
            data = button["callback_data"]
            if not data.startswith(keyboards.TASK_PREFIX):
                continue
            _, task, arg = data[len(keyboards.TASK_PREFIX):].split(":", 2)
            request = keyboards.task_request("chess", task, arg)
            seen.add(router.parse(request)["stage"])
    assert {"pengumuman", "h2_jam", "h1_jam"} <= seen


def test_chess_menu_has_stage_entry():
    markup = keyboards.account_markup("chess")
    texts = [b["text"] for row in markup["inline_keyboard"] for b in row]
    assert "⏱ Pengingat Arena" in texts


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