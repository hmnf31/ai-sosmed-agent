"""Menu tombol inline Telegram.

Pengguna tidak perlu mengetik panjang-panjang: pilih akun, pilih task, bot
mengeksekusi. Semua aksi tetap dipetakan ke perintah teks biasa, jadi menu ini
hanya pintasan, bukan logika terpisah.
"""
from utils import accounts as accounts_mod

# Menu per akun. Nilai = (label tombol, task router, argumen yang ditambahkan).
ACCOUNT_MENUS = {
    "chess": [
        ("♟️ TCO Mingguan", "tco_weekly", ""),
        ("📊 Liga", "league_standing", ""),
        ("🏟️ Arena Kings", "arena_schedule", ""),
        ("📈 Klasemen Liga", "league_standing", ""),
        ("💡 Konten Catur", "content", "catur"),
        ("🗓️ Plan Mingguan", "plan", ""),
    ],
    "wedding": [
        ("📈 Tren", "content", "tren"),
        ("💡 Ide Konten", "content", "ide"),
        ("🖼️ Carousel", "content", "carousel"),
        ("🎬 Reels", "content", "reels"),
        ("✍️ Caption", "content", "caption"),
    ],
    "mlbb": [
        ("🧩 Patch", "content", "patch terbaru"),
        ("📊 Meta", "content", "meta"),
        ("🗡️ Hero", "content", "hero"),
        ("🛡️ Counter", "content", "counter"),
        ("🏆 MPL", "content", "mpl"),
        ("🎮 Esports", "content", "esports"),
        ("💡 Tips", "content", "tips"),
        ("📈 Tren", "content", "tren"),
    ],
    "fashion": [
        ("📈 Tren", "content", "tren"),
        ("👕 OOTD", "content", "ootd"),
        ("🪡 Styling", "content", "styling"),
        ("💰 Affiliate", "content", "affiliate"),
        ("💡 Ide Konten", "content", "ide"),
    ],
}

BACK_PREFIX = "menu:back"
ACCOUNT_PREFIX = "menu:account:"
TASK_PREFIX = "menu:task:"
HISTORY_PREFIX = "menu:history:"
PREVIEW_PREFIX = "menu:preview:"
STYLE_PREFIX = "menu:style:"

#: Format yang bisa dipilih lewat tombol preview. Nilai ini diteruskan ke
#: perintah `/preview`, jadi renderer tetap punya satu jalur.
PREVIEW_FORMATS = (
    ("🖼️ Kartu", "image"),
    ("🎬 Video", "video"),
    ("📐 Portrait", "portrait"),
)

# Tahap pengingat yang bisa dipilih lewat tombol. Nilainya disisipkan ke teks
# permintaan; router tetap yang memastikan tahapnya dikenali.
STAGE_SUFFIX = {
    "pengumuman": "",
    "h14": " h-14",
    "h7": " h-7",
    "h1_hari": " h-1",
    "h2_jam": " 2 jam lagi",
    "h1_jam": " 1 jam lagi",
    # Bentuk yang diketik manual, bukan hasil penekanan tombol.
    "h-14": " h-14",
    "h-7": " h-7",
    "h-1": " h-1",
    "2 jam": " 2 jam lagi",
    "1 jam": " 1 jam lagi",
}

# Tombol per task yang punya beberapa tahap.
STAGE_BUTTONS = {
    "arena_schedule": ("pengumuman", "h7", "h2_jam", "h1_jam"),
    "tco_weekly": ("pengumuman", "h1_hari", "h1_jam"),
    "league_standing": (None, "jadwal"),
}


def _keyboard(rows):
    return {"inline_keyboard": rows}


def home_markup():
    """Tombol elegir akun, dua per baris."""
    buttons = [
        [
            {"text": f"{a.get('emoji', '')} {a['label']}", "callback_data": f"{ACCOUNT_PREFIX}{a['id']}"}
        ]
        for a in accounts_mod.list_accounts()
    ]
    return _keyboard(buttons)


