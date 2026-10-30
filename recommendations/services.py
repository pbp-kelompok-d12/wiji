from dataclasses import dataclass
from typing import Any

from .environment import fetch_environmental_data
from core.models import (
    Tanaman,
    PlantContaminantCapability,
)


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
FOOD_CROP_TERMS = (
    "tanaman pangan",
    "tanaman konsumsi",
    "pangan",
    "sayur",
    "sayuran",
    "buah",
    "bahan makanan",
    "food crop",
    "edible crop",
    "padi",
    "jagung",
    "singkong",
    "kentang",
    "kedelai",
    "kacang",
    "bayam",
    "kangkung",
    "sawi",
    "selada",
    "wortel",
    "tomat",
    "cabai",
    "terong",
    "pisang",
    "mangga",
    "pepaya",
)

NON_FOOD_TERMS = (
    "non-pangan",
    "bukan tanaman pangan",
    "bukan pangan",
    "non-food",
    "tidak untuk konsumsi",
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
        "kontaminan": (
            hasil_pemeriksaan.contaminant_findings.exists()
            or bool(hasil_pemeriksaan.kontaminan.strip())
        ),
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
        "temuan_kontaminan": [
            {
                "kontaminan_id": temuan.kontaminan_id,
                "nama": temuan.kontaminan.nama,
                "status": temuan.status,
                "nilai": (
                    str(temuan.nilai)
                    if temuan.nilai is not None
                    else None
                ),
                "satuan": temuan.satuan,
                "batas_deteksi": (
                    str(temuan.batas_deteksi)
                    if temuan.batas_deteksi is not None
                    else None
                ),
                "metode": temuan.metode,
                "catatan": temuan.catatan,
            }
            for temuan in (
                hasil_pemeriksaan.contaminant_findings
                .select_related("kontaminan")
                .all()
            )
        ],
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
def _is_food_crop_without_clear_consumption_safety(tanaman):
    plant_text = " ".join([
        tanaman.nama or "",
        tanaman.fungsi or "",
        tanaman.deskripsi or "",
        tanaman.kontaminan_ditangani or "",
    ]).casefold()

    risk_text = (tanaman.risiko_penggunaan or "").casefold()

    if any(term in plant_text for term in NON_FOOD_TERMS):
        return False

    is_food_crop = any(
        term in plant_text
        for term in FOOD_CROP_TERMS
    )

    if not is_food_crop:
        return False

    safety_verified = (
        "keamanan konsumsi terverifikasi" in risk_text
        and bool((tanaman.sumber_penelitian or "").strip())
    )

    return not safety_verified
def _get_supported_contaminant_capabilities(
    tanaman,
    hasil_pemeriksaan,
):
    """
    Mengambil kemampuan tanaman yang cocok dengan seluruh
    kontaminan terdeteksi dan memiliki referensi literatur.
    """
    temuan_terdeteksi = (
        hasil_pemeriksaan.contaminant_findings
        .filter(status="terdeteksi")
        .select_related("kontaminan")
    )

    kontaminan_ids = [
        temuan.kontaminan_id
        for temuan in temuan_terdeteksi
    ]

    if not kontaminan_ids:
        return []

    kemampuan = list(
        PlantContaminantCapability.objects.filter(
            tanaman=tanaman,
            kontaminan_id__in=kontaminan_ids,
        ).select_related("kontaminan")
    )

    kemampuan_by_id = {
        item.kontaminan_id: item
        for item in kemampuan
    }

    # Tanaman harus memiliki kemampuan untuk SEMUA
    # kontaminan yang terdeteksi.
    if len(kemampuan_by_id) != len(set(kontaminan_ids)):
        return []

    # Referensi literatur tanaman harus tersedia.
    # Setiap pasangan tanaman-kontaminan harus memiliki
# referensi yang membahas kontaminan tersebut.
    for item in kemampuan_by_id.values():
        referensi_pair = tanaman.referensi.filter(
            sumber_literatur__icontains=item.kontaminan.nama,
        ).exists()

        if not referensi_pair:
            return []

    return list(kemampuan_by_id.values())


def assess_soil_risk(hasil_pemeriksaan):
    """
    Periksa apakah data kontaminan cukup untuk melanjutkan
    rekomendasi otomatis.

    Data kosong dianggap belum diketahui, bukan berarti aman.
    """
    sumber = (
        hasil_pemeriksaan.sumber
        or hasil_pemeriksaan.get_asal_display()
    )

    temuan_terstruktur = list(
        hasil_pemeriksaan.contaminant_findings
        .select_related("kontaminan")
        .all()
    )

    temuan_terdeteksi = [
        temuan
        for temuan in temuan_terstruktur
        if temuan.status == "terdeteksi"
    ]

    # Kondisi 1: Ada kontaminan yang terdeteksi.
    if temuan_terdeteksi:
        ringkasan = "; ".join(
            f"{temuan.kontaminan.nama}: "
            f"{temuan.nilai} {temuan.satuan}"
            for temuan in temuan_terdeteksi
        )

        return {
            "risiko_tinggi": False,
            "temuan": ringkasan,
            "sumber": sumber,
            "alasan": (
                "Kontaminan terdeteksi. Rekomendasi hanya dapat "
                "diberikan untuk tanaman yang memiliki kemampuan "
                "tercatat menangani seluruh kontaminan dan didukung "
                "referensi literatur. Hasil ini bukan bukti bahwa "
                "tanah sudah aman."
            ),
        }

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

    # Kondisi 2: Ada catatan bebas yang belum terverifikasi.
    if raw and normalized not in explicit_no_contaminant:
        return {
            "risiko_tinggi": True,
            "temuan": raw,
            "sumber": sumber,
            "alasan": (
                "Catatan pemeriksaan mencantumkan informasi "
                "kontaminan yang belum dapat diverifikasi secara "
                "terstruktur. Penilaian ahli diperlukan sebelum "
                "rekomendasi otomatis diberikan."
            ),
        }

    # Kondisi 3: Tidak ada catatan atau temuan kontaminan sama sekali.
    if not raw and not temuan_terstruktur:
        return {
            "risiko_tinggi": True,
            "temuan": "Data kontaminan belum tersedia.",
            "sumber": sumber,
            "alasan": (
                "Belum ada data pemeriksaan kontaminan. "
                "Ketiadaan data tidak dapat dianggap sebagai "
                "bukti bahwa tanah bebas kontaminan. "
                "Lengkapi pemeriksaan atau minta penilaian ahli."
            ),
        }

    # Kondisi 4: Ada hasil eksplisit tidak terdeteksi.
    if temuan_terstruktur:
        ringkasan = "; ".join(
            f"{temuan.kontaminan.nama}: tidak terdeteksi"
            for temuan in temuan_terstruktur
        )
    else:
        ringkasan = raw

    return {
        "risiko_tinggi": False,
        "temuan": ringkasan,
        "sumber": sumber,
        "alasan": None,
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

        if _is_food_crop_without_clear_consumption_safety(tanaman):
            diblokir.append({
                "tanaman": tanaman,
                "alasan": (
                    "Tanaman pangan belum memiliki bukti dan sumber "
                    "penelitian yang memverifikasi keamanan konsumsinya."
                ),
            })
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

        temuan_terdeteksi = (
            hasil_pemeriksaan.contaminant_findings
            .filter(status="terdeteksi")
        )

        kemampuan_kontaminan = []

        if temuan_terdeteksi.exists():
            kemampuan_kontaminan = (
                _get_supported_contaminant_capabilities(
                    tanaman,
                    hasil_pemeriksaan,
                )
            )

            if not kemampuan_kontaminan:
                diblokir.append({
                    "tanaman": tanaman,
                    "alasan": (
                        "Tanaman belum memiliki bukti kemampuan "
                        "menangani seluruh kontaminan yang terdeteksi "
                        "beserta referensi literatur yang diperlukan."
                    ),
                })
                continue
        skor = 55
        alasan = [
            "Fungsi tanaman cocok dengan kata kunci tujuan pengelolaan."
        ]
        if kemampuan_kontaminan:
            for kemampuan in kemampuan_kontaminan:
                alasan.append(
                    f"Tanaman tercatat mampu menangani "
                    f"{kemampuan.kontaminan.nama}."
                )

            alasan.append(
                "Kemampuan tanaman didukung referensi literatur."
            )

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