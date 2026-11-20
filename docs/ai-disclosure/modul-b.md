# AI Disclosure: Modul B (Pemesanan Pemeriksaan)

**Penanggung jawab:** Muhammad Osman Fardin

Pengembangan Modul B, landing page, dashboard, dan beberapa pekerjaan lintas modul memakai **Claude Code (Anthropic)** sebagai alat bantu di terminal. AI tidak menjadi sumber kebenaran tunggal. Arah dan keputusan datang dariku, dan hasilnya selalu dibaca, dijalankan, dan dites sebelum dipakai.

## Alat yang dipakai

| Alat | Dipakai untuk |
|---|---|
| Claude Code (CLI) | Menulis dan menjalankan kode, tes, dan dokumen di repositori |
| Figma MCP | Membaca dan memperbarui desain di file Figma proyek |
| Claude in Chrome | Mencoba halaman di browser (tampilan HP, keyboard modal, pencarian katalog) |

## Tujuan penggunaan

- Memecah ketentuan tugas dan `docs/WORK-PLAN.md` menjadi tahap pengerjaan Modul B.
- Membuat rancangan awal model, aturan status, form, view, template, CSS, JavaScript, tes, dan data demo.
- Membuat demo HTML dan desain Figma sebelum dikodekan, supaya tampilan bisa dibandingkan dulu.
- Mengaudit hasil: syarat issue, tampilan HP, aksesibilitas, alur dari awal sampai akhir, dan kebocoran data antar-pengguna.
- Menyiapkan dokumentasi, termasuk deskripsi Pull Request.

## Strategi prompt

Setiap sesi dimulai dengan file catatan proyek (disimpan lokal) yang berisi aturan kerja, supaya aturan itu berlaku di sesi berikutnya. Aturan utamanya:

- Bahasa tulisan dan komentar kode santai dan singkat, penamaan model dan field memakai bahasa Indonesia sesuai kesepakatan tim.
- Perubahan status pesanan hanya lewat satu pintu (`inspections/services.py`).
- Aturan keamanan rekomendasi tidak boleh dilonggarkan untuk mengakali tes.

Prompt biasanya berupa tujuan singkat plus batasan, lalu kuarahkan lewat umpan balik (misalnya "terlalu besar", "kurang lega", "pakai yang versi 5 saja tapi logonya yang asli").

## Contoh penerapan

Contoh prompt di bawah ditulis ulang secara ringkas dari permintaan yang sebenarnya.

| Tujuan | Contoh prompt | Hasil bantuan AI | Peninjauan dan perbaikan manual |
|---|---|---|---|
| Perencanaan | Susun rencana pengerjaan landing page, login, dan daftar berdasarkan desain Figma dan dokumen proyek. | Rencana tahap, usulan Tailwind lewat CDN, struktur `base.html` dan `wiji.css`. | Kupilih Tailwind karena paling mudah buat tim. Komentar kode kuminta dibuat sederhana. |
| Penyiapan deployment | Pastikan foto lahan yang diunggah tetap tampil setelah aplikasi di-deploy, dan dokumen laboratorium tetap privat. | Rute `/media/` yang tetap jalan saat mode debug mati, dokumen privat tidak lewat rute itu, dan tes unggah foto. | Hasilnya dicek lewat tes otomatis, dan aturan akses dokumen tetap mengikuti izin halaman. |
| Desain antarmuka | Buat demo dashboard pemilik lahan dengan referensi dari empat desain dashboard ini. | Demo HTML, lalu implementasi dan pemindahan ke Figma. | Ukuran dikecilkan dua kali, warna dan jarak diubah, dan satu versi landing kuganti dengan versi lain. |
| Modul B | Kerjakan Modul B per tahap: model, aturan status, halaman pemilik, admin, petugas, dashboard, dan endpoint JSON, lengkap dengan tes. | Kode dan tes tiap tahap. Perubahan status hanya lewat satu pintu (`inspections/services.py`). | Halaman dicoba di browser dan hasil tes dibaca sebelum dipakai. |
| Perbaikan bug | Dashboard menampilkan "4 lahan terdaftar" tapi halaman lahan kosong. Cari penyebabnya dan perbaiki. | Penelusuran sumber angka dan penyambungan dashboard ke data asli. | Hasil dicek ulang dengan data demo. |
| Integrasi tim | Tinjau branch hasil pemeriksaan milik Modul C terhadap syarat issue 08. | Review di salinan sementara, seluruh tes dijalankan, dan dicocokkan dengan syarat issue. | Temuan jadi bahan untuk kusampaikan ke pemilik modulnya, kodenya tidak kuubah. |
| Data awal | Siapkan minimal 50 tanaman awal beserta sumbernya, dimuat otomatis saat migrate. | Draf 53 tanaman, migrasi data, perintah seed, dan tes. | Isinya belum diverifikasi ke sumber aslinya dan perlu dicek penanggung jawab Modul D. |
| Pengujian | Uji alur lengkap pemilik dan petugas dari awal sampai rencana tanam, termasuk kebocoran data antar-pengguna. | Skrip alur lewat HTTP dan daftar hasil pemeriksaan. | Hasil kubaca dan temuan kecil (label foto) kuperbaiki. |

## Keterbatasan dan perbaikan manual

- **Desain Figma berantakan di awal.** AI menyusun halaman Figma tanpa mengambil dari demo yang sudah dibuat, jadi kuhentikan dan kuminta diulang dari awal. Aku juga yang memutuskan layar mana yang dihapus.
- **Pengecekan tampilan HP baru ketemu belakangan.** Dashboard meluap ke samping di 390px dan baru ketahuan saat audit.
- **Perubahan di modul lain bisa merusak tes teman.** Data awal tanaman membuat tiga tes Modul E gagal karena tes itu mengira katalog kosong. Diperbaiki dengan satu baris di `setUp`, dan perubahan itu kusampaikan ke pemilik modulnya.
- **AI belum tahu perubahan teman sebelum di-pull.** Sebelum membuat sesuatu yang bersinggungan, kami pull dulu dan kode teman dibaca ulang.
- **Data tanaman awal belum diverifikasi.** Rentang pH dan iklim berasal dari pengetahuan umum (FAO EcoCrop, BBSDLP, ICRAF), bukan dibaca dari sumber aslinya satu per satu.
- **AI bisa salah menebak.** Misalnya tes yang kutulis di skrip alur sempat menguji pengguna yang salah (admin, bukan pemilik lain). Ketahuan dari hasilnya dan diperbaiki sebelum dipakai.

## Pengecekan

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Setiap Pull Request menjalankan tes otomatis lewat GitHub Actions. Saat audit terakhir, 565 tes seluruh proyek lulus. Coverage seluruh proyek sekitar 89%, dan coverage app `inspections` 99%.
