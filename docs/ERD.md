# ERD Wiji

Diagram ini menjadi acuan awal hubungan data utama Wiji untuk memulai development. Jika kebutuhan implementasi berubah, relasi dapat diperbarui bersama melalui pull request.

```mermaid
erDiagram
    USER ||--o{ LAND : memiliki
    USER o|--o{ PESANAN_PEMERIKSAAN : ditugaskan

    LAND }o--o{ MANAGEMENT_GOAL : mempunyai
    LAND ||--o{ PESANAN_PEMERIKSAAN : dipesankan
    LAND ||--o{ SOIL_RESULT : diperiksa
    LAND ||--o{ RECOMMENDATION_SNAPSHOT : direkomendasikan
    LAND ||--o{ MANAGEMENT_PLAN : direncanakan

    JENIS_PEMERIKSAAN ||--o{ PESANAN_PEMERIKSAAN : dipilih_untuk
    PESANAN_PEMERIKSAAN o|--o| SOIL_RESULT : menghasilkan
    PESANAN_PEMERIKSAAN ||--o{ RIWAYAT_PESANAN : mencatat
    USER ||--o{ RIWAYAT_PESANAN : melakukan

    SOIL_RESULT ||--o{ NUTRIENT_MEASUREMENT : memuat
    SOIL_RESULT ||--o{ CONTAMINANT_FINDING : memuat
    SOIL_RESULT ||--o{ RECOMMENDATION_SNAPSHOT : menjadi_dasar

    CONTAMINANT_TYPE ||--o{ CONTAMINANT_FINDING : ditemukan_sebagai
    CONTAMINANT_TYPE ||--o{ PLANT_CONTAMINANT_CAPABILITY : ditangani_oleh

    PLANT }o--o{ MANAGEMENT_GOAL : mendukung
    PLANT ||--o{ PLANT_REFERENCE : memiliki
    PLANT ||--o{ PLANT_CONTAMINANT_CAPABILITY : mempunyai
    PLANT ||--o{ RECOMMENDATION_SNAPSHOT : terpilih

    MANAGEMENT_GOAL ||--o{ RECOMMENDATION_SNAPSHOT : menjadi_tujuan
    RECOMMENDATION_SNAPSHOT ||--o| MANAGEMENT_PLAN : disimpan_sebagai
    USER ||--o{ MANAGEMENT_PLAN : membuat
```

## Kepemilikan Model

| Bagian | Model yang Dimiliki |
|---|---|
| Akun dan fitur bersama | `User` dan role pengguna |
| Modul A — Manajemen Lahan | `Land`, `ManagementGoal` |
| Modul B — Pemesanan Pemeriksaan | `JenisPemeriksaan`, `PesananPemeriksaan`, `RiwayatPesanan` |
| Modul C — Hasil Pemeriksaan | `SoilResult`, `NutrientMeasurement`, `ContaminantFinding` |
| Modul D — Katalog Tanaman | `Plant`, `PlantReference`, `ContaminantType`, `PlantContaminantCapability` |
| Modul E — Rekomendasi dan Rencana | `RecommendationSnapshot`, `ManagementPlan` |

## Hubungan Utama

- Satu pemilik dapat mempunyai banyak lahan.
- Satu lahan dapat mempunyai banyak pemesanan sepanjang waktu, tetapi hanya satu yang aktif pada saat yang sama.
- Satu pemesanan menghasilkan maksimal satu hasil pemeriksaan.
- Hasil mandiri tetap terhubung ke lahan, tetapi tidak harus mempunyai pemesanan.
- Satu hasil dapat memiliki beberapa pengukuran unsur hara dan temuan kontaminan.
- Satu tanaman dapat mendukung beberapa tujuan pengelolaan.
- Kemampuan fitoremediasi menghubungkan tanaman dengan jenis kontaminan tertentu.
- Satu snapshot rekomendasi memakai satu lahan, hasil pemeriksaan, tujuan utama, dan tanaman.
- Satu snapshot dapat disimpan menjadi maksimal satu rencana pengelolaan.
- `ContaminantType` dimiliki Modul D dan digunakan Modul C sebagai data referensi.
- Relasi pesanan ke lahan memakai `related_name='inspection_orders'` karena aturan arsip dan hapus lahan (Modul A) membaca nama itu. Nilai status disimpan huruf kecil (`selesai`, `dibatalkan`).
- `PesananPemeriksaan` tidak menyimpan pemilik secara langsung. Pemilik pesanan dibaca dari `Land.owner`, sedangkan relasi ke `User` di pesanan adalah petugas yang ditugaskan.
- `PesananPemeriksaan` menyimpan jadwal usulan (tanggal dan sesi dari pemilik) dan jadwal final (dari admin, kosong sampai `Dijadwalkan`).
- Setiap perubahan penting pada pesanan dicatat sebagai satu `RiwayatPesanan`: perubahan status, penjadwalan ulang, dan pergantian petugas. Event menyimpan status sebelum dan sesudah, pelaku, catatan atau alasan, serta waktunya. Untuk penjadwalan ulang, event juga menyimpan tanggal lama dan baru.
- `JenisPemeriksaan` dikelola admin dan diisi awal dengan tiga jenis bertingkat: Dasar, Unsur Hara, dan Kontaminan. Jenis ini menentukan data wajib saat Modul C memfinalkan hasil.
- Modul C tidak mengubah status pesanan secara langsung. Saat hasil difinalkan, Modul C memanggil fungsi transisi Modul B untuk mengubah pesanan dari `Diproses` ke `Selesai`.
- Data yang sudah mempunyai riwayat atau relasi penting diarsipkan dan tidak dihapus permanen.
