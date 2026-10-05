# PLAN UPDATE — SOCIAL MEDIA ASSISTANT BOT

## 0. Tujuan Proyek

Mengembangkan bot Telegram yang saat ini sudah berfungsi sebagai **bot pembuat konten** menjadi **Social Media Assistant pribadi** untuk mengelola empat akun sekaligus:

1. Klub Catur / TCO
2. Wedding Organizer
3. Mobile Legends Bang Bang / MLBB & Esports
4. Fashion Affiliate

Fokus fase sekarang adalah **content assistant + operational assistant**, bukan publikasi otomatis.

Integrasi TikTok dan Instagram tetap dipisahkan dari alur aktif sampai proses review/audit selesai. Dokumentasi proyek saat ini memang menyatakan bahwa publikasi otomatis belum menjadi bagian alur aktif. 

---

# 1. KONDISI SISTEM SAAT INI

## 1.1 Yang sudah berfungsi

- Telegram long polling
- Authorization chat
- Pemilihan akun berdasarkan keyword
- Resolving request sederhana
- Validasi request tidak jelas
- Riset trend berbasis Playwright/YouTube
- OpenRouter AI
- Output AI berbentuk JSON terstruktur
- Normalisasi payload AI
- Render image dengan Pillow
- Render video dengan FFmpeg
- Pengiriman media ke Telegram
- Pengiriman caption terpisah
- Logging
- TikTok/Instagram berada di luar alur aktif

## 1.2 Keterbatasan sekarang

- Router masih terutama berbasis keyword
- Akun catur belum menjadi akun aktif di konfigurasi saat ini
- Belum ada intent/task router yang formal
- Belum ada database riwayat konten
- Belum ada deduplikasi topik
- Research masih dominan YouTube
- Belum ada modul khusus TCO
- Belum ada modul khusus Liga
- Belum ada modul khusus Arena Kings
- Belum ada integrasi spreadsheet untuk data turnamen
- Belum ada sistem kalender konten
- Belum ada content planning lintas akun
- Video masih fixed 12 detik
- Belum ada template media berbeda per jenis konten
- Belum ada sistem fact-check khusus MLBB
- Belum ada sistem product/affiliate input untuk Fashion

Dokumentasi proyek saat ini juga mencatat tidak adanya riwayat/deduplication, pemrosesan serial, dan durasi video yang fixed sebagai keterbatasan. 

---

# 2. TARGET ARSITEKTUR FINAL

```text
                           TELEGRAM BOT
                                |
                                v
                         SMART REQUEST ROUTER
                                |
             +------------------+------------------+
             |                                     |
             v                                     v
       CONTENT MODE                           CHESS MODE
             |                                     |
      +------+------+                    +---------+---------+
      |      |      |                    |         |         |
      v      v      v                    v         v         v
   Wedding  MLBB  Fashion                TCO      LIGA    ARENA
      |      |      |                    |         |         |
      +------+------+                    +---------+---------+
             |                                     |
             v                                     v
       RESEARCH ENGINE                       DATA SOURCES
             |                                Spreadsheet
      +------+------+                              |
      |      |      |                              v
      v      v      v                        DATA NORMALIZER
    Trend  Search  Source                         |
      |      |      |                            v
      +------+------+                       CHESS ENGINE
             |                                 |
             +----------------+----------------+
                              |
                              v
                         OPENROUTER AI
                              |
                 +------------+------------+
                 |            |            |
                 v            v            v
               TEXT         IMAGE        VIDEO
                 |            |            |
                 +------------+------------+
                              |
                              v
                           TELEGRAM
                              |
                 +------------+------------+
                 |            |            |
                 v            v            v
                 WA        SOSMED       ARCHIVE
                              |
                              v
                       CONTENT DATABASE
```

Prinsip utama: **AI bukan satu-satunya sumber kebenaran**. Data faktual berasal dari sumber/data engine; AI bertugas mengolah, menulis, merangkum, menganalisis, dan menghasilkan konsep/media berdasarkan konteks yang diberikan.

---

# 3. PHASE 0 — STABILISASI & BACKUP

## Tujuan

Mengamankan versi bot yang saat ini sudah berfungsi sebelum refactor besar.

## Pekerjaan

- [ ] Backup repository
- [ ] Tag/branch versi stabil
- [ ] Backup `accounts.json`
- [ ] Backup `.env` secara aman dan jangan commit secret
- [ ] Backup folder `output/`
- [ ] Pastikan FFmpeg terdeteksi
- [ ] Pastikan Playwright/Chromium terpasang
- [ ] Dokumentasikan command yang saat ini berhasil
- [ ] Buat test request untuk wedding
- [ ] Buat test request untuk MLBB
- [ ] Buat test request fashion
- [ ] Simpan contoh output sukses

## Acceptance Criteria

Bot versi lama tetap bisa dijalankan dan menghasilkan output sebelum refactor dimulai.

---

# 4. PHASE 1 — REFACTOR CONFIGURATION MULTI-AKUN

## Tujuan

Mengubah konfigurasi akun menjadi struktur yang dapat menangani karakter, aturan, dan mode kerja berbeda.

## Target akun

### 4.1 Chess

```json
{
  "id": "chess",
  "label": "Klub Catur / TCO",
  "handle": "@...",
  "niche": "komunitas catur dan kegiatan TCO",
  "mode": ["content", "club_operations"],
  "tone": "komunitas, informatif, sportif",
  "keywords": [],
  "hashtags": [],
  "avoid": []
}
```

### 4.2 Wedding

Pertahankan konsep konfigurasi yang sudah ada:

- niche wedding organizer
- audience calon pengantin
- tone hangat/elegan/praktis
- keyword wedding
- seed topics
- hashtags
- aturan anti-hallucination mengenai harga/paket/tanggal/lokasi

Konfigurasi saat ini sudah menyediakan profil tersebut. 

### 4.3 MLBB

Pertahankan konsep:

- MLBB
- MPL
- hero
- meta
- esports
- tone energik
- aturan tidak mengarang hasil/statistik

Konfigurasi saat ini sudah mempunyai dasar tersebut. 

### 4.4 Fashion

Pertahankan:

- OOTD
- styling
- mix & match
- fashion hemat
- tone friendly
- aturan tidak mengarang brand/harga

Konfigurasi saat ini sudah mempunyai dasar tersebut. 

## Pekerjaan teknis

- [ ] Ganti akun `kuliner` menjadi `chess`
- [ ] Tambahkan `mode`
- [ ] Tambahkan `content_formats`
- [ ] Tambahkan `research_sources`
- [ ] Tambahkan `content_categories`
- [ ] Tambahkan `fact_check_rules`
- [ ] Tambahkan `default_templates`
- [ ] Tambahkan `schedule_rules` khusus akun yang membutuhkan

## Acceptance Criteria

Akun dapat dipanggil secara konsisten tanpa menyentuh kode Python ketika konfigurasi akun berubah.

---

# 5. PHASE 2 — SMART COMMAND & INTENT ROUTER

## Tujuan

Mengubah bot dari keyword matcher menjadi router yang memahami:

- akun
- task
- kategori
- topik
- format
- jumlah output
- target platform
- waktu/jadwal

## Struktur intent

```json
{
  "account": "mlbb",
  "task": "content",
  "category": "counter",
  "topic": "Hayabusa",
  "format": "video",
  "quantity": 1,
  "platform": ["tiktok", "instagram"],
  "date": null
}
```

## Contoh

### Request content

`buatkan 3 konten MLBB tentang counter hero`

Menjadi:

```text
account = mlbb
task = content
category = counter
quantity = 3
```

### Request TCO

`tco minggu ini`

Menjadi:

```text
account = chess
task = tco_weekly
period = current_week
```

### Request Liga

`buat pengumuman liga A`

Menjadi:

