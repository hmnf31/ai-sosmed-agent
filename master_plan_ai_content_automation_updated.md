# Master Plan — AI Content Automation Assistant
**Versi:** 2.0 | **Tanggal:** 5 Oktober 2026 | **Status:** Rancangan teknis

## 1. Ringkasan
Dokumen ini menggabungkan rancangan asisten produksi konten AI yang dikendalikan melalui Telegram. Sistem melakukan riset bila diperlukan, menyusun konsep dan naskah, membuat/menyiapkan aset visual, menghasilkan voice over dan sound effects, membangun timeline, merender melalui Remotion, melakukan QA, lalu mengirimkan preview dan hasil final ke Telegram untuk persetujuan.

Empat akun:
1. **Chess Club/TCO:** turnamen mingguan, TCO League, Arena Kings, edukasi dan recap catur.
2. **Wedding Organizer:** inspirasi, tren, edukasi, portofolio dan promosi.
3. **MLBB:** patch, hero, counter, meta, tips/trik, MPL/esports dan livestream.
4. **Fashion Affiliate:** outfit ideas, styling, showcase produk, rekomendasi dan CTA affiliate.

Auto-posting sosial media belum menjadi ketergantungan MVP karena API masih dalam proses peninjauan. Hasil akan disiapkan untuk publikasi manual. Prioritas deployment: gratis/no-card sebisa mungkin, tanpa tagihan tak terduga. Free tier tetap memiliki kuota dan kebijakan yang perlu diperiksa.

## 2. Tujuan dan prinsip
- Telegram menjadi pusat kendali.
- OpenRouter menangani perencanaan AI, naskah, metadata dan evaluasi.
- Python menjadi orkestrator.
- Remotion menjadi mesin komposisi dan rendering video berbasis React.
- Asset Generator menyiapkan visual per scene.
- MiniMax digunakan untuk TTS/voice over dan SFX setelah endpoint, model, kuota dan biaya diverifikasi.
- Cloudflare Worker menangani webhook/routing ringan; D1 menyimpan status dan metadata.
- GitHub Actions menjalankan pekerjaan berat.
- Google Sheets tetap menjadi sumber data operasional TCO.
- Pisahkan brand profile, template dan watermark tiap akun.
- Minta approval pengguna sebelum final render; jangan menyatakan konten sudah diposting jika baru dikirim.
- Simpan API key sebagai secrets, bukan di repository atau log.
- Jangan menjalankan Playwright, Chromium, FFmpeg atau rendering berat di Cloudflare Worker.

## 3. Profil akun dan workflow

### 3.1 Chess Club/TCO
**Gaya:** kompetitif, komunitas, informatif, premium sport.

**Turnamen mingguan:** pengguna memasukkan empat link Chess.com per bulan ke Google Sheets. Kolom yang disarankan: `event_id`, `title`, `date`, `start_time`, `duration`, `format` (Bullet/Blitz/Rapid), `platform`, `link`, `status`, `notes`. Bot membaca event minggu berjalan dan membuat pesan WhatsApp siap bagikan berisi judul, tanggal, waktu WIB, format, durasi, tautan dan ajakan. Jangan mengarang link atau data yang tidak ada.

**TCO League:** mengolah hasil/klasemen yang tersedia menjadi standings, berita pekanan, recap dan pengumuman internal. Bila data tidak lengkap, tandai kekurangan atau minta data.

**Arena Kings:** jadwal dikonfigurasi (umumnya Rabu awal bulan sekitar 23.00 WIB); link resmi dapat baru tersedia sekitar dua jam sebelum acara. Bot menyiapkan poster/motion poster dan pengumuman tanpa link, lalu memperbaruinya saat pengguna memberikan link yang benar.

### 3.2 Wedding Organizer
**Gaya:** elegan, hangat, minimal, romantis, profesional. Jenis konten: inspirasi dekorasi/venue/tema, tips persiapan, checklist, edukasi, portofolio, recap, promosi dan tren IG/TikTok. Dukung carousel, multi-image, Reels vertikal, Story dan poster. Tren menjadi inspirasi, bukan alasan menyalin konten atau aset kreator lain.

