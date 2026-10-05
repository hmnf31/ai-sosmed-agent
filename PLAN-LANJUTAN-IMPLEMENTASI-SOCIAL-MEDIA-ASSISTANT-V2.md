# PLAN LANJUTAN IMPLEMENTASI — SOCIAL MEDIA ASSISTANT

## 0. Dokumen Ini Untuk Apa

Dokumen ini adalah **lanjutan dan turunan implementasi** dari plan awal `PLAN-UPDATE-SOCIAL-MEDIA-ASSISTANT.md`.

Tujuannya bukan mengulang daftar fitur, tetapi mengubah rencana menjadi **urutan pembangunan yang bisa langsung dikerjakan di repository**, mulai dari kondisi bot sekarang sampai menjadi Social Media Assistant yang siap dikembangkan ke auto-posting.

Fokus fase ini:

- mempertahankan bot yang sekarang sudah berfungsi;
- menambahkan 4 akun utama;
- memisahkan content workflow dan chess operational workflow;
- menambahkan database/history;
- menambahkan spreadsheet workflow untuk klub catur;
- meningkatkan research engine;
- meningkatkan generator text/image/video;
- membuat Telegram sebagai dashboard;
- menyiapkan deployment tanpa bergantung pada PC lokal;
- menjaga TikTok/Instagram posting tetap terpisah sampai benar-benar siap.

---

# 1. KONDISI AWAL YANG HARUS DIPERTAHANKAN

Sistem saat ini sudah mempunyai jalur utama:

```text
Telegram
  ↓
account matching
  ↓
request resolving
  ↓
research
  ↓
OpenRouter
  ↓
image/video render
  ↓
Telegram
```

Komponen yang sudah ada dan jangan langsung dibongkar:

```text
bot.py
utils/telegram_bot.py
utils/accounts.py
utils/scraper.py
utils/content_generator.py
utils/image_maker.py
utils/video_maker.py
utils/notifier.py
```

Versi lama harus tetap dapat dijalankan selama proses refactor.

---

# 2. PRINSIP PEMBANGUNAN

## 2.1 Jangan rewrite total

Gunakan pendekatan **incremental refactor**.

```text
Kode lama
   ↓
Refactor satu modul
   ↓
Test
   ↓
Integrasi
   ↓
Commit
   ↓
Lanjut modul berikutnya
```

## 2.2 Satu perubahan besar = satu checkpoint

Setelah setiap fase yang besar, bot harus mempunyai kondisi yang dapat dijalankan.

## 2.3 Data, AI, dan renderer harus terpisah

```text
DATA
  ↓
LOGIC / RESEARCH
  ↓
AI
  ↓
OUTPUT JSON
  ↓
RENDERER
```

## 2.4 AI tidak menjadi sumber fakta utama

AI boleh:

- menulis;
- merangkum;
- membuat angle;
- membuat hook;
- membuat analisis;
- membuat visual direction.

AI tidak boleh mengisi fakta yang tidak tersedia.

## 2.5 Semua pekerjaan diberi ID

Setiap request, job, konten, research item, dan event harus bisa ditelusuri.

---

# 3. TARGET PRODUK SETELAH SEMUA FASE CORE SELESAI

```text
                    TELEGRAM ASSISTANT
                            │
                            ▼
                      SMART ROUTER
                            │
          ┌─────────────────┴─────────────────┐
          │                                   │
          ▼                                   ▼
      CONTENT MODE                       CHESS MODE
          │                                   │
    ┌─────┼─────┐                    ┌───────┼────────┐
    ▼     ▼     ▼                    ▼       ▼        ▼
 Wedding MLBB Fashion                TCO     Liga    Arena
    │     │     │                    │       │        │
    └─────┼─────┘                    └───────┼────────┘
          │                                  │
          ▼                                  ▼
       RESEARCH                         STRUCTURED DATA
          │                                  │
          └──────────────┬───────────────────┘
                         ▼
                    OPENROUTER AI
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
             TEXT       IMAGE      VIDEO
              │          │          │
              └──────────┼──────────┘
                         ▼
                      TELEGRAM
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
             WA        SOSMED      HISTORY
```

---

# 4. URUTAN PEMBANGUNAN WAJIB

Jangan membangun semua modul secara paralel.

Urutan utama:

```text
PHASE 0  Backup & baseline
   ↓
PHASE 1  Accounts v2
   ↓
PHASE 1A Brand Profile + Template + Watermark System
   ↓
PHASE 2  Data model + SQLite
   ↓
PHASE 3  Router / intent
   ↓
PHASE 4  Telegram command center
   ↓
PHASE 5  Chess data + spreadsheet
   ↓
PHASE 6  TCO
   ↓
PHASE 7  Liga
   ↓
PHASE 8  Arena Kings
   ↓
PHASE 9  Content Engine per akun
   ↓
PHASE 10 Research Engine 2.0
   ↓
PHASE 11 Media Engine 2.0
   ↓
PHASE 12 History + dedup + quality
   ↓
PHASE 13 Planner + briefing
   ↓
PHASE 14 Deployment serverless/job based
   ↓
PHASE 15 End-to-end testing
   ↓
PHASE 16 Future publisher layer
```

---

# 5. PHASE 0 — BASELINE & BACKUP

## Tujuan

Membuat titik aman sebelum perubahan besar.

## Checklist

- [ ] Simpan branch `stable-before-refactor`
- [ ] Backup `accounts.json`
- [ ] Backup `.env` di luar repository
- [ ] Backup folder `output/`
- [ ] Backup file log jika perlu
- [ ] Jalankan bot versi sekarang
- [ ] Uji Wedding
- [ ] Uji MLBB
- [ ] Uji Fashion
- [ ] Simpan minimal 1 output sukses untuk setiap akun
- [ ] Catat waktu proses rata-rata

## Acceptance Criteria

Bot lama masih menghasilkan konten seperti sebelum refactor.

---

# 6. PHASE 1 — ACCOUNTS V2

## Tujuan

Mengubah konfigurasi akun sehingga seluruh behavior dapat diarahkan lewat config.

## Target

Akun aktif:

```text
chess
wedding
mlbb
fashion
```

`kuliner` dikeluarkan dari daftar produksi utama.

## Struktur yang disarankan

```json
{
  "id": "mlbb",
  "label": "Esports MLBB",
  "handle": "@...",
  "niche": "...",
  "audience": "...",
  "tone": "...",
  "mode": ["content"],
  "content_categories": [
    "patch",
    "meta",
    "hero",
    "counter",
    "tips",
    "mpl",
    "esports"
  ],
  "research_sources": [
    "web",
    "youtube",
    "news"
  ],
  "hashtags": [],
  "avoid": [],
  "fact_rules": []
}
```

Untuk Chess:

```json
{
  "id": "chess",
  "label": "Klub Catur / TCO",
  "mode": ["content", "club_operations"],
  "content_categories": [
    "chess_tip",
    "event",
    "community",
    "announcement"
  ]
}
```

## File yang disentuh

```text
accounts.json
accounts.example.json
utils/accounts.py
```

## Acceptance Criteria

- [ ] `/akun` menampilkan 4 akun
- [ ] Semua akun dapat dipilih
- [ ] Config dapat diubah tanpa mengubah logic utama
- [ ] Kuliner tidak lagi menjadi akun produksi

---


# 6A. PHASE 1A — BRAND PROFILE, TEMPLATE STYLE & WATERMARK SYSTEM

## Tujuan

Setiap akun wajib memiliki **identitas visual dan gaya generate yang berbeda**.
Sistem tidak boleh lagi menggunakan satu renderer/template yang sama untuk semua akun.

Target:

```text
Account
  ↓
Brand Profile
  ├── Visual Identity
  ├── Writing Style
  ├── Content Template
  ├── Media Template
  ├── Watermark
  └── Generation Rules
```

Brand Profile menjadi kontrak utama antara:

```text
Account Config
     ↓
AI Prompt
     ↓
Content Schema
     ↓
Media Renderer
     ↓
Final Asset
```

## 6A.1 Prinsip Utama

1. Satu akun = satu Brand Profile.
2. Satu akun = satu watermark identity.
3. Template boleh banyak, tetapi semuanya harus mengikuti Brand Profile akun tersebut.
4. Style visual tidak boleh tercampur antar akun.
5. Prompt AI harus membaca Brand Profile sebelum menghasilkan konten.
6. Renderer tidak boleh menebak style; renderer mengambil style dari configuration.
7. Watermark harus ditambahkan secara konsisten pada output final.
8. Watermark tidak boleh menutupi informasi utama.
9. Logo asli, bila tersedia, harus digunakan sebagai asset; jangan dibuat ulang oleh AI.
10. Semua style dapat diubah dari config tanpa mengubah core engine.

---

## 6A.2 Struktur Brand Profile

Tambahkan blok `brand` di setiap akun.

Contoh:

```json
{
  "id": "wedding",
  "label": "Wedding Organizer",
  "handle": "@wedding.ko",
  "brand": {
    "identity": {
      "style": "elegant_warm_minimal",
      "visual_mood": ["elegan", "hangat", "romantis", "bersih", "premium"],
      "design_density": "low",
      "image_style": "editorial_wedding"
    },
    "colors": {
      "primary": "#...",
      "secondary": "#...",
      "accent": "#...",
      "background": "#...",
      "text": "#..."
    },
    "typography": {
      "heading_font": "...",
      "body_font": "...",
      "accent_font": "..."
    },
    "watermark": {
      "type": "logo_plus_handle",
      "asset": "assets/branding/wedding/watermark.png",
      "position": "bottom_right",
      "opacity": 0.78,
      "scale": 0.12,
      "margin": 48,
      "safe_area": true
    },
    "templates": {
      "square": ["wedding_tip_square", "wedding_quote_square"],
      "portrait": ["wedding_carousel_cover", "wedding_checklist"],
      "reel": ["wedding_reel_3scene", "wedding_reel_5scene"],
      "story": ["wedding_story_tip"]
    }
  },
  "generation_style": {
    "tone": "hangat_elegan",
    "sentence_style": "natural_indonesian",
    "hook_style": "relatable_problem",
    "cta_style": "soft_cta",
    "emoji_level": "low"
  }
}
```

Field wajib:

```text
brand.identity
brand.colors
brand.typography
brand.watermark
brand.templates
generation_style
```

Jika field wajib tidak ada, account configuration dianggap invalid.

---

## 6A.3 Brand Profile — Wedding

### Identitas

```text
edukatif
hangat
elegan
romantis
praktis
premium tetapi tidak kaku
soft-selling
```

### Visual Direction

Default awal:

```text
Style:
elegant / editorial / minimal

Layout:
banyak white space
hierarki tipografi jelas
tidak terlalu ramai

Image:
wedding editorial
venue
detail dekorasi
floral
bride/groom
table setting
lighting warm
```

### Template awal

```text
wedding_tip
wedding_checklist
wedding_mistake
wedding_trend
wedding_inspiration
wedding_reel
wedding_carousel
wedding_quote
```

### Writing Style

```text
hangat
tidak menggurui
praktis
mudah dipahami calon pengantin
hindari hard selling
```

### Hook style

```text
problem → consequence → practical tip
```

---

## 6A.4 Brand Profile — MLBB

### Identitas

```text
energik
cepat
gaming
esports
sedikit humor
langsung ke poin
```

### Visual Direction

```text
Style:
gaming / esports / high contrast

Layout:
headline besar
hero sebagai focal point
badge patch/meta
panel informasi
comparison/counter box
```

### Template awal

```text
mlbb_patch
mlbb_hero
mlbb_counter
mlbb_meta
mlbb_build
mlbb_tip
mlbb_mpl
mlbb_esports
mlbb_match_analysis
mlbb_trend
```

### Writing Style

```text
cepat
tegas
bahasa komunitas
tidak terlalu formal
humor secukupnya
```

### Struktur content

