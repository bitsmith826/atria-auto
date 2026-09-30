"""
router9.py: login ke 9Router lokal + tambah koneksi provider Atria Dawn.

Fungsi:
  - login_router(page, password) -> True kalau sudah di dashboard
  - tambah_koneksi_atria(page, nama, api_key) -> True kalau tersimpan
"""

from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import Page

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tampilan

_LOGIN = "http://localhost:20128/login"
_PROVIDERS = "http://localhost:20128/dashboard/providers"


def atur_url(base: str) -> None:
    """Ganti URL dasar 9Router (dipanggil dari main.py sesuai input user)."""
    global _LOGIN, _PROVIDERS
    base = base.rstrip("/")
    _LOGIN = f"{base}/login"
    _PROVIDERS = f"{base}/dashboard/providers"


def _klik_tombol(page: Page, nama: str) -> bool:
    """Klik tombol role=button kalau ada & terlihat. Kembalikan True kalau klik."""
    try:
        loc = page.get_by_role("button", name=nama)
        if loc.count() > 0 and loc.first.is_visible():
            loc.first.click()
            return True
    except Exception:
        return False
    return False


def _tombol_terlihat(page: Page, nama: str) -> bool:
    loc = page.get_by_role("button", name=nama)
    try:
        return loc.count() > 0 and loc.first.is_visible()
    except Exception:
        return False


def _sudah_login(page: Page) -> bool:
    """Cek apakah halaman sudah menampilkan dashboard (menu Providers)."""
    try:
        teks = page.inner_text("body")
    except Exception:
        return False
    # menu khas dashboard 9Router; 'Enter your password' = masih di login
    return "Providers" in teks and "Enter your password" not in teks


def login_router(page: Page, password: str = "123456") -> bool:
    """Login ke dashboard 9Router. Kembalikan True kalau sukses."""
    tampilan.log("INFO", f"buka halaman login 9Router ({_LOGIN}) ...")
    try:
        page.goto(_LOGIN, wait_until="domcontentloaded", timeout=15_000)
    except Exception as err:
        tampilan.log("ERROR", f"TIDAK BISA BUKA {_LOGIN}")
        tampilan.log("ERROR", f"cek apakah 9Router jalan & URL benar ({type(err).__name__})")
        return False
    time.sleep(1)

    # SPA butuh waktu render. Tunggu sampai HALAMAN SIAP: muncul form
    # password (perlu login) atau menu dashboard (sudah login).
    # Maksimal 30 detik, cek setiap 0.5 detik.
    for _ in range(60):
        teks_halaman = page.inner_text("body") or ""
        if "Loading" not in teks_halaman:
            break
        time.sleep(0.5)

    # ---- Kalau SUDAH login (cookie masih aktif), halaman langsung
    # menampilkan dashboard tanpa form password. Tidak perlu login lagi.
    if _sudah_login(page):
        tampilan.log("OK", "sudah login 9Router (sesi masih aktif)")
        return True

    # halaman SPA bisa lambat; tunggu field password betul-betul muncul
    tampilan.log("INFO", "tunggu field password ...")
    field = page.locator("input[type='password']")
    field.wait_for(state="visible", timeout=30_000)

    tampilan.log("INFO", "isi password ...")
    field.fill(password)
    time.sleep(0.5)
    try:
        page.get_by_role("button", name="Login").click(timeout=15_000)
    except Exception as err:
        # klik bisa menggantung kalau halaman melakukan request lambat.
        # Coba submit form lewat keyboard (Enter) sebagai jalan cadangan.
        tampilan.log("WARN", f"klik Login lambat ({type(err).__name__}), coba Enter ...")
        try:
            field.press("Enter")
        except Exception:
            pass
    time.sleep(4)

    # SPA tidak ganti URL setelah login (tetap /login tapi dashboard sudah
    # terbuka), jadi cek isinya: menu 'Providers' harus ada.
    if _sudah_login(page):
        tampilan.log("OK", "login 9Router SUKSES")
        return True

    # field password masih terlihat = login gagal (password salah?)
    tampilan.log("ERROR", f"login 9Router GAGAL -> {page.url}")
    tampilan.log("ERROR", "cek ROUTER_PASSWORD di file .env")
    return False