```text
account = chess
task = league_announcement
league = A
```

### Request Arena

`buat poster arena kings bulan ini`

Menjadi:

```text
account = chess
task = arena_announcement
period = current_month
```

## Pekerjaan

- [ ] Buat `router.py`
- [ ] Buat intent schema
- [ ] Fallback ke keyword matcher lama
- [ ] Tambahkan command eksplisit
- [ ] Tambahkan inline keyboard/menu
- [ ] Simpan context sesi Telegram bila diperlukan
- [ ] Ubah `telegram_bot.py` agar hanya menjadi orchestrator

## Acceptance Criteria

Bot mampu membedakan content request dan operational request tanpa bergantung hanya pada keyword.

---

# 6. PHASE 3 — TELEGRAM COMMAND CENTER

## Tujuan

Telegram menjadi dashboard utama.

## Main Menu

```text
🤖 SOCIAL MEDIA ASSISTANT

♟ Klub Catur
💍 Wedding
🎮 MLBB
👕 Fashion
📅 Content Planner
📊 History
⚙️ Settings
```

## Menu Klub Catur

```text
♟ KLUB CATUR

[TCO Mingguan]
[Liga]
[Arena Kings]
[Konten Catur]
[Jadwal]
```

## Menu Wedding

```text
💍 WEDDING

[Trend]
[Ide Konten]
[Reels]
[Carousel]
[Caption]
```

## Menu MLBB

```text
🎮 MLBB

[Patch]
[Meta]
[Hero]
[Counter]
[MPL]
[Esports]
[Tips & Trick]
[Trend]
```

## Menu Fashion

```text
👕 FASHION

[Trend]
[OOTD]
[Styling]
[Affiliate]
[Ide Konten]
```

## Acceptance Criteria

User bisa menjalankan sebagian besar pekerjaan utama tanpa mengetik command panjang.

---

# 7. PHASE 4 — CONTENT DATABASE & HISTORY

## Tujuan

Menyimpan semua request dan output untuk mencegah pengulangan dan memberi fondasi analitik.

## Database awal

SQLite direkomendasikan untuk fase awal karena sederhana dan cukup untuk satu bot.

## Tabel `contents`

```text
id
account_id
task
category
topic
title
caption
hashtags
format
platform_target
source_urls
created_at
status
output_path
prompt_version
```

## Tabel `research_items`

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
raw_data
```

## Tabel `chess_events`

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
```

## Pekerjaan

- [ ] Buat SQLite database
- [ ] Buat repository/data access layer
- [ ] Simpan request
- [ ] Simpan hasil
- [ ] Simpan source
- [ ] Simpan path media
- [ ] Tambahkan history command
- [ ] Tambahkan deduplication checker

## Acceptance Criteria

Sebelum generate, bot dapat mengecek apakah topik/angle serupa pernah dibuat.

---

# 8. PHASE 5 — RESEARCH ENGINE 2.0

## Tujuan

Meningkatkan riset trend dari sistem YouTube-only menjadi research engine multi-source.

## Arsitektur

```text
Research Request
      |
      v
Query Builder
      |
 +----+----+----+----+
 |    |    |    |    |
 v    v    v    v    v
Web  YouTube Search  Source APIs*  Manual Input
      |
      +----+----+
           |
           v
      Normalization
           |
           v
       Relevance
           |
           v
        Freshness
           |
           v
       Deduplication
           |
           v
      Research Pack
```

`*` API yang tersedia/diizinkan. Jangan bergantung pada API sosial yang sedang dalam proses review untuk fase ini.

## Research Item minimum

```json
{
  "title": "...",
  "source_url": "...",
  "source_type": "youtube|web|news|manual",
  "published_at": "...",
  "relevance_score": 0.92,
  "freshness_score": 0.87
}
```

## Pekerjaan

- [ ] Pisahkan scraper dari orchestrator
- [ ] Buat source adapter
- [ ] Normalisasi hasil
- [ ] Ranking relevance
- [ ] Ranking freshness
- [ ] Deduplicate
- [ ] Simpan URL sumber
- [ ] Kirim research pack ke AI

## Acceptance Criteria

AI menerima konteks yang mempunyai sumber, bukan sekadar daftar judul.

---

# 9. PHASE 6 — OPENROUTER CONTENT ENGINE 2.0

## Tujuan

Memisahkan generator berdasarkan tugas, bukan menggunakan satu prompt untuk semua kasus.

## Generator

```text
ContentGenerator
    |
    +-- WeddingGenerator
    +-- MLBBGenerator
    +-- FashionGenerator
    +-- ChessContentGenerator
    +-- TCOGenerator
    +-- LeagueGenerator
    +-- ArenaGenerator
```

## Output schema universal

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
  "fact_status": "verified|analysis|idea"
}
```

## Wajib

- [ ] AI harus menghasilkan JSON
- [ ] JSON divalidasi
- [ ] Field wajib memiliki fallback
- [ ] Hashtag dinormalisasi
- [ ] Source harus dipertahankan
- [ ] Fact status harus jelas
- [ ] Tidak boleh mengarang data yang tidak tersedia

---

# 10. PHASE 7 — WEDDING CONTENT SYSTEM

## Content Pillars

1. Edukasi
2. Inspirasi
3. Checklist
4. Trend
5. Problem/Solution
6. Soft Selling

## Input

```text
buat 3 konten wedding trend minggu ini
```

## Output

Untuk tiap konten:

```text
Judul
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

## Aturan

- Jangan mengarang harga paket
- Jangan menjanjikan tanggal/lokasi yang tidak tersedia
- Trend harus dapat ditelusuri sumbernya
- Hindari klaim faktual tanpa sumber

## Media

- Reels/short video
- Carousel
- Single image
- Story card

## Acceptance Criteria

Satu command dapat menghasilkan beberapa ide konten yang berbeda angle dan tidak duplikatif.

---

# 11. PHASE 8 — MLBB CONTENT SYSTEM

## Content Pillars

1. Patch update
2. Hero update
3. Meta
4. Counter
5. Build
6. Tips & tricks
7. MPL
8. Esports
9. Match analysis
10. Trend

## Jenis fakta

### VERIFIED

- Patch
- Buff/nerf
- Jadwal resmi
- Hasil pertandingan
- Klasemen
- Statistik dari sumber

### ANALYSIS

- Prediksi meta
- Analisis draft
- Potensi counter
- Opinion

### IDEA

- Meme
- Hook
- Engagement content

## Aturan fact-check

- [ ] Jangan mengarang hasil pertandingan
- [ ] Jangan mengarang statistik pemain
- [ ] Patch harus mempunyai source
- [ ] Hasil pertandingan harus mempunyai source
- [ ] Jika data tidak ditemukan, nyatakan tidak tersedia

## Acceptance Criteria

Konten faktual MLBB menyertakan source internal dan tidak mengisi data kosong dengan asumsi.

---

# 12. PHASE 9 — FASHION AFFILIATE CONTENT SYSTEM

## Content Pillars

1. OOTD
2. Mix & match
3. Styling tips
4. Trend
5. Problem/Solution
6. Affiliate

## Input product

```text
buat konten affiliate
produk: [link / foto / nama produk]
```

## Output

```text
Product angle
Hook
Script
Scene
Text overlay
CTA
Caption
Hashtag
Product placement
Affiliate CTA
```

## Aturan

- Jangan mengarang brand
- Jangan mengarang harga
- Jangan mengarang fitur produk yang tidak terlihat/tersedia
- Pisahkan opini styling dari fakta produk

## Acceptance Criteria

Bot bisa menghasilkan konten yang natural dan tidak terasa sebagai iklan keras.

---

# 13. PHASE 10 — CHESS CLUB DATA SYSTEM

## Tujuan

Menjadikan klub catur sebagai operational assistant, bukan sekadar content generator.

## Modul

