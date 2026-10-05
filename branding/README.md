# Brand system

Tampilan setiap akun dibaca dari file di repo ini, bukan dari kode dan bukan dari
jawaban AI. Mengganti warna atau layout cukup mengubah JSON, lalu asetnya dibuat
ulang.

```
branding/<akun>/brand.json   identitas akun: warna, mark, watermark, template
styles/<preset>.json         cara memakainya: kanvas, tipografi, jarak, bayangan
templates/registry.json      katalog template: akun + kategori + format
assets/branding/<akun>/*.png hasil build logo dan watermark (tidak di-commit)
```

## Prinsip

1. Config adalah sumber kebenaran. Renderer tidak menebak warna maupun font.
2. AI hanya menulis teks. Gaya bicara ikut masuk ke prompt, warnanya tidak.
3. Satu akun satu identitas. Template atau watermark akun lain dihentikan oleh
   `branding/validator.py` sebelum file dikirim.
4. Akun tanpa `brand.json` tetap bisa render dengan profil sintetis, tapi hasilnya
   ditandai di QA dan `/style` supaya tidak diam-diam lolos.

## Isi brand.json

| Field | Isi |
|---|---|
| `account` | id akun, harus sama dengan nama folder |
| `label`, `handle` | dipakai di watermark |
| `mark` | bentuk logo: `ring`, `bolt`, `pawn`, `hanger`, `crown` |
| `monogram` | huruf di bawah mark |
| `style_preset` | nama file di `styles/` tanpa ekstensi |
| `identity` | catatan mood visual, tidak dipakai renderer |
| `colors` | hex warna: `background`, `background_alt`, `surface`, `primary`, `accent`, `text`, `muted` |
| `typography` | pilihan font (`bold`/`regular`), skala diambil dari style preset |
| `watermark` | varian warna, posisi, skala, opasitas, safe area |
| `generation_style` | gaya tulis yang dikirim ke prompt AI |
| `templates` | template yang boleh dipakai per format |
| `default_template` | cadangan bila kategori tidak dikenali |

### Varian watermark

- `primary` tanda tangan akun dengan plat berwarna.
- `on_light` tanpa plat, tinta gelap. Dipakai di latar terang.
- `on_dark` tanpa plat, tinta terang. Dipakai di latar gelap.

`utils/media/watermark_engine.py` memilih varian otomatis dari kecerahan latar,
kecuali `watermark.variant` mengunci satu pilihan.

## Format kanvas

| Nama | Ukuran | Dipakai untuk |
|---|---|---|
| `square` | 1080x1080 | feed Instagram, thumbnail |
| `portrait` | 1080x1350 | carousel empat persegi lima |
| `reel` / `story` | 1080x1920 | video vertikal dan story |

`utils/media/layout_engine.py` menyesuaikan jumlah poin otomatis agar tidak
menimpa CTA, dan melaporkannya sebagai catatan kalau ada poin yang dilewati.

## Mengubah tampilan satu akun

1. Ubah `branding/<akun>/brand.json`.
2. Validasi tanpa membuat file:
   `.venv\Scripts\python.exe scripts\build_branding_assets.py --check`
3. Buat ulang aset: `.venv\Scripts\python.exe scripts\build_branding_assets.py <akun>`
4. Cek di Telegram: `/preview <akun> image` atau `/style <akun>`.

Langkah 2 penting: warna salah ketik atau template milik akun lain akan tertangkap
sebelum ada file yang perlu dibuang.

## Menambah template

Tambah entri baru di `templates/registry.json` dengan `id` unik, `account`,
`content_type`, dan `layout` (`standard` atau `table`). Lalu daftarkan id-nya di
`templates` pada `brand.json` akun tersebut. Rantai fallback menutupi kategori
yang belum punya template khusus, jadi menambah template tidak wajib untuk mulai.

Ganti gaya tampilan lain di `styles/<preset>.json`:

| Field | Nilai yang dipahami |
|---|---|
| `canvas.background` | `solid`, `gradient_vertical`, `gradient_diagonal`, `band_top` |
| `canvas.accent_bar` | `thin`, `medium`, `block` |
| `canvas.panel` | `soft`, `solid`, `outline` |
| `canvas.rule` | `hairline`, `medium`, `thick` |
| `canvas.texture` | `none`, `grid`, `board`, `diagonal_hatch` |
| `point_marker` | `dash`, `square`, `dot`, `rank` |

## Test

`.venv\Scripts\python.exe -m pytest tests\test_branding.py -q`

Test ini memeriksa hal yang harus dijaga: setiap akun berbeda, template milik
sendiri, watermark menempel dan di dalam kanvas, serta teks yang terpotong
selalu dilaporkan.

Empat kartu juga dibandingkan langsung lewat selisih piksel, karena outfit visual
yang mirip adalah kegagalan yang tidak terlihat dari log.