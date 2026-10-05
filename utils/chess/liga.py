"""Liga TCO: klasemen dan jadwal dari situs resmi, dengan cadangan spreadsheet.

Sumber utama adalah endpoint JSON situs https://web-tco.vercel.app/liga, karena
itu sudah dipakai panitia setiap minggu dan isinya satu season penuh: 4 liga,
jadwal per ronde, serta hasil per sesi. Semua angka klasemen dihitung ulang dari
hasil tersebut memakai aturan poin yang sama dengan situs (lihat webtco.py).

Sheet Liga tetap dibaca sebagai cadangan. Ini penting karena ada dua kemungkinan:
situs sedang tidak bisa dibaca, atau panitia ingin mengoreksi angka sementara di
spreadsheet. Urutannya: web-tco dulu, sheet hanya dipakai kalau situs gagal atau
liga yang diminta tidak ada di data situs.
"""
from utils.chess import spreadsheet, webtco

FORMAT = "Menang-Seri-Kalah"


def build_league_package(league=None, with_schedule=False):
    """Paket liga: klasemen, tabel, berita, dan jadwal berikutnya.

    `league` menerima "Liga 1", "liga 1", atau "1". Tanpa argumen, yang
    ditampilkan adalah ringkasan season, bukan gabungan semua liga. Menggabungkan
    empat liga dalam satu tabel akan membuat peringkatnya menyesatkan, karena
    poin antar liga tidak sebanding.

    `with_schedule` menambahkan jadwal match yang belum selesai. Jadwal diambil
    hanya dari situs, karena sheet Liga tidak berisi jadwal.
    """
    if not league:
        return build_overview_package()

    rows, source, notes = _standings(league)

    if not rows:
        return _empty(notes, league)

    label = (webtco.normalize_league(league) or "LIGA").upper()
    package = {
        "available": True,
        "league": label,
        "rows": rows,
        "source": source,
        "notes": notes,
        "wa": wa_message(label, rows, notes),
        "caption": social_caption(label, rows),
        "table": format_table(label, rows),
        "poster": poster_lines(label, rows),
    }

    if with_schedule:
        jadwal, err = webtco.upcoming(league, limit=5)
        package["jadwal"] = jadwal
        package["jadwal_error"] = err
        package["table"] = "\n\n".join(
            block for block in (package["table"], format_schedule(jadwal)) if block
        )
    return package


def _standings(league):
    """Mencoba web-tco dulu, lalu sheet sebagai cadangan.

    Mengembalikan (rows, sumber, catatan). Baris kosong berarti tidak ada
    klasemen yang bisa ditampilkan; `catatan` menjelaskan apa yang terjadi.
    """
    notes = []

    rows, err = webtco.standings(league)
    if rows:
        return rows, "web-tco", notes

    if err and "tidak dikenal" in err:
        # Nama liga yang salah tidak bisa diperbaiki dengan membaca sheet, dan
        # pesan dari situs sudah memuat daftar liga yang tersedia.
        notes.append(err)
        return [], "web-tco", notes

    notes.append(f"Situs TCO tidak terbaca ({err}).")
    rows, reason = spreadsheet.get_league_standings(league)
    if isinstance(rows, str):
        # get_league_standings mengembalikan pesan error di baris pertama.
        notes.append(rows)
        return [], "sheet", notes
    if not rows:
        notes.append(reason if reason else "Sheet Liga kosong")
        return [], "sheet", notes

    notes.append("Angka diambil dari sheet Liga, bukan dari situs TCO.")
    return _normalize_sheet_rows(rows), "sheet", notes


def _normalize_sheet_rows(rows):
    """Menyamakan bentuk baris sheet dengan baris dari situs."""
    out = []
    for row in rows:
        out.append({
            "rank": row.get("rank"),
            "nama": row.get("nama", ""),
            "username": "",
            "liga": row.get("liga", ""),
            "elo": 0,
            "main": row.get("main", 0),
            "menang": row.get("menang", 0),
            "seri": row.get("seri", 0),
            "kalah": row.get("kalah", 0),
            "poin": row.get("poin", 0),
            "wo": 0,
            "disqualified": False,
            "source": row.get("source", "sheet"),
        })
    out.sort(key=lambda r: (r["rank"] if r["rank"] is not None else 99, -r["poin"], r["nama"]))
    for index, row in enumerate(out, start=1):
        if row["rank"] is None:
            row["rank"] = index
    return out