def tambah_koneksi_atria(
    page: Page, nama: str, api_key: str, ganti_ada: bool = True
) -> str:
    """
    Tambah koneksi Atria Dawn: masuk halaman provider, CEK NAMA dulu.

    ganti_ada=True (mode 2, key baru):
      - kalau nama SUDAH ada -> HAPUS koneksi lama, lalu daftarkan ulang
        pakai key baru (supaya TIDAK ADA duplikat).
    ganti_ada=False (mode 3, import key):
      - kalau nama SUDAH ada -> kembalikan "sudah_ada" (tidak input ulang)

    Kembalikan:
      "ok"        -> tersimpan & lolos Check
      "sudah_ada" -> nama koneksi sudah ada (hanya mode 3)
      "invalid"   -> API key ditolak 9Router (perlu buat key baru)
      "gagal"     -> masalah lain
    """
    tampilan.log("INFO", "buka menu Providers ...")
    page.goto(_PROVIDERS, wait_until="domcontentloaded")
    # SPA: tunggu kata 'Atria Dawn' muncul
    page.get_by_text("Atria Dawn", exact=True).wait_for(state="visible", timeout=30_000)
    time.sleep(2)

    tampilan.log("INFO", "klik 'Atria Dawn' ...")
    page.get_by_text("Atria Dawn", exact=True).click()
    time.sleep(4)

    # ---- CEK NAMA: kalau sudah ada, tergantung mode ----
    # Daftar koneksi HANYA tampil di halaman detail Atria Dawn, bukan di
    # halaman providers. Jadi cek nama harus SETELAH klik section-nya.
    if _koneksi_ada(page, nama):
        if not ganti_ada:
            tampilan.log("OK", f"nama '{nama}' sudah ada di 9Router -> lewati")
            return "sudah_ada"

        # mode 2: hapus dulu, ganti key baru (anti duplikat)
        tampilan.log("INFO", f"nama '{nama}' sudah ada -> hapus dulu, ganti key baru")
        if not _hapus_koneksi(page, nama):
            tampilan.log("ERROR", f"gagal hapus koneksi lama '{nama}' -> lewati")
            return "gagal"
        time.sleep(2)
        if _koneksi_ada(page, nama):
            tampilan.log("ERROR", f"'{nama}' masih ada setelah hapus -> lewati")
            return "gagal"
        tampilan.log("OK", f"koneksi lama '{nama}' dihapus")

    tampilan.log("INFO", f"nama '{nama}' belum ada -> daftarkan")

    # Tombolnya bisa "Add Connection" (kalau belum punya koneksi)
    # atau "Add" (kalau sudah ada). Klik salah satu yang ada.
    tampilan.log("INFO", "klik tombol Add Connection/Add ...")
    if _tombol_terlihat(page, "Add Connection"):
        page.get_by_role("button", name="Add Connection").first.click()
    else:
        # tombol 'add' ke-0 = Add Connection, ke-1 = Add Model (jangan diklik)
        page.get_by_role("button", name="add").nth(0).click()
    time.sleep(3)

    # dialog "Add Atria Dawn API Key"
    tampilan.log("INFO", f"isi Nama: {nama} ...")
    field_nama = page.locator("input[placeholder='Production Key']")
    field_nama.wait_for(state="visible")
    field_nama.fill(nama)
    time.sleep(0.5)

    tampilan.log("INFO", f"isi API Key: {api_key[:12]}... ({len(api_key)} char)")
    field_key = page.locator("input[type='password']")
    field_key.wait_for(state="visible")
    field_key.fill(api_key)
    time.sleep(0.5)

    # Klik Check dulu untuk validasi key (sebelum Save).
    # HASIL CHECK hanya boleh dibaca di DALAM dialog Add Connection.
    # Jangan scan seluruh body: koneksi LAIN yang invalid juga menampilkan
    # teks "Invalid API key" di halaman -> false positive -> key valid
    # malah dibatalkan terus.
    tampilan.log("INFO", "klik Check (validasi key) ...")
    if _tombol_terlihat(page, "Check"):
        page.get_by_role("button", name="Check").click()
        time.sleep(4)
        hasil_check = _teks_dialog_add(page)
        if hasil_check is not None and "invalid api key" in hasil_check.lower():
            tampilan.log("ERROR", "key DITOLAK (Invalid API key)")
            _tutup_dialog(page)
            return "invalid"
        tampilan.log("OK", "key lolos Check")
    else:
        tampilan.log("WARN", "tidak ada tombol Check, lanjut Save")

    tampilan.log("INFO", "klik Save ...")
    page.get_by_role("button", name="Save").click()
    time.sleep(4)

    # Cek apakah koneksi baru muncul di list
    ok = _koneksi_ada(page, nama)
    if ok:
        tampilan.log("OK", f"koneksi '{nama}' TERSIMPAN")
    else:
        tampilan.log("ERROR", f"koneksi '{nama}' TIDAK YAKIN - periksa manual")
    return "ok" if ok else "gagal"


