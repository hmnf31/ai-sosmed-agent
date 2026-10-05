# Alur Proyek: Bot Telegram + Pembuat Konten

Dokumen ini menjelaskan seluruh alur proyek yang aktif: bot Telegram yang
membuat konten sesuai permintaan, lalu mengirimkannya untuk diunggah manual.

Integrasi Instagram dan TikTok tidak termasuk alur aktif. Kode dan konfigurasi
mereka masih ada di repository, tetapi tidak dipanggil oleh alur yang
dijelaskan di sini.

---

## 1. Ringkasan Alur

```
Pengguna chat ke bot
        |
        v
[1] Telegram long polling  -> utils/telegram_bot.py run()
        |
        v
[2] Deteksi perintah      -> /start /akun /status
        |  (bukan perintah, lanjut)
        v
[3] Tentukan akun+niche   -> utils/accounts.py match_account()
        |
        v
[4] Bersihkan permintaan  -> _resolve_request()
        |
        v
[5] Validasi kejelasan     -> _is_unclear()  (tolak "ya", "tes", dll)
        |
        v
[6] Riset topik terpanas  -> utils/scraper.py get_topic_trends()   (Playwright/YouTube)
        |
        v
[7] Teks AI terstruktur   -> utils/content_generator.py generate_content()  (OpenRouter)
        |
        v
[8] Render media          -> utils/video_maker.py  (ffmpeg)
        |                     utils/image_maker.py (Pillow)
        v
[9] Kirim ke Telegram     -> utils/notifier.py send_telegram_media()
        |
        v
[10] Ungah manual ke TikTok/IG oleh pengguna
```

Tidak ada langkah publikasi otomatis. Ini keputusan sadar: app TikTok masih
menunggu proses audit, dan dengan alur manual konten tetap bisa terbit sekarang.

---

## 2. Pemicu: Long Polling

`utils/telegram_bot.py` berjalan sebagai proses permanen, bukan satu kali jalan.

```python
offset = None
while True:
    updates = get_updates(offset=offset, timeout=30, allowed_updates=["message"])
    for update in updates:
        offset = update["update_id"] + 1   # ack: jangan diproses ulang
        handle_message(chat_id, text)
```

Cara kerja offset: setiap pesan yang diproses membuat `offset` naik ke
`update_id + 1`, jadi Telegram berhenti mengirim pesan yang sama lagi. Kalau
proses mati dan hidup lagi, pesan yang belum sempat diproses masih tertahan di
antrean Telegram dan akan diambil saat bot start ulang.

Long polling dipilih karena tidak butuh port terbuka, tidak butuh webhook, dan
cukup untuk satu pengguna. Batasnya: hanya satu instance bot yang boleh berjalan
sekaligus untuk satu token, karena dua proses akan saling mengambil pesan.

Filter akses ada di `authorized_chat()`: hanya `TELEGRAM_CHAT_ID` dan
`TELEGRAM_ALLOWED_CHATS` yang dilayani. Chat lain diabaikan dan dicatat ke log.

---

## 3. Router: Chat Bebas Menjadi Intent

Pengguna tidak memilih akun lewat perintah. `utils/router.py` mengubah chat
bebas menjadi dict intent: `account`, `task`, `category`, `topic`, `format`,
`quantity`, `platform`, `period`, `league`, `url`.

```text
"buatkan 3 konten mlbb tentang counter hayabusa"
        ↓
{"account": "mlbb", "task": "content", "topic": "counter hayabusa",
 "quantity": 3}
```

Task yang dikenali:

| Task | Contoh perintah |
| --- | --- |
| `content` | `buatkan 3 konten mlbb` |
| `tco_weekly` | `tco minggu ini` |
| `league_standing` | `/liga A`, `liga b klasemen` |
| `arena_schedule` | `arena kings minggu ini`, `/arena link <url>` |
| `history` | `/riwayat mlbb` |
| `plan` | `/plan`, `buatkan plan konten mingguan` |

