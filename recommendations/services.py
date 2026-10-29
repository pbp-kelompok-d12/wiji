from dataclasses import dataclass
from typing import Any

from .environment import fetch_environmental_data
from core.models import Tanaman


RULE_VERSION = "v1"

# Enam kategori data yang digunakan untuk menghitung kelengkapan.
# Ini adalah kebijakan awal aplikasi, bukan standar laboratorium.
DATA_CATEGORIES = (
    "ph",
    "kelembapan",
    "tekstur",
    "bahan_organik",
    "unsur_hara",
    "kontaminan",
)

MINIMUM_DATA_CATEGORIES = 2

# Kata-kata ini menandakan risiko yang perlu memblokir
# rekomendasi otomatis sampai ada penilaian lebih lanjut.
HIGH_RISK_TERMS = (
    "beracun",
    "invasif",
    "berbahaya",
    "risiko tinggi",
    "tidak aman",
    "jangan dikonsumsi",
    "tidak boleh dikonsumsi",
    "toxic",
    "high risk",
)

# Hubungan tujuan dengan fungsi tanaman dibuat eksplisit
# supaya alasannya dapat dijelaskan kepada pengguna.
GOAL_GROUPS = {
    "organik_hara": {
        "goal_terms": (
            "organik",
            "hara",
            "nutrien",
            "kesuburan",
            "pupuk",
        ),
        "plant_terms": (
            "organik",
            "hara",
            "nutrien",
            "kesuburan",
            "pupuk",
        ),
    },
    "erosi": {
        "goal_terms": ("erosi", "konservasi"),
        "plant_terms": (
            "erosi",
            "konservasi",
            "penutup tanah",
            "akar kuat",
            "perakaran",
        ),
    },
    "kontaminan": {
        "goal_terms": (
            "kontaminan",
            "pencemaran",
            "remediasi",
            "fitoremediasi",
            "logam berat",
            "polutan",
        ),
        "plant_terms": (
            "kontaminan",
            "pencemaran",
            "remediasi",
            "fitoremediasi",
            "logam berat",
            "polutan",
        ),
    },
    "air": {
        "goal_terms": (
            "kelembapan",
            "drainase",
            "kekeringan",
            "pengelolaan air",
        ),
        "plant_terms": (
            "kelembapan",
            "drainase",
            "kekeringan",
            "pengelolaan air",
        ),
    },
}


class RecommendationInputError(ValueError):
    """Input belum memenuhi syarat untuk menghitung rekomendasi."""


@dataclass
class RecommendationCandidate:
    tanaman: Tanaman
    skor: int
    alasan: list[str]
    kelengkapan_data: int
    input_snapshot: dict[str, Any]
    data_lingkungan: dict[str, Any]
    versi_aturan: str = RULE_VERSION


def _soil_data_status(hasil_pemeriksaan):
    has_nutrients = hasil_pemeriksaan.nutrient_measurements.exists()

    values = {
        "ph": hasil_pemeriksaan.ph is not None,
        "kelembapan": hasil_pemeriksaan.kelembapan is not None,
        "tekstur": bool(hasil_pemeriksaan.tekstur.strip()),
        "bahan_organik": hasil_pemeriksaan.bahan_organik is not None,
        "unsur_hara": has_nutrients or bool(
            hasil_pemeriksaan.unsur_hara.strip()
        ),
        "kontaminan": bool(hasil_pemeriksaan.kontaminan.strip()),
    }

    jumlah_terisi = sum(values.values())
    kelengkapan = round(jumlah_terisi / len(DATA_CATEGORIES) * 100)

    return values, jumlah_terisi, kelengkapan


