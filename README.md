# Wiji

**Kelompok:** 12
**Kelas:** PBP-D 
**Tema:** Sustainable Living  
**Subtema:** Sustainable Soil and Land Management

## Application Overview

**Wiji** adalah platform web yang membantu petani dan pemilik lahan mengetahui kondisi tanah serta mendapatkan rekomendasi tanaman untuk pemeliharaan atau pemulihan tanah.

Pengguna dapat memasukkan hasil pemeriksaan yang sudah dimiliki. Jika datanya belum lengkap, pengguna dapat menjadwalkan pemeriksaan oleh petugas. Setelah hasil tersedia, sistem menganalisis kondisi tanah, cuaca, dan iklim untuk merekomendasikan tanaman yang sesuai.

Nama **Wiji** berasal dari bahasa Jawa yang berarti benih.

## Peran Pengguna

### Pemilik Lahan

Mendaftarkan lahan, memesan pemeriksaan, melihat hasil, mendapatkan rekomendasi tanaman, dan membuat rencana pengelolaan.

### Petugas Pemeriksa

Menerima jadwal, memperbarui status pemeriksaan, memasukkan hasil pemeriksaan, dan mengunggah dokumen laboratorium.

## Anggota Kelompok

1. Rania Fauziah Nur Wahyudi — 2506595070
2. Muhammad Osman Fardin — 2506541723
3. Nadya Sekar Kayrana — 2506607133
4. Yosua Peitho Purba — 2506657402
5. Piedra Ridwan Azra Pulungan — 2506623055

## Daftar Modul dan Pembagian

### Modul A — Manajemen Lahan

**Penanggung jawab:** Rania Fauziah Nur Wahyudi

CRUD data lahan yang mencakup nama, lokasi, luas, penggunaan, kondisi umum, dan foto.

### Modul B — Pemesanan Pemeriksaan

**Penanggung jawab:** Muhammad Osman Fardin

CRUD pemesanan yang mencakup lahan, jenis pemeriksaan, petugas, jadwal, dan status pemeriksaan.

### Modul C — Hasil Pemeriksaan Tanah

**Penanggung jawab:** Nadya Sekar Kayrana

CRUD hasil pemeriksaan yang mencakup pH, kelembapan, tekstur, unsur hara, kontaminan, dan dokumen laboratorium.

### Modul D — Katalog Tanaman

**Penanggung jawab:** Yosua Peitho Purba

CRUD informasi tanaman yang mencakup fungsi, kondisi tumbuh, kontaminan yang dapat ditangani, dan ketersediaannya.

### Modul E — Rekomendasi dan Rencana Pengelolaan

**Penanggung jawab:** Piedra Ridwan Azra Pulungan

Menampilkan rekomendasi tanaman berdasarkan kondisi lahan serta CRUD rencana pengelolaan yang dibuat pengguna.

## Fitur per Modul

- **Lahan (A):** daftar, tambah, ubah, arsip, pulihkan, dan hapus lahan. Pencarian lokasi dan peta lewat OpenStreetMap, cuaca dari Open-Meteo, iklim dari NASA POWER, foto lahan opsional.
- **Pemesanan pemeriksaan (B):** pemilik memesan pemeriksaan, mengubah usulan, minta jadwal ulang, atau membatalkan. Admin menugaskan petugas dan menjadwalkan. Petugas mengambil sampel dan memproses. Status berjalan satu arah (diajukan, dikonfirmasi, dijadwalkan, sampel diambil, diproses, selesai, atau dibatalkan) dan tiap perubahan tercatat di riwayat.
- **Hasil pemeriksaan (C):** hasil mandiri (dari laboratorium pemilik) dan hasil Wiji (diisi petugas, draf dulu lalu difinalkan). Unsur hara, temuan kontaminan, dokumen laboratorium privat, dan koreksi hasil final dengan riwayat.
- **Katalog tanaman (D):** dibaca publik tanpa login. Pencarian dan filter (tujuan lahan, jenis, prioritas lokal) lewat HTMX. Admin menambah, mengubah, mengarsipkan, atau menghapus tanaman. Tanaman yang sudah dipakai rekomendasi hanya bisa diarsipkan. Ada 53 tanaman awal beserta sumbernya.
- **Rekomendasi dan rencana (E):** rekomendasi dihitung dari hasil pemeriksaan final dan tujuan lahan. Rencana tanam bisa dibuat, diubah, dan dihapus.

