"""
atria-auto: otomasi pendaftaran Atria console + simpan API key + daftar ke 9Router.

3 MODE:
  1. key             : login Atria + buat API key + simpan ke result.txt (STOP)
  2. full            : itu semua + daftarkan key ke 9Router (Check -> Save).
                       Kalau 9Router menolak, buat key baru, coba lagi (max 5x).
  3. import_result   : untuk yang SUDAH punya API key. Baca keys.txt
                       (nama|apikey), daftarkan setiap key ke 9Router.
                       Cek nama dulu: kalau sudah ada -> LEWATI.

Sumber:
  - empas.txt  : email|password        (mode 1 & 2)
  - keys.txt   : nama|apikey          (mode 3, dibuat user sendiri)

Hasil tersimpan di result.txt, LANGSUNG per akun (tidak menunggu semua selesai).
"""

from __future__ import annotations

import os
import sys
import time

from camoufox.sync_api import Camoufox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tampilan
from atria import login_atria, buat_api_key
import router9
from router9 import login_router, tambah_koneksi_atria, _koneksi_ada

# headless=False -> jendela browser TAMPIL supaya kamu bisa lihat jalannya.
# Bisa diubah lewat .env (HEADLESS=true/false).
HEADLESS = False

EMPAS_FILE = "empas.txt"    # sumber: email|password   (mode 1 & 2)
HASIL_FILE = "result.txt"   # hasil:  email|password|apikey
KEYS_FILE = "keys.txt"      # sumber: nama|apikey      (mode 3, opsional)
ENV_FILE = ".env"           # konfigurasi 9Router

# Default. Bisa ditimpa lewat .env (lihat muat_konfigurasi()).
MAX_COBA_KEY = 5            # berapa kali buat key ulang kalau ditolak 9Router
JEDA_ANTAR_AKUN = 5         # detik jeda sebelum proses akun berikutnya


def baca_env() -> dict[str, str]:
    """
    Baca file .env -> dict. Format: KEY=value, abaikan # dan baris kosong.

    Dipakai untuk konfigurasi 9Router supaya tidak perlu input manual
    setiap kali jalan. Cukup isi sekali di .env.
    """
    hasil: dict[str, str] = {}
    if not os.path.exists(ENV_FILE):
        return hasil
    with open(ENV_FILE, encoding="utf-8") as f:
        for baris in f:
            baris = baris.strip()
            if not baris or baris.startswith("#") or "=" not in baris:
                continue
            kunci, nilai = baris.split("=", 1)
            hasil[kunci.strip()] = nilai.strip()
    return hasil


def baca_empas() -> list[tuple[str, str]]:
    """Baca empas.txt -> list (email, password). Skip baris kosong/komentar.

    Kalau empas.txt belum ada, buat otomatis + buka di editor bawaan
    supaya user langsung bisa isi daftar akun (zero-config).
    """
    if not os.path.exists(EMPAS_FILE):
        tampilan.log("WARN", f"{EMPAS_FILE} belum ada - membuat file baru ...")
        with open(EMPAS_FILE, "w", encoding="utf-8") as f:
            f.write("# Isi daftar akun, satu per baris, format:\n")
            f.write("#   email|password\n")
            f.write("# Contoh:\n")
            f.write("#   budi@gmail.com|password123\n")
            f.write("#   sari@yahoo.com|password456\n")
            f.write("# Hapus/ubah contoh di bawah ini, lalu SIMPAN & tutup editor.\n\n")
            f.flush()
            os.fsync(f.fileno())
        tampilan.log("INFO", f"buka {EMPAS_FILE} - isi daftar akun kamu, lalu simpan & tutup ...")
        _buka_editor(EMPAS_FILE)
        tampilan.log("INFO", "lanjut ...")
    hasil = []
    with open(EMPAS_FILE, encoding="utf-8") as f:
        for baris in f:
            baris = baris.strip()
            if not baris or baris.startswith("#"):
                continue
            if "|" not in baris:
                tampilan.log("WARN", f"lewati baris aneh: {baris[:40]}")
                continue
            email, password = baris.split("|", 1)
            hasil.append((email.strip(), password.strip()))
    if not hasil:
        tampilan.log("ERROR", f"{EMPAS_FILE} masih kosong - isi dulu, lalu jalankan lagi.")
    return hasil


