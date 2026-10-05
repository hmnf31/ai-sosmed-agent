"""Turunannya Jadwal TCO mingguan.

Bot tidak boleh mengarang tanggal, jam, atau format. Semua baris berasal dari
spreadsheet; kalau kosong, pesannya jujursays data belum ada. Output dipisah
menjadi dua versi sesuai kebutuhan: pesan WhatsApp internal dan caption sosmed,
plus poster sebagai aset opsional.
"""
import os
from datetime import datetime, timedelta, timezone

from utils.chess import spreadsheet


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


def find_event(when=None):
    """Mencari jadwal TCO terdekat dari tanggal yang diminta."""
    schedule = spreadsheet.get_tco_schedule(when)
    if schedule["found"]:
        return schedule

    # CobaRabu berikutnya bila tanggal yang dicari belum ada.
    upcoming = _next_wednesday(when)
    return spreadsheet.get_tco_schedule(upcoming)


def build_tco_package(when=None):
    """Paket TCO: pesan WA, caption sosmed, dan data untuk poster.

    Mengembalikan dict yang selalu punya kunci, memakai `available=False` saat
    data belum ada supaya pemanggil tidak salah menganggap ada isi.
    """
    event = find_event(when)
    if not event["found"]:
        reason = event.get("reason", "Jadwal tidak ditemukan")
        return {
            "available": False,
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

    return {
        "available": True,
        "event": event,
        "wa": wa_message(event),
        "caption": social_caption(event),
        "poster": poster_lines(event),
    }


def wa_message(event):
    """Versi WhatsApp internal untuk grup administrator klub TCO."""
    lines = [
        "♟️ TCO - TIKTOK CHESS ONLINE",
        "",
        "Turnamen Internal Mingguan TCO kembali hadir!",
        "",
    ]
    tanggal = _pretty_date(event["tanggal"])
    lines.append(f"📅 {tanggal}")
    if event.get("waktu"):
        lines.append(f"🕗 Mulai: {event['waktu']}")
    if event.get("format"):
        lines.append(f"⏱ Format: {event['format']}")
    if event.get("lokasi"):
        lines.append(f"📍 Lokasi: {event['lokasi']}")

    if event.get("link"):
        lines.extend(["", "🔗 Link Turnamen:", event["link"]])

    if event.get("keterangan"):
        lines.extend(["", event["keterangan"]])

    lines.extend([
        "",
        "Peserta diharapkan sudah bergabung beberapa menit sebelum turnamen dimulai.",
        "",
        "Selamat bermain dan semoga mendapatkan hasil terbaik! ♟️",
    ])
    return "\n".join(lines)


def social_caption(event):
    """Caption sosmed yang lebih pendek."""
    lines = [
        "♟️ TCO - TIKTOK CHESS ONLINE",
        "",
        "Turnamen internal mingguan TCO dibuka untuk semua anggota. 👑",
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
        "Siapkan Mental dan King's. See you di board! ♟️",
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


def _pretty_date(iso_text):
    try:
        parsed = datetime.strptime(iso_text, "%Y-%m-%d")
    except (TypeError, ValueError):
        return iso_text or "-"
    return _wib_date_text(parsed)


def render_poster(event, account=None):
    """Membuat poster 1080x1080 bila renderer gambar tersedia."""
    from utils.image_maker import render_content_image

    content = {
        "title": "TCO TIKTOK CHESS ONLINE",
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