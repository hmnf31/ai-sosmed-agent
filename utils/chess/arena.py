"""Arena Kings: template pesan yang tetap, hanya tanggal yang berubah.

Polanya sudah disepakati: struktur, sistem reward, syarat klaim, dan kontak
tidak berubah dari bulan ke bulan. Yang berubah tiap bulan hanya nama bulan dan
tanggal acaranya. Karena itu bot menghitung sendiri kapan acaranya: Rabu
pertama setiap bulan, 23.00 WIB, format 3+0 dengan lama +-120 menit.

Tiga tahap keluaran:

- `pengumuman`: pesan utama, dipakai H-14 dan H-7 sebelum acara.
- `h2_jam`: pengingat dua jam sebelum mulai, memuat link arena.
- `h1_jam`: pengingat satu jam sebelum mulai.

Semua yang bisa berubah ada di sheet Arena (kunci di kolom A, nilai di kolom B):
`Link Klub`, `Link Arena`, `Link Form`, `Jam`, `Format`, `Durasi`, `Kontak 1`,
sampai `Kontak 4`, `Batas Form`, `Standby`, dan `Keterangan`. Nilai yang tidak
ada memakai bawaan; tidak ada satu pun tautan yang dikarang bot.
"""
from datetime import datetime, timedelta, timezone

from utils.chess import spreadsheet

DEFAULT_WAKTU = "23.00 WIB"
DEFAULT_FORMAT = "3+0"
DEFAULT_DURASI = "120 Menit"
DEFAULT_LINK_KLUB = "https://www.chess.com/club/turnamen-tiktok-chess-online-club"
DEFAULT_LINK_FORM = "https://forms.gle/1YCVyZMPwpWKN8ZX7"
DEFAULT_STANDBY = "Standby di Room 1 jam sebelum mulai!"
DEFAULT_BATAS_FORM = "22.30 WIB"
DEFAULT_KONTAK = (
    "1.Bang Wawan @waone0608",
    "2.Bang Arif @@~Shakaruby",
    "3.Bang Sul @~S U L",
    "4. Bang Teddy @Teddy Sapta Prayoga",
)
TAGLINE = "Gens Una Sumus | 🏆"

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

# Syarat klaim hadiah. Urutannya dipakai apa adanya di pesan.
SYARAT_KLAIM = (
    "Setiap calon peserta wajib mengisi formulir",
    "Setiap calon peserta wajib join WA grub Info Turnamen",
    "Setiap calon peserta wajib listing dan sudah terdaftar di form 1 jam sebelum "
    "turnamen dimulai.",
)

# Sistem reward. Nilai uang tidak pernah dihitung atau diubah bot; teks ini
# disalin apa adanya supaya nominal yang dikirim selalu sama dengan ketentuan.
SKENARIO = (
    ("🥇 SKENARIO 1: TCO TEMBUS JUARA 1", (
        "1️⃣ Rp 1.200.000 🔥",
        "2️⃣ Rp 1.100.000",
        "3️⃣ Rp 800.000",
        "4️⃣ Rp 500.000",
        "5️⃣ Rp 450.000",
        "6️⃣ Rp 400.000",
        "7️⃣ Rp 300.000",
        "8️⃣ Rp 250.000",
        "9️⃣ Rp 200.000",
        "🔟 Rp 200.000",
        "🏅 Rank 11 - 20: @ Rp 100.000",
        "🏅 Rank 21 - 30: @ Rp 50.000",
    )),
    ("🥈 SKENARIO 2: TCO TEMBUS JUARA 2", (
        "1️⃣ Rp 1.000.000",
        "2️⃣ Rp 800.000",
        "3️⃣ Rp 500.000",
        "4️⃣ Rp 400.000",
        "5️⃣ Rp 300.000",
        "🏅 Rank 6 - 10: @ Rp 200.000",
        "🏅 Rank 11 - 20: @ Rp 70.000",
        "🏅 Rank 21 - 30: @ Rp 40.000",
    )),
    ("🥉 SKENARIO 3: TCO TEMBUS JUARA 3", (
        "1️⃣ Rp 500.000",
        "2️⃣ Rp 350.000",
        "3️⃣ Rp 250.000",
        "🏅 Rank 4 - 5: @ Rp 150.000",
        "🏅 Rank 6 - 10: @ Rp 75.000",
        "🏅 Rank 11 - 20: @ Rp 50.000",
        "🏅 Rank 21 - 30: @ Rp 25.000",
    )),
    ("🎖️ SKENARIO 4: TCO PERINGKAT 4", (
        "1️⃣ Rp 350.000",
        "2️⃣ Rp 250.000",
        "3️⃣ Rp 150.000",
        "🏅 Rank 4 - 5: @ Rp 100.000",
        "🏅 Rank 6 - 10: @ Rp 50.000",
        "🏅 Rank 11 - 20: @ Rp 25.000",
        "🏅 Rank 21 - 30: @ Rp 15.000",
    )),
    ("🎖️ SKENARIO 5: TCO PERINGKAT 5", (
        "1️⃣ Rp 250.000",
        "2️⃣ Rp 150.000",
        "3️⃣ Rp 100.000",
        "🏅 Rank 4 - 5: @ Rp 75.000",
        "🏅 Rank 6 - 10: @ Rp 40.000",
        "🏅 Rank 11 - 20: @ Rp 15.000",
        "🏅 Rank 21 - 30: @ Rp 10.000",
    )),
)

