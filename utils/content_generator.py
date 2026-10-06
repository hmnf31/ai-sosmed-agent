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

API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
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

GAYA TULIS AKUN
{voice}

PERMINTAAN PEMAKAI
"{request}"

KONTEKS TOPIK YANG HARUS DIPAKAI
{topics}

KATEGORI KONTEN: {category}

ATURAN WAJIB (tidak boleh dilanggar)
{fact_rules}

Tugasmu. Jawab HANYA dengan objek JSON, tanpa teks lain, tanpa pembungkus markdown:

{{
  "title": "judul frame utama, maksimal 6 kata, TANPA tanda baca di akhir",
  "subtitle": "satu kalimat penjelas, maksimal 14 kata",
  "points": ["poin 1", "poin 2", "poin 3"],
  "caption": "caption lengkap 3-5 kalimat, bahasa Indonesia, ada ajakan ber komentar",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "cta": "satu kalimat ajakan bertindak, maksimal 10 kata",
  "angle": "sudut pandang konten ini, satu kalimat pendek",
  "source_url": "URL sumber utama bila ada, kalau tidak ada string kosong"
}}

Ketentuan tambahan:
- "points" berisi {max_points} butir, tiap butir maksimal 7 kata, tanpa titik di akhir.
- "title" dan "points" tidak boleh mengandung karakter newline.
- "hashtags" hanya dari daftar yang boleh dipakai atau yang wajar untuk niche ini.
- Jangan mengarang angka, harga, tanggal, nama brand, atau hasil yang tidak ada di konteks.
- "source_url" ditulis sebagai URL polos, tanpa format markdown seperti [teks](url).
- Bila data yang dibutuhkan tidak ada, tulis "data tidak tersedia" di dalam caption.
- Balas hanya JSON.
"""

FALLBACK_POINTS = [
    "Fokus pada satu pesan",
    "Contoh yang mudah diikuti",
    "Langkah berikutnya jelas",
]

#: Nilai enum di `generation_style` diterjemahkan ke arahan yang bisa dibaca model.
# Enum tetap dipakai di config supaya mudah divalidasi, tapi model perlu kalimat.
VOICE_GUIDE = {
    "sentence_style": {
        "natural_indonesian": "kalimat mengalir seperti orang biasa",
        "short_direct_sentences": "kalimat pendek dan langsung ke inti",
        "short_punchy": "kalimat pendek dengan ritme cepat",
        "warm_narrative": "kalimat mengalir hangat seperti bercerita",
        "conversational": "kalimat santai seperti ngobrol",
    },
    "hook_style": {
        "clear_value": "hook berupa janji nilai yang jelas",
        "bold_claim": "hook berupa klaim mencolok",
        "fact_or_question": "hook berupa fakta atau pertanyaan",
        "emotional_question": "hook berupa pertanyaan emosional",
        "relatable_problem": "hook berupa masalah yang terasa dekat",
    },
    "cta_style": {
        "direct_cta": "cta berupa perintah singkat",
        "community_prompt": "cta mengajak bergabung atau ikut berdiskusi",
        "polite_invitation": "cta berupa undangan dengan sopan",
        "soft_direct_cta": "cta lembut tapi tetap jelas",
    },
    "emoji_level": {
        "none": "tanpa emoji",
        "low": "pakai maksimal satu emoji",
        "medium": "pakai maksimal tiga emoji",
        "high": "boleh banyak emoji",
    },
}


def _candidate_models():
    preferred = os.getenv("OPENROUTER_MODEL")
    models = [preferred] if preferred else []
    models += [m for m in DEFAULT_MODELS if m not in models]
    return models


def _clean_source_url(raw):
    """Menyaring URL dari jawaban model.

    Model kadang membungkus URL sebagai markdown link. Bot harus mengirim URL
    polos supaya bisa disalin dan diklik, jadi semua bentuk markdown dibuang.
    """
    text = str(raw or "").strip()
    if not text:
        return ""
    match = re.search(r"https?://\S+", text)
    if not match:
        return ""
    url = match.group(0).strip().rstrip(".,);]}")
    url = url.replace("**", "").replace("<", "").replace(">", "")
    return url if url.startswith(("http://", "https://")) else ""


def voice_block(account, brand=None):
    """Blok arahan gaya tulis untuk prompt.

    Nilainya berasal dari `generation_style` di Brand Profile, dengan Nilai
    opsional dari `accounts.json` sebagai penimpa. Warna dan layout tidak ikut
    ke sini: prompt hanya mengatur tulisan, tampilan dibaca renderer dari config.
    """
    style = dict(brand.get("generation_style") or {}) if brand else {}
    style.update(account.get("generation_style") or {})

    lines = []
    if style.get("tone"):
        lines.append(f"- Nada bicara: {style['tone']}")
    for key in ("sentence_style", "hook_style", "cta_style", "emoji_level"):
        value = style.get(key)
        if not value:
            continue
        guide = VOICE_GUIDE.get(key, {}).get(value)
        lines.append(f"- {guide or value}")
    if style.get("vocabulary"):
        lines.append(f"- Istilah yang lazim dipakai: {style['vocabulary']}")
    return "\n".join(lines) or "- Nada bicara: santai dan ramah"


def _resolve_brand(account, brand=None):
    """Brand Profile milik akun, dibaca dari config bila tidak diberikan."""
    if brand:
        return brand
    try:
        from branding import loader

        return loader.brand_for(account or {})
    except Exception:
        return {}


def build_prompt(request, topics, account, category=None, max_points=MAX_FRAMES,
                 avoid_topics=None, angle_hint="", brand=None):
    """Menyusun prompt per akun.

    fact_check_rules ikut dimasukkan sebagai aturan wajib supaya MLBB dan catur
    tidak menghasilkan angka atau hasil pertandingan karangan. Gaya tulis dari
    Brand Profile ikut dimasukkan sebagai arahan, bukan sebagai data.
    """
    account = account or {}
    rules = account.get("fact_check_rules") or []
    avoid = account.get("avoid") or []
    combined = list(dict.fromkeys([*avoid, *rules])) or ["jangan mengarang fakta"]

    angle_block = f"\nSUDUT PANDANG: {angle_hint}\n" if angle_hint else ""
    avoid_block = "\nTOPIK YANG SUDAH PERNAH DIBUAT (jangan ulangi, ambil angle lain):\n" + "\n".join(
        f"- {t}" for t in (avoid_topics or [])
    ) + "\n" if avoid_topics else ""

    return PROMPT_TEMPLATE.format(
        label=account.get("label", "Akun"),
        handle=account.get("handle", ""),
        niche=account.get("niche", "umum"),
        audience=account.get("audience", "pengguna media sosial Indonesia"),
        tone=account.get("tone", "santai dan ramah"),
        voice=voice_block(account, brand or _resolve_brand(account, brand)),
        request=request,
        topics="\n".join(f"- {t}" for t in topics) or "- (belum ada topik, gunakan pengetahuan umum)",
        category=category or "umum",
        avoid=avoid_block or "\n(none)\n",
        fact_rules="\n".join(f"- {r}" for r in combined),
        max_points=max_points,
    ) + angle_block


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
        "angle": _one_line(raw.get("angle"), 120),
        "source_url": _clean_source_url(raw.get("source_url")),
    }


def generate_content(request, topics, account, category=None, avoid_topics=None,
                      angle_hint="", brand=None):
    """Menghasilkan caption + teks visual terstruktur untuk satu akun."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY tidak ditemukan!")

    prompt = build_prompt(
        request, topics, account, category=category,
        avoid_topics=avoid_topics, angle_hint=angle_hint, brand=brand,
    )
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