def _buka_editor(path: str) -> None:
    """Buka file di editor bawaan OS (Windows: notepad). Tunggu sampai ditutup."""
    try:
        import subprocess
        if sys.platform == "win32":
            # start menunggu editor tertutup (blocking)
            subprocess.run(["notepad.exe", path], check=False, timeout=None)
        else:
            subprocess.run([os.environ.get("EDITOR", "nano"), path], check=False)
    except Exception as err:
        tampilan.log("WARN", f"tidak bisa membuka editor otomatis: {err}")
        tampilan.log("INFO", f"buka & isi file ini manual: {path}")


def baca_keys() -> list[tuple[str, str]]:
    """
    Baca keys.txt -> list (nama, api_key) untuk MODE 3.

    Format tiap baris: nama|apikey
    (nama = email, dipakai sebagai nama koneksi di 9Router).
    Kalau belum ada, buat otomatis + buka editor (zero-config).
    """
    if not os.path.exists(KEYS_FILE):
        tampilan.log("WARN", f"{KEYS_FILE} belum ada - membuat file baru ...")
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            f.write("# Mode 3: input API key yang SUDAH ADA ke 9Router saja.\n")
            f.write("# Format tiap baris: nama|apikey\n")
            f.write("# Contoh:\n")
            f.write("#   budi@gmail.com|atr_xQRvOIV7T0uZmegg2oIid1rVKOwz20mH\n")
            f.write("# Hapus/ubah contoh di bawah ini, lalu SIMPAN & tutup editor.\n\n")
            f.flush()
            os.fsync(f.fileno())
        tampilan.log("INFO", f"buka {KEYS_FILE} - isi daftar key, lalu simpan & tutup ...")
        _buka_editor(KEYS_FILE)
        tampilan.log("INFO", "lanjut ...")
    hasil = []
    with open(KEYS_FILE, encoding="utf-8") as f:
        for baris in f:
            baris = baris.strip()
            if not baris or baris.startswith("#"):
                continue
            if "|" not in baris:
                tampilan.log("WARN", f"lewati baris aneh: {baris[:40]}")
                continue
            nama, api_key = baris.split("|", 1)
            nama = nama.strip()
            api_key = api_key.strip()
            if not nama or not api_key:
                continue
            hasil.append((nama, api_key))
    if not hasil:
        tampilan.log("ERROR", f"{KEYS_FILE} masih kosong - isi dulu, lalu jalankan lagi.")
    return hasil


def email_sudah_selesai(email: str) -> bool:
    """True kalau email ini sudah ada barisnya di result.txt."""
    if not os.path.exists(HASIL_FILE):
        return False
    with open(HASIL_FILE, encoding="utf-8") as f:
        for baris in f:
            if baris.startswith(email + "|"):
                return True
    return False


def simpan_hasil(email: str, password: str, api_key: str) -> None:
    """
    Simpan SATU baris hasil ke result.txt, LANGSUNG jadi file di disk.
    Kalau email ini sudah punya baris (misal key sebelumnya invalid),
    baris itu DIGANTI dengan key baru - tidak ada baris ganda.
    Dipanggil begitu key berhasil dibuat, supaya kalau script berhenti
    di tengah jalan, akun yang sudah selesai tidak hilang.
    """
    baris = f"{email}|{password}|{api_key}\n"
    sisa = []
    ada_header = False
    if os.path.exists(HASIL_FILE):
        with open(HASIL_FILE, encoding="utf-8") as f:
            for b in f:
                if b.startswith("#"):
                    ada_header = True
                    sisa.append(b)
                elif not b.startswith(email + "|"):
                    sisa.append(b)
    with open(HASIL_FILE, "w", encoding="utf-8") as f:
        if not ada_header:
            f.write("# format: email|password|apikey\n")
        f.writelines(sisa)
        f.write(baris)
        f.flush()
        os.fsync(f.fileno())
    tampilan.log("OK", f"TERSIMPAN ke {HASIL_FILE}: {email}")


# ---------------------------------------------------------------------------
# MODE 3: input result.txt ke 9Router saja (tanpa buat key baru)
# ---------------------------------------------------------------------------

