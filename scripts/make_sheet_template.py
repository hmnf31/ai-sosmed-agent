"""Membuat template spreadsheet klub catur dalam format .xlsx.

Jalankan sekali:
    .venv\\Scripts\\python.exe scripts\\make_sheet_template.py

Isi file yang dihasilkan dengan data asli, lalu hubungkan ke bot lewat salah
satu cara:

1) Unggah ke Google Sheets lalu bagikan ke email service account, dan isi
   SHEET_CREDENTIALS_JSON di .env. Cara ini paling praktis karena bisa diedit
   dari HP.
2) Simpan file .xlsx di repo lalu isi SHEET_XLSX_PATH di .env. Tidak perlu
   kredensial apa pun.

Nama sheet dan nama kolom sudah sesuai dengan yang dibaca
utils/chess/spreadsheet.py, jadi tidak perlu menyesuaikan kode.
"""
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.chess import spreadsheet as sheet_mod  # noqa: F401  (dokumentasikontrak)

OUTPUT_NAME = "club-data-template.xlsx"

HEADER_FILL = PatternFill("solid", fgColor="1F3A5F")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
SAMPLE_FILL = PatternFill("solid", fgColor="FFF4CE")
REQUIRED_FILL = PatternFill("solid", fgColor="FDE2E2")
THIN = Side(style="thin", color="C8D0DA")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

TCO_COLUMNS = [
    ("Judul", 30, False),
    ("Mode", 20, False),
    ("Tanggal", 16, True),
    ("Waktu", 14, False),
    ("Format", 14, False),
    ("Lokasi", 22, False),
    ("Link", 46, False),
    ("Keterangan", 34, False),
]

# Sheet Arena berisi konfigurasi dua kolom: kunci di kolom A, nilai di kolom B.
# Tanggal, reward system, syarat klaim, dan kontak tidak perlu diinput: jadwal
# tetap dihitung bot dan sisa teks template sudah permanen di kode.
ARENA_SETTINGS = [
    ("Link Klub", 62),
    ("Link Arena", 46),
    ("Link Form", 46),
    ("Jam", 16),
    ("Format", 12),
    ("Durasi", 14),
    ("Standby", 40),
    ("Batas Form", 14),
    ("Kontak 1", 34),
    ("Kontak 2", 34),
    ("Kontak 3", 34),
    ("Kontak 4", 34),
    ("Keterangan", 40),
]

ARENA_SAMPLES = [
    ["Link Klub", "https://www.chess.com/club/turnamen-tiktok-chess-online-club"],
    ["Link Arena", ""],
    ["Link Form", "https://forms.gle/1YCVyZMPwpWKN8ZX7"],
    ["Jam", "23.00 WIB"],
    ["Format", "3+0"],
    ["Durasi", "120 Menit"],
    ["Standby", "Standby di Room 1 jam sebelum mulai!"],
    ["Batas Form", "22.30 WIB"],
    ["Kontak 1", "1.Bang Wawan @waone0608"],
    ["Kontak 2", "2.Bang Arif @@~Shakaruby"],
    ["Kontak 3", "3.Bang Sul @~S U L"],
    ["Kontak 4", "4. Bang Teddy @Teddy Sapta Prayoga"],
    ["Keterangan", ""],
]

TCO_SAMPLES = [
    ["TCO Mingguan", "Internal Mingguan", "2026-10-07", "20.00 WIB", "Blitz 3+0",
     "Online", "https://www.chess.com/tco", "Turnamen internal mingguan TCO"],
    ["TCO Mingguan", "Internal Mingguan", "2026-10-14", "20.00 WIB", "Blitz 3+0",
     "Online", "", "Link akan diinput H-1"],
]

LEAGUE_COLUMNS = [
    ("Liga", 10, True),
    ("Rank", 8, False),
    ("Nama", 26, True),
    ("Main", 9, False),
    ("Menang", 9, False),
    ("Seri", 8, False),
    ("Kalah", 9, False),
    ("Poin", 9, False),
]

