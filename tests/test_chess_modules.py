"""Test modul operasional klub catur: TCO, Liga, Arena Kings.

Semua diuji tanpa spreadsheet nyata: sumber dipalsukan supaya angka yang
dipakai adalah angka tetap yang bisa diperiksa.
"""
from datetime import datetime

import pytest

from utils.chess import arena, liga, tco


def _event(tanggal="2026-10-14", link="https://chess.com/tco", waktu="20:00",
           fmt="Blitz", lokasi="Online", judul="", mode=""):
    return {
        "tanggal": tanggal, "tanggal_teks": tanggal, "judul": judul, "mode": mode,
        "waktu": waktu, "format": fmt, "lokasi": lokasi, "link": link,
        "keterangan": "", "source": "csv", "found": True,
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


def test_tco_template_follows_judul_and_mode(monkeypatch):
    """Pesan ikut isi sheet, bukan kalimat tetap di kode."""
    monkeypatch.setattr(
        tco.spreadsheet, "get_tco_schedule",
        lambda when=None: _event(judul="TCO Mingguan #12", mode="Internal Mingguan"),
    )
    wa = tco.build_tco_package()["wa"]
    assert wa.startswith("♟️ TCO Mingguan #12")
    assert "Internal Mingguan kembali hadir!" in wa


def test_tco_falls_back_to_default_judul(monkeypatch):
    monkeypatch.setattr(tco.spreadsheet, "get_tco_schedule", lambda when=None: _event())
    wa = tco.build_tco_package()["wa"]
    assert tco.DEFAULT_JUDUL in wa
    assert tco.DEFAULT_MODE in wa


def test_tco_reminder_h1_hari_has_no_link(monkeypatch):
    monkeypatch.setattr(tco.spreadsheet, "get_tco_schedule", lambda when=None: _event())
    wa = tco.build_tco_package("h1_hari")["wa"]
    assert "TCO BESOK" in wa
    assert "https://chess.com/tco" not in wa
    assert "Link pendaftaran akan dibagikan" in wa


def test_tco_reminder_h1_jam_includes_link(monkeypatch):
    monkeypatch.setattr(tco.spreadsheet, "get_tco_schedule", lambda when=None: _event())
    package = tco.build_tco_package("h1_jam")
    assert "1 JAM LAGI" in package["wa"]
    assert "https://chess.com/tco" in package["wa"]


def test_tco_reminder_h1_jam_without_link(monkeypatch):
    """Tanpa link, bot mengatakannya terus terang, bukan mengarang URL."""
    monkeypatch.setattr(
        tco.spreadsheet, "get_tco_schedule",
        lambda when=None: _event(link=""),
    )
    wa = tco.build_tco_package("h1_jam")["wa"]
    assert "belum dibagikan" in wa
    assert "http" not in wa


def test_tco_link_argument_overrides_sheet(monkeypatch):
    monkeypatch.setattr(tco.spreadsheet, "get_tco_schedule", lambda when=None: _event())
    wa = tco.build_tco_package("h1_jam", link="https://chess.com/baru")["wa"]
    assert "https://chess.com/baru" in wa
    assert "https://chess.com/tco" not in wa


def test_tco_stage_for_days():
    assert tco.stage_for(2) == "pengumuman"
    assert tco.stage_for(1) == "h1_hari"
    assert tco.stage_for(0) is None
    assert tco.days_until("2026-10-14", datetime(2026, 10, 12)) == 2


# --- Liga ------------------------------------------------------------------

@pytest.fixture
def standings():
    return [
        {"liga": "Liga 1", "rank": 1, "nama": "Player A", "main": 5, "menang": 4,
         "seri": 1, "kalah": 0, "poin": 13, "source": "web-tco", "elo": 2000,
         "username": "pa", "wo": 0, "disqualified": False},
        {"liga": "Liga 1", "rank": 2, "nama": "Player B", "main": 5, "menang": 4,
         "seri": 0, "kalah": 1, "poin": 12, "source": "web-tco", "elo": 1900,
         "username": "pb", "wo": 0, "disqualified": False},
        {"liga": "Liga 1", "rank": 3, "nama": "Player C", "main": 5, "menang": 3,
         "seri": 1, "kalah": 1, "poin": 10, "source": "web-tco", "elo": 1800,
         "username": "pc", "wo": 0, "disqualified": False},
    ]


def _no_site(monkeypatch, rows, reason="Situs TCO tidak terbaca"):
    """Mematikan sumber web-tco supaya sheet yang diuji jadi sumber utama."""
    monkeypatch.setattr(liga.webtco, "standings", lambda league=None: ([], reason))
    monkeypatch.setattr(liga.webtco, "upcoming", lambda *a, **k: ([], "tidak dipakai"))
    monkeypatch.setattr(liga.spreadsheet, "get_league_standings", lambda l=None: (rows, "sheet"))


def test_league_package_available(monkeypatch, standings):
    monkeypatch.setattr(liga.webtco, "standings", lambda league=None: (standings, None))
    package = liga.build_league_package("Liga 1")
    assert package["available"] is True
    assert package["source"] == "web-tco"
    assert "Player A" in package["wa"]
    assert "13 poin" in package["wa"]


def test_league_table_lists_all(monkeypatch, standings):
    monkeypatch.setattr(liga.webtco, "standings", lambda league=None: (standings, None))
    table = liga.build_league_package("Liga 1")["table"]
    for name in ("Player A", "Player B", "Player C"):
        assert name in table
    assert "13 poin" in table


def test_league_marks_walkover_and_disqualification(monkeypatch):
    rows = [
        {"liga": "Liga 1", "rank": 1, "nama": "Aman", "main": 2, "menang": 2,
         "seri": 0, "kalah": 0, "poin": 4.0, "elo": 2000, "username": "a",
         "wo": 0, "disqualified": False, "source": "web-tco"},
        {"liga": "Liga 1", "rank": 2, "nama": "Kena WO", "main": 2, "menang": 1,
         "seri": 0, "kalah": 1, "poin": 1.0, "elo": 1900, "username": "b",
         "wo": 1, "disqualified": False, "source": "web-tco"},
        {"liga": "Liga 1", "rank": 3, "nama": "_diskual", "main": 3, "menang": 1,
         "seri": 0, "kalah": 2, "poin": 1.0, "elo": 1800, "username": "c",
         "wo": 3, "disqualified": True, "source": "web-tco"},
    ]
    monkeypatch.setattr(liga.webtco, "standings", lambda league=None: (rows, None))
    table = liga.build_league_package("Liga 1")["table"]
    assert "WO 1" in table
    assert "DISKUALIFIKASI" in table


def test_league_falls_back_to_sheet(monkeypatch, standings):
    """Situs tidak terbaca -> angka diambil dari sheet, dengan catatan jujur."""
    _no_site(monkeypatch, standings)
    package = liga.build_league_package("Liga 1")
    assert package["available"] is True
    assert package["source"] == "sheet"
    assert "sheet Liga" in " ".join(package["notes"])


def test_league_without_data(monkeypatch):
    _no_site(monkeypatch, [])
    package = liga.build_league_package("Liga 1")
    assert package["available"] is False
    assert "belum tersedia" in package["wa"].lower()
    assert package["table"] == ""


def test_league_error_message_from_spreadsheet(monkeypatch):
    monkeypatch.setattr(liga.webtco, "standings", lambda league=None: ([], "Situs mati"))
    monkeypatch.setattr(liga.spreadsheet, "get_league_standings", lambda l=None: ("Sheet rusak", "error"))
    package = liga.build_league_package("Liga 1")
    assert package["available"] is False
    assert "Sheet rusak" in package["wa"]


def test_league_unknown_league_lists_choices(monkeypatch):
    pesan = "Liga 'Liga 9' tidak dikenal. Pilihan: Liga 1, Liga 2, Liga 3, Liga 4"
    monkeypatch.setattr(liga.webtco, "standings", lambda league=None: ([], pesan))
    package = liga.build_league_package("Liga 9")
    assert package["available"] is False
    assert "Liga 1" in package["wa"]


def test_league_single_player_still_works(monkeypatch):
    one = [{"liga": "Liga 1", "rank": 1, "nama": "Solo", "main": 3, "menang": 2,
            "seri": 0, "kalah": 1, "poin": 6, "elo": 2000, "username": "s",
            "wo": 0, "disqualified": False, "source": "web-tco"}]
    monkeypatch.setattr(liga.webtco, "standings", lambda league=None: (one, None))
    package = liga.build_league_package("Liga 1")
    assert "Solo" in package["wa"]


def test_league_two_players(monkeypatch):
    two = [
        {"liga": "Liga 1", "rank": 1, "nama": "Satu", "main": 3, "menang": 3,
         "seri": 0, "kalah": 0, "poin": 9, "elo": 2000, "username": "s",
         "wo": 0, "disqualified": False, "source": "web-tco"},
        {"liga": "Liga 1", "rank": 2, "nama": "Dua", "main": 3, "menang": 1,
         "seri": 0, "kalah": 2, "poin": 3, "elo": 1900, "username": "d",
         "wo": 0, "disqualified": False, "source": "web-tco"},
    ]
    monkeypatch.setattr(liga.webtco, "standings", lambda league=None: (two, None))
    package = liga.build_league_package("Liga 1")
    assert "Dua" in package["wa"]
    assert package["poster"]


def test_league_without_argument_shows_overview(monkeypatch):
    """Tanpa nama liga, yang ditampilkan ringkasan season, bukan gabungan liga."""
    monkeypatch.setattr(liga.webtco, "season_summary", lambda **k: {
        "available": True, "season": "1", "leagues": ["Liga 1", "Liga 2"],
        "players": 24, "matches_done": 10, "matches_total": 60, "source": "web-tco",
    })
    package = liga.build_league_package()
    assert package["available"] is True
    assert package["rows"] == []
    assert "RINGKASAN" in package["league"]
    assert "Liga 1, Liga 2" in package["wa"]


def test_league_schedule_block(monkeypatch, standings):
    jadwal = [{"tanggal": "2026-10-10", "waktu": "19:00", "round": 3, "liga": "Liga 1",
               "nama": "Player A", "lawan": "Player B", "source": "web-tco"}]
    monkeypatch.setattr(liga.webtco, "standings", lambda league=None: (standings, None))
    monkeypatch.setattr(liga.webtco, "upcoming", lambda *a, **k: (jadwal, None))
    package = liga.build_league_package("Liga 1", with_schedule=True)
    assert "JADWAL BERIKUTNYA" in package["table"]
    assert "Player A vs Player B" in package["table"]


# --- Arena Kings ------------------------------------------------------------

def _arena_settings(**overrides):
    values = {
        "link": "",
        "link_arena": "",
        "link_form": "",
        "waktu": "23.00 WIB",
        "format": "3+0",
        "durasi": "120 Menit",
        "lokasi": "Online",
        "keterangan": "",
    }
    values.update(overrides)
    return values


def _patch_settings(monkeypatch, values):
    monkeypatch.setattr(arena.spreadsheet, "read_settings", lambda *a, **k: (dict(values), "csv"))


def test_arena_uses_first_wednesday():
    assert arena.first_wednesday(2026, 10).isoformat() == "2026-10-07"
    assert arena.next_arena_date(datetime(2026, 10, 5)).isoformat() == "2026-10-07"
    # Rabu pertama yang sudah lewat -> bulan berikutnya, bukan tanggal lama.
    assert arena.next_arena_date(datetime(2026, 10, 8)).isoformat() == "2026-11-04"
    assert arena.next_arena_date(datetime(2026, 12, 20)).isoformat() == "2027-01-06"


def test_arena_dates_do_not_need_spreadsheet(monkeypatch):
    """Jadwal tetap dihitung sendiri; sheet hanya memuat pengaturan."""
    _patch_settings(monkeypatch, _arena_settings())
    config = arena.get_config(datetime(2026, 10, 5))
    assert config["tanggal"] == "2026-10-07"
    assert config["waktu"] == "23.00 WIB"
    assert config["format"] == "3+0"
    assert config["durasi"] == "120 Menit"
    assert config["bulan"] == "Oktober"


def test_arena_announcement_follows_fixed_template(monkeypatch):
    """Struktur pesan utama tetap: judul, info, form, syarat, reward, kontak."""
    _patch_settings(monkeypatch, _arena_settings())
    wa = arena.build_arena_package("pengumuman", when=datetime(2026, 10, 5))["wa"]
    assert wa.startswith("PENGUMUMAN RESMI TCO CHESS: OKTOBER ARENA KINGS & REWARD SYSTEM")
    assert "📅 : Rabu, 7 Oktober 2026" in wa
    assert "⚔️ : 3+0 (120 Menit)" in wa
    assert "Standby di Room 1 jam sebelum mulai!" in wa
    assert "ISI DATA DI SINI: https://forms.gle/1YCVyZMPwpWKN8ZX7" in wa
    assert "Syarat Claim Hadiah" in wa
    for nominal in ("Rp 1.200.000", "Rp 50.000", "Rp 10.000"):
        assert nominal in wa
    assert wa.count("SKENARIO") == 5
    assert "Gens Una Sumus" in wa


def test_arena_only_date_and_month_change_between_months(monkeypatch):
    """Dari satu bulan ke bulan, hanya tanggal dan nama bulan yang berubah."""
    _patch_settings(monkeypatch, _arena_settings())
    okt = arena.build_arena_package("pengumuman", when=datetime(2026, 10, 5))["wa"]
    nov = arena.build_arena_package("pengumuman", when=datetime(2026, 11, 2))["wa"]
    assert "Rabu, 7 Oktober 2026" in okt
    assert "Rabu, 4 November 2026" in nov
    # Blok hadiah tidak boleh ikut berubah antar bulan.
    assert okt[okt.index("💰 REWARD TCO"):] == nov[nov.index("💰 REWARD TCO"):]


def test_arena_reminder_stages(monkeypatch):
    _patch_settings(monkeypatch, _arena_settings())
    dua_jam = arena.build_arena_package(
        "h2_jam", link="https://chess.com/ak", when=datetime(2026, 10, 5)
    )
    assert "2 JAM LAGI" in dua_jam["wa"]
    assert "https://chess.com/ak" in dua_jam["wa"]

    satu_jam = arena.build_arena_package(
        "h1_jam", link="https://chess.com/ak", when=datetime(2026, 10, 5)
    )
    assert "1 JAM LAGI" in satu_jam["wa"]


def test_arena_reminder_without_arena_link(monkeypatch):
    """Link arena belum ada: bot memberi tahu letaknya, tidak mengarang URL."""
    _patch_settings(monkeypatch, _arena_settings(link_arena=""))
    wa = arena.build_arena_package("h2_jam", when=datetime(2026, 10, 5))["wa"]
    assert 'halaman club "Event"' in wa
    assert "chess.com/ak" not in wa


def test_arena_uses_sheet_arena_link(monkeypatch):
    _patch_settings(monkeypatch, _arena_settings(link_arena="https://chess.com/ak"))
    package = arena.build_arena_package("h2_jam", when=datetime(2026, 10, 5))
    assert "https://chess.com/ak" in package["wa"]


def test_arena_link_is_plain_text(monkeypatch):
    _patch_settings(monkeypatch, _arena_settings(link_arena="https://chess.com/ak"))
    wa = arena.build_arena_package("h2_jam", when=datetime(2026, 10, 5))["wa"]
    assert "](" not in wa


def test_arena_defaults_when_sheet_empty(monkeypatch):
    """Sheet kosong tidak membuat bot gagal; pesan tetap dari bawaan."""
    _patch_settings(monkeypatch, {})
    package = arena.build_arena_package(when=datetime(2026, 10, 5))
    assert package["available"] is True
    assert package["source"] == "default"
    assert package["event"]["waktu"] == "23.00 WIB"
    assert package["event"]["link_klub"] == arena.DEFAULT_LINK_KLUB
    assert package["event"]["link_form"] == arena.DEFAULT_LINK_FORM


def test_arena_never_invents_arena_link(monkeypatch):
    """Tanpa link di sheet dan tanpa link dari user, tidak ada URL karangan."""
    _patch_settings(monkeypatch, _arena_settings(link_arena=""))
    package = arena.build_arena_package("h2_jam", when=datetime(2026, 10, 5))
    assert "JOIN ARENA" not in package["wa"]


def test_arena_stage_for_days(monkeypatch):
    """Pengingat jatuh di hari yang ditentukan; hari lain tidak dipaksakan."""
    _patch_settings(monkeypatch, _arena_settings())
    when = datetime(2026, 10, 5)
    assert arena.days_until("2026-10-07", when) == 2
    assert arena.stage_for(arena.days_until("2026-10-07", when)) == "h2_jam"
    assert arena.stage_for(14) == "pengumuman"
    assert arena.stage_for(7) == "pengumuman"
    assert arena.stage_for(5) is None


def test_arena_settings_keys_accept_spaces(monkeypatch):
    """Header sheet pakai spasi ("Link Klub"), alias pakai garis bawah."""
    _patch_settings(monkeypatch, {
        "link klub": "https://chess.com/ak",
        "jam": "22.00 WIB",
        "link form": "https://forms.gle/baru",
        "kontak 1": "Bang Wawan",
        "kontak 2": "Bang Arif",
    })
    config = arena.get_config(datetime(2026, 10, 5))
    assert config["link_klub"] == "https://chess.com/ak"
    assert config["waktu"] == "22.00 WIB"
    assert config["link_form"] == "https://forms.gle/baru"
    assert config["kontak"] == ["Bang Wawan", "Bang Arif"]


def test_arena_contacts_come_from_sheet_when_filled(monkeypatch):
    _patch_settings(monkeypatch, {"kontak 1": "Bang Wawan @waone0608"})
    wa = arena.build_arena_package(when=datetime(2026, 10, 5))["wa"]
    assert "Bang Wawan @waone0608" in wa
    assert "Bang Arif" not in wa