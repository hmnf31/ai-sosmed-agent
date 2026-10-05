"""Test PHASE 1A: Brand Profile, template, layout, dan watermark.

Yang diuji di sini bukanjordikiel gambar, tapi aturan yang harus dijaga:

- setiap akun punya identitas visual sendiri dan tidak tertukar;
- template yang dipilih selalu milik akun pemanggil;
- watermark benar-benar menempel dan selalu di dalam kanvas;
- akun tanpa profil tetap bisa render, tapi dilaporkan sebagai Gaul.
"""
import itertools
import json
import os

import pytest
from PIL import Image, ImageChops, ImageStat

from branding import loader, style_registry, validator, watermark
from utils.media import asset_loader, layout_engine, template_engine, watermark_engine

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNT_IDS = ("chess", "wedding", "mlbb", "fashion")

CONTENT = {
    "title": "Klasemen Liga TCO Putaran 7",
    "subtitle": "Selisih posisi pertama dan kedua cuma satu poin",
    "points": ["1. Bagas 12 poin", "2. Raka 11 poin", "3. Dimas 9 poin", "4. Yuda 8 poin"],
    "cta": "Ikuti update Liga TCO setiap Kamis",
}


@pytest.fixture(autouse=True)
def isolated_assets(tmp_path, monkeypatch):
    """Aset branding ditulis ke folder sementara, bukan ke repository."""
    target = str(tmp_path / "branding")
    monkeypatch.setattr(watermark, "ASSETS_DIR", target)
    monkeypatch.setattr(asset_loader, "BRAND_ROOT", target)
    loader.clear_cache()
    style_registry.clear_cache()
    yield target
    loader.clear_cache()
    style_registry.clear_cache()


def _profile(account_id):
    return loader.load_profile(account_id)


# ---------------------------------------------------------------------------
# Brand Profile
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("account_id", ACCOUNT_IDS)
def test_profile_lengkap_dan_valid(account_id):
    profile = _profile(account_id)
    assert profile["synthetic"] is False
    assert validator.validate_profile(profile) == []
    assert profile["account"] == account_id
    assert profile["colors"]["background"].startswith("#")


@pytest.mark.parametrize("account_id", ACCOUNT_IDS)
def test_setiap_akun_punya_warna_dan_mark_berbeda(account_id):
    profile = _profile(account_id)
    lain = [
        _profile(other) for other in ACCOUNT_IDS if other != account_id
    ]
    assert profile["colors"]["background"] not in [p["colors"]["background"] for p in lain]
    assert profile["mark"] in validator.KNOWN_MARKS
    assert len({p["mark"] for p in lain} | {profile["mark"]}) >= 2


def test_akun_tanpa_profile_masih_dapat_dan_ditandai():
    profile = loader.load_profile("akun_baru", account={"label": "Akun Baru",
                                                        "handle": "@akunbaru"})
    assert profile["synthetic"] is True
    assert profile["monogram"] == "AB"
    assert validator.validate_profile(profile) == []


def test_cache_tidak_bocor_antar_akun():
    """Dua akun yang berbagi id profil tidak boleh saling menimpa gaya tulis."""
    pertama = loader.brand_for({"id": "chess", "generation_style": {"tone": "ringkas"}})
    kedua = loader.brand_for({"id": "chess", "generation_style": {"tone": "penuh"}})
    assert pertama["generation_style"]["tone"] == "ringkas"
    assert kedua["generation_style"]["tone"] == "penuh"


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

def test_registry_tidak_punya_id_duplikat():
    assert style_registry.duplicate_ids() == []


@pytest.mark.parametrize("account_id", ACCOUNT_IDS)
@pytest.mark.parametrize("category", ["tren", "tips", "ootd", "liga_news", "tco_weekly"])
def test_template_selalu_milik_akun(account_id, category):
    template = style_registry.select_template(account_id, content_type=category,
                                             fmt="square")
    assert template.get("account") == account_id
    assert template.get("fallback")
    validator.assert_same_account(account_id, template=template, brand=_profile(account_id))


def test_kategori_aja_sudah_cukup_tanpa_format():
    template = style_registry.select_template("chess", content_type="liga_news", fmt=None)
    assert template["id"] == "chess_liga_news"


def test_template_kategori_tidak_dikenal_jatuh_ke_default_akun():
    template = style_registry.select_template("mlbb", content_type="kategori_ngawur",
                                             fmt="square")
    assert template["id"] == "mlbb_patch"
    assert template["fallback"] == "default-akun"


def test_akun_tanpa_template_pakai_generic():
    registry = {"generic": {"id": "generic_card", "account": None, "layout": "standard"},
                "defaults": {}, "templates": []}
    template = style_registry.select_template("mlbb", content_type="tips",
                                             registry=registry)
    assert template["id"] == "generic_card"
    assert template["fallback"] == "generic"


