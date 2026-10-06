---
name: project-continuation
description: Melanjutkan proyek Social Media Assistant (Telegram bot + content creation) di C:\Users\Administrator\Desktop\Automation. Gunakan saat diminta melanjutkan/mengubah bot, generator konten, scraper, atau integrasi 9Router.
---

# Lanjutan Proyek: Social Media Assistant

Proyek Python ini: bot Telegram yang membuat konten (caption, video, gambar)
dari permintaan chat, lalu mengirim media ke Telegram. Unggah ke TikTok/IG manual.

## Sumber kebenaran

- `ALUR-PROYEK.md` — alur aktif end-to-end (wajib baca dulu)
- `Plan.md`, `PLAN-UPDATE-SOCIAL-MEDIA-ASSISTANT.md`,
  `PLAN-LANJUTAN-IMPLEMENTASI-SOCIAL-MEDIA-ASSISTANT-V2.md` — rencana lanjutan
- `master_plan_ai_content_automation_updated.md` — master plan

## Cara jalan

```bat
cd C:\Users\Administrator\Desktop\Automation
.venv\Scripts\python.exe bot.py        :: long polling Telegram
```

Konfigurasi di `.env` (akun, token Telegram, niche `CONTENT_NICHE=mlbb`,
Google Sheet `SHEET_PUBLIC_ID`, TikTok API). Akun + niche: `accounts.json`
(contoh: `accounts.example.json`).

## Struktur penting

- `bot.py`, `main.py` — entry point
- `utils/telegram_bot.py` — long polling, filter `authorized_chat()`
- `utils/router.py` — chat bebas → intent (account/task/topic/quantity)
- `utils/accounts.py` — `match_account()`
- `utils/scraper.py` — riset topik terpanas (Playwright/YouTube)
- `utils/content_generator.py`, `utils/ai_generator.py` — teks AI (OpenAI-compatible)
- `utils/video_maker.py` (ffmpeg), `utils/image_maker.py` (Pillow)
- `utils/notifier.py` — kirim media ke Telegram
- `templates/`, `branding/`, `styles/`, `assets/`, `output/`

## 9Router (gateway AI gratis, localhost:20128)

Agar proyek pakai AI gratis via 9Router, set di `.env`:

```ini
OPENROUTER_API_URL=http://localhost:20128/v1/chat/completions
OPENROUTER_API_KEY=<API_KEY_DARI_DASHBOARD_9ROUTER>
OPENROUTER_MODEL=free-max
```

(`utils/content_generator.py` dan `utils/ai_generator.py` sudah mendukung
`OPENROUTER_API_URL`; tanpa variabel itu mereka tetap pakai OpenRouter langsung.)

Combo `free-max` (fallback): `kr/claude-sonnet-4.5` → `kr/glm-5` →
`kr/MiniMax-M2.5` → `oc/space-bunny-free` → `oc/jev-1.13-free`
(OpenCode Free, no-auth, selalu tersedia).
Kiro (`kr/*`) perlu di-connect dulu di Dashboard → Providers (OAuth browser).

Fitur token saver aktif di 9Router: RTK (built-in), Headroom (localhost:8787),
Caveman + Ponytail (level full), observability. Caveman/Ponytail mengubah gaya
keluaran LLM — jika caption terasa terlalu pendek/aneh, matikan di Dashboard →
Endpoint settings, atau kirim header `X-9Router-Token-Saver: off`.

## Hati-hati

- Hanya satu instance bot per token Telegram (long polling).
- TikTok app masih menunggu audit scope `video.publish`; alur unggah manual.
- Kredensial TikTok sandbox di `.env` — jangan commit `.env` (sudah di `.gitignore`).