### 3.3 MLBB
**Gaya:** gaming/esports, energik, kontras tinggi, terbaca di ponsel. Jenis konten: patch/balance, hero spotlight, build/emblem jika tersedia, counter/sinergi, meta, tips, MPL/esports, livestream dan recap. Klaim yang bergantung pada patch, jadwal, hasil atau berita harus diteliti dari sumber yang sesuai dan diberi tanggal. Pisahkan fakta dari opini/prediksi.

### 3.4 Fashion Affiliate
**Gaya:** clean editorial, lifestyle, modern dan autentik. Jenis konten: outfit ideas, mix-and-match, styling, product showcase, perbandingan, tips bahan/ukuran/perawatan jika bersumber, video pendek dengan hook/manfaat/CTA. Harga, stok, diskon dan spesifikasi harus berasal dari input atau sumber yang dapat diperiksa. Sertakan disclosure affiliate sesuai ketentuan.

## 4. Arsitektur

```text
Telegram -> Cloudflare Worker (webhook/auth/router)
                    |-> Cloudflare D1 (jobs/status/history)
                    |-> Trigger GitHub Actions
                              |
                         Python Runner
                         | OpenRouter
                         | Research/sources
                         | Google Sheets (TCO)
                         | Image Asset Generator
                         | MiniMax TTS/SFX
                         | Timeline JSON
                         | Remotion + FFmpeg pipeline
                         | QA
                              |
                         Telegram preview/approval/final
```

| Komponen | Tanggung jawab |
|---|---|
| Telegram | Perintah, upload, preview, approval, revisi, notifikasi |
| Cloudflare Worker | Validasi webhook, auth, dedupe, enqueue/trigger |
| D1 | Status job, event, approval, konfigurasi ringan |
| GitHub Actions | Python, Node/Remotion, browser automation bila perlu, media render |
| OpenRouter | Planner, scriptwriter, metadata, QA berbantuan |
| Google Sheets | Jadwal, tautan, data liga TCO |
| Asset Generator | Gambar/visual per scene, normalisasi, manifest |
| MiniMax | TTS dan SFX melalui adapter |
| Remotion | Scene, teks, animasi, audio, caption, watermark dan render |
| FFmpeg | Utilitas media dalam pipeline render/konversi |
| R2/object storage | Opsional; bukan syarat MVP |

Worker hanya untuk tugas ringan. GitHub Actions menjalankan pekerjaan berat dan mengirim status kembali ke D1/Telegram. Gunakan `VIDEO_ENGINE=legacy` atau `VIDEO_ENGINE=remotion`; pertahankan `video_maker.py` (Pillow + FFmpeg) sebagai fallback sampai Remotion stabil.

## 5. Biaya dan deployment
- Gunakan Cloudflare Workers/D1 free tier jika memenuhi kebutuhan dan batas paket terkini.
- GitHub Actions free minutes bergantung pada jenis repository dan kebijakan GitHub; monitor pemakaian. Jangan menganggap kapasitas gratis tanpa batas.
- Jika kuota habis tanpa metode pembayaran, job dapat tertahan/diblokir sesuai kebijakan layanan; verifikasi pengaturan billing/quota sebelum deploy.
- OpenRouter dan MiniMax dapat menimbulkan biaya tergantung model/endpoint. Terapkan allowlist model, batas job, preview rendah, retry terbatas dan estimasi penggunaan.
- Jangan aktifkan R2 atau layanan berbayar sebelum kebutuhan dan billing dipahami.
- Mulai dengan GitHub artifacts/Telegram dan metadata D1; rancang storage permanen belakangan.
- Hindari polling workflow, cache dependencies, batasi concurrency/durasi dan sediakan `/usage`.