def _build_input_snapshot(lahan, hasil_pemeriksaan):
    nutrients = [
        {
            "nama": item.nama_unsur,
            "nilai": str(item.nilai),
            "satuan": item.satuan,
            "metode": item.metode,
        }
        for item in hasil_pemeriksaan.nutrient_measurements.all()
    ]

    return {
        "lahan_id": str(lahan.pk),
        "hasil_pemeriksaan_id": hasil_pemeriksaan.pk,
        "tanggal_pemeriksaan": (
            hasil_pemeriksaan.tanggal_pemeriksaan.isoformat()
        ),
        "ph": (
            str(hasil_pemeriksaan.ph)
            if hasil_pemeriksaan.ph is not None
            else None
        ),
        "kelembapan": (
            str(hasil_pemeriksaan.kelembapan)
            if hasil_pemeriksaan.kelembapan is not None
            else None
        ),
        "tekstur": hasil_pemeriksaan.tekstur,
        "bahan_organik": (
            str(hasil_pemeriksaan.bahan_organik)
            if hasil_pemeriksaan.bahan_organik is not None
            else None
        ),
        "unsur_hara": hasil_pemeriksaan.unsur_hara,
        "pengukuran_unsur_hara": nutrients,
        "kontaminan": hasil_pemeriksaan.kontaminan,
    }


def _goal_matches_plant(tujuan, tanaman):
    goal_text = (
        f"{tujuan.nama} {tujuan.slug} {tujuan.deskripsi}"
    ).casefold()

    plant_text = (
        f"{tanaman.fungsi} {tanaman.deskripsi}"
    ).casefold()

    matching_groups = [
        group
        for group in GOAL_GROUPS.values()
        if any(term in goal_text for term in group["goal_terms"])
    ]

    if matching_groups:
        return any(
            term in plant_text
            for group in matching_groups
            for term in group["plant_terms"]
        )

    # Untuk tujuan yang belum memiliki kelompok kata khusus,
    # gunakan kecocokan kata secara sederhana dan transparan.
    stop_words = {
        "dan", "atau", "untuk", "dengan", "pada", "dari",
        "yang", "ke", "di", "meningkatkan", "mengurangi",
        "menambah", "pengelolaan", "tanah",
    }

    goal_words = {
        word
        for word in goal_text.replace("-", " ").split()
        if len(word) > 3 and word not in stop_words
    }

    return any(word in plant_text for word in goal_words)


def _is_high_risk(tanaman):
    risk_text = (tanaman.risiko_penggunaan or "").casefold()
    return any(term in risk_text for term in HIGH_RISK_TERMS)

def assess_soil_risk(hasil_pemeriksaan):
    """
    Periksa apakah catatan kontaminan memerlukan penilaian ahli.

    Karena nilai dan batas aman disimpan sebagai teks bebas,
    fungsi ini tidak mengklaim bahwa suatu angka melampaui batas resmi.
    """
    raw = (hasil_pemeriksaan.kontaminan or "").strip()
    normalized = " ".join(raw.casefold().split()).strip(" .,:;")

    explicit_no_contaminant = {
        "tidak ada",
        "tidak ada kontaminan",
        "tidak terdeteksi",
        "tidak terdeteksi kontaminan",
        "none detected",
        "no contaminant detected",
        "no contaminants detected",
        "negatif",
    }

    if not raw or normalized in explicit_no_contaminant:
        return {
            "risiko_tinggi": False,
            "temuan": raw,
            "sumber": (
                hasil_pemeriksaan.sumber
                or hasil_pemeriksaan.get_asal_display()
            ),
            "alasan": None,
        }

    return {
        "risiko_tinggi": True,
        "temuan": raw,
        "sumber": (
            hasil_pemeriksaan.sumber
            or hasil_pemeriksaan.get_asal_display()
        ),
        "alasan": (
            "Hasil pemeriksaan mencatat kontaminan, tetapi nilai dan "
            "batas aman belum diverifikasi menggunakan aturan yang "
            "terstruktur. Rekomendasi otomatis memerlukan penilaian ahli."
        ),
    }


