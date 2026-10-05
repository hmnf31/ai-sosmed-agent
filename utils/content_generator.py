"""Pembuat konten per akun.

Tujuan modul ini: satu permintaan pengguna (misal "buatkan 1 konten trend wedding")
menjadi dua hal yang siap dipakai:

  1. caption lengkap + hashtag untuk ditempel di media sosial
  2. teks visual singkat untuk dijadikan judul dan poin-poin di frame

Model diminta menjawab JSON murni supaya teksnya bisa langsung dipakai renderer.
"""
import json
import os
import re

import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "dots-studio/dots-3-note-preview:free",
    "qwen/qwen3.8-27b:free",
]
TIMEOUT = 180

MAX_FRAMES = 4
JSON_BLOCK_RE = re.compile(r"\{.*\}", re.S)

PROMPT_TEMPLATE = """
Kamu adalah content creator Media Sosial untuk sebuah akun di Indonesia.

PROFIL AKUN
- Nama akun: {label} ({handle})
- Niche: {niche}
- Audiens: {audience}
- Nada bicara: {tone}

PERMINTAAN PEMAKAI
"{request}"

KONTEKS TOPIK YANG HARUS DIPAKAI
{topics}

ATURAN
{avoid}

Tugasmu. Jawab HANYA dengan objek JSON, tanpa teks lain, tanpa pembungkus markdown:

{{
  "title": "judul frame utama, maksimal 6 kata, TANPA tanda baca di akhir",
  "subtitle": "satu kalimat penjelas, maksimal 14 kata",
  "points": ["poin 1", "poin 2", "poin 3"],
  "caption": "caption lengkap 3-5 kalimat, bahasa Indonesia, ada ajakan ber komentar",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "cta": "satu kalimat ajakan bertindak, maksimal 10 kata"
}}

Ketentuan tambahan:
- "points" berisi {max_points} butir, tiap butir maksimal 7 kata, tanpa titik di akhir.
- "title" dan "points" tidak boleh mengandung karakter newline.
- "hashtags" hanya dari daftar yang boleh dipakai atau yang wajar untuk niche ini.
- Jangan mengarang angka, harga, tanggal, nama brand, atau hasil yang tidak ada di konteks.
- Balas hanya JSON.
"""

FALLBACK_POINTS = [
    "Fokus pada satu pesan",
    "Contoh yang mudah diikuti",
    "Langkah berikutnya jelas",
]


def _candidate_models():
    preferred = os.getenv("OPENROUTER_MODEL")
    models = [preferred] if preferred else []
    models += [m for m in DEFAULT_MODELS if m not in models]
    return models


def build_prompt(request, topics, account, max_points=MAX_FRAMES):
    avoid = account.get("avoid") or ["jangan mengarang fakta"]
    return PROMPT_TEMPLATE.format(
        label=account.get("label", "Akun"),
        handle=account.get("handle", ""),
        niche=account.get("niche", "umum"),
        audience=account.get("audience", "pengguna media sosial Indonesia"),
        tone=account.get("tone", "santai dan ramah"),
        request=request,
        topics="\n".join(f"- {t}" for t in topics) or "- (belum ada topik, gunakan pengetahuan umum)",
        avoid="\n".join(f"- {a}" for a in avoid),
        max_points=max_points,
    )


def _extract_json(text):
    """Model kadang membungkus JSON dengan ``` atau prosa, ambil objeknya saja."""
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = JSON_BLOCK_RE.search(cleaned)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"Tidak bisa membaca JSON dari respons model: {cleaned[:200]}")


def _one_line(value, limit):
    """Ringkas ke satu baris supaya aman dipakai di dalam frame gambar."""
    text = " ".join(str(value or "").split())
    text = text.rstrip(" .,:;!-–—")
    if len(text) > limit:
        cut = text[:limit].rsplit(" ", 1)[0]
        text = cut
    return text


def _clean_points(raw, max_points):
    if isinstance(raw, str):
        raw = [raw]
    points = []
    for item in raw or []:
        text = _one_line(item, 60)
        if text:
            points.append(text)
        if len(points) >= max_points:
            break
    while len(points) < max_points:
        points.append(FALLBACK_POINTS[len(points) % len(FALLBACK_POINTS)])
    return points


def _clean_hashtags(raw, allowed):
    tags = []
    for item in raw or []:
        tag = "".join(str(item or "").split())
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = "#" + tag
        tag = "#" + "".join(ch for ch in tag[1:] if ch.isalnum() or ch == "_")
        if len(tag) > 2 and tag not in tags:
            tags.append(tag)

    for tag in allowed or []:
        if len(tags) >= 6:
            break
        if tag not in tags:
            tags.append(tag)
    return tags[:6]


def normalize_payload(raw, account):
    """Menjaga agar renderer selalu punya field yang lengkap dan aman."""
    caption = " ".join(str(raw.get("caption") or "").split())
    tags = _clean_hashtags(raw.get("hashtags"), account.get("hashtags"))

    if tags:
        joined = " ".join(tags)
        if joined not in caption:
            caption = f"{caption}\n\n{joined}"

    return {
        "title": _one_line(raw.get("title"), 60) or account.get("label", "Konten"),
        "subtitle": _one_line(raw.get("subtitle"), 110),
        "points": _clean_points(raw.get("points"), MAX_FRAMES),
        "cta": _one_line(raw.get("cta"), 70),
        "caption": caption.strip(),
        "hashtags": tags,
    }


def generate_content(request, topics, account):
    """Menghasilkan caption + teks visual terstruktur untuk satu akun."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY tidak ditemukan!")

    prompt = build_prompt(request, topics, account)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    errors = []
    for model in _candidate_models():
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1200,
            "temperature": 0.8,
        }

        print(f"[AI] Meminta konten ke OpenRouter (model: {model})...")
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT)
        except requests.RequestException as e:
            errors.append(f"{model}: koneksi gagal ({e})")
            continue

        if response.status_code != 200:
            errors.append(f"{model}: HTTP {response.status_code} {response.text[:200]}")
            continue

        message = response.json().get("choices", [{}])[0].get("message", {})
        content = (message.get("content") or "").strip()
        if not content:
            errors.append(f"{model}: respons kosong")
            continue

        try:
            raw = _extract_json(content)
        except ValueError as e:
            errors.append(f"{model}: {e}")
            continue

        print(f"[AI] Konten dibuat dengan model {model}.")
        return normalize_payload(raw, account)

    raise Exception("Gagal meminta konten ke OpenRouter. " + " | ".join(errors))