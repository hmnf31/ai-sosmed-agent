"""Internal Mingguan TCO: template mengikuti kolom data, bukan teks tetap.

Berbeda dengan Arena Kings yang templatenya tetap, TCO mingguan berubah-ubah
sesuai isi sheet: judul, mode, tanggal, jam, format, lokasi, link, dan catatan
ikut apa yang diinput panitia. Jadi semua baris pesan dibangun dari baris
spreadsheet, bukan dari kalimat yang ditulis di sini.

Tiga tahap keluaran:

- `pengumuman`: pesan utama, dipakai H-2 sebelum acara.
- `h1_hari`: pengingat satu hari sebelum, tanpa link pendaftaran.
- `h1_jam`: pengingat satu jam sebelum, dengan link pendaftaran.

Bot tidak boleh mengarang tanggal, jam, format, atau link. Kalau baris yang
dibutuhkan tidak ada di sheet, pesannya menyebutkan itu terus terang.
"""
import os
from datetime import datetime, timedelta, timezone

from utils.chess import spreadsheet

# Tahap yang bisa dipilih pemanggil, urut dari yang paling awal.
STAGES = ("pengumuman", "h1_hari", "h1_jam")

# Tahap yang dipakai untuk pengingat pada jarak hari tertentu.
STAGE_BY_DAYS = {2: "pengumuman", 1: "h1_hari"}

DEFAULT_JUDUL = "TCO - TIKTOK CHESS ONLINE"
DEFAULT_MODE = "Internal Mingguan"


def _wib_now():
    return datetime.now(timezone(timedelta(hours=7)))


def _wib_date_text(value):
    """Tanggal dalam bahasa Indonesia, contoh: Rabu, 7 Oktober 2026."""
    hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    bulan = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    return f"{hari[value.weekday()]}, {value.day} {bulan[value.month - 1]} {value.year}"


def _next_wednesday(when=None):
    """Rabu terdekat yang belum lewat."""
    base = when or _wib_now()
    days_ahead = (2 - base.weekday()) % 7
    return base + timedelta(days=days_ahead)


def stage_for(days_left):
    """Tahap yang sesuai untuk banyaknya hari menuju acara, None bila tidak ada."""
    try:
        return STAGE_BY_DAYS.get(int(days_left))
    except (TypeError, ValueError):
        return None


def days_until(event, when=None):
    """Berapa hari lagi menuju acara. Negatif berarti acaranya lewat."""
    target = _parse_date(event) if isinstance(event, str) else event
    if target is None:
        return None
    return (target - (when or _wib_now()).date()).days