CATATAN_PENTING = (
    "1. Sportivitas: Akun yang terdeteksi curang atau di-banned otomatis "
    "diskualifikasi (Hadiah Hangus).",
    "2. Streamer: (Opsional) pasang judul \"!arenakings\" saat live streaming.",
    "3. Pencairan: Maksimal 30 hari (Menyesuaikan pencairan dari pihak Chess.com).",
)

CLOSING = "Mari kita fokus \"nguli\" poin dan bawa TCO kembali ke podium tertinggi! Gaspol tanpa ampun! 🚀🔥"

# Tahap yang bisa dipilih pemanggil.
STAGES = ("pengumuman", "h2_jam", "h1_jam")

# Tahap yang paling masuk akal untuk setiap jarak hari sebelum acara.
STAGE_BY_DAYS = {14: "pengumuman", 7: "pengumuman", 2: "h2_jam", 1: "h1_jam"}


def _wib_now():
    return datetime.now(timezone(timedelta(hours=7)))


def _pretty_date(value):
    """Tanggal dalam bahasa Indonesia, contoh: Rabu, 7 Oktober 2026."""
    return f"{HARI[value.weekday()]}, {value.day} {BULAN[value.month - 1]} {value.year}"


def _parse_date(iso_text):
    try:
        return datetime.strptime(str(iso_text), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def first_wednesday(year, month):
    """Rabu pertama pada bulan tertentu.

    Tanggal 1 yang jatuh Rabu dihitung sendiri, jadi tidak perlu kalender
    eksternal untuk menentukan minggu pertama.
    """
    first = datetime(year, month, 1)
    return (first + timedelta(days=(2 - first.weekday()) % 7)).date()


def next_arena_date(when=None):
    """Tanggal Arena Kings berikutnya: Rabu pertama bulan ini atau bulan depan.

    Kalau Rabu pertama bulan ini sudah lewat, mengembalikan Rabu pertama bulan
    berikutnya. Ini membuat perintah bisa dipakai kapan saja tanpa menunggu.
    """
    base = (when or _wib_now()).date()
    this_month = first_wednesday(base.year, base.month)
    if this_month >= base:
        return this_month
    if base.month == 12:
        return first_wednesday(base.year + 1, 1)
    return first_wednesday(base.year, base.month + 1)


def stage_for(days_left):
    """Tahap yang sesuai untuk banyaknya hari menuju acara.

    Hari yang tidak ada di peta mengembalikan None supaya pemanggil tahu
    pengingat tidak jatuh pada hari itu, bukan diam-diam memakai tahap lain.
    """
    try:
        return STAGE_BY_DAYS.get(int(days_left))
    except (TypeError, ValueError):
        return None


def days_until(event, when=None):
    """Berapa hari lagi menuju acara. Nilai negatif berarti acaranya lewat."""
    target = _parse_date(event) if isinstance(event, str) else event
    if target is None:
        return None
    return (target - (when or _wib_now()).date()).days


def _settings():
    """Membaca konfigurasi sheet, menormalkan kunci ke bentuk garis bawah."""
    try:
        raw, _ = spreadsheet.read_settings()
    except ValueError:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}

    settings = {}
    for key, value in raw.items():
        # Header sheet memakai spasi ("Link Klub"), alias di bawah memakai garis
        # bawah, jadi keduanya dinormalkan ke bentuk yang sama.
        normalized = key.replace("_", " ")
        for setting, aliases in spreadsheet.SETTING_ALIASES.items():
            if normalized in aliases:
                settings[setting] = value
                break
    return settings