```text
HOOK
↓
MASALAH / PERUBAHAN
↓
PENJELASAN
↓
IMPLIKASI
↓
CTA
```

### Guardrail visual

Angka/statistik, hasil pertandingan, patch change, jadwal, dan klasemen hanya boleh ditampilkan sebagai fakta ketika mempunyai source yang terverifikasi.

---

## 6A.5 Brand Profile — Fashion

### Identitas

```text
bersahabat
modern
praktis
stylish
budget-conscious
```

### Visual Direction

```text
Style:
clean editorial
lifestyle
OOTD
street / campus / casual

Layout:
foto sebagai fokus utama
teks singkat
sedikit elemen dekoratif
product area jika data tersedia
```

### Template awal

```text
fashion_ootd
fashion_mix_match
fashion_1_item_3_looks
fashion_campus
fashion_work
fashion_hijab
fashion_accessory
fashion_trend
fashion_problem_solution
fashion_affiliate
```

### Writing Style

```text
seperti teman memberi rekomendasi
konkret
tidak terlalu formal
```

### Affiliate overlay

```text
PRODUCT
↓
USE CASE / BENEFIT
↓
HOW TO STYLE
↓
CTA
```

Fakta produk seperti brand, harga, material, diskon, rating, jumlah terjual, dan fitur harus berasal dari data/source; AI tidak boleh mengarang.

---

## 6A.6 Brand Profile — Klub Catur / TCO

### Identitas

```text
community
sporty
kompetitif
profesional
ramah
bernuansa klub
```

### Visual Direction

```text
Style:
chess club / competitive / premium sport

Layout:
papan catur
bidak
ranking
event badge
tanggal/jam
league badge
```

Konten event harus lebih informatif daripada dekoratif.

### Template awal

```text
chess_tco_announcement
chess_tco_reminder
chess_tco_result
chess_liga_standings
chess_liga_news
chess_arena_announcement
chess_arena_reminder
chess_tip
chess_puzzle
chess_match_recap
chess_community
```

### Writing Style

```text
jelas
rapi
sportif
komunitas
mudah dibagikan ke WA
```

Field event seperti tanggal, waktu, format, durasi, dan link **harus berasal dari data event**, bukan improvisasi AI.

---

## 6A.7 Sistem Watermark Unik per Akun

Watermark bukan sekadar menambahkan teks handle di gambar.

Buat satu `Watermark Profile` per akun.

```text
assets/
└── branding/
    ├── chess/
    │   ├── logo.png
    │   ├── watermark.png
    │   └── watermark_light.png
    ├── wedding/
    │   ├── logo.png
    │   ├── watermark.png
    │   └── watermark_light.png
    ├── mlbb/
    │   ├── logo.png
    │   ├── watermark.png
    │   └── watermark_light.png
    └── fashion/
        ├── logo.png
        ├── watermark.png
        └── watermark_light.png
```

### Requirement

Setiap akun minimal mempunyai:

```text
primary watermark
light watermark
dark watermark
```

Renderer memilih versi berdasarkan background.

### Posisi

```text
Square:
bottom-right

Portrait:
bottom-right / bottom-safe-area

Reel:
top-right atau bottom-right
tergantung subtitle/caption area
```

Posisi final dihitung terhadap safe area, bukan selalu koordinat tetap.

### Ukuran

Gunakan ukuran relatif terhadap canvas:

```text
logo watermark:
8% - 14% dari lebar canvas

handle:
2% - 4% tinggi canvas
```

### Opacity

Default:

```text
0.65 - 0.85
```

### Rule

Watermark tidak boleh menutupi:

```text
wajah
hero
judul
CTA
skor
link/event information
```

---

## 6A.8 Watermark pada Video

Watermark tidak hanya muncul pada frame pertama.

Versi pertama:

```text
persistent watermark
```

Watermark tampil konsisten pada setiap scene dengan animasi minimal atau tanpa animasi agar branding stabil dan render ringan.

---

## 6A.9 Template Registry

Buat registry yang menghubungkan:

```text
account
content_type
format
template
style
watermark
```

Contoh:

```json
{
  "id": "mlbb_patch_square",
  "account": "mlbb",
  "content_type": "patch",
  "format": "1080x1080",
  "template": "mlbb_patch",
  "style": "mlbb_esports",
  "watermark": "mlbb_primary"
}
```

Request:

```text
buat konten patch MLBB
```

dirouting menjadi:

```text
account = mlbb
task = content
category = patch
format = square
template = mlbb_patch
style = mlbb_esports
watermark = mlbb_primary
```

---

## 6A.10 AI Style Prompt

AI menerima dua context berbeda:

```text
FACT CONTEXT
+
BRAND CONTEXT
```

Brand context mengatur:

```text
tone
audience
hook_style
sentence_style
emoji_level
vocabulary
cta_style
```

AI **tidak menentukan**:

```text
warna
font
logo
watermark
koordinat layout
```

Semua itu berasal dari config/renderer.

AI menghasilkan:

```text
content
copy
scene concept
visual direction
```

---

## 6A.11 Style Presets

Gunakan preset:

```text
styles/
├── wedding_elegant.json
├── mlbb_esports.json
├── fashion_editorial.json
└── chess_club.json
```

Preset berisi:

```text
palette
typography
spacing
corner_radius
shadow
overlay
icon_style
watermark
```

---

## 6A.12 Content Template vs Visual Template

Pisahkan dua hal.

### Content Template

Mengatur:

```text
hook
title
subtitle
points
script
CTA
caption
hashtag
```

### Visual Template

Mengatur:

```text
canvas
layout
font
warna
gambar
shape
icon
watermark
animation
```

Contoh:

```text
MLBB PATCH

Content Template:
"5 perubahan hero paling penting"

Visual Template:
mlbb_patch_square

Watermark:
mlbb_primary
```

---

## 6A.13 Template Fallback

Jika template spesifik belum tersedia:

```text
specific template
      ↓ gagal
account default template
      ↓ gagal
generic safe template
```

Watermark akun tetap wajib diterapkan.

---

## 6A.14 Struktur File Branding

```text
branding/
├── loader.py
├── validator.py
├── watermark.py
└── style_registry.py

templates/
├── registry.json
├── wedding/
├── mlbb/
├── fashion/
└── chess/

assets/
└── branding/
    ├── wedding/
    ├── mlbb/
    ├── fashion/
    └── chess/

styles/
├── wedding_elegant.json
├── mlbb_esports.json
├── fashion_editorial.json
└── chess_club.json
```

Renderer helper:

```text
utils/media/
├── template_engine.py
├── layout_engine.py
├── watermark_engine.py
└── asset_loader.py
```

---

## 6A.15 Branding QA sebelum Telegram

Flow:

```text
Content generated
      ↓
Template selected
      ↓
Brand applied
      ↓
Watermark applied
      ↓
Render
      ↓
Brand QA
```

Automated checks:

```text
[ ] watermark exists
[ ] watermark belongs to selected account
[ ] template belongs to selected account
[ ] dimensions correct
[ ] no overflow
[ ] no text collision
[ ] CTA visible
[ ] critical information visible
```

Sistem harus menolak asset bila:

```text
account = mlbb
template = wedding
```

atau:

```text
account = wedding
watermark = fashion
```

---

## 6A.16 Prevent Cross-Account Branding

Setiap render menerima:

```json
{
  "account_id": "mlbb",
  "template_id": "mlbb_patch",
  "watermark_id": "mlbb_primary"
}
```

Renderer melakukan validasi:

```text
template.account_id == account_id
watermark.account_id == account_id
```

Jika tidak sama:

```text
BRANDING_MISMATCH
```

dan render dihentikan.

---

## 6A.17 Preview Mode

Tambahkan command:

```text
/preview wedding
/preview mlbb
/preview fashion
/preview chess
```

atau:

```text
/style wedding
```

Bot menampilkan sample template + watermark untuk memastikan identitas visual sudah benar sebelum produksi massal.

---

## 6A.18 Approval Workflow untuk Branding

Tahap awal:

```text
generate preview
      ↓
Telegram
      ↓
[✅ Approve]
[🔄 Regenerate]
[🎨 Change Style]
```

Hanya asset yang di-approve yang dianggap `production-ready`.

---

## 6A.19 Urutan Implementasi Branding

```text
1. Kumpulkan logo/aset asli tiap akun
        ↓
2. Buat brand profile JSON
        ↓
3. Buat style presets
        ↓
4. Buat watermark engine
        ↓
5. Buat template registry
        ↓
6. Hubungkan AI generation ke brand context
        ↓
7. Hubungkan renderer ke style registry
        ↓
8. Tambahkan brand QA
        ↓
9. Buat preview command
        ↓
10. Uji 4 akun
```

## Acceptance Criteria

Semua akun menghasilkan output yang secara visual dapat dibedakan tanpa membaca caption.

```text
Wedding → langsung terasa wedding
MLBB    → langsung terasa gaming/esports
Fashion → langsung terasa fashion/OOTD
Chess   → langsung terasa klub catur
```

Dan pada semua output:

```text
account watermark = account yang membuat konten
```

Tidak boleh ada watermark silang.

---

# 7. PHASE 2 — DATA MODEL & SQLITE

## Tujuan

Membangun memory sistem.

## Database

Untuk fase awal gunakan SQLite.

## Tabel inti

### `jobs`

```text
id
chat_id
account_id
task
status
created_at
started_at
finished_at
error
```

### `contents`

```text
id
job_id
account_id
category
topic
title
hook
caption
hashtags
format
platform_target
status
output_path
created_at
```

### `research_items`

```text
id
account_id
topic
title
source_url
source_type
published_at
collected_at
relevance_score
freshness_score
fact_status
raw_data
```

### `chess_events`

```text
event_id
event_type
title
date
start_time
duration
format
link
season
league
status
notes
```

### `feedback`

```text
id
content_id
feedback_type
created_at
notes
```

## File baru

```text
utils/database.py
utils/repositories.py
```

## Acceptance Criteria

- [ ] Database otomatis dibuat
- [ ] Job dapat dicatat
- [ ] Content dapat disimpan
- [ ] Research dapat disimpan
- [ ] Event catur dapat disimpan
- [ ] Tidak ada secret yang masuk database

---

# 8. PHASE 3 — SMART ROUTER / INTENT ENGINE

## Tujuan

Mengubah bot dari keyword-only menjadi task-oriented assistant.

## Output router

```json
{
  "account": "chess",
  "task": "tco_weekly",
  "category": null,
  "topic": null,
  "quantity": 1,
  "format": null,
  "parameters": {}
}
```

## Task utama

```text
content
trend_research
caption
image
video
planner
history

tco_weekly
league
arena
chess_content
```

## File baru

```text
utils/router.py
utils/intent_schema.py
```

## Strategi

```text
explicit command
    ↓
structured intent
    ↓
validation
    ↓
handler
```

Natural language tetap diperbolehkan sebagai fallback.

## Acceptance Criteria

Bot dapat membedakan:

```text
buat konten MLBB
```

dari:

```text
tco minggu ini
```

tanpa salah masuk generator generik.

---

# 9. PHASE 4 — TELEGRAM COMMAND CENTER

## Tujuan

Membuat Telegram terasa seperti aplikasi mini.

## Main Menu

```text
🤖 SOCIAL MEDIA ASSISTANT

♟ Klub Catur
💍 Wedding
🎮 MLBB
👕 Fashion
📅 Planner
📚 History
⚙️ Settings
```

## Implementasi

- [ ] Inline keyboard
- [ ] Callback handler
- [ ] Back button
- [ ] Cancel job
- [ ] Retry
- [ ] Regenerate
- [ ] Ganti angle
- [ ] Pilih format

## File

```text
utils/telegram_bot.py
utils/telegram_menu.py
```

## Acceptance Criteria

Perintah utama dapat dijalankan dari menu tanpa harus menghafal syntax.

