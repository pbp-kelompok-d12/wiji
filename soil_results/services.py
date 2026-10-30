from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from inspections.models import PesananPemeriksaan
from inspections.services import ubah_status

from .models import HasilPemeriksaan
from .permissions import pastikan_boleh_mengelola


@transaction.atomic
def finalkan_hasil_petugas(*, hasil_id, user):
    # Cari hanya hasil Wiji yang ditugaskan kepada petugas ini.
    calon = get_object_or_404(
        HasilPemeriksaan,
        pk=hasil_id,
        asal=HasilPemeriksaan.Asal.WIJI,
        pesanan__petugas=user,
    )

    # Kunci pesanan dahulu, sama seperti saat menyimpan draf.
    pesanan = get_object_or_404(
        PesananPemeriksaan.objects.select_for_update(),
        pk=calon.pesanan_id,
        petugas=user,
    )
    hasil = get_object_or_404(
        HasilPemeriksaan.objects.select_for_update(),
        pk=hasil_id,
    )
    hasil.pesanan = pesanan

    pastikan_boleh_mengelola(user, hasil)

    errors = []

    # Nilai 0 tetap dianggap terisi.
    for field, label in [
        ("ph", "pH"),
        ("kelembapan", "Kelembapan"),
        ("bahan_organik", "Bahan organik"),
    ]:
        if getattr(hasil, field) is None:
            errors.append(f"{label} wajib diisi.")

    if not hasil.tekstur.strip():
        errors.append("Tekstur tanah wajib diisi.")

    tingkat = pesanan.jenis.tingkat

    if tingkat not in (1, 2, 3):
        errors.append("Tingkat jenis pemeriksaan belum didukung.")

    if tingkat >= 2 and not hasil.nutrient_measurements.exists():
        errors.append(
            "Pemeriksaan ini membutuhkan minimal satu pengukuran unsur hara."
        )

    if tingkat >= 3 and not hasil.contaminant_findings.exists():
        errors.append(
            "Pemeriksaan kontaminan membutuhkan minimal satu temuan, "
            "termasuk jika hasilnya tidak terdeteksi."
        )

    if errors:
        raise ValidationError(errors)

    # Validasi kembali data utama dan data pendukung.
    hasil.full_clean()

    for pengukuran in hasil.nutrient_measurements.all():
        pengukuran.full_clean()

    for temuan in hasil.contaminant_findings.all():
        temuan.full_clean()

    hasil.status_hasil = HasilPemeriksaan.StatusHasil.FINAL
    hasil.difinalkan_pada = timezone.now()
    hasil.save(
        update_fields=[
            "status_hasil",
            "difinalkan_pada",
            "diperbarui_pada",
        ]
    )

    # Modul B mengurus perubahan status beserta riwayatnya.
    ubah_status(
        pesanan,
        PesananPemeriksaan.Status.SELESAI,
        oleh=user,
        catatan="Hasil pemeriksaan telah difinalkan oleh petugas.",
    )

    return hasil