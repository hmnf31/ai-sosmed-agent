"""Validasi content plan: schema jsonschema + aturan semantik."""
import pytest

from utils import content_plan


def valid_plan():
    return {
        "schema_version": "1.0",
        "job_id": "job_0001",
        "account": "mlbb",
        "content_type": "hero_explainer",
        "format": "vertical_short",
        "language": "id-ID",
        "aspect_ratio": "9:16",
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "target_duration_sec": 30,
        "title": "Jungler Pemula",
        "hook": "Jangan asal rusuh buff",
        "caption": "Tiga fondasi jungler untuk pemula.",
        "hashtags": ["#MLBB", "#tipsmlbb"],
        "research": {
            "required": False,
            "sources": [],
            "checked_at": None,
            "fact_check_status": "pending",
        },
        "voiceover": {
            "enabled": True,
            "provider": None,
            "segments": [
                {"segment_id": "vo_01", "text": "Narasi pembuka",
                 "estimated_duration_sec": 4.0},
            ],
        },
        "scenes": [
            {
                "scene_id": "scene_01",
                "duration_sec": 6,
                "purpose": "hook",
                "visual_type": "image",
                "visual_prompt": "visual orisinal jungler",
                "on_screen_text": "JUNGLER",
                "voiceover_segment_ids": ["vo_01"],
            },
            {
                "scene_id": "scene_02",
                "duration_sec": 6,
                "purpose": "body",
                "visual_type": "image",
                "visual_prompt": "visual rotasi",
                "on_screen_text": "ROTASI",
            },
            {
                "scene_id": "scene_03",
                "duration_sec": 6,
                "purpose": "body",
                "visual_type": "image",
                "visual_prompt": "visual farm",
                "on_screen_text": "FARM",
            },
            {
                "scene_id": "scene_04",
                "duration_sec": 6,
                "purpose": "body",
                "visual_type": "image",
                "visual_prompt": "visual hero",
                "on_screen_text": "HERO",
            },
            {
                "scene_id": "scene_05",
                "duration_sec": 6,
                "purpose": "outro",
                "visual_type": "image",
                "visual_prompt": "visual cta",
                "on_screen_text": "IKUTI",
            },
        ],
        "branding": {
            "profile": "mlbb",
            "template_id": "mlbb_vertical_hook",
            "watermark_variant": "primary",
        },
    }


def test_valid_plan_passes():
    assert content_plan.validate(valid_plan()) == []
    assert content_plan.assert_valid(valid_plan())["job_id"] == "job_0001"


def test_invalid_account_rejected():
    plan = valid_plan()
    plan["account"] = "tiktoker"
    problems = content_plan.validate(plan)
    assert any("account" in p for p in problems)


def test_account_mismatch_branding():
    plan = valid_plan()
    plan["account"] = "wedding"
    plan["branding"]["profile"] = "mlbb"
    problems = content_plan.validate(plan)
    assert any("account" in p and "branding" in p for p in problems)


def test_scene_references_missing_voiceover():
    plan = valid_plan()
    plan["scenes"][0]["voiceover_segment_ids"] = ["vo_99"]
    problems = content_plan.validate(plan)
    assert any("vo_99" in p for p in problems)


def test_duration_far_from_target():
    plan = valid_plan()
    plan["target_duration_sec"] = 300
    plan["scenes"] = plan["scenes"][:1]
    problems = content_plan.validate(plan)
    assert any("durasi" in p for p in problems)


def test_pixel_size_mismatch_aspect_ratio():
    plan = valid_plan()
    plan["width"] = 1080
    plan["height"] = 1080
    problems = content_plan.validate(plan)
    assert any("aspect_ratio" in p for p in problems)


def test_format_mismatch_aspect_ratio():
    square = valid_plan()
    square["format"] = "square"
    square["aspect_ratio"] = "1:1"
    square["width"] = 1080
    square["height"] = 1080
    square["target_duration_sec"] = 18
    square["scenes"] = square["scenes"][:3]
    assert content_plan.validate(square) == []

    bad = valid_plan()
    bad["format"] = "square"
    problems = content_plan.validate(bad)  # 9:16 dipakai untuk square
    assert any("format" in p for p in problems)


def test_duplicate_scene_id_rejected():
    plan = valid_plan()
    plan["scenes"][1]["scene_id"] = "scene_01"
    problems = content_plan.validate(plan)
    assert any("scene_id" in p for p in problems)


def test_duplicate_segment_id_rejected():
    plan = valid_plan()
    plan["voiceover"]["segments"].append(
        {"segment_id": "vo_01", "text": "duplikat", "estimated_duration_sec": 1}
    )
    problems = content_plan.validate(plan)
    assert any("segment_id" in p for p in problems)


def test_unknown_field_rejected_by_schema():
    plan = valid_plan()
    plan["dimensi_ajaib"] = True
    problems = content_plan.validate(plan)
    assert any("dimensi_ajaib" in p for p in problems)


def test_research_required_but_no_sources():
    plan = valid_plan()
    plan["research"] = {
        "required": True,
        "sources": [],
        "checked_at": None,
        "fact_check_status": "pending",
    }
    problems = content_plan.validate(plan)
    assert any("sumber" in p for p in problems)


def test_sec_to_frames_rounds():
    assert content_plan.sec_to_frames(6, 30) == 180
    assert content_plan.sec_to_frames(4.5, 30) == 135


def test_duration_frames_sums_scenes():
    assert content_plan.duration_frames(valid_plan()) == 30 * 30


def test_assert_valid_raises_on_problems():
    bad = valid_plan()
    bad["account"] = "tiktoker"
    with pytest.raises(content_plan.ContentPlanValidationError, match="account"):
        content_plan.assert_valid(bad)