def _empty(notes, league=None):
    lines = ["Data klasemen belum tersedia."]
    for note in notes or []:
        lines.append(f"Alasan: {note}")
    lines.extend([
        "",
        "Sumber klasemen adalah situs resmi TCO (https://web-tco.vercel.app/liga) "
        "dengan cadangan sheet Liga. Setelah salah satunya ada, bot otomatis "
        "menampilkan klasemen di sini.",
    ])
    return {
        "available": False,
        "league": None,
        "rows": [],
        "jadwal": [],
        "reason": "; ".join(notes or ["data kosong"]),
        "notes": notes,
        "wa": "\n".join(lines),
        "caption": "",
        "table": "",
        "poster": [],
    }


def _leader(rows):
    """Pemimpin klasemen: rank terkecil, atau poin tertinggi bila rank kosong."""
    return min(
        rows,
        key=lambda r: (
            r["rank"] if r["rank"] is not None else 99,
            -r["poin"],
            r["nama"].lower(),
        ),
    )


def _record(row):
    return f"{row['menang']}-{row['seri']}-{row['kalah']}"


def _flag(row):
    """Penanda tambahan: walkover dan diskualifikasi."""
    if row.get("disqualified"):
        return " ⛔ DISKUALIFIKASI"
    if row.get("wo"):
        return f" (WO {row['wo']})"
    return ""


def wa_message(league, rows, notes=None):
    """Berita klasemen untuk pesan internal, bahasa lugas."""
    top = _leader(rows)
    lines = [f"♟️ UPDATE KLASEMEN TCO - {league}", ""]

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
        f"Catatan: format {FORMAT}, poin sesuai hasil di Chess.com.",
        "Persaingan masih terbuka. Setiap poin bisa mengubah posisi.",
        "",
        "Semangat sampai season selesai! ♟️",
    ])

    for note in notes or []:
        lines.extend(["", f"ℹ️ {note}"])

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
            f"{position}. {row['nama']}{_flag(row)} — {row['poin']} poin "
            f"({_record(row)})"
        )
    lines.extend(["", f"Format: {FORMAT}"])
    return "\n".join(lines)


def format_schedule(jadwal):
    """Daftar match berikutnya, dipakai bersama tabel klasemen."""
    if not jadwal:
        return ""
    lines = ["🗓 JADWAL BERIKUTNYA", ""]
    for row in jadwal:
        tanggal = row["tanggal"] or "-"
        waktu = f" {row['waktu']}" if row.get("waktu") else ""
        ronde = f" (ronde {row['round']})" if row.get("round") else ""
        lines.append(f"• {tanggal}{waktu}{ronde}: {row['nama']} vs {row['lawan']}")
    return "\n".join(lines)


def poster_lines(league, rows):
    """Baris teratas untuk leaderboard di gambar."""
    lines = [f"KLASEMEN {league}"]
    for index, row in enumerate(rows[:4], start=1):
        position = row["rank"] if row["rank"] is not None else index
        lines.append(f"{position}. {row['nama']} {row['poin']}")
    return lines


def build_overview_package():
    """Ringkasan season: berapa liga, berapa pemain, dan progres match."""
    summary = webtco.season_summary()
    if not summary.get("available"):
        return _empty([summary.get("reason", "data tidak terbaca")])

    lines = [
        "♟️ LIGA TCO - RINGKASAN SEASON",
        "",
        f"Season {summary['season']} berjalan dengan {len(summary['leagues'])} liga: "
        f"{', '.join(summary['leagues'])}.",
        "",
        f"👥 Pemain terdaftar: {summary['players']}",
        f"🎯 Match selesai: {summary['matches_done']} dari {summary['matches_total']}",
        "",
        "Minta klasemen satu liga, contoh: /liga Liga 1",
    ]
    return {
        "available": True,
        "league": "RINGKASAN",
        "rows": [],
        "source": summary["source"],
        "notes": [],
        "wa": "\n".join(lines),
        "caption": "",
        "table": "",
        "poster": ["LIGA TCO", f"SEASON {summary['season']}"]
        + [f"{len(summary['leagues'])} liga", f"{summary['players']} pemain"],
    }
