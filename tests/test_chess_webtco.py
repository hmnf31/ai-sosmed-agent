"""Test sumber data liga dari situs TCO.

Tidak ada jaringan di dalam test. Payload di bawah adalah cuplikan nyata dari
`/api/liga`, jadi aturan poin yang diuji sama dengan yang dipakai situs.
"""
import pytest
import requests

from utils.chess import webtco


def _player(pid, name, league="Liga 1", elo=2000):
    return {
        "id": pid, "name": name, "username": name.lower(), "league": league,
        "elo": elo, "elo_avg": elo, "status": "active",
    }


def _match(mid, p1, p2, status="completed", date="2026-10-03", time="19:00", round_no=1):
    return {
        "id": mid, "league": "Liga 1", "round": round_no, "player1_id": p1,
        "player2_id": p2, "date": date, "time": time, "status": status, "season": 1,
    }


def _result(sid, s1, s2, g1=None, g2=None, wo=0):
    """Baris hasil. `wo` menunjuk pemain yang gagal hadir: 1 = player1, 2 = player2."""
    return {
        "id": "r" + sid, "schedule_id": sid, "score1": s1, "score2": s2,
        "wo_player": wo, "game1_result": g1, "game2_result": g2, "season": 1,
    }


def _by_name(rows):
    """Mengubah tabel klasemen jadi dict berdasarkan nama, biar tes tidak rapuh."""
    return {row["nama"]: row for row in rows}


def test_two_wins_gives_two_points():
    players = [_player("a", "Andi"), _player("b", "Budi")]
    rows = webtco.compute_standings(
        players,
        [_match("m1", "a", "b")],
        [_result("m1", 2, 0)],
    )
    andi, budi = rows
    assert andi["poin"] == 2.0
    assert (andi["menang"], andi["seri"], andi["kalah"]) == (2, 0, 0)
    assert budi["poin"] == 0.0
    assert (budi["menang"], budi["seri"], budi["kalah"]) == (0, 0, 2)


def test_draw_games_count_half_point():
    players = [_player("a", "Andi"), _player("b", "Budi")]
    rows = webtco.compute_standings(
        players,
        [_match("m1", "a", "b")],
        [_result("m1", 1, 1, "D", "D")],
    )
    assert [r["poin"] for r in rows] == [1.0, 1.0]
    assert [r["seri"] for r in rows] == [2, 2]


def test_ambiguous_split_uses_game_results():
    """Skor 1-1 berarti 1 menang 1 kalah, bukan 2 remis."""
    players = [_player("a", "Andi"), _player("b", "Budi")]
    rows = webtco.compute_standings(
        players,
        [_match("m1", "a", "b")],
        [_result("m1", 1, 1, "W", "L")],
    )
    andi, budi = rows
    assert (andi["menang"], andi["kalah"]) == (1, 1)
    assert (budi["menang"], budi["kalah"]) == (1, 1)
    assert andi["poin"] == budi["poin"] == 1.0


def test_split_ambiguous_draw_without_game_results():
    """Tanpa kolom hasil game, skor 1-1 dibaca sebagai 1 menang 1 kalah."""
    players = [_player("a", "Andi"), _player("b", "Budi")]
    rows = webtco.compute_standings(
        players,
        [_match("m1", "a", "b")],
        [_result("m1", 1, 1)],
    )
    assert [r["poin"] for r in rows] == [1.0, 1.0]
    assert rows[0]["seri"] == 0


def test_single_walkover_costs_one_point():
    """Budi menang satu match lalu gagal hadir satu kali: 2 - 1 = 1 poin."""
    players = [_player("a", "Andi"), _player("b", "Budi"), _player("c", "Caca")]
    rows = _by_name(webtco.compute_standings(
        players,
        [
            _match("m1", "b", "c"),
            _match("m2", "a", "b", round_no=2),  # Budi walkover, skor 0-2
        ],
        [_result("m1", 2, 0), _result("m2", 2, 0, wo=2)],
    ))
    assert rows["Budi"]["wo"] == 1
    assert rows["Budi"]["poin"] == 1.0  # 2.0 dikurangi 1
    assert rows["Andi"]["wo"] == 0
    assert rows["Andi"]["poin"] == 2.0