```text
chess/
    spreadsheet.py
    tco.py
    liga.py
    arena.py
    chess_content.py
```

---

# 14. PHASE 11 — GOOGLE SHEET / SPREADSHEET TCO

## Struktur sheet TCO

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

## Contoh

| ID | Judul | Tanggal | Jam | Durasi | Format | Link |
|---|---|---|---|---|---|---|
| TCO-001 | TCO Week 1 | 07/10/2026 | 20:00 | 60m | Blitz | link |
| TCO-002 | TCO Week 2 | 14/10/2026 | 20:00 | 60m | Rapid | link |
| TCO-003 | TCO Week 3 | 21/10/2026 | 20:00 | 60m | Bullet | link |
| TCO-004 | TCO Week 4 | 28/10/2026 | 20:00 | 60m | Blitz | link |

## Pekerjaan

- [ ] Tentukan sumber spreadsheet
- [ ] Buat sheet TCO
- [ ] Buat spreadsheet reader
- [ ] Validasi tanggal
- [ ] Validasi jam
- [ ] Validasi link
- [ ] Mapping minggu
- [ ] Cache data bila diperlukan
- [ ] Error message jika data kosong

## Acceptance Criteria

User cukup mengisi spreadsheet bulanan dan bot dapat menemukan event yang relevan berdasarkan minggu/tanggal.

---

# 15. PHASE 12 — TCO WEEKLY ASSISTANT

## Command

```text
/tco
```

```text
/tco minggu ini
```

```text
/tco next
```

## Workflow

```text
Telegram Request
      |
      v
Find current week
      |
      v
Read spreadsheet
      |
      v
Validate event
      |
      v
Generate announcement
      |
      +------> WA message
      |
      +------> Social caption
      |
      +------> Poster (optional)
      |
      v
Send Telegram package
```

## Output package

```text
[TCO INFO]
[WA MESSAGE]
[SOSMED CAPTION]
[IMAGE]
```

## Acceptance Criteria

Satu command menghasilkan paket yang siap disalin ke WA dan sosmed.

---

# 16. PHASE 13 — LIGA / STANDING ENGINE

## Struktur spreadsheet Liga

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

## Workflow

```text
Spreadsheet
   |
   v
Read league data
   |
   v
Validate rows
   |
   v
Calculate/verify ranking
   |
   v
Generate news
   |
   v
Generate table visualization
   |
   +----> WA
   |
   +----> Social caption
   |
   +----> Image
```

## Command

```text
/liga
```

```text
/liga A
```

```text
/liga A update
```

## Acceptance Criteria

Bot bisa membuat berita klasemen berdasarkan data sheet tanpa mengarang nama, angka, atau posisi.

---

# 17. PHASE 14 — ARENA KINGS ENGINE

## Masalah

Link turnamen baru muncul sekitar dua jam sebelum acara, tetapi jadwal kegiatan sudah diketahui sebelumnya.

## Solusi dua tahap

### Tahap A — Schedule Announcement

Data berasal dari aturan jadwal bulanan.

Output:

- poster
- WA announcement
- social caption

### Tahap B — Link Update

User memberikan link ketika sudah tersedia:

```text
/arena link https://...
```

Bot menghasilkan:

- reminder
- link announcement
- updated social caption

## Data model

```text
month
date
day
start_time
location/online
link
status
```

## Acceptance Criteria

Bot tidak gagal hanya karena link resmi belum tersedia.

---

# 18. PHASE 15 — MEDIA ENGINE 2.0

## Tujuan

Media tidak lagi memakai satu template untuk semua akun.

## Template system

```text
templates/
    wedding/
    mlbb/
    fashion/
    chess/
        tco/
        liga/
        arena/
```

## Output image

- 1080x1080
- 1080x1350
- 1080x1920

## Output video

- short reel
- story format
- configurable duration
- configurable number of scenes

## Media spec object

```json
{
  "format": "video",
  "width": 1080,
  "height": 1920,
  "duration": 15,
  "scenes": 5,
  "template": "mlbb_patch"
}
```

## Pekerjaan

- [ ] Pisahkan content data dan visual template
- [ ] Buat template registry
- [ ] Buat configurable scene count
- [ ] Buat configurable duration
- [ ] Buat carousel renderer
- [ ] Buat poster generator
- [ ] Tambahkan font/font fallback yang aman
- [ ] Tambahkan asset/logo support

---

# 19. PHASE 16 — IMAGE / VISUAL GENERATION LAYER

## Tujuan

Menyediakan visual yang lebih fleksibel daripada kartu teks sederhana.

## Jenis output

### Wedding

- venue concept
- wedding decoration concept
- moodboard style
- carousel illustration

### MLBB

- infographic
- hero build card
- patch change card
- counter diagram
- esports news card

### Fashion

- outfit concept
- styling board
- combination card
- product-centered content

### Chess

- event poster
- standings poster
- announcement card
- tournament reminder

## Acceptance Criteria

Media dapat dihasilkan berdasarkan `visual_prompt` dari AI tanpa mengubah logic content generator.

---

# 20. PHASE 17 — CONTENT CALENDAR / PLANNER

## Tujuan

Bot tidak hanya menunggu perintah, tetapi dapat membantu merencanakan konten.

## Data

```text
calendar_id
account_id
date
category
topic
format
status
priority
notes
content_id
```

## Command

```text
/plan
```

```text
/plan mlbb minggu ini
```

```text
/plan wedding oktober
```

## Output

```text
SENIN
MLBB — Tips Counter

SELASA
Wedding — Checklist Persiapan

RABU
Fashion — OOTD Kampus

KAMIS
MLBB — Patch / Meta

JUMAT
Wedding — Trend
```

## Acceptance Criteria

Bot dapat membuat content plan tanpa langsung membuat semua medianya.

---

# 21. PHASE 18 — CONTENT DEDUPLICATION

## Tujuan

Menghindari pengulangan topik, angle, hook, dan struktur yang terlalu mirip.

## Mekanisme

```text
New Topic
   |
   v
Exact Match
   |
   v
Keyword Similarity
   |
   v
Semantic Similarity
   |
   +---- high similarity --> Change angle
   |
   +---- low similarity  --> Generate
```

## Pengecekan

- topic
- title
- hook
- key points
- caption
- visual concept

## Acceptance Criteria

Konten baru tidak menduplikasi konten sebelumnya secara dekat.

---

# 22. PHASE 19 — RESEARCH + FACT CHECK PIPELINE

## Tujuan

Memastikan konten faktual tidak dibangun hanya dari asumsi model.

## Pipeline

```text
Research
  |
  v
Source Validation
  |
  v
Freshness Check
  |
  v
Claim Extraction
  |
  v
AI Draft
  |
  v
Claim vs Source Check
  |
  v
Final Content
```

## Status

```text
verified
partially_verified
analysis
idea
insufficient_source
```

## Digunakan terutama untuk

- MLBB patch
- MLBB esports
- MPL
- trend yang memerlukan tanggal/fakta
- berita klasemen catur

---

# 23. PHASE 20 — NOTIFICATION & DELIVERY PACKAGE

## Tujuan

Telegram menjadi tempat menerima hasil dalam bentuk paket yang mudah digunakan.

## Format output

```text
📦 CONTENT PACKAGE

Account: MLBB
Category: Counter
Format: Video
Status: Ready

[VIDEO]

[CAPTION]

[SOURCES]

[HASHTAGS]
```

Untuk catur:

```text
📦 EVENT PACKAGE

[POSTER]

[WA VERSION]

[SOCIAL VERSION]

[DETAIL DATA]
```

## Pekerjaan

- [ ] Pisahkan WA copy dan social copy
- [ ] Tampilkan source
- [ ] Tampilkan status fact-check
- [ ] Tampilkan file path
- [ ] Tombol regenerate
- [ ] Tombol alternative angle

