"""Job store: pembuatan job, transisi status, event, dan redaksi rahasia."""
import pytest

from utils import job_store


def test_create_job_starts_received(jobs_db_path):
    job = job_store.create_job("mlbb", "buat video tips jungler", path=jobs_db_path)
    assert job["job_id"] == "job_0001"
    assert job["status"] == "received"
    assert job["account"] == "mlbb"


def test_job_id_sequential(jobs_db_path):
    first = job_store.create_job("mlbb", "a", path=jobs_db_path)
    second = job_store.create_job("wedding", "b", path=jobs_db_path)
    assert first["job_id"] == "job_0001"
    assert second["job_id"] == "job_0002"


def test_create_job_requires_account(jobs_db_path):
    with pytest.raises(ValueError):
        job_store.create_job("", "x", path=jobs_db_path)


def test_get_unknown_job_returns_none(jobs_db_path):
    assert job_store.get_job("job_9999", path=jobs_db_path) is None


def test_full_happy_path(jobs_db_path):
    job = job_store.create_job("mlbb", "buat konten", path=jobs_db_path)
    for status in ("queued", "researching", "planning", "generating_assets",
                   "building_timeline", "rendering_preview", "qa_preview",
                   "awaiting_approval", "rendering_final", "qa_final", "delivered"):
        job_store.update_status(job["job_id"], status, message=f"ke {status}", path=jobs_db_path)
    saved = job_store.get_job(job["job_id"], path=jobs_db_path)
    assert saved["status"] == "delivered"
    assert len(job_store.events(job["job_id"], path=jobs_db_path)) == 12


def test_invalid_transition_rejected(jobs_db_path):
    job = job_store.create_job("mlbb", "x", path=jobs_db_path)
    with pytest.raises(ValueError, match="received -> delivered"):
        job_store.update_status(job["job_id"], "delivered", path=jobs_db_path)


def test_unknown_status_rejected(jobs_db_path):
    job = job_store.create_job("mlbb", "x", path=jobs_db_path)
    with pytest.raises(ValueError, match="Status tidak dikenal"):
        job_store.update_status(job["job_id"], "mengambang", path=jobs_db_path)


def test_update_unknown_job_rejected(jobs_db_path):
    with pytest.raises(ValueError, match="tidak ada"):
        job_store.update_status("job_9999", "queued", path=jobs_db_path)


def test_attach_plan_roundtrip(jobs_db_path):
    job = job_store.create_job("fashion", "outfit", path=jobs_db_path)
    plan = {
        "schema_version": "1.0",
        "job_id": job["job_id"],
        "account": "fashion",
        "content_type": "outfit_ideas",
        "format": "vertical_short",
        "language": "id-ID",
        "aspect_ratio": "9:16",
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "scenes": [{
            "scene_id": "scene_01",
            "duration_sec": 5,
            "purpose": "hook",
            "visual_type": "image",
            "visual_prompt": "outfit",
            "on_screen_text": "OOTD",
        }],
        "branding": {"profile": "fashion", "template_id": "fashion_reel",
                     "watermark_variant": "primary"},
    }
    job_store.attach_plan(job["job_id"], plan, path=jobs_db_path)
    saved = job_store.get_job(job["job_id"], path=jobs_db_path)
    assert saved["plan"]["content_type"] == "outfit_ideas"
    assert saved["content_type"] == "outfit_ideas"
    assert saved["account"] == "fashion"


def test_mark_failed_redacts_secret(jobs_db_path):
    job = job_store.create_job("chess", "x", path=jobs_db_path)
    job_store.mark_failed(
        job["job_id"],
        "koneksi gagal github_pat_11AKJACEA0yv6nfepWZ4ft_SegmenRahasia",
        path=jobs_db_path,
    )
    saved = job_store.get_job(job["job_id"], path=jobs_db_path)
    assert saved["status"] == "failed"
    assert "github_pat_" not in saved["error"]
    assert "[redacted]" in saved["error"]


def test_cancel_job(jobs_db_path):
    job = job_store.create_job("wedding", "x", path=jobs_db_path)
    job_store.cancel_job(job["job_id"], path=jobs_db_path)
    assert job_store.get_job(job["job_id"], path=jobs_db_path)["status"] == "cancelled"


def test_stats_group_by_status(jobs_db_path):
    a = job_store.create_job("mlbb", "x", path=jobs_db_path)
    job_store.create_job("mlbb", "y", path=jobs_db_path)
    job_store.create_job("fashion", "z", path=jobs_db_path)
    job_store.update_status(a["job_id"], "queued", path=jobs_db_path)
    job_store.update_status(a["job_id"], "planning", path=jobs_db_path)
    stats = job_store.stats(path=jobs_db_path)
    assert stats["received"] == 2
    assert stats["planning"] == 1
    for status in job_store.STATUS_FLOW:
        assert status in stats


def test_list_jobs_filters_account(jobs_db_path):
    job_store.create_job("mlbb", "x", path=jobs_db_path)
    job_store.create_job("chess", "y", path=jobs_db_path)
    rows = job_store.list_jobs(account="chess", path=jobs_db_path)
    assert [r["account"] for r in rows] == ["chess"]


def test_safe_error_alone():
    cleaned = job_store.safe_error("token github_pat_11AKJACEA0yAb12cD3eF4gh5IJ6kl")
    assert "github_pat_" not in cleaned
    assert "[redacted]" in cleaned
    assert "sk-bebas-1" in job_store.safe_error("sk-bebas-1")