LEAGUE_SAMPLES = [
    ["Liga 1", 1, "Player A", 5, 4, 1, 0, 13],
    ["Liga 1", 2, "Player B", 5, 4, 0, 1, 12],
    ["Liga 1", 3, "Player C", 5, 3, 1, 1, 10],
    ["Liga 2", 1, "Player D", 5, 5, 0, 0, 15],
    ["Liga 2", 2, "Player E", 5, 3, 1, 1, 10],
]


def _style_header(worksheet, columns):
    for index, (title, width, _required) in enumerate(columns, start=1):
        cell = worksheet.cell(row=1, column=index, value=title)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER
        worksheet.column_dimensions[get_column_letter(index)].width = width
    worksheet.row_dimensions[1].height = 24
    worksheet.freeze_panes = "A2"


def _fill_samples(worksheet, columns, samples, start_row=2):
    for row_index, values in enumerate(samples, start=start_row):
        for column_index, value in enumerate(values, start=1):
            cell = worksheet.cell(row=row_index, column=column_index, value=value)
            cell.fill = SAMPLE_FILL
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=(column_index == len(columns)))
    return start_row + len(samples)


def _add_note(worksheet, row, text, bold=False):
    cell = worksheet.cell(row=row, column=1, value=text)
    cell.font = Font(bold=bold, size=10)
    cell.alignment = Alignment(vertical="top")
    return row + 1


def _add_table(worksheet, columns, samples, notes):
    _style_header(worksheet, columns)
    next_row = _fill_samples(worksheet, columns, samples)

    if notes:
        next_row += 1
        next_row = _add_note(worksheet, next_row, notes[0], bold=True)
        for line in notes[1:]:
            next_row = _add_note(worksheet, next_row, line)
    return next_row


def _add_validations(worksheet, columns, row_start, row_end):
    mapping = {title: index for index, (title, _, _) in enumerate(columns, start=1)}
    if "Format" in mapping:
        letter = get_column_letter(mapping["Format"])
        validation = DataValidation(
            type="list",
            formula1='"Blitz,Rapid,Bullet,Classical,Timed,Untimed"',
            allow_blank=True,
        )
        worksheet.add_data_validation(validation)
        validation.add(f"{letter}{row_start}:{letter}{row_end}")
    for title in ("Main", "Menang", "Seri", "Kalah", "Poin", "Rank"):
        if title not in mapping:
            continue
        letter = get_column_letter(mapping[title])
        validation = DataValidation(
            type="whole", operator="between", formula1=0, formula2=99, allow_blank=True
        )
        worksheet.add_data_validation(validation)
        validation.add(f"{letter}{row_start}:{letter}{row_end}")


def _build_tco(workbook):
    worksheet = workbook.create_sheet("TCO")
    notes = [
        "CARA PAKAI SHEET TCO",
        "Diperbarui setiap minggu, biasanya setiap hari Minggu.",
        "Template pesan ikut isi sheet: kolom Judul, Mode, Tanggal, Waktu, "
        "Format, Lokasi, Link, dan Keterangan semua ikut terbaca apa adanya.",
        "Kolom merah wajib diisi: Tanggal. Sisanya boleh kosong.",
        "Judul boleh kosong; bot memakai judul bawaan 'TCO - TIKTOK CHESS ONLINE'.",
        "Mode boleh kosong; bot memakai 'Internal Mingguan'.",
        "Tanggal boleh 2026-10-07, 07/10/2026, atau 07-10-2026.",
        "Waktu ditulis bebas, contoh 20.00 WIB.",
        "Link boleh dikosongkan kalau link resmi belum ada; bot tidak akan mengarang link.",
        "Contoh baris kuning adalah data contoh. Ganti atau hapus setelah mengisi data asli.",
        "Pengingat yang bisa dibuat: H-2, H-1, dan 1 jam sebelum acara.",
        "Perintah bot: 'tco minggu ini', 'tco 1 jam lagi', atau "
        "/menu > Klub Catur > TCO Mingguan.",
    ]
    row = _add_table(worksheet, TCO_COLUMNS, TCO_SAMPLES, notes)
    _add_validations(worksheet, TCO_COLUMNS, 2, 500)
    return worksheet, row


