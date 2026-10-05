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

## 3. Memilih Akun dari Chat Bebas

Pengguna tidak memilih akun lewat perintah. Bot menebak dari kata kunci.

`accounts.json` mendefinisikan tiap akun:

```json
{
  "id": "wedding",
  "label": "Wedding Organizer",
  "handle": "@wedding.ko",
  "niche": "organizer pernikahan dan dekorasi pesta di Indonesia",
  "keywords": ["wedding", "pengantin", "bridal", "venue", "dekorasi", ...],
  "source_query": "wedding indonesia",
  "seed_topics": ["Ide dekorasi panggung wedding modern", ...],
  "hashtags": ["#weddingindonesia", "#pengantin", ...],
  "avoid": ["jangan mengarang harga paket", ...]
}
```

`match_account()` menormalkan teks jadi huruf kecil tanpa tanda baca, lalu
mencari kata kunci terpanjang yang cocok. Kata kunci terpanjang menang supaya
"wedding day" lebih dulu dicocokkan daripada "wedding", supaya tidak salah tangkap.

Kalau tidak ada kata kunci yang cocok, bot memakai akun `default_account`.

Empat akun sudah dikonfigurasi: `wedding`, `mlbb`, `kuliner`, `fashion`.
Menambah akun berarti menyalin satu blok di `accounts.json`; tidak ada kode
Python yang perlu disentuh.

`accounts.json` ada di `.gitignore`. File `accounts.example.json` yang
di-commit berisi template dengan isi yang sama.

---

## 4. Membersihkan Permintaan

`_resolve_request()` mengubah "buatkan 1 konten trend wedding" menjadi
 Permintaan inti `wedding`, sambil mengembalikan akun dan kata kunci yang cocok.

Kata yang dibuang: kata kerja (buatkan, bikin, buat, generate, tolong),
penyebut format (konten, video, gambar, foto, post), penanda tren (tren,
terkini, terbaru, hari ini), dan angka di depan.

Kata kunci niche yang dipakai untuk memilih akun digabung kembali ke sisa
kata, jadi "buat konten jajanan pasar" tetap menjadi "jajanan pasar", bukan
hanya "pasar".

Kalau semua kata habis, kata kunci niche dipakai sebagai topik. Jadi
"buatkan 1 konten trend wedding" tetap bermakna.

---

## 5. Validasi Kejelasan

`_is_unclear()` mencegah kuota OpenRouter terbuang untuk pesan yang bukan
permintaan.

Pesan ditolak bila tidak ada kata kunci niche cocok, hanya satu kata, atau
termasuk daftar sapaan yang dikenal (`ya`, `ok`, `sip`, `makasih`, `tes`,
`halo`, `bro`, dan sejenisnya). Bot membalas dengan contoh perintah, bukan
diam saja.

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

Waktu scraping sekitar 60 detik. Ini bagian terlambat dari satu siklus.

---

## 7. Teks AI Terstruktur

`utils/content_generator.py` meminta OpenRouter menjawab JSON murni, bukan
teks bebas, supaya hasilnya bisa langsung dipakai renderer.

```json
{
  "title": "Inspirasi Lagu Jazz Pernikahan",
  "subtitle": "Playlist romantis untuk acara resepsi",
  "points": ["Jazz session...", "Cover Cinta Terakhir...", "...", "..."],
  "caption": "Memilih lagu untuk resepsi memang butuh...",
  "hashtags": ["#weddingorganizer", "#idepernikahan", "..."],
  "cta": "Simpan ide lagu ini sekarang"
}
```

Prompt memuat profil akun lengkap: niche, audiens, nada bicara, topik dari
riset, dan daftar larangan (misal "jangan mengarang harga paket").

Tiga lapis perlindungan menjaga field tetap aman dipakai:

1. `_extract_json()` menerima JSON polos, dibungkus ```json, atau dikelilingi
   prosa model. Diuji dengan keempat format.
2. `_one_line()` meratakan teks jadi satu baris dan memotong di batas kata,
   supaya judul tidak berisi newline atau terlalu panjang untuk frame.
3. `normalize_payload()` mengisi field yang hilang, membersihkan poin kosong,
   menormalkan hashtag agar unik dan berawalan `#`, serta menempelkan hashtag
   ke caption bila model lupa.

Bila model pertama gagal atau tidak mengembalikan JSON, bot mencoba model
gratis berikutnya. Raise exception kalau semua gagal.

Hasil dunia nyata: satu permintaan wedding menghasilkan judul "Inspirasi Lagu
Jazz Pernikahan", 4 poin, caption dengan 6 hashtag.

---

## 8. Render Media

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

Format dipilih di `_requested_format()`; default dari `DEFAULT_CONTENT_FORMAT`.
Batas Telegram 50 MB per video dicek sebelum kirim.

---

## 9. Pengiriman

`utils/notifier.py` mengirim video lalu caption sebagai pesan terpisah.

Caption dikirim terpisah, bukan sebagai caption media, karena Telegram membatasi
caption 1024 karakter sementara caption AI bisa lebih panjang, dan supaya
caption mudah disalin.