def test_template_akun_lain_ditolak():
    template = style_registry.select_template("wedding", content_type="tips", fmt="square")
    with pytest.raises(validator.BrandingMismatch):
        validator.assert_same_account("mlbb", template=template, brand=_profile("mlbb"))


def test_varian_watermark_asing_ditolak():
    with pytest.raises(validator.BrandingMismatch):
        validator.assert_same_account("chess", watermark="on_terang",
                                      brand=_profile("chess"))


# ---------------------------------------------------------------------------
# Kanvas dan layout
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fmt,size", [
    ("square", (1080, 1080)),
    ("portrait", (1080, 1350)),
    ("reel", (1080, 1920)),
])
def test_ukuran_kanvas(fmt, size):
    assert layout_engine.canvas_size(fmt) == size


def test_warna_terconvert_dengan_benar():
    assert layout_engine.hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert layout_engine.hex_to_rgb("fff") == (255, 255, 255)
    assert layout_engine.hex_to_rgb("bukan-warna") == (0, 0, 0)


def test_latar_terang_dan_gelap_terbaca():
    assert layout_engine.is_light_background(_profile("wedding")) is True
    assert layout_engine.is_light_background(_profile("chess")) is False


def test_limiter_poin_menyesuaikan_ruang():
    profil, style = _profile("chess"), loader.visual_style(_profile("chess"))
    width = layout_engine.resolve_canvas("square")["content_width"]
    assert layout_engine.fit_point_limit(profil, style, CONTENT["points"], width,
                                        available=10_000, hard_limit=4) == 4
    assert layout_engine.fit_point_limit(profil, style, CONTENT["points"], width,
                                        available=200, hard_limit=4) < 4


# ---------------------------------------------------------------------------
# Aset watermark
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("account_id", ACCOUNT_IDS)
@pytest.mark.parametrize("variant", ["primary", "on_light", "on_dark"])
def test_aset_watermark_terbuat(account_id, variant):
    path = watermark.build_watermark(account_id, variant)
    assert os.path.exists(path)
    with Image.open(path) as image:
        assert image.mode == "RGBA"
        assert image.size == (watermark.WATERMARK_WIDTH, watermark.WATERMARK_HEIGHT)
        assert image.getbbox() is not None


@pytest.mark.parametrize("account_id", ACCOUNT_IDS)
def test_logo_akun_tidak_sama(account_id):
    for other in ACCOUNT_IDS:
        watermark.build_logo(other)
    with Image.open(watermark.logo_path(account_id)) as image:
        pixels = image.convert("RGBA").tobytes()
    for other in ACCOUNT_IDS:
        if other == account_id:
            continue
        with Image.open(watermark.logo_path(other)) as image:
            assert image.convert("RGBA").tobytes() != pixels


def test_aset_dipakai_ulang_bila_sudah_ada(tmp_path, monkeypatch):
    watermark.build_watermark("chess", "primary")
    mtime = os.path.getmtime(watermark.watermark_path("chess", "primary"))
    watermark.ensure_watermark("chess", "primary")
    assert os.path.getmtime(watermark.watermark_path("chess", "primary")) == mtime


def test_varian_watermark_tidak_dikenal():
    with pytest.raises(ValueError):
        watermark.build_watermark("chess", "warna_lain")


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("account_id", ACCOUNT_IDS)
def test_kartu_ikut_brand_akun(account_id, tmp_path):
    profile = _profile(account_id)
    result = template_engine.render_card(CONTENT, profile, output_dir=str(tmp_path),
                                         category="liga_news", fmt="square")
    assert result["watermark"]["applied"] is True
    assert result["problems"] == []
    ok, size, expected = layout_engine.media_size_ok(result["path"], "square")
    assert ok, f"ukuran {size} bukan {expected}"

    with Image.open(result["path"]) as image:
        rgb = image.convert("RGB")
        mark = rgb.crop(box=[result["watermark"]["box"][0], result["watermark"]["box"][1],
                             result["watermark"]["box"][0] + result["watermark"]["box"][2],
                             result["watermark"]["box"][1] + result["watermark"]["box"][3]])
        assert mark.getbbox() is not None, "area watermark kosong"


def test_kartu_tiap_akun_berbeda_kasar(tmp_path):
    """Ciri visual tiap akun harus berbeda jauh, bukan sama-sama generik."""
    gambar = {}
    for account_id in ACCOUNT_IDS:
        result = template_engine.render_card(CONTENT, _profile(account_id),
                                             output_dir=str(tmp_path), fmt="square")
        with Image.open(result["path"]) as image:
            gambar[account_id] = image.convert("L").resize((64, 64))

    for kiri in ACCOUNT_IDS:
        for kanan in ACCOUNT_IDS:
            if kiri >= kanan:
                continue
            selisih = ImageChops.difference(gambar[kiri], gambar[kanan])
            histogram = selisih.histogram()
            rata = sum(i * jumlah for i, jumlah in enumerate(histogram)) / (64 * 64)
            assert rata > 8, f"{kiri} dan {kanan} terlalu mirip (rata {rata:.1f})"