## Aturan Keamanan Rekomendasi

Wiji sengaja berhati-hati supaya nggak merekomendasikan sesuatu yang berbahaya:

- Data kontaminan yang **kosong** dianggap belum diketahui, bukan aman. Hasil harus mencatat eksplisit "tidak terdeteksi" supaya rekomendasi otomatis jalan.
- Kontaminan yang terdeteksi menghentikan rekomendasi otomatis dan mengarahkan ke penilaian ahli.
- Tanaman pangan diblokir sampai keamanan konsumsinya terverifikasi dan bersumber.
- Tanaman invasif atau berisiko tinggi diblokir.
- Rekomendasi fitoremediasi hanya muncul kalau tanaman punya pasangan kontaminan dengan referensi literatur.

## Public API

API pihak ketiga yang dipakai:

- **OpenStreetMap/Nominatim:** peta dan pencarian lokasi  
  https://nominatim.org/release-docs/latest/api/Overview/
- **Open-Meteo:** data cuaca, suhu tanah, dan estimasi kelembapan  
  https://open-meteo.com/en/docs
- **NASA POWER:** data iklim historis  
  https://power.larc.nasa.gov/docs/services/api/

## Endpoint JSON Wiji

Semuanya hanya baca (GET) kecuali yang tertulis lain. Yang butuh login memakai sesi yang sama dengan halaman web: belum login dibalas 401, peran salah 403, dan data milik orang lain dibalas 404.

| Modul | Endpoint | Akses |
|---|---|---|
| Lahan | `/lahan/api/`, `/lahan/api/<id>/` | Pemilik, lahannya sendiri |
| Pesanan | `/pemeriksaan/api/pesanan/`, `/pemeriksaan/api/pesanan/<id>/` | Pemilik, pesanannya sendiri |
| Pesanan | `/pemeriksaan/api/pesanan/<id>/batalkan/`, `.../jadwal-ulang/` (POST) | Pemilik |
| Pesanan | `/pemeriksaan/api/pesanan/<id>/transition/` (POST) | Admin dan petugas yang ditugaskan |
| Hasil | `/hasil-tanah/api/hasil/`, `/hasil-tanah/api/hasil/<id>/` | Sama dengan izin halaman hasil: pemilik lahannya, petugas yang menangani, dan admin |
| Katalog | `/katalog/api/` (filter `q`, `tujuan`, `jenis`, `lokal`), `/katalog/api/<id>/` | Publik |
| Rencana | `/rekomendasi/api/rencana/` (filter `status`), `/rekomendasi/api/rencana/<id>/` | Pemilik, rencananya sendiri |
| Rekomendasi | `/rekomendasi/api/lahan/<id>/rekomendasi/?hasil=<id>&tujuan=<id>` | Pemilik, menghitung tanpa menyimpan |
| Rekomendasi | `/rekomendasi/api/lahan/<id>/hasil/` | Pemilik |

## Fitur Bersama

Autentikasi dengan peran (pemilik, petugas, admin), dashboard sesuai peran, tampilan responsif sampai lebar HP, filter dan pencarian dengan HTMX, integrasi API, halaman error 403, 404, dan 500, serta endpoint JSON.

## Teknologi

Django 5.2, SQLite, Tailwind CSS (CDN), HTMX, Leaflet (peta), Pillow (foto), WhiteNoise (file statis).