Kata kunci akun jadi fallback, bukan penentu utama. Urutan pemeriksaan task:
perintah eksplisit (`/liga`), pola operasional (`tco`, `liga`, `arena`), kata
kerja `buat`, lalu default `content`. Karena itu "buat pengumuman liga B" dibaca
sebagai pembuatan konten, bukan pembacaan klasemen.

Penentuan topik membuang kata kerja, penanda format, dan penghubung, lalu
membuang kata kunci akun hanya bila sisa topik masih punya isi. "counter
hayabusa" tetap utuh, bukan menjadi "hayabusa".

---

## 4. Akun: Schema v2

`accounts.json` mendefinisikan tiap akun:

```json
{
  "id": "wedding",
  "label": "Wedding Organizer",
  "handle": "@wedding.ko",
  "emoji": "💍",
  "mode": ["content"],
  "niche": "organizer pernikahan dan dekorasi pesta di Indonesia",
  "audience": "calon pengantin usia 25-40 di Indonesia",
  "tone": "hangat, elegan, penuh detail praktis",
  "keywords": ["wedding", "pengantin", "bridal", "venue", "dekorasi", ...],
  "seed_topics": ["Ide dekorasi panggung wedding modern", ...],
  "hashtags": ["#weddingindonesia", "#pengantin", ...],
  "content_categories": ["edukasi", "Checklist", "trend", ...],
  "fact_check_rules": ["jangan mengarang harga paket", ...],
  "avoid": ["jangan mengarang harga paket", ...],
  "default_templates": ["wedding_trend", "wedding_education"]
}
```

Field baru `mode` membedakan cara kerja sebuah akun:

| Mode | Akun | Arti |
| --- | --- | --- |
| `content` | semua | Produksi konten dari riset |
| `club_operations` | `chess` | Data dari spreadsheet, bukan riset |
| `affiliate` | `fashion` | Mode produk affiliate |

`fact_check_rules` dikirim ke prompt sebagai aturan wajib, terpisah dari
`avoid` yang bersifat perilaku umum.

Empat akun dikonfigurasi: `chess`, `wedding`, `mlbb`, `fashion`.
`accounts_mod.has_mode()` dipakai bot untuk memilih jalur: akun
`club_operations` memakai spreadsheet, akun `content` memakai riset tren.

`accounts.json` ada di `.gitignore`. File `accounts.example.json` yang
di-commit berisi template dengan isi yang sama.

Field baru bersifat opsional: file schema v1 tanpa `mode`, `fact_check_rules`,
atau `content_categories` tetap bisa dibaca. `utils/accounts.py` mengisi nilai
default supaya pemanggil tidak perlu memeriksa keberadaan kunci.

---

## 5. Validasi Kejelasan

`_is_unclear()` mencegah kuota OpenRouter terbuang untuk pesan yang bukan
permintaan.

Pesan ditolak bila tidak ada kata kunci niche cocok, hanya satu kata, atau
termasuk daftar sapaan yang dikenal (`ya`, `ok`, `sip`, `makasih`, `tes`,
`halo`, `bro`, dan sejenisnya). Bot membalas contoh perintah dan tombol menu,
bukan diam saja.

Ini masalah nyata yang ditemukan saat pengujian: pesan "ya" dan "tes" sempat
dikirim ke AI dan menghabiskan kuota. Sekarang teks pendek seperti itu sudah
masuk daftar penolakan.

---

## 6. Riset Tren per Niche

`utils/scraper.py get_topic_trends()` memakai Playwright membuka hasil
pencarian YouTube dengan filter upload terbaru, lalu mengambil judul video.

Query dibentuk dari `source_query` akun ditambah permintaan pengguna:
`"wedding indonesia" + "wedding"`.

Judul dibersihkan dari emoji, badge "LIVE", dan karakter yang tidak bisa
dirender font, lalu diurutkan berdasarkan relevansi terhadap `keywords` akun.
Tiga teratas dipakai sebagai konteks untuk AI.

