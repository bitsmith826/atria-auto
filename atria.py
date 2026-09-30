"""
atria.py: login ke Atria console + buat API key.

Fungsi:
  - login_atria(page, email, password) -> True kalau sudah di dalam console
  - buat_api_key(page, email) -> api_key (string) atau None kalau gagal
"""

from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import Page

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tampilan

_START = "https://api.atria-asi.ai/"
_KEYS_URL = "https://api.atria-asi.ai/console/keys"


def _tombol_terlihat(page: Page, nama: str) -> bool:
    loc = page.get_by_role("button", name=nama)
    try:
        return loc.count() > 0 and loc.first.is_visible()
    except Exception:
        return False


_teks_terakhir = ""


def _klik_tombol_lanjut_otomatis(page: Page, skip: tuple | None = None) -> bool:
    """
    Klik tombol 'lanjut' di layar konfirmasi Google, untuk BAHASA APA PUN.

    Strategi utama: tombol utama Google SELALU punya background berwarna
    (biru), terlepas dari bahasa. Tebak-tebakan teks saja tidak cukup karena
    bahasa akun bisa beda-beda.

    skip = (url, teks) -> jangan klik tombol dengan teks yang sama kalau
    url-nya masih sama (mencegah klik berulang yang bikin Google error).

    Kembalikan True kalau ada tombol yang diklik.
    """
    # ambil info semua tombol: teks, warna background, ukuran
    try:
        info = page.evaluate("""() => {
            const sem = Array.from(document.querySelectorAll('button, [role="button"], a[role="button"]'));
            const hasil = [];
            for (let i = 0; i < sem.length; i++) {
                const b = sem[i];
                const rect = b.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;
                const st = window.getComputedStyle(b);
                const bg = st.backgroundColor;
                const m = bg.match(/[0-9.]+/g);
                let r = 255, g = 255, bl = 255;
                if (m && m.length >= 3) { r = +m[0]; g = +m[1]; bl = +m[2]; }
                const mx = Math.max(r, g, bl), mn = Math.min(r, g, bl);
                hasil.push({
                    i: i,
                    teks: (b.innerText || b.textContent || '').trim().slice(0, 60),
                    berwarna: (mx - mn) > 40 && mx > 100,   // bukan putih/abu-abu
                    biru: bl > r + 20 && bl > g + 20,        // dominan biru (khas Google)
                    area: Math.round(rect.width * rect.height),
                });
            }
            return hasil;
        }""")
    except Exception:
        return False
    if not info:
        return False

    # kata "batal/tolak" dalam banyak bahasa
    kata_batal = (
        "cancel", "cancelar", "abbrechen", "annuler", "annulla",
        "zrušit", "anuluj", "отмена", "batal", "batalkan", "cancel·la",
        "no thanks", "no, thanks", "not now", "maybe later", "later",
        "tidak", "nanti", "tidak sekarang", "jangan",
        "no", "nein", "non", "não", "否", "取消", "취소",
        "back", "zurück", "retour", "atrás", "kembali", "返回", "뒤로",
        "deny", "refuse", "reject", "decline",
    )
    # kata "lanjut" dalam banyak bahasa (skor tambahan)
    kata_lanjut = (
        "continue", "next", "lanjut", "lanjutkan", "berikutnya",
        "saya mengerti", "i understand", "i agree", "i accept", "agree", "accept",
        "saya setuju", "setuju", "saya menyetujui", "menyetujui",
        "saya menyetujui persyaratan", "i accept the terms",
        "weiter", "weitergehen", "einverstanden", "ich stimme zu",
        "continuar", "siguiente", "aceptar", "estoy de acuerdo",
        "suivant", "j'accepte", "accepter", "je suis d'accord",
        "avanti", "prossimo", "accetto",
        "dalej", "akceptuję", "zgadzam się",
        "далее", "принимаю", "согласен",
        "aceitar", "concordo", "continuar",
        "volgende", "ga verder", "fortsæt", "nästa", "neste",
        "继续", "繼續", "下一步", "同意", "계속", "동의",
    )

    kandidat = []
    for b in info:
        teks = (b["teks"] or "").strip().lower()
        if not teks:
            continue
        # jangan klik tombol batal
        if any(k in teks for k in kata_batal):
            continue
        # jangan klik link merk/nama domain (contoh: "atria-asi.ai")
        # -> ini bukan tombol lanjut, hanya bikin pindah ke halaman pilih akun
        if "." in teks and " " not in teks and len(teks) < 30:
            continue

        skor = 0
        if b["biru"]:
            skor += 20          # tombol biru = tombol utama Google
        elif b["berwarna"]:
            skor += 8           # warna lain, mungkin tombol utama
        if any(k in teks for k in kata_lanjut):
            skor += 5
        skor += min(3, b["area"] // 5000)  # tombol besar sedikit diunggulkan

        kandidat.append((skor, b["i"], teks))

    if not kandidat:
        return False

    # skor tertinggi menang; seri = ambil yang paling akhir di halaman
    kandidat.sort(key=lambda x: (x[0], x[1]))
    skor, idx, teks = kandidat[-1]

    # jangan klik tombol yang sama 2x di halaman yang sama.
    # CATATAN: kalau URL sudah berubah, izinkan teks yang sama karena
    # layar consent Google berurutan bisa punya beberapa tombol
    # 'lanjutkan' di halaman yang berbeda (akun baru = lebih banyak layar).
    if skip is not None and teks == skip[1] and page.url == skip[0]:
        return False

    try:
        page.evaluate(f"""() => {{
            const sem = document.querySelectorAll('button, [role="button"], a[role="button"]');
            sem[{idx}].click();
        }}""")
        global _teks_terakhir
        _teks_terakhir = teks
        tampilan.log("INFO", f"klik tombol Google: '{teks[:30]}'")
        return True
    except Exception as err:
        tampilan.log("WARN", f"(klik tertahan: {type(err).__name__}, halaman navigasi)")
        return True


def _klik_tombol_substr(
    page: Page, daftar_sub: tuple[str, ...], terakhir: bool = False
) -> str | None:
    """
    Klik tombol pertama yang teksnya mengandung salah satu substring.
    Bahasa-agnostik: cocok 'create key', '创建密钥', dll.

    terakhir=True -> klik tombol TERAKHIR yang cocok (untuk dialog yang
    muncul setelah tombol utama dengan nama sama).

    Kembalikan teks tombol yang diklik, atau None.
    """
    try:
        pilihan = page.evaluate(
            """(daftar) => {
                const sem = Array.from(document.querySelectorAll('button, [role="button"]'));
                const cocok = [];
                for (let i = 0; i < sem.length; i++) {
                    const b = sem[i];
                    const r = b.getBoundingClientRect();
                    if (r.width === 0 || r.height === 0) continue;
                    const t = (b.innerText || b.textContent || '').trim().toLowerCase();
                    if (!t) continue;
                    if (daftar.some(s => t.includes(s))) cocok.push(i);
                }
                if (!cocok.length) return null;
                const idx = cocok[cocok.length - 1];
                sem[idx].click();
                return (sem[idx].innerText || sem[idx].textContent || '').trim();
            }""",
            list(daftar_sub),
        )
    except Exception:
        pilihan = None
    if pilihan:
        tampilan.log("INFO", f"klik tombol '{pilihan[:30]}' ...")
    return pilihan


def _klik_tombol(page: Page, nama: str) -> bool:
    """Klik button kalau ada. Tahan bila Google sedang redirect."""
    if not _tombol_terlihat(page, nama):
        return False
    tampilan.log("INFO", f"klik '{nama}' ...")
    try:
        page.get_by_role("button", name=nama).first.click(timeout=15_000)
    except Exception as err:
        tampilan.log("WARN", f"(klik tertahan: {type(err).__name__}, halaman navigasi)")
    return True


# label "berikutnya" Google dalam banyak bahasa
_LABEL_BERIKUTNYA = (
    "Berikutnya", "Next", "Weiter", "Suivant", "Siguiente",
    "次へ", "다음", "Далее", "Próximo", "Dalej",
)


def _klik_berikutnya(page: Page) -> bool:
    """Klik tombol 'berikutnya' Google, bahasa apa pun."""
    for label in _LABEL_BERIKUTNYA:
        if _klik_tombol(page, label):
            return True
    return False


def _klik_link_terlihat(page: Page, daftar_label: tuple[str, ...]) -> bool:
    """Klik link pertama yang terlihat dari daftar label (multi-bahasa)."""
    for label in daftar_label:
        try:
            link = page.get_by_role("link", name=label).first
            link.wait_for(state="visible", timeout=20_000)
            link.click()
            tampilan.log("INFO", f"klik link '{label}' ...")
            return True
        except Exception:
            continue
    tampilan.log("ERROR", f"tidak ketemu link dari: {daftar_label}")
    return False


def _klik_tombol_terlihat(page: Page, daftar_label: tuple[str, ...]) -> bool:
    """Klik button pertama yang terlihat dari daftar label (multi-bahasa)."""
    for label in daftar_label:
        try:
            b = page.get_by_role("button", name=label).first
            b.wait_for(state="visible", timeout=20_000)
            b.click()
            tampilan.log("INFO", f"klik tombol '{label}' ...")
            return True
        except Exception:
            continue
    tampilan.log("ERROR", f"tidak ketemu tombol dari: {daftar_label}")
    return False


def _selesai_login(page: Page) -> bool:
    """Sudah masuk console Atria (bukan halaman login Google atau Atria)."""
    url = page.url or ""
    if "accounts.google" in url:
        return False
    # auth.atria-asi.ai/sign-in atau /register = belum login
    if "auth.atria-asi.ai" in url:
        return False
    return "atria-asi.ai" in url


def _klik_email_sendiri(page: Page, email: str) -> bool:
    """Di layar 'pilih akun' Google, klik baris yang berisi email kita."""
    try:
        info = page.evaluate("""(email) => {
            const sem = Array.from(document.querySelectorAll(
                'a, button, [role="link"], [role="button"], div, li'
            ));
            for (const b of sem) {
                const t = (b.innerText || b.textContent || '').trim();
                if (t.toLowerCase().includes(email.toLowerCase())) {
                    const r = b.getBoundingClientRect();
                    if (r.width === 0 || r.height === 0) continue;
                    return t.slice(0, 60);
                }
            }
            return null;
        }""", email)
    except Exception:
        return False
    if not info:
        return False
    try:
        page.get_by_text(email, exact=False).first.click(timeout=10_000)
        tampilan.log("INFO", f"klik akun '{email}' ...")
        return True
    except Exception:
        return False


def _pendek(url: str) -> str:
    if not url:
        return "(kosong)"
    if len(url) <= 60:
        return url
    return url[:60] + "..."


def login_atria(page: Page, email: str, password: str) -> bool:
    """Login Google sampai masuk ke console Atria. Kembalikan True kalau sukses."""
    tampilan.log("INFO", "buka landing page Atria ...")
    page.goto(_START, timeout=60_000)
    page.wait_for_load_state("domcontentloaded")

    tampilan.log("INFO", "klik 'Open console' ...")
    page.locator("a.button-primary").first.click(timeout=30_000)
    page.wait_for_load_state("domcontentloaded", timeout=30_000)

    tampilan.log("INFO", "klik 'Create account' ...")
    _klik_link_terlihat(page, ("Create account", "创建账户", "Buat akun", "Daftar akun"))
    page.wait_for_load_state("domcontentloaded", timeout=30_000)

    tampilan.log("INFO", "klik 'Continue with Google' ...")
    _klik_tombol_terlihat(
        page,
        ("Continue with Google", "使用 Google 继续", "Lanjutkan dengan Google"),
    )
    page.wait_for_load_state("domcontentloaded", timeout=30_000)

    tampilan.log("INFO", f"isi email {email} ...")
    field_email = page.get_by_role("textbox", name="Email")
    field_email.wait_for(state="visible", timeout=30_000)
    field_email.click()
    field_email.fill(email)
    time.sleep(0.5)
    _klik_berikutnya(page)
    page.wait_for_load_state("domcontentloaded", timeout=30_000)

    tampilan.log("INFO", "isi password ...")
    field_pw = page.locator("input[name='Passwd']")
    field_pw.wait_for(state="visible", timeout=30_000)
    field_pw.click()
    field_pw.fill(password)
    time.sleep(0.5)
    _klik_berikutnya(page)
    page.wait_for_load_state("domcontentloaded", timeout=30_000)

    tampilan.log("INFO", "deteksi layar konfirmasi Google ...")
    klik_terakhir = None  # (url, teks) supaya tidak klik tombol sama 2x
    for percobaan in range(1, 12):
        time.sleep(2)
        if _selesai_login(page):
            tampilan.log("OK", "sudah kembali ke Atria")
            break
        url = page.url or ""
        # layar "pilih akun": klik email kita sendiri
        if "accountchooser" in url:
            if _klik_email_sendiri(page, email):
                tampilan.log("INFO", f"pilih akun {email} -> {_pendek(page.url)}")
                klik_terakhir = None
                continue
        if _klik_tombol_lanjut_otomatis(page, klik_terakhir):
            tampilan.log("INFO", f"-> {_pendek(page.url)}")
            klik_terakhir = (url, _teks_terakhir)
        else:
            tampilan.log("INFO", f"(percobaan {percobaan}) tidak ada tombol lanjut, tunggu ...")

    ok = _selesai_login(page)
    if ok:
        tampilan.log("OK", "login Atria SUKSES")
    else:
        tampilan.log("ERROR", "login Atria GAGAL")
    return ok


def buat_api_key(page: Page, email: str) -> str | None:
    """
    Buka menu API Keys, klik 'Create key' (创建密钥),
    isi nama pakai email, lalu ambil API key yang muncul.
    """
    # /console/keys di-redirect ke /console, jadi harus klik menu 'API Key'.
    # Catatan: halaman bisa sedang di 9Router (loop percobaan ulang), jadi
    # pastikan dulu kita ada di domain Atria.
    tampilan.log("INFO", "buka menu API Keys ...")
    if "atria-asi.ai" not in (page.url or ""):
        page.goto(_KEYS_URL, wait_until="domcontentloaded")
        time.sleep(3)
    if "/console/keys" not in (page.url or ""):
        page.get_by_role("link", name="API Key").first.click()
        time.sleep(4)

    # Klik tombol 'Create key' (bahasa apa pun: 创建密钥 / Create key).
    # Pakai substring match supaya tidak tergantung bahasa console.
    tombol_buat = _klik_tombol_substr(page, ("create key", "创建密钥", "buat key"))
    if not tombol_buat:
        # SPA bisa lambat; tunggu tombolnya muncul dulu
        tampilan.log("INFO", "tunggu tombol create key ...")
        time.sleep(5)
        tombol_buat = _klik_tombol_substr(page, ("create key", "创建密钥", "buat key"))

    if not tombol_buat:
        tampilan.log("ERROR", "GAGAL: tombol create key tidak ditemukan")
        return None

    time.sleep(2)

    # Isi nama key dengan email
    tampilan.log("INFO", f"isi nama key: {email} ...")
    field_nama = page.get_by_role("textbox").first
    field_nama.wait_for(state="visible")
    field_nama.click()
    field_nama.fill(email)
    time.sleep(0.5)

    # Klik tombol submit di dialog (create key / confirm / 确定).
    # Pakai substring match, klik tombol terakhir yang cocok (dialog paling baru).
    tampilan.log("INFO", "submit dialog create key ...")
    if not _klik_tombol_substr(
        page, ("create key", "创建密钥", "confirm", "确定", "ok", "submit"), terakhir=True
    ):
        tampilan.log("WARN", "submit tertahan, coba sekali lagi ...")
        time.sleep(2)
        if not _klik_tombol_substr(
            page, ("create key", "创建密钥", "confirm", "确定", "ok", "submit"), terakhir=True
        ):
            tampilan.log("ERROR", "submit gagal")
            return None
    time.sleep(4)

    # API key muncul di layar.
    api_key = _ambil_api_key(page)
    if api_key:
        tampilan.log("OK", f"API key didapat: {api_key[:12]}... ({len(api_key)} char)")
        # Tutup dialog: 'I have saved the key' / '我已保存密钥' / Done / OK.
        # Pakai substring, kalau tidak ada tutup pakai X.
        if not _klik_tombol_substr(
            page, ("saved", "已保存", "i have saved", "done", "ok", "关闭", "close")
        ):
            # tutup pakai tombol X di dialog
            try:
                page.locator("dialog button[aria-label='Close']").first.click(timeout=5_000)
            except Exception:
                pass
        time.sleep(1)
    else:
        tampilan.log("ERROR", "GAGAL: API key tidak ditemukan di layar")
        # cetak kondisi layar untuk debugging
        try:
            teks = page.inner_text("body")
            import re as _re

            semua = _re.findall(r"atr_[A-Za-z0-9_•]{4,}", teks)
            tampilan.log("WARN", f"key di layar sekarang: {semua[:8]}")
            tampilan.log("WARN", f"dialog 'created' terbuka? {'created' in teks.lower() or '已创建' in teks}")
        except Exception as ex:
            tampilan.log("WARN", f"gagal baca body: {ex}")
    return api_key


def _ambil_api_key(page: Page) -> str | None:
    """
    Ambil API key baru dari dialog hasil Create.

    Dialognya: 'API Key 已创建' + '请立即复制，关闭后将无法再次查看' (copy
    sekarang, tidak bisa dilihat lagi setelah ditutup) + key lengkap +
    tombol '复制' & '我已保存密钥'.

    Di list key, semua key ditampilkan teredaksi (atr_XXXX••••), jadi cuma
    key BARU di dialog yang lengkap.

    Cara: scan textContent SEMUA elemen, cari semua yang match pola key,
    ambil yang TERPANJANG. Tie-break: kalau ada 2+ elemen dengan panjang
    sama, ambil yang teksnya PALING bersih (persis = key saja), lalu yang
    ada di dialog. Beri waktu sampai 20 detik.
    """
    import re

    # Ambil API key dari dialog hasil Create.
    #
    # Struktur DOM (dipastikan lewat probe):
    #   <DIALOG class="key-create-dialog">
    #     <DIV class="key-dialog-result">
    #       <CODE class="key-dialog-secret">atr_xxxx_yyyy...</CODE>  <-- KEY LENGKAP
    #   <TABLE><TBODY><TR><TH><CODE class="key-usage-module__prefix">atr_xxxx••••</CODE>
    #       ^ list key lama, TEREDAKSI, BUKAN sumbernya
    #
    # Jadi: ambil EKSKLUSIF dari class key-dialog-secret. Kalau gagal, fallback
    # ke elemen mana pun yang teksnya murni satu key (tidak mengandung teks lain).

    # maksimal ~10 detik. Kalau lebih dari itu, mending refresh dan buat
    # key baru (lebih cepat daripada nunggu dialog lambat).
    for putaran in range(10):
        try:
            hasil = page.evaluate(
                """() => {
                    // 1) sumber utama: class key-dialog-secret
                    const rahasia = document.querySelector('.key-dialog-secret');
                    if (rahasia) {
                        const t = (rahasia.textContent || '').trim();
                        if (t.startsWith('atr_') && !t.includes('•')) return t;
                    }
                    // 2) fallback: elemen <code> di dalam dialog apa pun
                    const dialog = document.querySelector('dialog');
                    if (dialog) {
                        for (const c of dialog.querySelectorAll('code, pre, input, textarea')) {
                            const t = (c.value || c.textContent || '').trim();
                            if (t.startsWith('atr_') && !t.includes('•') && t.length >= 10) return t;
                        }
                    }
                    // 3) fallback terakhir: elemen yang teksnya PERSIS satu key
                    for (const e of document.querySelectorAll('code, pre, span, div, p, input')) {
                        const t = (e.value || e.textContent || '').trim();
                        if (!t.startsWith('atr_') || t.includes('•')) continue;
                        if (t.length < 10) continue;
                        // harus murni key, bukan elemen pembungkus
                        if (/^atr_[A-Za-z0-9_\\-]+$/.test(t)) return t;
                    }
                    return null;
                }"""
            )
        except Exception:
            hasil = None

        if hasil and "•" not in hasil:
            return hasil

        time.sleep(1)

    return None