---

# 10. PHASE 5 — CHESS DATA FOUNDATION

## Tujuan

Membuat sumber data klub catur menjadi data terstruktur.

## Sumber utama

Spreadsheet bulanan.

## Workbook yang disarankan

```text
TCO_DATA
├── TCO
├── LIGA
├── ARENA
└── CONFIG
```

## Sheet `TCO`

```text
id
judul_turnamen
tanggal
hari
jam_mulai
durasi
format
link_turnamen
status
notes
```

## Sheet `LIGA`

```text
season
league
rank
player
played
win
draw
loss
points
tiebreak
status
```

## Sheet `ARENA`

```text
month
date
day
start_time
link
status
notes
```

## File

```text
utils/chess/spreadsheet.py
utils/chess/validators.py
```

## Acceptance Criteria

Bot dapat membaca sheet dan menghasilkan object Python yang tervalidasi.

---

# 11. PHASE 6 — TCO WEEKLY ENGINE

## Tujuan

Mengotomatiskan pembuatan pengumuman mingguan dari spreadsheet.

## Command

```text
/tco
/tco minggu ini
/tco next
```

## Workflow

```text
Telegram
  ↓
TCO Handler
  ↓
Resolve week/date
  ↓
Read spreadsheet
  ↓
Validate event
  ↓
Generate WA text
  ↓
Generate social caption
  ↓
Optional poster
  ↓
Store history
  ↓
Send package
```

## Output package

```text
📦 TCO PACKAGE

[DETAIL EVENT]
[WA VERSION]
[SOCIAL VERSION]
[POSTER]
```

## File

```text
utils/chess/tco.py
utils/chess/tco_formatter.py
```

## Acceptance Criteria

Dari satu data spreadsheet, bot dapat menghasilkan seluruh paket TCO tanpa pengetikan ulang.

---

# 12. PHASE 7 — LIGA ENGINE

## Tujuan

Membuat berita dan visual klasemen berdasarkan data nyata.

## Command

```text
/liga
/liga A
/liga A update
```

## Workflow

```text
Read spreadsheet
   ↓
Validate rows
   ↓
Sort / verify ranking
   ↓
Generate report
   ↓
Generate WA
   ↓
Generate social
   ↓
Generate standings image
   ↓
Store history
```

## Guardrail

Tidak boleh mengarang:

- nama pemain;
- poin;
- rank;
- jumlah pertandingan;
- hasil.

## File

```text
utils/chess/liga.py
utils/chess/liga_formatter.py
```

## Acceptance Criteria

Visual dan teks klasemen berasal dari dataset yang sama.

---

# 13. PHASE 8 — ARENA KINGS ENGINE

## Tujuan

Menangani event yang jadwalnya diketahui tetapi link turnamen baru muncul mendekati acara.

## Workflow tahap 1

```text
Arena schedule
  ↓
Generate monthly announcement
  ↓
Poster
  ↓
WA
  ↓
Social
```

## Workflow tahap 2

```text
/arena link <URL>
       ↓
Find open event
       ↓
Attach URL
       ↓
Generate reminder
       ↓
Send Telegram
```

## File

```text
utils/chess/arena.py
utils/chess/arena_scheduler.py
```

## Acceptance Criteria

Sistem dapat bekerja dengan maupun tanpa link turnamen.

---

# 14. PHASE 9 — GENERIC CONTENT ENGINE 2.0

## Tujuan

Memecah generator generik menjadi generator berbasis akun dan task.

## Struktur

```text
utils/ai/
├── base_generator.py
├── content_generator.py
├── wedding_generator.py
├── mlbb_generator.py
├── fashion_generator.py
├── chess_generator.py
├── tco_generator.py
├── liga_generator.py
└── arena_generator.py
```

## Schema universal

```json
{
  "title": "",
  "subtitle": "",
  "hook": "",
  "script": [],
  "points": [],
  "caption": "",
  "hashtags": [],
  "cta": "",
  "visual_prompt": "",
  "sources": [],
  "fact_status": "verified"
}
```

## Acceptance Criteria

Generator dapat diganti atau ditingkatkan per akun tanpa memengaruhi akun lain.

---

# 15. PHASE 10 — WEDDING ENGINE

## Content pillars

```text
education
inspiration
checklist
trend
problem_solution
soft_sell
```

## Input contoh

```text
buat 3 konten wedding trend minggu ini
```

## Output per konten

```text
Title
Hook
Angle
Script
Scene
Text Overlay
CTA
Caption
Hashtag
Visual direction
Source
```

## Guardrail

- Jangan mengarang harga.
- Jangan mengarang paket.
- Jangan mengarang tanggal/lokasi.
- Klaim trend harus mempunyai sumber atau diberi status sebagai idea.

---

# 16. PHASE 11 — MLBB ENGINE

## Content pillars

```text
patch
hero
counter
meta
build
tips
MPL
esports
match analysis
trend
```

## Classification

```text
VERIFIED
ANALYSIS
IDEA
```

## Rule

### VERIFIED
Harus mempunyai sumber.

### ANALYSIS
Boleh berasal dari reasoning model tetapi harus jelas sebagai analisis/opini.

### IDEA
Tidak boleh ditulis seolah-olah fakta.

## Guardrail

- Jangan mengarang hasil pertandingan.
- Jangan mengarang statistik.
- Jangan mengarang patch change.
- Jangan menulis jadwal seolah resmi jika sumber tidak tersedia.

---

# 17. PHASE 12 — FASHION AFFILIATE ENGINE

## Mode

```text
inspiration
styling
trend
OOTD
problem_solution
affiliate
```

## Input produk

```text
buat konten affiliate
produk: <link/nama/foto>
```

## Output

```text
product angle
hook
script
scene
text overlay
CTA
caption
hashtags
product placement
affiliate CTA
```

## Guardrail

- Jangan mengarang brand.
- Jangan mengarang harga.
- Jangan mengarang material/fungsi produk tanpa sumber.
- Styling opinion boleh, fakta produk harus diverifikasi.

---

# 18. PHASE 13 — CHESS CONTENT ENGINE

Selain operational assistant, akun catur tetap mempunyai content generator.

## Content pillars

```text
tips catur
trik
mini lesson
event
community
match recap
fun facts
announcement
```

Operational data tetap dipisahkan dari generic content.

```text
Chess Operations
       ≠
Chess Content
```

---

# 19. PHASE 14 — RESEARCH ENGINE 2.0

## Tujuan

Mengembangkan research dari satu sumber menjadi research pack.

## Arsitektur

```text
Query
 ↓
Source adapters
 ↓
Normalization
 ↓
Freshness
 ↓
Relevance
 ↓
Deduplication
 ↓
Source pack
 ↓
AI
```

## Source adapter concept

```text
research/
├── base.py
├── web.py
├── youtube.py
├── news.py
└── manual.py
```

## Research item

```json
{
  "title": "...",
  "source_url": "...",
  "source_type": "web",
  "published_at": "...",
  "relevance_score": 0.92,
  "freshness_score": 0.88
}
```

## Acceptance Criteria

Generator menerima research pack lengkap dengan source, bukan hanya daftar judul.

---

# 20. PHASE 15 — FACT-CHECK PIPELINE

## Workflow

```text
Research
  ↓
Candidate claims
  ↓
Source matching
  ↓
AI draft
  ↓
Claim verification
  ↓
Final output
```

## Status

```text
verified
partially_verified
analysis
idea
insufficient_source
```

## Prioritas

1. MLBB patch
2. MLBB esports
3. MPL
4. Liga catur
5. Trend dengan klaim waktu/statistik

---

# 21. PHASE 16 — MEDIA ENGINE 2.0

## Tujuan

Membuat renderer berdasarkan template.

## Struktur

```text
templates/
├── wedding/
├── mlbb/
├── fashion/
└── chess/
    ├── tco/
    ├── liga/
    └── arena/
```

## Output

```text
image square       1080x1080
image portrait     1080x1350
story/reel         1080x1920
```

## Video object

```json
{
  "format": "video",
  "duration": 15,
  "scenes": 5,
  "template": "mlbb_patch"
}
```

## Pekerjaan

- [ ] template registry
- [ ] scene renderer
- [ ] carousel renderer
- [ ] poster renderer
- [ ] configurable duration
- [ ] configurable scene count
- [ ] logo/brand asset support
- [ ] fallback font


### Integrasi dengan Brand System

Media Engine **wajib mengambil style dari Brand Profile**, bukan hard-code per renderer.

Flow:

```text
request
  ↓
account_id
  ↓
content_category
  ↓
template registry
  ↓
brand profile
  ↓
style preset
  ↓
asset/logo selection
  ↓
watermark engine
  ↓
renderer
```

Setiap template mempunyai:

```text
template_id
account_id
supported_formats
style_preset
watermark_profile
content_schema
```

Renderer melakukan validasi kepemilikan account sebelum render.

---

# 22. PHASE 17 — CONTENT HISTORY & DEDUPLICATION

## Tujuan

Mencegah akun membuat hal yang sama terus-menerus.

## Flow

```text
New request
  ↓
History lookup
  ↓
Exact similarity
  ↓
Keyword similarity
  ↓
Semantic similarity
  ↓

high similarity → ganti angle
low similarity  → generate
```

## Yang dicek

- topic
- title
- hook
- points
- caption
- visual concept

## Command

```text
/history
/history mlbb
/history wedding
```

---

# 23. PHASE 18 — QUALITY SCORE

Setiap content package dapat mempunyai skor internal.

```text
relevance
freshness
originality
fact_confidence
hook_quality
cta_quality
visual_readiness
```

Contoh:

```json
{
  "relevance": 0.94,
  "freshness": 0.91,
  "originality": 0.87,
  "fact_confidence": 0.96
}
```

## Rule

Konten dengan skor terlalu rendah:

```text
regenerate
atau
ganti angle
atau
ganti source
```

---

# 24. PHASE 19 — FEEDBACK LOOP

## Telegram buttons

```text
[✅ Pakai]
[🔄 Regenerate]
[🎯 Ganti Angle]
[📝 Edit]
[🗑 Tolak]
```

## Data

```text
content_id
feedback_type
created_at
notes
```

## Manfaat

Data feedback dipakai untuk:

- mengetahui template favorit;
- mengetahui topik yang sering ditolak;
- mengetahui angle yang disukai;
- memperbaiki prompt secara bertahap.

---

# 25. PHASE 20 — CONTENT PLANNER

## Tujuan

Bot mulai membantu berpikir sebelum membuat konten.

## Command

```text
/plan
/plan mlbb minggu ini
/plan wedding oktober
/plan semua minggu ini
```

## Workflow

```text
Account goals
  ↓
Available days
  ↓
Content pillars
  ↓
Recent history
  ↓
Trend research
  ↓
Generate plan
  ↓
Save calendar
```

## Hasil

Planner tidak langsung membuat semua media.

```text
PLAN
  ↓
APPROVE
  ↓
GENERATE
```

---

# 26. PHASE 21 — DAILY / WEEKLY BRIEFING

## Daily briefing

```text
🤖 DAILY SOCIAL BRIEF

Wedding
- trend penting
- konten terjadwal

MLBB
- patch/news penting

Fashion
- ide trend

Chess
- event terdekat
```

## Weekly briefing

```text
📅 WEEKLY CONTENT BRIEF

Akun yang perlu perhatian:
...

Topik yang sedang naik:
...

Event catur minggu ini:
...

Konten yang belum dibuat:
...
```

---

# 27. PHASE 22 — JOB QUEUE & STATE MACHINE

Ini penting sebelum deployment cloud.

## Status job

```text
queued
running
success
failed
cancelled
retrying
```

## Workflow

```text
Telegram request
  ↓
create job
  ↓
queued
  ↓
running
  ↓
research
  ↓
AI
  ↓
render
  ↓
send
  ↓
success
```

