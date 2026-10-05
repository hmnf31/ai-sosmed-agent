import os
import re
import time
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright

RSS_URL = "https://trends.google.com/trending/rss?geo={geo}"
LEGACY_URL = "https://trends.google.com/trends/trendingsearches/daily?geo={geo}"
ITEM_TITLE_RE = re.compile(r"<item>.*?<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", re.S)

YOUTUBE_SEARCH_URL = "https://www.youtube.com/results?search_query={query}&sp=CAI%253D"
YOUTUBE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
EXTRACT_VIDEOS_JS = r"""els => els.slice(0, 20).map(e => ({
    title: (e.querySelector('#video-title')?.textContent || '').trim(),
    meta: (e.querySelector('#metadata-line')?.textContent || '').replace(/\s+/g, ' ').trim()
}))"""

MLBB_KEYWORDS = (
    "mpl", "mlbb", "mobile legends", "evos", "rrq", "alter ego", "idolo", "ongko",
    "mip", "bren", "kagura", "ling", "esport", "asian games", "aov",
)
HIGH_SIGNAL = (
    "mpl id", "mplid", "evos", "rrq", "alter ego", "idolo", "ongko", "bren",
    "asian games", "aov", "playoff", "bracket", "final", "grand final", " vs ",
    "world cup", "mpl season", "s1", "s2",
)
MLBB_DEFAULT_SEEDS = [
    "MPL ID Season terbaru",
    "RRQ vs EVOS",
    "Draft dan meta hero MPL ID",
    "Jadwal bracket MPL ID",
    "Tim esports Indonesia",
]
NOISE_PREFIXES = ("live", "live streaming", "streaming", "video", "official")
UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9\s+#&.,:;'!?()\-/]")


def _extract_item_titles(html):
    return [title.strip() for title in ITEM_TITLE_RE.findall(html) if title.strip()]


def clean_title(title):
    """Membuang emoji, badge live, dan karakter yang tidak bisa dirender font."""
    text = UNSAFE_CHARS.sub("", title)
    text = re.sub(r"^\s*(?:\[[^\]]*\]|\([^)]*\))\s*", "", text)
    text = re.sub(r"\b(?:%s)\b\s*[:|-]*\s*" % "|".join(NOISE_PREFIXES), "", text, flags=re.I)
    text = re.sub(r"\s*\|\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|:")
    return text


def _dedupe(items):
    seen, unique = set(), []
    for item in items:
        key = item.lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _relevance(title, keywords=()):
    """Skor sederhana: judul yang menyebut kata kunci niche naik ke atas."""
    low = title.lower()
    tokens = tuple(keywords) or MLBB_KEYWORDS + HIGH_SIGNAL
    score = sum(1 for token in tokens if token in low)
    return score


def _scrape_youtube(query):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=YOUTUBE_USER_AGENT)
            page.goto(YOUTUBE_SEARCH_URL.format(query=quote_plus(query)), timeout=60000,
                      wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            videos = page.eval_on_selector_all("ytd-video-renderer", EXTRACT_VIDEOS_JS)
        finally:
            browser.close()
    return [clean_title(v["title"]) for v in videos if v.get("title")]


def get_google_trends(geo="ID", max_results=3):
    """Mengambil tren harian dari Google Trends menggunakan Playwright."""
    rss_url = RSS_URL.format(geo=geo)
    legacy_url = LEGACY_URL.format(geo=geo)
    print(f"[SCRAPER] Membuka {rss_url}...")

    trends = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Jalur utama: feed RSS resmi Google Trends (stabil terhadap redesign UI).
            page.goto(rss_url, timeout=30000)
            trends = _extract_item_titles(page.content())

            # Jalur cadangan: DOM halaman lama kalau feed RSS tidak menghasilkan judul.
            if not trends:
                page.goto(legacy_url, timeout=30000)
                page.wait_for_selector(".trend-title", timeout=10000)
                trends = page.eval_on_selector_all(
                    ".trend-title",
                    "elements => elements.map(e => e.innerText.trim())",
                )

            browser.close()
    except Exception as e:
        print(f"[SCRAPER ERROR] Gagal mengambil tren: {e}")
        trends = []

    result = trends[:max_results] if trends else ["Teknologi AI", "Otomatisasi Digital"]
    print(f"[SCRAPER] Berhasil mendapatkan tren: {result}")
    return result


def get_topic_trends(query, keywords=(), seed_topics=(), max_results=3):
    """Mengambil topik panas dari video YouTube terbaru untuk query bebas.

    Dipakai semua niche: MLBB, wedding, kuliner, dan lainnya.
    """
    query = (query or "").strip() or "tren indonesia"
    url = YOUTUBE_SEARCH_URL.format(query=quote_plus(query))
    print(f"[SCRAPER] Membuka {url}...")

    titles = []
    for attempt in (1, 2):
        try:
            titles = _scrape_youtube(query)
            if titles:
                break
            print(f"[SCRAPER] Percobaan {attempt}: judul video tidak ditemukan, mencoba lagi.")
        except Exception as e:
            print(f"[SCRAPER ERROR] Gagal mengambil tren dari YouTube: {e}")
        if attempt == 1:
            time.sleep(5)

    titles = [t for t in _dedupe(titles) if len(t) > 8]
    titles.sort(key=lambda t: _relevance(t, keywords), reverse=True)

    if not titles:
        seeds = [s.strip() for s in seed_topics if s and s.strip()]
        titles = seeds or [query.title()]
        print("[SCRAPER] Fallback ke daftar topik seed.")

    result = titles[:max_results]
    print(f"[SCRAPER] Topik: {result}")
    return result


def get_mlbb_trends(max_results=3, query=None):
    """Topik panas MLBB dari video YouTube terbaru."""
    return get_topic_trends(
        query or os.getenv("MLBB_YOUTUBE_QUERY") or "mobile legends indonesia",
        keywords=MLBB_KEYWORDS + HIGH_SIGNAL,
        seed_topics=[
            s.strip()
            for s in (os.getenv("MLBB_SEED_TOPICS") or ",".join(MLBB_DEFAULT_SEEDS)).split(",")
            if s.strip()
        ],
        max_results=max_results,
    )


def get_trends(niche="general", max_results=3):
    """Pemilih sumber tren berdasarkan niche konten."""
    if niche == "mlbb":
        return get_mlbb_trends(max_results=max_results)
    return get_google_trends(max_results=max_results)