## 6. Alur end-to-end
1. Terima perintah Telegram.
2. Identifikasi akun, tujuan, format, durasi dan bahasa; minta klarifikasi bila penting.
3. Riset jika konten aktual/faktual memerlukannya.
4. Buat dan validasi `content_plan.json`.
5. Buat script dan shot list.
6. Generate/siapkan visual per scene.
7. Buat VO/SFX bila diaktifkan.
8. Susun `timeline.json` berbasis frame.
9. Render preview Remotion.
10. Jalankan QA awal.
11. Kirim preview ke Telegram: Approve / Revise / Regenerate scene / Cancel.
12. Setelah approval, render final dan jalankan QA final.
13. Kirim video/gambar, caption, CTA, hashtag dan sumber/notes.
14. Arsipkan metadata dan status; pengguna mempublikasikan manual sampai integrasi resmi tersedia.

Contoh perintah: `/start`, `/account`, `/new`, `/trend`, `/script`, `/image`, `/voice`, `/sfx`, `/video`, `/preview`, `/approve <job_id>`, `/revise <job_id> <instruksi>`, `/regenerate <job_id> <bagian>`, `/status <job_id>`, `/history`, `/usage`, `/help`. Natural language dapat didukung oleh router.

Status job: `received`, `queued`, `researching`, `planning`, `generating_assets`, `generating_audio`, `building_timeline`, `rendering_preview`, `qa_preview`, `awaiting_approval`, `rendering_final`, `qa_final`, `delivered`, `failed`, `cancelled`. Semua transisi diberi timestamp dan error aman.

## 7. Content Plan JSON
AI tidak langsung membuat video. Ia menghasilkan struktur data tervalidasi yang menjadi masukan bagi asset, audio dan renderer.

Contoh ringkas:
```json
{
  "schema_version": "1.0",
  "job_id": "job_0001",
  "account": "mlbb",
  "content_type": "hero_explainer",
  "format": "vertical_short",
  "language": "id-ID",
  "aspect_ratio": "9:16",
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "target_duration_sec": 35,
  "title": "Judul",
  "hook": "Hook 1-3 detik",
  "caption": "Draft caption",
  "hashtags": ["#MLBB"],
  "research": {"required": true, "sources": [], "checked_at": null, "fact_check_status": "pending"},
  "voiceover": {"enabled": true, "provider": "minimax", "segments": [{"segment_id": "vo_01", "text": "Narasi", "estimated_duration_sec": 4}]},
  "scenes": [{"scene_id": "scene_01", "duration_sec": 4, "purpose": "hook", "visual_type": "image", "visual_prompt": "Visual orisinal", "on_screen_text": "HOOK", "voiceover_segment_ids": ["vo_01"], "sfx_cues": [], "transition_in": "cut", "transition_out": "cut"}],
  "branding": {"profile": "mlbb", "template_id": "mlbb_vertical_hook", "watermark_variant": "primary"},
  "approval": {"required": true, "status": "pending"}
}
```

Validator memeriksa account/template, format, durasi scene, referensi VO/aset, sumber, watermark dan file path. Semua waktu rendering dikonversi ke frame menurut FPS.

## 8. Image Asset Generator
**Pipeline:** baca plan → ekstrak visual per scene → bentuk prompt sesuai brand → panggil provider adapter → simpan file → normalisasi format/rasio/dimensi → crop/fit → QA file → tulis manifest → tandai kegagalan/fallback.

Aset dapat berupa gambar AI, upload pengguna, logo/ikon, grafik programatik, footage berizin atau materi resmi yang penggunaannya sesuai. Hindari penggunaan ulang materi berhak cipta tanpa izin. Jangan menyajikan aset buatan sebagai logo, UI atau materi resmi. Catat provenance dan status hak pakai.

Contoh `asset_manifest.json`:
```json
{
  "schema_version": "1.0",
  "job_id": "job_0001",
  "assets": [{
    "asset_id": "asset_scene_01",
    "scene_id": "scene_01",
    "type": "image",
    "path": "assets/scene_01.webp",
    "purpose": "hook_visual",
    "source_type": "ai_generated",
    "provider": "configured_provider",
    "prompt_version": "1",
    "width": 1024,
    "height": 1792,
    "status": "ready",
    "usage_rights": "review_required"
  }]
}
```
Provider modular; API key tidak pernah disimpan dalam manifest. Bila generator gagal, gunakan placeholder brand atau minta upload. Hindari retry tanpa batas.