Kalau YouTube gagal dua kali, bot jatuh ke `seed_topics` dari akun supaya
permintaan tidak gagal total hanya karena jaringan.

Waktu scraping sekitar 60 detik. Ini bagian terlambat dari satu siklus, dan
sumbernya masih dominan YouTube.

---

## 7. Mesin per Akun

`utils/engines/` memberi tiap akun aturan main sendiri. Modul ini menyusun
brief untuk AI; angka dan fakta tetap berasal dari sumber.

| Akun | Aturan khusus |
| --- | --- |
| `wedding` | Tren diubah jadi ide; dilarang mengarang harga paket |
| `mlbb` | Fact-check ketat: patch, buff/nerf, hasil, dan statistik wajib bersumber |
| `fashion` | Larangan nama brand/harga karangan; mode affiliate fokus masalah nyata |
| `chess` | Larangan hasil, skor, dan Elo karangan |

Tugas tiap engine:

1. `detect_category()` membaca kategori dari teks: `patch`, `counter`, `mpl`
   untuk MLBB; `ootd`, `styling`, `affiliate` untuk fashion.
2. `build_brief()` mengembalikan `request`, `topics`, `category`,
   `angle_hint`, `avoid_topics`, dan `extra_rules`.
3. `extra_instructions()` menambah arahan khusus kategori.

`avoid_topics` diisi dari riwayat supaya model tidak mengulang konten lama.

---

## 8. Teks AI Terstruktur

`utils/content_generator.py` meminta OpenRouter menjawab JSON murni, bukan
teks bebas, supaya hasilnya bisa langsung dipakai renderer.

```json
{
  "title": "Inspirasi Lagu Jazz Pernikahan",
  "subtitle": "Playlist romantis untuk acara resepsi",
  "points": ["Jazz session...", "Cover Cinta Terakhir...", "...", "..."],
  "caption": "Memilih lagu untuk resepsi memang butuh...",
  "hashtags": ["#weddingorganizer", "#idepernikahan", "..."],
  "cta": "Simpan ide lagu ini sekarang",
  "angle": "angle yang dipakai untuk konten ini",
  "source_url": "https://sumber-artikel..."
}
```

Prompt memuat profil akun lengkap: niche, audiens, nada bicara, kategori,
topik dari riset, topik lama yang harus dihindari, dan aturan fact-check akun
(diambil dari `fact_check_rules` plus `avoid`).

Lima lapis perlindungan menjaga field tetap aman dipakai:

1. `_extract_json()` menerima JSON polos, dibungkus ```json, atau dikelilingi
   prosa model. Diuji dengan keempat format.
2. `_one_line()` meratakan teks jadi satu baris dan memotong di batas kata,
   supaya judul tidak berisi newline atau terlalu panjang untuk frame.
3. `normalize_payload()` mengisi field yang hilang, membersihkan poin kosong,
   menormalkan hashtag agar unik dan berawalan `#`, serta menempelkan hashtag
   ke caption bila model lupa.
4. `_clean_source_url()` mengambil URL polos dari jawaban model. Model kadang
   membungkus URL sebagai `[teks](url)`; bentuk itu dibuang supaya URL yang
   dikirim ke Telegram bisa langsung disalin dan diklik.
5. `fact_check_rules` masuk sebagai aturan wajib, sehingga MLBB dan catur punya
   satu tempat untuk melarang angka atau hasil pertandingan karangan.

Bila model pertama gagal atau tidak mengembalikan JSON, bot mencoba model
gratis berikutnya. Raise exception kalau semua gagal.

---

## 9. Render Media

**Video** (`utils/video_maker.py`) adalah jalur default.

Tiga frame vertikal 1080x1920 dirender dengan Pillow:

| Frame | Isi |
| --- | --- |
| 1 | Label "TREN TERKINI", judul besar, subtitle, tanggal |
| 2 | "POIN PENTING" + 4 poin bernomor |
| 3 | "GILIRANMU" + ajakan bertindak + handle akun |

Lalu ffmpeg menggabungkannya dengan `zoompan` halus, `fade` di awal dan akhir
setiap segmen, 4 detik per frame. Hasil akhir: mp4 H.264 High, yuv420p,
25 fps, 1080x1920, 12 detik, sekitar 0,3 MB, AAC stereo dengan `+faststart`.

Parameter ini memenuhi syarat unggah TikTok: minimum 23 fps (dipakai 25),
ukuran minimum 360 piklus kedua sisi (dipakai 1080), H.264, yuv420p.

**Gambar** (`utils/image_maker.py`) untuk permintaan yang menyebut "gambar",
"foto", atau "ig". Kartu 1080x1080 dengan judul, subtitle, 3 poin, dan CTA.

Format dipilih dari `intent["format"]`, lalu default `DEFAULT_CONTENT_FORMAT`.
Batas Telegram 50 MB per video dicek sebelum kirim.

---

## 10. Histori dan Deduplikasi

`utils/history.py` menyimpan setiap konten di SQLite
(`output/content-history.db`, diatur lewat `CONTENT_DB_PATH`).

Tiga tabel: `content_history` (isi konten), `topic_usage` (topik per akun),
dan `request_log` (percakapan untuk observability).

Setiap konten mendapat ID berurutan per tahun, contoh `2026-014`, dan dicatat
sebelum render. Kalau render gagal, histori tetap ada sehingga hasilnya tahu
topik mana yang sudah dicoba.

`topic_key()` menormalkan topik: huruf kecil, tanpa tanda baca, tanpa kata
biasa seperti "yang" dan "terbaru`. "Counter Hayabusa!" dan "counter hayabusa"
menjadi key yang sama.

Sebelum membuat konten, bot mencari topik yang mirip:

- `is_duplicate()` true bila topik persis sudah pernah dipakai untuk akun itu.
- `duplicate_candidates()` mencari topik dengan awalan kata pertama yang sama,
  lalu mengurutkan dari jumlah kata yang sama. "Counter Hiu" akan menemukan
  "Counter Hayabusa".

Duplikasi hanya memberi peringatan, tidak pernah memblokir permintaan, dan
kegagalan baca database tidak menghentikan produksi konten.

Status konten mengikuti alur: `generated` → `approved` → `published` →
`archived`, dengan `rejected` bisa kembali ke `generated`. Transisi yang tidak
diizinkan ditolak dengan pesan jelas.

---

## 11. Menu Tombol

`utils/keyboards.py` menyediakan tombol inline supaya pengguna tidak perlu
mengetik panjang-panjang.

```
🤖 SOCIAL MEDIA ASSISTANT

Pilih akun:
♟️ Klub Catur / TCO
💍 Wedding Organizer
🎮 Esports MLBB
👕 Fashion Affiliate
```

Menu tiap akun punya tombol task: catur punya TCO/Liga/Arena, MLBB punya
Patch/Meta/Hero/Counter/MPL/Esports, fashion punya OOTD/Styling/Affiliate.

Tombol tidak punya logika sendiri. `keyboards.task_request()` menyusun teks
permintaan dari tombol, lalu teks itu diproses router dan `build_package()`
seperti pesan biasa. Satu jalur kebenaran, bukan dua.

`handle_callback()` menangani `menu:back`, `menu:account:<id>`,
`menu:task:<id>:<task>:<arg>`, dan `menu:history:<id>`. Polling kini meminta
`callback_query` selain `message`.

---

## 12. Klub Catur dari Spreadsheet

Akun `chess` punya `mode: ["club_operations"]`, jadi TCO, Liga, dan Arena
Kings memakai data spreadsheet, bukan riset tren. Angka tidak pernah datang dari
model.

`utils/chess/spreadsheet.py` membaca dari dua sumber:

| Sumber | Cara |
| --- | --- |
| Google Sheets REST API | `SHEET_CREDENTIALS_JSON` berisi JSON service account |
| CSV lokal | `SHEET_CSV_PATH` |

Satu CSV boleh memuat beberapa tabel berurutan; baris header dicari per tabel,
dan pembacaan berhenti saat baris header tabel berikutnya muncul.

Kolom yang dikenali menerima beberapa nama: `Nama`/`Player`, `Poin`/`Points`,
`Menang`/`Win`, `Tanggal`/`Date`, `Waktu`/`Jam`. Tanggal diterima dalam format
`2026-10-14`, `14/10/2026`, `14-10-2026`, dan `2026/10/14`.

Tiga modul hasil turunannya:

- `utils/chess/tco.py` membangun pesan WhatsApp internal, caption sosmed, dan
  baris poster. Bila jadwal belum ada, bot mengatakannya terus terang.
- `utils/chess/liga.py` membangun berita klasemen, tabel yang bisa disalin, dan
  baris leaderboard.
- `utils/chess/arena.py` membangun dua tahap. Tahap 1 pengumuman tanpa link;
  tahap 2 setelah link dikirim lewat `/arena link <url>`. Link tidak pernah
  dikarang; tahap 1 menyatakan link akan dibagikan menjelang acara.

Contoh keluaran TCO:

```text
♟️ TCO - TIKTOK CHESS ONLINE

Turnamen Internal Mingguan TCO kembali hadir!

📅 Rabu, 14 Oktober 2026
🕗 Mulai: 20.00 WIB
⏱ Format: Blitz

🔗 Link Turnamen:
https://www.chess.com/...
```

Link ditulis sebagai URL polos, bukan markdown, supaya bisa langsung disalin.

Semua task operasional dicatat dengan `status` `ok` atau `no_data`, sehingga
`/status` membedakan konten yang sukses dari permintaan yang datanya memang
belum ada.

---

## 13. Pengiriman

`utils/notifier.py` mengirim video lalu caption sebagai pesan terpisah.

Caption dikirim terpisah, bukan sebagai caption media, karena Telegram membatasi
caption 1024 karakter sementara caption AI bisa lebih panjang, dan supaya
caption mudah disalin.

Header pengiriman memuat ID konten, topik, sudut pandang, dan sumber sebagai URL
polos. Kalau unggah media gagal, bot tetap mengirim caption beserta lokasi file
lokal di `output/`, jadi hasilnya tidak hilang.

---

## 14. Logging dan Observability

Semua output masuk satu file: `output/content-bot.log`
(diatur lewat `CONTENT_LOG_PATH`).

Rotasi otomatis: 1 MB per berkas, 3 berkas lama disimpan.

Baris log memuat timestamp, level, label chat, dan request ID:

```
2026-10-05 16:45:57,770 INFO    [chat <id>] intent task=tco_weekly account=chess
```

Modul scraper, AI, dan renderer masih memakai `print()`. `setup_logging()`
mengalihkan `sys.stdout` ke logger lewat kelas `_PrintToLog`, sehingga output
modul-modul itu ikut masuk ke file log yang sama tanpa mengubah kode sumbernya.
Baris kosong dari `print()` kosong otomatis tersaring, jadi log tidak dipenuhi
record kosong. Penulisan log dibungkus try-except; kegagalan log tidak boleh
menghentikan pemrosesan konten.

Setiap request dicatat di tabel `request_log` berisi `request_id`, akun, task,
status, dan durasi dalam milidetik. `status` bisa `ok`, `error`, `no_data`, atau
`config_error`. `/status` menampilkan jumlah konten per akun selama 7 hari dan
berapa request terakhir yang bermasalah.

Contoh satu siklus penuh dari pengujian nyata:

```
[chat <id>] pesan masuk: buatkan 1 konten trend wedding
[chat <id>] intent task=content account=wedding topic='wedding'
[SCRAPER] Membuka https://www.youtube.com/results?search_query=wedding+indonesia+wedding...
[SCRAPER] Topik: ['Wedding Jazz Session I Lagu Indo Populer', ...]
[chat <id>] topik Wedding Organizer: Wedding Jazz Session I Lagu Indo Populer; ...
[AI] Meminta konten ke OpenRouter (model: nvidia/nemotron-3-ultra-550b-a55b:free)...
[IMAGE] 3 frame konten dibuat di output
[VIDEO] Video konten dibuat: output\konten-20261005-152322.mp4 (0.32 MB, 12 detik)
[chat <id>] Wedding Organizer selesai: 2026-001 video konten-20261005-152322.mp4 (132.6s)
[NOTIFIER] sendVideo berhasil dikirim ke Telegram.
```

Baris "selesai" memuat ID konten dan durasi, jadi kelambatan bisa langsung
terlihat dari log tanpa perlu mengukur sendiri.

---

## 15. Struktur Berkas

```
bot.py                       entry point bot
accounts.json                akun yang dikelola (tidak di-commit)
accounts.example.json        template akun (di-commit)
utils/
  telegram_bot.py            polling, orkestrasi, tombol, logging
  router.py                  chat bebas -> intent terstruktur
  accounts.py                baca, cari, dan validasi akun
  history.py                 histori konten, dedup, request log
  keyboards.py               tombol inline dan teks permintaan
  engines/                   aturan khusus per akun
  chess/
    spreadsheet.py           baca Google Sheets atau CSV
    tco.py                   pengumuman TCO mingguan
    liga.py                  berita dan tabel klasemen
    arena.py                 dua tahap Arena Kings
  scraper.py                 riset tren via Playwright
  content_generator.py       caption + teks visual dari OpenRouter
  image_maker.py             render frame dan kartu
  video_maker.py             komposisi video via ffmpeg
  notifier.py                kirim pesan, tombol, dan media
  tiktok.py                  Content Posting API (tidak dipakai alur ini)
  instagram.py               Meta Graph API (tidak dipakai alur ini)
  ai_generator.py            generator caption lama (dipakai main.py)
tests/                       test suite pytest
main.py                      agen terjadwal sekali jalan (alur lama)
```

`main.py` adalah agen lama berbasis GitHub Actions yang berjalan terjadwal.
Bot `bot.py` adalah alur on-demand yang sekarang dipakai. Keduanya tidak
saling mengganggu: `main.py` tidak memanggil modul bot, dan bot tidak
memanggil `main.py`.

Jalankan test dengan `.venv\Scripts\python.exe -m pytest -q`. Test memakai
database sendiri di folder temporer, tidak menyentuh `output/`, dan tidak
memanggil jaringan: riset, AI, renderer, dan Telegram dipalsukan lewat fixture.

---

## 16. Variabel Lingkungan

Wajib:

| Variabel | Keterangan |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Token dari @BotFather |
| `TELEGRAM_CHAT_ID` | Chat yang boleh memakai bot |
| `OPENROUTER_API_KEY` | Kunci API OpenRouter |

Opsional:

| Variabel | Default | Keterangan |
| --- | --- | --- |
| `ACCOUNTS_FILE` | `accounts.json` | Lokasi file akun |
| `DEFAULT_CONTENT_FORMAT` | `video` | Default saat format tidak disebut |
| `CONTENT_MAX_TOPICS` | `3` | Berapa topik dari riset |
| `CONTENT_DB_PATH` | `output/content-history.db` | Database histori konten |
| `CONTENT_LOG_PATH` | `output/content-bot.log` | Lokasi file log |
| `TELEGRAM_ALLOWED_CHATS` | kosong | Chat tambahan, pisahkan dengan koma |
| `SHEET_CREDENTIALS_JSON` | kosong | JSON service account Google Sheets |
| `SHEET_CSV_PATH` | kosong | CSV lokal sebagai pengganti Sheets API |

