Berikut adalah isi file **`README.md`** lengkap dan terstruktur. Dokumen ini dirancang khusus agar siap Anda serahkan langsung ke AI Agent di VS Code (seperti GitHub Copilot Workspace, Cursor, Roo Code, atau Cline) untuk dieksekusi secara otomatis.

---

### File: `AGENT_INSTRUCTIONS.md`

```markdown
# 🤖 Spesifikasi Project: AI Social Media Agent (Python + GitHub Actions)

Dokumen ini berisi instruksi lengkap, arsitektur, dependencies, serta struktur kode untuk membangun **AI Social Media Agent** yang berjalan secara teratur menggunakan **GitHub Actions** (Heartbeat pattern).

---

## 📋 1. Ringkasan & Tujuan Sistem
Sistem ini bertugas untuk:
1. **Riset Tren:** Mengambil tren harian dari Google Trends secara otomatis menggunakan Headless Browser (Playwright).
2. **Generasi Konten:** Memproses tren tersebut menggunakan **OpenRouter API** (model LLM gratis) untuk menghasilkan caption Instagram yang menarik dan relevan.
3. **Auto-Post Instagram:** Mengunggah gambar beserta caption hasil olahan ke Instagram Bisnis menggunakan **Meta Graph API**.
4. **Notifikasi Laporan:** Mengirimkan laporan eksekusi (berhasil/gagal) ke **Telegram Bot**.

---

## 🛠️ 2. Library & Dependencies (`requirements.txt`)

Berikut adalah pustaka Python yang dibutuhkan beserta kegunaannya:

```text
# Web Automation & Scraping
playwright==1.42.0

# HTTP Requests & API Client
requests==2.31.0

# Pengolahan Gambar (Untuk membuat/memanipulasi template visual)
Pillow==10.2.0

# Utilitas Environment
python-dotenv==1.0.1

```

---

## 📁 3. Struktur Direktori Project

Harap buat struktur folder dan file berikut:

```text
ai-sosmed-agent/
├── .github/
│   └── workflows/
│       └── heartbeat.yml       # Konfigurasi GitHub Actions Cron Trigger
├── .env.example                # Template rahasia lokal
├── .gitignore                  # File pengabaian Git
├── requirements.txt            # Daftar library Python
├── main.py                     # Script orchestrator utama
└── utils/
    ├── __init__.py
    ├── scraper.py              # Modul Playwright untuk riset tren
    ├── ai_generator.py         # Modul integrasi OpenRouter API
    ├── instagram.py            # Modul integrasi Meta Graph API
    └── notifier.py             # Modul integrasi Notifikasi Telegram

```

---

## ⚙️ 4. Variabel Lingkungan / Environment Variables

Daftar **GitHub Secrets** / file `.env` yang wajib ada:

| Variable Name | Deskripsi |
| --- | --- |
| `OPENROUTER_API_KEY` | API Key dari OpenRouter (OpenAI-compatible) |
| `IG_USER_ID` | Instagram Business Account ID dari Meta for Developers |
| `IG_ACCESS_TOKEN` | Page Access Token / User Access Token berumur panjang |
| `TELEGRAM_BOT_TOKEN` | Token Bot Telegram dari `@BotFather` |
| `TELEGRAM_CHAT_ID` | ID Chat Telegram Anda untuk penerimaan laporan |

---

## 📝 5. Implementasi Kode Lengkap

### 📄 File: `.github/workflows/heartbeat.yml`

```yaml
name: AI Sosmed Heartbeat Agent

on:
  schedule:
    # Berjalan otomatis setiap jam 08:00 WIB (01:00 UTC)
    - cron: '0 1 * * *'
  workflow_dispatch: # Mengizinkan pemicu manual dari Dashboard GitHub

jobs:
  run-agent:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          playwright install chromium --with-deps

      - name: Eksekusi AI Agent
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          IG_USER_ID: ${{ secrets.IG_USER_ID }}
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python main.py

```

---

### 📄 File: `utils/scraper.py`

```python
from playwright.sync_api import sync_playwright
import logging

def get_google_trends(geo="ID", max_results=3):
    """Mengambil tren harian dari Google Trends menggunakan Playwright."""
    url = f"[https://trends.google.com/trends/trendingsearches/daily?geo=](https://trends.google.com/trends/trendingsearches/daily?geo=){geo}"
    print(f"[SCRAPER] Membuka {url}...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_selector(".trend-title", timeout=10000)
            
            trends = page.eval_on_selector_all(
                ".trend-title", 
                "elements => elements.map(e => e.innerText.trim())"
            )
            browser.close()
            
            result = trends[:max_results] if trends else ["Teknologi AI", "Otomatisasi Digital"]
            print(f"[SCRAPER] Berhasil mendapatkan tren: {result}")
            return result
    except Exception as e:
        print(f"[SCRAPER ERROR] Gagal mengambil tren: {e}")
        return ["Inovasi Teknologi", "Tren Terkini"]

```

---

### 📄 File: `utils/ai_generator.py`

```python
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
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "meta-llama/llama-3-8b-instruct:free",
        "messages": [{"role": "user", "content": prompt}]
    }

    print("[AI] Mengirim permintaan ke OpenRouter...")
    response = requests.post("[https://openrouter.ai/api/v1/chat/completions](https://openrouter.ai/api/v1/chat/completions)", headers=headers, json=payload)
    
    if response.status_code == 200:
        caption = response.json()['choices'][0]['message']['content']
        print("[AI] Caption berhasil dibuat.")
        return caption
    else:
        raise Exception(f"Gagal memanggil OpenRouter API: {response.text}")

