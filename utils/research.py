"""Riset konten multi-sumber (Phase 5 Research).

Satu permintaan ("buat kan konten trend MLBB") menghasilkan paket riset berisi
sumber yang terstruktur: judul, URL, penerbit, tanggal terbit, klaim pendek,
dan status fact-check. Paket itu bisa dipetakan ke field `research` pada
content plan supaya konten aktual "menyimpan sumber/status".

Urutan penyedia (fallback):
1. Web search 9Router (`POST <NINEROUTER_URL>/v1/search`) -> item ber-URL.
2. Tren YouTube via `utils.scraper` -> judul tanpa URL (unverified).
3. `seed_topics` akun / query itu sendiri.

Item dianggap *verified* bila punya URL + penerbit + tanggal terbit dari sumber
web/news, artinya klaim bisa ditelusuri ke sumber tertanggal. Item tanpa itu
tetap disimpan sebagai *unverified*, tidak pernah di buang; keputusan akhir
tetap di tangan reviewer (approval).
"""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

#: URL 9Router default beda dari .env.example (3000): klien lokal ini
#: memakai instansi yang benar-benar berjalan.
DEFAULT_NINEROUTER_URL = os.getenv("NINEROUTER_URL") or "http://127.0.0.1:20128"
DEFAULT_NINEROUTER_KEY = os.getenv("NINEROUTER_KEY") or ""

#: Status dlama schema content_plan (research.sources[].status).
ITEM_STATUSES = ("verified", "unverified", "contradicted", "pending")
#: Status keseluruhan pada research.fact_check_status.
PACK_STATUSES = ("verified", "unverified", "failed")

_URL_RE = re.compile(r"https?://\S+")
_DATE_RE = re.compile(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$")
_ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$")

#: Nama bulan Indonesia -> nomor, agar "6 Oktober 2026" ikut terbaca.
_ID_MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11,
    "desember": 12,
}
_STRPTIME_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
)


class ResearchError(Exception):
    """Kegagalan riset; pemanggil harus menangani fallback, bukan error."""


def _truncate(text, limit):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text[:limit] if len(text) <= limit else text[: limit - 3] + "..."


def clean_url(value):
    """Mengambil URL http(s) polos dari teks; None bila tidak ada.

    Model/sumber kadang membalas URL berformat markdown `[teks](url)`;
    bentuk itu dibuang supaya URL tersimpan polos dan bisa diklik.
    """
    if not value:
        return None
    match = _URL_RE.search(str(value))
    if not match:
        return None
    # Markdown `[teks](url)` menyisakan kurung tutup; tanda baca akhir yang
    # tidak mungkin jadi bagian URL dibuang.
    return re.sub(r"[)\]}>,\"']+$", "", match.group(0))


def _domain(url):
    if not url:
        return None
    return urlparse(url).netloc


def _stable_id(url, title):
    """ID sumber stabil: hash URL bila ada, kalau tidak hash judul."""
    seed = (url or title or "unknown").strip()
    return "src_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def _utcnow():
    return datetime.now(timezone.utc)


def _iso_now():
    return _utcnow().isoformat(timespec="seconds")


def parse_date(value):
    """Mengubah beragam bentuk tanggal menjadi ISO `YYYY-MM-DD` (atau None).

    Menerima ISO datetime, `Y-m-d`, `d-m-Y`, dan nama bulan Indonesia/Inggris
    ('6 Oktober 2026', 'Oct 6, 2026', ...). Bila tidak bisa dibaca -> None.
    """
    if value in (None, "", 0):
        return None
    if isinstance(value, (int, float)):
        seconds = value
        if seconds > 10_000_000_000:
            seconds = seconds / 1000  # milidetik -> detik
        return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%d")

    text = str(value).strip()
    match = _ISO_DATE_RE.match(text)
    if match:
        return match.group(0)[:10]

    match = _DATE_RE.match(text)
    if match:
        day, month_word, year = match.groups()
        month = _ID_MONTHS.get(month_word.lower())
        if month:
            return f"{int(year):04d}-{month:02d}-{int(day):02d}"

    lowered = text.lower()
    for id_name, num in _ID_MONTHS.items():
        if id_name in lowered and (year_match := re.search(r"(\d{4})", text)):
            year = year_match.group(1)
            day_match = re.search(r"(?<!\d)(\d{1,2})(?!\d)", text.split(year)[0])
            if day_match:
                return f"{int(year):04d}-{num:02d}-{int(day_match.group(1)):02d}"

    for fmt in _STRPTIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def normalize_item(raw, provider=None):
    """Merapikan satu hasil pencarian/sumber jadi dict ResearchItem.

    Output memakai kunci yang selaras dengan schema content_plan
    `research.sources` (source_id, url, title, publisher, published_date,
    retrieved_at, claim, status) plus metadata posisi/score.
    """
    raw = raw or {}
    metadata = raw.get("metadata") or {}
    url = clean_url(raw.get("url") or raw.get("link") or raw.get("source_url"))
    title = _truncate(raw.get("title") or raw.get("headline") or metadata.get("title") or "", 200)
    snippet = raw.get("snippet") or raw.get("content") or raw.get("description") or ""
    claim = _truncate(snippet or title, 300)
    published = parse_date(
        raw.get("published_at")
        or raw.get("published_date")
        or raw.get("published")
        or raw.get("date")
    )
    source_type = (
        metadata.get("source_type") or _infer_source_type(url)
    )
    publisher = (
        raw.get("publisher")
        or metadata.get("site_name")
        or metadata.get("source")
        or _domain(url)
    )
    citation = raw.get("citation") or {}
    retrieved = citation.get("retrieved_at") or raw.get("retrieved_at") or _iso_now()

    status = "unverified"
    if (
        url
        and publisher
        and published
        and source_type in ("web", "news")
    ):
        status = "verified"

    return {
        "source_id": raw.get("source_id") or _stable_id(url, title or claim),
        "url": url,
        "title": title or None,
        "publisher": _truncate(publisher, 100) or None,
        "source_type": source_type,
        "published_date": published,
        "retrieved_at": retrieved,
        "claim": claim or None,
        "status": status,
        "position": raw.get("position"),
        "score": raw.get("score"),
        "provider": provider or raw.get("provider") or citation.get("provider"),
    }


