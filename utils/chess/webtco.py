"""Sumber data liga dari situs resmi TCO.

Situs https://web-tco.vercel.app/liga menyimpan seluruh data liga TCO dan
menyediakannya lewat endpoint JSON publik `/api/liga`. Isinya satu season penuh:
daftar pemain, jadwal pertandingan, dan hasil per sesi, jadi bot tidak perlu
menebak angka klasemen maupun menebak kapan pertandingan berikutnya.

Perhitungan poin di modul ini sengaja meniru aturan yang dipakai situs, bukan
mengarang aturan sendiri:

- Satu match berisi dua game. Skor 2-0 berarti 2 menang, 1-0.5 berarti 1 menang
  1 remis, 1-1 ambigu (bisa 1-1 game atau 2 remis) sehingga dipecah berdasarkan
  `game1_result` dan `game2_result` bila tersedia.
- Poin satu game: menang 1, remis 0.5, kalah 0. Jadi poin match sama dengan
  skor yang tercatat.
- Walkover (WO) dicatat ke pemain yang gagal hadir. Satu WO mengurangi 1 poin,
  dua WO atau lebih mengurangi 3 poin. Tiga WO atau lebih diskualifikasi.
- Urutan klasemen: tidak diskualifikasi dulu, lalu poin, menang, ELO, nama.

Modul ini hanya membaca. Tidak ada operasi tulis ke situs.
"""
from datetime import datetime, timedelta, timezone

import requests

API_LIGA = "https://web-tco.vercel.app/api/liga"
TIMEOUT = 30

LEAGUES = ("Liga 1", "Liga 2", "Liga 3", "Liga 4")

# Poin satu game: menang penuh, remis setengah, kalah nol.
POIN_MENANG = 1.0
POIN_SERI = 0.5
POIN_KALAH = 0.0

# Ambang walkover, sesuai aturan situs: 1 WO = -1 poin, 2 WO atau lebih = -3
# poin sekaligus, 3 WO atau lebih = diskualifikasi.
WO_PENALTY_SATU = 1
WO_PENALTY_BANYAK = 3
WO_BANYAK_MULAI = 2
WO_DISKUALIFIKASI = 3


def _as_date(value=None):
    """Menerima datetime maupun date dan mengembalikan date."""
    base = value or _wib_now()
    return base.date() if isinstance(base, datetime) else base


def _wib_now():
    return datetime.now(timezone(timedelta(hours=7)))


def fetch_payload(url=API_LIGA):
    """Mengambil JSON mentah dari endpoint liga.

    Melempar ValueError bila sumber tidak bisa dibaca, supaya pemanggil bisa
    jatuh ke sumber lain dan menyatakan alasannya secara terus terang.
    """
    try:
        response = requests.get(url, timeout=TIMEOUT, headers={"Accept": "application/json"})
    except requests.RequestException as e:
        raise ValueError(f"Gagal menghubungi web-tco: {e}") from e

    if response.status_code != 200:
        raise ValueError(f"Web TCO membalas HTTP {response.status_code}")

    try:
        return response.json()
    except ValueError as e:
        raise ValueError(f"Respons web-tco bukan JSON: {e}") from e


def load(url=API_LIGA):
    """Mengambil dan memvalidasi payload liga.

    Mengembalikan dict berisi season, players, schedules, results. Kunci yang
    tidak ada diisi list kosong supaya pemanggil tidak perlu memeriksa None.
    """
    payload = fetch_payload(url)
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise ValueError("Struktur respons web-tco tidak dikenali")

    players = [p for p in data.get("players") or [] if isinstance(p, dict) and p.get("id")]
    schedules = [s for s in data.get("schedules") or [] if isinstance(s, dict) and s.get("id")]
    results = [r for r in data.get("results") or [] if isinstance(r, dict) and r.get("schedule_id")]
    if not players:
        raise ValueError("Daftar pemain kosong di web-tco")

    return {
        "season": str(data.get("season") or ""),
        "players": players,
        "schedules": schedules,
        "results": results,
        "source": "web-tco",
    }


def _game_score(value):
    """Hasil satu game dari kolom W/D/L, atau None bila kosong."""
    text = str(value or "").strip().upper()
    return text if text in ("W", "D", "L") else None


