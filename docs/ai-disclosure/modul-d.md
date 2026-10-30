# AI Disclosure: Modul D (Katalog Tanaman)

**Penanggung jawab**: Yosua Peitho Purba

Pengembangan Modul D, khususnya perancangan model database (CRUD Tanaman) dan integrasi relasi antar-modul, memakai Google Gemini (chat) sebagai asisten diskusi dan pair-programmer. AI tidak menjadi sumber kebenaran tunggal. Arah dan keputusan akhir, adaptasi terhadap kode milik teman sekelompok, serta eksekusi pengujian manual di Django Admin selalu dilakukan dan diverifikasi sendiri sebelum di-push ke repositori.

## Alat yang dipakai

- **Google Gemini(Chat)** dipakai untuk Mendiskusikan struktur model Django, memberikan saran apa yang harus dilakukan, panduan troubleshooting error, dan perintah Git.

## Tujuan Penggunaan

- Memetakan ulang requirements dari dokumen ERD gabungan menjadi langkah kerja yang spesifik untuk Modul D.
- Membantu menyusun sintaks Python/Django untuk model-model baru (ContaminantType, PlantReference, PlantContaminantCapability) dan pembuatan relasi Many-to-Many maupun One-to-Many.
- Mencari solusi secara cepat untuk error operasional, seperti masalah autentikasi Superuser, halaman 404 pada navigasi URL, dan error pada saat push ke GitHub.
- Menyiapkan urutan perintah Git yang aman agar pekerjaan lokal tidak merusak atau bentrok dengan kode teman kelompok lain (workflow sinkronisasi).


## Strategi Prompt

Setiap sesi dimulai dengan memberikan konteks posisi kode saat ini dan kendala yang dihadapi. Aturan dan strategi utamanya meliputi:

- Berbasis Dokumen Acuan: Menyertakan salinan teks asli ERD Wiji ke dalam prompt agar AI memberikan saran relasi yang akurat dengan modul lain (seperti relasi dengan ManagementGoal dari Modul A).
- Berbasis Visual (Screenshot): Memberikan tangkapan layar ketika menghadapi error di antarmuka browser (misal: tulisan merah saat login atau halaman Page not found) agar AI memahami letak kesalahan dengan cepat.
- Pendekatan Bertahap: Meminta panduan dalam bentuk urutan (step-by-step) mulai dari penulisan models.py, pendaftaran ke admin.py, hingga perintah terminal, supaya perubahan bisa dikontrol.


## Contoh Penerapan

## Contoh penerapan

Contoh prompt di bawah ditulis ulang secara ringkas dari permintaan yang sebenarnya.

| Tujuan | Contoh prompt | Hasil bantuan AI | Peninjauan dan perbaikan manual |
|---|---|---|---|
| Implementasi Model dari ERD | "Jujur gua bingung... ERD-nya disuruh gini (menyertakan teks ERD lengkap). Sebenarnya ini udah bener gasi?" | Penjelasan posisi Modul D dalam ERD, dan usulan sintaks pada kelas `ContaminantType`, `PlantReference`, dsb beserta relasinya. | Kode dimodifikasi sesuai keiinginan. Impor modul disesuaikan dengan struktur nama *app* milik teman (`lands.ManagementGoal`). |
| Troubleshooting Git Push | "Malah gini... (screenshot pesan error: `src refspec feature/... does not match any`)" | Arahan untuk menggunakan jalan pintas `git push -u origin HEAD` dan pengecekan status *branch*. | Status *branch* dicek manual, lalu perintah *push* dijalankan ulang hingga sukses. |
| Pengujian Relasi via Admin | "Lalu cara gua cek gimana?" | Panduan mendaftarkan model ke `admin.py` dan alur *testing* tambah data beserta relasinya di halaman Admin. | Pendaftaran dilakukan, lalu pengujian relasi (*dropdown* pilihan tujuan pengelolaan & referensi) diisi dan divalidasi langsung secara manual. |

## Keterbatasan dan Perbaikan manual 

- AI tidak memiliki konteks kode teman kelompok secara otomatis. Saat menyambungkan relasi Many-to-Many, AI membuat perkiraan nama aplikasi teman. Saya harus menarik kode teman (via pull), membaca file models.py milik teman untuk memastikan nama app adalah lands dan modelnya ManagementGoal, lalu menyesuaikan kode yang diberikan AI sebelum disimpan.
- Risiko redundansi database (Normalisasi). Setelah AI membantu membuatkan tabel khusus untuk relasi Kontaminan dan Referensi yang lebih rapi, ada beberapa field teks lama di model utama (Tanaman) yang fungsinya menjadi tumpang tindih. Saya harus mengambil inisiatif untuk melakukan comment atau menghapus field lama tersebut agar database tetap ternormalisasi dengan baik.
- AI belum bisa membedakan isi data secara mandiri. Saat melakukan pengujian di Django Admin untuk menguji form PlantReference, pengisian field sumber literatur awalnya menggunakan nama tanaman secara berulang. Saya harus memperbaiki pemahaman pengisian datanya secara manual agar diisi dengan nama buku/jurnal yang masuk akal.

