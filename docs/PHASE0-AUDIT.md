# Phase 0 — Audit Baseline

**Tanggal:** 6 Oktober 2026
**Status:** Selesai (exit criteria terpenuhi)
**Tujuan:** Mendokumentasikan kondisi sistem lama sebelum implementasi master plan dengan OpenClaw, termasuk jalur rollback.

## 1. Hasil pengujian baseline

| Pemeriksaan | Hasil |
|---|---|
| `pytest -q` (venv Python 3.13.1) | **326 passed** dalam 30,20 detik |
| Import seluruh modul inti (`telegram_bot`, `router`, `engines`, `history`, `accounts`, `branding/*`, `chess/*`) | OK |
| Kondisi proses bot | Tidak ada proses bot berjalan (aman untuk perubahan) |
| `gh auth status` | Login sebagai `hmnf31`, protokol HTTPS — siap dipakai `gh workflow run` |

Baseline ini adalah patokan: semua fase berikutnya harus menjaga `pytest -q` tetap hijau.

## 2. Komponen sistem lama

### 2.1 Entry point
- `bot.py` — bot Telegram interaktif, long polling (`getUpdates`) via `utils/telegram_bot.py:791` (`run()`). Dijalankan manual/lewat `run.bat`.
- `main.py` — satu siklus otomatis (riset tren → caption AI → render media → kirim ke Telegram/publish). Dijalankan GitHub Actions `heartbeat.yml` tiap hari 08:00 WIB (cron `0 1 * * *`), mode `DRY_RUN=true` (kirim preview, tanpa posting otomatis).

### 2.2 Alur bot interaktif
```
Telegram (long polling)
  → allowlist chat (TELEGRAM_CHAT_ID + TELEGRAM_ALLOWED_CHATS)
  → handle_message / handle_callback (utils/telegram_bot.py)
      ├── router: chat bebas → intent {account, task, topic, format, jumlah}
      │     (utils/router.py — keyword + fallback, OPERATIONAL_TASKS vs CONTENT_TASKS)
      ├── engines: brief per akun (mlbb/wedding/fashion/chess)
      │     (utils/engines/__init__.py — fact-check rules per akun)
      ├── content_generator + ai_generator (OpenRouter)
      ├── image_maker / video_maker (Pillow + FFmpeg; TIDAK ada VIDEO_ENGINE flag)
      ├── chess: tco.py, liga.py, arena.py, spreadsheet.py, webtco.py
      ├── branding: loader/validator/style_registry + watermark
      ├── history: dedupe topik + riwayat (CONTENT_DB_PATH)
      └── keyboards: menu tombol + callback query
  → hasil dikirim ke Telegram untuk posting manual (tanpa auto-post)
```

### 2.3 GitHub Actions (repo `hmnf31/ai-sosmed-agent`, branch `main`)
- `heartbeat.yml` — cron harian menjalankan `main.py`; secrets sudah terisi (OPENROUTER_API_KEY, TELEGRAM_*, IG_*, TIKTOK_*), Python 3.13, ffmpeg, Playwright chromium.
- `pages.yml` — deploy `docs/` ke GitHub Pages (verifikasi TikTok + halaman app).
- **Belum ada workflow render** (`workflow_dispatch` untuk Remotion belum ada).

### 2.4 Konfigurasi & secrets
- `.env` lokal (jangan di-commit): nama-nama variabel sesuai `.env.example` plus `NINEROUTER_URL`, `NINEROUTER_KEY` (router lokal, terkait folder `9router/` yang belum di-track).
- `.env.example` hanya berisi nama variabel (aman).
- GitHub Actions secrets sudah tersedia untuk fase render nanti: `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

## 3. Kesenjangan terhadap master plan

| Kebutuhan master plan | Kondisi sekarang |
|---|---|
| Remotion + `timeline.json` + flag `VIDEO_ENGINE=legacy\|remotion` | Belum ada; hanya `utils/video_maker.py` (Pillow + FFmpeg) |
| Job store dengan status (`received`…`delivered`) | Belum ada; hanya `history` sederhana |
| Content Plan JSON + validator schema | Setengah jalan: `data/schemas/content_plan_schema.json` ada, planner/belum memakainya |
| Approval preview/final berbasis `job_id` | Belum ada (bot lama langsung mengirim hasil) |
| Render via GitHub Actions (`workflow_dispatch`) | Belum ada |
| OpenClaw (channel, agents, skills, automations) | Belum terpasang (CLI global `openclaw@2026.9.2` sudah terinstal) |
| 4 agent terpisah (chess/wedding/mlbb/fashion) | Belum; satu proses bot melayani semua akun |
| MiniMax TTS/SFX, image provider adapter | Belum ada |

## 4. Kondisi Git & jalur rollback

Kondisi working tree saat audit (belum di-commit):
- Diubah: `.env.example`, `template-klub-tco.md`, `utils/ai_generator.py`, `utils/content_generator.py` (22 insertions, 6 deletions)
- Belum di-track: `.kilo/`, `9router/`, `data/`, `run.bat`
- Branch: `main`; remote: `https://github.com/hmnf31/ai-sosmed-agent.git`

**Aturan rollback fase berikutnya:**
1. Bot lama TIDAK dihapus atau diubah perilakunya sampai jalur OpenClaw MVP stabil. `bot.py` tetap bisa dijalankan kapan pun lewat `run.bat`.
2. Sebelum perubahan besar di fase berikutnya: commit baseline dulu (`git add -A && git commit`) agar setiap fase punya titik kembalian jelas.
3. Jika jalur OpenClaw gagal: hentikan Gateway, jalankan ulang `run.bat` — sistem kembali persis ke kondisi audit ini.
4. Jangan mengubah workflow `heartbeat.yml` yang sudah berjalan; workflow render baru dibuat terpisah (`render.yml`).

## 5. Exit criteria Phase 0

- [x] Seluruh test hijau (326 passed)
- [x] Baseline terdokumentasi (dokumen ini)
- [x] Komponen & alur sistem lama dipahami
- [x] Jalur rollback jelas (bot lama tetap utuh, `run.bat`)
- [x] `gh` terautentikasi untuk trigger GitHub Actions

**Langkah berikutnya:** Phase 1 — Fondasi OpenClaw (`openclaw onboard`, gateway service, provider OpenRouter, agent `mlbb`, channel Telegram).