def test_watermark_dipilih_sesuai_latar():
    assert watermark_engine.choose_variant(_profile("wedding")) == "on_light"
    assert watermark_engine.choose_variant(_profile("chess")) == "on_dark"


def test_watermark_selalu_di_dalam_kanvas():
    for account_id in ACCOUNT_IDS:
        for canvas in ("square", "portrait", "reel"):
            image = Image.new("RGB", layout_engine.canvas_size(canvas), (20, 20, 20))
            result = watermark_engine.apply(image, _profile(account_id), canvas)
            assert result["applied"] is True
            assert watermark_engine.audit(image, result, _profile(account_id)) == []


def test_watermark_menghormati_posisi_kiri_atas():
    image = Image.new("RGB", layout_engine.canvas_size("square"), (20, 20, 20))
    profile = _profile("chess")
    profile["watermark"] = dict(profile["watermark"], position="top_left", margin=80)
    result = watermark_engine.apply(image, profile, "square")
    x, y, width, height = result["box"]
    assert x == 80 and y == 80


def test_render_kartu_akun_tanpa_profile_tetap_jalan(tmp_path):
    profile = loader.load_profile("akun_baru", account={"label": "Akun Baru"})
    result = template_engine.render_card(CONTENT, profile, output_dir=str(tmp_path),
                                         fmt="square")
    assert os.path.exists(result["path"])
    assert any("gaya generik" in p for p in result["problems"])


def test_poin_berlebih_dilaporkan_bukan_diam_diam(tmp_path):
    content = dict(CONTENT, points=[f"Poin nomor {i}" for i in range(1, 8)])
    result = template_engine.render_card(content, _profile("chess"),
                                         output_dir=str(tmp_path), fmt="square")
    assert any("poin" in problem for problem in result["problems"])


def test_judul_terlalu_panjang_dilaporkan(tmp_path):
    result = template_engine.render_card(
        dict(CONTENT, title="Judul yang sangat panjang sekali dan tidak mungkin muat "
                            "dalam empat baris pendek karenaKalimatnya panjang"),
        _profile("mlbb"), output_dir=str(tmp_path), fmt="square")
    assert any("terpotong" in problem for problem in result["problems"])


@pytest.mark.parametrize("account_id", ACCOUNT_IDS)
def test_frame_video_vertical(account_id, tmp_path):
    result = template_engine.render_frames(CONTENT, _profile(account_id),
                                           output_dir=str(tmp_path))
    assert len(result["paths"]) == 3
    for path in result["paths"]:
        ok, size, expected = layout_engine.media_size_ok(path, "reel")
        assert ok, f"ukuran {size} bukan {expected}"


def test_frame_kosong_tetap_valid(tmp_path):
    result = template_engine.render_frames({"title": "Hanya judul"}, _profile("wedding"),
                                           output_dir=str(tmp_path))
    assert len(result["paths"]) == 3
    assert result["problems"] == []


# ---------------------------------------------------------------------------
# QA render
# ---------------------------------------------------------------------------

def test_verify_render_menangkap_ukuran_salah(tmp_path):
    result = template_engine.render_card(CONTENT, _profile("chess"),
                                         output_dir=str(tmp_path), fmt="square")
    profile = _profile("chess")
    assert validator.verify_render(result["path"], "chess", brand=profile,
                                   expected_size=(1080, 1080)) == []
    masalah = validator.verify_render(result["path"], "chess", brand=profile,
                                      expected_size=(1080, 1920))
    assert masalah and "ukuran" in masalah[0]


def test_verify_render_menangkap_akun_salah(tmp_path):
    template_engine.render_card(CONTENT, _profile("chess"), output_dir=str(tmp_path),
                                fmt="square")
    hasil = str(tmp_path / os.listdir(tmp_path)[0])
    template = style_registry.select_template("mlbb", content_type="tips", fmt="square")
    masalah = validator.verify_render(hasil, "wedding", template=template,
                                      brand=_profile("wedding"))
    assert masalah and "template" in masalah[0]


def test_video_menghormati_content_output_dir(monkeypatch, tmp_path):
    from utils import video_maker

    target = tmp_path / "keluaran"
    monkeypatch.setenv("CONTENT_OUTPUT_DIR", str(target))
    monkeypatch.setattr(video_maker, "_compose", lambda frames, out: _touch(out))

    hasil = video_maker.render_content_video(CONTENT, brand=_profile("mlbb"))

    assert os.path.dirname(hasil) == str(target)
    assert hasil.endswith(".mp4")
    assert not os.path.exists(os.path.join(video_maker.OUTPUT_DIR, os.path.basename(hasil)))


