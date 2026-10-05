"""Test modul operasional klub catur: TCO, Liga, Arena Kings.

Semua diuji tanpa spreadsheet nyata: sumber dipalsukan supaya angka yang
dipakai adalah angka tetap yang bisa diperiksa.
"""
from datetime import datetime

import pytest

from utils.chess import arena, liga, tco


def _event(tanggal="2026-10-14", link="https://chess.com/tco", waktu="20:00",
           fmt="Blitz", lokasi="Online"):
    return {
        "tanggal": tanggal, "tanggal_teks": tanggal, "waktu": waktu, "format": fmt,
        "lokasi": lokasi, "link": link, "keterangan": "", "source": "csv", "found": True,
    }


# --- TCO -------------------------------------------------------------------

def test_tco_package_when_data_available(monkeypatch):
    monkeypatch.setattr(tco.spreadsheet, "get_tco_schedule", lambda when=None: _event())
    package = tco.build_tco_package()
    assert package["available"] is True
    assert "TCO" in package["wa"]
    assert "20:00" in package["wa"]
    assert "Blitz" in package["wa"]
    assert package["wa"].count("https://chess.com/tco") == 1


def test_tco_wa_mentions_join_early(monkeypatch):
    monkeypatch.setattr(tco.spreadsheet, "get_tco_schedule", lambda when=None: _event())
    assert "bergabung" in tco.build_tco_package()["wa"]


def test_tco_caption_has_hashtags(monkeypatch):
    monkeypatch.setattr(tco.spreadsheet, "get_tco_schedule", lambda when=None: _event())
    caption = tco.build_tco_package()["caption"]
    assert "#TCO" in caption and "#ChessOnline" in caption


def test_tco_link_is_plain_text_not_markdown(monkeypatch):
    monkeypatch.setattr(tco.spreadsheet, "get_tco_schedule", lambda when=None: _event())
    wa = tco.build_tco_package()["wa"]
    assert "](" not in wa
    assert "https://chess.com/tco" in wa


def test_tco_without_data_is_honest(monkeypatch):
    empty = {"found": False, "reason": "Belum ada jadwal", "tanggal": None, "waktu": "",
             "format": "", "lokasi": "", "link": "", "keterangan": ""}
    monkeypatch.setattr(tco.spreadsheet, "get_tco_schedule", lambda when=None: empty)
    package = tco.build_tco_package()
    assert package["available"] is False
    assert "Belum ada jadwal" in package["wa"]
    assert package["caption"] == ""


def test_tco_date_text_in_indonesian(monkeypatch):
    monkeypatch.setattr(tco.spreadsheet, "get_tco_schedule", lambda when=None: _event())
    wa = tco.build_tco_package()["wa"]
    assert "Rabu, 14 Oktober 2026" in wa


def test_tco_tries_next_wednesday_when_missing(monkeypatch):
    seen = []

    def fake(when=None):
        seen.append(when)
        return {**_event(), "found": False, "reason": "kosong"}

    monkeypatch.setattr(tco.spreadsheet, "get_tco_schedule", fake)
    tco.build_tco_package(datetime(2026, 10, 5))
    assert len(seen) == 2
    assert seen[1].weekday() == 2  # Rabu


# --- Liga ------------------------------------------------------------------

@pytest.fixture
def standings():
    return [
        {"liga": "A", "rank": 1, "nama": "Player A", "main": 5, "menang": 4,
         "seri": 1, "kalah": 0, "poin": 13, "source": "csv"},
        {"liga": "A", "rank": 2, "nama": "Player B", "main": 5, "menang": 4,
         "seri": 0, "kalah": 1, "poin": 12, "source": "csv"},
        {"liga": "A", "rank": 3, "nama": "Player C", "main": 5, "menang": 3,
         "seri": 1, "kalah": 1, "poin": 10, "source": "csv"},
    ]


def test_league_package_available(monkeypatch, standings):
    monkeypatch.setattr(liga.spreadsheet, "get_league_standings", lambda l=None: (standings, "csv"))
    package = liga.build_league_package("A")
    assert package["available"] is True
    assert "Player A" in package["wa"]
    assert "13 poin" in package["wa"]


def test_league_table_lists_all(monkeypatch, standings):
    monkeypatch.setattr(liga.spreadsheet, "get_league_standings", lambda l=None: (standings, "csv"))
    table = liga.build_league_package("A")["table"]
    for name in ("Player A", "Player B", "Player C"):
        assert name in table
    assert "13 Poin" in table


def test_league_without_data(monkeypatch):
    monkeypatch.setattr(liga.spreadsheet, "get_league_standings", lambda l=None: ([], "csv"))
    package = liga.build_league_package("A")
    assert package["available"] is False
    assert "Belum ada data" in package["wa"]
    assert package["table"] == ""