```

---

### 📄 File: `utils/instagram.py`

```python
import os
import requests

def publish_to_instagram(image_url, caption):
    """Mengunggah gambar dan caption ke Instagram Bisnis via Meta Graph API."""
    ig_user_id = os.getenv("IG_USER_ID")
    access_token = os.getenv("IG_ACCESS_TOKEN")

    if not ig_user_id or not access_token:
        raise ValueError("IG_USER_ID atau IG_ACCESS_TOKEN belum diset!")

    # Step 1: Buat Media Container
    container_url = f"[https://graph.facebook.com/v19.0/](https://graph.facebook.com/v19.0/){ig_user_id}/media"
    container_payload = {
        'image_url': image_url,
        'caption': caption,
        'access_token': access_token
    }
    
    print("[INSTAGRAM] Membuat container media...")
    r_container = requests.post(container_url, data=container_payload)
    res_container = r_container.json()

    if 'id' not in res_container:
        raise Exception(f"Gagal membuat container media IG: {res_container}")

    creation_id = res_container['id']

    # Step 2: Publish Container
    publish_url = f"[https://graph.facebook.com/v19.0/](https://graph.facebook.com/v19.0/){ig_user_id}/media_publish"
    publish_payload = {
        'creation_id': creation_id,
        'access_token': access_token
    }

    print("[INSTAGRAM] Mengunggah postingan ke Instagram...")
    r_publish = requests.post(publish_url, data=publish_payload)
    res_publish = r_publish.json()

    if 'id' not in res_publish:
        raise Exception(f"Gagal publish postingan IG: {res_publish}")

    print(f"[INSTAGRAM] Postingan berhasil dipublikasikan! Post ID: {res_publish['id']}")
    return res_publish['id']

```

---

### 📄 File: `utils/notifier.py`

```python
import os
import requests

def send_telegram_notification(message):
    """Mengirim pesan notifikasi status ke Bot Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[NOTIFIER] Token/Chat ID Telegram tidak diset. Notifikasi dilewati.")
        return

    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        requests.post(url, json=payload)
        print("[NOTIFIER] Notifikasi Telegram berhasil dikirim.")
    except Exception as e:
        print(f"[NOTIFIER ERROR] Gagal mengirim notifikasi: {e}")

```

---

### 📄 File: `main.py`

```python
import os
from dotenv import load_dotenv
from utils.scraper import get_google_trends
from utils.ai_generator import generate_caption
from utils.instagram import publish_to_instagram
from utils.notifier import send_telegram_notification

# Load variabel lingkungan untuk pengembangan lokal
load_dotenv()

def run_agent():
    print("=== [MULAI SIKLUS AI SOSMED AGENT] ===")
    
    try:
        # 1. Riset Tren
        trends = get_google_trends()
        
        # 2. Generasi Caption via AI
        caption = generate_caption(trends)
        
        # 3. Tentukan URL Gambar (Gambar sampel high quality atau image generator)
        sample_image_url = "[https://picsum.photos/1080/1080](https://picsum.photos/1080/1080)"
        
        # 4. Upload ke Instagram
        post_id = publish_to_instagram(sample_image_url, caption)
        
        # 5. Kirim Notifikasi Sukses
        success_msg = f"✅ *AI Agent Report: Sukses Posting!*\n\n*Topik Tren:* {', '.join(trends)}\n*Post ID IG:* `{post_id}`"
        send_telegram_notification(success_msg)
        
    except Exception as e:
        error_msg = f"❌ *AI Agent Report: Gagal!*\n\n*Error Detail:* `{str(e)}`"
        print(f"[MAIN ERROR] {e}")
        send_telegram_notification(error_msg)
        
    print("=== [SIKLUS SELESAI] ===")

if __name__ == "__main__":
    run_agent()

```

---

## 🚀 6. Petunjuk Implementasi untuk AI Agent di VS Code

Apabila Anda menggunakan AI Agent di VS Code (seperti **Cursor**, **Roo Code**, atau **Cline**), berikan instruksi berikut:

> *"Tolong buatkan file dan direktori sesuai spesifikasi di dokumen Markdown ini secara bertahap. Mulailah dari membuat `requirements.txt`, struktur modul di folder `utils/`, file `main.py`, dan terakhir file `.github/workflows/heartbeat.yml`."*

```

---

<FollowUp label="Ingin saya jelaskan cara melakukan uji coba (testing) script ini secara lokal sebelum di-push ke GitHub?" query="Bagaimana cara menjalankan dan menguji coba script AI Sosmed Agent ini di komputer lokal sebelum di-push ke GitHub?"/>

```