## Kenapa harus sebelum cloud

Karena environment job-based tidak boleh mengandalkan proses Python yang selalu hidup untuk menyimpan state request.

---

# 28. PHASE 23 — REFACTOR TELEGRAM: POLLING → WEBHOOK-READY

## Kondisi lama

```text
Python process
   ↓
long polling
   ↓
menunggu terus
```

## Target

Pisahkan:

```text
Telegram transport
        │
        ▼
Request router
        │
        ▼
Job queue
```

## Aturan

Logic core tidak boleh tergantung pada mekanisme Telegram polling.

## File

```text
utils/telegram_bot.py
utils/telegram_transport.py
utils/request_handler.py
```

## Acceptance Criteria

Bot dapat menerima request menggunakan polling maupun webhook tanpa mengganti logic generator.

---

# 29. PHASE 24 — LOCAL WORKER MODE

Sebelum cloud, buat mode worker lokal.

```bash
python worker.py
```

Worker membaca job dan memprosesnya.

## Target arsitektur lokal

```text
Telegram
   ↓
Bot
   ↓
DB / Queue
   ↓
Worker
   ↓
Research / AI / Render
   ↓
Telegram
```

Ini adalah tahap penting karena nanti `worker.py` yang sama bisa dipindahkan ke environment job cloud.

## Acceptance Criteria

Bot dan worker dapat dijalankan sebagai dua proses terpisah.

---

# 30. PHASE 25 — CLOUD DEPLOYMENT TANPA SERVER VPS BERBAYAR

## Arsitektur target

```text
                         TELEGRAM
                            │
                            ▼
                  CLOUDFLARE ENTRYPOINT
                            │
                            ▼
                      JOB DISPATCHER
                            │
                            ▼
                    GITHUB ACTIONS JOB
                            │
                            ▼
                     PYTHON WORKER
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
     OpenRouter         Spreadsheet          Web
         │
         ▼
    Pillow / FFmpeg / Playwright
         │
         ▼
      Telegram
```

## Prinsip

Cloudflare digunakan untuk layer ringan/entrypoint.

GitHub Actions digunakan sebagai execution worker untuk pekerjaan berat.

Core Python tidak mengetahui detail hosting.

## Wajib sebelum deployment

- [ ] worker sudah terpisah
- [ ] semua config lewat environment variable
- [ ] state disimpan persistent
- [ ] job idempotent
- [ ] retry aman
- [ ] timeout aman
- [ ] output media tidak bergantung pada folder sesi sementara

---


# 30A. DEPLOYMENT RUNBOOK — CLOUDFLARE + GITHUB ACTIONS + D1 + TELEGRAM + SHEETS

Bagian ini merupakan kelanjutan implementasi deployment dari PHASE 25. Targetnya adalah memindahkan bot dari model `long polling di PC` menjadi arsitektur **webhook + job worker** tanpa menjadikan PC lokal sebagai dependency utama.

Arsitektur production yang dituju:

```text
                                      INTERNET
                                         │
                                         ▼
                                  ┌─────────────┐
                                  │  TELEGRAM   │
                                  │  Bot API    │
                                  └──────┬──────┘
                                         │ HTTPS POST
                                         ▼
                           ┌──────────────────────────┐
                           │   CLOUDFLARE WORKER      │
                           │                          │
                           │ webhook                  │
                           │ authentication           │
                           │ router ringan            │
                           │ D1 access                │
                           │ GitHub dispatch          │
                           └────────────┬─────────────┘
                                        │
                                        │ repository_dispatch /
                                        │ workflow_dispatch
                                        ▼
                           ┌──────────────────────────┐
                           │     GITHUB ACTIONS       │
                           │     Python Worker        │
                           │                          │
                           │ Python                   │
                           │ Playwright + Chromium    │
                           │ Pillow                   │
                           │ FFmpeg                   │
                           │ Research                 │
                           │ OpenRouter               │
                           │ Google Sheets            │
                           └────────────┬─────────────┘
                                        │
                   ┌────────────────────┼────────────────────┐
                   │                    │                    │
                   ▼                    ▼                    ▼
              OpenRouter          Google Sheets          Web/Research
                   │                    │
                   └──────────────┬─────┘
                                  ▼
                             Python Worker
                                  │
                    ┌─────────────┼──────────────┐
                    ▼             ▼              ▼
                  Image         Video          Text
                    │             │              │
                    └─────────────┼──────────────┘
                                  ▼
                               Telegram
                                  │
                                  ▼
                            User / WA / Sosmed

                          OPTIONAL / FUTURE
                                  │
                                  ▼
                              Cloudflare R2
```

## 30A.1 Prinsip pembagian tanggung jawab

### Cloudflare Worker = pintu masuk bot

Worker hanya menangani pekerjaan ringan:

- menerima webhook Telegram;
- memvalidasi secret webhook;
- memvalidasi chat/user yang diizinkan;
- membaca/menulis status job sederhana ke D1;
- membuat `job_id`;
- menerjemahkan update Telegram menjadi job;
- memicu GitHub Actions;
- menerima callback status dari worker Python;
- menyediakan endpoint health/status terbatas.

Worker **tidak** menjalankan:

- Playwright;
- Chromium;
- FFmpeg;
- rendering video;
- proses AI yang panjang;
- pekerjaan scraping berat.

Cloudflare Workers Free saat ini memiliki batas 100.000 request/hari, 10 ms CPU/request, 128 MB memory, dan maksimal 5 Cron Trigger per akun. Batas tersebut membuat Worker cocok sebagai entrypoint dan dispatcher ringan, bukan sebagai mesin rendering utama. citeturn999493search10

### GitHub Actions = mesin kerja Python

GitHub Actions menjalankan worker yang sudah dibangun dari repository:

```text
checkout
→ install dependency
→ install Chromium
→ install/cek FFmpeg
→ run python worker
→ kirim hasil ke Telegram
→ update status
→ selesai
```

GitHub Free saat ini memberikan 2.000 CI/CD minutes/bulan untuk akun Free, sedangkan standard GitHub-hosted runners gratis untuk repository public. Untuk repository private, penggunaan di luar quota dapat menjadi billable; bila tidak ada payment method, GitHub menyatakan usage akan diblokir setelah quota habis. Karena tujuan proyek adalah menghindari billing tak sengaja, repository private + tanpa payment method harus dianggap sebagai baseline yang paling aman, dengan pemantauan quota. citeturn805722search5turn805722search4

### Cloudflare D1 = state dan histori

D1 digunakan untuk:

- jobs;
- job status;
- content history;
- deduplication;
- source metadata;
- scheduler state;
- account configuration ringan;
- event history;
- error records.

Workers Free saat ini mencakup D1 dengan 5 juta row reads/hari, 100.000 row writes/hari, dan 5 GB total storage. D1 juga menegakkan daily free-tier limits; ketika limit tercapai, query gagal sampai quota reset, bukan otomatis mengubah account menjadi paid. citeturn999493search13turn999493search3turn999493search8

D1 schema target:

```text
accounts
jobs
job_events
content_items
content_sources
content_variants
chess_events
chess_standings
scheduler_runs
media_refs
settings
```

### Cloudflare R2 = storage media, tetapi OPSIONAL

R2 **tidak boleh menjadi dependency wajib v1** karena tujuan deployment saat ini adalah meminimalkan risiko billing.

R2 mempunyai included free monthly usage, tetapi dokumentasi Cloudflare saat ini menyatakan aktivasi R2 melalui checkout/subscription flow. Karena kebutuhan proyek kita dapat dipenuhi tanpa R2 pada tahap awal, R2 hanya dinyalakan setelah kebutuhan storage benar-benar muncul dan syarat billing akun sudah dipahami. citeturn999493search12turn393545search2

Strategi v1:

```text
Python Worker
   ↓
render ke filesystem runner
   ↓
kirim langsung ke Telegram
   ↓
runner selesai
   ↓
file sementara dihapus
```

R2 baru digunakan ketika:

- perlu arsip video jangka panjang;
- file perlu diakses ulang dari dashboard;
- file besar perlu disimpan lintas job;
- workflow membutuhkan URL asset permanen.

### OpenRouter = AI provider

API key disimpan sebagai secret. OpenRouter menyatakan API dapat dimulai tanpa subscription dan tanpa kartu, tetapi model gratis/berbayar mengikuti kondisi masing-masing model/provider sehingga penggunaan harus tetap dipantau. citeturn393545search10

### Telegram = interface utama

Telegram tetap menjadi UI operasional:

```text
User
 ↓
Telegram
 ↓
Cloudflare webhook
 ↓
Job
 ↓
GitHub worker
 ↓
Telegram response
```

Telegram `setWebhook` membutuhkan HTTPS URL. Telegram juga menyediakan `secret_token`, yang dikirim melalui header `X-Telegram-Bot-Api-Secret-Token`; ini harus digunakan untuk validasi request webhook. Saat webhook aktif, `getUpdates`/long polling tidak dapat dipakai secara bersamaan. citeturn661332search0

### Google Sheets = source of truth operasional klub

Spreadsheet tetap menjadi sumber data manual untuk:

- TCO bulanan;
- Liga;
- jadwal Arena Kings;
- data tambahan klub yang memang lebih nyaman dikelola manual.

Python worker mengambil data melalui Google Sheets API. Google Sheets API saat ini memiliki quota 300 read requests/menit/project dan 300 write requests/menit/project, serta menyarankan backoff untuk error 429. Untuk kebutuhan satu klub, quota tersebut jauh lebih dari cukup selama pembacaan dibatch dan tidak dilakukan polling terus-menerus. citeturn393545search0turn393545search11

---

# 30A.2 REPOSITORY FINAL UNTUK DEPLOYMENT

Target struktur repository setelah deployment refactor:

```text
social-media-assistant/
│
├── bot.py
├── worker.py
├── requirements.txt
├── pyproject.toml                    # opsional
├── .gitignore
├── README.md
├── CHANGELOG.md
│
├── app/
│   ├── router.py
│   ├── config.py
│   ├── models.py
│   ├── errors.py
│   └── constants.py
│
├── utils/
│   ├── telegram_bot.py
│   ├── notifier.py
│   ├── accounts.py
│   │
│   ├── ai/
│   │   ├── content_generator.py
│   │   ├── prompt_builder.py
│   │   ├── response_parser.py
│   │   └── model_fallback.py
│   │
│   ├── research/
│   │   ├── base.py
│   │   ├── web.py
│   │   ├── youtube.py
│   │   ├── news.py
│   │   └── scorer.py
│   │
│   ├── chess/
│   │   ├── spreadsheet.py
│   │   ├── tco.py
│   │   ├── liga.py
│   │   ├── arena.py
│   │   └── validators.py
│   │
│   ├── media/
│   │   ├── image_maker.py
│   │   ├── video_maker.py
│   │   ├── template_engine.py
│   │   └── asset_manager.py
│   │
│   └── storage/
│       ├── database.py
│       ├── repositories.py
│       └── media_store.py
│
├── templates/
│   ├── wedding/
│   ├── mlbb/
│   ├── fashion/
│   └── chess/
│
├── schemas/
│   ├── content.json
│   ├── job.json
│   └── chess.json
│
├── db/
│   ├── schema.sql
│   └── migrations/
│
├── cloudflare/
│   ├── worker/
│   │   ├── src/index.ts
│   │   ├── wrangler.toml
│   │   └── package.json
│   └── migrations/
│
├── .github/
│   └── workflows/
│       ├── worker.yml
│       ├── tests.yml
│       └── deploy-worker.yml
│
└── tests/
    ├── unit/
    ├── integration/
    └── scenarios/
```

Catatan: bagian `cloudflare/worker` menggunakan TypeScript/JavaScript sebagai default implementation karena tugasnya ringan, bukan karena Python tidak tersedia. Core content worker tetap Python di GitHub Actions.

---

# 30A.3 KONTRAK JOB

