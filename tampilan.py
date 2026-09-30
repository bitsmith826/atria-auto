"""
tampilan.py: utilitas output ke console - warna, garis, dan layout yang rapi.

Format log: [HH:MM:SS] [STATUS] pesan (mengikuti style telegram-store-bot-v1).
Semua perhitungan lebar memakai _lebar_tampilan() supaya karakter lebar
(em-dash, emoji, huruf CJK) tidak membuat garis/tengah jadi meleset.
"""

from __future__ import annotations

import ctypes
import sys
import time
import unicodedata

LEBAR = 60

# warna ANSI
CYN = "\033[36m"
GRN = "\033[32m"
RED = "\033[31m"
YEL = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RST = "\033[0m"

_WARNA_STATUS = {
    "INFO": CYN,
    "OK": GRN,
    "ERROR": RED,
    "WARN": YEL,
}


def aktifkan_warna() -> None:
    """Hidupkan ANSI + UTF-8 di console Windows (tanpa library tambahan)."""
    if sys.platform != "win32":
        return
    # aktifkan Virtual Terminal Processing (ESC sequence di-render)
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass
    # console default-nya cp1252; emoji/boks字符 jadi '?' -> paksa utf-8
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _lebar_tampilan(teks: str) -> int:
    """Lebar tampilan teks di terminal (karakter lebar = 2 kolom)."""
    total = 0
    for ch in teks:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            total += 2
        elif unicodedata.category(ch) in ("Mn", "Me"):
            pass  # combining mark, tidakmakan tempat
        else:
            total += 1
    return total


def _tengah(teks: str) -> str:
    """Bungkus teks supaya persis di tengah (rata kiri & kanan)."""
    isi = f" {teks} "
    sisa = LEBAR - _lebar_tampilan(isi)
    if sisa < 0:
        return isi
    kiri = sisa // 2
    kanan = sisa - kiri
    return " " * kiri + isi + " " * kanan


def judul(teks: str) -> None:
    """Blok judul dengan garis tebal di atas & bawah (teks persis tengah)."""
    garis_atas = CYN + "═" * LEBAR + RST
    print(garis_atas)
    print(BOLD + CYN + _tengah(teks) + RST)
    print(garis_atas)


def garis() -> None:
    """Garis pemisah biasa sepanjang LEBAR."""
    print(DIM + "─" * LEBAR + RST)


def bilah(label: str, waktu: str = "", warna: str = YEL) -> None:
    """
    Header blok: garis + 'label' + waktu di kanan + garis.
    Waktu (eber: 'HH:MM:SS') di-kanan-kanan secara presisi.
    """
    isi = f" {label} "
    if waktu:
        isi = _tengah_kanan(isi, f" {waktu} ")
    print(warna + "─" * LEBAR + RST)
    print(BOLD + warna + isi + RST)
    print(warna + "─" * LEBAR + RST)


def _tengah_kanan(kiri: str, kanan: str) -> str:
    """Tempel 'kanan' ke ujung kanan; spasi menyesuaikan."""
    sisa = LEBAR - _lebar_tampilan(kiri) - _lebar_tampilan(kanan)
    if sisa < 0:
        sisa = 0
    return kiri + " " * sisa + kanan


def log(status: str, pesan: str) -> None:
    """
    Satu baris log terformat: [HH:MM:SS] [STATUS]  pesan.
    Kolom pesan selalu mulai di kolom yang sama (status dipadding).
    """
    jam = time.strftime("%H:%M:%S")
    warna = _WARNA_STATUS.get(status, "")
    label = f"[{status}]"
    # [INFO] = 6, [OK] = 5, [ERROR] = 7 -> padding ke 7 supaya presisi
    print(f"{DIM}[{jam}]{RST} {warna}{label:<7}{RST} {pesan}", flush=True)


def sukses(pesan: str) -> None:
    print(f"{GRN}✅ {pesan}{RST}", flush=True)


def dilewati(pesan: str) -> None:
    print(f"{DIM}⏭  {pesan}{RST}", flush=True)


def gagal(pesan: str) -> None:
    print(f"{RED}❌ {pesan}{RST}", flush=True)


def ringkasan(berhasil: int, skip: int, error: int) -> None:
    """Blok ringkasan akhir."""
    bilah("RINGKASAN", time.strftime("%H:%M:%S"), GRN)
    print(f"{GRN}✅ Berhasil   : {berhasil}{RST}")
    print(f"{DIM}⏭  Dilewati   : {skip}{RST}")
    print(f"{RED}❌ Gagal      : {error}{RST}")
    garis()


def _fmt_dur(detik: float) -> str:
    """Format durasi: '62 menit' / '2 jam 15 menit' / '45 detik'."""
    detik = int(detik)
    if detik < 60:
        return f"{detik} detik"
    if detik < 3600:
        return f"{detik // 60} menit"
    jam = detik // 3600
    sisa = (detik % 3600) // 60
    if sisa == 0:
        return f"{jam} jam"
    return f"{jam} jam {sisa} menit"


def estimasi_progres(index: int, total: int, mulai: float, selesai: int) -> None:
    """Estimasi sisa waktu saat mulai akun baru.

    index    : nomor akun yang sedang diproses (mulai dari 1)
    total    : total akun
    mulai    : time.time() saat batch mulai
    selesai  : jumlah akun yang sudah selesai (berhasil+skip+gagal)
    """
    if selesai == 0:
        # belum ada data, jangan tebak
        return
    berjalan = time.time() - mulai
    rata = berjalan / selesai
    sisa = (total - index + 1) * rata
    selesai_pct = selesai / total * 100
    log("INFO", f"progres {selesai}/{total} ({selesai_pct:.0f}%) - "
                f"rata-rata {_fmt_dur(rata)}/akun, "
                f"estimasi sisa ~{_fmt_dur(sisa)}")


def estimasi_ringkasan(mulai: float) -> None:
    """Cetak total durasi & rata-rata per akun di ringkasan akhir."""
    if not mulai:
        return
    total_detik = time.time() - mulai
    log("INFO", f"total waktu {_fmt_dur(total_detik)}")
    garis()
