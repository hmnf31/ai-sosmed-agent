import re

from playwright.sync_api import sync_playwright

RSS_URL = "https://trends.google.com/trending/rss?geo={geo}"
LEGACY_URL = "https://trends.google.com/trends/trendingsearches/daily?geo={geo}"
ITEM_TITLE_RE = re.compile(r"<item>.*?<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", re.S)


def _extract_item_titles(html):
    return [title.strip() for title in ITEM_TITLE_RE.findall(html) if title.strip()]


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