def test_league_error_message_from_spreadsheet(monkeypatch):
    monkeypatch.setattr(liga.spreadsheet, "get_league_standings", lambda l=None: ("Sheet rusak", "error"))
    package = liga.build_league_package("A")
    assert package["available"] is False
    assert "Sheet rusak" in package["wa"]


def test_league_single_player_still_works(monkeypatch):
    one = [{"liga": "A", "rank": 1, "nama": "Solo", "main": 3, "menang": 2,
            "seri": 0, "kalah": 1, "poin": 6, "source": "csv"}]
    monkeypatch.setattr(liga.spreadsheet, "get_league_standings", lambda l=None: (one, "csv"))
    package = liga.build_league_package("A")
    assert "Solo" in package["wa"]


def test_league_two_players(monkeypatch):
    two = [
        {"liga": "A", "rank": 1, "nama": "Satu", "main": 3, "menang": 3,
         "seri": 0, "kalah": 0, "poin": 9, "source": "csv"},
        {"liga": "A", "rank": 2, "nama": "Dua", "main": 3, "menang": 1,
         "seri": 0, "kalah": 2, "poin": 3, "source": "csv"},
    ]
    monkeypatch.setattr(liga.spreadsheet, "get_league_standings", lambda l=None: (two, "csv"))
    package = liga.build_league_package("A")
    assert "Dua" in package["wa"]
    assert package["poster"]


# --- Arena Kings ------------------------------------------------------------

def _arena_events():
    return [
        {"tanggal": "2026-10-07", "waktu": "23:00", "format": "Rapid", "lokasi": "Online",
         "link": "", "keterangan": "", "status": "menunggu_link", "source": "csv"},
        {"tanggal": "2026-11-04", "waktu": "23:00", "format": "Rapid", "lokasi": "Online",
         "link": "https://chess.com/ak", "keterangan": "", "status": "link_tersedia",
         "source": "csv"},
    ]


def test_arena_stage_one_has_no_link(monkeypatch):
    monkeypatch.setattr(arena.spreadsheet, "get_arena_schedule", lambda w=None: (_arena_events(), "csv"))
    package = arena.build_arena_package(when=datetime(2026, 10, 5))
    assert package["stage"] == "pengumuman"
    assert "Link turnamen akan dibagikan" in package["wa"]
    assert "chess.com/ak" not in package["wa"]


def test_arena_stage_two_includes_link(monkeypatch):
    monkeypatch.setattr(arena.spreadsheet, "get_arena_schedule", lambda w=None: (_arena_events(), "csv"))
    package = arena.build_arena_package(link="https://chess.com/ak", when=datetime(2026, 10, 5))
    assert package["stage"] == "t_minus_2jam"
    assert "https://chess.com/ak" in package["wa"]
    assert "DIMULAI MALAM INI" in package["wa"]


def test_arena_link_is_plain_text(monkeypatch):
    monkeypatch.setattr(arena.spreadsheet, "get_arena_schedule", lambda w=None: (_arena_events(), "csv"))
    wa = arena.build_arena_package(link="https://chess.com/ak", when=datetime(2026, 10, 5))["wa"]
    assert "](" not in wa


def test_arena_skips_past_events(monkeypatch):
    past = [
        {"tanggal": "2020-01-01", "waktu": "23:00", "format": "Rapid", "lokasi": "",
         "link": "", "keterangan": "", "status": "lewat", "source": "csv"},
    ]
    monkeypatch.setattr(arena.spreadsheet, "get_arena_schedule", lambda w=None: (past, "csv"))
    package = arena.build_arena_package(when=datetime(2026, 10, 5))
    assert package["available"] is False


def test_arena_without_data(monkeypatch):
    monkeypatch.setattr(arena.spreadsheet, "get_arena_schedule", lambda w=None: ([], "csv"))
    package = arena.build_arena_package(when=datetime(2026, 10, 5))
    assert package["available"] is False
    assert "Belum ada jadwal" in package["wa"]


def test_arena_never_invents_link(monkeypatch):
    """Tanpa link di spreadsheet dan tanpa link dari user, tidak ada URL karangan."""
    events = [{
        "tanggal": "2026-10-07", "waktu": "23:00", "format": "Rapid", "lokasi": "",
        "link": "", "keterangan": "", "status": "menunggu_link", "source": "csv",
    }]
    monkeypatch.setattr(arena.spreadsheet, "get_arena_schedule", lambda w=None: (events, "csv"))
    package = arena.build_arena_package(when=datetime(2026, 10, 5))
    assert "http" not in package["wa"]