def proses_import_result(url_router: str, sandi_router: str) -> tuple[int, int, int]:
    """
    Mode 3. Baca keys.txt (nama|apikey), daftarkan tiap key ke 9Router.
    Cek nama dulu: kalau sudah ada -> LEWATI.

    Kembalikan (berhasil, dilewati, gagal).
    """
    daftar = baca_keys()
    total = len(daftar)
    if total == 0:
        return 0, 0, 0

    tampilan.log("INFO", f"{total} baris dibaca dari {KEYS_FILE}")

    berhasil = 0
    skip = 0
    gagal_count = 0

    # browser fresh: TIDAK perlu login Atria, cuma butuh 9Router
    with Camoufox(
        headless=HEADLESS,
        humanize=True,
        os=(("windows",)),
        locale=["id-ID"],
        geoip=True,
    ) as browser:
        page = browser.new_page()
        # Timeout operasi 90 detik: server Atria kadang sangat lambat,
        # tapi tidak boleh menggantung selamanya.
        page.set_default_timeout(90_000)
        page.set_default_navigation_timeout(90_000)

        # login 9Router SEKALI untuk semua akun
        router9.atur_url(url_router)
        tampilan.log("INFO", f"login ke 9Router {url_router} ...")
        if not login_router(page, sandi_router):
            tampilan.log("ERROR", "GAGAL login 9Router - cek apakah 9Router jalan")
            return 0, 0, total

        for index, (nama, api_key) in enumerate(daftar, 1):
            tampilan.bilah(f"AKUN {index} dari {total}", time.strftime("%H:%M:%S"))
            tampilan.log("INFO", nama)

            try:
                status = tambah_koneksi_atria(page, nama, api_key, ganti_ada=False)
            except Exception as err:
                tampilan.log("ERROR", f"{type(err).__name__}: {err}")
                status = "gagal"

            if status == "ok":
                tampilan.sukses(f"SELESAI: {nama}")
                berhasil += 1
            elif status == "sudah_ada":
                tampilan.dilewati(f"DILEWATI: {nama} - sudah ada di 9Router")
                skip += 1
            else:
                tampilan.gagal(f"GAGAL: {nama} - (lanjut akun berikutnya)")
                gagal_count += 1

    return berhasil, skip, gagal_count


# ---------------------------------------------------------------------------
# MODE 1 & 2: buat API key (full = lanjut daftar ke 9Router)
# ---------------------------------------------------------------------------