def _points_of(games):
    total = 0.0
    for game in games:
        if game == "W":
            total += POIN_MENANG
        elif game == "D":
            total += POIN_SERI
        else:
            total += POIN_KALAH
    return total


def _split_by_score(score):
    """Menebak susunan W/D/L dari skor saat kolom hasil game tidak diisi.

    Skor tercatat dalam kelipatan 0.5 (0, 0.5, 1, 1.5, 2). Skor 1 tidak bisa
    ditebak sendiri karena 1-0.5-0 dan 0.5-0.5-0.5 sama-sama bernilai 1, jadi
    skor 1 selalu dibaca sebagai 1 menang 1 kalah, sama seperti bawaan situs.
    """
    value = max(0.0, min(2.0, float(score)))
    if value >= 1.5:
        return ["W", "W"]
    if value >= 1.0:
        return ["W", "L"]
    if value > 0.0:
        return ["D", "L"]
    return ["L", "L"]


def games_for_player_one(result):
    """Dua hasil game untuk pemain di kolom player1."""
    first = _game_score(result.get("game1_result"))
    second = _game_score(result.get("game2_result"))
    if first and second:
        return [first, second]
    return _split_by_score(result.get("score1"))


def games_for_player_two(result):
    """Dua hasil game untuk pemain di kolom player2, yaitu komplemennya."""
    swap = {"W": "L", "D": "D", "L": "W"}
    return [swap[game] for game in games_for_player_one(result)]


def compute_standings(players, schedules, results):
    """Menghitung klasemen satu liga memakai aturan yang sama dengan situs.

    Mengembalikan list dict yang sudah terurut, lengkap dengan poin, WD-L, dan
    penanda diskualifikasi.
    """
    results_by_schedule = {r["schedule_id"]: r for r in results}
    tally = {
        p["id"]: {"main": 0, "menang": 0, "seri": 0, "kalah": 0, "poin": 0.0, "wo": 0}
        for p in players
    }

    for schedule in schedules:
        if schedule.get("status") != "completed":
            continue
        result = results_by_schedule.get(schedule["id"])
        if not result:
            continue

        first_id = schedule.get("player1_id")
        second_id = schedule.get("player2_id")
        if first_id not in tally or second_id not in tally:
            continue

        # wo_player menunjuk pemain yang gagal hadir. Situs menyimpannya di
        # baris hasil; schedule dipakai sebagai cadangan kalau hasil kosong.
        forfeiter = {1: first_id, 2: second_id}.get(
            _to_int(result.get("wo_player", schedule.get("wo_player")))
        )
        if forfeiter:
            tally[forfeiter]["wo"] += 1

        try:
            score1 = float(result.get("score1"))
            score2 = float(result.get("score2"))
        except (TypeError, ValueError):
            continue

        for player_id, games in (
            (first_id, games_for_player_one(result)),
            (second_id, games_for_player_two(result)),
        ):
            row = tally[player_id]
            row["main"] += 1
            row["menang"] += games.count("W")
            row["seri"] += games.count("D")
            row["kalah"] += games.count("L")
            row["poin"] = round(row["poin"] + _points_of(games), 2)

    rows = []
    for player in players:
        row = tally[player["id"]]
        # Satu WO kena 1 poin, dua WO atau lebih kena 3 poin sekaligus.
        if row["wo"] >= WO_BANYAK_MULAI:
            penalty = WO_PENALTY_BANYAK
        elif row["wo"] == WO_PENALTY_SATU:
            penalty = WO_PENALTY_SATU
        else:
            penalty = 0
        rows.append({
            "id": player["id"],
            "nama": player.get("name") or player.get("username") or player["id"],
            "username": player.get("username", ""),
            "liga": player.get("league", ""),
            "elo": _to_int(player.get("elo"), 0),
            "main": row["main"],
            "menang": row["menang"],
            "seri": row["seri"],
            "kalah": row["kalah"],
            "poin": round(max(0.0, row["poin"] - penalty), 2),
            "wo": row["wo"],
            "disqualified": row["wo"] >= WO_DISKUALIFIKASI,
            "source": "web-tco",
        })

    rows.sort(key=lambda r: (
        r["disqualified"],
        -r["poin"],
        -r["menang"],
        -r["elo"],
        r["nama"].lower(),
    ))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def normalize_league(league=None):
    """Menerima "1", "liga 1", atau "Liga 1" lalu mengembalikan "Liga 1".

    Mengembalikan None bila tidak bisa dipetakan ke liga yang ada, supaya
    pemanggil bisa menampilkan daftar liga yang tersedia, bukan menebak.
    """
    if not league:
        return None
    text = str(league).strip().lower()
    if not text:
        return None
    for known in LEAGUES:
        if text == known.lower():
            return known
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        for known in LEAGUES:
            if known.lower() == f"liga {digits}":
                return known
    return None


