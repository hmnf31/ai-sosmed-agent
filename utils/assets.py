"""Generator aset gambar untuk scene bertipe `image`.

Pipeline mengikuti master plan Phase 6: baca plan -> ekstrak visual per
scene -> bentuk prompt sesuai brand -> panggil provider adapter (9Router)
-> simpan file -> normalisasi format/rasio/dimensi -> QA file -> tulis
`asset_manifest.json` -> tandai kegagalan/fallback.

Prinsip:
- API key TIDAK pernah ditulis ke manifest.
- Retry dibatasi (tidak pernah tanpa batas); bila gagal, fallback ke
  placeholder bergradasi warna brand (atau ditandai gagal bila fallback pun
  rusak).
- Provenance dan status hak pakai dicatat di manifest (`usage_rights`).
- Aset buatan AI tidak pernah dipresentasikan sebagai logo, UI, atau materi
  resmi; właściwy status dicatat sebagai `review_required`.
"""
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

from PIL import Image, ImageDraw

DEFAULT_NINEROUTER_URL = os.getenv("NINEROUTER_URL") or "http://127.0.0.1:20128"
DEFAULT_NINEROUTER_KEY = os.getenv("NINEROUTER_KEY") or ""
DEFAULT_IMAGE_MODEL = os.getenv("NINEROUTER_IMAGE_MODEL") or "ag/gemini-3.1-flash-image"

IMAGE_ENDPOINT = "/v1/images/generations"
MODELS_IMAGE_ENDPOINT = "/v1/models/image"

#: Retry maksimal per scene (total panggilan <= MAX_ATTEMPTS). "Hindari retry
#: tanpa batas" dari master plan.
MAX_ATTEMPTS = 2

VALID_ASSET_STATUS = ("ready", "fallback", "failed")
VALID_SOURCE_TYPES = ("ai_generated", "upload", "logo", "programmatic",
                      "placeholder", "footage", "official_material")

#: Ambang deviasi standar luminansi; di bawahnya gambar dianggap polos.
BLANK_STDDEV_THRESHOLD = 3.0

NEUTRAL_COLORS = {
    "background": "#1B1D23",
    "background_alt": "#2C3038",
    "surface": "#24272F",
    "primary": "#3A3F4B",
    "secondary": "#7C8494",
    "accent": "#C8CDD6",
    "text": "#F2F3F5",
    "muted": "#A7AEBB",
    "on_primary": "#1B1D23",
}

#: Nama-nama model yang tidak menerima parameter `size` (nano-banana, dst).
#: Dipakai untuk menahan `size` saat pemanggil memintanya.
SIZE_IGNORED_MODELS = re.compile(r"(nano|gemini)", re.IGNORECASE)


class AssetError(Exception):
    """Gagal membuat, menormalkan, atau memverifikasi aset gambar."""


