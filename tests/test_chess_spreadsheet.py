"""Test spreadsheet catur: parsing, normalisasi, dan kondisi data kosong."""
import csv
import json
from datetime import datetime

import pytest

from utils.chess import spreadsheet


def _write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    return str(path)


def test_not_configured_by_default(monkeypatch):
    monkeypatch.delenv("SHEET_CREDENTIALS_JSON", raising=False)
    monkeypatch.delenv("SHEET_CSV_PATH", raising=False)
    assert not spreadsheet.is_configured()


def test_read_range_without_source_returns_empty(monkeypatch):
    monkeypatch.delenv("SHEET_CREDENTIALS_JSON", raising=False)
    monkeypatch.delenv("SHEET_CSV_PATH", raising=False)
    rows, source = spreadsheet.read_range("TCO!A2:Z50")
    assert rows == []
    assert source == "tidak_ada"


def test_tco_without_data_reports_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("SHEET_CREDENTIALS_JSON", raising=False)
    monkeypatch.setenv("SHEET_CSV_PATH", str(_write_csv(tmp_path / "kosong.csv", [])))
    result = spreadsheet.get_tco_schedule(datetime(2026, 10, 14))
    assert result["found"] is False
    assert result["reason"]


def test_tco_found_from_csv(tmp_path, monkeypatch):
    csv_file = _write_csv(
        tmp_path / "tco.csv",
        [
            ["Tanggal", "Waktu", "Format", "Lokasi", "Link", "Keterangan"],
            ["2026-10-14", "20:00", "Blitz", "Online", "https://chess.com/tco", ""],
        ],
    )
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)
    result = spreadsheet.get_tco_schedule(datetime(2026, 10, 14))
    assert result["found"] is True
    assert result["waktu"] == "20:00"
    assert result["format"] == "Blitz"
    assert result["link"] == "https://chess.com/tco"
    assert result["source"] == "csv"


def test_tco_reads_judul_and_mode(tmp_path, monkeypatch):
    """Judul dan Mode ikut terbaca supaya template pesan mengikuti isi sheet."""
    csv_file = _write_csv(
        tmp_path / "tco.csv",
        [
            ["Judul", "Mode", "Tanggal", "Waktu", "Link"],
            ["TCO Mingguan #12", "Internal Mingguan", "2026-10-14", "20:00",
             "https://chess.com/tco/12"],
        ],
    )
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)
    result = spreadsheet.get_tco_schedule(datetime(2026, 10, 14))
    assert result["judul"] == "TCO Mingguan #12"
    assert result["mode"] == "Internal Mingguan"


def test_tco_missing_judul_and_mode_are_empty(tmp_path, monkeypatch):
    csv_file = _write_csv(
        tmp_path / "tco.csv",
        [["Tanggal", "Waktu"], ["2026-10-14", "20:00"]],
    )
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)
    result = spreadsheet.get_tco_schedule(datetime(2026, 10, 14))
    assert result["judul"] == ""
    assert result["mode"] == ""


@pytest.mark.parametrize("tanggal", ["2026-10-14", "14/10/2026", "14-10-2026", "2026/10/14"])
def test_tco_accepts_common_date_formats(tmp_path, monkeypatch, tanggal):
    csv_file = _write_csv(
        tmp_path / f"tco-{tanggal.replace('/', '-')}.csv",
        [["Tanggal", "Waktu"], [tanggal, "20:00"]],
    )
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)
    assert spreadsheet.get_tco_schedule(datetime(2026, 10, 14))["found"] is True


def test_tco_ignores_other_dates(tmp_path, monkeypatch):
    csv_file = _write_csv(
        tmp_path / "tco.csv", [["Tanggal", "Waktu"], ["2026-11-11", "20:00"]]
    )
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)
    assert spreadsheet.get_tco_schedule(datetime(2026, 10, 14))["found"] is False


def test_tco_broken_credentials_raise_value_error(monkeypatch):
    monkeypatch.setenv("SHEET_CREDENTIALS_JSON", "{rusak")
    monkeypatch.delenv("SHEET_CSV_PATH", raising=False)
    result = spreadsheet.get_tco_schedule(datetime(2026, 10, 14))
    assert result["found"] is False
    assert "JSON" in result["reason"]


def test_league_standings_sorted_and_parsed(tmp_path, monkeypatch):
    csv_file = _write_csv(
        tmp_path / "liga.csv",
        [
            ["Liga", "Rank", "Nama", "Main", "Menang", "Seri", "Kalah", "Poin"],
            ["A", 2, "Player B", 5, 4, 0, 1, 12],
            ["A", 1, "Player A", 5, 4, 1, 0, 13],
            ["B", 1, "Player C", 5, 3, 1, 1, 10],
        ],
    )
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)
    rows, source = spreadsheet.get_league_standings("A")
    assert [r["nama"] for r in rows] == ["Player A", "Player B"]
    assert rows[0]["poin"] == 13
    assert rows[0]["seri"] == 1
    assert source == "csv"


