# IDB Room — Sistem Reservasi Ruangan Kampus IDB Bali

Aplikasi web responsif untuk mengajukan, memantau, dan menyetujui peminjaman ruangan kampus. Dibangun dari **PRD Reservasi Peminjaman Ruangan Kampus IDB Bali v1.0**.

Logo dan foto gedung pada halaman login memakai aset yang diberikan pengguna (foto dipotong ke bagian gedung kampus). Desain login mengacu pada halaman SSO SINERGY IDB Bali (biru `#044C71`, aksen oranye, panel terbelah), lalu diterjemahkan menjadi sistem desain sendiri: **Campus Modernist** — Source Serif 4 untuk judul, Source Sans 3 untuk antarmuka, papan jadwal sebagai elemen pengingat utama.

## Menjalankan

Prasyarat: **Python 3.9+** (tanpa Node/npm).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Mode debug hanya jika diperlukan: `FLASK_DEBUG=1 python app.py`.

Buka <http://127.0.0.1:5001>. Server mendengarkan di `0.0.0.0:5001`, sehingga perangkat lain di jaringan yang sama dapat membuka **`http://<IP-lokal>:5001`**.

Cek IP lokal (macOS):

```bash
ipconfig getifaddr en0
```

Jika muncul dialog firewall macOS, izinkan koneksi masuk untuk Python agar perangkat lain bisa mengakses. Port/host dapat diubah lewat env `PORT` dan `IDB_HOST`.

Database SQLite dan data awal dibuat otomatis di `instance/idb_room.sqlite` saat pertama dijalankan.

Alternatif menjalankan server:

```bash
FLASK_APP=app .venv/bin/flask run --host=0.0.0.0 --port 5001
```

### Akun demo

| Peran | Nama | Email | Kata sandi |
|---|---|---|---|
| Mahasiswa | Kean Azkara | `kean.azkara@idbbali.ac.id` | `123456` |
| Dosen | Tania Moona | `tania.moona@idbbali.ac.id` | `tania124` |
| Admin | Admin Kampus | `admin@idbbali.ac.id` | `idbbali123` |

Akun mahasiswa lain tersedia untuk data contoh (mis. `ayu.lestari@idbbali.ac.id`, `yoga.pratama@idbbali.ac.id`) dengan kata sandi `idb2026`. Login juga menerima username internal (mis. `kean`, `tania`) untuk kompatibilitas.

Data awal juga memuat contoh dari PRD (Aula, 20 November 2026: 09.00–11.00 disetujui dan 10.00–12.00 menunggu — terdeteksi bentrok di antrean admin).

## Fitur yang tersedia

- Login email mahasiswa, dosen, dan admin, sesi aman, CSRF pada semua form.
- Dashboard peminjam: ringkasan status, jadwal terdekat, ruangan tersedia sekarang, agenda kampus hari ini.
- 29 ruangan + opsi **Lainnya** (nama ruangan bebas) untuk mahasiswa dan dosen.
- Papan jadwal per ruangan dengan penanda waktu sekarang, status disetujui/menunggu/dipakai/selesai.
- Kalender bulanan seluruh kampus dengan filter ruangan dan agenda per tanggal.
- Formulir reservasi dengan jenis peminjam (mahasiswa/dosen), NIM atau NIDN/NIP, validasi tanggal/jam, jam operasional, durasi, serta pemeriksaan bentrok langsung (AJAX) + pemeriksaan ulang di server.
- Pencegahan bentrok terhadap reservasi **disetujui dan yang masih menunggu**, termasuk jeda pergantian yang dapat diatur admin.
- Persetujuan/penolakan admin dengan catatan, pemeriksaan ulang konflik saat menyetujui, dan pemblokiran persetujuan ganda.
- Pembatalan oleh pemohon/admin dengan dialog konfirmasi dan batas waktu yang dapat diatur.
- Riwayat status (audit trail) per reservasi, notifikasi dalam aplikasi.
- Admin: antrean persetujuan dengan penanda konflik, daftar semua reservasi dengan pencarian/filter, kelola ruangan, kelola akun mahasiswa/dosen (aktif/nonaktif, reset sandi, pencarian), pengaturan aturan reservasi.
- Empty state, loading state, error state, validasi inline, dan fokus keyboard di seluruh alur.