def _headers(key):
    headers = {"Accept": "application/json, image/*"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _post_bytes(url, payload, *, headers=None, timeout=60):
    """POST ke 9Router dan mengembalikan bytes (response_format=binary).

    Bila endpoint membalas JSON (mis. provider yang menolak binary), JSON
    diurai: `error` -> AssetError, `b64_json` -> bytes hasil dekode,
    `data[].url` -> hasil unduh. Gagal JARINGAN -> AssetError dengan sebab.
    """
    data = json.dumps(payload).encode("utf-8")
    merged = dict(headers or {})
    merged["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=merged, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")[:300]
        raise AssetError(f"9Router image HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise AssetError(f"9Router tidak terjangkau: {error.reason}") from error
    except TimeoutError as error:
        raise AssetError("9Router image timeout") from error

    if "json" in content_type.lower():
        return _bytes_from_json_payload(raw)
    return raw


def _bytes_from_json_payload(raw):
    """Mengekstrak bytes dari body JSON (b64_json / data[].url / error)."""
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AssetError(f"Respons image bukan JSON: {error}") from error
    if isinstance(payload, dict) and payload.get("error"):
        raise AssetError(f"9Router image error: {payload['error']}")
    candidates = []
    for item in (_iter_data_items(payload)):
        if item.get("b64_json"):
            candidates.append(item["b64_json"])
        if item.get("url"):
            candidates.append(item["url"])
    if not candidates:
        raise AssetError("Respons image tanpa gambar (b64_json/url)")
    first = candidates[0]
    if first.startswith("http://") or first.startswith("https://"):
        return _download(first)
    if first.startswith("data:image"):
        _, _, first = first.partition(",")
    try:
        return base64.b64decode(first)
    except (ValueError, TypeError) as error:
        raise AssetError(f"b64_json tidak valid: {error}") from error


def _iter_data_items(payload):
    if isinstance(payload, dict):
        data = payload.get("data", [])
        if isinstance(data, list):
            for item in data:
                yield item if isinstance(item, dict) else {}
        if payload.get("b64_json"):
            yield {"b64_json": payload["b64_json"]}
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item


def _download(url, timeout=60):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read()
    except urllib.error.URLError as error:
        raise AssetError(f"Unduh URL aset gagal: {error.reason}") from error


def list_image_models(url=None, key=None, timeout=8):
    """Mendaftar model image yang aktif di 9Router.

    Mengembalikan daftar `id`. URL dan key bisa diberikan eksplisit untuk
    testing; default diambil dari env.
    """
    base = (url or DEFAULT_NINEROUTER_URL).rstrip("/")
    payload = _request_json(f"{base}{MODELS_IMAGE_ENDPOINT}", headers=_headers(key), timeout=timeout)
    return [item.get("id") for item in payload.get("data", []) if isinstance(item, dict) and item.get("id")]


def generate_image_bytes(prompt, *, model=None, size=None, url=None, key=None, timeout=60):
    """Memanggil `/v1/images/generations?response_format=binary`.

    Mengembalikan bytes gambar mentah dari provider. `size` hanya dikirim
    bila diisi dan model bukan model yang mengabaikan size (nano-banana dll).
    Model default diambil dari env `NINEROUTER_IMAGE_MODEL`.
    """
    base = (url or DEFAULT_NINEROUTER_URL).rstrip("/")
    model = model or DEFAULT_IMAGE_MODEL
    payload = {"model": model, "prompt": prompt, "n": 1}
    if size and not SIZE_IGNORED_MODELS.search(model):
        payload["size"] = size
    endpoint = f"{base}{IMAGE_ENDPOINT}?response_format=binary"
    return _post_bytes(endpoint, payload, headers=_headers(key), timeout=timeout)


def save_bytes(data, path):
    """Menyimpan bytes ke `path`; membuat folder induk bila belum ada."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def _hex_to_rgb(value):
    value = str(value or "").strip().lstrip("#")
    try:
        if len(value) == 6:
            return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
        if len(value) == 3:
            return tuple(int(value[i] * 2, 16) for i in range(3))
    except ValueError:
        pass
    return None


def normalize_image(src_path, target_size, out_path):
    """Menormalkan gambar: crop cover (crop/fit) ke rasio target lalu simpan.

    Mengubah format apa pun yang bisa dibuka PIL menjadi PNG RGB dengan
    dimensi persis `target_size`; EXIF orientasi diterapkan. Mengembalikan
    tuple (lebar, tinggi) hasil. `src_path` boleh sama dengan `out_path`.
    """
    target_w, target_h = target_size
    try:
        with Image.open(src_path) as source:
            img = ImageOps_exif(source)
    except OSError as error:
        raise AssetError(f"Tidak bisa membuka gambar {src_path}: {error}") from error

    img = img.convert("RGB")
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = max(1, round(src_w * scale)), max(1, round(src_h * scale))
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))

    return _save_image(img, out_path)


def ImageOps_exif(source):
    """Menerapkan EXIF orientation via ImageOps bila tersedia."""
    try:
        from PIL import ImageOps
        return ImageOps.exif_transpose(source)
    except (ImportError, AttributeError):
        return source


def _save_image(img, path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    size = img.size
    img.close()
    return size


def placeholder_image(path, size, colors=None):
    """Membuat placeholder gradasi warna brand (fallback sah).

    Bukan pengganti estetika, tapi aset valid yang tetap bisa dirender dan
    jelas bukan aset AI. Mengembalikan (lebar, tinggi).
    """
    palette = dict(NEUTRAL_COLORS)
    if colors:
        palette.update({k: v for k, v in colors.items() if v})
    background = _hex_to_rgb(palette.get("background")) or (27, 29, 35)
    accent = _hex_to_rgb(palette.get("accent") or palette.get("primary")) or (200, 205, 214)

    width, height = size
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / max(1, height - 1)
        row = tuple(round(a + (b - a) * t) for a, b in zip(background, accent))
        draw.line([(0, y), (width, y)], fill=row)
    return _save_image(img, path)


def build_asset_prompt(scene, account=None, brand=None):
    """Menyusun prompt generatif dari scene + identitas brand.

    Teks di layar TIDAK dimasukkan ke prompt (teks adalah overlay renderer;
    gambar AI berteks menjadi tidak konsisten). Aset tidak boleh memuat
    watermark/logo sendiri karena watermark ditambahkan sebagai layer.
    """
    base = str(scene.get("visual_prompt") or "").strip() or "visual scene kosong"
    parts = [base]

    identity = (brand or {}).get("identity") or {}
    mood = identity.get("visual_mood") or []
    image_style = identity.get("image_style")
    color_block = _color_hint((brand or {}).get("colors") or {})

    style_tokens = []
    if image_style:
        style_tokens.append(image_style)
    if mood:
        style_tokens.append(", ".join(mood))
    if style_tokens:
        parts.append("Style: " + " | ".join(style_tokens))
    if color_block:
        parts.append("Palette hint: " + color_block)
    if account:
        parts.append(f"Untuk konten akun {account}")

    parts.append(
        "Tanpa teks, kata, huruf, angka, watermark, atau logo dalam gambar."
    )
    return ". ".join(parts).strip(" .") + "."


def _color_hint(colors):
    picked = []
    for key in ("primary", "secondary", "accent", "background"):
        value = colors.get(key)
        if value:
            picked.append(f"{key}={value}")
    return ", ".join(picked) if picked else ""


def target_size(plan):
    """Ukuran kanvas aset dari plan (lebar x tinggi)."""
    return (int(plan.get("width") or 1080), int(plan.get("height") or 1920))


def verify_asset(path, expected_size=None):
    """QA file aset; mengembalikan daftar masalah (kosong = sah).

    Memeriksa: keberadaan, ukuran file, bisa dibuka PIL, dimensi sesuai
    target, dan tidak polos. Gaya sama seperti validator content_plan.
    """
    problems = []
    if not path:
        return ["path aset kosong"]
    if not os.path.isfile(path):
        return ["file aset tidak ada"]
    if os.path.getsize(path) == 0:
        return ["file aset kosong (0 byte)"]
    try:
        with Image.open(path) as img:
            img.load()
            width, height = img.size
    except OSError as error:
        return [f"file aset tidak bisa dibuka: {error}"]
    if expected_size and (width, height) != tuple(expected_size):
        problems.append(f"dimensi {width}x{height}, target {expected_size[0]}x{expected_size[1]}")
    with Image.open(path) as img:
        gray = img.convert("L")
        sample = gray.resize((64, 64), Image.LANCZOS)
        pixels = list(sample.tobytes())
        mean = sum(pixels) / len(pixels)
        variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
        if variance ** 0.5 < BLANK_STDDEV_THRESHOLD:
            problems.append("gambar hampir polos (diduga blank)")
    return problems


def build_manifest(plan, assets):
    """Menyusun dict `asset_manifest.json` sesuai contoh master plan."""
    clean = []
    for item in assets:
        entry = {
            "asset_id": item["asset_id"],
            "scene_id": item["scene_id"],
            "type": "image",
            "path": item.get("path"),
            "purpose": item.get("purpose") or "visual",
            "source_type": item["source_type"],
            "status": item["status"],
        }
        if item.get("provider"):
            entry["provider"] = item["provider"]
        if item.get("prompt_version"):
            entry["prompt_version"] = item["prompt_version"]
        if item.get("width") is not None:
            entry["width"] = item["width"]
        if item.get("height") is not None:
            entry["height"] = item["height"]
        if item.get("usage_rights"):
            entry["usage_rights"] = item["usage_rights"]
        if item.get("error"):
            entry["error"] = item["error"]
        clean.append(entry)
    return {
        "schema_version": "1.0",
        "job_id": plan.get("job_id"),
        "assets": clean,
    }


def apply_manifest(plan, manifest):
    """Menulis `asset_files` scene dari manifest ke salinan plan (in-place).

    Hanya scene bertipe `image` yang diisi; scene lain dikosongkan supaya
    konsisten (renderer tidak boleh menyangka ada aset untuk teks/gradien).
    """
    by_scene = {item["scene_id"]: item for item in manifest.get("assets", [])}
    for scene in plan.get("scenes", []):
        entry = by_scene.get(scene.get("scene_id"))
        if scene.get("visual_type") == "image":
            scene["asset_files"] = [entry["path"]] if entry and entry.get("path") else []
        else:
            scene["asset_files"] = []
    return plan


def _account_brand(plan, brand=None):
    """Mengambil brand profile; fallback palet netral bila gagal."""
    if brand:
        return brand
    try:
        from branding import loader
        return loader.resolve_brand(account=plan.get("account"))
    except Exception:
        return {}


def _record_ready(asset_id, scene, purpose, path, size, provider, prompt_version):
    return {
        "asset_id": asset_id,
        "scene_id": scene.get("scene_id"),
        "purpose": purpose,
        "path": path,
        "source_type": "ai_generated",
        "provider": provider,
        "prompt_version": prompt_version,
        "width": size[0],
        "height": size[1],
        "status": "ready",
        "usage_rights": "review_required",
    }


def _record_fallback(asset_id, scene, purpose, path, size, provider):
    return {
        "asset_id": asset_id,
        "scene_id": scene.get("scene_id"),
        "purpose": purpose,
        "path": path,
        "source_type": "placeholder",
        "provider": provider,
        "width": size[0],
        "height": size[1],
        "status": "fallback",
        "usage_rights": "internal",
    }


def generate_assets(plan, *, model=None, output_dir=None, ninerouter_url=None,
                    ninerouter_key=None, brand=None, timeout=60):
    """Pipeline aset penuh; mengembalikan dict manifest dan menulis file.

    Untuk tiap scene bertipe `image`: generate -> simpan mentah -> normalisasi
    -> QA; bila gagal, fallback placeholder; bila fallback pun rusak, status
    `failed`. Manifest ditulis ke `output_dir/asset_manifest.json`.
    """
    provider = model or DEFAULT_IMAGE_MODEL
    output_dir = output_dir or os.path.join("output", "assets", str(plan.get("job_id") or "untitled"))
    os.makedirs(output_dir, exist_ok=True)
    brand = _account_brand(plan, brand=brand)
    colors = (brand or {}).get("colors") or {}

    size = target_size(plan)
    prompt_version = "1"
    assets = []
    for scene in plan.get("scenes", []):
        if scene.get("visual_type") != "image":
            continue
        asset_id = f"asset_{scene.get('scene_id')}"
        purpose = scene.get("purpose") or "visual"
        prompt = build_asset_prompt(scene, account=plan.get("account"), brand=brand)

        record = None
        last_error = None
        final_path = display_path(os.path.join(output_dir, f"{scene.get('scene_id')}.png"))
        for attempt in range(MAX_ATTEMPTS):
            try:
                data = generate_image_bytes(prompt, model=provider, url=ninerouter_url,
                                            key=ninerouter_key, timeout=timeout)
                raw_path = os.path.join(output_dir, f"{scene.get('scene_id')}.raw")
                save_bytes(data, raw_path)
                size_actual = normalize_image(raw_path, size, os.path.join(output_dir, os.path.basename(final_path)))
                problems = verify_asset(os.path.join(output_dir, os.path.basename(final_path)), expected_size=size)
                if problems:
                    raise AssetError("QA aset tidak lolos: " + "; ".join(problems))
                record = _record_ready(asset_id, scene, purpose, final_path,
                                       size_actual, provider, prompt_version)
                break
            except AssetError as error:
                last_error = str(error)
                if attempt + 1 < MAX_ATTEMPTS:
                    continue
        if record is None:
            fallback_path = os.path.join(output_dir, f"{scene.get('scene_id')}.placeholder.png")
            try:
                size_actual = placeholder_image(fallback_path, size, colors=colors)
                problems = verify_asset(fallback_path, expected_size=size)
                if problems:
                    raise AssetError("QA placeholder tidak lolos: " + "; ".join(problems))
                record = _record_fallback(asset_id, scene, purpose,
                                          display_path(fallback_path),
                                          size_actual, provider)
            except AssetError as error:
                record = {
                    "asset_id": asset_id,
                    "scene_id": scene.get("scene_id"),
                    "purpose": purpose,
                    "path": None,
                    "source_type": "placeholder",
                    "provider": provider,
                    "status": "failed",
                    "error": f"{last_error} | fallback: {error}",
                }
        assets.append(record)

    manifest = build_manifest(plan, assets)
    manifest_path = os.path.join(output_dir, "asset_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
    return manifest


def display_path(path):
    """Path relatif ke cwd bila berada di dalamnya, absolut bila di luar."""
    abs_path = os.path.abspath(path)
    cwd = os.path.abspath(os.getcwd())
    if abs_path.startswith(cwd):
        return os.path.relpath(abs_path, cwd)
    return abs_path


def _request_json(url, *, method="GET", payload=None, headers=None, timeout=20):
    """Variasi JSON dari `_post_bytes`: untuk endpoint return-JSON seperti
    daftar model (agar `list_image_models` bisa distub dengan mudah)."""
    data = None
    merged = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        merged["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=merged, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")[:200]
        raise AssetError(f"9Router HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise AssetError(f"9Router tidak terjangkau: {error.reason}") from error
    except (json.JSONDecodeError, ValueError) as error:
        raise AssetError(f"Respons 9Router bukan JSON: {error}") from error
    except TimeoutError as error:
        raise AssetError("9Router timeout") from error


def _main(argv=None):
    """CLI: daftar model image atau generate aset untuk satu plan JSON.

    Contoh:
      python -m utils.assets --models
      python -m utils.assets plan.json
      python -m utils.assets plan.json --model gemini/gemini-2.5-flash-image
    """
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv or "--help" in argv or "-h" in argv:
        print("Gunakan: python -m utils.assets [--models] PLAN_JSON [--model MODEL] [--out DIR]")
        return 0
    if argv[0] == "--models":
        for model in list_image_models(timeout=10):
            print(model)
        return 0

    model = None
    output_dir = None
    plan_path = argv[0]
    if "--model" in argv:
        model = argv[argv.index("--model") + 1]
    if "--out" in argv:
        output_dir = argv[argv.index("--out") + 1]

    with open(plan_path, "r", encoding="utf-8") as handle:
        plan = json.load(handle)
    manifest = generate_assets(plan, model=model, output_dir=output_dir)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())