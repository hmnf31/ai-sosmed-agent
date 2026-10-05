"""Liga: klasemen per liga. Angka dan urutan pemain hanya dari spreadsheet."""
from utils.chess import spreadsheet


def build_league_package(league=None):
    """Paket klasemen: berita, tabel, pesan internal, dan caption.

    Mengembalikan `available=False` plus alasannya bila sheet belum terisi, agar
    bot tidak pernah menampilkan klasemen karangan.
    """
    rows, source = spreadsheet.get_league_standings(league)

    if isinstance(rows, str):
        return _empty(rows)
    if not rows:
        return _empty("Belum ada data klasemen di spreadsheet")

    label = (league or "Liga").upper()
    return {
        "available": True,
        "league": label,
        "rows": rows,
        "source": source,
        "wa": wa_message(label, rows),
        "caption": social_caption(label, rows),
        "table": format_table(label, rows),
        "poster": poster_lines(label, rows),
    }


def _empty(reason):
    return {
        "available": False,
        "league": None,
        "rows": [],
        "reason": reason,
        "wa": (
            "Data klasemen belum tersedia.\n"
            f"Alasan: {reason}\n\n"
            "Setelah sheet Liga terisi, bot otomatis membuat berita klasemen."
        ),
        "caption": "",
        "table": "",
        "poster": [],
    }


def _leader(rows):
    return max(rows, key=lambda r: r["poin"])


def wa_message(league, rows):
    """Berita klasemen untuk pesan internal, bahasa lugas."""
    top = _leader(rows)
    lines = [
        f"♟️ UPDATE KLASEMEN TCO - {league}",
        "",
        f"Persaingan {league} semakin memanas!",
        "",
    ]

    if len(rows) >= 3:
        first, second, third = rows[0], rows[1], rows[2]
        lines.append(
            f"{first['nama']} masih memimpin klasemen dengan "
            f"{first['poin']} poin dari {first['main']} pertandingan."
        )
        lines.append(
            f"Di posisi kedua terdapat {second['nama']} dengan {second['poin']} poin, "
            f"sedangkan {third['nama']} berada di posisi ketiga dengan {third['poin']} poin."
        )
    elif len(rows) == 2:
        second = rows[1]
        lines.append(
            f"{top['nama']} memimpin dengan {top['poin']} poin, sedangkan "
            f"{second['nama']} punya {second['poin']} poin."
        )
    else:
        lines.append(
            f"{top['nama']} memimpin klasemen dengan {top['poin']} poin "
            f"dari {top['main']} pertandingan."
        )

    lines.extend([
        "",
        "Persaingan menuju akhir season masih terbuka.",
        "Setiap poin bisa mengubah posisi.",
        "",
        "Semangat sampai season selesai! ♟️",
    ])
    return "\n".join(lines)


def social_caption(league, rows):
    """Caption sosmed singkat dengan papan tiga besar teratas."""
    top = _leader(rows)
    lines = [
        f"♟️ KLASEMEN {league} - TCO",
        "",
        f"{top['nama']} masih di puncak dengan {top['poin']} poin. ⚔️",
    ]
    if len(rows) >= 2:
        lines.append(f"{rows[1]['nama']} punya {rows[1]['poin']} poin dan masih mengejar.")
    lines.extend([
        "",
        "📊 Tabel lengkap ada di caption ini.",
        "",
        "#TCO #Chess #Liga",
    ])
    return "\n".join(lines)


def format_table(league, rows):
    """Tabel teks yang bisa disalin ke grup WhatsApp."""
    lines = [f"📊 KLASEMEN {league}", ""]
    for index, row in enumerate(rows, start=1):
        position = row["rank"] if row["rank"] is not None else index
        lines.append(
            f"{position}. {row['nama']} — {row['poin']} Poin "
            f"({row['menang']}-{row['seri']}-{row['kalah']})"
        )
    lines.extend(["", "Format: Main-Menang-Seri-Kalah"])
    return "\n".join(lines)


def poster_lines(league, rows):
    """Baris teratas untuk leaderboard di gambar."""
    lines = [f"KLASEMEN {league}"]
    for index, row in enumerate(rows[:4], start=1):
        position = row["rank"] if row["rank"] is not None else index
        lines.append(f"{position}. {row['nama']} {row['poin']}")
    return lines