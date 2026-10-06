"""Penyimpan status job produksi konten (Phase 4 Content Planner).

Setiap permintaan dari Telegram menjadi satu job yang berjalan melewati
status dari `received` sampai `delivered`. Status memakai daftar dari master
plan (bagian 6) dan setiap perpindahan dicatat sebagai event ber-timestamp
supaya nanti bisa dilihat di /status maupun `/history`.

Berkas default: output/jobs.db. API mengikuti gaya `utils/history.py`:
fungsi menerima `path` opsional dan selalu menulis timestamp WIB.
"""
import json
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

DEFAULT_DB = os.path.join("output", "jobs.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id         TEXT PRIMARY KEY,
    account        TEXT,
    content_type   TEXT,
    input          TEXT,
    request_id     TEXT,
    status         TEXT NOT NULL,
    progress       TEXT,
    plan           TEXT,
    timeline       TEXT,
    error          TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_account ON jobs(account, created_at DESC);

CREATE TABLE IF NOT EXISTS job_events (
    event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id     TEXT NOT NULL,
    stage      TEXT,
    status     TEXT NOT NULL,
    message    TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_job ON job_events(job_id, event_id);
"""

#: Status yang sah menurut master plan (bagian 6), transisi perpindahan status.
STATUS_FLOW = {
    "received": ("queued", "failed", "cancelled"),
    "queued": ("researching", "planning", "failed", "cancelled"),
    "researching": ("planning", "failed", "cancelled"),
    "planning": ("generating_assets", "failed", "cancelled"),
    "generating_assets": ("generating_audio", "building_timeline", "failed", "cancelled"),
    "generating_audio": ("building_timeline", "failed", "cancelled"),
    "building_timeline": ("rendering_preview", "failed", "cancelled"),
    "rendering_preview": ("qa_preview", "failed", "cancelled"),
    "qa_preview": ("awaiting_approval", "failed", "cancelled"),
    "awaiting_approval": ("rendering_final", "planning", "failed", "cancelled"),
    "rendering_final": ("qa_final", "failed", "cancelled"),
    "qa_final": ("delivered", "failed", "cancelled"),
    "delivered": (),
    "failed": (),
    "cancelled": (),
}

_LOCK = threading.Lock()

#: Pola yang menyerupai rahasia agar tidak pernah tertulis bulat ke database.
_SECRET_PATTERNS = (
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"gho_[A-Za-z0-9_]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9\-_]{16,}"),
    re.compile(r"\bAIza[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\bAQ\.[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]+", re.I),
    re.compile(r"\b[0-9]+:[A-Za-z0-9_\-]{20,}"),
)


def _wib_now():
    return datetime.now(timezone(timedelta(hours=7)))


def db_path(path=None):
    return path or os.environ.get("JOBS_DB_PATH") or DEFAULT_DB


def connect(path=None):
    """Membuka koneksi siap pakai. Penutupan lewat context manager `_session`."""
    target = db_path(path)
    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(target, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def _session(path=None):
    conn = connect(path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(path=None):
    with _LOCK, _session(path) as conn:
        conn.executescript(SCHEMA)
    return db_path(path)


def safe_error(text):
    """Merapikan pesan error agar tidak memuat rahasia seperti token/kunci."""
    cleaned = str(text or "")
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[redacted]", cleaned)
    return cleaned[:2000]


def _next_job_id(conn):
    row = conn.execute(
        "SELECT job_id FROM jobs ORDER BY job_id DESC LIMIT 1"
    ).fetchone()
    current = 0
    if row:
        tail = str(row["job_id"]).split("_")[-1]
        if tail.isdigit():
            current = int(tail)
    return f"job_{current + 1:04d}"


def create_job(account, input, content_type=None, request_id=None, path=None):
    """Membuat job baru dengan status awal `received`. Mengembalikan dict job."""
    if not account:
        raise ValueError("create_job butuh account")
    now = _wib_now().isoformat(timespec="seconds")
    with _LOCK, _session(path) as conn:
        conn.executescript(SCHEMA)
        job_id = _next_job_id(conn)
        conn.execute(
            """
            INSERT INTO jobs
                (job_id, account, content_type, input, request_id, status,
                 created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (job_id, account, content_type, input, request_id, "received", now, now),
        )
        conn.execute(
            "INSERT INTO job_events (job_id, stage, status, message, created_at) "
            "VALUES (?,?,?,?,?)",
            (job_id, None, "received", "job diterima", now),
        )
    return get_job(job_id, path=path)


def _row_to_job(row):
    job = dict(row)
    for key in ("plan", "timeline"):
        if job.get(key):
            try:
                job[key] = json.loads(job[key])
            except (TypeError, ValueError):
                job[key] = None
    return job


def get_job(job_id, path=None):
    with _session(path) as conn:
        row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    return _row_to_job(row) if row else None


def update_status(job_id, status, message=None, path=None):
    """Perpindahan status dengan validasi transisi + catatan event."""
    if status not in STATUS_FLOW:
        raise ValueError(f"Status tidak dikenal: {status}")
    now = _wib_now().isoformat(timespec="seconds")
    with _LOCK, _session(path) as conn:
        row = conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise ValueError(f"Job {job_id} tidak ada")
        current = row["status"]
        if status != current and status not in STATUS_FLOW[current]:
            raise ValueError(f"Status {current} -> {status} tidak diizinkan")
        if status == "failed":
            conn.execute(
                "UPDATE jobs SET status=?, error=?, updated_at=? WHERE job_id=?",
                (status, safe_error(message) if message else None, now, job_id),
            )
        else:
            conn.execute(
                "UPDATE jobs SET status=?, updated_at=? WHERE job_id=?",
                (status, now, job_id),
            )
        conn.execute(
            "INSERT INTO job_events (job_id, stage, status, message, created_at) "
            "VALUES (?,?,?,?,?)",
            (job_id, status, status, safe_error(message) if message else None, now),
        )
    return status


def attach_plan(job_id, plan, path=None):
    """Menyimpan content plan (dict) dan menyamakan account/content_type."""
    if not isinstance(plan, dict):
        raise ValueError("attach_plan butuh dict content plan")
    now = _wib_now().isoformat(timespec="seconds")
    with _LOCK, _session(path) as conn:
        row = conn.execute(
            "SELECT account FROM jobs WHERE job_id=?", (job_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Job {job_id} tidak ada")
        conn.execute(
            "UPDATE jobs SET plan=?, account=?, content_type=?, updated_at=? WHERE job_id=?",
            (
                json.dumps(plan, ensure_ascii=False),
                plan.get("account") or row["account"],
                plan.get("content_type"),
                now,
                job_id,
            ),
        )
        conn.execute(
            "INSERT INTO job_events (job_id, stage, status, message, created_at) "
            "VALUES (?,?,?,?,?)",
            (job_id, "planning", "planning", "plan valid tersimpan", now),
        )
    return True


def set_progress(job_id, progress, path=None):
    with _session(path) as conn:
        conn.execute(
            "UPDATE jobs SET progress=?, updated_at=? WHERE job_id=?",
            (progress, _wib_now().isoformat(timespec="seconds"), job_id),
        )
    return True


def mark_failed(job_id, error, path=None):
    """Menandai job gagal dengan error yang sudah dibersihkan dari rahasia."""
    return update_status(job_id, "failed", message=safe_error(error), path=path)


def cancel_job(job_id, path=None):
    return update_status(job_id, "cancelled", message="dibatalkan pengguna", path=path)


def events(job_id, limit=50, path=None):
    with _session(path) as conn:
        rows = conn.execute(
            "SELECT * FROM job_events WHERE job_id=? "
            "ORDER BY event_id DESC LIMIT ?",
            (job_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def list_jobs(limit=10, account=None, path=None):
    with _session(path) as conn:
        try:
            if account:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE account=? ORDER BY created_at DESC LIMIT ?",
                    (account, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
        except sqlite3.OperationalError:
            return []
    return [_row_to_job(r) for r in rows]


def stats(account=None, path=None):
    """Jumlah job per status, opsional dibatasi satu akun."""
    with _session(path) as conn:
        try:
            if account:
                rows = conn.execute(
                    "SELECT status, COUNT(*) AS total FROM jobs "
                    "WHERE account=? GROUP BY status",
                    (account,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT status, COUNT(*) AS total FROM jobs GROUP BY status"
                ).fetchall()
        except sqlite3.OperationalError:
            return {}
    result = {r["status"]: r["total"] for r in rows}
    for status in STATUS_FLOW:
        result.setdefault(status, 0)
    return result