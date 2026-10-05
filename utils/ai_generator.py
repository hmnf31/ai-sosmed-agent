import os
import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "dots-studio/dots-3-note-preview:free",
    "qwen/qwen3.8-27b:free",
]
TIMEOUT = 120

NICHES = {
    "general": """
    Kamu adalah seorang Social Media Manager profesional.
    Berikut adalah tren topik hari ini: {trends}.

    Tugasmu:
    1. Buatkan 1 caption Instagram yang menarik, edukatif, dan interaktif sesuai tren tersebut.
    2. Sertakan call-to-action (CTA) ramah di akhir kalimat.
    3. Tambahkan 5-8 hashtag yang relevan di bagian paling bawah.
    4. Gunakan bahasa Indonesia yang santai dan profesional.
    5. Jawab HANYA dengan caption final, tanpa penjelasan atau proses berpikir.
    """,
    "mlbb": """
    Kamu adalah content creator esports Mobile Legends: Bang Bang (MLBB) untuk akun
    fans Indonesia. Following ini adalah topik paling baru dari kanal esports:
    {trends}.

    Tugasmu:
    1. Buat 1 caption TikTok maksimal 60 kata yang memicu debat dan komentar.
    2. Nada: bahasa anak muda esports Indonesia, percaya diri, sedikit humor.
    3. Pancing interaksi dengan pertanyaan (misal prediksi hasil, pilih tim, pilih hero).
    4. Wajib 5-8 hashtag relevan seperti #MPLID #MLBB #MobileLegends.
    5. Jangan mengarang hasil pertandingan yang tidak ada di topik di atas.
    6. Jawab HANYA dengan caption final, tanpa penjelasan atau proses berpikir.
    """,
}


def build_prompt(trends, niche="general"):
    template = NICHES.get(niche, NICHES["general"])
    return template.format(trends=", ".join(trends))


def _candidate_models():
    preferred = os.getenv("OPENROUTER_MODEL")
    models = [preferred] if preferred else []
    models += [m for m in DEFAULT_MODELS if m not in models]
    return models


def generate_caption(trends, niche=None):
    """Mengirim tren ke OpenRouter API untuk dibuatkan caption sesuai niche konten."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY tidak ditemukan!")

    niche = (niche or os.getenv("CONTENT_NICHE") or "general").strip().lower()
    prompt = build_prompt(trends, niche)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    errors = []
    for model in _candidate_models():
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 800,
        }

        print(f"[AI] Mengirim permintaan ke OpenRouter (model: {model})...")
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT)
        except requests.RequestException as e:
            errors.append(f"{model}: koneksi gagal ({e})")
            continue

        if response.status_code != 200:
            errors.append(f"{model}: HTTP {response.status_code} {response.text[:200]}")
            continue

        message = response.json().get("choices", [{}])[0].get("message", {})
        caption = (message.get("content") or "").strip()
        if not caption:
            errors.append(f"{model}: respons kosong")
            continue

        print(f"[AI] Caption berhasil dibuat dengan model {model}.")
        return caption

    raise Exception("Gagal memanggil OpenRouter API pada semua model. " + " | ".join(errors))