def calculate_recommendations(lahan, hasil_pemeriksaan, tujuan):
    """
    Menghasilkan kandidat rekomendasi tanpa menyimpan snapshot.

    Jika hasil pemeriksaan mencatat kontaminan yang belum terverifikasi,
    rekomendasi otomatis dihentikan dan hasil diarahkan ke penilaian ahli.
    """
    if hasil_pemeriksaan.status_hasil != "final":
        raise RecommendationInputError(
            "Rekomendasi hanya dapat dibuat dari hasil pemeriksaan final."
        )
    
    if hasil_pemeriksaan.lahan_id != lahan.pk:
        raise RecommendationInputError(
            "Hasil pemeriksaan bukan milik lahan yang dipilih."
        )

    if not tujuan.aktif:
        raise RecommendationInputError(
            "Tujuan pengelolaan ini sudah tidak aktif."
        )

    _, jumlah_terisi, kelengkapan = _soil_data_status(
        hasil_pemeriksaan
    )
    input_snapshot = _build_input_snapshot(lahan, hasil_pemeriksaan)

    risiko_tanah = assess_soil_risk(hasil_pemeriksaan)

    # Jangan menghitung skor atau mengambil data lingkungan ketika
    # catatan kontaminan belum diverifikasi.
    if risiko_tanah["risiko_tinggi"]:
        return {
            "rekomendasi": [],
            "diblokir": [],
            "kelengkapan_data": kelengkapan,
            "input_snapshot": input_snapshot,
            "data_lingkungan": {
                "status": "unavailable",
                "source": "Open-Meteo",
                "reason": "soil_risk_review_required",
                "message": (
                    "Data lingkungan tidak diambil karena hasil "
                    "pemeriksaan membutuhkan penilaian ahli."
                ),
                "timezone": None,
                "current": {},
                "units": {},
            },
            "versi_aturan": RULE_VERSION,
            "risiko_tinggi": True,
            "temuan_risiko": risiko_tanah,
        }

    if jumlah_terisi < MINIMUM_DATA_CATEGORIES:
        raise RecommendationInputError(
            "Data tanah belum mencukupi. Isi setidaknya dua kategori "
            "data pemeriksaan sebelum meminta rekomendasi."
        )

    data_lingkungan = fetch_environmental_data(lahan)

    rekomendasi = []
    diblokir = []

    for tanaman in Tanaman.objects.all():
        if not _goal_matches_plant(tujuan, tanaman):
            continue

        if not tanaman.tersedia_di_indonesia:
            continue

        if _is_high_risk(tanaman):
            diblokir.append({
                "tanaman": tanaman,
                "alasan": (
                    "Risiko penggunaan memerlukan penilaian lebih lanjut. "
                    "Rekomendasi otomatis untuk tanaman ini diblokir."
                ),
            })
            continue

        skor = 55
        alasan = [
            "Fungsi tanaman cocok dengan kata kunci tujuan pengelolaan."
        ]

        skor += 15
        alasan.append("Tanaman tercatat tersedia di Indonesia.")

        if tanaman.kondisi_pertumbuhan.strip():
            skor += 10
            alasan.append(
                "Informasi kondisi pertumbuhan tanaman sudah dicatat."
            )
        else:
            alasan.append(
                "Informasi kondisi pertumbuhan tanaman belum lengkap."
            )

        poin_data = round(kelengkapan * 0.20)
        skor += poin_data
        alasan.append(
            f"Kelengkapan data tanah {kelengkapan}% "
            f"({jumlah_terisi}/{len(DATA_CATEGORIES)} kategori)."
        )

        rekomendasi.append(
            RecommendationCandidate(
                tanaman=tanaman,
                skor=min(skor, 100),
                alasan=alasan,
                kelengkapan_data=kelengkapan,
                input_snapshot=input_snapshot,
                data_lingkungan=data_lingkungan,
            )
        )

    rekomendasi.sort(
        key=lambda item: (-item.skor, item.tanaman.nama.casefold())
    )

    return {
        "rekomendasi": rekomendasi,
        "diblokir": diblokir,
        "kelengkapan_data": kelengkapan,
        "input_snapshot": input_snapshot,
        "data_lingkungan": data_lingkungan,
        "versi_aturan": RULE_VERSION,
        "risiko_tinggi": False,
        "temuan_risiko": None,
    }