"""Cek apakah bot bisa membaca data spreadsheet yang sudah diisi.

Jalankan:
    .venv\\Scripts\\python.exe scripts\\check_sheet_data.py

Script ini hanya membaca, tidak mengubah apa pun. Tujuannya memberi tahu
dulu masalahnya sebelum bot dijalankan: sumber belum diset, sheet kosong,
kolom tidak dikenali, atau baris contoh yang masih tertinggal.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from utils.chess import spreadsheet as sheet_mod


def _wib_now():
    return datetime.now(timezone(timedelta(hours=7)))


def _active_source():
    if os.getenv("SHEET_CREDENTIALS_JSON"):
        return "SHEET_CREDENTIALS_JSON (Google Sheets)"
    if sheet_mod._xlsx_path():
        return f"SHEET_XLSX_PATH -> {sheet_mod._xlsx_path()}"
    if sheet_mod._csv_path():
        return f"SHEET_CSV_PATH -> {sheet_mod._csv_path()}"
    return None


def check_tco():
    print("\n=== TCO ===")
    schedule = sheet_mod.get_tco_schedule()
    if not schedule["found"]:
        print(f"  belum ada jadwal: {schedule.get('reason')}")
        print("  isi sheet TCO dengan tanggal hari ini atau tanggal Rabu terdekat.")
        return False
    print(f"  tanggal : {schedule['tanggal']} ({schedule['tanggal_teks']})")
    print(f"  waktu   : {schedule['waktu'] or '-'}")
    print(f"  format  : {schedule['format'] or '-'}")
    print(f"  lokasi  : {schedule['lokasi'] or '-'}")
    print(f"  link    : {schedule['link'] or '(kosong)'}")
    print(f"  sumber  : {schedule['source']}")
    return True


def check_league():
    print("\n=== LIGA ===")
    rows, source = sheet_mod.get_league_standings()
    if isinstance(rows, str):
        print(f"  gagal dibaca: {rows}")
        return False
    if not rows:
        print(f"  belum ada klasemen (sumber: {source})")
        print("  isi sheet Liga: Liga, Rank, Nama, Main, Menang, Seri, Kalah, Poin.")
        return False
    leagues = []
    for row in rows:
        if row["liga"] and row["liga"] not in leagues:
            leagues.append(row["liga"])
    print(f"  sumber     : {source}")
    print(f"  jumlah baris: {len(rows)}")
    print(f"  liga ada    : {', '.join(leagues)}")
    for row in rows[:5]:
        print(
            f"    {row['liga'] or '-'} | {row['nama']} | poin {row['poin']} "
            f"({row['menang']}-{row['seri']}-{row['kalah']}) dari {row['main']}"
        )
    return True


def check_arena():
    from utils.chess import arena

    print("\n=== ARENA KINGS ===")
    config = arena.get_config()
    print(f"  sumber pengaturan: {config['source']}")
    print("  jadwal tetap: Rabu minggu pertama setiap bulan, 23.00 WIB")
    print("  tiga tanggal ke depan: " + ", ".join(arena.upcoming_dates(3)))
    print(f"  acara berikutnya : {_pretty(config['tanggal'])} {config['waktu']}")
    print(f"  format           : {config['format']} ({config['durasi']})")
    print(f"  standby          : {config['standby']}")
    print(f"  batas form       : {config['batas_form']}")
    print(f"  link klub        : {config['link_klub']}")
    link_arena = config["link_arena"] or '(kosong, bot menulis "Tersedia di halaman club Event")'
    print(f"  link arena       : {link_arena}")
    print(f"  link form        : {config['link_form']}")
    print(f"  kontak           : {len(config['kontak'])} orang")
    for kontak in config["kontak"]:
        print(f"    - {kontak}")
    if config["keterangan"]:
        print(f"  keterangan       : {config['keterangan']}")

    print("  jumlah karakter tiap tahap pengingat:")
    for stage in arena.STAGES:
        package = arena.build_arena_package(stage)
        print(f"    {stage}: {len(package['wa'])} karakter")
    return bool(config["link_klub"])


def check_webtco():
    """Cek sumber klasemen utama, yaitu situs resmi TCO."""
    from utils.chess import webtco

    print("\n=== SUMBER KLASEMEN (WEB TCO) ===")
    summary = webtco.season_summary()
    if not summary.get("available"):
        print(f"  tidak terbaca: {summary.get('reason')}")
        print("  bot akan memakai sheet Liga sebagai cadangan.")
        return False
    print(f"  endpoint       : {webtco.API_LIGA}")
    print(f"  season         : {summary['season']}")
    print(f"  liga           : {', '.join(summary['leagues'])}")
    print(f"  pemain         : {summary['players']}")
    print(f"  match selesai  : {summary['matches_done']} dari {summary['matches_total']}")
    return True


def check_league_site():
    """Tampilkan sampel klasemen langsung dari situs, supaya angka bisa dicek."""
    from utils.chess import webtco

    print("\n=== SAMPL KLASEMEN DARI SITUS ===")
    for league in webtco.LEAGUES:
        rows, err = webtco.standings(league)
        if err:
            print(f"  {league}: {err}")
            continue
        if not rows:
            print(f"  {league}: belum ada pemain")
            continue
        top = rows[0]
        print(f"  {league}: {len(rows)} pemain, leader {top['nama']} "
              f"{top['poin']} poin ({top['menang']}-{top['seri']}-{top['kalah']})")
    return True


def _pretty(iso_text):
    try:
        parsed = datetime.strptime(iso_text, "%Y-%m-%d")
    except (TypeError, ValueError):
        return iso_text or "-"
    hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    bulan = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    return f"{hari[parsed.weekday()]}, {parsed.day} {bulan[parsed.month - 1]} {parsed.year}"


def check_template_rows():
    """Menandai baris contoh yang masih tertinggal.

    Hanya baris di dalam tabel yang diperiksa. Baris kosong mengakhiri tabel,
    jadi catatan petunjuk yang kebetulan memuat kata "contoh" bukan data.
    """
    print("\n=== CEK BARIS CONTOH ===")
    try:
        rows, source = sheet_mod.read_range(sheet_mod.RANGE_TCO)
    except ValueError as e:
        print(f"  tidak bisa dibaca: {e}")
        return
    if source == "tidak_ada":
        return

    leftovers = []
    for row in rows:
        if sheet_mod._is_blank(row):
            break  # tabel selesai, sisanya catatan
        if any("contoh" in str(cell).lower() for cell in row):
            leftovers.append(row)

    if leftovers:
        print(f"  {len(leftovers)} baris masih memuat kata 'contoh'.")
        print("  Hapus atau ganti baris contoh agar tidak terbaca sebagai data asli.")
    else:
        print("  tidak ada baris contoh yang tertinggal.")


def main():
    print("CEK KONEKSI SPREADSHEET KLUB CATUR")
    print(f"waktu pemeriksaan: {_wib_now().strftime('%Y-%m-%d %H:%M')} WIB")

    ok = []
    source = _active_source()
    if not source:
        print("\nSUMBER SPREADSHEET BELUM DISET.")
        print("Isi salah satu di .env:")
        print("  SHEET_XLSX_PATH=club-data.xlsx")
        print("  atau SHEET_CREDENTIALS_JSON={...} (Google Sheets)")
        print("Template tersedia: scripts/make_sheet_template.py")
        print("TCO dan Liga tetap bisa jalan tanpa spreadsheet: Liga dibaca dari")
        print("situs resmi TCO, dan Arena Kings tidak butuh data jadwal.")
        ok.append(True)
    else:
        print(f"sumber aktif: {source}")
        ok.extend([check_tco(), check_league(), check_arena()])
        check_template_rows()

    ok.append(check_webtco())
    check_league_site()

    if all(ok):
        print("\nSemua sumber terbaca. Bot siap dipakai untuk TCO, Liga, dan Arena Kings.")
        return 0
    print("\nAda bagian yang belum terisi. Bot tetap jalan dan akan menjawab")
    print("'belum tersedia' untuk bagian itu, bukan menebak angka.")
    return 0


if __name__ == "__main__":
    sys.exit(main())