def proses_akun(email: str, password: str, mode: str, url_router: str, sandi_router: str) -> str:
    """
    Jalankan satu akun penuh dengan browser baru.

    mode "key"  : login Atria + buat API key + simpan ke result.txt (STOP)
    mode "full" : itu semua + daftarkan key ke 9Router.

    Kembalikan: "ok" | "gagal".
    """
    # browser baru per akun supaya sesi Google sebelumnya tidak ikut
    with Camoufox(
        headless=HEADLESS,
        humanize=True,
        os=("windows",),
        locale=["id-ID"],
        geoip=True,
    ) as browser:
        page = browser.new_page()
        # Timeout operasi 90 detik: server Atria kadang sangat lambat,
        # tapi tidak boleh menggantung selamanya.
        page.set_default_timeout(90_000)
        page.set_default_navigation_timeout(90_000)

        # ---- login Atria + ambil API key ----
        if not login_atria(page, email, password):
            tampilan.log("ERROR", f"{email}: GAGAL login Atria")
            return "gagal"

        # ---- MODE "key": simpan key saja, STOP ----
        if mode == "key":
            api_key = buat_api_key(page, email)
            if not api_key:
                tampilan.log("ERROR", f"{email}: GAGAL dapat API key")
                return "gagal"
            tampilan.log("INFO", f"{email}: API key: {api_key[:12]}... ({len(api_key)} char)")
            simpan_hasil(email, password, api_key)
            tampilan.sukses(f"SELESAI: {email} - key tersimpan di {HASIL_FILE}")
            return "ok"

        # ---- MODE "full": lanjut ke 9Router ----
        router9.atur_url(url_router)
        tampilan.log("INFO", f"login ke 9Router {url_router} ...")
        if not login_router(page, sandi_router):
            tampilan.log("ERROR", f"{email}: GAGAL login 9Router (login Atria OK)")
            return "gagal"

        # ---- LOOP: buat key -> simpan -> daftar ke 9Router ----
        for percobaan in range(1, MAX_COBA_KEY + 1):
            tampilan.log(
                "INFO",
                f"{email}: percobaan key ke-{percobaan}/{MAX_COBA_KEY}",
            )
            api_key = buat_api_key(page, email)
            if not api_key:
                tampilan.log("ERROR", f"{email}: GAGAL dapat API key, coba lagi ...")
                continue

            # ---- SIMPAN LANGSUNG ke result.txt (ganti baris lama) ----
            tampilan.log("INFO", f"{email}: API key: {api_key[:12]}... ({len(api_key)} char)")
            simpan_hasil(email, password, api_key)

            # ---- daftarkan ke 9Router ----
            tampilan.log("INFO", f"{email}: daftarkan ke 9Router ...")
            status = tambah_koneksi_atria(page, email, api_key)
            if status == "ok":
                tampilan.sukses(f"SELESAI: {email} - koneksi terdaftar & valid")
                return "ok"
            if status == "sudah_ada":
                tampilan.dilewati(f"{email}: sudah ada di 9Router - anggap selesai")
                return "ok"
            if status == "invalid":
                tampilan.log("WARN", f"{email}: key ditolak 9Router")
                if percobaan < MAX_COBA_KEY:
                    tampilan.log("INFO", f"{email}: buat key baru & coba lagi ...")
                else:
                    tampilan.log("ERROR", f"{email}: sudah {MAX_COBA_KEY} kali ditolak - lewati")
                continue
            tampilan.log("ERROR", f"{email}: 9Router bermasalah (key sudah tersimpan)")
            return "gagal"

        return "gagal"


def muat_konfigurasi() -> None:
    """
    Baca konfigurasi dari .env ke variabel global.

      HEADLESS         true/false  (default: false = browser tampil)
      MAX_COBA_KEY     angka       (default: 5)
      JEDA_ANTAR_AKUN  detik       (default: 5)

    Nilai yang tidak ada atau salah format tetap pakai default.
    """
    global HEADLESS, MAX_COBA_KEY, JEDA_ANTAR_AKUN
    env = baca_env()

    # selalu reset ke default dulu, supaya nilai .env lama tidak nyangkut
    HEADLESS = False
    MAX_COBA_KEY = 5
    JEDA_ANTAR_AKUN = 5

    nilai_headless = env.get("HEADLESS", "").strip().lower()
    if nilai_headless in ("true", "1", "yes", "ya"):
        HEADLESS = True
    elif nilai_headless in ("false", "0", "no", "tidak"):
        HEADLESS = False

    for kunci, default in (("MAX_COBA_KEY", MAX_COBA_KEY), ("JEDA_ANTAR_AKUN", JEDA_ANTAR_AKUN)):
        nilai = env.get(kunci, "").strip()
        if not nilai:
            continue
        try:
            globals()[kunci] = max(0, int(nilai))
        except ValueError:
            tampilan.log("WARN", f".env: nilai {kunci}='{nilai}' bukan angka, pakai {default}")


def muat_router() -> tuple[str, str]:
    """
    Ambil konfigurasi 9Router dari file .env.

      ROUTER_URL      default: http://localhost:20128
      ROUTER_PASSWORD default: 123456

    Kalau .env belum ada atau kosong, pakai default di atas
    (cocok untuk 9Router lokal standar).
    """
    env = baca_env()
    url = env.get("ROUTER_URL", "").strip()
    sandi = env.get("ROUTER_PASSWORD", "").strip()

    if not url:
        url = "http://localhost:20128"
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    if not sandi:
        sandi = "123456"
    return url, sandi