## 9. MiniMax Voice Over dan SFX
MiniMax menjadi provider melalui adapter `TTSProvider` dan `SFXProvider`. Sebelum integrasi, verifikasi dokumentasi resmi: endpoint, model, voice ID, bahasa, format audio, limit, lisensi dan harga. Detail tersebut dapat berubah dan tidak boleh diasumsikan.

Alur: script final → segmentasi per scene → normalisasi pelafalan → pilih voice profile → panggil TTS → simpan audio mentah → validasi durasi/format/clipping → mapping ke timeline → buat SFX cue → atur level VO/SFX/BGM terpisah → preview/approval. Musik latar harus berasal dari sumber dengan hak penggunaan yang sesuai; TTS/SFX bukan berarti musik otomatis bebas pakai.

Contoh manifest:
```json
{
  "schema_version": "1.0",
  "job_id": "job_0001",
  "audio": [{
    "audio_id": "vo_01",
    "type": "voiceover",
    "provider": "minimax",
    "path": "audio/vo_01.wav",
    "scene_id": "scene_01",
    "text_ref": "voiceover.segments.vo_01",
    "voice_profile": "mlbb_narrator",
    "duration_sec": null,
    "status": "ready"
  }]
}
```
Simpan audio mentah dan metadata agar render ulang tidak memanggil API lagi. Terapkan cache/hash, batas penggunaan dan `audio.enabled=false` sebagai fallback. Wedding memakai audio lembut/terukur; MLBB boleh lebih dinamis tetapi VO tetap jelas.

## 10. Remotion dan Timeline
Remotion adalah automatic editor yang merender struktur data ke video, bukan AI yang menentukan seluruh editing secara bebas. Komponen:
- `Root`, `Composition`
- `SceneRenderer`
- `ImageScene`, `VideoScene`, `TextScene`
- `AudioTrack`, `CaptionTrack`
- `BrandLayer`
- `Transition`, motion presets dan lower-third

`timeline.json` adalah sumber kebenaran. Setiap item memiliki ID, track, `start_frame`, `duration_frames`, referensi asset/audio, volume/fit/motion dan transisi. Track terpisah untuk visual, teks, VO, SFX, BGM, caption dan branding. Validator memastikan tidak ada referensi hilang, durasi tidak valid atau overlap tak disengaja.

Contoh ringkas:
```json
{
  "schema_version": "1.0",
  "job_id": "job_0001",
  "composition_id": "MLBBVerticalExplainer",
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "duration_frames": 1050,
  "tracks": [
    {"track_id": "visuals", "type": "visual", "items": [{"item_id": "visual_01", "scene_id": "scene_01", "asset_id": "asset_scene_01", "start_frame": 0, "duration_frames": 120, "fit": "cover", "motion": "slow_zoom"}]},
    {"track_id": "voice", "type": "audio", "items": [{"item_id": "vo_01", "audio_id": "vo_01", "start_frame": 0, "duration_frames": 120, "volume": 1.0}]},
    {"track_id": "branding", "type": "overlay", "items": [{"item_id": "watermark", "template_id": "mlbb_vertical_hook", "start_frame": 0, "duration_frames": 1050}]}
  ]
}
```

Preview dirender rendah (misalnya 540×960); final mengikuti preset (misalnya 1080×1920, 30 FPS, H.264). Simpan input props, versi template, plan, manifest dan timeline untuk reproduksibilitas. Watermark menjadi layer Remotion, bukan tempelan manual pascarender.

Pertahankan renderer lama `video_maker.py` melalui feature flag `VIDEO_ENGINE=legacy|remotion`. Migrasi hanya dinyatakan selesai setelah audio sync, branding, caption, seluruh rasio dan GitHub Actions teruji.

