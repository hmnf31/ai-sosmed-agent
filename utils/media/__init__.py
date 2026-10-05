"""Lapisan media: kanvas, layout, template, dan watermark.

Renderer lama di `utils/image_maker.py` dan `utils/video_maker.py` memakai
package ini sebagai satu-satunya sumber kebenaran visual. Import dari sini,
bukan langsung ke modul internal, supaya urutan dan nama tetap stabil.
"""
from utils.media import asset_loader, layout_engine, template_engine, watermark_engine

__all__ = [
    "asset_loader",
    "layout_engine",
    "template_engine",
    "watermark_engine",
    "render_card",
    "render_frames",
]


def render_card(*args, **kwargs):
    return template_engine.render_card(*args, **kwargs)


def render_frames(*args, **kwargs):
    return template_engine.render_frames(*args, **kwargs)