def account_markup(account_id):
    """Tombol task milik satu akun, dua per baris."""
    items = ACCOUNT_MENUS.get(
        account_id,
        [("💡 Konten", "content", ""), ("📈 Tren", "content", "tren"), ("🗓️ Plan", "plan", "")],
    )
    row = []
    rows = []
    for label, task, arg in items:
        row.append({"text": label, "callback_data": f"{TASK_PREFIX}{account_id}:{task}:{arg}"})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    # Task yang punya beberapa tahap pengingat mendapat submenu tersendiri,
    # supaya tombol utama tetap ringkas.
    if "arena_schedule" in {task for _, task, _ in items}:
        rows.append([{
            "text": "⏱ Pengingat Arena",
            "callback_data": f"{TASK_PREFIX}{account_id}:arena_schedule:{STAGE_MENU_MARKER}",
        }])

    rows.append([
        {"text": "🕘 Riwayat", "callback_data": f"{HISTORY_PREFIX}{account_id}"},
        {"text": "🎨 Preview", "callback_data": f"{PREVIEW_PREFIX}{account_id}"},
    ])
    rows.append([
        {"text": "🧩 Style", "callback_data": f"{STYLE_PREFIX}{account_id}"},
        {"text": "◀️ Menu utama", "callback_data": BACK_PREFIX},
    ])
    return _keyboard(rows)


def preview_markup(account_id):
    """Tombol format untuk preview brand satu akun."""
    format_buttons = [
        {"text": label, "callback_data": f"{PREVIEW_PREFIX}{account_id}:{fmt}"}
        for label, fmt in PREVIEW_FORMATS
    ]
    return _keyboard([
        format_buttons,
        [{"text": "◀️ Kembali", "callback_data": f"{ACCOUNT_PREFIX}{account_id}"}],
    ])


def home_text():
    """Teks sambutan dashboard utama."""
    default = accounts_mod.default_account()
    lines = ["🤖 SOCIAL MEDIA ASSISTANT", "", "Pilih akun:"]
    for account in accounts_mod.list_accounts():
        emoji = account.get("emoji", "")
        lines.append(f"{emoji} {account['label']}")
    lines.append("")
    lines.append(f"Default: {default['label'] if default else '-'}")
    lines.append("Ketik /bantu untuk daftar perintah teks, /preview untuk contoh tampilan.")
    return "\n".join(lines)


def account_text(account_id):
    account = accounts_mod.find_account(account_id)
    if not account:
        return home_text()
    lines = [
        f"{account.get('emoji', '')} {account['label']}".strip(),
        "",
        account.get("niche", ""),
    ]
    modes = ", ".join(account.get("mode", []))
    if modes:
        lines.append(f"Mode: {modes}")
    lines.append("")
    lines.append("Pilih aksi di bawah, atau tulis permintaan bebas.")
    return "\n".join(lines)


STAGE_MENU_MARKER = "__stages__"


def stage_markup(account_id, task):
    """Tombol tahap untuk satu task, atau None kalau tasknya cuma satu tahap.

    Callback memakai argumen sebagai tahap supaya format callback tetap sama
    dengan task biasa: menu:task:<akun>:<task>:<argumen>.
    """
    stages = STAGE_BUTTONS.get(task)
    if not stages or len(stages) == 1:
        return None

    labels = {
        "pengumuman": "📢 Pengumuman",
        "h14": "⏳ H-14",
        "h7": "⏳ H-7",
        "h1_hari": "📆 H-1 Hari",
        "h2_jam": "⏰ 2 Jam",
        "h1_jam": "⏰ 1 Jam",
        "jadwal": "🗓️ Jadwal",
    }
    rows = []
    row = []
    for stage in stages:
        text = labels.get(stage, stage)
        row.append({
            "text": text,
            "callback_data": f"{TASK_PREFIX}{account_id}:{task}:{stage}",
        })
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([
        {"text": "◀️ Kembali", "callback_data": f"{ACCOUNT_PREFIX}{account_id}"},
    ])
    return _keyboard(rows)


def task_request(account_id, task, arg):
    """Membangun teks permintaan dari satu penekanan tombol.

    Menu hanya mengubah cara memesan; task router tetap yang memutuskan.
    `arg` pada task bertahap berisi nama tahap, jadi tombol pengingat punya
    kalimat sendiri.
    """
    account = accounts_mod.find_account(account_id)
    resolved_id = account["id"] if account else account_id
    keywords = (account or {}).get("keywords") or []
    keyword = keywords[0] if keywords else None

    if task == "tco_weekly":
        return "tco minggu ini" + STAGE_SUFFIX.get(arg, "")
    if task == "league_standing":
        if arg == "jadwal":
            return "jadwal liga berikutnya"
        return "liga klasemen terbaru"
    if task == "arena_schedule":
        # Jadwal Arena Kings tetap tiap bulan, jadi kalimatnya bulanan.
        return "arena kings bulan ini" + STAGE_SUFFIX.get(arg, "")
    if task == "plan":
        return f"buatkan plan konten mingguan {resolved_id}"

    parts = ["buatkan konten"]
    if arg:
        parts.append(arg)
    if keyword and keyword not in arg:
        parts.append(keyword)
    return " ".join(p for p in parts if p)