## 11. Brand Profile dan Template Registry
Setiap akun memiliki tone of voice, audience, tujuan, gaya visual, warna, font, logo, watermark, safe zone, CTA, hashtag, disclosure dan larangan.

```text
branding/
  chess/{brand.json,colors.json,watermark/,fonts/,templates/}
  wedding/{brand.json,colors.json,watermark/,fonts/,templates/}
  mlbb/{brand.json,colors.json,watermark/,fonts/,templates/}
  fashion/{brand.json,colors.json,watermark/,fonts/,templates/}
```

Watermark varian `primary`, `light`, `dark`. Validasi account/template/watermark sebelum render; jika wajib namun hilang, hentikan final render. Template dipilih melalui `account -> category -> format -> style -> watermark`.

Pisahkan **content template** (hook, isi, CTA, caption) dan **visual template** (layout, warna, font, animasi, transisi). Format:
- Vertical: `hook_explainer`, `listicle`, `news_update`, `tutorial`, `comparison`, `storytelling`, `product_showcase`.
- Square: `announcement`, `infographic`, `quote`, `standings`.
- Landscape: `youtube`, `presentation`, `longform`.

## 12. Research dan Fact-check
Riset diperlukan untuk tren, patch/meta, esports, jadwal/hasil, tren Wedding, serta data produk yang berubah. Simpan `source_id`, URL, judul, publisher, tanggal publikasi bila ada, `retrieved_at`, klaim yang didukung dan status verifikasi. Utamakan sumber resmi untuk data resmi; pisahkan fakta, analisis, prediksi dan opini. Jika sumber tidak cukup atau bertentangan, tandai ketidakpastian dan minta review. Jangan menyalin naskah atau visual pihak lain.

## 13. Telegram UX dan Approval
Menu: Buat Konten, Cari Tren, Jadwal TCO, TCO League, Arena Kings, Riwayat, Brand Settings, Usage/Status.

Kartu status contoh:
```text
JOB #0001 — MLBB
Status: Generating assets
Format: Vertical 9:16 | Target: 35 detik
Progress: 4/7 scene
```
Setelah preview sediakan **Approve**, **Revise**, **Regenerate scene**, **Cancel**. Approval terikat pada `job_id` dan versi preview; perubahan setelah preview membatalkan approval lama. Final delivery berisi media, caption, CTA, hashtag, sumber/notes dan spesifikasi file. Status harus menyatakan “siap ditinjau/dipublikasikan”, bukan “sudah diposting” tanpa konfirmasi posting.

## 14. Data Model D1
Tabel yang disarankan:
- `jobs`: `job_id`, user/chat, account, content type, status, progress, input, plan, timeline, safe error, timestamps.
- `job_events`: event ID, job ID, stage, status, safe message, timestamp.
- `assets`: asset ID, job/scene, type, storage/artifact path, source, provider, metadata, status.
- `audio_assets`: audio ID, job/scene, type, provider, path, metadata, status.
- `brand_profiles`: account ID, profile JSON, version, updated timestamp.
- `telegram_updates`: Telegram `update_id` unique, received/processed timestamps, status.
- `approvals`: approval ID, job ID, preview version, approver, decision, revision note, timestamp.

Google Sheets tetap menjadi source of truth TCO di tahap awal. D1 dapat menyimpan snapshot/cache bila berguna, tetapi hindari duplikasi data yang tidak perlu. Jangan simpan video besar dalam database.

## 15. Repository Structure
```text
project/
  bot/{telegram,router,handlers,keyboards}/
  api/{openrouter,minimax,image_provider}/
  ai/{prompts,content_planner,script_writer,fact_checker,metadata}/
  research/{trends,web,sources}/
  accounts/{chess,wedding,mlbb,fashion}/
  assets/{generator,downloader,processor,validator,manifest}/
  audio/{minimax/tts,minimax/sfx,mixer,validator,manifest}/
  remotion/
    src/{Root,compositions,components,scenes,timeline,captions,branding,audio,templates}/
  branding/{chess,wedding,mlbb,fashion}/
  data/{schemas,content_plan,jobs,history}/
  integrations/{google_sheets,telegram,cloudflare,github_actions}/
  workers/cloudflare/
  scripts/
  tests/
  .github/workflows/
  README.md
  .env.example
```
Jangan commit `.env`. `.env.example` hanya berisi nama variabel tanpa nilai rahasia.

