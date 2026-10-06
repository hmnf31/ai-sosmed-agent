"""Research adapter: normalisasi sumber, tanggal, status fact-check, fallback."""
import pytest

from utils import content_plan
from utils import research


def fake_result(**overrides):
    base = {
        "title": "Judul Berita MPL",
        "url": "https://contoh-gaming.id/artikel-mpl",
        "snippet": "Berita singkat tentang hasil pertandingan.",
        "published_at": "2026-10-05",
        "position": 1,
        "score": 0.92,
        "metadata": {"source_type": "news"},
        "citation": {"provider": "tavily", "retrieved_at": "2026-10-06T08:00:00+07:00"},
    }
    base.update(overrides)
    return base


def valid_plan_with_research(research_block):
    return {
        "schema_version": "1.0",
        "job_id": "job_0001",
        "account": "mlbb",
        "content_type": "patch_update",
        "format": "vertical_short",
        "language": "id-ID",
        "aspect_ratio": "9:16",
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "target_duration_sec": 15,
        "scenes": [
            {
                "scene_id": "scene_01",
                "duration_sec": 15,
                "purpose": "body",
                "visual_type": "image",
                "visual_prompt": "visual patch",
                "on_screen_text": "PATCH",
            }
        ],
        "branding": {"profile": "mlbb", "template_id": "mlbb_patch",
                     "watermark_variant": "primary"},
        "research": research_block,
    }


def test_normalize_item_maps_fields():
    item = research.normalize_item(fake_result())
    assert item["title"] == "Judul Berita MPL"
    assert item["url"] == "https://contoh-gaming.id/artikel-mpl"
    assert item["published_date"] == "2026-10-05"
    assert item["status"] == "verified"
    assert item["publisher"] == "contoh-gaming.id"
    assert item["source_type"] == "news"
    assert item["source_id"].startswith("src_")


def test_normalize_with_metadata_title():
    item = research.normalize_item({"title": "", "metadata": {"title": "judul meta"}})
    assert item["title"] == "judul meta"


def test_normalize_missing_url_is_unverified():
    item = research.normalize_item({"title": "Tanpa URL"})
    assert item["url"] is None
    assert item["status"] == "unverified"
    assert item["source_type"] == "youtube"


def test_normalize_cuts_long_claim():
    item = research.normalize_item(fake_result(snippet="x" * 500))
    assert len(item["claim"]) <= 300


def test_clean_url_rejects_non_http():
    assert research.clean_url("tel:555") is None
    assert research.clean_url("www.tanpa-http.com") is None
    assert research.clean_url("Lihat https://a.co/x yuk").startswith("https://")
    assert research.clean_url("[teks](https://a.co/x)") == "https://a.co/x"


def test_parse_date_iso():
    assert research.parse_date("2026-10-06") == "2026-10-06"
    assert research.parse_date("2026-10-06T08:00:00+07:00") == "2026-10-06"


def test_parse_date_news_and_indonesian():
    assert research.parse_date("06-10-2026") == "2026-10-06"
    assert research.parse_date("6 Oktober 2026") == "2026-10-06"
    assert research.parse_date("Oct 6, 2026") == "2026-10-06"


def test_parse_date_invalid_returns_none():
    assert research.parse_date("kemarin sore") is None
    assert research.parse_date(None) is None


def test_stable_id_consistent():
    a = research._stable_id("https://x.id/a", "judul")
    b = research._stable_id("https://x.id/a", "judul")
    assert a == b
    no_url = research._stable_id(None, "judul saja")
    assert no_url.startswith("src_")


def test_search_web_posts_payload_and_normalizes(monkeypatch):
    captured = {}

    def fake_request(url, *, method="GET", payload=None, headers=None, timeout=20):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return {"provider": "tavily", "results": [fake_result()]}

    monkeypatch.setattr(research, "_request_json", fake_request)
    items = research.search_web("patch MPL terbaru", model="tavily/search",
                                max_results=5, url="http://router:20128", key="k")
    assert captured["url"] == "http://router:20128/v1/search"
    assert captured["payload"]["model"] == "tavily/search"
    assert captured["payload"]["query"] == "patch MPL terbaru"
    assert captured["headers"]["Authorization"] == "Bearer k"
    assert items[0]["status"] == "verified"


def test_search_web_picks_default_model(monkeypatch):
    captured = {}

    def fake_models(url=None, key=None, timeout=8):
        return {"search": ["tavily/search"], "fetch": []}

    def fake_request(url, *, method="GET", payload=None, headers=None, timeout=20):
        captured["model"] = payload["model"]
        return {"results": [fake_result(url="https://x.id/1")]}

    monkeypatch.setattr(research, "list_web_models", fake_models)
    monkeypatch.setattr(research, "_request_json", fake_request)
    research.search_web("query")
    assert captured["model"] == "tavily/search"