Semua eksekusi cloud harus mempunyai payload standar.

```json
{
  "job_id": "job_20261005_000123",
  "account": "mlbb",
  "task": "content",
  "request": "buat 3 konten meta terbaru",
  "chat_id": "...",
  "requested_by": "...",
  "priority": "normal",
  "created_at": "2026-10-05T15:00:00+07:00"
}
```

Untuk TCO:

```json
{
  "job_id": "job_20261005_000124",
  "account": "chess",
  "task": "tco_weekly",
  "chat_id": "...",
  "week": "2026-W41"
}
```

GitHub `repository_dispatch` dapat menerima `client_payload`; payload tersebut dibatasi maksimum 64 KB dan maksimal 10 top-level properties. Alternatifnya adalah `workflow_dispatch` dengan inputs hingga 25 properties. Karena kebutuhan job kita kecil, keduanya memadai; standar proyek dipilih **repository_dispatch** agar payload job bisa fleksibel. citeturn805722search2turn805722search3

---

# 30A.4 PHASE DEPLOY 1 — SIAPKAN GITHUB REPOSITORY

## Checklist

- [ ] Buat repository project.
- [ ] Pilih private repository bila source code tidak ingin public.
- [ ] Pastikan branch utama `main`.
- [ ] Push kode yang sudah lulus checkpoint local.
- [ ] Tambahkan `.gitignore`.
- [ ] Jangan commit `.env`.
- [ ] Jangan commit `accounts.json` yang berisi rahasia.
- [ ] Jangan commit Google credential JSON.
- [ ] Jangan commit Telegram token.
- [ ] Jangan commit OpenRouter key.

## Acceptance Criteria

Repository dapat di-clone dari mesin baru tanpa membutuhkan file rahasia yang ter-commit.

---

# 30A.5 PHASE DEPLOY 2 — GITHUB ACTIONS WORKER

Buat workflow:

```text
.github/workflows/worker.yml
```

Trigger utama:

```yaml
on:
  repository_dispatch:
    types: [social-media-job]
```

Langkah workflow:

```text
1. checkout
2. setup Python
3. pip install
4. install Playwright browser
5. validate environment
6. run worker.py
7. worker process job
8. kirim output
9. callback status ke Cloudflare
10. cleanup
```

### Environment secret minimal

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_API_SECRET
OPENROUTER_API_KEY
GOOGLE_SHEETS_CREDENTIALS
GOOGLE_SHEETS_SPREADSHEET_ID
CLOUDFLARE_CALLBACK_URL
CLOUDFLARE_CALLBACK_SECRET
```

### Jangan gunakan artifact sebagai storage utama

Job harus sebisa mungkin:

```text
Generate
→ Send Telegram
→ optional upload R2
→ update DB
→ cleanup
```

Bukan:

```text
Generate
→ simpan artifact permanen
→ user baru mengambil nanti
```

---

# 30A.6 PHASE DEPLOY 3 — CLOUDFLARE WORKER

Buat Worker yang memiliki route utama:

```text
POST /telegram/webhook
POST /internal/job/update
GET  /health
GET  /status
```

### `/telegram/webhook`

Urutan:

```text
Request masuk
   ↓
check X-Telegram-Bot-Api-Secret-Token
   ↓
parse update
   ↓
authorized?
   ↓
resolve command/intent
   ↓
create job_id
   ↓
INSERT jobs ke D1
   ↓
dispatch GitHub Action
   ↓
return 200 OK
```

Worker tidak boleh menunggu sampai Python selesai. Telegram webhook harus mendapatkan response cepat.

### `/internal/job/update`

Endpoint ini hanya menerima callback dari GitHub worker.

Validasi:

```text
Authorization / secret header
→ job_id valid
→ allowed status transition
→ update D1
```

Status transition:

```text
queued
  ↓
running
  ↓
success
```

atau:

```text
queued
  ↓
running
  ↓
failed
```

Tidak boleh terjadi:

```text
success → running
failed  → queued
```

kecuali memang ada command retry yang membuat attempt baru.

---

# 30A.7 PHASE DEPLOY 4 — CLOUDFLARE D1

## Database minimal

### `jobs`

```sql
CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  account TEXT NOT NULL,
  task TEXT NOT NULL,
  request_text TEXT,
  chat_id TEXT,
  status TEXT NOT NULL,
  attempt INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  error_code TEXT,
  error_message TEXT,
  result_json TEXT
);
```

### `content_items`

```sql
CREATE TABLE content_items (
  id TEXT PRIMARY KEY,
  account TEXT NOT NULL,
  content_type TEXT NOT NULL,
  topic TEXT NOT NULL,
  title TEXT,
  created_at TEXT NOT NULL,
  source_hash TEXT,
  payload_json TEXT
);
```

### `content_sources`

```sql
CREATE TABLE content_sources (
  id TEXT PRIMARY KEY,
  content_id TEXT,
  source_type TEXT,
  source_url TEXT,
  title TEXT,
  published_at TEXT,
  collected_at TEXT NOT NULL,
  relevance_score REAL,
  freshness_score REAL
);
```

### `chess_events`

```sql
CREATE TABLE chess_events (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  title TEXT NOT NULL,
  start_at TEXT,
  duration_minutes INTEGER,
  format TEXT,
  join_url TEXT,
  season TEXT,
  league TEXT,
  status TEXT NOT NULL,
  payload_json TEXT
);
```

---

# 30A.8 PHASE DEPLOY 5 — JOB DISPATCH DARI CLOUDFLARE KE GITHUB

Metode utama:

```text
Cloudflare Worker
      ↓
GitHub API
      ↓
repository_dispatch
      ↓
workflow.yml
```

GitHub mendukung `repository_dispatch` untuk memicu workflow dari aktivitas di luar GitHub dan menyediakan `client_payload` untuk data job. Fine-grained token dapat digunakan dengan permission `Contents: write`. citeturn805722search2

## Secret yang diperlukan di Worker

```text
GITHUB_TOKEN
GITHUB_OWNER
GITHUB_REPO
```

Gunakan fine-grained GitHub token dengan permission minimum yang diperlukan.

Jangan menyimpan token GitHub di Python worker bila hanya Cloudflare yang membutuhkan token untuk dispatch.

---

# 30A.9 PHASE DEPLOY 6 — TELEGRAM WEBHOOK MIGRATION

Bot sekarang menggunakan long polling. Deployment cloud menggantinya dengan webhook.

## Sebelum migrasi

- [ ] Matikan proses `bot.py` lokal.
- [ ] Pastikan tidak ada instance polling lain menggunakan token yang sama.
- [ ] Deploy Worker.
- [ ] Tes `/health`.
- [ ] Set Telegram webhook.

Contoh konsep:

```text
https://api.telegram.org/bot<TOKEN>/setWebhook
```

dengan parameter:

```text
url = https://<worker-domain>/telegram/webhook
secret_token = <random-secret>
allowed_updates = ["message", "callback_query"]
```

Telegram mengirim secret melalui header `X-Telegram-Bot-Api-Secret-Token`. Telegram juga menyatakan `getUpdates` tidak dapat digunakan ketika outgoing webhook sedang aktif. citeturn661332search0

## Rollback

Bila deployment bermasalah:

```text
setWebhook(url="")
↓
nyalakan bot.py lokal
↓
getUpdates berjalan kembali
```

Rollback harus selalu diuji sebelum production cutover.

---

# 30A.10 PHASE DEPLOY 7 — GOOGLE SHEETS

## Struktur workbook

Gunakan satu workbook khusus klub:

```text
TCO
LIGA
ARENA
SETTINGS
```

### Sheet `TCO`

```text
id
month
title
date
start_time
timezone
duration_minutes
format
join_url
status
notes
```

### Sheet `LIGA`

```text
season
league
rank
player
played
wins
draws
losses
points
notes
```

### Sheet `ARENA`

```text
month
event_date
start_time
timezone
title
public_message
status
join_url
```

### Sheet `SETTINGS`

```text
key
value
```

Contoh:

```text
arena_day = Wednesday
arena_start_time = 23:00
arena_notice_lead_hours = 2
timezone = Asia/Jakarta
```

## Authentication

Produksi memerlukan project Google Cloud dan Google Sheets API yang diaktifkan. Google menyediakan client library Python dan merekomendasikan pendekatan autentikasi/otorisasi yang sesuai untuk production, bukan sekadar quickstart testing. citeturn660178search0

Untuk service account, alur yang direkomendasikan:

```text
Google Cloud Project
   ↓
Enable Google Sheets API
   ↓
Create service account
   ↓
Create credential
   ↓
Share target spreadsheet kepada service-account email
   ↓
GitHub Secret
   ↓
Python worker
```

Credential private wajib dianggap sebagai secret dan tidak boleh di-commit.

## Optimasi

Jangan membaca seluruh workbook berulang kali. Gunakan range yang diperlukan dan batch request. Google juga menyarankan payload sekitar maksimum 2 MB, batching, dan exponential backoff ketika terkena 429. citeturn393545search0turn393545search11

---

# 30A.11 PHASE DEPLOY 8 — D1 SEBAGAI JOB QUEUE, BUKAN MESSAGE BROKER PENUH

D1 cukup untuk state queue ringan:

```text
queued
running
success
failed
cancelled
```

Tetapi jangan membuat Worker terus-menerus polling D1 untuk mencari queue.

Pola:

```text
Webhook
 ↓
INSERT job
 ↓
Dispatch GitHub
```

Scheduler:

```text
Cron
 ↓
find due jobs
 ↓
create dispatch
```

Karena D1 Free memiliki daily row read/write limits, query scheduler harus selektif dan job state tidak boleh ditulis berulang kali tanpa kebutuhan. citeturn999493search13turn999493search3

---

# 30A.12 PHASE DEPLOY 9 — CALLBACK DARI PYTHON KE CLOUDFLARE

Python worker harus memberitahu lifecycle job:

```text
running
```

kemudian:

```text
success
```

atau:

```text
failed
```

Payload contoh:

```json
{
  "job_id": "job_20261005_000123",
  "status": "success",
  "finished_at": "2026-10-05T16:02:11+07:00",
  "result": {
    "content_id": "cnt_001",
    "media_count": 3,
    "telegram_sent": true
  }
}
```

Log detail tetap berada di GitHub Actions output dan/atau ringkasan database; jangan memasukkan API key atau credentials ke callback.

---

# 30A.13 PHASE DEPLOY 10 — SECRET MANAGEMENT

## GitHub Actions Secrets

Minimal:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
OPENROUTER_API_KEY
GOOGLE_SERVICE_ACCOUNT_JSON
GOOGLE_SPREADSHEET_ID
CALLBACK_SECRET
```

## Cloudflare Worker Secrets

