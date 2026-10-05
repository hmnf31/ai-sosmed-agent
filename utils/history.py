"""Database konten: histori, deduplikasi topik, dan statistik per akun.

Tujuannya satu: setiap konten yang pernah dibuat punya ID dan bisa dicari lagi.
Deduplikasi berhenti opsional supaya modul lain tidak perlu tahu soal database
yang tidak ada.

Berkas default: output/content-history.db
"""
import json
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

DEFAULT_DB = os.path.join("output", "content-history.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS content_history (
    id            TEXT PRIMARY KEY,
    account       TEXT NOT NULL,
    task          TEXT,
    content_type  TEXT,
    category      TEXT,
    topic         TEXT,
    topic_key     TEXT,
    title         TEXT,
    status        TEXT DEFAULT 'generated',
    source_url    TEXT,
    file_path     TEXT,
    caption       TEXT,
    angle         TEXT,
    platform      TEXT,
    request_id    TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_account ON content_history(account, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_topic_key ON content_history(account, topic_key);
CREATE INDEX IF NOT EXISTS idx_history_created ON content_history(created_at DESC);

CREATE TABLE IF NOT EXISTS topic_usage (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    account       TEXT NOT NULL,
    topic_key     TEXT NOT NULL,
    content_id    TEXT,
    used_at       TEXT NOT NULL,
    UNIQUE(account, topic_key)
);

CREATE TABLE IF NOT EXISTS request_log (
    request_id    TEXT PRIMARY KEY,
    raw_text      TEXT,
    account       TEXT,
    task          TEXT,
    status        TEXT,
    duration_ms   INTEGER,
    error         TEXT,
    created_at    TEXT NOT NULL
);
"""

STATUS_FLOW = {
    "generated": ("approved", "published", "archived", "rejected"),
    "approved": ("published", "archived"),
    "published": ("archived",),
    "rejected": ("generated",),
    "archived": (),
}

_LOCK = threading.Lock()


def _wib_now():
    return datetime.now(timezone(timedelta(hours=7)))


def db_path(path=None):
    return path or os.environ.get("CONTENT_DB_PATH") or DEFAULT_DB


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
    """Koneksi yang selalu ditutup, dengan commit otomatis bila tidak ada error."""
    conn = connect(path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(path=None):
    """Membuat tabel bila belum ada. Aman dipanggil berulang."""
    with _LOCK, _session(path) as conn:
        conn.executescript(SCHEMA)
    return db_path(path)


def topic_key(text):
    """Normalisasi topik untuk perbandingan: huruf kecil, tanpa tanda baca."""
    cleaned = re.sub(r"[^a-z0-9\s]+", " ", (text or "").lower())
    words = [w for w in cleaned.split() if w not in STOPWORDS]
    return " ".join(words)


STOPWORDS = {
    "yang", "untuk", "dari", "pada", "dengan", "tentang", "cara", "tips",
    "ide", "ideas", "konten", "content", "video", "gambar", "terbaru",
    "trend", "tren", "hari", "ini", "minggu", "sepanjang",
}


def next_content_id(conn, prefix=None):
    """Membuat ID konten berurutan per tahun, contoh: 2026-014."""
    prefix = prefix or _wib_now().strftime("%Y")
    like = f"{prefix}-%"
    row = conn.execute(
        "SELECT id FROM content_history WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (like,),
    ).fetchone()
    current = 0
    if row:
        tail = row["id"].split("-")[-1]
        if tail.isdigit():
            current = int(tail)
    return f"{prefix}-{current + 1:03d}"


def record_content(
    account,
    topic=None,
    title=None,
    task=None,
    content_type=None,
    category=None,
    status="generated",
    source_url=None,
    file_path=None,
    caption=None,
    angle=None,
    platform=None,
    request_id=None,
    path=None,
):
    """Menyimpan satu konten ke histori. Mengembalikan dict berisi id dan topic_key."""
    if not account:
        raise ValueError("record_content butuh account")

    with _LOCK, _session(path) as conn:
        conn.executescript(SCHEMA)
        content_id = next_content_id(conn)
        key = topic_key(topic or title or "")
        now = _wib_now().isoformat(timespec="seconds")
        conn.execute(
            """
            INSERT INTO content_history
                (id, account, task, content_type, category, topic, topic_key, title,
                 status, source_url, file_path, caption, angle, platform, request_id,
                 created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                content_id, account, task, content_type, category, topic, key, title,
                status, source_url, file_path, caption, angle,
                json.dumps(platform) if platform else None,
                request_id, now, now,
            ),
        )
        # Satu topik per akun hanya boleh dipakai sekali; INSERT OR IGNORE
        # membuat pemakaian kedua menjadi no-op agar histori tetap utuh.
        conn.execute(
            "INSERT OR IGNORE INTO topic_usage (account, topic_key, content_id, used_at) VALUES (?,?,?,?)",
            (account, key, content_id, now),
        )
    return {"id": content_id, "topic_key": key, "created_at": now}


def is_duplicate(account, topic=None, title=None, path=None):
    """True bila topik ini sudah pernah dipakai untuk akun tersebut."""
    key = topic_key(topic or title or "")
    if not key:
        return False
    with _session(path) as conn:
        try:
            row = conn.execute(
                "SELECT 1 FROM topic_usage WHERE account=? AND topic_key=?", (account, key)
            ).fetchone()
        except sqlite3.OperationalError:
            return False
    return row is not None


def duplicate_candidates(account, topic=None, title=None, limit=5, path=None):
    """Riwayat topik yang mirip untuk membantu mencari angle lain.

    Pencocokan memakai awalan kata pertama ('counter hayabusa' cocok dengan
    'counter hiu') lalu diurutkan dari yang paling mirip, sehingga saran
    angle tidak kosong hanya karena perbedaan satu kata.
    """
    key = topic_key(topic or title or "")
    if not key:
        return []
    first_word = key.split()[0]
    if len(first_word) < 3:
        return []
    with _session(path) as conn:
        try:
            rows = conn.execute(
                """
                SELECT id, topic, topic_key, title, created_at, status
                FROM content_history
                WHERE account=? AND topic_key LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (account, f"{first_word}%", limit * 4),
            ).fetchall()
        except sqlite3.OperationalError:
            return []

    # Urutkan dari jumlah awalan kata yang sama, lalu dari yang terbaru.
    candidates = key.split()
    def similarity(row):
        words = (row["topic_key"] or "").split()
        shared = 0
        for a, b in zip(candidates, words):
            if a != b:
                break
            shared += 1
        return (-shared, row["created_at"] or "")

    ordered = sorted((dict(r) for r in rows), key=similarity)
    return ordered[:limit]


def recent(account=None, limit=10, path=None):
    """Konten terbaru, terbaru dulu.

    Diurutkan dengan rowid sebagai penentu akhir supaya konten yang dibuat dalam
    detik yang sama tidak tampil acak.
    """
    with _session(path) as conn:
        try:
            if account:
                rows = conn.execute(
                    "SELECT * FROM content_history WHERE account=? "
                    "ORDER BY created_at DESC, rowid DESC LIMIT ?",
                    (account, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM content_history ORDER BY created_at DESC, rowid DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        except sqlite3.OperationalError:
            return []
    return [dict(r) for r in rows]


def get_content(content_id, path=None):
    with _session(path) as conn:
        row = conn.execute("SELECT * FROM content_history WHERE id=?", (content_id,)).fetchone()
    return dict(row) if row else None


def update_status(content_id, status, path=None):
    """Mengubah status konten dengan validasi transisi."""
    with _LOCK, _session(path) as conn:
        row = conn.execute("SELECT status FROM content_history WHERE id=?", (content_id,)).fetchone()
        if row is None:
            raise ValueError(f"Konten {content_id} tidak ada di histori")
        current = row["status"]
        if status != current and status not in STATUS_FLOW.get(current, ()):
            raise ValueError(f"Status {current} -> {status} tidak diizinkan")
        conn.execute(
            "UPDATE content_history SET status=?, updated_at=? WHERE id=?",
            (status, _wib_now().isoformat(timespec="seconds"), content_id),
        )
    return status


def set_file(content_id, file_path, caption=None, path=None):
    """Menyimpan path media dan caption setelah render selesai."""
    with _LOCK, _session(path) as conn:
        if caption is None:
            conn.execute(
                "UPDATE content_history SET file_path=?, updated_at=? WHERE id=?",
                (file_path, _wib_now().isoformat(timespec="seconds"), content_id),
            )
        else:
            conn.execute(
                "UPDATE content_history SET file_path=?, caption=?, updated_at=? WHERE id=?",
                (file_path, caption, _wib_now().isoformat(timespec="seconds"), content_id),
            )
    return True


def log_request(request_id, raw_text=None, account=None, task=None, status="ok",
                duration_ms=None, error=None, path=None):
    """Mencatat satu percakapan untuk observability."""
    if not request_id:
        return False
    with _LOCK, _session(path) as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            """
            INSERT OR REPLACE INTO request_log
                (request_id, raw_text, account, task, status, duration_ms, error, created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (request_id, raw_text, account, task, status, duration_ms,
             (error or None), _wib_now().isoformat(timespec="seconds")),
        )
    return True


def requests_recent(limit=10, path=None):
    with _session(path) as conn:
        try:
            rows = conn.execute(
                "SELECT * FROM request_log ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    return [dict(r) for r in rows]


def account_stats(days=7, path=None):
    """Jumlah konten per akun dalam N hari terakhir."""
    since = (_wib_now() - timedelta(days=days)).isoformat(timespec="seconds")
    with _session(path) as conn:
        try:
            rows = conn.execute(
                """
                SELECT account, COUNT(*) AS total
                FROM content_history
                WHERE created_at >= ?
                GROUP BY account
                """,
                (since,),
            ).fetchall()
        except sqlite3.OperationalError:
            return {}
    return {r["account"]: r["total"] for r in rows}