---

# 24. PHASE 21 — ERROR HANDLING & RESILIENCE

## Kondisi yang harus ditangani

### Research gagal

Fallback ke cached/seed topic.

### AI gagal

Fallback ke model OpenRouter berikutnya.

### Spreadsheet gagal

Gunakan cache terakhir dan tampilkan warning.

### Media gagal

Tetap kirim teks/caption.

### Data liga tidak lengkap

Jangan generate angka yang tidak ada.

### Link Arena belum tersedia

Generate schedule announcement tanpa link.

### Request ambigu

Tampilkan menu pilihan, bukan langsung memanggil AI.

---

# 25. PHASE 22 — LOGGING & OBSERVABILITY

## Logging saat ini

Log sudah tersedia dalam satu file dengan rotasi. Sistem juga mencatat durasi satu siklus. 

## Peningkatan

Tambahkan:

```text
request_id
account
intent
task
research_duration
ai_duration
render_duration
telegram_duration
total_duration
status
error
```

## Contoh

```text
[REQ-20261005-001]
account=mlbb
intent=content
research=12.4s
ai=8.7s
render=4.2s
send=1.1s
total=26.4s
status=success
```

## Acceptance Criteria

Setiap request dapat ditrace dari Telegram sampai output akhir.

---

# 26. PHASE 23 — TESTING

## Unit tests

- [ ] account matcher
- [ ] intent router
- [ ] request normalizer
- [ ] date parser
- [ ] week resolver
- [ ] spreadsheet parser
- [ ] league ranking parser
- [ ] payload normalizer
- [ ] deduplication
- [ ] source parser

## Integration tests

- [ ] Telegram → Router
- [ ] Router → Research
- [ ] Research → OpenRouter
- [ ] OpenRouter → Renderer
- [ ] Renderer → Telegram
- [ ] Spreadsheet → TCO
- [ ] Spreadsheet → Liga

## Scenario tests

### Wedding

```text
buat 3 konten wedding trend minggu ini
```

### MLBB

```text
buat konten patch terbaru MLBB
```

### Fashion

```text
buat 3 ide affiliate fashion
```

### TCO

```text
tco minggu ini
```

### Liga

```text
liga A
```

### Arena

```text
buat jadwal arena kings bulan ini
```

---

# 27. PHASE 24 — SECURITY

## Wajib

- [ ] Secret hanya di `.env`
- [ ] Jangan menyimpan token di database
- [ ] Authorization Telegram tetap aktif
- [ ] Validasi URL
- [ ] Sanitasi file path
- [ ] Batasi ukuran upload
- [ ] Validasi spreadsheet input
- [ ] Sanitasi HTML/Markdown bila dipakai
- [ ] Logging jangan membocorkan secret

---

# 28. PHASE 25 — PERFORMANCE

## Masalah sekarang

Dokumentasi saat ini mencatat satu siklus sekitar dua menit dan bot memproses request secara serial. 

## Target

- Research dapat di-cache
- Source dapat dicache sementara
- Content template dapat dicache
- Spreadsheet tidak dibaca berulang kali dalam request yang sama
- Research adapter dapat berjalan paralel jika aman
- AI call hanya dilakukan jika memang diperlukan
- History lookup cepat dengan index

## Target performa awal

```text
Simple command        < 10 detik
Cached research       < 15 detik
Fresh content         < 30 detik
Heavy render          < 60 detik
```

Target dapat disesuaikan berdasarkan hardware dan model yang digunakan.

---

# 29. PHASE 26 — CONTENT QUALITY SYSTEM

## Quality score

Setiap konten dapat diberi skor internal:

```text
Relevance
Freshness
Originality
Fact confidence
Hook quality
CTA quality
Visual readiness
```

Contoh:

```json
{
  "relevance": 0.94,
  "freshness": 0.91,
  "originality": 0.87,
  "fact_confidence": 0.96,
  "hook": 0.89
}
```

## Rule

Konten dengan quality score rendah dapat:

- regenerate
- ganti angle
- ganti source
- ditandai review manual

---

# 30. PHASE 27 — USER FEEDBACK LOOP

## Tujuan

Bot belajar dari keputusan pengguna tanpa perlu melatih model sendiri.

## Tombol

```text
[✅ Pakai]
[🔄 Regenerate]
[🎯 Ganti Angle]
[📝 Edit]
[🗑 Tolak]
```

## Data yang disimpan

```text
content_id
feedback
time
selected_variant
```

## Manfaat

- Mengetahui template favorit
- Mengetahui jenis konten yang sering ditolak
- Mengetahui angle yang disukai
- Menjadi dasar rekomendasi konten berikutnya

---

# 31. PHASE 28 — SMART DAILY / WEEKLY ASSISTANT

Setelah fondasi stabil, bot dapat mempunyai mode proaktif.

## Daily briefing

```text
🤖 DAILY SOCIAL BRIEF

💍 Wedding
1 trend menarik
2 ide konten

🎮 MLBB
Patch/news penting
3 ide konten

👕 Fashion
2 trend
2 affiliate ideas

♟ Chess
Event terdekat
TCO minggu ini
```

## Weekly briefing

```text
📅 WEEKLY CONTENT PLAN

Wedding: 4 posts
MLBB: 5 posts
Fashion: 5 posts
Chess: 2 operational + 2 social
```

Fitur ini dapat memakai scheduler setelah seluruh mesin utama stabil.

---

# 32. PHASE 29 — FUTURE AUTO-POSTING LAYER

## Status

DITUNDA.

## Prinsip

Auto-posting harus menjadi **layer terpisah** dari content engine.

```text
CONTENT READY
     |
     v
APPROVAL
     |
     v
PUBLISHER
   /     \
 TikTok  Instagram
```

## Keuntungan

Jika API/policy berubah, publisher dapat diperbaiki tanpa merusak:

- router
- research
- AI
- database
- renderer
- chess assistant

## Future command

```text
/publish content_id
```

atau setelah approval:

```text
[🚀 Publish]
```

Tetap memerlukan pengecekan permission, audit, OAuth, dan API terbaru sebelum diaktifkan.

---

# 33. STRUKTUR FOLDER TARGET

```text
project/
│
├── bot.py
├── requirements.txt
├── .env
├── accounts.json
│
├── config/
│   ├── accounts.json
│   ├── templates.json
│   ├── content_rules.json
│   └── schedules.json
│
├── database/
│   ├── database.py
│   ├── models.py
│   └── migrations.py
│
├── utils/
│   ├── telegram_bot.py
│   ├── router.py
│   ├── accounts.py
│   ├── notifier.py
│   │
│   ├── ai/
│   │   ├── content_generator.py
│   │   ├── chess_generator.py
│   │   ├── prompt_builder.py
│   │   └── validators.py
│   │
│   ├── research/
│   │   ├── manager.py
│   │   ├── youtube.py
│   │   ├── web.py
│   │   ├── trends.py
│   │   └── ranking.py
│   │
│   ├── chess/
│   │   ├── spreadsheet.py
│   │   ├── tco.py
│   │   ├── liga.py
│   │   ├── arena.py
│   │   └── schedules.py
│   │
│   ├── media/
│   │   ├── image_maker.py
│   │   ├── video_maker.py
│   │   ├── carousel_maker.py
│   │   └── template_engine.py
│   │
│   ├── history/
│   │   ├── repository.py
│   │   ├── deduplication.py
│   │   └── feedback.py
│   │
│   └── publishers/
│       ├── tiktok.py
│       └── instagram.py
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
├── output/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── scenarios/
│
└── docs/
    ├── architecture.md
    ├── commands.md
    ├── spreadsheet-schema.md
    └── deployment.md
```

---

# 34. COMMAND SPECIFICATION TARGET

## General

```text
/start
/akun
/status
/help
```

## Content