def test_two_walkovers_cost_three_points():
    """Dua walkover kena penalti 3 poin total, bukan 1+1."""
    players = [_player("a", "Andi"), _player("b", "Budi"), _player("c", "Caca")]
    rows = _by_name(webtco.compute_standings(
        players,
        [
            _match("m1", "b", "c"),
            _match("m2", "b", "c", round_no=2),
            _match("m3", "a", "b", round_no=3),  # Budi walkover
            _match("m4", "a", "b", round_no=4),  # Budi walkover lagi
        ],
        [
            _result("m1", 2, 0),
            _result("m2", 2, 0),
            _result("m3", 2, 0, wo=2),
            _result("m4", 2, 0, wo=2),
        ],
    ))
    assert rows["Budi"]["wo"] == 2
    assert rows["Budi"]["poin"] == 1.0  # 4.0 dikurangi 3
    assert rows["Budi"]["disqualified"] is False


def test_three_walkovers_disqualify_and_sink_to_bottom():
    players = [_player("a", "Andi"), _player("b", "Budi"), _player("c", "Caca")]
    table = webtco.compute_standings(
        players,
        [
            _match("m1", "b", "c"),
            _match("m2", "b", "c", round_no=2),
            _match("m3", "b", "c", round_no=3),
            _match("m4", "a", "b", round_no=4),
            _match("m5", "a", "b", round_no=5),
            _match("m6", "a", "b", round_no=6),
        ],
        [
            _result("m1", 2, 0),
            _result("m2", 2, 0),
            _result("m3", 2, 0),
            _result("m4", 2, 0, wo=2),
            _result("m5", 2, 0, wo=2),
            _result("m6", 2, 0, wo=2),
        ],
    )
    rows = _by_name(table)
    assert rows["Budi"]["disqualified"] is True
    assert rows["Budi"]["poin"] == 3.0  # 6.0 dikurangi 3
    # Diskualifikasi selalu di urutan bawah, walau poin kasarnya paling tinggi.
    assert table[-1]["nama"] == "Budi"
    assert table[0]["nama"] == "Andi"


def test_unfinished_matches_are_ignored():
    players = [_player("a", "Andi"), _player("b", "Budi")]
    rows = webtco.compute_standings(
        players,
        [_match("m1", "a", "b", status="upcoming")],
        [],
    )
    assert [r["main"] for r in rows] == [0, 0]
    assert [r["poin"] for r in rows] == [0.0, 0.0]


def test_ranking_order_uses_points_then_wins_then_elo():
    players = [
        _player("a", "Andi", elo=2100),
        _player("b", "Budi", elo=2400),
        _player("c", "Caca", elo=2000),
    ]
    rows = webtco.compute_standings(
        players,
        [
            _match("m1", "a", "c"),
            _match("m2", "b", "c"),
        ],
        [_result("m1", 2, 0), _result("m2", 0, 2)],
    )
    # Andi dan Caka sama-sama 2 poin dengan 2 menang, jadi ELO yang menentukan:
    # Andi 2100 di atas Caca 2000. Budi kalah dua kali sehingga di paling bawah
    # meski ELO-nya paling tinggi.
    assert [r["nama"] for r in rows] == ["Andi", "Caca", "Budi"]
    assert [r["rank"] for r in rows] == [1, 2, 3]


def test_match_without_result_row_is_skipped():
    players = [_player("a", "Andi"), _player("b", "Budi")]
    rows = webtco.compute_standings(players, [_match("m1", "a", "b")], [])
    assert [r["main"] for r in rows] == [0, 0]


