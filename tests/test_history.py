"""Test histori konten: ID berurutan, deduplikasi, status, dan statistik."""
import pytest

from utils import history


def test_init_creates_tables(db_path):
    assert history.init_db(db_path) == db_path
    assert history.recent(path=db_path) == []


def test_content_id_is_sequential(db_path):
    first = history.record_content("mlbb", topic="Counter Hayabusa", path=db_path)
    second = history.record_content("mlbb", topic="Build Chou", path=db_path)
    assert first["id"] == "2026-001"
    assert second["id"] == "2026-002"


def test_topic_key_normalization(db_path):
    record = history.record_content("mlbb", topic="Counter HAYABUSA!", path=db_path)
    assert record["topic_key"] == "counter hayabusa"


def test_duplicate_detected_per_account(db_path):
    history.record_content("mlbb", topic="Counter Hayabusa", path=db_path)
    assert history.is_duplicate("mlbb", "counter hayabusa", path=db_path)
    assert not history.is_duplicate("wedding", "counter hayabusa", path=db_path)


def test_empty_topic_is_not_duplicate(db_path):
    history.record_content("mlbb", topic="apapun", path=db_path)
    assert not history.is_duplicate("mlbb", "", path=db_path)


def test_duplicate_candidates_finds_similar_topic(db_path):
    history.record_content("mlbb", topic="Counter Hayabusa", path=db_path)
    candidates = history.duplicate_candidates("mlbb", "Counter Hiu", path=db_path)
    assert [c["id"] for c in candidates] == ["2026-001"]


def test_duplicate_candidates_empty_for_new_topic(db_path):
    history.record_content("mlbb", topic="Counter Hayabusa", path=db_path)
    assert history.duplicate_candidates("mlbb", "Brand baru sekali", path=db_path) == []


def test_status_transition_allowed(db_path):
    record = history.record_content("mlbb", topic="Hero X", path=db_path)
    assert history.update_status(record["id"], "approved", path=db_path) == "approved"
    assert history.update_status(record["id"], "published", path=db_path) == "published"


def test_invalid_status_transition_rejected(db_path):
    record = history.record_content("mlbb", topic="Hero X", path=db_path)
    history.update_status(record["id"], "approved", path=db_path)
    with pytest.raises(ValueError):
        history.update_status(record["id"], "rejected", path=db_path)


def test_status_of_unknown_id_rejected(db_path):
    with pytest.raises(ValueError):
        history.update_status("9999-999", "approved", path=db_path)


def test_set_file_saves_path_and_caption(db_path):
    record = history.record_content("mlbb", topic="Hero X", path=db_path)
    history.set_file(record["id"], "output/2026-001.mp4", caption="cap", path=db_path)
    saved = history.get_content(record["id"], path=db_path)
    assert saved["file_path"] == "output/2026-001.mp4"
    assert saved["caption"] == "cap"


def test_recent_newest_first(db_path):
    for i in range(3):
        history.record_content("mlbb", topic=f"Topik {i}", path=db_path)
    rows = history.recent("mlbb", path=db_path)
    assert [r["id"] for r in rows] == ["2026-003", "2026-002", "2026-001"]


def test_recent_filters_by_account(db_path):
    history.record_content("mlbb", topic="Satu", path=db_path)
    history.record_content("wedding", topic="Dua", path=db_path)
    assert len(history.recent("wedding", path=db_path)) == 1


def test_account_stats_counts_all(db_path):
    history.record_content("mlbb", topic="A", path=db_path)
    history.record_content("mlbb", topic="B", path=db_path)
    history.record_content("fashion", topic="C", path=db_path)
    assert history.account_stats(path=db_path) == {"mlbb": 2, "fashion": 1}


def test_record_content_requires_account(db_path):
    with pytest.raises(ValueError):
        history.record_content("", topic="x", path=db_path)


def test_request_log_roundtrip(db_path):
    history.log_request("r1", "buat mlbb", "mlbb", "content", "ok", 120, path=db_path)
    history.log_request("r2", "tco", "chess", "tco_weekly", "error", 30, "boom", path=db_path)
    rows = {r["request_id"]: r for r in history.requests_recent(path=db_path)}
    assert rows["r1"]["status"] == "ok"
    assert rows["r2"]["error"] == "boom"


def test_duplicate_topic_does_not_block_new_record(db_path):
    """Topik yang sama tetap boleh dicatat; dedup hanya memberi peringatan."""
    history.record_content("mlbb", topic="Counter", path=db_path)
    second = history.record_content("mlbb", topic="Counter", path=db_path)
    assert second["id"] == "2026-002"
    assert len(history.recent("mlbb", path=db_path)) == 2