Kalau unggah media gagal, bot tetap mengirim caption beserta lokasi file lokal
di `output/`, jadi hasilnya tidak hilang.

---

## 10. Logging

Semua output masuk satu file: `output/content-bot.log`
(diatur lewat `CONTENT_LOG_PATH`).

Rotasi otomatis: 1 MB per berkas, 3 berkas lama disimpan.

Baris log memuat timestamp, level, dan label chat untuk korelasi:

```
2026-10-05 15:12:48,736 INFO    === [BOT PEMBUAT KONTEN AKTIF] ===
2026-10-05 15:12:48,783 INFO    Chat diizinkan: ['8245943494']
```

Modul scraper, AI, dan renderer masih memakai `print()`. `setup_logging()`
mengalihkan `sys.stdout` ke logger lewat kelas `_PrintToLog`, sehingga output
modul-modul itu ikut masuk ke file log yang sama tanpa mengubah kode sumbernya.
Baris kosong dari `print()` kosong otomatis tersaring, jadi log tidak dipenuhi
record kosong. Penulisan log dibungkus try-except; kegagalan log tidak boleh
menghentikan pemrosesan konten.

Contoh satu siklus penuh dari pengujian nyata:

```
[chat 8245943494] pesan masuk: buatkan 1 konten trend wedding
[chat 8245943494] Proses: akun=wedding topik='wedding' keyword='wedding'
[SCRAPER] Membuka https://www.youtube.com/results?search_query=wedding+indonesia+wedding...
[SCRAPER] Percobaan 1: judul video tidak ditemukan, mencoba lagi.
[SCRAPER] Topik: ['Wedding Jazz Session I Lagu Indo Populer', ...]
[chat 8245943494] topik Wedding Organizer: Wedding Jazz Session I Lagu Indo Populer; ...
[AI] Meminta konten ke OpenRouter (model: nvidia/nemotron-3-ultra-550b-a55b:free)...
[AI] Konten dibuat dengan model nvidia/nemotron-3-ultra-550b-a55b:free.
[IMAGE] 3 frame konten dibuat di output
[VIDEO] Video konten dibuat: output\konten-20261005-152322.mp4 (0.32 MB, 12 detik)
[chat 8245943494] Wedding Organizer selesai: video konten-20261005-152322.mp4 (132.6s)
[NOTIFIER] sendVideo berhasil dikirim ke Telegram.
```

Baris "selesai" mencantumkan durasi, jadi kelambatan bisa langsung terlihat dari
log tanpa perlu mengukur sendiri.

---

## 11. Struktur Berkas

```
bot.py                       entry point bot
accounts.json                akun yang dikelola (tidak di-commit)
accounts.example.json        template akun (di-commit)
utils/
  telegram_bot.py            polling, parsing, orkestrasi, logging
  accounts.py                baca dan cari akun
  scraper.py                 riset tren via Playwright
  content_generator.py       caption + teks visual dari OpenRouter
  image_maker.py             render frame dan kartu
  video_maker.py             komposisi video via ffmpeg
  notifier.py                kirim pesan dan media ke Telegram
  tiktok.py                  Content Posting API (tidak dipakai alur ini)
  instagram.py               Meta Graph API (tidak dipakai alur ini)
  ai_generator.py            generator caption lama (dipakai main.py)
main.py                      agen terjadwal sekali jalan (alur lama)
```

`main.py` adalah agen lama berbasis GitHub Actions yang berjalan terjadwal.
Bot `bot.py` adalah alur on-demand yang sekarang dipakai. Keduanya tidak
saling mengganggu: `main.py` tidak memanggil modul bot, dan bot tidak
memanggil `main.py`.

---

## 12. Variabel Lingkungan

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
| `CONTENT_LOG_PATH` | `output/content-bot.log` | Lokasi file log |
| `TELEGRAM_ALLOWED_CHATS` | kosong | Chat tambahan, pisahkan dengan koma |

Bot berhenti sendiri kalau `TELEGRAM_CHAT_ID` kosong atau `accounts.json`
tidak terbaca, dan alasannya dicatat di log.

---

## 13. Menjalankan

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
buatkan 1 konten trend wedding
bikin konten mlbb
buat konten jajanan pasar
ootd ke kampus
buatkan gambar dekorasi akad nikah
/akun
/status
```

---

## 14. Batasan yang Diketahui

- **Waktu satu siklus sekitar 2 menit**, didominasi scraping YouTube dan
  panggilan model gratis.
- **Hanya satu instance bot** boleh berjalan untuk satu token.
- **Bot serialize pemrosesan.** Satu pesan diproses sampai selesai sebelum
  pesan berikutnya, jadi antrean bisa menumpuk.
- **Kualitas konten tergantung hasil scraping.** Kalau YouTube mengembalikan
  video yang kurang relevan, konten bisa menyimpang dari topik yang diminta.
- **Belum ada riwayat konten.** Semua request langsung diproses, tidak ada
  database atau deduplikasi topik.
- **Video 12 detik** hanya cocok untuk konten pendek; tidak ada opsi durasi
  berbeda.

---

## 15. Integrasi Sosmed yang Ditunda

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