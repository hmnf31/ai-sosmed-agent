"""Pembaca spreadsheet klub catur (TCO, Liga, Arena Kings).

Bot membaca angka langsung dari spreadsheet, bukan dari ingatan model. Kalau
koneksi gagal atau baris tidak lengkap, fungsi mengembalikan nilai kosong dan
status yang jelas, bukan angka tebakan.

Tiga sumber yang didukung:
- Google Sheets REST API v4 lewat service account JSON.
- CSV lokal untuk dipakai tanpa kredensial apa pun.
- File .xlsx lokal, dibaca tanpa kredensial.
"""
import csv
import io
import json
import os
from datetime import datetime, timedelta, timezone

import requests

API_URL = "https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{range}"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
TIMEOUT = 30

RANGE_TCO = "TCO!A2:Z50"
RANGE_LEAGUE = "Liga!A2:Z500"
# Sheet Arena berisi konfigurasi, bukan daftar acara: dua kolom kunci dan nilai.
RANGE_ARENA_CONFIG = "Arena!A2:B20"

# Nama header yang diterima. Spreadsheet milik pengguna bisa beda kapitalisasi.
HEADER_ALIASES = {
    "liga": ("liga", "league", "divisi", "division"),
    "rank": ("rank", "peringkat", "pos", "position"),
    "nama": ("nama", "name", "player", "pemain", "peserta", "anggota"),
    "main": ("main", "played", "match", "match played", "pertandingan"),
    "menang": ("menang", "win", "wins", "won", "menang"),
    "seri": ("seri", "draw", "draws", "tie", " seri"),
    "kalah": ("kalah", "loss", "losses", "lost"),
    "poin": ("poin", "point", "points", "score", "skor"),
    "tanggal": ("tanggal", "date", "tgl", "hari"),
    "waktu": ("waktu", "time", "jam", "start"),
    "format": ("format", "tempo", "durasi", "duration", "time control"),
    "lokasi": ("lokasi", "location", "venue", "tempat"),
    "link": ("link", "url", "tautan", "turnamen link", "link klub", "club link"),
    "keterangan": ("keterangan", "catatan", "note", "notes", "deskripsi"),
    "multiklub": ("multiklub", "multi klub", "multi-club", "terbuka"),
    "judul": ("judul", "title", "heading", "nama acara", "nama turnamen"),
    "mode": ("mode", "jenis", "tipe", "type", "kategori"),
}

# Nama kunci konfigurasi yang dikenali di sheet Arena.
SETTING_ALIASES = {
    "waktu": ("waktu", "jam", "time", "mulai"),
    "format": ("format", "tempo", "time control", "kontrol waktu"),
    "durasi": ("durasi", "lama", "lamanya"),
    "link": ("link", "link klub", "url", "club link", "tautan"),
    "link_arena": ("link arena", "arena link", "arena", "tautan arena", "link invite"),
    "link_form": (
        "link form", "form", "formulir", "google form", "pendaftaran",
        "link pendaftaran",
    ),
    "link_form": (
        "link form", "form", "formulir", "google form", "pendaftaran",
        "link pendaftaran",
    ),
    "lokasi": ("lokasi", "venue", "tempat", "platform"),
    "standby": ("standby", "catatan standby", "keterangan standby"),
    "batas_form": (
        "batas form", "batas pendaftaran", "deadline", "batas waktu form",
        "batas mengisi",
    ),
    "keterangan": ("keterangan", "catatan", "note"),
    "kontak_1": ("kontak 1", "kontak1", "admin 1", "pic 1"),
    "kontak_2": ("kontak 2", "kontak2", "admin 2", "pic 2"),
    "kontak_3": ("kontak 3", "kontak3", "admin 3", "pic 3"),
    "kontak_4": ("kontak 4", "kontak4", "admin 4", "pic 4"),
    "multiklub": ("multiklub", "multi klub", "terbuka", "open"),
}


