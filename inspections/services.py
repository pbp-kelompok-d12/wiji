"""Aturan perpindahan status pesanan.

Semua perubahan status HARUS lewat sini (termasuk dari Modul C, pas hasil difinalkan),
jangan ngubah kolom status langsung. Tiap perubahan otomatis tercatat di riwayat.
"""
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import PesananPemeriksaan, RiwayatPesanan

Status = PesananPemeriksaan.Status

# Status asal -> status tujuan yang boleh. Jadwal ulang punya jalur sendiri (lihat pemesanan.py).
TRANSISI = {
    Status.DIAJUKAN: {Status.DIKONFIRMASI, Status.DIBATALKAN},
    Status.DIKONFIRMASI: {Status.DIJADWALKAN, Status.DIBATALKAN},
    Status.DIJADWALKAN: {Status.SAMPEL_DIAMBIL, Status.DIBATALKAN},
    Status.SAMPEL_DIAMBIL: {Status.DIPROSES},
    Status.DIPROSES: {Status.SELESAI},
}

# Petugas masih boleh diganti selama sampel belum diambil
STATUS_BISA_GANTI_PETUGAS = (Status.DIKONFIRMASI, Status.DIJADWALKAN)


def catat_riwayat(pesanan, oleh, jenis=RiwayatPesanan.Jenis.STATUS, sebelum='', sesudah='',
                  catatan='', tanggal_lama=None, tanggal_baru=None):
    return RiwayatPesanan.objects.create(
        pesanan=pesanan,
        oleh=oleh,
        jenis=jenis,
        status_sebelum=sebelum,
        status_sesudah=sesudah,
        catatan=catatan,
        tanggal_lama=tanggal_lama,
        tanggal_baru=tanggal_baru,
    )


def _petugas_valid(petugas):
    if petugas is None or petugas.role != 'officer' or not petugas.is_active:
        raise ValidationError('Pilih petugas pemeriksa yang masih aktif.')


@transaction.atomic
def ubah_status(pesanan, status_baru, oleh=None, catatan=''):
    """Pindahin pesanan ke status_baru kalau urutannya boleh dan datanya lengkap."""
    pesanan = PesananPemeriksaan.objects.select_for_update().get(pk=pesanan.pk)
    status_lama = pesanan.status
    status_baru = Status(status_baru)

    if status_baru not in TRANSISI.get(status_lama, set()):
        raise ValidationError(
            f'Pesanan yang berstatus {Status(status_lama).label} nggak bisa langsung jadi {status_baru.label}.'
        )
    if status_baru == Status.DIKONFIRMASI and pesanan.petugas_id is None:
        raise ValidationError('Tugaskan petugas dulu sebelum pesanan dikonfirmasi.')
    if status_baru == Status.DIJADWALKAN and not (pesanan.tanggal_final and pesanan.sesi_final):
        raise ValidationError('Isi tanggal dan sesi final dulu sebelum pesanan dijadwalkan.')
    if status_baru == Status.DIBATALKAN and not catatan.strip():
        raise ValidationError('Alasan pembatalan wajib diisi.')

    pesanan.status = status_baru
    pesanan.save(update_fields=['status', 'diperbarui_pada'])
    catat_riwayat(pesanan, oleh, sebelum=status_lama, sesudah=status_baru, catatan=catatan.strip())
    return pesanan


@transaction.atomic
def konfirmasi_pesanan(pesanan, petugas, oleh=None, catatan=''):
    """Admin menugaskan petugas, status jadi Dikonfirmasi."""
    _petugas_valid(petugas)
    PesananPemeriksaan.objects.filter(pk=pesanan.pk).update(petugas=petugas)
    pesanan.petugas = petugas
    return ubah_status(pesanan, Status.DIKONFIRMASI, oleh, catatan)


@transaction.atomic
def jadwalkan_pesanan(pesanan, tanggal, sesi, oleh=None, catatan=''):
    """Admin menetapkan jadwal final, status jadi Dijadwalkan."""
    PesananPemeriksaan.objects.filter(pk=pesanan.pk).update(tanggal_final=tanggal, sesi_final=sesi)
    pesanan.tanggal_final = tanggal
    pesanan.sesi_final = sesi
    return ubah_status(pesanan, Status.DIJADWALKAN, oleh, catatan)


@transaction.atomic
def ganti_petugas(pesanan, petugas_baru, oleh=None, catatan=''):
    """Admin ganti petugas. Statusnya nggak berubah."""
    pesanan = PesananPemeriksaan.objects.select_for_update().get(pk=pesanan.pk)
    if pesanan.status not in STATUS_BISA_GANTI_PETUGAS:
        raise ValidationError('Petugas cuma bisa diganti sebelum sampel diambil.')
    _petugas_valid(petugas_baru)

    lama = pesanan.petugas
    pesanan.petugas = petugas_baru
    pesanan.save(update_fields=['petugas', 'diperbarui_pada'])
    ringkas = f'{lama.display_name if lama else "belum ada"} → {petugas_baru.display_name}'
    catat_riwayat(
        pesanan, oleh, jenis=RiwayatPesanan.Jenis.GANTI_PETUGAS,
        sebelum=pesanan.status, sesudah=pesanan.status,
        catatan=f'{ringkas}. {catatan}'.strip(),
    )
    return pesanan