def _build_arena(workbook):
    """Sheet Arena berformat konfigurasi: kunci di kiri, nilai di kanan.

    Tidak dipakai _add_table karena sheet ini bukan daftar baris data. Baris
    kosong memisahkan isi dari catatan, supaya catatan tidak terbaca sebagai
    konfigurasi.
    """
    worksheet = workbook.create_sheet("Arena")
    worksheet.column_dimensions["A"].width = 22
    worksheet.column_dimensions["B"].width = 56

    header = worksheet.cell(row=1, column=1, value="Pengaturan")
    header.fill = HEADER_FILL
    header.font = HEADER_FONT
    header.alignment = Alignment(horizontal="left", vertical="center")
    other = worksheet.cell(row=1, column=2, value="Nilai")
    other.fill = HEADER_FILL
    other.font = HEADER_FONT
    other.alignment = Alignment(horizontal="left", vertical="center")
    worksheet.row_dimensions[1].height = 24

    for row_index, (key, value) in enumerate(ARENA_SAMPLES, start=2):
        key_cell = worksheet.cell(row=row_index, column=1, value=key)
        value_cell = worksheet.cell(row=row_index, column=2, value=value)
        key_cell.fill = SAMPLE_FILL
        if value:
            value_cell.fill = SAMPLE_FILL
        key_cell.font = Font(bold=True)
        for cell in (key_cell, value_cell):
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top")

    notes = [
        "CARA PAKAI SHEET ARENA",
        "Sheet ini berisi pengaturan, bukan daftar acara. Kolom kiri adalah "
        "nama pengaturan, kolom kanan adalah nilainya.",
        "TIDAK PERLU DIISI: tanggal acara, sistem reward, syarat klaim hadiah, "
        "dan penutup. Tanggal dihitung bot sendiri (Rabu minggu pertama tiap "
        "bulan) dan teks template sudah tetap di kode.",
        "Link Klub   : satu link untuk semua bulan. Bot tidak akan membuat link "
        "atau link arena sendiri.",
        "Link Arena  : boleh dikosongkan. Bot akan menulis 'Tersedia di halaman "
        "club Event' sampai link diinput, paling lambat saat pengingat 2 jam.",
        "Link Form   : link pendaftaran data hadiah.",
        "Jam         : waktu mulai, contoh 23.00 WIB.",
        "Format      : contoh 3+0.",
        "Durasi      : contoh 120 Menit.",
        "Batas Form  : batas akhir mengisi data hadiah, contoh 22.30 WIB.",
        "Kontak 1-4  : isi kalau ada perubahan. Kalau kosong, dipakai kontak bawaan.",
        "Pengingat yang bisa dibuat: H-14, H-7, 2 jam, dan 1 jam sebelum acara.",
        "Perintah bot: 'arena kings bulan ini', 'arena 1 jam lagi', atau "
        "/menu > Klub Catur > Pengingat Arena.",
    ]
    row = 2 + len(ARENA_SAMPLES) + 2
    row = _add_note(worksheet, row, notes[0], bold=True)
    for line in notes[1:]:
        row = _add_note(worksheet, row, line)
    return worksheet, row


def _build_league(workbook):
    worksheet = workbook.create_sheet("Liga")
    notes = [
        "CARA PAKAI SHEET LIGA",
        "Sumber utama klasemen adalah situs resmi TCO "
        "(https://web-tco.vercel.app/liga), bukan sheet ini.",
        "Sheet ini hanya dipakai kalau situs tidak bisa dibaca, jadi isi dengan "
        "hasil resmi agar angkanya sama.",
        "Satu baris satu pemain. Kolom merah wajib: Liga dan Nama.",
        "Liga ditulis 'Liga 1' sampai 'Liga 4' sesuai kasta di situs.",
        "Poin boleh diisi manual atau dikira sendiri: 1 poin per menang, 0,5 per seri.",
        "Kalau kolom Rank dikosongkan, bot mengurutkan dari poin.",
        "Contoh baris kuning adalah data contoh. Ganti atau hapus setelah mengisi data asli.",
        "Perintah bot: '/liga Liga 1' atau 'jadwal liga 1'.",
    ]
    row = _add_table(worksheet, LEAGUE_COLUMNS, LEAGUE_SAMPLES, notes)
    _add_validations(worksheet, LEAGUE_COLUMNS, 2, 500)
    return worksheet, row