def test_search_web_raises_when_no_models(monkeypatch):
    monkeypatch.setattr(research, "list_web_models", lambda **k: {"search": [], "fetch": []})
    with pytest.raises(research.ResearchError, match="tidak punya model"):
        research.search_web("query")


def test_request_raises_research_error(monkeypatch):
    import urllib.error
    import urllib.request

    def boom(request, timeout=None):
        raise urllib.error.URLError("hub hilang")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(research.ResearchError, match="tidak terjangkau"):
        research._request_json("http://router/v1/any")


def test_build_research_prefers_web_and_falls_back(monkeypatch):
    monkeypatch.setattr(
        research, "search_web",
        lambda *a, **k: [fake_result(url="https://x.id/1", title="Sumber web")],
    )
    pack = research.build_research("patch MLBB", account={"id": "mlbb"})
    assert pack["used_fallback"] is False
    assert pack["providers_tried"] == ["ninerouter"]
    assert pack["items"][0]["url"] == "https://x.id/1"


def test_build_research_falls_back_to_youtube(monkeypatch):
    def failing(*a, **k):
        raise research.ResearchError("9Router tidak terjangkau")

    monkeypatch.setattr(research, "search_web", failing)
    monkeypatch.setattr(research, "_youtube_items", lambda *a, **k: [
        {"source_id": "src_a", "url": None, "title": "Tren YouTube",
         "source_type": "youtube", "status": "unverified"},
    ])
    pack = research.build_research("tren", account={"id": "mlbb"})
    assert pack["used_fallback"] is True
    assert pack["error"] is not None
    assert pack["items"][0]["title"] == "Tren YouTube"


def test_build_research_seed_is_last_resort(monkeypatch):
    monkeypatch.setattr(research, "search_web", lambda *a, **k: (_ for _ in ()).throw(
        research.ResearchError("gagal")))
    monkeypatch.setattr(research, "_youtube_items", lambda *a, **k: [])
    pack = research.build_research(
        "ide", account={"id": "wedding", "seed_topics": ["Ide pernikahan minimalis"]}
    )
    assert pack["items"][0]["title"] == "Ide pernikahan minimalis"


def test_build_research_dedupes_and_trims_to_top_n(monkeypatch):
    items = [fake_result(url="https://x.id/same", title=f"dup-{i}") for i in range(3)]
    monkeypatch.setattr(research, "search_web", lambda *a, **k: items)
    pack = research.build_research("q", top_n=2)
    assert len(pack["items"]) <= 2


def test_to_content_plan_research_status_rules():
    verified = [{"source_id": "a", "status": "verified"}]
    assert research.to_content_plan_research({"items": verified})["fact_check_status"] == "verified"

    mixed = [{"source_id": "a", "status": "verified"}, {"source_id": "b", "status": "unverified"}]
    assert research.to_content_plan_research({"items": mixed})["fact_check_status"] == "unverified"

    empty = research.to_content_plan_research({"items": []})
    assert empty["fact_check_status"] == "failed"
    assert empty["sources"] == []


def test_content_plan_research_validates_against_schema():
    pack = {
        "build_at": "2026-10-06T09:00:00+07:00",
        "items": [research.normalize_item(fake_result())],
    }
    research_block = research.to_content_plan_research(pack, required=True)
    plan = valid_plan_with_research(research_block)
    assert plan["research"]["fact_check_status"] == "verified"
    assert content_plan.validate(plan) == []


def test_mark_status_updates_items():
    pack = {"items": [fake_result()]}
    updated = research.mark_status(pack, "verified")
    assert updated["items"][0]["status"] == "verified"
    with pytest.raises(ValueError, match="Status tidak dikenal"):
        research.mark_status(pack, "hoki")


def test_summarize_includes_urls_and_dates():
    pack = {
        "items": [research.normalize_item(fake_result())],
        "used_fallback": False,
    }
    text = research.summarize(pack)
    assert "Riset 1 sumber" in text
    assert "https://contoh-gaming.id/artikel-mpl" in text
    assert "[2026-10-05]" in text


def test_summarize_empty():
    assert research.summarize({"items": [], "used_fallback": True}) == "Riset: 0 sumber"


def test_topics_from_pack_uses_titles_and_caps():
    pack = {"items": [
        {"title": "Topik A"},
        {"title": "Topik B"},
        {"title": "Topik C"},
        {"title": "Topik D"},
    ]}
    assert research.topics_from_pack(pack, max_results=3) == ["Topik A", "Topik B", "Topik C"]
    assert research.topics_from_pack({"items": []}, max_results=3) == []
    # Item tanpa judul diabaikan, bukan dikonversi jadi None.
    items = [{"title": "Ada"}, {"title": None}]
    assert research.topics_from_pack({"items": items}, max_results=3) == ["Ada"]