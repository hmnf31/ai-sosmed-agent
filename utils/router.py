"""Router permintaan: mengubah chat bebas menjadi intent yang terstruktur.

Tujuan: bot tidak lagi hanya mencocokkan keyword. Router membaca maksud, lalu
menghasilkan intent berisi akun, task, kategori, topik, format, jumlah, dan
platform. Keyword Akun tetap dipakai sebagai fallback supaya perilaku lama tidak
hilang.
"""
import re

from utils import accounts as accounts_mod

# Task yang understands operands dan tidak butuh riset konten.
OPERATIONAL_TASKS = ("tco_weekly", "league_standing", "arena_schedule", "arena_link")
CONTENT_TASKS = ("content", "research", "history", "plan")

# Kata yang menandai task operasional, dipetakan ke nama task.
TASK_PATTERNS = (
    (re.compile(r"\btco\b", re.I), "tco_weekly"),
    (re.compile(r"\bliga\b|\bklasemen\b|\bstanding\b", re.I), "league_standing"),
    (re.compile(r"\barena\b", re.I), "arena_schedule"),
)

# Perintah eksplisit.
COMMAND_TASKS = {
    "tco": "tco_weekly",
    "liga": "league_standing",
    "arena": "arena_schedule",
    "konten": "content",
    "content": "content",
    "trend": "research",
    "tren": "research",
    "history": "history",
    "riwayat": "history",
    "plan": "plan",
    "jadwal": "plan",
}

# Kata kerja yang menandai permintaan pembuatan konten.
CONTENT_VERBS = ("buatkan", "bikin", "buat", "generate", "create", "tolong", "buatin")

NOISE_WORDS = (
    "konten", "content", "video", "gambar", "foto", "image", "post", "unggahan",
    "tren", "trend", "terkini", "terbaru", "hari ini", "minggu ini", "bulan ini",
    "yang", "tentang", "soal", "dari", "untuk", "dengan", "ide", "ideas", "dan", "atau",
    "tiktok", "ig", "instagram", "reels", "reel", "facebook", "wa", "whatsapp",
    "caption", "script", "poster", "carousel", "png", "mp4", "dong", "saya",
    "tolong", "buatkan", "bikin", "generate", "create",
)

FORMAT_WORDS = {
    "image": ("gambar", "foto", "image", "ig", "instagram", "carousel"),
    "video": ("video", "mp4", "tiktok", "reels", "reel"),
}

PERIOD_WORDS = {
    "current_week": ("minggu ini", "this week", "week ini", "pekan ini"),
    "next_week": ("minggu depan", "next week", "pekan depan"),
    "current_month": ("bulan ini", "this month", "bulan ini"),
}

HISTORY_RE = re.compile(r"^\s*/?(riwayat|history|recent)\b", re.I)
PLAN_RE = re.compile(r"\bplan\s+konten\b|\bkonten\s+mingguan\b|\bplan\s+minggu", re.I)
LEAGUE_RE = re.compile(r"\bliga\s*([a-z])\b", re.I)
NUMBER_RE = re.compile(r"\b(\d{1,2})\b")
URL_RE = re.compile(r"https?://\S+")


def _clean(text):
    return " ".join((text or "").split())