def _tutup_dialog(page: Page) -> None:
    """Tutup dialog Add tanpa menyimpan (klik Cancel / X)."""
    for nama in ("Cancel", "✕", "Close"):
        if _klik_tombol(page, nama):
            break
    time.sleep(1)


def _teks_dialog_add(page: Page) -> str | None:
    """Ambil teks HANYA dari dialog Add Connection yang sedang terbuka.

    Penting: pesan error koneksi LAIN yang invalid juga muncul di halaman
    (di luar dialog). Kalau scan seluruh body, key yang valid bisa salah
    dianggap invalid. Jadi baca hanya isi dialog.
    """
    try:
        # dialog modal biasanya <div role="dialog"> atau overlay terakhir
        teks = page.evaluate(
            """() => {
                // 1) role="dialog"
                let d = document.querySelector('[role="dialog"]');
                if (d) return (d.textContent || '').trim();
                // 2) modal overlay terakhir (kalau pakai antd/modal custom)
                const modal = document.querySelectorAll('.ant-modal, .modal, [class*="modal"], [class*="dialog"]');
                if (modal.length) return (modal[modal.length-1].textContent || '').trim();
                // 3) overlay backdrop terakhir di body
                const ov = document.querySelectorAll('body > div[class*="overlay"], body > div[class*="overlay"]');
                if (ov.length) return (ov[ov.length-1].textContent || '').trim();
                return null;
            }"""
        )
        return teks
    except Exception:
        return None


def _koneksi_ada(page: Page, nama: str) -> bool:
    """Cari apakah nama koneksi sudah ada di list Connections."""
    try:
        teks = page.inner_text("body")
        return nama in teks
    except Exception:
        return False


def _hapus_koneksi(page: Page, nama: str) -> bool:
    """Hapus koneksi bernama 'nama' dari list Atria Dawn.

    Tombol delete berada 3 level di atas elemen <p> yang berisi nama,
    jadi kita naik ke ancestor tersebut, lalu cari tombol delete di dalamnya.
    """
    p_nama = page.locator(f"p:has-text('{nama}')")
    if p_nama.count() == 0:
        return False

    # Tombol delete ada di baris yang sama, SETELAH elemen nama.
    # 'following::button' ambil tombol delete pertama setelah nama itu.
    del_btn = p_nama.locator("xpath=following::button[contains(.,'delete')]")
    if del_btn.count() == 0:
        return False

    try:
        del_btn.first.click()
        time.sleep(2)
        if _tombol_terlihat(page, "Confirm"):
            page.get_by_role("button", name="Confirm").click()
            time.sleep(3)
        return True
    except Exception:
        return False