## Aturan bisnis yang diterapkan

| Aturan | Implementasi |
|---|---|
| Bentrok jadwal | Overlap `[mulai, selesai)` + jeda; diperiksa saat pengajuan dan saat persetujuan |
| Pengajuan menunggu | Menahan slot dan diperiksa seperti reservasi disetujui |
| Bentrok saat persetujuan | Disetujui hanya jika tidak ada konflik disetujui **dan** tidak ada pengajuan menunggu lain di slot sama |
| Pembatalan | Sebelum jam mulai; batas H-X jam dapat diatur |
| Status lampau | Reservasi disetujui otomatis tampil **Selesai** setelah jam selesai |
| Ruangan nonaktif | Tidak muncul di form, riwayat tetap tersimpan |

## Asumsi yang diambil (PRD menandai perlu konfirmasi)

- Akun dibuat oleh admin; tidak ada pendaftaran mandiri.
- Jeda pergantian default **0 menit**; jam operasional **07.00–22.00 WITA**; pengajuan maksimal **180 hari**; durasi **30 menit–8 jam**.
- Pembatalan diizinkan sampai sebelum jam mulai (batas dapat diubah admin).
- Notifikasi MVP berupa notifikasi dalam aplikasi (bukan WhatsApp/email).
- Zona waktu seluruh sistem: **WITA (Asia/Makassar, UTC+8)**.
- Admin tidak membuat pengajuan; admin meninjau, menyetujui, dan mengelola akun.

Semua nilai di atas dapat diubah di **Admin → Pengaturan**.

## Struktur proyek

```
app.py              rute, autentikasi, CSRF, template filters
database.py         skema SQLite, koneksi, perintah CLI
seed.py             akun mahasiswa/dosen, 29 ruangan, akun demo, reservasi contoh
services.py         aturan bentrok, status, kalender, transaksi, audit, notifikasi
templates/          Jinja: login, dashboard, ruangan, kalender, reservasi, admin
static/css/app.css  token desain, komponen, responsif 1440/900/390
static/js/app.js    dialog, cek ketersediaan AJAX, password toggle, konfirmasi
instance/           database + secret key (tidak di-commit)
```

## Verifikasi

Jalankan uji otomatis:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

- Semua halaman utama diuji dengan `agent-browser` pada **1440×900** dan **390×844**.
- Audit axe-core (`agent-browser a11y --tags wcag2a,wcag2aa`) pada halaman login, dashboard, ruangan, detail ruangan, form, detail reservasi, dan admin.
- Alur yang diuji: login, pengajuan bentrok ditolak, pengajuan valid tersimpan, persetujuan konflik diblokir, persetujuan valid, penolakan dengan catatan, pembatalan, notifikasi, ruangan "Lainnya", filter kalender/daftar.
- Uji otomatis `tests/test_core.py` mencakup autentikasi (termasuk login email), contoh bentrok PRD, penolakan pengajuan bentrok, persetujuan valid + notifikasi, aturan jeda, dan header keamanan.
- Contrast token diperiksa manual (teks ≥ 4.5:1, UI ≥ 3:1).

## Reset data

```bash
FLASK_APP=app .venv/bin/flask reset-db
```

atau hapus `instance/idb_room.sqlite` lalu jalankan ulang aplikasi.

## Catatan produksi

- Jalankan di belakang HTTPS dan set `SESSION_COOKIE_SECURE=1` (tambahkan pada konfigurasi).
- Matikan `debug` (gunakan `flask run`/server WSGI seperti Gunicorn atau Waitress, bukan `python app.py`).
- Ganti kata sandi demo dan atur `IDB_SECRET_KEY` dari secret manager.
- Cadangkan `instance/idb_room.sqlite`; pertimbangkan PostgreSQL untuk beban banyak pengguna.
- Tambahkan rate limiting login, email/WhatsApp, reservasi berulang, dan laporan statistik pada tahap berikutnya sesuai PRD.