## Menjalankan Secara Lokal

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate            # sekalian mengisi 53 tanaman awal
python manage.py seed_demo          # data demo semua modul (opsional)
python manage.py createsuperuser    # akun admin (is_staff), kalau perlu
python manage.py runserver
```

Buka http://127.0.0.1:8000. Menjalankan test: `python manage.py test`.

Nggak perlu bikin file `.env` buat jalanin di lokal, pengaturan bawaannya sudah cukup. Kalau mau nimpa, bikin file `.env` sendiri (jangan di-commit).

### Data demo

`python manage.py seed_demo` mengisi akun, lahan, pesanan di semua status, hasil pemeriksaan (final, draf, mandiri, berkontaminan), dan rencana tanam. Aman dijalankan berulang, dan `--ulang` membuat data dari awal. Semua akun demo memakai kata sandi `demo-wiji-123`:

| Akun | Peran |
|---|---|
| `pemilik.demo` | Pemilik lahan |
| `admin.demo` | Admin |
| `petugas.bima`, `petugas.laras`, `petugas.dimas` | Petugas pemeriksa |

Akun demo cuma buat percobaan.

Akun petugas tidak bisa mendaftar sendiri. Admin membuatnya lewat `/admin/` dan memilih peran **Petugas Pemeriksa**.

## Deployment

Deployment otomatis lewat GitHub Actions (`.github/workflows/deploy.yml`) ke PWS UI:

1. Setiap Pull Request ke `main` dan setiap push ke `main` menjalankan `manage.py check` dan `manage.py test`.
2. Kalau tes lulus dan perubahannya masuk ke `main`, workflow mendorong kode ke branch `master` di PWS, yang membangun dan menjalankan aplikasinya.
3. Workflow membaca alamat PWS dari secret repositori `PWS_URL` (Settings, Secrets and variables, Actions). Kalau secret kosong, job berhenti dengan pesan yang jelas.

Migrasi database (termasuk 53 tanaman awal, tujuan pengelolaan, dan jenis pemeriksaan) berjalan lewat `python manage.py migrate`. File statis disajikan WhiteNoise, foto lahan disajikan Django lewat `/media/`.

## Struktur Proyek

| Folder | Isi |
|---|---|
| `accounts/` | Pengguna dengan peran (pemilik, petugas), login, dan daftar |
| `lands/` | Modul A: lahan, tujuan pengelolaan, peta, cuaca, dan iklim |
| `inspections/` | Modul B: pesanan pemeriksaan, status, jadwal, dan dashboard peran |
| `soil_results/` | Modul C: hasil pemeriksaan, unsur hara, kontaminan, dan dokumen |
| `core/` | Modul D: katalog tanaman, data awal, dan landing page |
| `recommendations/` | Modul E: aturan rekomendasi dan rencana pengelolaan |
| `dashboard/` | Dashboard pemilik |
| `templates/`, `static/` | Template dan aset bersama (`static/css/wiji.css` adalah sumber warna dan komponen) |
| `docs/` | Catatan domain, ERD, rencana kerja, dan AI disclosure |

## Kontribusi

- Satu branch per fitur dari `main` terbaru (misalnya `feat/...`, `fix/...`, `docs/...`).
- Pesan commit memakai gaya conventional commit (`feat:`, `fix:`, `test:`, `docs:`).
- Buka Pull Request ke `main` dengan judul dan deskripsi yang jelas, dan pastikan tes lulus.

## Pengujian

```bash
python manage.py test
```

Ada ratusan tes yang mencakup akses per peran, aturan status pesanan, validasi hasil, aturan keamanan rekomendasi, dan endpoint JSON. Setiap Pull Request ke `main` menjalankan tes lewat GitHub Actions, dan merge ke `main` otomatis dikirim ke PWS kalau tesnya lulus.

## Keterbatasan yang Diketahui

- Data 53 tanaman awal berisi rentang umum dari FAO EcoCrop, BBSDLP, dan ICRAF. Belum diverifikasi pakar, jadi nggak boleh dianggap acuan agronomi resmi.
- Tanaman pangan belum punya verifikasi keamanan konsumsi, jadi tujuan "Pangan keluarga" memberi sedikit rekomendasi otomatis.
- Fitoremediasi baru mencakup empat tanaman kandidat, dan hanya satu yang lolos aturan keamanan (akar wangi).
- Foto lahan dan dokumen laboratorium disimpan di disk server. Kalau disk tidak persisten, unggahan bisa hilang saat redeploy.
- Rekomendasi memakai aturan kata kunci sederhana (versi aturan `v1`), bukan model agronomi lengkap.
- Reset kata sandi belum ada.

## AI Disclosure

Analisis pemakaian AI dicatat per modul di folder [`docs/ai-disclosure/`](docs/ai-disclosure/), dengan format yang sama: tujuan penggunaan, strategi prompt, contoh prompt beserta peninjauannya, keterbatasan, dan pengecekan.

- [Modul B: Pemesanan Pemeriksaan](docs/ai-disclosure/modul-b.md)

Penanggung jawab modul lain menambahkan berkasnya sendiri di folder yang sama (`modul-a.md`, `modul-c.md`, `modul-d.md`, `modul-e.md`).

## Tautan

- Figma: https://www.figma.com/design/B4eTABpgEN98udSKNps3DU/Wiji
- Deployment PWS: https://muhammad-osman-wiji.pws.cs.ui.ac.id/