def _wib_now():
    return datetime.now(timezone(timedelta(hours=7)))


def is_configured():
    """True bila ada cara membaca spreadsheet: service account, CSV, atau XLSX."""
    return (
        bool(os.getenv("SHEET_CREDENTIALS_JSON"))
        or bool(_csv_path())
        or bool(_xlsx_path())
    )


def _csv_path():
    value = os.getenv("SHEET_CSV_PATH") or ""
    return value if value and os.path.exists(value) else ""


def _xlsx_path():
    value = os.getenv("SHEET_XLSX_PATH") or ""
    return value if value and os.path.exists(value) else ""


def _normalize_header(text):
    return " ".join(str(text or "").strip().lower().split())


def _field_name(header, field):
    """Mencocokkan satu header spreadsheet ke field yang kita kenal."""
    normalized = _normalize_header(header)
    for alias in HEADER_ALIASES.get(field, (field,)):
        if alias == normalized:
            return field
        if normalized.startswith(alias) or normalized.endswith(alias):
            return field
    return None


def _row_to_dict(header, row):
    """Mengubah satu baris menjadi dict memakai header yang dikenali."""
    item = {}
    for index, cell in enumerate(row):
        name = header[index] if index < len(header) else None
        if not name:
            continue
        item[name] = str(cell or "").strip()
    return item


def _to_int(value, default=None):
    """Mengubah sel spreadsheet menjadi angka.

    Sel kosong atau tanda hubung berarti 'tidak ada angka' sehingga nilai
    `default` dipakai, bukan nol, supaya nol tidak appear sebagai data.
    """
    text = str(value or "").strip()
    if not text or text in {"-", "–", "—"}:
        return default
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else default


def _access_token(credentials):
    """Mendapat access token berumur pendek dari service account."""
    key = credentials.get("private_key", "").replace("\\n", "\n")
    email = credentials.get("client_email", "")
    if not key or not email:
        raise ValueError("Kredensial spreadsheet tidak lengkap.")

    now = int(_wib_now().timestamp())
    claim_set = {"iss": email, "scope": SCOPE, "aud": TOKEN_URL, "iat": now, "exp": now + 3600}
    assertion = _jwt(claim_set, key)

    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        raise ValueError(f"Gagal dapat token Google (HTTP {response.status_code}).")
    return response.json().get("access_token")


