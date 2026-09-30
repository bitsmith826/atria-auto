# Atria Auto

Otomasi pembuatan API Key Atria + pendaftaran ke 9Router, pakai Camoufox (browser anti-detect berbasis Firefox).

## Cara pakai

1. **Download / salin** folder ini ke komputer Windows.
2. Buka **`.env`**, sesuaikan kalau perlu (lihat penjelasan di bawah).
   Default-nya sudah siap untuk 9Router lokal standar.
3. Buka **`empas.txt`**, isi daftar akun. Format satu per baris:
   ```
   email|password
   ```
   Contoh:
   ```
   contoh1@gmail.com|sandi123
   contoh2@gmail.com|sandi456
   ```
   Baris diawali `#` tidak diproses (dianggap catatan).
4. **Klik dua kali `run.bat`**. Selesai.

`run.bat` akan otomatis:
- cek Python; kalau tidak ada → download dan install Python
- install library (`camoufox`, `playwright`) — sekali saja
- download browser Camoufox (~500 MB) — sekali saja
- menjalankan otomasi untuk tiap akun di `empas.txt`

Browser akan terbuka dan terlihat bekerja. Biarkan saja sampai selesai.

## Pilih mode

Saat jalan, akan muncul pertanyaan:

```
PILIH MODE
──────────────────────────────────────────────────
 1. Buat API Key saja
    Login Atria -> buat key -> simpan ke result.txt

 2. Full - sampai terdaftar di 9Router
    Login Atria -> buat key -> simpan -> daftar ke 9Router

 3. Input keys.txt ke 9Router saja
    Untuk yang sudah punya API key, tinggal daftar ke 9Router
──────────────────────────────────────────────────
Pilih (1/2/3) [default 2]:
```

- **Ketik 1** → login Atria, buat API key, simpan ke `result.txt`. Tidak menyentuh 9Router.
- **Ketik 2** (atau Enter) → lanjut daftarkan key ke 9Router sampai valid. Kalau key ditolak (*Invalid API key*), otomatis buat key baru, maksimal 5 kali per akun.
- **Ketik 3** → **untuk orang yang sudah punya API key.** Tidak perlu `empas.txt` dan tidak perlu login Atria. Cukup buat file `keys.txt` berisi daftar API key:

  ```
  nama|apikey
  ```
  Contoh:
  ```
  budi@gmail.com|atr_xQRvOIV7T0uZmegg2oIid1rVKOwz20mH
  sari@gmail.com|atr_f5eyeA9fUKZNcYQQBbaU9UeUuk5A5rr6
  ```
  `nama` = email, dipakai sebagai nama koneksi di 9Router. Setiap nama dicek dulu: kalau sudah ada di 9Router → **dilewati**, kalau belum → didaftarkan (Check → Save).

  File `keys.txt` **hanya dibutuhkan kalau pilih mode 3**. Kalau belum ada saat dipilih, script akan kasih tahu cara buatnya.

## Hasil

Tersimpan di **`result.txt`**, format:
```
email|password|apikey
```

Ditulis langsung setiap kali satu API key berhasil dibuat — jika skrip dihentikan di tengah jalan, akun yang sudah selesai tetap tersimpan.

## Resume otomatis

Saat dijalankan lagi, akun yang emailnya sudah ada di `result.txt` **akan dilewati**. Jadi cukup klik `run.bat` lagi untuk melanjutkan sisanya.

## Yang dilakukan per akun

**Mode 1 (Buat API Key saja):**
1. Buka Atria console → *Create account* → *Continue with Google*
2. Isi email + password, klik *Berikutnya*
3. Klik tombol konfirmasi Google (*Saya mengerti* / *Lanjutkan*)
4. Buka menu *API Keys* → *Create key* → ambil key baru
5. Simpan ke `result.txt`

**Mode 2 (Full):** semua di atas, lalu:

6. Buka 9Router → login → *Providers* → *Atria Dawn* → isi *Name* (email) + *API Key*
7. Klik **Check**. Jika key ditolak (*Invalid API key*), buat key baru di Atria dan coba lagi, maksimal 5 kali per akun.

**Mode 3 (Input keys.txt ke 9Router saja):** tidak perlu login Atria, langsung:

1. Buka 9Router → login → halaman *Providers*
2. Cek nama: kalau sudah ada → **dilewati**, kalau belum → daftarkan
3. Isi *Name* + *API Key* → klik **Check** → klik **Save**
4. Ulangi untuk setiap baris di `keys.txt`

## File penting

| File | Kegunaan |
|---|---|
| `run.bat` | **klik dua kali untuk mulai** |
| `.env` | **konfigurasi** — URL, password, headless, dll (lihat bawah) |
| `empas.txt` | daftar akun (mode 1 & 2) |
| `keys.txt` | daftar API key (mode 3, opsional) |
| `result.txt` | hasil (email\|password\|apikey) |
| `main.py`, `atria.py`, `router9.py`, `tampilan.py` | kode program |
| `requirements.txt` | daftar library Python |

## Konfigurasi (file `.env`)

Semua pengaturan ada di satu file `.env`. Isi sekali, tidak perlu buka kode.

```
ROUTER_URL=http://localhost:20128     # URL 9Router + port
ROUTER_PASSWORD=***                 # password login 9Router
HEADLESS=false                         # false = browser tampil, true = tersembunyi
MAX_COBA_KEY=5                          # ulang buat key kalau ditolak (maks 5x)
JEDA_ANTAR_AKUN=5                       # jeda detik antar akun (0 = tanpa jeda)
```

Kalau file `.env` tidak ada atau isinya kosong, semua kembali ke nilai default di atas.

## Troubleshooting

- **"Gagal download Python/Camoufox"** → cek koneksi internet, jalankan lagi.
- **Google meminta verifikasi (captcha / 2FA)** → akun itu dilewati, lanjut akun berikutnya.
- **Login 9Router gagal** → cek `ROUTER_URL` dan `ROUTER_PASSWORD` di file `.env`, dan pastikan 9Router sedang berjalan.
- **Browser tidak muncul** → set `HEADLESS=false` di `.env`.

## Catatan

- Hanya untuk komputer Windows.
- Butuh koneksi internet (download Python, library, browser Camoufox; saat berjalan).
- Tombol "lanjut" di layar Google dideteksi **otomatis** (warna tombol, bukan teks), jadi cocok untuk akun Google dengan bahasa apa pun.