def _normalize(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _detect_format(text):
    low = (text or "").lower()
    for fmt, words in FORMAT_WORDS.items():
        if any(w in low for w in words):
            return fmt
    return None


def _detect_period(text):
    low = (text or "").lower()
    for period, words in PERIOD_WORDS.items():
        if any(w in low for w in words):
            return period
    return None


def _strip_command(text):
    """Memisahkan perintah eksplisit dari argumennya. 'liga A update' -> ('liga', 'A update')."""
    text = _clean(text)
    if not text.startswith("/"):
        return None, text
    parts = text.split(None, 1)
    command = parts[0][1:].split("@")[0].lower()
    return command, (parts[1] if len(parts) > 1 else "")


def _detect_task(original, source, command, account):
    """Menentukan task dari perintah eksplisit, pola operasional, lalu default.

    Perintah eksplisit ('/liga') dicek lebih dulu karena isinya sudah dipisah
    dari argumen. Setelah itu pola operasional di teks penuh, sehingga '/liga A'
    tetap terdeteksi meski kata 'liga' hanya ada di perintahnya.
    """
    if command in COMMAND_TASKS:
        return COMMAND_TASKS[command]

    # 'riwayat'/'history' bisa muncul tanpa garis miring, jadi dicek terpisah.
    if HISTORY_RE.match(original):
        return "history"

    # 'plan konten'/'konten mingguan' berarti permintaan ide mingguan, bukan
    # satu konten. Dicek sebelum kata 'buat' agar tidak tertangkap sebagai content.
    if PLAN_RE.search(original):
        return "plan"

    # Kata kerja 'buat/bikin' selalu berarti produksi konten, walau kata
    # 'liga' atau 'tco' ikut muncul. 'buat pengumuman liga B' adalah konten
    # pengumuman liga, bukan pembacaan klasemen.
    if any(v in source.lower() for v in CONTENT_VERBS):
        return "content"

    for pattern, task in TASK_PATTERNS:
        if pattern.search(original):
            return task

    return "content"


def _extract_topic(text):
    """Membuang kata kerja, noise, dan penanda format; menyisakan topik inti."""
    topic = _clean(text)

    for verb in CONTENT_VERBS:
        topic = re.sub(rf"\b{verb}\b\s*", " ", topic, flags=re.I)

    for word in NOISE_WORDS:
        topic = re.sub(rf"\b{re.escape(word.strip())}\b\s*", " ", topic, flags=re.I)

    topic = re.sub(r"https?://\S+", " ", topic, flags=re.I)
    topic = NUMBER_RE.sub(" ", topic)
    topic = re.sub(r"\s{2,}", " ", topic).strip(" -")
    return topic


def parse(text):
    """Mengubah chat bebas menjadi dict intent.

    Kunci yang selalu ada: account, task, category, topic, format, quantity,
    platform, period, league, url, raw. Nilai bisa None bila tidak terdeteksi.
    """
    original = _clean(text)
    command, args = _strip_command(original)
    source = args if command else original

    # Pencocokan akun memakai teks penuh: '/liga A' tetap harus menemukan chess.
    account, keyword = accounts_mod.match_account(original, fallback=False)
    if account is None:
        # Tidak ada akun yang disebut, jadi pakai akun default.
        account = accounts_mod.default_account()
        keyword = None

    task = _detect_task(original, source, command, account)

    # Jumlah konten: angka di dalam teks, atau default mingguan untuk /plan.
    quantity = 1
    if command == "plan":
        quantity = 7
    else:
        match = NUMBER_RE.search(source)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 10:
                quantity = value

    league = None
    league_match = LEAGUE_RE.search(source) or LEAGUE_RE.search(original)
    if league_match:
        league = league_match.group(1).upper()

    url = URL_RE.search(source) or URL_RE.search(original)
    url = url.group(0) if url else None

    # Topik diambil dari teks mentah. Kata kunci akun ('counter', 'ootd') bisa
    # jadi bagian topik itu sendiri, jadi dibuang hanya bila masih ada sisa kata.
    topic = _extract_topic(source)
    if topic:
        fillers = [k for k in [keyword, account["id"] if account else None] if k]
        for filler in fillers:
            candidate = _clean(re.sub(rf"\b{re.escape(filler)}\b", " ", topic, flags=re.I))
            # Hanya dibuang bila sisa topik masih punya isi berarti (2+ kata),
            # supaya 'counter hayabusa' tidak menjadi 'hayabusa'.
            if len(candidate.split()) >= 2:
                topic = candidate
    if not topic:
        topic = _clean(keyword or "")

    fmt = _detect_format(source)
    if task in ("tco_weekly", "league_standing", "arena_schedule"):
        # Task operasional catur menghasilkan teks + poster, bukan video tren.
        fmt = "image"

    period = _detect_period(source)
    if task == "tco_weekly" and not period:
        period = "current_week"

    platform = []
    low = f" {source.lower()} "
    if "tiktok" in low:
        platform.append("tiktok")
    if "instagram" in low or " ig " in low or "reels" in low or "reel " in low:
        platform.append("instagram")
    platform = platform or None

    return {
        "account": account["id"] if account else None,
        "task": task,
        "category": None,
        "topic": topic or None,
        "format": fmt,
        "quantity": quantity,
        "platform": platform,
        "period": period,
        "league": league,
        "url": url,
        "command": command,
        "keyword": keyword,
        "raw": original,
    }


def is_operational(intent):
    return intent.get("task") in OPERATIONAL_TASKS


def is_content(intent):
    return intent.get("task") in CONTENT_TASKS


def describe(intent):
    """Ringkasan singkat intent untuk log dan pesan konfirmasi."""
    parts = [f"task={intent.get('task')}", f"account={intent.get('account')}"]
    if intent.get("category"):
        parts.append(f"category={intent['category']}")
    if intent.get("topic"):
        parts.append(f"topic={intent['topic']!r}")
    if intent.get("format"):
        parts.append(f"format={intent['format']}")
    if intent.get("quantity", 1) > 1:
        parts.append(f"qty={intent['quantity']}")
    if intent.get("league"):
        parts.append(f"league={intent['league']}")
    if intent.get("period"):
        parts.append(f"period={intent['period']}")
    if intent.get("url"):
        parts.append("url=ada")
    return " ".join(parts)