# Istilah dan Arah Wiji

Ini rangkuman istilah dan beberapa arah utama Wiji yang sudah disepakati bersama kelompok.

## Istilah

| Istilah | Arti |
|---|---|
| **Pemilik Lahan** | Orang yang mendaftarkan dan mengelola data lahannya di Wiji. |
| **Petugas Pemeriksa** | Petugas yang menangani pesanan dan mengisi hasil pemeriksaan. |
| **Lahan** | Area yang mau diperiksa dan dicarikan rekomendasi tanamannya. |
| **Pemesanan Pemeriksaan** | Permintaan untuk memeriksa kondisi tanah di suatu lahan. |
| **Jenis Pemeriksaan** | Layanan yang dipilih saat memesan, misalnya Dasar, Unsur Hara, atau Kontaminan. Dikelola admin. |
| **Pesanan Aktif** | Pesanan yang statusnya belum `Selesai` atau `Dibatalkan`. Satu lahan hanya boleh punya satu pesanan aktif. |
| **Penjadwalan Ulang** | Permintaan pemilik untuk mengganti tanggal pemeriksaan setelah pesanan dikonfirmasi. |
| **Dibatalkan** | Status akhir pesanan yang dibatalkan. Pesanan tetap disimpan sebagai riwayat dan tidak bisa dibuka lagi. |
| **Hasil Mandiri** | Hasil pemeriksaan dari luar Wiji yang dimasukkan sendiri oleh pemilik lahan. |
| **Hasil Wiji** | Hasil yang dimasukkan petugas lewat simulasi pemeriksaan di Wiji. |
| **Data Lingkungan** | Data cuaca dan iklim dari lokasi lahan sebagai informasi tambahan. |
| **Katalog Tanaman** | Kumpulan informasi tanaman, kebutuhan tumbuh, manfaat, risiko, dan sumbernya. |
| **Jalur Pemeliharaan** | Rekomendasi tanaman untuk menjaga atau memperbaiki kondisi tanah. |
| **Jalur Pemulihan** | Rekomendasi terbatas untuk tanah yang punya kontaminan tertentu. |
| **Rekomendasi** | Hasil pencocokan kondisi tanah, tujuan pengguna, lingkungan, dan data tanaman. |
| **Skor Kecocokan** | Nilai 0–100 untuk membandingkan tanaman. Nilai ini bukan jaminan tanaman akan berhasil. |
| **Rencana Pengelolaan** | Rencana yang disimpan pengguna setelah memilih tanaman dari hasil rekomendasi. |
| **Arsip** | Data yang sudah tidak aktif, tetapi tetap disimpan supaya riwayatnya tidak hilang. |

## Arah yang Disepakati

### 1. Pemeriksaannya berupa simulasi

Alur pemesanan dan pemeriksaan dibuat untuk kebutuhan tugas. Jadi, Wiji tidak benar-benar menjanjikan kunjungan petugas atau layanan laboratorium.

### 2. Fokus utamanya pemeliharaan tanah

Fitur utamanya membantu menjaga atau memperbaiki kondisi tanah. Fitoremediasi tetap ada, tetapi dibatasi ke beberapa tanaman dan kontaminan yang sumbernya jelas.

### 3. Hasil dari pengguna dan petugas dibedakan

Hasil yang dimasukkan pemilik lahan dibedakan dari hasil yang dicatat petugas. Asal datanya perlu terlihat supaya pengguna tidak menganggap keduanya sama.

### 4. Cara membuat rekomendasinya harus jelas

Rekomendasi dibuat dengan aturan dan skor yang bisa dijelaskan, bukan model AI yang perlu dilatih. Kalau risikonya tinggi, Wiji tidak memberi rekomendasi otomatis dan menyarankan pengguna mencari bantuan ahli.

### 5. Status pesanan dan siapa yang mengubahnya

Pesanan punya tujuh status: `Diajukan`, `Dikonfirmasi`, `Dijadwalkan`, `Sampel Diambil`, `Diproses`, `Selesai`, dan `Dibatalkan`.

| Perubahan | Dilakukan oleh |
|---|---|
| `Diajukan → Dikonfirmasi` | Admin, saat menugaskan petugas |
| `Dikonfirmasi → Dijadwalkan` | Admin, saat menetapkan tanggal final |
| `Dijadwalkan → Sampel Diambil → Diproses` | Petugas yang ditugaskan |
| `Diproses → Selesai` | Otomatis saat hasil pemeriksaan difinalkan di Modul C |

