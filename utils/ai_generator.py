import os
import requests


def generate_caption(trends):
    """Mengirim tren ke OpenRouter API untuk dibuatkan caption Instagram."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY tidak ditemukan!")

    prompt = f"""
    Kamu adalah seorang Social Media Manager profesional.
    Berikut adalah tren topik hari ini: {', '.join(trends)}.

    Tugasmu:
    1. Buatkan 1 caption Instagram yang menarik, edukatif, dan interaktif sesuai tren tersebut.
    2. Sertakan call-to-action (CTA) ramah di akhir kalimat.
    3. Tambahkan 5-8 hashtag yang relevan di bagian paling bawah.
    4. Gunakan bahasa Indonesia yang santai dan profesional.
    """

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "meta-llama/llama-3-8b-instruct:free",
        "messages": [{"role": "user", "content": prompt}],
    }

    print("[AI] Mengirim permintaan ke OpenRouter...")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
    )

    if response.status_code == 200:
        caption = response.json()["choices"][0]["message"]["content"]
        print("[AI] Caption berhasil dibuat.")
        return caption
    else:
        raise Exception(f"Gagal memanggil OpenRouter API: {response.text}")