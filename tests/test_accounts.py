"""Test registry akun: schema v2, fallback, dan deteksi mode."""
import json

import pytest

from utils import accounts as accounts_mod


def test_loads_four_accounts():
    data = accounts_mod.load()
    ids = [a["id"] for a in data["accounts"]]
    assert ids == ["chess", "wedding", "mlbb", "fashion"]


def test_schema_version_is_two():
    assert accounts_mod.schema_version() >= 2


def test_default_account_is_chess():
    assert accounts_mod.default_account()["id"] == "chess"


def test_operational_accounts_only_chess():
    assert [a["id"] for a in accounts_mod.operational_accounts()] == ["chess"]


def test_has_mode():
    chess = accounts_mod.find_account("chess")
    wedding = accounts_mod.find_account("wedding")
    assert accounts_mod.has_mode(chess, "club_operations")
    assert not accounts_mod.has_mode(wedding, "club_operations")


@pytest.mark.parametrize("account_id", ["chess", "wedding", "mlbb", "fashion"])
def test_every_account_has_required_new_fields(account_id):
    account = accounts_mod.find_account(account_id)
    assert account["mode"], "mode wajib ada"
    assert account["fact_check_rules"], "aturan fact-check wajib ada"
    assert account["content_categories"], "kategori konten wajib ada"
    assert account["seed_topics"], "seed topics wajib ada"


def test_longest_keyword_wins():
    account, keyword = accounts_mod.match_account("buat konten wedding day")
    assert account["id"] == "wedding"
    assert keyword == "wedding day"


def test_match_account_without_fallback():
    account, keyword = accounts_mod.match_account("halo dunia", fallback=False)
    assert account is None
    assert keyword is None


def test_match_account_with_fallback_returns_default():
    account, keyword = accounts_mod.match_account("halo dunia")
    assert account["id"] == "chess"
    assert keyword is None


def test_missing_file_raises_clear_error(tmp_path):
    missing = str(tmp_path / "tidak-ada.json")
    with pytest.raises(FileNotFoundError) as e:
        accounts_mod.load(missing)
    assert "tidak-ada.json" in str(e.value)


def test_broken_json_raises_value_error(tmp_path):
    bad = tmp_path / "rusak.json"
    bad.write_text("{bukan json", encoding="utf-8")
    with pytest.raises(ValueError):
        accounts_mod.load(str(bad))


def test_missing_required_field_is_reported(tmp_path):
    bad = tmp_path / "kurang.json"
    bad.write_text(json.dumps({"accounts": [{"id": "x", "label": "X"}]}), encoding="utf-8")
    with pytest.raises(ValueError) as e:
        accounts_mod.load(str(bad))
    assert "niche" in str(e.value)


def test_duplicate_account_id_is_rejected(tmp_path):
    dup = tmp_path / "dup.json"
    dup.write_text(
        json.dumps(
            {
                "accounts": [
                    {"id": "a", "label": "A", "niche": "n"},
                    {"id": "a", "label": "A2", "niche": "n"},
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as e:
        accounts_mod.load(str(dup))
    assert "lebih dari sekali" in str(e.value)


def test_old_schema_v1_still_loads(tmp_path):
    """Skema lama tanpa field baru harus tetap bisa dibaca."""
    legacy = tmp_path / "lama.json"
    legacy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "default_account": "wedding",
                "accounts": [{"id": "wedding", "label": "W", "niche": "n"}],
            }
        ),
        encoding="utf-8",
    )
    data = accounts_mod.load(str(legacy))
    account = data["accounts"][0]
    assert account["mode"] == ["content"]
    assert account["hashtags"] == []


def test_empty_account_list_is_rejected(tmp_path):
    empty = tmp_path / "kosong.json"
    empty.write_text(json.dumps({"accounts": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        accounts_mod.load(str(empty))