def get_config(when=None):
    """Konfigurasi Arena Kings untuk acara berikutnya.

    Bawaan dipakai supaya bot tetap bisa menjelaskan acaranya walau sheet Arena
    belum diisi. Tidak ada bawaan untuk link arena dan link form: kalau kosong,
    bot tidak menampilkan URL apa pun.
    """
    settings = _settings()
    event_date = next_arena_date(when)

    kontak = settings.get("kontak_1"), settings.get("kontak_2"), \
        settings.get("kontak_3"), settings.get("kontak_4")
    kontak_terisi = tuple(k for k in kontak if k)

    return {
        "tanggal": event_date.isoformat(),
        "bulan": BULAN[event_date.month - 1],
        "waktu": settings.get("waktu") or DEFAULT_WAKTU,
        "format": settings.get("format") or DEFAULT_FORMAT,
        "durasi": settings.get("durasi") or DEFAULT_DURASI,
        "link_klub": settings.get("link") or DEFAULT_LINK_KLUB,
        "link_arena": settings.get("link_arena") or "",
        "link_form": settings.get("link_form") or DEFAULT_LINK_FORM,
        "standby": settings.get("standby") or DEFAULT_STANDBY,
        "batas_form": settings.get("batas_form") or DEFAULT_BATAS_FORM,
        "kontak": list(kontak_terisi) or list(DEFAULT_KONTAK),
        "keterangan": settings.get("keterangan") or "",
        "source": "spreadsheet" if settings else "default",
    }


def build_arena_package(stage="pengumuman", link=None, when=None):
    """Paket Arena Kings untuk satu tahap.

    Tahap `pengumuman` dipakai H-14 dan H-7. Tahap `h2_jam` dan `h1_jam`
    menjadi pengingat dekat dengan link arena. `link` dari pemanggil menang atas
    link di sheet, jadi perintah manual tetap jalan walau sheet belum diisi.
    """
    if stage not in STAGES:
        stage = "pengumuman"

    config = get_config(when)
    arena_link = link or config["link_arena"]

    if stage == "h2_jam":
        message = reminder_two_hours(config, arena_link)
    elif stage == "h1_jam":
        message = reminder_one_hour(config, arena_link)
    else:
        message = announcement(config)

    package = {
        "available": True,
        "stage": stage,
        "event": config,
        "source": config["source"],
        "wa": message,
        "caption": social_caption(config),
        "poster": poster_lines(config),
    }
    if stage != "pengumuman":
        package["link_arena"] = arena_link
    return package


def _info_block(event):
    """Blok INFO TURNAMEN: tanggal, jam, format, dan link yang tersedia."""
    lines = [
        "♟️ INFO TURNAMEN ♟️",
        f"📅 : {_pretty_date(_parse_date(event['tanggal']))}",
        f"🕛 : {event['waktu']} ({event['standby']})",
        f"⚔️ : {event['format']} ({event['durasi']})",
    ]
    if event["link_klub"]:
        lines.append(f"🔗 : Link Club: {event['link_klub']}")
    return lines


def _form_block(event):
    """Blok pendataan hadiah, hanya tampil kalau ada link form."""
    lines = [
        "📝 WAJIB: PENDATAAN HADIAH (SISTEM OTOMATIS) 📝",
        "",
        "Untuk bulan Mei dan bulan selanjutnya, panitia menerapkan sistem Transfer "
        "Otomatis. Seluruh peserta WAJIB mengisi data pembayaran melalui link di "
        f"bawah ini SEBELUM turnamen dimulai atau sebelum pukul {event['batas_form']}.",
        "",
        "Hal ini dilakukan agar jika kalian masuk Top 30, hadiah bisa langsung "
        "dikirim begitu dana dari Chess.com cair tanpa perlu panitia japri satu "
        "per satu.",
        "",
    ]
    if event["link_form"]:
        lines.extend([f"👉 ISI DATA DI SINI: {event['link_form']}", ""])
    return lines


def _reward_block():
    lines = ["💰 REWARD TCO 💰", ""]
    for judul, nominal in SKENARIO:
        lines.append(judul)
        lines.extend(nominal)
        lines.append("")
    return lines


def _contact_block(event):
    lines = ["Untuk info lanjut bisa hubungi :"]
    lines.extend(event["kontak"])
    lines.append("")
    lines.append(TAGLINE)
    return lines