def _infer_source_type(url):
    if not url:
        return "youtube"
    domain = _domain(url)
    if "youtube.com" in domain or "youtu.be" in domain:
        return "youtube"
    if "twitter.com" in domain or "x.com" in domain:
        return "x"
    return "web"


def _request_json(url, *, method="GET", payload=None, headers=None, timeout=20):
    """GET/POST HTTP JSON sederhana; gagal -> ResearchError berisi sebab."""
    data = None
    merged = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        merged["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=merged, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")[:200]
        raise ResearchError(f"9Router HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise ResearchError(f"9Router tidak terjangkau: {error.reason}") from error
    except (json.JSONDecodeError, ValueError) as error:
        raise ResearchError(f"Respons 9Router bukan JSON: {error}") from error
    except TimeoutError as error:
        raise ResearchError("9Router timeout") from error


def list_web_models(url=None, key=None, timeout=8):
    """Mendaftar model web search + web fetch dari 9Router.

    Mengembalikan dict `{"search": [id ...], "fetch": [id ...]}`. URL dan key
    bisa diberikan eksplisit untuk testing; default diambil dari env.
    """
    base = (url or DEFAULT_NINEROUTER_URL).rstrip("/")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    payload = _request_json(f"{base}/v1/models/web", method="GET", headers=headers, timeout=timeout)
    kinds = {"search": [], "fetch": []}
    for model in payload.get("data", []):
        kind = model.get("kind")
        if kind == "webSearch":
            kinds["search"].append(model.get("id"))
        elif kind == "webFetch":
            kinds["fetch"].append(model.get("id"))
    return kinds


def search_web(query, *, model=None, max_results=5, search_type="web", url=None,
               key=None, timeout=20):
    """Web search via 9Router `/v1/search`; mengembalikan daftar item.

    Pemanggil bertanggung jawab menangkap ResearchError (riset tidak boleh
    menggagalkan produksi konten; pemanggil yang memilih fallback).
    """
    base = (url or DEFAULT_NINEROUTER_URL).rstrip("/")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    if not model:
        models = list_web_models(url=url, key=key, timeout=max(8, timeout))
        candidates = models.get("search")
        if not candidates:
            raise ResearchError("9Router tidak punya model web search aktif")
        model = candidates[0]
    payload = {
        "model": model,
        "query": query,
        "max_results": max_results,
    }
    if search_type and search_type != "web":
        payload["search_type"] = search_type
    response = _request_json(
        f"{base}/v1/search",
        method="POST",
        payload=payload,
        headers=headers,
        timeout=timeout,
    )
    results = response.get("results") or []
    provider = response.get("provider") or model
    return [normalize_item(item, provider=provider) for item in results]


def _youtube_items(query, keywords=(), seeds=(), max_results=3):
    """Judul tren YouTube sebagai item tanpa URL (fallback lokal)."""
    try:
        from utils.scraper import get_topic_trends
    except ImportError:
        return []
    try:
        titles = get_topic_trends(
            query,
            keywords=keywords,
            seed_topics=seeds,
            max_results=max_results,
        )
    except Exception:
        return []
    items = []
    for title in titles:
        title = str(title).strip()
        if title:
            items.append({
                "source_id": _stable_id(None, title),
                "url": None,
                "title": _truncate(title, 200),
                "publisher": "YouTube",
                "source_type": "youtube",
                "published_date": None,
                "retrieved_at": _iso_now(),
                "claim": _truncate(title, 300),
                "status": "unverified",
            })
    return items


def _seed_items(account, query):
    """Item dari `seed_topics` akun; jalan terakhir bila semua sumber gagal."""
    seeds = (account or {}).get("seed_topics") or []
    topics = [str(s).strip() for s in seeds if str(s).strip()] or [str(query or "").strip()]
    return [
        {
            "source_id": _stable_id(None, topic),
            "url": None,
            "title": _truncate(topic, 200),
            "publisher": None,
            "source_type": "seed",
            "published_date": None,
            "retrieved_at": _iso_now(),
            "claim": _truncate(topic, 300),
            "status": "unverified",
        }
        for topic in topics if topic
    ]


def _dedupe(items):
    seen, unique = set(), []
    for item in items:
        key = (item.get("url") or item.get("title") or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _rank(items):
    """Mengurutkan: ber-URL lebih dulu, lalu yang punya tanggal, lalu posisi."""

    def score(item):
        has_url = 0 if item.get("url") else 1
        has_date = 0 if item.get("published_date") else 1
        position = item.get("position") if isinstance(item.get("position"), int) else 99
        return (has_url, has_date, position)

    return sorted(items, key=score)


def build_research(query, *, account=None, max_results=5, top_n=5,
                   ninerouter_url=None, ninerouter_key=None):
    """Membangun paket riset dengan fallback berlapis.

    Urutan penyedia: 9Router web search -> tren YouTube -> seed_topics.
    Selalu mengembalikan dict (tidak pernah memakai raise Error), sehingga
    panggilan riset aman dipakai di jalur produksi konten.
    """
    providers_tried = []
    error = None
    items = []
    try:
        items = search_web(
            query,
            max_results=max_results,
            url=ninerouter_url,
            key=ninerouter_key,
        )
        providers_tried.append("ninerouter")
    except ResearchError as exc:
        error = str(exc)

    used_fallback = bool(error) or not items
    if not items:
        items = _youtube_items(
            query,
            keywords=(account or {}).get("keywords", []),
            seeds=(account or {}).get("seed_topics", []),
            max_results=max_results,
        )
    if not items:
        items = _seed_items(account, query)

    items = _dedupe(items)
    items = _rank(items)[:top_n]

    return {
        "query": query,
        "build_at": _iso_now(),
        "items": items,
        "providers_tried": providers_tried,
        "used_fallback": used_fallback,
        "error": error,
        "account": (account or {}).get("id"),
    }


def mark_status(pack, status):
    """Menetapkan status fact-check untuk seluruh item dalam paket.

    Dipakai alur MLBB setelah reviewer memastikan klaim: patch/hasil wajib
    punya sumber, lalu paket ditandai `verified` sebelum dirender final.
    """
    if status not in ITEM_STATUSES:
        raise ValueError(f"Status tidak dikenal: {status}")
    updated = dict(pack)
    updated["items"] = [dict(item, status=status) for item in pack.get("items", [])]
    return updated


def to_content_plan_research(pack, *, required=False, max_sources=5):
    """Menyusun blok `research` yang siap dimasukkan ke content plan.

    Konsisten dengan validator (utils/content_plan): bila ada sumber maka
    fact_check_status bukan `pending` lagi, tapi `unverified` (masih perlu
    review) atau `verified` (semua item ber-URL + tanggal).
    """
    items = pack.get("items", [])[:max_sources]
    sources = []
    for item in items:
        sources.append({
            "source_id": item.get("source_id"),
            "url": item.get("url"),
            "title": item.get("title"),
            "publisher": item.get("publisher"),
            "published_date": item.get("published_date"),
            "retrieved_at": item.get("retrieved_at"),
            "claim": item.get("claim"),
            "status": item.get("status") or "unverified",
        })

    if not sources:
        status = "failed"
    elif all(s.get("status") == "verified" for s in sources):
        status = "verified"
    else:
        status = "unverified"

    return {
        "required": bool(required),
        "sources": sources,
        "checked_at": pack.get("build_at") or _iso_now(),
        "fact_check_status": status,
    }


def summarize(pack):
    """Ringkasan paket riset untuk log Telegram (cetak satu baris per sumber)."""
    items = pack.get("items", [])
    fallback = " (fallback)" if pack.get("used_fallback") else ""
    if not items:
        return "Riset: 0 sumber"
    lines = [f"Riset {len(items)} sumber{fallback}"]
    for item in items:
        line = f"- {item.get('title') or 'Tanpa judul'}"
        if item.get("url"):
            line = f"{line} ({item['url']})"
        if item.get("published_date"):
            line = f"{line} [{item['published_date']}]"
        lines.append(line)
    if pack.get("error"):
        lines.append(f"  catatan: {pack['error']}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Riset konten multi-sumber")
    parser.add_argument("query", help="permintaan/topik riset")
    parser.add_argument("--account", default=None, help="id akun (mlbb/wedding/... )")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--json-out", action="store_true", help="cetak tetap sebagai JSON")
    args = parser.parse_args()

    account = None
    if args.account:
        from utils import accounts
        account = accounts.find_account(args.account)
        if account is None:
            sys.exit(f"Akun tidak ditemukan: {args.account}")

    pack = build_research(
        args.query,
        account=account,
        max_results=args.max_results,
        top_n=args.top_n,
    )
    if args.json_out:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(to_content_plan_research(pack, required=True),
                         ensure_ascii=False, indent=2))
        print()
        print(summarize(pack))