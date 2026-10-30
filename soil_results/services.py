from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from inspections.models import PesananPemeriksaan
from inspections.services import ubah_status

from .models import HasilPemeriksaan, RiwayatKoreksiHasil
from .forms import KoreksiHasilForm
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

FIELD_KOREKSI_DASAR = (
    "tanggal_pemeriksaan",
    "ph",
    "kelembapan",
    "tekstur",
    "bahan_organik",
    "catatan",
)


def snapshot_data_dasar(hasil):
    # Tanggal dan Decimal diubah menjadi teks agar bisa disimpan ke JSON.
    return {
        nama: (
            str(getattr(hasil, nama))
            if getattr(hasil, nama) is not None
            else None
        )
        for nama in FIELD_KOREKSI_DASAR
    }


@transaction.atomic
def koreksi_hasil_final(*, hasil_id, user, data):
    if not user.is_authenticated or not user.is_active or not user.is_staff:
        raise PermissionDenied(
            "Hanya admin aktif yang dapat mengoreksi hasil final."
        )

    hasil = get_object_or_404(
        HasilPemeriksaan.objects.select_for_update(),
        pk=hasil_id,
        asal=HasilPemeriksaan.Asal.WIJI,
        status_hasil=HasilPemeriksaan.StatusHasil.FINAL,
    )

    if hasil.lahan.diarsipkan:
        raise ValidationError(
            "Hasil pada lahan yang diarsipkan tidak dapat dikoreksi."
        )

    if hasil.dipakai_dalam_rencana():
        raise ValidationError(
            "Hasil sudah digunakan dalam rencana pengelolaan "
            "sehingga tidak dapat dikoreksi."
        )

    sebelum = snapshot_data_dasar(hasil)

    form = KoreksiHasilForm(data, instance=hasil)

    if not form.is_valid():
        pesan = [
            f"{nama}: {error}"
            for nama, errors in form.errors.items()
            for error in errors
        ]
        raise ValidationError(pesan)

    hasil = form.save(commit=False)
    sesudah = snapshot_data_dasar(hasil)

    if sebelum == sesudah:
        raise ValidationError(
            "Tidak ada perubahan data yang perlu disimpan."
        )

    hasil.full_clean()
    hasil.save(
        update_fields=[
            *FIELD_KOREKSI_DASAR,
            "diperbarui_pada",
        ]
    )

    RiwayatKoreksiHasil.objects.create(
        hasil=hasil,
        dikoreksi_oleh=user,
        alasan=form.cleaned_data["alasan"],
        data_sebelum=sebelum,
        data_sesudah=sesudah,
    )

    return hasil