Minimal:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
GITHUB_TOKEN
GITHUB_OWNER
GITHUB_REPO
CALLBACK_SECRET
```

## Secret policy

```text
Source code             = no secret
.env                    = local only
GitHub Secrets          = CI secret
Cloudflare Secrets      = Worker secret
D1                      = state only, never raw credential
Logs                    = redact secrets
```

---

# 30A.14 PHASE DEPLOY 11 — GRATIS DAN ANTI-BILLING GUARDRAILS

Karena requirement proyek adalah **sebisa mungkin gratis dan tidak terjadi auto-charge**, deployment harus memiliki pagar berikut.

## GitHub

- [ ] Jangan memasukkan payment method selama masih ingin hard-stop setelah quota.
- [ ] Gunakan standard runner saja.
- [ ] Jangan menggunakan larger runner.
- [ ] Monitor Actions minutes.
- [ ] Batasi concurrency.
- [ ] Hindari job retry tanpa batas.
- [ ] Jangan upload artifact besar tanpa alasan.
- [ ] Hindari workflow loop.

GitHub mendokumentasikan bahwa tanpa payment method, penggunaan Actions akan diblokir setelah quota gratis habis; dengan payment method, penggunaan tambahan dapat menjadi billable. citeturn805722search4

## Cloudflare

- [ ] Pertahankan Workers Free.
- [ ] Monitor Worker request/CPU usage.
- [ ] Monitor D1 row reads/writes.
- [ ] Jangan mengaktifkan layanan paid hanya untuk convenience.
- [ ] R2 tetap OFF untuk baseline jika storage permanen belum diperlukan.

Workers Free dan D1 Free memiliki batas harian; ketika batas free tercapai, operasi terkait akan gagal sampai reset atau perlu upgrade untuk melanjutkan. citeturn999493search10turn999493search8

## OpenRouter

- [ ] Simpan key sebagai secret.
- [ ] Set model fallback.
- [ ] Batasi jumlah request/job.
- [ ] Tolak pesan spam/unclear sebelum AI call.
- [ ] Simpan hasil yang sudah dibuat untuk mengurangi regenerasi.

OpenRouter menyatakan memulai penggunaan tidak membutuhkan subscription atau kartu, tetapi model/provider tertentu bisa memiliki kondisi biaya sendiri. citeturn393545search10

---

# 30A.15 PHASE DEPLOY 12 — CONCURRENCY CONTROL

Karena GitHub Actions dapat menerima trigger berturut-turut, perlu lock.

## Rule

Untuk account yang sama:

```text
max_concurrency = 1
```

Contoh:

```text
MLBB job sedang running
      ↓
request baru
      ↓
queued
```

Untuk account berbeda, concurrency dapat dinaikkan setelah stabil.

Target awal:

```text
global max concurrent jobs = 1
```

Kemudian:

```text
production target = 2
```

setelah konsumsi minutes dan resource terukur.

---

# 30A.16 PHASE DEPLOY 13 — IDEMPOTENCY

Job tidak boleh menghasilkan konten dua kali akibat webhook retry atau workflow retry.

Gunakan:

```text
job_id
request_hash
idempotency_key
```

Sebelum start:

```text
apakah job_id sudah success?
   ↓
YES → return hasil lama
NO  → lanjut
```

Telegram sendiri dapat mengulangi delivery webhook ketika request sebelumnya gagal. Karena itu Worker harus selalu membedakan update yang sudah diproses dari update baru. citeturn661332search0

---

# 30A.17 PHASE DEPLOY 14 — MEDIA STRATEGY TANPA R2

Untuk baseline, jangan mengarsipkan media di cloud.

```text
Python runner
   ↓
output/
   ├── image.png
   └── video.mp4
   ↓
Telegram
   ↓
cleanup
```

Telegram menjadi delivery channel dan source file permanen pertama bagi penggunaan operasional manual.

Database hanya menyimpan:

```text
content_id
file_name
mime_type
size_bytes
telegram_message_id
created_at
```

Bukan binary file.

## Kapan R2 diaktifkan

Aktifkan R2 bila salah satu kebutuhan berikut muncul:

- perlu download ulang dari dashboard;
- perlu arsip > beberapa hari;
- perlu content library;
- perlu asset URL;
- perlu reuse media antarkonten.

---

# 30A.18 PHASE DEPLOY 15 — SCHEDULER CLOUD

Scheduler tidak membuat konten secara langsung.

Scheduler hanya:

```text
find due event
→ create job
→ dispatch job
```

## TCO scheduler

```text
setiap hari 18:00 WIB
   ↓
cek event TCO untuk hari berikutnya
   ↓
kalau ada
   ↓
create tco announcement job
```

## Arena scheduler

```text
awal bulan
   ↓
create arena announcement
```

Kemudian:

```text
T-2 jam
   ↓
check join_url
   ↓
kalau ada → generate final reminder
```

Jika link belum ada:

```text
status = WAITING_FOR_LINK
```

bukan error.

## Content planner

Contoh:

```text
Senin 08:00
   ↓
weekly briefing job
   ↓
research topik
   ↓
rekomendasi konten
   ↓
Telegram
```

---

# 30A.19 PHASE DEPLOY 16 — HEALTH CHECK

Worker:

```text
GET /health
```

Expected:

```json
{
  "status": "ok",
  "service": "social-media-assistant",
  "version": "1.0.0"
}
```

D1 check:

```text
health
 ↓
SELECT 1
```

GitHub check:

```text
manual dispatch test
```

Telegram check:

```text
getWebhookInfo
```

Telegram menyediakan `getWebhookInfo` untuk melihat URL webhook, pending updates, dan error webhook terakhir. citeturn661332search0

---

# 30A.20 PHASE DEPLOY 17 — OBSERVABILITY

## Dashboard minimal

Tampilkan:

```text
Jobs today
Jobs success
Jobs failed
Queued
Avg processing time
AI failures
Research failures
Telegram failures
Actions minutes estimate
D1 usage
```

## Logging

Gunakan format:

```text
timestamp
job_id
account
task
stage
status
duration
error_code
```

Contoh:

```text
2026-10-05T16:00:21+07:00
job_123
mlbb
content
research
SUCCESS
12.3s
-
```

---

# 30A.21 PHASE DEPLOY 18 — CI PIPELINE

Sebelum merge ke `main`:

```text
push
 ↓
tests.yml
 ↓
lint
 ↓
unit tests
 ↓
import checks
 ↓
workflow success
 ↓
merge
```

Deployment Worker:

```text
merge main
 ↓
deploy-worker.yml
 ↓
wrangler deploy
```

Python worker tidak perlu otomatis dieksekusi setiap push. Ia hanya dijalankan ketika ada job.

---

# 30A.22 PHASE DEPLOY 19 — LOCAL / CLOUD DUAL MODE

Untuk debugging, project harus mendukung dua mode:

### Local

```text
bot.py / local webhook simulation
   ↓
Python worker
```

### Cloud

```text
Telegram webhook
   ↓
Cloudflare Worker
   ↓
GitHub Actions
   ↓
Python worker
```

Config:

```text
APP_ENV=local
APP_ENV=cloud
```

Jangan membuat logic bisnis bercabang berdasarkan environment lebih dari yang diperlukan.

---

# 30A.23 PHASE DEPLOY 20 — ROLLOUT BERTAHAP

Jangan cutover empat akun sekaligus.

## Step 1 — Health only

```text
Cloudflare Worker
   ↓
health
```

## Step 2 — Telegram test

```text
/start
/status
```

## Step 3 — Simple content

```text
buat konten wedding sederhana
```

## Step 4 — Image

```text
buat gambar wedding
```

## Step 5 — Video

```text
buat video MLBB
```

## Step 6 — Chess read-only

```text
/tco
/liga
/arena
```

## Step 7 — Scheduler

```text
TCO reminder
Arena announcement
```

## Step 8 — Semua akun

```text
Wedding
MLBB
Fashion
Chess
```

---

# 30A.24 PHASE DEPLOY 21 — ROLLBACK PLAN

## Rollback Telegram

```text
deleteWebhook
↓
run local long polling
```

## Rollback Cloudflare

```text
deploy previous worker version
```

## Rollback Python

GitHub Actions menggunakan commit/tag stabil terakhir.

```text
v1.0.0
↓
v1.0.1
↓
regression
↓
rollback v1.0.0
```

## Rollback database

Schema migration harus versioned.

```text
migration_001
migration_002
migration_003
```

Jangan mengedit schema production secara manual tanpa migration file.

---

# 30A.25 PHASE DEPLOY 22 — SECURITY HARDENING

## Telegram

- [ ] Webhook secret aktif.
- [ ] Chat allowlist aktif.
- [ ] Validasi command callback.
- [ ] Rate limit sederhana.
- [ ] Jangan percaya `chat_id` dari payload sebagai authorization tunggal tanpa allowlist.

## Cloudflare

- [ ] Secrets hanya di Worker secret store.
- [ ] Internal endpoint memakai secret terpisah.
- [ ] Jangan expose D1 langsung tanpa authentication.

Cloudflare sendiri merekomendasikan penggunaan Worker sebagai API untuk mengakses D1 dari luar Worker daripada mengekspos akses langsung, serta menyarankan parameterized queries dan access control. citeturn805722search0

## GitHub

- [ ] Fine-grained token.
- [ ] Permission minimum.
- [ ] Jangan pakai token classic bila tidak diperlukan.
- [ ] Actions workflow hanya menerima payload yang tervalidasi.

## Google

- [ ] Spreadsheet hanya dibagikan ke credential yang diperlukan.
- [ ] Credential JSON tidak masuk Git.
- [ ] Rotate/revoke credential bila bocor.

---

# 30A.26 PHASE DEPLOY 23 — CHECKLIST COMMAND TELEGRAM

Setelah cloud aktif, command minimum:

```text
/start
/help
/status
/akun

/content wedding
/content mlbb
/content fashion

/tco
/tco next
/liga A
/arena
/arena link <url>
```

Natural language juga harus tetap didukung:

```text
buat 3 konten wedding minggu ini
cari meta mlbb terbaru
buat konten fashion affiliate
tco minggu ini
update klasemen liga A
buat poster arena kings
```

---

# 30A.27 PHASE DEPLOY 24 — CLOUD ACCEPTANCE TEST

## Test 1 — Telegram → Worker

```text
kirim /status
```

Expected:

```text
Worker menerima update
D1 job/event tercatat jika relevan
Telegram mendapat response
```

## Test 2 — Worker → GitHub

```text
buat konten wedding
```

Expected:

```text
D1 = queued
GitHub workflow = triggered
D1 = running
D1 = success
Telegram = hasil
```

## Test 3 — failure

Matikan OpenRouter secret sementara pada environment test.

Expected:

```text
job = failed
error_code = AI_AUTH_ERROR
Telegram = pesan error yang aman
```

Jangan tampilkan secret.

## Test 4 — duplicate webhook

Kirim update yang sama dua kali pada test harness.

Expected:

```text
1 job
1 generation
```

## Test 5 — spreadsheet

Ubah satu row TCO.

Expected:

```text
/tco
→ membaca nilai baru
```

## Test 6 — rendering

Generate:

```text
1 image
1 video
```

Expected:

```text
Telegram menerima file
DB mencatat hasil
runner cleanup
```

---

# 30A.28 PHASE DEPLOY 25 — COST / QUOTA MONITORING

Walaupun baseline dirancang untuk free-only, semua limit harus diperlakukan sebagai quota keras.

## GitHub

Pantau:

```text
Actions minutes
Artifacts
Cache
Failed jobs
Retry count
```

Free plan GitHub saat ini mencantumkan 2.000 CI/CD minutes/month; standard runners di public repo gratis, sementara private repo memakai quota plan dan dapat menjadi billable jika payment method tersedia. citeturn805722search5turn805722search4

## Cloudflare Workers

Pantau:

```text
requests
CPU
D1 rows read
D1 rows written
D1 storage
```

Workers Free memiliki 100.000 request/day dan 10 ms CPU/request; D1 Free memiliki 5M row reads/day, 100K writes/day, dan 5 GB storage. citeturn999493search10turn999493search13

## Google Sheets

Pantau error:

```text
429
401
403
```

Implement exponential backoff.

---

# 30A.29 PHASE DEPLOY 26 — STRATEGI BACKUP

## Source code

```text
Git
GitHub
release tags
```

## D1

Minimal:

```text
periodic export / backup
schema migrations
```

## Spreadsheet

Tetap menjadi source manual yang mudah diduplikasi.

## Media

Baseline:

```text
Telegram + optional local download
```

Future:

```text
R2 archive
```

---

# 30A.30 PHASE DEPLOY 27 — FINAL PRODUCTION FLOW

Setelah seluruh deployment lulus, flow final menjadi:

```text
USER
 │
 │ Telegram
 ▼