def _jwt(claims, private_key):
    """Membuat JWT RS256 tanpa dependensi eksternal."""
    import base64

    header = {"alg": "RS256", "typ": "JWT"}

    def segment(data):
        raw = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    body = f"{segment(header)}.{segment(claims)}"
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    key = serialization.load_pem_private_key(private_key.encode(), password=None)
    signature = key.sign(body.encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{body}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def read_range(rng):
    """Membaca satu range spreadsheet sebagai list of list.

    Mengembalikan (rows, sumber). rows kosong berarti tidak ada sumber yang
    terkonfigurasi; pemanggil harus melaporkan kondisi ini secara langsung.
    """
    credentials_json = os.getenv("SHEET_CREDENTIALS_JSON")
    if credentials_json:
        try:
            credentials = json.loads(credentials_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"SHEET_CREDENTIALS_JSON bukan JSON valid: {e}")

        token = _access_token(credentials)
        response = requests.get(
            API_URL.format(
                sheet_id=credentials.get("sheet_id", ""),
                range=rng,
            ),
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
        if response.status_code != 200:
            raise ValueError(f"Gagal baca spreadsheet (HTTP {response.status_code}).")
        return response.json().get("values", []), "google_sheets"

    # Urutan prioritas: kredensial Google, lalu CSV, lalu XLSX. CSV menang
    # supaya mudah dipakai sebagai pengganti sementara saat menguji.
    csv_file = _csv_path()
    if csv_file:
        with open(csv_file, newline="", encoding="utf-8-sig") as handle:
            content = handle.read()
        return list(csv.reader(io.StringIO(content))), "csv"

    xlsx_file = _xlsx_path()
    if xlsx_file:
        return _read_xlsx(xlsx_file, rng)

    return [], "tidak_ada"


def _read_xlsx(path, rng):
    """Membaca satu sheet dari file .xlsx lokal.

    Baris kosong di tengah tabel dilewati supaya kolom yang belum diisi tidak
    memutus pembacaan. Baris pertama yang benar-benar berisi data diperlakukan
    sebagai header oleh pemanggil.
    """
    try:
        from openpyxl import load_workbook
    except ImportError as e:
        raise ValueError(
            "openpyxl belum terpasang. Jalankan pip install openpyxl atau pakai SHEET_CSV_PATH."
        ) from e

    sheet_name = rng.split("!")[0].strip() or None
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet_name and sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
        else:
            # Tanpa nama sheet yang cocok, pakai sheet data pertama yang ada.
            worksheet = None
            for name in workbook.sheetnames:
                if name.strip().lower() in {"petunjuk", "readme", "catatan"}:
                    continue
                worksheet = workbook[name]
                break
            if worksheet is None:
                return [], "xlsx"

        rows = []
        for row in worksheet.iter_rows(values_only=True):
            values = ["" if cell is None else str(cell).strip() for cell in row]
            rows.append(values)
        # Baris kosong di dalam tabel sengaja dipertahankan: baris kosong
        # adalah batas tabel, jadi catatan di bawah data tidak ikut terbaca.
        while rows and not any(rows[-1]):
            rows.pop()
        return rows, "xlsx"
    finally:
        workbook.close()


def _find_header(rows, required):
    """Mencari baris header yang memuat semua field yang dibutuhkan.

    Google Sheets memisahkan tiap tabel lewat tab, tapi satu CSV bisa memuat
    beberapa tabel berurutan. Karena itu baris header dicari, bukan diasumsikan
    selalu di baris pertama.
    """
    needed = set(required)
    for index, row in enumerate(rows):
        mapping = _row_mapping(row)
        if needed.issubset(set(mapping.values())):
            return index, mapping
    return None, None


def _records(rng, required=("nama",)):
    """Membaca range menjadi daftar dict dengan header yang sudah dipetakan."""
    rows, source = read_range(rng)
    if not rows:
        return [], source

    header_index, mapping = _find_header(rows, required)
    if mapping is None:
        return [], source

    records = []
    fields = set(mapping.values())
    for row in rows[header_index + 1:]:
        # Baris kosong mengakhiri tabel. Catatan di bawah tabel tidak dibaca
        # sebagai data, dan tabel berikutnya dimulai setelah baris kosong.
        if _is_blank(row):
            break
        if _starts_new_table(row, fields):
            break
        item = _row_to_dict(mapping, row)
        if any(item.values()):
            records.append(item)
    return records, source


def _row_mapping(row):
    """Memetakan satu baris ke nama field yang dikenali."""
    mapping = {}
    for column, header in enumerate(row):
        for field in HEADER_ALIASES:
            if field not in mapping.values() and _field_name(header, field):
                mapping[column] = field
    return mapping


def _row_values(row):
    """Menyihkan satu baris menjadi daftar teks tanpa sel kosong di ekor."""
    values = [("" if cell is None else str(cell).strip()) for cell in row]
    while values and values[-1] == "":
        values.pop()
    return values


def _is_blank(row):
    """Baris kosong berarti tabel selesai; catatan di bawah tabel diabaikan."""
    return not _row_values(row)


def _starts_new_table(row, current_fields):
    """True bila baris ini header tabel lain, bukan data tabel sekarang.

    Alias yang tidak ada di tabel sekarang menandakan tabel baru, jadi baris
    data berikutnya tidak boleh ikut dibaca sebagai data tabel lama.
    """
    mapping = _row_mapping(row)
    return any(field not in current_fields for field in mapping.values())


def get_tco_schedule(when=None):
    """Jadwal TCO untuk satu tanggal (default hari ini, WIB).

    Mengembalikan dict berisi tanggal, waktu, format, lokasi, link, dan status.
    """
    target = (when or _wib_now()).date()
    try:
        rows, source = read_range(RANGE_TCO)
    except ValueError as e:
        return _tco_empty(str(e))

    if not rows:
        return _tco_empty("Spreadsheet belum dikonfigurasi" if source == "tidak_ada"
                          else "Sheet TCO kosong")

    header_index, mapping = _find_header(rows, ("tanggal",))
    if mapping is None:
        return _tco_empty("Header TCO tidak dikenali")

    fields = set(mapping.values())
    for row in rows[header_index + 1:]:
        if _is_blank(row) or _starts_new_table(row, fields):
            break
        item = _row_to_dict(mapping, row)
        raw_date = item.get("tanggal") or ""
        parsed = _parse_date(raw_date)
        if parsed is None or parsed != target:
            continue
        return {
            "tanggal": parsed.isoformat(),
            "tanggal_teks": raw_date,
            "judul": item.get("judul", ""),
            "mode": item.get("mode", ""),
            "waktu": item.get("waktu", ""),
            "format": item.get("format", ""),
            "lokasi": item.get("lokasi", ""),
            "link": item.get("link", ""),
            "keterangan": item.get("keterangan", ""),
            "source": source,
            "found": True,
        }

    return _tco_empty(f"Belum ada jadwal TCO untuk {target.isoformat()}")


def _tco_empty(reason):
    return {
        "tanggal": None, "tanggal_teks": "", "judul": "", "mode": "",
        "waktu": "", "format": "", "lokasi": "", "link": "", "keterangan": "",
        "source": "tidak_ada", "found": False, "reason": reason,
    }


def _parse_date(text):
    """Menerima beberapa format tanggal yang lazim dipakai di spreadsheet."""
    raw = str(text or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw[:10]).date()
    except ValueError:
        return None


def get_league_standings(league=None):
    """Klasemen liga, opsional disaring satu liga.

    Baris diurutkan rank, lalu poin, supaya aman bila kolom rank kosong.
    """
    try:
        records, source = _records(RANGE_LEAGUE, required=("nama", "poin"))
    except ValueError as e:
        return [], str(e)

    if not records:
        return [], "Sheet Liga belum dikonfigurasi"

    if league:
        wanted = str(league).strip().upper()
        records = [r for r in records if r.get("liga", "").strip().upper() == wanted]

    rows = []
    for record in records:
        rows.append({
            "liga": record.get("liga", ""),
            "rank": _to_int(record.get("rank")),
            "nama": record.get("nama", ""),
            "main": _to_int(record.get("main"), 0),
            "menang": _to_int(record.get("menang"), 0),
            "seri": _to_int(record.get("seri"), 0),
            "kalah": _to_int(record.get("kalah"), 0),
            "poin": _to_int(record.get("poin"), 0),
            "source": source,
        })

    rows.sort(key=lambda r: (r["rank"] if r["rank"] is not None else 99, -r["poin"], r["nama"]))
    return rows, source


def read_settings(rng=RANGE_ARENA_CONFIG):
    """Membaca sheet konfigurasi dua kolom: kunci di kiri, nilai di kanan.

    Bentuk ini dipakai sheet Arena. Baris kosong menghentikan pembacaan supaya
    catatan di bawah isi tidak terbaca sebagai pengaturan. Nama kunci dinormalkan
    supaya "Link Klub", "link", dan "LINK" dibaca sama.
    """
    rows, source = read_range(rng)
    if not rows:
        return {}, source

    settings = {}
    for row in rows:
        values = _row_values(row)
        if not values:
            break  # baris kosong: catatan di bawahnya bukan pengaturan
        if len(values) < 2:
            continue
        key = _normalize_header(values[0]).replace(" ", "_")
        value = values[1].strip()
        if key and value:
            settings[key] = value
    return settings, source