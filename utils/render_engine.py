"""Pemilihan mesin render video (feature flag VIDEO_ENGINE).

legacy   -> renderer lama Pillow + FFmpeg di utils/video_maker.py (default,
            sudah teruji oleh test suite).
remotion -> render lewat GitHub Actions (workflow render.yml). Dispatch
            otomatis dari Python menyusul bersama timeline builder (Phase 8);
            sampai saat itu engine remotion menolak render lokal supaya tidak
            diam-diam memakai renderer legacy.
"""
import os

LEGACY = "legacy"
REMOTION = "remotion"
SUPPORTED = (LEGACY, REMOTION)


class RemotionLocalUnsupported(RuntimeError):
    """VIDEO_ENGINE=remotion diminta, tetapi dispatch belum tersedia dari Python."""


def video_engine(env=None):
    """Kembalikan mesin render yang sah atau raise bila konfigurasi tidak valid.

    `env` boleh dict (untuk test); default memakai os.environ.
    """
    source = os.environ if env is None else env
    value = (source.get("VIDEO_ENGINE") or "").strip().lower() or LEGACY
    if value not in SUPPORTED:
        raise ValueError(
            f"VIDEO_ENGINE tidak dikenal: {value!r} (harus legacy atau remotion)"
        )
    if value == REMOTION:
        raise RemotionLocalUnsupported(
            "VIDEO_ENGINE=remotion: render Remotion berjalan lewat GitHub Actions "
            "(.github/workflows/render.yml), bukan dari Python. Untuk render "
            "lokal pakai VIDEO_ENGINE=legacy."
        )
    return LEGACY
