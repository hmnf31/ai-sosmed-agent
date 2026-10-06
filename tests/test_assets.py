"""Image Asset Generator: prompt, generate, normalisasi, QA, manifest, fallback."""
import io
import json
import os
import tempfile

import pytest
from PIL import Image, ImageDraw

from utils import assets


def plan_fixture(scenes=None, width=1080, height=1920):
    scenes = scenes or [
        {
            "scene_id": "scene_01",
            "duration_sec": 15,
            "purpose": "hook",
            "visual_type": "image",
            "visual_prompt": "hero melambai di arena",
            "on_screen_text": "PATCH BARU",
        }
    ]
    return {
        "schema_version": "1.0",
        "job_id": "job_0001",
        "account": "mlbb",
        "content_type": "patch_update",
        "format": "vertical_short",
        "language": "id-ID",
        "aspect_ratio": "9:16",
        "width": width,
        "height": height,
        "fps": 30,
        "target_duration_sec": 15,
        "scenes": scenes,
        "branding": {"profile": "mlbb", "template_id": "mlbb_patch",
                     "watermark_variant": "primary"},
    }


def gradient_png_bytes(width=800, height=1200):
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        tone = int(255 * y / max(1, height - 1))
        draw.line([(0, y), (width, y)], fill=(tone, 60, 200 - tone))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def load_schema():
    with open("data/schemas/asset_manifest_schema.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_manifest(manifest):
    import jsonschema
    jsonschema.validate(manifest, load_schema())


class TestBuildPrompt:
    def test_menyertakan_visual_prompt_dan_gaya_brand(self):
        brand = {
            "identity": {
                "image_style": "esports_arena",
                "visual_mood": ["energik", "tegas"],
            },
            "colors": {"primary": "#00B8D4", "background": "#0A0E17"},
        }
        prompt = assets.build_asset_prompt(plan_fixture()["scenes"][0], account="mlbb", brand=brand)
        assert "hero melambai di arena" in prompt
        assert "esports_arena" in prompt
        assert "energik" in prompt
        assert "#00B8D4" in prompt
        assert "Tanpa teks" in prompt
        assert "watermark" in prompt

    def test_teks_layar_tidak_masuk_prompt(self):
        scene = plan_fixture()["scenes"][0]
        assert "PATCH BARU" not in assets.build_asset_prompt(scene)

    def test_tanpa_brand_tetap_menghasilkan_prompt(self):
        scene = plan_fixture()["scenes"][0]
        prompt = assets.build_asset_prompt(scene)
        assert prompt.startswith("hero melambai di arena")


class TestSizeDanQA:
    def test_target_size_dari_plan(self):
        assert assets.target_size(plan_fixture()) == (1080, 1920)

    def test_validate_assets_valid_untuk_tidak_polos(self, tmp_path):
        path = str(tmp_path / "ok.png")
        assets.placeholder_image(path, (1080, 1920), colors={"background": "#0A0E17", "accent": "#00B8D4"})
        assert assets.verify_asset(path, expected_size=(1080, 1920)) == []

    def test_validate_file_missing(self):
        problems = assets.verify_asset("tidak-ada.png", expected_size=(1080, 1920))
        assert any("tidak ada" in p for p in problems)

    def test_validate_file_kosong(self, tmp_path):
        path = str(tmp_path / "kosong.png")
        path_bytes = tmp_path / "kosong.png"
        path_bytes.write_bytes(b"")
        problems = assets.verify_asset(path)
        assert any("kosong" in p for p in problems)

    def test_validate_bukan_gambar(self, tmp_path):
        path = str(tmp_path / "bukan.png")
        path_bytes = tmp_path / "bukan.png"
        path_bytes.write_bytes(b"ini bukan gambar")
        problems = assets.verify_asset(str(path_bytes))
        assert any("tidak bisa dibuka" in p for p in problems)

    def test_validate_dimensi_salah(self, tmp_path):
        path = str(tmp_path / "kecil.png")
        assets.placeholder_image(path, (640, 640))
        problems = assets.verify_asset(path, expected_size=(1080, 1920))
        assert any("dimensi" in p for p in problems)

    def test_validate_gambar_polos(self, tmp_path):
        path = str(tmp_path / "polos.png")
        image = Image.new("RGB", (64, 64), (120, 120, 120))
        image.save(path, "PNG")
        problems = assets.verify_asset(path)
        assert any("polos" in p for p in problems)

    def test_normalisasi_diagram_rasio(self, tmp_path):
        src = tmp_path / "src.png"
        src.write_bytes(gradient_png_bytes(width=1920, height=1080))
        out = tmp_path / "final.png"
        size = assets.normalize_image(str(src), (1080, 1920), str(out))
        assert size == (1080, 1920)
        assert assets.verify_asset(str(out), expected_size=(1080, 1920)) == []


class TestManifest:
    def test_schema_valid_untuk_keseluruhan(self):
        manifest = assets.build_manifest(
            plan_fixture(),
            [{
                "asset_id": "asset_scene_01",
                "scene_id": "scene_01",
                "purpose": "hook",
                "path": "output/scene_01.png",
                "source_type": "ai_generated",
                "provider": "ag/gemini-3.1-flash-image",
                "prompt_version": "1",
                "width": 1080,
                "height": 1920,
                "status": "ready",
                "usage_rights": "review_required",
            }],
        )
        validate_manifest(manifest)
        assert manifest["job_id"] == "job_0001"
        assert manifest["assets"][0]["asset_id"] == "asset_scene_01"

    def test_schema_valid_fallback_dan_failed(self):
        manifest = assets.build_manifest(
            plan_fixture(),
            [
                {
                    "asset_id": "asset_scene_01", "scene_id": "scene_01", "purpose": "hook",
                    "path": "output/fallback.png", "source_type": "placeholder",
                    "width": 1080, "height": 1920, "status": "fallback", "usage_rights": "internal",
                },
                {
                    "asset_id": "asset_scene_02", "scene_id": "scene_02", "purpose": "body",
                    "path": None, "source_type": "placeholder", "width": None, "height": None,
                    "status": "failed", "error": "9Router tidak terjangkau",
                },
            ],
        )
        validate_manifest(manifest)

    def test_manifest_tidak_menyimpan_api_key(self):
        manifest = assets.build_manifest(
            plan_fixture(),
            [{
                "asset_id": "asset_scene_01", "scene_id": "scene_01", "purpose": "hook",
                "path": "output/scene_01.png", "source_type": "ai_generated",
                "provider": "ag/gemini-3.1-flash-image", "width": 1080, "height": 1920,
                "status": "ready", "usage_rights": "review_required",
            }],
        )
        blob = json.dumps(manifest)
        assert "sk-abc" not in blob
        assert "AIza" not in blob


class TestApplyManifest:
    def test_hanya_image_scene_diisi_asset_files(self):
        plan = plan_fixture(scenes=[
            {"scene_id": "scene_01", "visual_type": "image", "duration_sec": 5,
             "purpose": "hook", "visual_prompt": "x", "on_screen_text": ""},
            {"scene_id": "scene_02", "visual_type": "text", "duration_sec": 5,
             "purpose": "body", "visual_prompt": "y", "on_screen_text": "TEXT"},
        ])
        manifest = assets.build_manifest(plan, [
            {"asset_id": "asset_scene_01", "scene_id": "scene_01", "purpose": "hook",
             "path": "output/scene_01.png", "source_type": "ai_generated",
             "provider": "m", "width": 1080, "height": 1920, "status": "ready",
             "usage_rights": "review_required"},
        ])
        assets.apply_manifest(plan, manifest)
        assert plan["scenes"][0]["asset_files"] == ["output/scene_01.png"]
        assert plan["scenes"][1]["asset_files"] == []


class TestHTTP:
    def test_generate_post_ke_binary_endpoint(self, monkeypatch):
        captured = {}

        def fake_post(url, payload, headers=None, timeout=60):
            captured["url"] = url
            captured["payload"] = payload
            return gradient_png_bytes()

        monkeypatch.setattr(assets, "_post_bytes", fake_post)
        data = assets.generate_image_bytes("prompt tes", model="black-forest-labs/flux-pro", size="1024x1024")
        assert data
        assert "response_format=binary" in captured["url"]
        assert captured["payload"]["model"] == "black-forest-labs/flux-pro"
        assert captured["payload"]["prompt"] == "prompt tes"
        assert captured["payload"]["n"] == 1
        assert captured["payload"]["size"] == "1024x1024"

    def test_size_ditahan_untuk_model_gemini(self, monkeypatch):
        captured = {}

        def fake_post(url, payload, headers=None, timeout=60):
            captured["payload"] = payload
            return gradient_png_bytes()

        monkeypatch.setattr(assets, "_post_bytes", fake_post)
        assets.generate_image_bytes("p", model="gemini/gemini-2.5-flash-image", size="1024x1024")
        assert "size" not in captured["payload"]

    def test_list_image_models(self, monkeypatch):
        monkeypatch.setattr(
            assets, "_request_json",
            lambda *a, **k: {"data": [{"id": "a/model"}, {"id": "b/model"}]},
        )
        assert assets.list_image_models() == ["a/model", "b/model"]


class TestPipeline:
    def test_sukses_menghasilkan_manifest_ready(self, monkeypatch, tmp_path):
        monkeypatch.setattr(assets, "generate_image_bytes",
                            lambda *a, **k: gradient_png_bytes())
        out = str(tmp_path)
        manifest = assets.generate_assets(plan_fixture(), output_dir=out, model="ag/gemini-3.1-flash-image")
        validate_manifest(manifest)
        assert manifest["assets"][0]["status"] == "ready"
        assert manifest["assets"][0]["source_type"] == "ai_generated"
        path = manifest["assets"][0]["path"]
        assert os.path.exists(path)
        assert assets.verify_asset(path, expected_size=(1080, 1920)) == []
        assert (tmp_path / "asset_manifest.json").exists()

    def test_fallback_placeholder_saat_generator_gagal(self, monkeypatch, tmp_path):
        from utils import assets as assets_mod
        monkeypatch.setattr(assets_mod, "generate_image_bytes",
                            lambda *a, **k: (_ for _ in ()).throw(assets_mod.AssetError("9Router 503")))
        manifest = assets_mod.generate_assets(plan_fixture(), output_dir=str(tmp_path))
        assert manifest["assets"][0]["status"] == "fallback"
        assert manifest["assets"][0]["source_type"] == "placeholder"
        assert os.path.exists(manifest["assets"][0]["path"])
        validate_manifest(manifest)

    def test_retry_terbatas_dua_kali(self, monkeypatch):
        from utils import assets as assets_mod
        calls = {"n": 0}

        def flaky(*a, **k):
            calls["n"] += 1
            raise assets_mod.AssetError("sementara")

        against = tempfile.mkdtemp()
        monkeypatch.setattr(assets_mod, "generate_image_bytes", flaky)
        manifest = assets_mod.generate_assets(plan_fixture(), output_dir=against)
        assert calls["n"] == assets_mod.MAX_ATTEMPTS
        assert manifest["assets"][0]["status"] == "fallback"

    def test_failed_bila_fallback_pun_rusak(self, monkeypatch, tmp_path):
        from utils import assets as assets_mod
        monkeypatch.setattr(assets_mod, "generate_image_bytes",
                            lambda *a, **k: (_ for _ in ()).throw(assets_mod.AssetError("9Router 503")))
        monkeypatch.setattr(assets_mod, "placeholder_image",
                            lambda *a, **k: (_ for _ in ()).throw(assets_mod.AssetError("placeholder gagal")))
        manifest = assets_mod.generate_assets(plan_fixture(), output_dir=str(tmp_path))
        entry = manifest["assets"][0]
        assert entry["status"] == "failed"
        assert entry["path"] is None
        assert "fallback" in entry["error"]
        validate_manifest(manifest)

    def test_skip_scene_non_image(self, monkeypatch, tmp_path):
        from utils import assets as assets_mod
        plan = plan_fixture(scenes=[
            {"scene_id": "scene_01", "duration_sec": 5, "purpose": "body",
             "visual_type": "text", "visual_prompt": "t", "on_screen_text": "TEXT"},
        ])
        monkeypatch.setattr(assets_mod, "generate_image_bytes",
                            lambda *a, **k: (_ for _ in ()).throw(AssertionError("tidak boleh dipanggil")))
        manifest = assets_mod.generate_assets(plan, output_dir=str(tmp_path))
        assert manifest["assets"] == []
        validate_manifest(manifest)

    def test_sudah_tulis_manifest_ke_disk(self, monkeypatch, tmp_path):
        from utils import assets as assets_mod
        monkeypatch.setattr(assets_mod, "generate_image_bytes",
                            lambda *a, **k: gradient_png_bytes())
        assets_mod.generate_assets(plan_fixture(), output_dir=str(tmp_path))
        on_disk = json.loads((tmp_path / "asset_manifest.json").read_text(encoding="utf-8"))
        validate_manifest(on_disk)