def pilih_mode() -> str:
    print()
    print(tampilan.CYN + "PILIH MODE" + tampilan.RST)
    tampilan.garis()
    print(" 1. Buat API Key saja")
    print("    Login Atria -> buat key -> simpan ke result.txt")
    print()
    print(" 2. Full - sampai terdaftar di 9Router")
    print("    Login Atria -> buat key -> simpan -> daftar ke 9Router")
    print()
    print(" 3. Input keys.txt ke 9Router saja")
    print("    Untuk yang sudah punya API key, tinggal daftar ke 9Router")
    tampilan.garis()
    while True:
        jawab = input("Pilih (1/2/3) [default 2]: ").strip()
        if jawab in ("", "2"):
            return "full"
        if jawab == "1":
            return "key"
        if jawab == "3":
            return "import_result"
        tampilan.log("WARN", "ketik 1, 2, atau 3")


def main() -> None:
    tampilan.aktifkan_warna()
    tampilan.judul("ATRIA AUTO — Atria + 9Router")
    print()

    muat_konfigurasi()

    mode = pilih_mode()
    print()
    if mode == "key":
        tampilan.log("INFO", "Mode: Buat API Key saja")
    elif mode == "full":
        tampilan.log("INFO", "Mode: Full (Atria + 9Router)")
    else:
        tampilan.log("INFO", "Mode: Input keys.txt ke 9Router saja")

    tampilan.log("INFO", f"Browser headless={HEADLESS}")

    # ---- MODE 3: jalan sendiri (baca result.txt) ----
    if mode == "import_result":
        url_router, sandi_router = muat_router()
        tampilan.log("INFO", f"9Router: {url_router}")
        waktu_mulai = time.time()
        berhasil, skip, gagal_count = proses_import_result(url_router, sandi_router)
        print()
        tampilan.ringkasan(berhasil, skip, gagal_count)
        tampilan.estimasi_ringkasan(waktu_mulai)
        tampilan.garis()
        print(f"Lihat hasil lengkap di {HASIL_FILE}")
        return

    # ---- MODE 2 butuh URL & password 9Router ----
    url_router, sandi_router = "", ""
    if mode == "full":
        url_router, sandi_router = muat_router()
        tampilan.log("INFO", f"9Router: {url_router}")

    # ---- MODE 1 & 2: baca empas.txt ----
    daftar = baca_empas()
    total = len(daftar)
    if total == 0:
        return

    # hitung yang sudah selesai
    sudah = sum(1 for email, _ in daftar if email_sudah_selesai(email))
    tampilan.log("INFO", f"{total} akun dibaca dari {EMPAS_FILE}")
    if sudah:
        tampilan.log("INFO", f"{sudah} sudah ada di {HASIL_FILE} (akan di-skip)")

    berhasil = 0
    skip = 0
    gagal_count = 0
    selesai = 0
    waktu_mulai = time.time()

    for index, (email, password) in enumerate(daftar, 1):
        # skip yang sudah pernah selesai (sudah ada di result.txt)
        if email_sudah_selesai(email):
            tampilan.bilah(f"AKUN {index} dari {total}", time.strftime("%H:%M:%S"))
            tampilan.log("INFO", email)
            tampilan.dilewati(f"DILEWATI: {email} - sudah ada di {HASIL_FILE}")
            skip += 1
            selesai += 1
            continue

        tampilan.estimasi_progres(index, total, waktu_mulai, selesai)
        tampilan.bilah(f"AKUN {index} dari {total}", time.strftime("%H:%M:%S"))
        tampilan.log("INFO", email)
        try:
            status = proses_akun(email, password, mode, url_router, sandi_router)
        except Exception as err:
            # satu akun error jangan matikan sisanya
            tampilan.log("ERROR", f"{email}: {type(err).__name__}: {err}")
            tampilan.log("INFO", "lanjut ke akun berikutnya ...")
            status = "gagal"

        if status == "ok":
            berhasil += 1
        else:
            gagal_count += 1
        selesai += 1

        if index < total and JEDA_ANTAR_AKUN > 0:
            tampilan.log("INFO", f"jeda {JEDA_ANTAR_AKUN} detik sebelum akun berikutnya ...")
            time.sleep(JEDA_ANTAR_AKUN)

    print()
    tampilan.ringkasan(berhasil, skip, gagal_count)
    tampilan.estimasi_ringkasan(waktu_mulai)
    tampilan.garis()
    print(f"Lihat hasil lengkap di {HASIL_FILE}")


if __name__ == "__main__":
    main()