CLOUDFLARE WORKER
 │
 ├── authenticate
 ├── resolve intent
 ├── create job
 ├── D1
 └── GitHub dispatch
          │
          ▼
    GITHUB ACTIONS
          │
          ▼
      PYTHON WORKER
          │
    ┌─────┼─────────┐
    ▼     ▼         ▼
 Research Sheets  History
    │     │         │
    └─────┼─────────┘
          ▼
      OpenRouter
          │
          ▼
    Structured JSON
          │
    ┌─────┼──────┐
    ▼     ▼      ▼
 Image Video    Text
    │     │      │
    └─────┼──────┘
          ▼
       Telegram
          │
          ▼
   USER REVIEW / POST
```

---

# 30A.31 URUTAN IMPLEMENTASI DEPLOY YANG HARUS DIIKUTI

Jangan mengerjakan deployment dalam satu commit besar. Ikuti urutan berikut:

```text
D01  pisahkan worker.py
D02  tambah job contract
D03  tambah D1 schema
D04  tambah database repository
D05  tambah GitHub workflow manual
D06  jalankan Python worker di GitHub secara manual
D07  verifikasi Playwright
D08  verifikasi FFmpeg
D09  verifikasi OpenRouter
D10  verifikasi Google Sheets
D11  verifikasi Telegram send
D12  buat Cloudflare Worker /health
D13  bind D1 ke Worker
D14  buat endpoint internal callback
D15  buat GitHub dispatch dari Worker
D16  test Worker → GitHub
D17  test GitHub → callback → D1
D18  set Telegram webhook
D19  test /status
D20  test Wedding
D21  test MLBB
D22  test Fashion
D23  test TCO
D24  test Liga
D25  test Arena
D26  aktifkan scheduler
D27  aktifkan deduplication
D28  aktifkan concurrency lock
D29  aktifkan monitoring
D30  production cutover
```

---

# 30A.32 TARGET AKHIR DEPLOYMENT

Core system dianggap **cloud-ready v1** bila:

- [ ] PC lokal tidak perlu hidup untuk menerima command Telegram.
- [ ] Telegram webhook aktif.
- [ ] Cloudflare Worker menerima dan mengamankan webhook.
- [ ] Worker dapat membuat job.
- [ ] D1 menyimpan status job.
- [ ] Worker dapat memicu GitHub Actions.
- [ ] GitHub Actions dapat menjalankan Python worker.
- [ ] Playwright/Chromium berjalan di runner.
- [ ] FFmpeg berjalan di runner.
- [ ] OpenRouter berjalan via secret.
- [ ] Google Sheets dapat dibaca oleh worker.
- [ ] Hasil dapat dikirim kembali ke Telegram.
- [ ] History tersimpan di D1.
- [ ] Duplicate job dicegah.
- [ ] Scheduler dapat membuat job.
- [ ] Failure dapat di-retry.
- [ ] Rollback Telegram diuji.
- [ ] Tidak ada credential di repository.
- [ ] Tidak ada R2 dependency untuk core v1.
- [ ] Tidak ada auto-posting TikTok/Instagram.

---

# 30A.33 CATATAN KHUSUS R2

R2 tetap dipertahankan di arsitektur sebagai **future storage layer**, tetapi tidak dimasukkan ke jalur wajib v1.

Alasannya bukan karena R2 tidak bagus. Justru R2 cocok untuk object storage, tetapi kebutuhan saat ini dapat dipenuhi dengan:

```text
Generate
→ Telegram
→ cleanup
```

Memaksakan R2 pada awal deployment menambah satu komponen billing/subscription yang belum diperlukan.

Ketika R2 akhirnya diperlukan, migrasi:

```text
media_store.py
```

cukup diubah dari:

```text
LocalMediaStore
```

menjadi:

```text
R2MediaStore
```

tanpa mengubah content generator.

---

# 30A.34 CATATAN KHUSUS D1

D1 menjadi penyimpanan state cloud, tetapi Python worker tidak mengakses D1 secara langsung melalui credential admin sebagai jalur utama.

Gunakan:

```text
Python Worker
   ↓ HTTPS
Cloudflare internal API
   ↓
D1 binding
```

Dengan demikian:

```text
D1
 ↑
Worker
 ↑
Python
```

dan bukan:

```text
Python
 ↓
Cloudflare account-wide admin API
 ↓
D1
```

Cloudflare sendiri menyediakan pola proxy Worker untuk mengakses D1 dari aplikasi luar dan menekankan kebutuhan access control serta parameterized queries. citeturn805722search0

---

# 30A.35 CATATAN KHUSUS GOOGLE SHEETS

Google Sheets tidak dijadikan database utama aplikasi.

Pembagian:

```text
Google Sheets
= data operasional klub yang mudah diedit manusia

D1
= state, history, jobs, logs metadata
```

Contoh:

```text
Spreadsheet
   ↓
TCO tanggal 14/10, 20:00, Blitz, URL
   ↓
Python
   ↓
validate
   ↓
D1 chess_events
   ↓
AI formatter
```

Jadi spreadsheet tetap nyaman bagi pengelola klub, sedangkan D1 menangani state aplikasi.

---

# 30A.36 DOKUMENTASI YANG HARUS ADA SETELAH DEPLOY

Tambahkan:

```text
/docs
  architecture.md
  deployment.md
  telegram-webhook.md
  github-actions.md
  cloudflare.md
  d1.md
  google-sheets.md
  secrets.md
  rollback.md
  troubleshooting.md
```

`deployment.md` minimal harus memuat:

```text
1. prerequisite
2. Cloudflare setup
3. D1 setup
4. GitHub setup
5. secrets
6. Worker deploy
7. webhook setup
8. Google Sheets setup
9. test
10. rollback
```

---

# 30A.37 SUMBER RESMI YANG MENJADI ACUAN DEPLOYMENT

- Cloudflare Workers limits/pricing: https://developers.cloudflare.com/workers/platform/pricing/
- Cloudflare Workers limits: https://developers.cloudflare.com/workers/platform/limits/
- Cloudflare D1 pricing: https://developers.cloudflare.com/d1/platform/pricing/
- Cloudflare D1 limits: https://developers.cloudflare.com/d1/platform/limits/
- Cloudflare D1 external API pattern: https://developers.cloudflare.com/d1/tutorials/build-an-api-to-access-d1/
- Cloudflare R2: https://developers.cloudflare.com/r2/get-started/
- GitHub pricing: https://github.com/pricing
- GitHub Actions billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- GitHub repository dispatch: https://docs.github.com/en/rest/repos/repos
- GitHub workflow dispatch: https://docs.github.com/en/rest/actions/workflows
- Telegram Bot API / Webhook: https://core.telegram.org/bots/api
- Google Sheets API: https://developers.google.com/workspace/sheets/api/quickstart/python
- Google Sheets API limits: https://developers.google.com/workspace/sheets/api/limits
- OpenRouter developer docs: https://openrouter.ai/developers

Catatan: limit dan kebijakan provider dapat berubah. Sebelum production cutover, cek kembali dashboard/official docs provider yang bersangkutan.

---

# 30A.38 CHECKPOINT FINAL DEPLOYMENT

```text
[ ] LOCAL BASELINE PASSED
        ↓
[ ] WORKER PYTHON PASSED
        ↓
[ ] GITHUB ACTIONS PASSED
        ↓
[ ] CLOUDFLARE WORKER PASSED
        ↓
[ ] D1 PASSED
        ↓
[ ] GOOGLE SHEETS PASSED
        ↓
[ ] TELEGRAM WEBHOOK PASSED
        ↓
[ ] END-TO-END CONTENT PASSED
        ↓
[ ] CHESS OPERATIONS PASSED
        ↓
[ ] QUOTA/BILLING GUARD PASSED
        ↓
[ ] ROLLBACK PASSED
        ↓
[ ] PRODUCTION
```

Setelah checkpoint ini lulus, bot sudah dapat dianggap sebagai **Social Media Assistant cloud-based**, sementara TikTok/Instagram publisher tetap menjadi modul terpisah yang bisa dinyalakan kemudian setelah approval API tersedia.

# 31. PHASE 26 — CLOUD STORAGE / PERSISTENCE

## Minimal

SQLite dapat digunakan pada fase development.

Untuk deployment yang worker-nya ephemeral, gunakan persistent database/storage yang sesuai dengan layer cloud.

## Prinsip

```text
Database = state
Object storage = media
Worker filesystem = temporary
```

Jangan mengandalkan file lokal worker sebagai storage permanen.

---

# 32. PHASE 27 — SCHEDULER

## Scheduler yang dibutuhkan

### TCO

```text
weekly check
```

### Liga

```text
scheduled / manual update
```

### Arena Kings

```text
monthly schedule
T-2 hour reminder
```

### Content planner

```text
daily briefing
weekly briefing
```

## Prinsip

Scheduler hanya membuat job.

Scheduler tidak boleh berisi logic generator.

```text
Scheduler
   ↓
Create job
   ↓
Worker
   ↓
Handler
```

---

# 33. PHASE 28 — ERROR HANDLING

## Error categories

```text
CONFIG_ERROR
AUTH_ERROR
RESEARCH_ERROR
AI_ERROR
DATA_ERROR
RENDER_ERROR
TELEGRAM_ERROR
STORAGE_ERROR
```

## Rule

### Research gagal

Gunakan cached result atau fallback topic.

### AI gagal

Retry / fallback model.

### Spreadsheet gagal

Gunakan cached copy jika aman dan beri warning.

### Render gagal

Tetap kirim text/caption.

### Data Liga tidak lengkap

Stop generation yang membutuhkan angka.

---

# 34. PHASE 29 — LOGGING & OBSERVABILITY

## Setiap job mencatat

```text
job_id
account
task
status
research_duration
ai_duration
render_duration
send_duration
total_duration
error
```

## Contoh

```text
JOB=20261005-0001
ACCOUNT=mlbb
TASK=content
RESEARCH=12.4s
AI=8.7s
RENDER=5.1s
SEND=1.2s
TOTAL=27.4s
STATUS=SUCCESS
```

## Acceptance Criteria

Satu job dapat ditelusuri dari request hingga output.

---

# 35. PHASE 30 — SECURITY CHECK

## Wajib

- [ ] Telegram token di secret
- [ ] OpenRouter key di secret
- [ ] Spreadsheet credential di secret
- [ ] Tidak ada token dalam log
- [ ] Tidak ada secret di Git
- [ ] Validasi Telegram chat/user
- [ ] Validasi URL
- [ ] Sanitasi file name
- [ ] Limit ukuran file
- [ ] Limit job concurrency

---

# 36. PHASE 31 — TEST MATRIX

## Account tests

- [ ] Chess
- [ ] Wedding
- [ ] MLBB
- [ ] Fashion

## Content tests

- [ ] text
- [ ] image
- [ ] video
- [ ] multi-content

## Chess tests

- [ ] TCO minggu ini
- [ ] TCO next
- [ ] Liga A
- [ ] Liga B
- [ ] Arena bulan ini
- [ ] Arena tanpa link
- [ ] Arena dengan link

## Failure tests

- [ ] OpenRouter gagal
- [ ] Research gagal
- [ ] Spreadsheet gagal
- [ ] Telegram gagal
- [ ] Render gagal
- [ ] Data invalid
- [ ] User tidak authorized

---

# 37. PHASE 32 — END-TO-END ACCEPTANCE TEST

Sebelum dianggap v1 selesai, jalankan skenario lengkap berikut.

## Scenario A — Wedding

```text
buatkan 3 konten wedding trend minggu ini
```

Expected:

```text
3 content concepts
3 scripts
3 captions
sources
media
history
```

## Scenario B — MLBB

```text
buat konten MLBB tentang meta terbaru
```

Expected:

```text
research
source
fact status
content
media
history
```

## Scenario C — Fashion

```text
buat 3 ide affiliate fashion
```

Expected:

```text
3 ideas
hook
script
CTA
caption
```

## Scenario D — TCO

```text
/tco minggu ini
```

Expected:

```text
event details
WA copy
social copy
poster optional
```

## Scenario E — Liga

```text
/liga A
```

Expected:

```text
validated standings
news
WA
social
image
```

## Scenario F — Arena

```text
/arena
```

Expected:

```text
monthly announcement
poster
WA
social
```

Kemudian:

```text
/arena link <URL>
```

Expected:

```text
linked event
final reminder
```

---

# 38. PHASE 33 — RELEASE v1.0

## Scope

v1.0 dianggap selesai ketika fitur berikut stabil:

```text
✅ 4 accounts
✅ smart router
✅ Telegram menu
✅ SQLite / persistent state
✅ TCO
✅ Liga
✅ Arena
✅ Wedding content
✅ MLBB content
✅ Fashion content
✅ Chess content
✅ research engine
✅ source tracking
✅ image generation/render
✅ video generation/render
✅ history
✅ basic deduplication
✅ logging
✅ error handling
```

## Yang BELUM masuk v1

```text
⏸ TikTok auto-post
⏸ Instagram auto-post
⏸ analytics sosial otomatis
⏸ advanced recommendation model
```

---

# 39. PHASE 34 — v1.1 QUALITY IMPROVEMENT

Setelah v1 stabil, jangan langsung menambah fitur besar.

Perbaiki kualitas:

- prompt;
- template;
- source ranking;
- duplicate detection;
- speed;
- error recovery;
- UX Telegram.

## Target

Kurangi kebutuhan edit manual sebelum posting.

---

# 40. PHASE 35 — v1.2 CONTENT INTELLIGENCE

Tambahkan:

```text
quality score
feedback loop
content recommendation
weekly brief
trend brief
```

Bot mulai bisa berkata:

```text
3 topik MLBB yang belum dibuat minggu ini:
1. ...
2. ...
3. ...
```

---

# 41. PHASE 36 — FUTURE PUBLISHER LAYER

Ketika TikTok/Meta sudah siap, jangan ubah content engine.

Tambahkan layer baru:

```text
Publisher Interface
├── ManualPublisher
├── TikTokPublisher
└── InstagramPublisher
```

Workflow:

```text
Content Approved
       ↓