def _parse_date(iso_text):
    try:
        return datetime.strptime(str(iso_text), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _pretty_date(iso_text):
    parsed = _parse_date(iso_text)
    return _wib_date_text(parsed) if parsed else (iso_text or "-")


def find_event(when=None):
    """Mencari jadwal TCO terdekat dari tanggal yang diminta."""
    schedule = spreadsheet.get_tco_schedule(when)
    if schedule["found"]:
        return schedule

    # Coba Rabu berikutnya bila tanggal yang dicari belum ada.
    upcoming = _next_wednesday(when)
    return spreadsheet.get_tco_schedule(upcoming)


def build_tco_package(stage="pengumuman", when=None, link=None):
    """Paket TCO: pesan internal, caption sosmed, dan baris poster.

    `link` dari pemanggil menggantikan link di sheet, jadi satu putaran bisa
    dipakai tanpa menyentuh spreadsheet. Mengembalikan `available=False` saat
    data belum ada supaya pemanggil tidak salah menganggap ada isi.
    """
    if stage not in STAGES:
        stage = "pengumuman"

    event = find_event(when)
    if not event["found"]:
        reason = event.get("reason", "Jadwal tidak ditemukan")
        return {
            "available": False,
            "stage": stage,
            "reason": reason,
            "wa": (
                "Jadwal TCO untuk minggu ini belum tersedia.\n"
                f"Alasan: {reason}\n\n"
                "Begitu sudah masuk ke spreadsheet, bot otomatis membuat pengumuman "
                "di sini. Tidak ada tanggal atau link yang dikarang bot."
            ),
            "caption": "",
            "event": event,
        }

    if link:
        event = dict(event, link=link)

    if stage == "h1_hari":
        message = reminder_one_day(event)
    elif stage == "h1_jam":
        message = reminder_one_hour(event)
    else:
        message = wa_message(event)

    return {
        "available": True,
        "stage": stage,
        "event": event,
        "wa": message,
        "caption": social_caption(event),
        "poster": poster_lines(event),
    }


def _heading(event):
    """Judul utama, memakai kolom Judul bila diisi."""
    return event.get("judul") or DEFAULT_JUDUL


def _detail_lines(event, with_link=True):
    """Baris detail yang selalu sama: tanggal, jam, format, lokasi."""
    lines = [f"📅 {_pretty_date(event['tanggal'])}"]
    if event.get("waktu"):
        lines.append(f"🕗 Mulai: {event['waktu']}")
    if event.get("format"):
        lines.append(f"⏱ Format: {event['format']}")
    if event.get("lokasi"):
        lines.append(f"📍 Lokasi: {event['lokasi']}")
    if with_link and event.get("link"):
        lines.extend(["", "🔗 Link Turnamen:", event["link"]])
    return lines


def wa_message(event):
    """Pesan utama untuk grup administrator, dipakai H-2 sebelum acara."""
    mode = event.get("mode") or DEFAULT_MODE
    lines = [
        f"♟️ {_heading(event)}",
        "",
        f"{mode} kembali hadir!",
        "",
    ]
    lines.extend(_detail_lines(event))

    if event.get("keterangan"):
        lines.extend(["", event["keterangan"]])

    lines.extend([
        "",
        "Peserta diharapkan sudah bergabung beberapa menit sebelum turnamen dimulai.",
        "",
        "Selamat bermain dan semoga mendapatkan hasil terbaik! ♟️",
    ])
    return "\n".join(lines)


def reminder_one_day(event):
    """Pengingat satu hari sebelum: jadwal terkunci, link menyusul."""
    tanggal = _pretty_date(event["tanggal"])
    lines = [
        "⏰ TCO BESOK!",
        "",
        f"♟️ {_heading(event)}",
        "",
        f"📅 {tanggal}",
    ]
    if event.get("waktu"):
        lines.append(f"🕗 Mulai: {event['waktu']}")
    if event.get("format"):
        lines.append(f"⏱ Format: {event['format']}")

    lines.extend([
        "",
        "Besok kita bertarung. Pastikan akun sudah siap dan tidak lupa join room.",
        "Link pendaftaran akan dibagikan menjelang acara.",
        "",
        "Sampai jumpa besok! ♟️",
    ])
    return "\n".join(lines)


def reminder_one_hour(event):
    """Pengingat satu jam sebelum, lengkap dengan link pendaftaran."""
    lines = [
        "🚨 TCO DIMULAI 1 JAM LAGI!",
        "",
        f"♟️ {_heading(event)}",
        "",
        f"📅 {_pretty_date(event['tanggal'])}",
    ]
    if event.get("waktu"):
        lines.append(f"🕗 Mulai: {event['waktu']}")

    if event.get("link"):
        lines.extend(["", "🔗 DAFTAR SEKARANG:", event["link"]])
    else:
        lines.extend([
            "",
            "Link pendaftaran belum dibagikan. Hubungi admin Turnamen.",
        ])

    lines.extend([
        "",
        "Belum daftar? sekarang masih sempat. Jangan telat masuk room.",
        "",
        "Gaspol! 🚀♟️",
    ])
    return "\n".join(lines)


def social_caption(event):
    """Caption sosmed yang lebih pendek."""
    mode = event.get("mode") or DEFAULT_MODE
    lines = [
        f"♟️ {_heading(event)}",
        "",
        f"{mode} dibuka untuk semua anggota. 👑",
        "",
        f"📅 {_pretty_date(event['tanggal'])}",
    ]
    if event.get("waktu"):
        lines.append(f"🕗 {event['waktu']}")
    if event.get("format"):
        lines.append(f"⏱ {event['format']}")
    if event.get("link"):
        lines.extend(["", "🔗 Daftar di sini:", event["link"]])
    lines.extend([
        "",
        "Siapkan Mental dan King's. See you at the board! ♟️",
        "",
        "#TCO #Chess #ChessOnline",
    ])
    return "\n".join(lines)


def poster_lines(event):
    """Baris-baris pendek untuk ditampilkan di poster 1080x1080."""
    lines = ["TCO", "TIKTOK", "CHESS ONLINE"]
    detail = [event.get("tanggal") and _pretty_date(event["tanggal"])]
    if event.get("waktu"):
        detail.append(event["waktu"])
    if event.get("format"):
        detail.append(event["format"])
    return [line for line in lines + detail if line]


def render_poster(event, account=None):
    """Membuat poster 1080x1080 bila renderer gambar tersedia."""
    from utils.image_maker import render_content_image

    content = {
        "title": _heading(event),
        "subtitle": _pretty_date(event.get("tanggal")),
        "points": [
            p for p in (event.get("waktu"), event.get("format"), event.get("lokasi")) if p
        ],
        "cta": "Menang Klub? Daftar TCO",
        "caption": social_caption(event),
        "hashtags": ["#TCO", "#Chess"],
    }
    footer = (account or {}).get("label", "TCO")
    path = render_content_image(content, footer=footer)
    return os.path.basename(path)