```text
/konten wedding
/konten mlbb
/konten fashion
/konten chess
```

## Research

```text
/trend wedding
/trend mlbb
/trend fashion
```

## Chess

```text
/tco
/tco minggu ini
/liga
/liga A
/arena
/arena bulan ini
/arena link <url>
```

## History

```text
/history mlbb
/history wedding
/history chess
```

## Planner

```text
/plan
/plan mlbb
/plan wedding
/plan fashion
```

---

# 35. PRIORITAS IMPLEMENTASI

## PRIORITAS P0 — WAJIB

- [ ] Backup sistem lama
- [ ] Refactor accounts
- [ ] Router/intent
- [ ] Chess account
- [ ] SQLite history
- [ ] Spreadsheet reader
- [ ] TCO module
- [ ] Liga module
- [ ] Arena module
- [ ] Telegram menu
- [ ] Error handling
- [ ] Test end-to-end

## PRIORITAS P1 — SANGAT PENTING

- [ ] Research engine 2.0
- [ ] Wedding content engine
- [ ] MLBB fact-check engine
- [ ] Fashion affiliate engine
- [ ] Media template engine
- [ ] Content deduplication
- [ ] WA/social output package

## PRIORITAS P2 — PENINGKATAN

- [ ] Content planner
- [ ] Quality score
- [ ] Feedback loop
- [ ] Daily briefing
- [ ] Weekly briefing
- [ ] Cache optimization

## PRIORITAS P3 — NANTI

- [ ] TikTok publisher
- [ ] Instagram publisher
- [ ] Approval workflow untuk publish
- [ ] Analytics
- [ ] Auto-posting

---

# 36. DEFINITION OF DONE

Proyek dianggap mencapai versi **Social Media Assistant v1.0** ketika:

- [ ] Empat akun dapat dipilih secara konsisten
- [ ] Bot memahami task, bukan hanya keyword
- [ ] Wedding dapat menghasilkan konten multi-format
- [ ] MLBB dapat menghasilkan konten berbasis source/fact status
- [ ] Fashion dapat menghasilkan content affiliate
- [ ] Chess dapat melakukan operasi TCO
- [ ] Chess dapat membuat berita/klasemen Liga
- [ ] Chess dapat membuat jadwal/poster Arena Kings
- [ ] TCO membaca data spreadsheet
- [ ] Liga membaca data klasemen
- [ ] Arena dapat bekerja tanpa link sampai link tersedia
- [ ] Semua output dapat dikirim sebagai paket ke Telegram
- [ ] Semua konten tersimpan di database
- [ ] Sistem dapat mendeteksi topik duplikat
- [ ] Error tidak menyebabkan output hilang
- [ ] Semua request tercatat di log
- [ ] Test utama berhasil
- [ ] TikTok/Instagram tetap tidak mengganggu sistem aktif

---

# 37. ROADMAP VERSI BERURUTAN

```text
STEP 01
Backup & Stabilize
        |
STEP 02
Accounts Refactor
        |
STEP 03
Smart Router
        |
STEP 04
Telegram Menu
        |
STEP 05
SQLite History
        |
STEP 06
Chess Data Layer
        |
STEP 07
Spreadsheet Reader
        |
STEP 08
TCO
        |
STEP 09
Liga
        |
STEP 10
Arena Kings
        |
STEP 11
Wedding Engine
        |
STEP 12
MLBB Engine
        |
STEP 13
Fashion Engine
        |
STEP 14
Research 2.0
        |
STEP 15
Fact Check
        |
STEP 16
Media Template Engine
        |
STEP 17
Deduplication
        |
STEP 18
Content Planner
        |
STEP 19
Feedback & Quality Score
        |
STEP 20
Daily/Weekly Assistant
        |
STEP 21
Integration Test & Hardening
        |
STEP 22
Future Publisher Layer
        |
STEP 23
TikTok/Instagram Activation
```

---

# 38. HASIL AKHIR YANG DIINGINKAN

Pada akhirnya, pengalaman pengguna harus terasa seperti ini:

```text
User:
"buatkan 3 konten MLBB tentang counter hero yang sedang meta"

Bot:
- menentukan akun MLBB
- menentukan task content
- mencari data terbaru
- mengecek source
- mengecek history agar tidak duplikat
- menyusun 3 angle
- membuat caption/script
- membuat media
- mengirim paket konten

--------------------------------

User:
"tco minggu ini"

Bot:
- membaca spreadsheet
- menemukan event minggu ini
- validasi data
- membuat WA copy
- membuat social copy
- membuat poster jika diminta
- mengirim paket

--------------------------------

User:
"liga A"

Bot:
- membaca klasemen
- memvalidasi data
- membuat berita klasemen
- membuat versi WA
- membuat versi social
- membuat image leaderboard

--------------------------------

User:
"buat arena kings bulan ini"

Bot:
- mengambil jadwal
- membuat poster
- membuat pengumuman
- menyimpan event

Dua jam sebelum acara:

User:
"arena link https://..."

Bot:
- menghubungkan link ke event
- membuat reminder
- membuat pesan final
```

---

# 39. CATATAN ARSITEKTUR PENTING

1. **Jangan menggabungkan chess logic dengan generic content generator.** Chess mempunyai data terstruktur dan workflow operasional sendiri.

2. **Jangan mengikat research engine langsung ke satu platform.** Source adapter harus terpisah agar sistem bisa berkembang.

3. **Jangan menjadikan AI sumber data utama untuk fakta.** AI hanya mengolah data yang telah diberikan oleh research/data engine.

4. **Jangan menjadikan renderer bagian dari AI generator.** Content JSON harus tetap dapat dirender ke image/video dengan template berbeda.

5. **Jangan memasukkan publisher TikTok/Instagram ke core workflow.** Publisher harus menjadi layer terpisah.

6. **Semua output harus mempunyai ID/history.** Ini menjadi dasar deduplication, feedback, analytics, dan future publishing.

7. **Semua workflow harus tetap bisa menghasilkan output manual.** Sistem tidak boleh bergantung pada API publikasi untuk menjadi berguna.

---

# 40. VERSI TARGET PRODUK

## Social Media Assistant v1.0

```text
4 Accounts
+
Smart Router
+
Research Engine
+
OpenRouter AI
+
Media Generator
+
SQLite History
+
Chess Operations
+
Spreadsheet Integration
+
Content Planner
+
Telegram Dashboard
```

## Social Media Assistant v2.0

```text
v1.0
+
Quality Score
+
Feedback Loop
+
Advanced Research
+
Analytics
+
Approval Workflow
```

## Social Media Assistant v3.0

```text
v2.0
+
TikTok Publisher
+
Instagram Publisher
+
Scheduling
+
Auto-posting
```

---

# 41. NEXT IMPLEMENTATION ORDER

Urutan coding yang paling aman:

### Sprint 1

- Accounts v2
- Router
- Telegram menu
- SQLite

### Sprint 2

- Spreadsheet connector/reader
- TCO
- Liga
- Arena

### Sprint 3

- Wedding generator
- MLBB generator
- Fashion generator
- Chess content generator

### Sprint 4

- Research engine 2.0
- Fact-check
- Source tracking
- Deduplication

### Sprint 5

- Media templates
- Carousel
- Poster
- Video variants

### Sprint 6

- Planner
- Feedback
- Quality score
- Daily/weekly briefing

### Sprint 7

- Full integration testing
- Performance
- Security
- Deployment

### Sprint 8

- Review ulang TikTok/Meta API
- Publisher abstraction
- Approval workflow
- Aktifkan publishing hanya setelah requirement platform terpenuhi

---

# 42. STATUS BOARD

Gunakan bagian ini sebagai checklist hidup proyek.