def test_league_without_data_returns_message(tmp_path, monkeypatch):
    monkeypatch.setenv("SHEET_CSV_PATH", str(_write_csv(tmp_path / "liga.csv", [])))
    rows, _ = spreadsheet.get_league_standings()
    assert rows == []


def test_arena_reads_key_value_settings(tmp_path, monkeypatch):
    csv_file = _write_csv(
        tmp_path / "arena.csv",
        [
            ["Link Klub", "https://chess.com/ak"],
            ["Jam", "22.00 WIB"],
            ["Format", "Blitz 5 menit"],
            ["Multiklub", "Ya"],
        ],
    )
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)
    settings, _ = spreadsheet.read_settings()
    # Kunci dinormalkan, nilai disimpan apa adanya supaya "23.00 WIB" tetap rapi.
    assert settings == {
        "link_klub": "https://chess.com/ak",
        "jam": "22.00 WIB",
        "format": "Blitz 5 menit",
        "multiklub": "Ya",
    }


def test_arena_settings_stop_at_blank_row(tmp_path, monkeypatch):
    """Catatan di bawah isi tidak boleh terbaca sebagai pengaturan."""
    csv_file = _write_csv(
        tmp_path / "arena.csv",
        [
            ["Link Klub", "https://chess.com/ak"],
            [],
            ["Keterangan", "ini catatan, bukan pengaturan"],
        ],
    )
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)
    settings, _ = spreadsheet.read_settings()
    assert settings == {"link_klub": "https://chess.com/ak"}


def test_arena_empty_sheet(tmp_path, monkeypatch):
    monkeypatch.setenv("SHEET_CSV_PATH", str(_write_csv(tmp_path / "a.csv", [])))
    settings, _ = spreadsheet.read_settings()
    assert settings == {}


def test_arena_ignores_single_column_sheet(tmp_path, monkeypatch):
    """Satu kolom bukan format pengaturan; tidak ada data yang dikarang."""
    csv_file = _write_csv(tmp_path / "a.csv", [["Link Klub"], ["https://x"]])
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)
    settings, _ = spreadsheet.read_settings()
    assert settings == {}


def test_header_alias_matching():
    assert spreadsheet._field_name("Nama Pemain", "nama") == "nama"
    assert spreadsheet._field_name("Poin", "poin") == "poin"
    assert spreadsheet._field_name("Menang", "menang") == "menang"
    assert spreadsheet._field_name("Kolom Aneh", "nama") is None


def test_single_csv_with_multiple_tables(tmp_path, monkeypatch):
    """Satu CSV boleh memuat beberapa tabel berurutan, dipisahkan baris kosong."""
    csv_file = _write_csv(
        tmp_path / "club.csv",
        [
            ["Link Klub", "https://chess.com/ak"],
            [],
            ["Liga", "Rank", "Nama", "Main", "Menang", "Seri", "Kalah", "Poin"],
            ["A", 1, "Player A", 5, 4, 1, 0, 13],
            ["A", 2, "Player B", 5, 4, 0, 1, 12],
        ],
    )
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)

    standings, _ = spreadsheet.get_league_standings("A")
    assert [r["nama"] for r in standings] == ["Player A", "Player B"]

    settings, _ = spreadsheet.read_settings()
    assert settings == {"link_klub": "https://chess.com/ak"}


def test_tco_found_in_multi_table_csv(tmp_path, monkeypatch):
    csv_file = _write_csv(
        tmp_path / "club.csv",
        [
            ["Liga", "Rank", "Nama", "Poin"],
            ["A", 1, "Player A", 13],
            ["Tanggal", "Waktu", "Link"],
            ["2026-10-14", "20:00", "https://chess.com/x"],
        ],
    )
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)
    assert spreadsheet.get_tco_schedule(datetime(2026, 10, 14))["found"] is True


def test_league_rows_stop_at_next_header(tmp_path, monkeypatch):
    """Baris tabel lain tidak boleh ikut dibaca sebagai klasemen."""
    csv_file = _write_csv(
        tmp_path / "liga.csv",
        [
            ["Liga", "Rank", "Nama", "Poin"],
            ["A", 1, "Player A", 13],
            ["Tanggal", "Waktu", "Link"],
            ["2026-10-14", "20:00", "https://chess.com/x"],
        ],
    )
    monkeypatch.setenv("SHEET_CSV_PATH", csv_file)
    rows, _ = spreadsheet.get_league_standings()
    assert [r["nama"] for r in rows] == ["Player A"]


def test_to_int_handles_text():
    assert spreadsheet._to_int("5 poin") == 5
    assert spreadsheet._to_int("-") is None
    assert spreadsheet._to_int("", 0) == 0
    assert spreadsheet._to_int("abc", 7) == 7