def _build_readme(workbook, sheets):
    worksheet = workbook.create_sheet("Petunjuk", 0)
    worksheet.column_dimensions["A"].width = 26
    worksheet.column_dimensions["B"].width = 86

    rows = [
        ("TEMPLATE DATA KLUB CATUR TCO", ""),
        ("", ""),
        ("Tujuan", "Sumber angka tunggal untuk bot. Bot tidak mengarang tanggal, poin, atau link."),
        ("", ""),
        ("SHEET TERSEDIA", ""),
    ]
    for name, purpose in sheets:
        rows.append((name, purpose))
    rows += [
        ("", ""),
        ("CARA HUBUNGKAN", ""),
        ("Cara 1 - Google Sheets (disarankan)",
         "Unggah file ini ke Google Drive, ubah ke Google Sheets, lalu bagikan ke email "
         "service account dengan akses Viewer. Tempel JSON service account ke "
         "SHEET_CREDENTIALS_JSON di .env."),
        ("Cara 2 - File lokal",
         "Simpan file ini di repo lalu isi SHEET_XLSX_PATH di .env dengan path lengkap, "
         "contoh SHEET_XLSX_PATH=club-data.xlsx. Tidak perlu kredensial."),
        ("", ""),
        ("SETELAH DIISI", ""),
        ("Cek cepat",
         "Jalankan .venv\\Scripts\\python.exe scripts\\check_sheet_data.py untuk melihat "
         "apakah bot bisa membaca datanya."),
        ("Contoh perintah bot",
         "tco minggu ini | /liga A | arena kings minggu ini | /arena link <url>"),
        ("", ""),
        ("CATATAN PENTING", ""),
        ("Baris contoh", "Baris kuning adalah contoh. Hapus setelah mengisi data asli; "
                         "baris contoh yang tertinggal akan terbaca sebagai data."),
        ("Angka tidak dikarang",
         "Sheet kosong membuat bot menjawab 'belum tersedia', bukan menebak."),
        ("Kolom boleh ditambah",
         "Kolom tambahan diabaikan. Kolom yang tidak dikenali tidak akan merusak pembacaan."),
        ("Nama kolom", "Nama alternatif seperti Player, Win, Points, Jam juga dikenali."),
    ]

    for row_index, (label, value) in enumerate(rows, start=1):
        left = worksheet.cell(row=row_index, column=1, value=label)
        right = worksheet.cell(row=row_index, column=2, value=value)
        right.alignment = Alignment(vertical="top", wrap_text=True)
        if row_index == 1:
            left.font = Font(bold=True, size=14, color="1F3A5F")
        elif value == "" and label:
            left.font = Font(bold=True, size=11, color="1F3A5F")
            left.fill = PatternFill("solid", fgColor="E8EEF5")
        elif label:
            left.font = Font(bold=True)
    return worksheet


def build_template(path=OUTPUT_NAME):
    """Membuat template .xlsx dan mengembalikan path-nya."""
    workbook = Workbook()
    workbook.remove(workbook.active)

    _build_tco(workbook)
    _build_arena(workbook)
    _build_league(workbook)
    _build_readme(workbook, [
        ("TCO", "Jadwal Turnamen internal mingguan. Dipakai perintah "
                "'tco minggu ini'. Diperbarui tiap minggu."),
        ("Liga", "Klasemen per liga. Dipakai perintah '/liga A'. Skor "
                 "diperbarui sekali seminggu."),
        ("Arena", "Pengaturan Arena Kings: link klub, jam, format. Tanggal "
                  "otomatis Rabu minggu pertama tiap bulan, 23.00 WIB, Blitz 3 "
                  "menit, terbuka untuk semua klub."),
    ])

    workbook.active = 0
    workbook.save(path)
    return path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_NAME
    saved = build_template(target)
    print(f"[TEMPLATE] {saved}")
    print("[TEMPLATE] sheet: Petunjuk, TCO, Liga, Arena")
    print("[TEMPLATE] isi data asli, lalu hubungkan lewat SHEET_XLSX_PATH "
          "atau SHEET_CREDENTIALS_JSON.")