| Modul | Status | Catatan |
|---|---|---|
| Telegram Bot | ✅ Existing | Sudah berjalan |
| OpenRouter | ✅ Existing | Sudah berjalan |
| Generic Content | ✅ Existing | Perlu refactor |
| Wedding | ✅ Existing | Perlu engine khusus |
| MLBB | ✅ Existing | Perlu fact-check |
| Fashion | ✅ Existing | Perlu affiliate mode |
| Chess Account | 🔴 Todo | Menggantikan kuliner |
| Smart Router | 🔴 Todo | Prioritas tinggi |
| SQLite | 🔴 Todo | Prioritas tinggi |
| Spreadsheet | 🔴 Todo | Prioritas tinggi |
| TCO | 🔴 Todo | Prioritas tinggi |
| Liga | 🔴 Todo | Prioritas tinggi |
| Arena Kings | 🔴 Todo | Prioritas tinggi |
| Research 2.0 | 🔴 Todo | Multi-source |
| Media Templates | 🔴 Todo | Per akun |
| Deduplication | 🔴 Todo | Database-based |
| Planner | 🟡 Planned | Setelah core |
| Feedback | 🟡 Planned | Setelah core |
| Analytics | 🟡 Planned | Setelah history matang |
| TikTok Publisher | ⏸ Deferred | Menunggu review/audit |
| Instagram Publisher | ⏸ Deferred | Diaktifkan belakangan |

---

# 43. KESIMPULAN

Fokus utama proyek bukan lagi membangun "bot yang bisa membuat video", tetapi membangun **satu asisten yang memahami empat akun dan dua jenis pekerjaan: content creation dan operational management**.

Arsitektur final harus menjaga tiga lapisan tetap terpisah:

```text
DATA / RESEARCH
       |
       v
INTELLIGENCE / AI
       |
       v
OUTPUT / MEDIA / DELIVERY
```

dan untuk klub catur ditambah:

```text
STRUCTURED EVENT DATA
       |
       v
CHESS OPERATIONS
       |
       v
WA + SOCIAL + POSTER
```

Dengan pemisahan tersebut, ketika integrasi posting otomatis TikTok dan Instagram nantinya siap, yang ditambahkan hanyalah **publisher layer**, bukan membongkar kembali seluruh bot.

Ya, sekarang arah proyeknya jauh lebih jelas. Menurut saya keputusan untuk **memisahkan dulu “content assistant” dari auto-posting** justru bagus, karena bot yang sekarang sudah punya fondasi yang tepat: Telegram → pilih akun → riset → OpenRouter → render media → kirim hasil ke Telegram → posting manual. Alur publikasi TikTok/Instagram memang sedang tidak menjadi bagian alur aktif. 

Yang perlu dilakukan sekarang bukan membuat bot baru dari nol, tetapi **mengembangkan bot yang sekarang menjadi Social Media Assistant dengan beberapa mode kerja**.

## 1. Bentuk bot yang saya sarankan

Jangan membuat bot hanya sebagai:

> “buatkan konten MLBB”

Tetapi jadikan sebagai:

> **Asisten Sosial Media pribadi yang mempunyai 4 akun dan beberapa jenis pekerjaan.**

Strukturnya kira-kira:

```text
                        TELEGRAM BOT
                              │
                              ▼
                    ┌───────────────────┐
                    │     COMMAND       │
                    │ /akun /status     │
                    │ /konten /catur    │
                    │ /tco /liga /arena │
                    └─────────┬─────────┘
                              │
                              ▼
                     ACCOUNT / MODE ROUTER
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
        WEDDING             MLBB            FASHION
      Content Mode       Content Mode      Content Mode
             │                │                │
             └────────────────┼────────────────┘
                              │
                              ▼
                       TREND / RESEARCH
                              │
                              ▼
                         OPENROUTER AI
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
              TEXT          IMAGE          VIDEO
                │             │             │
                └─────────────┼─────────────┘
                              ▼
                           TELEGRAM
                              │
                              ▼
                     POSTING MANUAL
```

Tetapi **akun catur berbeda**. Catur sebaiknya mempunyai modul sendiri karena dia bukan hanya content generator.

```text
                    AKUN KLUB CATUR
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
          TCO WEEKLY      LIGA         ARENA KINGS
            │              │              │
            ▼              ▼              ▼
       Spreadsheet      Data klasemen   Jadwal bulanan
            │              │              │
            ▼              ▼              ▼
        Generator       Generator      Generator
            │              │              │
            └──────────────┼──────────────┘
                           ▼
                     TELEGRAM OUTPUT
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                  WA            SOSMED
```

## 2. Empat akun yang sebaiknya menjadi konfigurasi utama

Saat ini `accounts.json` masih mempunyai `wedding`, `mlbb`, `kuliner`, dan `fashion`. Jadi untuk rancangan baru, **akun `kuliner` diganti menjadi akun klub catur**, bukan menambah akun kelima.  

Saya akan membaginya seperti ini:

| ID        | Akun              | Fungsi utama                         |
| --------- | ----------------- | ------------------------------------ |
| `chess`   | Klub Catur / TCO  | Operasional klub + konten catur      |
| `wedding` | Wedding Organizer | Konten edukasi, inspirasi, trend     |
| `mlbb`    | MLBB / Esports    | Patch, meta, hero, tips, MPL/esports |
| `fashion` | Fashion Affiliate | OOTD, styling, produk, affiliate     |

Profil akun yang sekarang sudah mendukung niche, audience, tone, keyword, seed topic, hashtag, dan larangan konten. Itu sebenarnya fondasi yang sangat bagus untuk sistem ini. Misalnya wedding sudah mempunyai tone “hangat, elegan, penuh detail praktis, tanpa jualan keras”, sedangkan MLBB sudah diatur lebih energik dan bernuansa esports.  

---

# 3. Saya sarankan bot mempunyai 3 “mesin”

Ini bagian terpenting.

### Mesin A — Content Generator

Untuk:

**Wedding**

* ide konten
* trend
* edukasi calon pengantin
* kesalahan umum wedding
* dekorasi
* rundown
* budget planning
* tips persiapan
* konten soft-selling

**MLBB**

* patch terbaru
* perubahan hero
* buff/nerf
* counter hero
* build
* emblem
* meta
* tips & trik
* MPL
* esports
* RRQ/EVOS/tim lain
* draft/pick-ban
* analisis pertandingan

**Fashion**

* OOTD
* mix & match
* gaya kampus
* outfit kerja
* outfit kondangan
* hijab styling
* accessories
* ide outfit murah
* konten affiliate

Untuk ketiga akun tersebut, input bisa sangat sederhana:

```text
buat konten wedding
```

atau

```text
buatkan 3 konten MLBB yang sedang trend
```

atau

```text
cari ide konten fashion untuk affiliate minggu ini
```

---

# 4. Mesin B — Chess Club Assistant

Nah, ini saya justru akan buat lebih spesifik.

Karena klub catur bukan sekadar niche content.

## A. TCO Weekly

Alur yang Anda jelaskan sangat cocok dijadikan automation:

Anda cukup mengisi spreadsheet **sekali untuk satu bulan**:

| No | Judul Turnamen | Tanggal | Hari | Jam   | Durasi | Format | Link          |
| -- | -------------- | ------- | ---- | ----- | ------ | ------ | ------------- |
| 1  | TCO Minggu 1   | 07/10   | Rabu | 20:00 | 60m    | Blitz  | chess.com/... |
| 2  | TCO Minggu 2   | 14/10   | Rabu | 20:00 | 60m    | Rapid  | chess.com/... |
| 3  | TCO Minggu 3   | 21/10   | Rabu | 20:00 | 60m    | Bullet | chess.com/... |
| 4  | TCO Minggu 4   | 28/10   | Rabu | 20:00 | 60m    | Blitz  | chess.com/... |

Kemudian bot tinggal diberi:

```text
/tco minggu ini
```

