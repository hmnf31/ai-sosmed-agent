"""Arena Kings: dua tahap karena link resmi baru muncul menjelang acara.

Tahap 1 adalah pengumuman tanpa link. Tahap 2 menyusul begitu link dikirim lewat
"/arena link <url>". Bot tidak pernah membuat link atau jadwal sendiri.
"""
from datetime import datetime, timedelta

from utils.chess import spreadsheet


def _wib_now():
    from datetime import timezone

    return datetime.now(timezone(timedelta(hours=7)))


def _pretty_date(iso_text):
    hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    bulan = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    try:
        parsed = datetime.strptime(iso_text, "%Y-%m-%d")
    except (TypeError, ValueError):
        return iso_text or "-"
    return f"{hari[parsed.weekday()]}, {parsed.day} {bulan[parsed.month - 1]} {parsed.year}"


def build_arena_package(link=None, when=None):
    """Paket Arena Kings.

    Dengan `link`, hasilnya adalah pengumuman T-2 jam. Tanpa link, hasilnya
    pengumuman tahap 1 untuk acara terdekat yang link-nya belum tersedia.
    """
    events, source = spreadsheet.get_arena_schedule(when)

    if isinstance(events, str):
        return _empty(events)
    if not events:
        return _empty("Belum ada jadwal Arena Kings di spreadsheet")

    if link:
        event = _match_link_event(events, link, when)
        if event is None:
            return _empty("Link diberikan tapi tidak cocok dengan jadwal mana pun")
        return {
            "available": True,
            "stage": "t_minus_2jam",
            "event": event,
            "source": source,
            "wa": reminder_message(event, link),
            "caption": reminder_message(event, link),
            "poster": poster_lines(event),
        }

    upcoming = _next_upcoming(events, when)
    if upcoming is None:
        return _empty("Tidak ada agenda Arena Kings yang akan datang")

    return {
        "available": True,
        "stage": "pengumuman",
        "event": upcoming,
        "source": source,
        "wa": announcement_message(upcoming),
        "caption": announcement_message(upcoming),
        "poster": poster_lines(upcoming),
    }


def _empty(reason):
    return {
        "available": False,
        "stage": None,
        "reason": reason,
        "wa": (
            "Jadwal Arena Kings belum tersedia.\n"
            f"Alasan: {reason}\n\n"
            "Setelah jadwal diinput, bot otomatis membuat pengumuman."
        ),
        "caption": "",
        "poster": [],
    }


def _next_upcoming(events, when=None):
    today = (when or _wib_now()).date()
    for event in events:
        if event["status"] != "lewat" and event["tanggal"] >= today.isoformat():
            return event
    return None


def _match_link_event(events, link, when=None):
    """Mencari event yang cocok dengan link, atau event terdekat bila belum ada."""
    today = (when or _wib_now()).date()
    upcoming = [e for e in events if e["tanggal"] >= today.isoformat() and e["status"] != "lewat"]
    for event in events:
        if event.get("link") == link:
            return event
    return upcoming[0] if upcoming else None


def announcement_message(event):
    """Tahap 1 adalah pengumuman tanpa link."""
    lines = [
        "♟️ ARENA KINGS TCO",
        "",
        "Arena Kings kembali hadir!",
        "",
        f"📅 {_pretty_date(event['tanggal'])}",
    ]
    if event.get("waktu"):
        lines.append(f"🕚 {event['waktu']}")
    lines.extend([
        "",
        "Kegiatan terbuka untuk umum.",
        "Mari ramaikan Arena Kings bersama komunitas TCO!",
        "",
        "🔗 Link turnamen akan dibagikan menjelang acara.",
        "",
        "#TCO #ArenaKings #Chess",
    ])
    return "\n".join(lines)


def reminder_message(event, link):
    """Tahap 2: pengingat dengan link join."""
    lines = [
        "🚨 ARENA KINGS DIMULAI MALAM INI!",
        "",
        "♟️ Arena Kings TCO",
        "",
    ]
    if event.get("waktu"):
        lines.append(f"🕚 {event['waktu']}")
    lines.extend([
        "",
        "🔗 JOIN:",
        link,
        "",
        "Siapkan papanmu.",
        "Sampai jumpa di arena! 🔥♟️",
    ])
    return "\n".join(lines)


def poster_lines(event):
    lines = ["ARENA KINGS", "TCO"]
    detail = [_pretty_date(event["tanggal"])]
    if event.get("waktu"):
        detail.append(event["waktu"])
    return lines + detail