def available_leagues(players):
    """Daftar liga yang benar-benar ada di data, urut dari kasta tertinggi."""
    found = {p.get("league", "").strip() for p in players if p.get("league")}
    ordered = [name for name in LEAGUES if name in found]
    return ordered or sorted(found)


def standings(league=None, url=API_LIGA, payload=None):
    """Klasemen satu liga, lengkap dengan peringkat.

    Mengembalikan (rows, alasan). `rows` kosong berarti klasemen tidak bisa
    ditampilkan, dan `alasan` menjelaskan kenapa.
    """
    try:
        data = payload or load(url)
    except ValueError as e:
        return [], str(e)

    wanted = normalize_league(league)
    if league and wanted is None:
        pilihan = ", ".join(available_leagues(data["players"]))
        return [], f"Liga '{league}' tidak dikenal. Pilihan: {pilihan}"

    players = data["players"]
    if wanted:
        players = [p for p in players if p.get("league", "").strip() == wanted]
    if not players:
        pilihan = ", ".join(available_leagues(data["players"]))
        return [], f"Belum ada pemain di {wanted}. Liga yang ada: {pilihan}" if pilihan \
            else "Belum ada pemain di liga ini"

    ids = {p["id"] for p in players}
    schedules = [
        s for s in data["schedules"]
        if s.get("player1_id") in ids and s.get("player2_id") in ids
    ]
    return compute_standings(players, schedules, data["results"]), None


def _player_name(players, schedule, side):
    """Nama pemain dari daftar, dengan fallback ke kolom jadwal."""
    player = players.get(schedule.get(f"player{side}_id"))
    if player:
        return player.get("name") or player.get("username") or ""
    return schedule.get(f"player{side}_name") or ""


def upcoming(league=None, url=API_LIGA, payload=None, limit=5, when=None):
    """Jadwal match yang belum selesai, urut dari yang paling dekat."""
    try:
        data = payload or load(url)
    except ValueError as e:
        return [], str(e)

    wanted = normalize_league(league)
    players = {p["id"]: p for p in data["players"]}
    base = _as_date(when)

    rows = []
    for schedule in data["schedules"]:
        if schedule.get("status") == "completed":
            continue
        if wanted and schedule.get("league", "").strip() != wanted:
            continue
        name = _player_name(players, schedule, 1)
        against = _player_name(players, schedule, 2)
        if not name or not against:
            continue
        rows.append({
            "tanggal": schedule.get("date", ""),
            "waktu": schedule.get("time", ""),
            "round": schedule.get("round"),
            "liga": schedule.get("league", ""),
            "nama": name,
            "lawan": against,
            "source": "web-tco",
        })

    rows.sort(key=lambda r: (
        r["tanggal"] or "9999",
        r["waktu"] or "99:99",
        _to_int(r["round"], 99),
    ))
    future = [r for r in rows if (r["tanggal"] or "") >= base.isoformat()]
    return (future or rows)[:limit], None


def season_summary(url=API_LIGA, payload=None):
    """Ringkasan season: jumlah pemain, jumlah match selesai, dan sisa jadwal."""
    try:
        data = payload or load(url)
    except ValueError as e:
        return {"available": False, "reason": str(e)}

    done = sum(1 for s in data["schedules"] if s.get("status") == "completed")
    return {
        "available": True,
        "season": data["season"],
        "leagues": available_leagues(data["players"]),
        "players": len(data["players"]),
        "matches_done": done,
        "matches_total": len(data["schedules"]),
        "source": "web-tco",
    }