def announcement(event):
    """Pesan utama, dipakai H-14 dan H-7 sebelum acara."""
    lines = [
        f"PENGUMUMAN RESMI TCO CHESS: {event['bulan'].upper()} ARENA KINGS "
        "& REWARD SYSTEM 📢*",
        "",
        "Halo Rekan-rekan Pejuang TCO Chess! 🔥",
        "",
        f"Bulan ini kita kembali mendapat panggilan tempur di Arena Kings edisi "
        f"{event['bulan']} .Mari kita tunjukkan solidaritas dan kekuatan penuh "
        "TCO Chess di Arena Kings Multiclub! ⚔️♟️",
        "",
    ]
    lines.extend(_info_block(event))

    if event["link_arena"]:
        lines.append(f"📍 : Link Arena: {event['link_arena']}")
    else:
        # Link arena baru muncul dua jam sebelum acara, jadi bot hanya
        # memberi tahu letaknya dan tidak pernah mengarang tautannya.
        lines.append('📍 : Link Arena: Tersedia di halaman club "Event" '
                     "(Muncul 2 jam sebelum acara dimulai)")

    lines.append("")
    lines.extend(_form_block(event))

    lines.append("•  Syarat Claim Hadiah: ")
    for index, syarat in enumerate(SYARAT_KLAIM, start=1):
        lines.append(f"{index}.{syarat}")
    lines.append("")
    lines.extend(_reward_block())

    lines.append("⚠️ CATATAN PENTING:")
    for catatan in CATATAN_PENTING:
        lines.append(f" {catatan}")
    lines.append("")

    if event["keterangan"]:
        lines.extend([event["keterangan"], ""])

    lines.append(CLOSING)
    lines.append("")
    lines.extend(_contact_block(event))
    return "\n".join(lines)


def _bulan_of(config):
    return config.get("bulan") or "Arena Kings"


def _reminder_header(event, jam_label):
    lines = [
        f"🚨 ARENA KINGS {_bulan_of(event).upper()} DIMULAI {jam_label}!",
        "",
        "♟️ Arena Kings TCO",
        "",
        f"📅 : {_pretty_date(_parse_date(event['tanggal']))}",
        f"🕛 : {event['waktu']}",
        f"⚔️ : {event['format']} ({event['durasi']})",
    ]
    return lines


def reminder_two_hours(event, link=None):
    """Pengingat dua jam sebelum mulai."""
    lines = _reminder_header(event, "2 JAM LAGI")
    if link:
        lines.extend(["", "🔗 JOIN ARENA:", link])
    else:
        lines.extend([
            "",
            '🔗 Link arena sudah muncul di halaman club "Event". Cek sekarang!',
        ])
    if event["link_form"]:
        lines.extend([
            "",
            "Belum mengisi data hadiah? isi sekarang sebelum batas waktu:",
            event["link_form"],
        ])
    lines.extend(["", CLOSING, ""])
    lines.extend(_contact_block(event))
    return "\n".join(lines)


def reminder_one_hour(event, link=None):
    """Pengingat satu jam sebelum mulai."""
    lines = _reminder_header(event, "1 JAM LAGI")
    if link:
        lines.extend(["", "🔗 JOIN SEKARANG:", link])
    else:
        lines.extend([
            "",
            '🔗 Link arena sudah muncul di halaman club "Event".',
        ])
    lines.extend([
        "",
        f"Format {event['format']} selama {event['durasi']}. Siapkan boardmu dan "
        "jangan telat masuk room.",
        "",
        CLOSING,
        "",
    ])
    lines.extend(_contact_block(event))
    return "\n".join(lines)


def social_caption(event):
    """Caption sosmed: inti acara tanpa tabel hadiah yang panjang."""
    lines = [
        "♟️ ARENA KINGS TCO",
        "",
        f"Arena Kings edisi {event['bulan']} hadir! 🔥",
        "",
        f"📅 {_pretty_date(_parse_date(event['tanggal']))}",
        f"🕚 {event['waktu']}",
        f"⚔️ {event['format']} ({event['durasi']})",
    ]
    if event["link_klub"]:
        lines.extend(["", "🔗 Link Club:", event["link_klub"]])
    if event["link_form"]:
        lines.extend([
            "",
            "📝 WAJIB isi data hadiah sebelum batas waktu:",
            event["link_form"],
        ])
    lines.extend([
        "",
        "Multiclub, terbuka untuk semua klub. Gaspol! 🚀♟️",
        "",
        "#TCO #ArenaKings #Chess",
    ])
    return "\n".join(lines)


def poster_lines(event):
    """Baris pendek untuk poster 1080x1080."""
    lines = ["ARENA KINGS", "TCO", f"EDISI {_bulan_of(event).upper()}"]
    tanggal = _parse_date(event.get("tanggal"))
    if tanggal:
        lines.append(_pretty_date(tanggal))
    if event.get("waktu"):
        lines.append(event["waktu"])
    if event.get("format"):
        lines.append(f"{event['format']} ({event['durasi']})")
    return [line for line in lines if line]


def upcoming_dates(count=3, when=None):
    """Tanggal Arena Kings beberapa bulan ke depan, untuk sanity check pola."""
    base = (when or _wib_now()).date()
    dates = []
    year, month = base.year, base.month
    for _ in range(count * 2):
        target = first_wednesday(year, month)
        if target >= base:
            dates.append(target.isoformat())
        month += 1
        if month > 12:
            month, year = 1, year + 1
        if len(dates) >= count:
            break
    return dates[:count]