Publisher Router
       ↓
Platform adapter
       ↓
Publish
```

## Prinsip

Content creation tetap dapat berjalan walaupun publisher sedang mati/nonaktif.

---

# 42. STRUKTUR PROJECT TARGET

```text
project/
│
├── bot.py
├── worker.py
├── requirements.txt
├── accounts.json
├── accounts.example.json
├── .env.example
│
├── utils/
│   ├── telegram_bot.py
│   ├── telegram_transport.py
│   ├── telegram_menu.py
│   ├── router.py
│   ├── intent_schema.py
│   ├── accounts.py
│   ├── notifier.py
│   │
│   ├── database.py
│   ├── repositories.py
│   │
│   ├── ai/
│   │   ├── base_generator.py
│   │   ├── content_generator.py
│   │   ├── wedding_generator.py
│   │   ├── mlbb_generator.py
│   │   ├── fashion_generator.py
│   │   ├── chess_generator.py
│   │   ├── tco_generator.py
│   │   ├── liga_generator.py
│   │   └── arena_generator.py
│   │
│   ├── research/
│   │   ├── base.py
│   │   ├── web.py
│   │   ├── youtube.py
│   │   ├── news.py
│   │   └── manual.py
│   │
│   ├── chess/
│   │   ├── spreadsheet.py
│   │   ├── validators.py
│   │   ├── tco.py
│   │   ├── liga.py
│   │   ├── arena.py
│   │   └── arena_scheduler.py
│   │
│   └── media/
│       ├── image_maker.py
│       ├── video_maker.py
│       ├── template_engine.py
│       └── asset_manager.py
│
├── templates/
│   ├── wedding/
│   ├── mlbb/
│   ├── fashion/
│   └── chess/
│       ├── tco/
│       ├── liga/
│       └── arena/
│
├── data/
│   └── app.db
│
├── output/
│   ├── images/
│   ├── videos/
│   └── posters/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── scenarios/
│
└── logs/
```

---

# 43. PEMBAGIAN TUGAS ANTAR FILE

## `bot.py`

Hanya entry point.

## `telegram_bot.py`

Mengurus lifecycle Telegram.

## `router.py`

Menentukan account + task.

## `worker.py`

Menjalankan job.

## `database.py`

Koneksi dan schema DB.

## `research/*`

Mengambil dan normalisasi sumber.

## `ai/*`

Mengubah context menjadi output terstruktur.

## `chess/*`

Semua logic operasional catur.

## `media/*`

Mengubah JSON menjadi media.

## `notifier.py`

Mengirim paket ke Telegram.

Dengan pembagian ini, perubahan satu modul tidak menimbulkan domino change ke semua sistem.

---

# 44. GIT / BRANCH STRATEGY

Gunakan branch per fase.

```text
main
│
├── feature/accounts-v2
├── feature/database
├── feature/router
├── feature/telegram-ui
├── feature/chess-tco
├── feature/chess-liga
├── feature/chess-arena
├── feature/content-engines
├── feature/research-v2
├── feature/media-v2
├── feature/history-dedup
└── feature/deployment
```

Setelah lulus test:

```text
feature
   ↓
main
   ↓
tag release
```

---

# 45. DEFINITION OF DONE PER PHASE

Setiap fase hanya dianggap selesai jika:

```text
1. kode selesai
2. test selesai
3. tidak merusak feature lama
4. log dapat dibaca
5. error handling tersedia
6. commit dibuat
7. dokumentasi diupdate
```

Tidak boleh melanjutkan fitur besar jika fase sebelumnya belum lolos acceptance criteria.

---

# 46. PRIORITAS ABSOLUT

## P0 — Wajib

```text
Accounts
Router
Database
Chess spreadsheet
TCO
Liga
Arena
Content engines
Research
Media
History
Testing
```

## P1 — Setelah core stabil

```text
Planner
Quality score
Feedback
Briefing
Performance
```

## P2 — Setelah platform siap

```text
TikTok publisher
Instagram publisher
Auto scheduling
Analytics
```

---

# 47. CHECKPOINT IMPLEMENTASI

## CHECKPOINT A — Foundation

```text
Accounts v2
Database
Router
Telegram UI
```

Status target: bot sudah menjadi multi-account assistant.

## CHECKPOINT B — Chess Operations

```text
Spreadsheet
TCO
Liga
Arena
```

Status target: klub catur dapat dikelola dari Telegram.

## CHECKPOINT C — Content Factory

```text
Wedding
MLBB
Fashion
Chess
```

Status target: empat akun dapat menghasilkan konten sesuai karakter masing-masing.

## CHECKPOINT D — Intelligence

```text
Research 2.0
Fact-check
Dedup
Quality
Feedback
```

Status target: bot tidak hanya menghasilkan, tetapi membantu memilih konten.

## CHECKPOINT E — Cloud

```text
Webhook-ready
Worker
Job queue
Scheduler
Cloud entrypoint
Persistent storage
```

Status target: PC lokal tidak lagi menjadi dependency utama.

## CHECKPOINT F — Publisher-ready

```text
Content approval
Publisher abstraction
TikTok adapter
Instagram adapter
```

Status target: tinggal menyalakan publisher ketika API/platform sudah siap.

---

# 48. URUTAN CODING PALING PRAKTIS

Mulai implementasi secara benar-benar berurutan seperti ini:

```text
01. Backup
02. accounts.json v2
03. SQLite schema
04. repository layer
05. router
06. Telegram menu
07. worker.py
08. chess spreadsheet reader
09. TCO handler
10. Liga handler
11. Arena handler
12. chess content generator
13. wedding generator
14. MLBB generator
15. fashion generator
16. research adapters
17. source scoring
18. fact-check
19. media template engine
20. history
21. deduplication
22. quality score
23. feedback
24. planner
25. scheduler
26. webhook-ready transport
27. cloud worker dispatch
28. end-to-end test
29. production deployment
30. documentation update
```

---

# 49. HASIL AKHIR YANG DIHARAPKAN

Setelah seluruh core selesai, Anda cukup menggunakan Telegram seperti berbicara dengan asisten.

Contoh:

```text
buat 3 konten wedding trend minggu ini
```

```text
cari ide MLBB berdasarkan patch terbaru
```

```text
buat konten affiliate fashion dari produk ini
```

```text
tco minggu ini
```

```text
liga A update
```

```text
buat poster arena kings bulan ini
```

```text
arena link https://...
```

Dan bot selalu mengembalikan **paket siap pakai**, bukan sekadar jawaban AI.

---

# 50. ROADMAP SETELAH v1

```text
v1.0
Core Assistant

        ↓

v1.1
Quality & Reliability

        ↓

v1.2
Planning & Intelligence

        ↓

v2.0
Analytics & Learning from Feedback

        ↓

v3.0
TikTok / Instagram Publisher

        ↓

v4.0
Semi-autonomous Social Media Operations
```

---

# 51. ATURAN PENTING UNTUK PENGEMBANGAN BERIKUTNYA

1. **Jangan menghidupkan kembali auto-posting sebelum core assistant stabil.**
2. **Jangan memasukkan logic catur ke generic content generator.**
3. **Jangan menyimpan fakta yang berasal dari AI tanpa status/sumber.**
4. **Jangan membuat renderer tergantung pada format prompt AI tertentu.**
5. **Jangan membuat worker bergantung pada filesystem lokal sebagai database.**
6. **Jangan membuat scheduler menjalankan business logic langsung.**
7. **Semua job harus idempotent dan punya status.**
8. **Semua output harus mempunyai content/job ID.**
9. **Setiap fase harus dapat dites secara terpisah.**
10. **Publisher harus menjadi layer terakhir dan opsional.**

---

# 52. CHECKLIST MASTER

## Foundation

- [ ] Backup
- [ ] Accounts v2
- [ ] SQLite
- [ ] Router
- [ ] Telegram UI
- [ ] Worker

## Chess

- [ ] Spreadsheet
- [ ] TCO
- [ ] Liga
- [ ] Arena
- [ ] Chess content

## Content

- [ ] Wedding
- [ ] MLBB
- [ ] Fashion
- [ ] Research
- [ ] Fact-check
- [ ] Media

## Intelligence

- [ ] History
- [ ] Dedup
- [ ] Quality score
- [ ] Feedback
- [ ] Planner
- [ ] Briefing

## Production

- [ ] Webhook-ready
- [ ] Job queue
- [ ] Scheduler
- [ ] Persistent storage
- [ ] Cloud deployment
- [ ] Logging
- [ ] Security
- [ ] End-to-end testing

## Future

- [ ] Publisher abstraction
- [ ] TikTok adapter
- [ ] Instagram adapter
- [ ] Approval workflow
- [ ] Analytics

---

# 53. FINAL BUILD PHILOSOPHY

Project ini harus dibangun sebagai **assistant platform**, bukan kumpulan script yang kebetulan bekerja bersama.

Fondasi yang benar adalah:

```text
              DATA
               ↓
          ORCHESTRATION
               ↓
             AI
               ↓
           RENDERER
               ↓
           DELIVERY
               ↓
            HISTORY
               ↓
           FEEDBACK
               ↓
          IMPROVEMENT
```

Untuk klub catur:

```text
SPREADSHEET
     ↓
CHESS OPERATIONS
     ↓
WA / SOCIAL / POSTER
```

Untuk akun konten:

```text
RESEARCH
   ↓
ACCOUNT STRATEGY
   ↓
AI
   ↓
MEDIA
   ↓
MANUAL PUBLISH
```

Dan untuk masa depan:

```text
APPROVAL
   ↓
PUBLISHER
   ↓
SOCIAL PLATFORM
```

Dengan urutan ini, fitur baru dapat ditambahkan tanpa membongkar fondasi yang sudah ada.