Bot berhenti sendiri kalau `TELEGRAM_CHAT_ID` kosong atau `accounts.json`
tidak terbaca, dan alasannya dicatat di log.

Task TCO, Liga, dan Arena Kings butuh salah satu dari `SHEET_CREDENTIALS_JSON`
atau `SHEET_CSV_PATH`. Tanpa keduanya, bot tetap jalan dan menyatakan data
belum tersedia; tidak ada angka yang dikarang.

---

## 17. Menjalankan

```bash
# sekali saja
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium

# setiap kali dipakai
.venv\Scripts\python.exe bot.py
```

ffmpeg wajib ada untuk render video. Deteksi otomatis lewat PATH, `FFMPEG_PATH`,
lokasi WinGet, atau `shutil.which`.

Bot berjalan permanen sampai proses dihentikan. Kalau dijalankan lewat Kilo,
bot ikut berhenti saat Kilo ditutup. Untuk berjalan terus-menerus, jalankan
`python bot.py` di terminal terpisah atau lewat Task Scheduler.

Contoh perintah di Telegram:

```
buatkan 3 konten mlbb tentang counter hayabusa
bikin 1 konten tren wedding
ootd ke kampus
buatkan gambar dekorasi akad nikah
tco minggu ini
/liga A
arena kings minggu ini
/arena link https://www.chess.com/...
/riwayat mlbb
/menu
/akun
/status
```

`/menu` membuka tombol, sehingga sebagian besar perintah tidak perlu diketik.

---

## 18. Batasan yang Diketahui

- **Waktu satu siklus sekitar 2 menit**, didominasi scraping YouTube dan
  panggilan model gratis.
- **Hanya satu instance bot** boleh berjalan untuk satu token.
- **Bot serialize pemrosesan.** Satu pesan diproses sampai selesai sebelum
  pesan berikutnya, jadi antrean bisa menumpuk.
- **Kualitas konten tergantung hasil scraping.** Sumber riset masih dominan
  YouTube, jadi kalau hasilnya kurang relevan, konten bisa menyimpang dari topik
  yang diminta. Riset multi-sumber belum ada.
- **Task `plan` belum punya pembuat sendiri.** Bot menjelaskannya dan memproses
  permintaan sebagai daftar ide, bukan kalender mingguan.
- **Deduplikasi hanya memberi peringatan.** Topik yang sama tetap bisa dibuat
  ulang bila memang diminta.
- **Video 12 detik** hanya cocok untuk konten pendek; tidak ada opsi durasi
  berbeda.
- **Generate gambar AI dan renderer opsional belum dipasang.** Renderer yang
  dipakai sekarang FFmpeg dan Pillow.

---

## 19. Integrasi Sosmed yang Ditunda

Kode TikTok (`utils/tiktok.py`) sudah berfungsi untuk OAuth, refresh token,
`user/info`, dan unggah chunked. Yang belum bisa dipakai adalah init unggah
karena app ditolak dengan `unaudited_client_can_only_post_to_private_accounts`.
TikTok menolak init unggah untuk klien yang belum diaudit pada semua privacy
level dan kedua mode (`DIRECT_POST` dan `MEDIA_UPLOAD`), termasuk `SELF_ONLY`.

Konsekuensinya: verifikasi domain tidak menyelesaikan masalah. Verifikasi itu
hanya berlaku untuk `PULL_FROM_URL`, sedangkan kode memakai `FILE_UPLOAD` yang
tidak butuh verifikasi.

Kode TikTok siap dipakai begitu audit selesai; tidak perlu perubahan kode, hanya
set `TIKTOK_ENABLED=true`.

`utils/instagram.py` sudah memanggil Meta Graph API dengan benar, tetapi
`main.py` masih mengarahkan `sample_image_url` ke picsum.photos sebagai URL
contoh. Jadi jalur Instagram belum berfungsi untuk posting sungguhan.