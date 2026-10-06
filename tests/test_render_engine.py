"""Feature flag VIDEO_ENGINE (legacy|remotion) — utils/render_engine.py."""
import pytest

from utils import render_engine, video_maker


def test_default_engine_is_legacy():
    assert render_engine.video_engine({}) == "legacy"


def test_env_legacy():
    assert render_engine.video_engine({"VIDEO_ENGINE": "legacy"}) == "legacy"


def test_env_blank_falls_back_to_legacy():
    assert render_engine.video_engine({"VIDEO_ENGINE": "   "}) == "legacy"


def test_unknown_value_rejected():
    with pytest.raises(ValueError, match="VIDEO_ENGINE"):
        render_engine.video_engine({"VIDEO_ENGINE": "pillow"})


def test_remotion_flag_refuses_local_render():
    with pytest.raises(render_engine.RemotionLocalUnsupported, match="render.yml"):
        render_engine.video_engine({"VIDEO_ENGINE": "remotion"})


def test_render_content_video_refuses_remotion(monkeypatch):
    monkeypatch.setenv("VIDEO_ENGINE", "remotion")
    with pytest.raises(render_engine.RemotionLocalUnsupported):
        video_maker.render_content_video({"title": "judul", "points": []})


def test_render_trend_video_refuses_remotion(monkeypatch):
    monkeypatch.setenv("VIDEO_ENGINE", "remotion")
    with pytest.raises(render_engine.RemotionLocalUnsupported):
        video_maker.render_trend_video([{"name": "topik"}])