def test_normalize_league_accepts_common_shapes():
    assert webtco.normalize_league("Liga 1") == "Liga 1"
    assert webtco.normalize_league("liga 3") == "Liga 3"
    assert webtco.normalize_league("2") == "Liga 2"
    assert webtco.normalize_league("") is None
    assert webtco.normalize_league("Liga 9") is None


def test_games_complement_for_second_player():
    result = _result("m1", 2, 0, "W", "W")
    assert webtco.games_for_player_one(result) == ["W", "W"]
    assert webtco.games_for_player_two(result) == ["L", "L"]


def test_standings_filters_to_one_league():
    payload = {
        "season": "1",
        "players": [_player("a", "Andi", "Liga 1"), _player("b", "Budi", "Liga 2")],
        "schedules": [],
        "results": [],
    }
    rows, err = webtco.standings("Liga 2", payload=payload)
    assert err is None
    assert [r["nama"] for r in rows] == ["Budi"]


def test_standings_unknown_league_lists_choices():
    payload = {
        "season": "1",
        "players": [_player("a", "Andi", "Liga 1"), _player("b", "Budi", "Liga 2")],
        "schedules": [],
        "results": [],
    }
    rows, err = webtco.standings("Liga 4", payload=payload)
    assert rows == []
    assert "Liga 1" in err and "Liga 2" in err


def test_upcoming_sorted_and_skips_completed():
    from datetime import date

    payload = {
        "season": "1",
        "players": [_player("a", "Andi"), _player("b", "Budi"), _player("c", "Caca")],
        "schedules": [
            _match("m1", "a", "b", status="completed", date="2026-10-01"),
            _match("m2", "a", "c", status="upcoming", date="2026-10-10", time="19:00", round_no=3),
            _match("m3", "b", "c", status="upcoming", date="2026-10-08", time="20:00", round_no=2),
        ],
        "results": [_result("m1", 2, 0)],
    }
    rows, err = webtco.upcoming(payload=payload, when=date(2026, 10, 5))
    assert err is None
    assert [r["nama"] for r in rows] == ["Budi", "Andi"]
    assert rows[0]["lawan"] == "Caca"
    assert rows[0]["round"] == 2


def test_season_summary_counts():
    payload = {
        "season": "3",
        "players": [_player("a", "Andi", "Liga 1"), _player("b", "Budi", "Liga 2")],
        "schedules": [
            _match("m1", "a", "b", status="completed"),
            _match("m2", "a", "b", status="upcoming"),
        ],
        "results": [],
    }
    summary = webtco.season_summary(payload=payload)
    assert summary["available"] is True
    assert summary["season"] == "3"
    assert summary["matches_done"] == 1
    assert summary["matches_total"] == 2
    assert summary["leagues"] == ["Liga 1", "Liga 2"]


def test_unreachable_endpoint_reports_reason(monkeypatch):
    """Endpoint mati harus jadi ValueError dengan alasan, bukan exception lain."""
    def boom(*args, **kwargs):
        raise requests.ConnectionError("koneksi ditolak")

    monkeypatch.setattr(webtco.requests, "get", boom)
    with pytest.raises(ValueError) as excinfo:
        webtco.fetch_payload()
    assert "web-tco" in str(excinfo.value)


def test_non_json_response_reports_reason(monkeypatch):
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            raise ValueError("bukan json")

    monkeypatch.setattr(webtco.requests, "get", lambda *a, **k: FakeResponse())
    with pytest.raises(ValueError):
        webtco.fetch_payload()


def test_payload_without_players_is_rejected(monkeypatch):
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"data": {"players": [], "schedules": [], "results": []}}

    monkeypatch.setattr(webtco.requests, "get", lambda *a, **k: FakeResponse())
    with pytest.raises(ValueError):
        webtco.load()


def test_http_error_status_is_reported(monkeypatch):
    class FakeResponse:
        status_code = 503

    monkeypatch.setattr(webtco.requests, "get", lambda *a, **k: FakeResponse())
    with pytest.raises(ValueError) as excinfo:
        webtco.fetch_payload()
    assert "503" in str(excinfo.value)