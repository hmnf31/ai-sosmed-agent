"""Validator content plan (Phase 4 Content Planner).

`content_plan.json` adalah hasil AI dan menjadi masukan seluruh pipeline
(asset, audio, timeline, renderer). Sebelum diproses lebih jauh, plan harus
lulus dua lapis pemeriksaan:

1. **Schema**: cocok dengan `data/schemas/content_plan_schema.json` lewat
   jsonschema (struktur, tipe, enum, referensi wajib).
2. **Semantik**: aturan yang tidak bisa dinyatakan schema — akun harus sama
   dengan branding, durasi scene kira-kira sama dengan target, referensi
   voiceover tidak boleh mengarah ke segmen yang tidak ada, dan rasio bingkai
   harus cocok dengan `aspect_ratio` dan `format`.

Mengikuti gaya `branding/validator.py`: fungsi mengembalikan daftar masalah,
daftar kosong berarti plan aman dipakai. Semua pesan dalam bahasa Indonesia.
"""
import json
import os

from jsonschema import Draft7Validator

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "schemas", "content_plan_schema.json",
)

#: Satu detik tambahan toleransi, lalu 10% dari durasi target.
DURATION_TOLERANCE_SEC = 1.0
DURATION_TOLERANCE_RATIO = 0.10

#: Kombinasi format -> kumpulan rasio yang wajar.
FORMAT_ASPECTS = {
    "vertical_short": {"9:16", "4:5"},
    "vertical_long": {"9:16", "4:5", "3:4"},
    "square": {"1:1"},
    "landscape": {"16:9", "4:3"},
    "youtube": {"16:9"},
}


class ContentPlanValidationError(ValueError):
    """Plan tidak valid; pesan berisi semua masalah yang ditemukan."""


def load_schema(path=None):
    """Memuat schema content plan dari berkas JSON."""
    target = path or SCHEMA_PATH
    with open(target, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sec_to_frames(seconds, fps):
    """Detik -> frame. Semua waktu render dikonversi ke frame menurut FPS."""
    return int(round(float(seconds) * float(fps)))


def duration_frames(plan):
    """Total durasi akhir plan dalam frame sesuai fps & target input."""
    fps = int(plan.get("fps") or 30)
    scenes = plan.get("scenes") or []
    return sum(sec_to_frames(s.get("duration_sec") or 0, fps) for s in scenes)


def _schema_problems(plan, schema):
    validator = Draft7Validator(schema)
    problems = []
    for error in sorted(validator.iter_errors(plan), key=lambda e: list(e.path)):
        problems.append(f"{error.json_path}: {error.message}")
    return problems


def _aspect_problems(plan):
    """Ukuran bingkai harus konsisten dengan aspect_ratio dan format."""
    problems = []
    width = plan.get("width")
    height = plan.get("height")
    aspect = plan.get("aspect_ratio")
    fmt = plan.get("format")

    if isinstance(width, int) and isinstance(height, int) and height:
        if aspect and ":" in str(aspect):
            try:
                ratio_w, ratio_h = (float(x) for x in str(aspect).split(":", 1))
            except ValueError:
                ratio_w, ratio_h = None, None
            if ratio_w:
                expected = ratio_w / ratio_h
                actual = width / height
                if abs(expected - actual) > 0.01:
                    problems.append(
                        f"ukuran {width}x{height} tidak cocok dengan aspect_ratio {aspect}"
                    )

    if fmt in FORMAT_ASPECTS and aspect not in FORMAT_ASPECTS[fmt]:
        problems.append(f"format '{fmt}' biasanya memakai rasio {sorted(FORMAT_ASPECTS[fmt])}, bukan '{aspect}'")
    return problems


def _semantic_problems(plan):
    problems = _aspect_problems(plan)

    account = plan.get("account")
    branding = plan.get("branding") or {}
    if account and branding.get("profile"):
        if account != branding["profile"]:
            problems.append(
                f"account '{account}' berbeda dengan branding.profile "
                f"'{branding['profile']}'"
            )

    if not plan.get("content_type"):
        problems.append("content_type harus diisi (misal hero_explainer, tips)")

    scenes = plan.get("scenes") or []
    scene_ids = [s.get("scene_id") for s in scenes if s.get("scene_id")]
    duplicates = sorted({sid for sid in scene_ids if scene_ids.count(sid) > 1})
    if duplicates:
        problems.append(f"scene_id tidak unik: {duplicates}")

    voiceover = plan.get("voiceover") or {}
    segments = voiceover.get("segments") or []
    segment_ids = [seg.get("segment_id") for seg in segments if seg.get("segment_id")]
    duplicate_segments = sorted({sid for sid in segment_ids if segment_ids.count(sid) > 1})
    if duplicate_segments:
        problems.append(f"voiceover.segments.segment_id tidak unik: {duplicate_segments}")

    known_segments = set(segment_ids)
    for seg in scenes:
        for ref in seg.get("voiceover_segment_ids") or []:
            if ref not in known_segments:
                problems.append(
                    f"scene {seg.get('scene_id')} merujuk voiceover '{ref}' yang tidak ada"
                )

    total = sum(float(s.get("duration_sec") or 0) for s in scenes)
    target = plan.get("target_duration_sec")
    if target is not None:
        tolerance = DURATION_TOLERANCE_SEC + float(target) * DURATION_TOLERANCE_RATIO
        if abs(total - float(target)) > tolerance:
            problems.append(
                f"total durasi scene {total:.1f}s jauh dari target {target:.1f}s"
            )

    research = plan.get("research") or {}
    if research.get("required") and not (research.get("sources") or []):
        problems.append("research.required=true tetapi tidak ada sumber riset")
    if research.get("fact_check_status") == "pending" and (research.get("sources") or []):
        problems.append("sumber sudah ada tetapi fact_check_status masih pending")

    return problems


def validate(plan, schema=None):
    """Semua masalah plan (schema + semantik). Kosong berarti valid."""
    schema_data = schema or load_schema()
    return _schema_problems(plan, schema_data) + _semantic_problems(plan)


def assert_valid(plan, schema=None):
    """Melempar ContentPlanValidationError bila plan tidak valid."""
    problems = validate(plan, schema=schema)
    if problems:
        raise ContentPlanValidationError("\n".join(problems))
    return plan