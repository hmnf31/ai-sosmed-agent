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

    rows.append([
        {"text": "🕘 Riwayat", "callback_data": f"{HISTORY_PREFIX}{account_id}"},
        {"text": "◀️ Menu utama", "callback_data": BACK_PREFIX},
    ])
    return _keyboard(rows)


def home_text():
    """Teks sambutan dashboard utama."""
    default = accounts_mod.default_account()
    lines = ["🤖 SOCIAL MEDIA ASSISTANT", "", "Pilih akun:"]
    for account in accounts_mod.list_accounts():
        emoji = account.get("emoji", "")
        lines.append(f"{emoji} {account['label']}")
    lines.append("")
    lines.append(f"Default: {default['label'] if default else '-'}")
    lines.append("Ketik /bantu untuk daftar perintah teks.")
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


def task_request(account_id, task, arg):
    """Membangun teks permintaan dari satu penekanan tombol.

    Menu hanya mengubah cara memesan; task router tetap yang memutuskan.
    """
    account = accounts_mod.find_account(account_id)
    resolved_id = account["id"] if account else account_id
    keywords = (account or {}).get("keywords") or []
    keyword = keywords[0] if keywords else None

    if task == "tco_weekly":
        return "tco minggu ini"
    if task == "league_standing":
        return "liga klasemen terbaru"
    if task == "arena_schedule":
        return "arena kings minggu ini"
    if task == "plan":
        return f"buatkan plan konten mingguan {resolved_id}"

    parts = ["buatkan konten"]
    if arg:
        parts.append(arg)
    if keyword and keyword not in arg:
        parts.append(keyword)
    return " ".join(p for p in parts if p)