Bot:

1. membaca spreadsheet
2. mencari event berdasarkan tanggal
3. mengambil data turnamen
4. membuat pengumuman
5. membuat versi WA
6. membuat versi caption sosmed
7. bila diperlukan membuat gambar
8. mengirim semuanya ke Telegram

Jadi Anda tidak perlu lagi mengetik ulang.

### Output misalnya:

```text
♟️ TCO – TIKTOK CHESS ONLINE

Turnamen Internal Mingguan TCO kembali hadir!

📅 Rabu, 14 Oktober 2026
🕗 Mulai: 20.00 WIB
⏱ Durasi: 60 menit
⚡ Format: Blitz

🔗 Link Turnamen:
https://www.chess.com/...

Peserta diharapkan sudah bergabung beberapa menit
sebelum turnamen dimulai.

Selamat bermain dan semoga mendapatkan hasil terbaik! ♟️

#TCO #Chess #ChessOnline
```

Dan bot bisa sekaligus membuat:

> **VERSI WA INTERNAL**

dan

> **VERSI SOSMED**

Jadi Anda tinggal copy-paste.

---

# 5. Mesin C — Liga Perseason

Untuk Liga saya akan membuat format data berbeda.

Misalnya sheet:

| Liga   | Rank | Nama     | Main | Menang | Seri | Kalah | Poin |
| ------ | ---: | -------- | ---: | -----: | ---: | ----: | ---: |
| Liga A |    1 | Player A |    5 |      4 |    1 |     0 |   13 |
| Liga A |    2 | Player B |    5 |      4 |    0 |     1 |   12 |
| Liga A |    3 | Player C |    5 |      3 |    1 |     1 |   10 |

Bot kemudian:

```text
/liga
```

atau:

```text
/liga A
```

akan menghasilkan:

### Berita klasemen

```text
♟️ UPDATE KLASemen TCO – LIGA A

Persaingan Liga A semakin memanas!

Player A masih memimpin klasemen dengan
13 poin dari 5 pertandingan.

Di posisi kedua terdapat Player B dengan
12 poin, sementara Player C berada di posisi ketiga
dengan 10 poin.

Persaingan menuju akhir season masih terbuka...
```

Kemudian:

```text
📊 KLASEMEN LIGA A

1. Player A — 13 Poin
2. Player B — 12 Poin
3. Player C — 10 Poin
...
```

Bisa dibuat satu paket:

**berita + klasemen + pengumuman WA + caption sosmed + image leaderboard.**

---

# 6. Arena Kings justru jangan diperlakukan seperti TCO

Karena problemnya berbeda.

Jadwal sudah diketahui:

> Rabu awal bulan
> sekitar 23.00 WIB

tetapi link resmi baru muncul sekitar 2 jam sebelum event.

Maka saya sarankan dibuat **dua tahap**.

### Tahap 1 — Announcement

Contoh:

```text
♟️ ARENA KINGS TCO

Arena Kings kembali hadir!

📅 Rabu, 7 Oktober 2026
🕚 23.00 WIB

Kegiatan terbuka untuk umum.
Mari ramaikan Arena Kings bersama komunitas TCO!

🔗 Link turnamen akan dibagikan menjelang acara.

#TCO #ArenaKings #Chess
```

Bot juga menghasilkan **poster 1080×1080**.

### Tahap 2 — T-2 Jam

Anda cukup kirim:

```text
/arena link https://www.chess.com/...
```

Bot otomatis membuat:

```text
🚨 ARENA KINGS DIMULAI MALAM INI!

♟️ Arena Kings TCO

🕚 23.00 WIB

🔗 JOIN:
https://www.chess.com/...

Siapkan papanmu.
Sampai jumpa di arena! 🔥♟️
```

Jadi sistem tidak bergantung pada link yang belum tersedia.

---

# 7. Yang menurut saya paling penting: jangan lagi hanya menggunakan “keyword detection”

Bot Anda sekarang memang sudah menggunakan keyword untuk memilih akun, dan keyword terpanjang menjadi prioritas. 

Itu bagus sebagai fallback.

Tetapi kalau proyek ini berkembang, saya lebih merekomendasikan:

```text
/chat biasa
       ↓
intent detector
       ↓
account
       ↓
task
```

Contohnya:

```text
buat konten mlbb tentang counter hayabusa
```

terdeteksi:

```json
{
  "account": "mlbb",
  "task": "content",
  "topic": "counter hayabusa"
}
```

Sedangkan:

```text
tco minggu ini
```

menjadi:

```json
{
  "account": "chess",
  "task": "tco_weekly"
}
```

dan:

```text
buat pengumuman liga B
```

menjadi:

```json
{
  "account": "chess",
  "task": "liga_announcement",
  "league": "B"
}
```

Ini akan membuat bot jauh lebih terasa seperti **asisten**, bukan sekadar generator.

---

# 8. Struktur teknis yang saya sarankan

Struktur project Anda sekarang sudah cukup bersih:

```text
bot.py
accounts.json

utils/
  telegram_bot.py
  accounts.py
  scraper.py
  content_generator.py
  image_maker.py
  video_maker.py
  notifier.py
```

Struktur tersebut bisa berkembang menjadi:

```text
bot.py

config/
    accounts.json
    content_templates.json

utils/
    telegram_bot.py
    router.py
    accounts.py

    research/
        trends.py
        youtube.py
        tiktok.py
        instagram.py
        web_search.py

    ai/
        content_generator.py
        chess_generator.py
        prompt_builder.py

    media/
        image_maker.py
        video_maker.py
        template_engine.py

    chess/
        spreadsheet.py
        tco.py
        liga.py
        arena.py

    history/
        database.py
        content_history.py

    notifier.py
```

---

# 9. Ada satu kelemahan penting dari bot sekarang

Saat ini riset trend Anda sebenarnya masih sangat sederhana: `scraper.py` menggunakan Playwright untuk membuka hasil pencarian YouTube, mengambil judul video, lalu tiga topik teratas diberikan ke AI. Bila gagal, ia memakai `seed_topics`. 

Artinya:

```text
TREND WEDDING
   ↓
YouTube
   ↓
3 judul
   ↓
AI
```

Belum benar-benar:

```text
TREND WEDDING
   ↓
TikTok
Instagram
YouTube
Google/Search
berita/web
   ↓
gabungkan
   ↓
ranking trend
   ↓
AI
```

Untuk target Anda, **research engine harus dinaikkan levelnya**.

Dan saya tidak akan membuat AI langsung “percaya” semua hasil scraping.

Saya akan membuat:

```text
SOURCE
  ↓
RAW DATA
  ↓
FILTER
  ↓
RELEVANCE
  ↓
FRESHNESS
  ↓
AI
```

Sehingga AI mendapat konteks seperti:

```json
{
  "topic": "Hero X sedang populer",
  "source": "...",
  "published": "...",
  "relevance_score": 0.94
}
```

Hal ini sangat penting untuk MLBB dan trend sosial.

---

# 10. Untuk MLBB, ada aturan tambahan

Karena Anda ingin:

> patch terbaru
> hero
> counter
> meta
> MPL
> esports

maka AI sebaiknya tidak boleh mengarang fakta.

Di konfigurasi yang sekarang pun sudah ada larangan untuk tidak mengarang hasil pertandingan dan statistik pemain. 

Saya akan memperluas aturan menjadi:

```text
MLBB FACT CHECK

- patch harus memiliki sumber
- perubahan hero harus berasal dari patch/source
- hasil pertandingan harus berasal dari source
- klasemen harus berasal dari source
- statistik pemain tidak boleh dibuat
- jika data tidak ditemukan → katakan data tidak tersedia
```

Jadi konten MLBB bisa dibedakan menjadi:

**FACTUAL CONTENT**

vs

**OPINION / ANALYSIS**