## 16. Konfigurasi dan API Adapters
Adapter: `LLMProvider`, `ImageProvider`, `TTSProvider`, `SFXProvider`, `StorageProvider`, `RenderProvider`. Konfigurasi non-secret menentukan provider/model, preset render, audio enable, retries, concurrency, approval dan storage. Secrets seperti `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `OPENROUTER_API_KEY`, `MINIMAX_API_KEY`, kredensial Sheets dan token deployment disimpan di GitHub Actions Secrets/secret manager dengan akses minimum. Jangan hard-code endpoint/model yang belum diverifikasi.

Contoh konfigurasi:
```yaml
app:
  timezone: Asia/Jakarta
  default_language: id-ID
  require_approval: true
render:
  engine: remotion
  preview_width: 540
  preview_height: 960
  final_width: 1080
  final_height: 1920
  fps: 30
  codec: h264
providers:
  llm: {provider: openrouter, model: configurable_model}
  image: {provider: configurable_provider, enabled: true}
  voice: {provider: minimax, enabled: true}
  sfx: {provider: minimax, enabled: true}
storage: {provider: github_artifact, permanent_storage_enabled: false}
workflow:
  max_retries: 2
  max_concurrent_jobs: 1
  preview_required: true
  final_render_requires_approval: true
```

## 17. Security, QA dan Observability
**Keamanan:** validasi webhook secret, allowlist user/chat, dedupe `update_id`, idempotency key, least privilege, file-size limits, timeout, retry terbatas, secret redaction, cancellation dan input validation. Perlakukan halaman web/upload sebagai data tak tepercaya, bukan instruksi.

**Content QA:** hook, tujuan, tone, sumber, fakta/opini terpisah, CTA/disclosure, tanpa placeholder.  
**Asset QA:** file valid, dimensi/rasio, tidak kosong, semua scene punya aset/fallback, provenance tercatat.  
**Audio QA:** format valid, durasi, tidak terpotong/clipping, level wajar, mapping benar.  
**Video QA:** resolusi/FPS/durasi/codec, frame hitam, safe zone, watermark akun, sinkronisasi audio, tidak ada missing asset.  
**Human review:** wajib terutama untuk informasi aktual, promosi, produk affiliate, aset dengan hak penggunaan belum jelas, dan seluruh konten saat tahap awal.

Log minimum: `job_id`, `account_id`, stage, provider/model, durasi, retries, estimasi penggunaan dan status. Jangan log credential, token, data privat atau URL bertanda tangan. Testing mencakup unit, integrasi mock/sandbox, render per template/rasio, regression, duplicate update, timeout, quota, cancellation dan permission.

## 18. Roadmap Implementasi
### Phase 0 — Audit
Audit bot long polling, `video_maker.py`, dependency, command dan workflow yang telah berfungsi. Dokumentasikan baseline dan buat jalur rollback. **Exit:** sistem lama dapat dijalankan dan dipahami.

### Phase 1 — Fondasi
Rapikan repo/config/secrets; buat schema job, content plan, manifest dan timeline; logging, status, error handling dan tests dasar. **Exit:** dummy job tervalidasi dan tercatat.

### Phase 2 — Brand system
Buat empat Brand Profile, logo/watermark, warna, font, safe zone dan template statis lintas format. **Exit:** satu output dummy per akun memiliki branding benar.

### Phase 3 — Remotion foundation
Inisialisasi Remotion, komponen scene/media/text/audio/BrandLayer, input props dan renderer timeline. Pertahankan legacy feature flag; uji GitHub Actions. **Exit:** timeline dummy dirender stabil.

### Phase 4 — Content Planner
Hubungkan OpenRouter; buat planner, script, shot list, caption dan schema validation. **Exit:** permintaan Telegram menghasilkan plan valid.

### Phase 5 — Research
Bangun adapter, source metadata, tanggal, fact-check dan fallback. **Exit:** konten aktual menyimpan sumber/status.

### Phase 6 — Image Asset Generator
Buat adapter, generate/prepare aset, normalisasi, manifest, fallback dan QA. **Exit:** setiap scene memiliki aset valid atau fallback.

### Phase 7 — MiniMax TTS/SFX
Verifikasi API dan biaya resmi; implementasi TTS/SFX adapter, voice profiles, audio manifest, cache, mixer dan QA. **Exit:** audio sinkron dapat dipreview/render; mode audio-off tersedia.

### Phase 8 — Timeline/captions
Bangun timeline frame-based, track visual/text/VO/SFX/BGM/caption/brand, transitions, validator dan style subtitle. **Exit:** plan lengkap menghasilkan video sinkron.

### Phase 9 — Telegram review
Preview, approve/revise/regenerate/cancel, versioned approval dan history. **Exit:** satu siklus produksi selesai dari Telegram.

### Phase 10 — Deployment
Migrasi webhook ke Worker; D1, trigger Actions, artifacts, secrets, retries, timeout, concurrency dan monitoring. **Exit:** Telegram memicu runner dan menerima status/hasil.

### Phase 11 — Workflow per akun
TCO Sheets, League, Arena Kings; Wedding trend/multi-image; MLBB update/fact-check; Fashion affiliate/disclosure. **Exit:** semua akun punya alur teruji.

### Phase 12 — Production hardening
Failure recovery, biaya per konten, retensi/cleanup, dokumentasi deploy/rollback/secret rotation. Auto-posting hanya setelah API resmi tersedia. **Exit:** penggunaan rutin terkontrol dan dapat dipulihkan.

## 19. MVP yang Disarankan
Mulai dengan satu jalur kecil:
1. Telegram memilih akun.
2. OpenRouter membuat Content Plan JSON valid.
3. Satu template Remotion vertical dan satu square.
4. Image generator menghasilkan gambar statis.
5. TTS MiniMax opsional; SFX setelah pipeline dasar stabil.
6. Preview dikirim ke Telegram.
7. Approval/revisi sederhana.
8. Status job tersimpan.
9. TCO weekly schedule membaca Google Sheets.
10. Final media dan caption dikirim untuk posting manual.

## 20. Contoh Alur MLBB
Perintah: “Buat video 35 detik tips hero, TikTok vertikal.”
Router memilih MLBB → riset patch/hero → planner membuat hook/script/scenes → fact-check → generator menyiapkan visual → MiniMax membuat VO/SFX → Timeline Builder mengubah durasi ke frame → Remotion preview → QA → Telegram approval → final 1080×1920, 30 FPS, H.264 sesuai preset → QA final → kirim video/caption/hashtags/sumber. Pengguna mengunggah manual.

## 21. Contoh Alur Wedding
Perintah: “Buat Reels inspirasi intimate wedding, hangat dan elegan.”
Router memilih Wedding → riset bila dibutuhkan → planner membuat storytelling/shot list → aset orisinal atau upload pengguna → VO opsional dan musik berizin → Remotion dengan font/warna/transisi/watermark Wedding → preview → revisi/approval → final dan caption dikirim ke Telegram.

## 22. Workflow Operasional TCO
**Mingguan:** baca sheet → validasi event → susun pesan WhatsApp → kirim draft Telegram → pengguna review dan bagikan.  
**League:** input hasil/standings → validasi → buat update dan visual → review → bagikan.  
**Arena Kings:** siapkan materi sesuai jadwal tanpa link → review → saat link resmi diterima, perbarui CTA/pesan → review dan bagikan. Tidak boleh mengarang link, hasil atau jadwal.

## 23. Risiko dan Mitigasi
| Risiko | Mitigasi |
|---|---|
| API sosial belum disetujui | Posting manual sementara |
| Kuota Actions habis | Monitor, preview ringan, concurrency/retry terbatas |
| Provider AI berubah | Adapter dan konfigurasi |
| MiniMax API/harga berubah | Verifikasi docs/dashboard sebelum aktivasi |
| Asset generation gagal | Retry terbatas, placeholder/upload manual |
| Fakta aktual salah | Sumber, fact-check, human review |
| Watermark tertukar | Validasi account/template |
| Render gagal/lama | Timeout, status, resume per stage |
| Update Telegram ganda | Dedupe dan idempotency |
| Storage membengkak | Retensi dan cleanup |
| Tagihan tak terduga | Jangan aktifkan billing tanpa persetujuan, limit internal |
| Hak cipta | Provenance dan aset berizin/orisinal |
| Approval kedaluwarsa | Versioned preview dan invalidasi approval lama |

## 24. Checklist Go-Live
- [ ] Webhook Telegram dan allowlist aman.
- [ ] Dedupe dan idempotency teruji.
- [ ] D1 mencatat job/event/approval.
- [ ] Actions berjalan dengan least privilege.
- [ ] Secrets tidak masuk repo/log.
- [ ] Quota, retry, timeout dan cancellation diuji.
- [ ] Plan, manifest dan timeline tervalidasi.
- [ ] Template dan watermark semua akun benar.
- [ ] Audio/caption sinkron dan safe zone aman.
- [ ] Hak penggunaan aset diperiksa.
- [ ] Preview dan approval wajib aktif.
- [ ] History dan recovery tersedia.
- [ ] Prosedur publikasi manual tersedia.
- [ ] Auto-posting tetap nonaktif sampai API resmi disetujui.

## 25. Definisi Selesai
Versi produksi awal tercapai saat pengguna dapat memilih satu dari empat akun, memberi instruksi melalui Telegram, menerima plan valid, menyiapkan aset/audio, merender melalui Remotion, melihat preview, meminta revisi, menyetujui final, menerima media/caption, melihat status/history, menjalankan workflow TCO dari Sheets, dan mengoperasikan seluruhnya dengan pemisahan brand serta kontrol biaya.

## 26. Referensi Implementasi
Dokumentasi dan ketentuan vendor dapat berubah; verifikasi kembali sebelum deployment:
- Remotion: https://www.remotion.dev/docs/
- Parameterized rendering: https://www.remotion.dev/docs/parameterized-rendering
- Renderer: https://www.remotion.dev/docs/renderer
- CLI: https://www.remotion.dev/docs/cli
- Server-side rendering: https://www.remotion.dev/docs/ssr
- Cloudflare Workers: https://developers.cloudflare.com/workers/
- Cloudflare D1: https://developers.cloudflare.com/d1/
- Cloudflare R2: https://developers.cloudflare.com/r2/
- GitHub Actions: https://docs.github.com/actions
- Telegram Bot API: https://core.telegram.org/bots/api
- OpenRouter: https://openrouter.ai/docs
- MiniMax: gunakan dokumentasi API resmi dan dashboard akun untuk endpoint TTS/SFX, model, format, kuota dan biaya aktual.

## 27. Langkah Berikutnya
1. Audit bot dan renderer lama.
2. Finalisasi schema JSON.
3. Buat satu komposisi Remotion dummy dengan image, text, audio placeholder dan watermark.
4. Render lewat GitHub Actions.
5. Hubungkan satu job Telegram end-to-end.
6. Tambahkan image provider lalu MiniMax setelah detail API/harga diverifikasi.
7. Uji satu contoh per brand.
8. Perluas fitur setelah jalur kecil stabil.

**Prinsip utama:** bangun satu jalur produksi yang kecil, berulang dan dapat diuji terlebih dahulu. Perluas secara bertahap tanpa mengorbankan akurasi, pemisahan brand, hak penggunaan aset, approval pengguna dan kontrol biaya.