Pemilik tidak memajukan status. Semua perubahan status lewat satu fungsi transisi di Modul B, termasuk dari Modul C. Modul lain tidak mengubah kolom status secara langsung.

### 6. Mengubah, menjadwalkan ulang, dan membatalkan pesanan

- Saat masih `Diajukan`, pemilik bebas mengubah tanggal usulan dan catatan.
- Saat `Dikonfirmasi` atau `Dijadwalkan`, pemilik bisa meminta penjadwalan ulang dengan tanggal baru dan alasan. Status kembali ke `Dikonfirmasi`, petugas tetap sama, tanggal final dikosongkan, lalu admin menetapkan jadwal baru. Tidak ada batas jumlah penjadwalan ulang.
- Pesanan menyimpan dua pasang jadwal: jadwal usulan dari pemilik dan jadwal final dari admin. Jadwal final masih kosong sampai status `Dijadwalkan`.
- Admin bisa mengganti petugas sebelum `Sampel Diambil`. Statusnya tidak berubah.
- Pemilik bisa membatalkan pesanan yang masih `Diajukan`, `Dikonfirmasi`, atau `Dijadwalkan` dengan alasan. Admin juga bisa membatalkan. Siapa, kapan, dan alasannya disimpan.
- Mulai `Sampel Diambil`, pesanan tidak bisa dijadwalkan ulang atau dibatalkan.
- Pesanan tidak pernah dihapus permanen. Status `Dibatalkan` menjadi bentuk *soft delete* (sudah dikonfirmasi asisten dosen).

### 7. Syarat membuat pesanan

- Lahan harus milik pemesan, sudah punya koordinat, dan tidak diarsipkan. Kalau koordinat belum ada, pemilik diarahkan melengkapi lahan dulu.
- Lahan tidak sedang punya pesanan aktif.
- Jenis pemeriksaan yang bisa dipilih hanya yang masih aktif.
- Jadwal usulan berupa tanggal dan sesi (Pagi atau Siang), paling cepat besok dan paling lambat 30 hari ke depan. Ketersediaan petugas tidak dicek karena pemeriksaannya simulasi.
- Lahan yang sudah pernah punya pesanan hanya bisa diarsipkan, tidak dihapus.
- Lahan yang masih punya pesanan aktif tidak bisa diarsipkan. Pemilik perlu membatalkan pesanannya dulu.

### 8. Riwayat dan akses pesanan

- Setiap perubahan penting dicatat sebagai riwayat: perubahan status, penjadwalan ulang beserta tanggal lama dan baru, serta pergantian petugas. Riwayat menyimpan siapa yang mengubah, catatan atau alasan, dan waktunya, lalu ditampilkan sebagai linimasa di detail pesanan.
- Admin mengelola pesanan lewat halaman staf di Wiji, bukan dengan mengubah status langsung di Django Admin. Di Django Admin, status hanya bisa dibaca.
- Pemilik hanya melihat pesanan untuk lahannya, petugas hanya melihat pesanan yang ditugaskan kepadanya, dan admin melihat semuanya. Pengunjung yang belum masuk tidak melihat pesanan apa pun.
- Petugas melihat nama, alamat, dan koordinat lahan, jenis pemeriksaan, jadwal final, catatan pemilik, dan nama pemilik. Email dan data kontak pemilik tidak ditampilkan.
- Halaman HTML dan endpoint JSON memakai aturan akses dan fungsi transisi yang sama.
- Wiji tidak mengirim email atau notifikasi real-time. Perubahan pesanan terlihat lewat pesan setelah aksi dan kartu di dashboard.

### 9. Hubungan pesanan dengan hasil pemeriksaan

Bagian ini masih perlu disepakati dengan penanggung jawab Modul C.

- Jenis pemeriksaan bersifat bertingkat, jadi setiap Hasil Wiji selalu punya data minimum untuk rekomendasi:

| Jenis | Data wajib saat finalisasi |
|---|---|
| Dasar | pH, tekstur, kelembapan, dan bahan organik |
| Unsur Hara | Data Dasar dan minimal satu pengukuran unsur hara |
| Kontaminan | Data Dasar dan bagian kontaminan yang terisi, boleh berisi "tidak terdeteksi" |

- Petugas baru bisa membuat draf hasil ketika pesanan berstatus `Diproses`.
- Pemilik tetap bisa memasukkan Hasil Mandiri walaupun lahannya punya pesanan aktif. Pesanan tidak dibatalkan otomatis, dan pemilik memilih sendiri hasil yang dipakai untuk rekomendasi.