def _touch(path):
    with open(path, "wb") as handle:
        handle.write(b"\x00")
    return path


def test_isi_mentah_brand_json_dikenali_sebagai_profile():
    """Isi file brand.json apa adanya harus jadi profile, bukan dict akun.

    Kalau salah dikira dict akun, hasilnya profil generik: tanpa warna akun,
    tanpa watermark akun, dan QA tidak bisa menemukan bedanya.
    """
    with open(os.path.join(ROOT, "branding", "mlbb", "brand.json"), encoding="utf-8") as handle:
        mentah = json.load(handle)

    assert loader.is_profile(mentah)
    profile = asset_loader.brand_of(mentah)

    assert profile["style"]["id"] == mentah["style_preset"]
    assert profile["colors"]["background"] == mentah["colors"]["background"]
    assert profile["watermark"].get("position")
    assert "style" not in mentah, "dict sumber tidak boleh ikut berubah"


def test_brand_of_menerima_beberapa_bentuk():
    assert asset_loader.brand_of({"id": "mlbb"})["style"]["id"] == "mlbb_esports"
    assert asset_loader.brand_of("wedding")["style"]["id"] == "wedding_elegant"
    assert asset_loader.brand_of("wedding")["account_id"] == "wedding"
    assert asset_loader.brand_of({"id": "lain", "brand_profile": "fashion"})["style"]["id"] \
        == "fashion_editorial"
    assert asset_loader.brand_of("tidak-ada")["synthetic"] is True


def test_style_preset_konsisten_dengan_brand():
    for account_id in ACCOUNT_IDS:
        profile = _profile(account_id)
        style = loader.visual_style(profile)
        assert style["id"] == profile["style_preset"]
        assert style["canvas"]["background"] in layout_engine.BACKGROUND_TREATMENTS
        assert style["canvas"]["panel"] in layout_engine.PANEL_STYLES
        assert style["canvas"].get("texture") in layout_engine.TEXTURES


def test_empat_akun_terlihat_berbeda(tmp_path):
    """Empat kartu harus berbeda tanpa membaca teksnya.

    Dicek dengan selisih piksel rata-rata. Angkanya sengaja longgar: yang dicek
    adalah arah besar, bukan kesamaan persis, karena font dan subpixel rendering
    selalu menambah sedikit noise.
    """
    from utils.media import template_engine

    gambar = {}
    for account_id in ACCOUNT_IDS:
        hasil = template_engine.render_card(CONTENT, _profile(account_id),
                                            output_dir=str(tmp_path), fmt="square")
        with Image.open(hasil["path"]) as handle:
            gambar[account_id] = handle.convert("RGB").resize((160, 160), Image.LANCZOS)

    for a, b in itertools.combinations(ACCOUNT_IDS, 2):
        selisih = ImageChops.difference(gambar[a], gambar[b])
        rata = sum(ImageStat.Stat(selisih).mean) / 3
        assert rata >= 12, f"kartu {a} dan {b} terlalu mirip (selisih {rata:.1f})"


def test_teksur_baru_terbaca_dan_teks_tetap_aman(tmp_path):
    """Tekstur board dan hatch harus terlihat, tapi tidak menabrak teks."""
    for account_id, tekstur in (("chess", "board"), ("fashion", "diagonal_hatch")):
        profile = _profile(account_id)
        style = loader.visual_style(profile)
        assert style["canvas"]["texture"] == tekstur

        dengan, _ = layout_engine.paint_background(profile, style, "square")
        polos = Image.new("RGB", dengan.size, layout_engine.palette(profile)["background"])
        selisih = ImageChops.difference(dengan, polos)
        assert sum(ImageStat.Stat(selisih).mean) / 3 >= 3, f"{tekstur} tidak terlihat"

        hasil = template_engine.render_card(CONTENT, profile, output_dir=str(tmp_path),
                                           fmt="square")
        assert hasil["problems"] == []


def test_setiap_akun_punya_ciri_visual_sendiri():
    """Tidak boleh ada dua akun dengan kombinasi treatment yang sama persis."""
    CORES = ("background", "accent_bar", "panel", "rule", "texture")
    cidari = {}
    for account_id in ACCOUNT_IDS:
        canvas = loader.visual_style(_profile(account_id))["canvas"]
        cidari[account_id] = tuple(canvas.get(kunci) for kunci in CORES)

    assert len(set(cidari.values())) == len(ACCOUNT_IDS), cidari


def test_registry_bisa_dibaca_sebagai_json():
    with open(os.path.join(ROOT, "templates", "registry.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    assert data["templates"]
    assert data["generic"]["account"] is None