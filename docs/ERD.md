# ERD Wiji

Diagram ini menjadi acuan awal hubungan data utama Wiji untuk memulai development. Jika kebutuhan implementasi berubah, relasi dapat diperbarui bersama melalui pull request.

```mermaid
erDiagram
    USER ||--o{ LAND : memiliki
    USER o|--o{ INSPECTION_ORDER : ditugaskan

    LAND }o--o{ MANAGEMENT_GOAL : mempunyai
    LAND ||--o{ INSPECTION_ORDER : dipesankan
    LAND ||--o{ SOIL_RESULT : diperiksa
    LAND ||--o{ RECOMMENDATION_SNAPSHOT : direkomendasikan
    LAND ||--o{ MANAGEMENT_PLAN : direncanakan

    INSPECTION_TYPE ||--o{ INSPECTION_ORDER : dipilih_untuk
    INSPECTION_ORDER o|--o| SOIL_RESULT : menghasilkan

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
| Modul B — Pemesanan Pemeriksaan | `InspectionType`, `InspectionOrder` |
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
- Data yang sudah mempunyai riwayat atau relasi penting diarsipkan dan tidak dihapus permanen.