Ini sangat bagus untuk menjaga akun tetap kredibel.

---

# 11. Wedding juga harus punya mode sendiri

Untuk wedding, AI tidak boleh sekadar mengambil trend lalu “menyalin”.

Misalnya trend:

> warna wedding tertentu sedang populer

Bot mengubahnya menjadi:

```text
TREND
   ↓
IDEA
   ↓
ANGLE
   ↓
CONTENT
```

Contoh:

```text
Trend:
Wedding modern minimalis

Angle 1:
3 kesalahan dekorasi minimalis

Angle 2:
Cara membuat venue kecil terlihat elegan

Angle 3:
Estimasi kebutuhan dekorasi berdasarkan konsep
```

Tetapi tetap mengikuti aturan bahwa bot **tidak boleh mengarang harga paket** atau menjanjikan tanggal/lokasi yang tidak ada. Itu sudah sesuai konfigurasi wedding sekarang. 

---

# 12. Fashion sebaiknya dipersiapkan untuk affiliate

Ini juga sedikit berbeda dari akun konten biasa.

Saya akan membagi:

```text
Fashion
├── Inspiration
├── Styling
├── Problem/Solution
├── Trend
└── Affiliate
```

Contoh:

```text
buat 3 konten fashion affiliate
```

hasil:

### Content 1

**“3 outfit yang kelihatan mahal padahal simple”**

### Content 2

**“1 celana, 4 gaya”**

### Content 3

**“Aksesoris murah yang bikin outfit kelihatan lebih rapi”**

Kemudian output bukan hanya caption, tetapi:

```text
Hook
Script
Scene
Text overlay
CTA
Caption
Hashtag
Product placement
```

Jadi suatu saat ketika Anda memasukkan link affiliate:

```text
buat konten affiliate
produk:
https://...
```

bot tinggal membuat konten berbasis produk tersebut.

---

# 13. Saya sangat menyarankan menambahkan Content Database

Ini adalah salah satu fitur yang **belum ada** di bot sekarang. Dokumentasi Anda juga menyebut belum ada riwayat konten maupun deduplikasi topik. 

Ini akan menjadi penting sekali ketika bot menangani 4 akun.

Minimal simpan:

```text
id
account
content_type
topic
title
created_at
status
source
file_path
caption
```

Contoh:

```text
2026-001
mlbb
hero-counter
Hayabusa
2026-10-05
generated
...
```

Kemudian sebelum membuat konten:

```text
Apakah topic ini pernah dibuat?
       ↓
      YA ──→ cari angle lain
       │
      TIDAK
       ↓
    generate
```

Bahkan kita bisa membuat:

```text
/content history mlbb
```

atau:

```text
/recent mlbb
```

---

# 14. Telegram UI-nya juga bisa dibuat lebih nyaman

Daripada selalu mengetik semuanya, bot nantinya bisa menggunakan tombol.

Misalnya:

```text
🤖 SOCIAL MEDIA ASSISTANT

Pilih akun:

♟️ Klub Catur
💍 Wedding
🎮 MLBB
👕 Fashion
```

Setelah pilih:

```text
♟️ KLUB CATUR

[TCO Mingguan]
[Liga]
[Arena Kings]
[Konten Catur]
```

Untuk Wedding:

```text
💍 WEDDING

[Trend]
[Ide Konten]
[Carousel]
[Reels]
[Caption]
```

MLBB:

```text
🎮 MLBB

[Patch]
[Meta]
[Hero]
[Counter]
[MPL]
[Esports]
[Tips & Trick]
[Trend]
```

Fashion:

```text
👕 FASHION

[Trend]
[OOTD]
[Styling]
[Affiliate]
[Ide Konten]
```

Ini akan membuat pengalaman bot jauh lebih mirip **dashboard mini**, tetapi tetap semuanya berjalan melalui Telegram.

---

# 15. Arsitektur final yang menurut saya paling ideal

Jadi saya tidak akan membangun:

```text
BOT → AI → VIDEO
```

lagi.

Saya akan mengarahkannya menjadi:

```text
                         TELEGRAM
                             │
                             ▼
                       SMART ROUTER
                             │
                 ┌───────────┴───────────┐
                 │                       │
            CONTENT MODE             CHESS MODE
                 │                       │
        ┌────────┼────────┐        ┌─────┼─────┐
        │        │        │        │     │     │
      Wedding   MLBB   Fashion    TCO   Liga  Arena
        │        │        │        │     │     │
        └────────┼────────┘        └─────┼─────┘
                 │                       │
                 ▼                       ▼
              RESEARCH                DATA SOURCE
                 │                       │
       ┌─────────┼─────────┐         Spreadsheet
       │         │         │              │
     Trend     Search    Source           ▼
       │         │         │         DATA NORMALIZER
       └─────────┼─────────┘              │
                 ▼                        ▼
                  AI / OPENROUTER
                         │
               ┌─────────┼─────────┐
               │         │         │
             TEXT      IMAGE      VIDEO
               │         │         │
               └─────────┼─────────┘
                         ▼
                      TELEGRAM
                         │
                ┌────────┼────────┐
                ▼        ▼        ▼
                WA     SOSMED    ARCHIVE
```

Dan satu prinsip penting:

> **AI bukan otak tunggal sistem. AI adalah salah satu komponen di dalam orchestration system.**

Spreadsheet menyediakan fakta.

Research engine menyediakan trend.

Database menyediakan histori.

Router menentukan pekerjaan.

AI membuat tulisan/ide.

Renderer membuat media.

Telegram menjadi interface Anda.

Ini menurut saya akan membuat proyek Anda jauh lebih mudah dikembangkan.

## 16. Urutan pembangunan yang saya sarankan

Saya tidak akan langsung mengerjakan semuanya sekaligus.

**Tahap 1 — Fondasi multi-akun**

* ganti `kuliner` → `chess`
* perbaiki account router
* buat command/button menu
* pisahkan `content mode` dan `chess mode`

**Tahap 2 — Chess Assistant**

* koneksi spreadsheet
* `/tco`
* `/liga`
* `/arena`
* generator pesan WA
* generator caption sosmed
* poster Arena Kings

**Tahap 3 — Content Engine**

* template Wedding
* template MLBB
* template Fashion
* output carousel / image / video
* content history

**Tahap 4 — Research Engine**

* multi-source trend
* source URL
* freshness score
* relevance score
* fact checking untuk MLBB

**Tahap 5 — Intelligence**

* deduplikasi
* rekomendasi ide
* kalender konten
* performa konten
* “minggu ini akun mana yang kurang konten?”

Dengan struktur seperti ini, ketika nanti TikTok dan Meta selesai review, **auto-posting tinggal menjadi layer terakhir**, bukan sesuatu yang harus mengubah keseluruhan sistem. Dokumentasi Anda juga menunjukkan kode TikTok dan Instagram sudah dipisahkan dari alur bot aktif, sehingga pendekatan ini cukup natural untuk proyek yang sekarang. 

Satu catatan teknis: untuk spreadsheet, integrasi langsung dari bot ke sumber spreadsheet akan lebih tepat daripada menjadikan ChatGPT sebagai perantara; pencarian plugin yang tersedia menunjukkan Google Drive/Sheets connector saat ini tidak tersedia untuk akun ini, jadi arsitekturnya sebaiknya tidak bergantung pada itu.

**Langkah paling masuk akal berikutnya adalah mendesain spesifikasi `accounts.json` baru + struktur spreadsheet TCO/Liga/Arena + daftar command Telegram, karena tiga bagian itu akan menjadi kontrak utama sebelum kita mulai mengubah kode.**

Saya juga bisa membuatkan **diagram arsitektur visual lengkap bot ini**, termasuk alur 4 akun, TCO, Liga, Arena Kings, research, OpenRouter, database, dan renderer dalam satu gambar.
