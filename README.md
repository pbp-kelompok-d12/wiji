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

## Public API

- **OpenStreetMap/Nominatim:** peta dan pencarian lokasi  
  https://nominatim.org/release-docs/latest/api/Overview/
- **Open-Meteo:** data cuaca, suhu tanah, dan estimasi kelembapan  
  https://open-meteo.com/en/docs
- **NASA POWER:** data iklim historis  
  https://power.larc.nasa.gov/docs/services/api/

## Fitur Bersama

Autentikasi, dashboard, tampilan responsif, filter data, AJAX/HTMX, integrasi API, dan endpoint JSON.

## Tautan

- Figma: [Belum tersedia]
- Deployment PWS: [Belum tersedia]
