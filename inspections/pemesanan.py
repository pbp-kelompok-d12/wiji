"""Aturan yang dipakai pemilik lahan: bikin pesanan, ubah usulan, batalkan, dan minta jadwal ulang."""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import PesananPemeriksaan, RiwayatPesanan
from .services import catat_riwayat, ubah_status

Status = PesananPemeriksaan.Status

MAKS_HARI_KE_DEPAN = 30
STATUS_BISA_BATAL = (Status.DIAJUKAN, Status.DIKONFIRMASI, Status.DIJADWALKAN)
STATUS_BISA_JADWAL_ULANG = (Status.DIKONFIRMASI, Status.DIJADWALKAN)


def validasi_tanggal_usulan(tanggal, hari_ini=None):
    """Paling cepat besok, paling lambat 30 hari ke depan."""
    hari_ini = hari_ini or timezone.localdate()
    if tanggal <= hari_ini:
        raise ValidationError('Tanggal usulan paling cepat besok.')
    if tanggal > hari_ini + timedelta(days=MAKS_HARI_KE_DEPAN):
        raise ValidationError(f'Tanggal usulan paling lambat {MAKS_HARI_KE_DEPAN} hari dari sekarang.')


def validasi_lahan_bisa_dipesan(lahan):
    if lahan.diarsipkan:
        raise ValidationError('Lahan yang diarsipkan nggak bisa dipesankan pemeriksaan.')
    if lahan.adalah_draf or not lahan.punya_koordinat:
        raise ValidationError('Lengkapi data lahan (termasuk koordinat) dulu sebelum memesan pemeriksaan.')
    if lahan.punya_pesanan_aktif():
        raise ValidationError('Lahan ini masih punya pesanan yang berjalan.')


@transaction.atomic
def buat_pesanan(pemilik, lahan, jenis, tanggal_usulan, sesi_usulan, catatan=''):
    if lahan.owner_id != pemilik.pk:
        raise ValidationError('Lahan ini bukan milikmu.')
    if not jenis.aktif:
        raise ValidationError('Jenis pemeriksaan ini sudah nggak tersedia.')
    validasi_lahan_bisa_dipesan(lahan)
    validasi_tanggal_usulan(tanggal_usulan)

    try:
        # savepoint sendiri, biar kalau kebentur aturan "satu pesanan aktif" transaksi luar tetap sehat
        with transaction.atomic():
            pesanan = PesananPemeriksaan.objects.create(
                lahan=lahan,
                jenis=jenis,
                tanggal_usulan=tanggal_usulan,
                sesi_usulan=sesi_usulan,
                catatan=catatan.strip(),
            )
    except IntegrityError:
        raise ValidationError('Lahan ini masih punya pesanan yang berjalan.')

    catat_riwayat(pesanan, pemilik, sesudah=Status.DIAJUKAN)
    return pesanan


@transaction.atomic
def ubah_usulan(pesanan, tanggal_usulan, sesi_usulan, catatan=''):
    """Pemilik bebas ngubah usulan selama masih Diajukan."""
    pesanan = PesananPemeriksaan.objects.select_for_update().get(pk=pesanan.pk)
    if pesanan.status != Status.DIAJUKAN:
        raise ValidationError('Usulan cuma bisa diubah selama pesanan masih Diajukan.')
    validasi_tanggal_usulan(tanggal_usulan)

    pesanan.tanggal_usulan = tanggal_usulan
    pesanan.sesi_usulan = sesi_usulan
    pesanan.catatan = catatan.strip()
    pesanan.save(update_fields=['tanggal_usulan', 'sesi_usulan', 'catatan', 'diperbarui_pada'])
    return pesanan


@transaction.atomic
def batalkan_pesanan(pesanan, oleh, alasan):
    """Pembatalan jadi soft delete: pesanan tetap ada sebagai riwayat."""
    pesanan = PesananPemeriksaan.objects.select_for_update().get(pk=pesanan.pk)
    if pesanan.status not in STATUS_BISA_BATAL:
        raise ValidationError('Pesanan ini sudah nggak bisa dibatalkan.')
    return ubah_status(pesanan, Status.DIBATALKAN, oleh, alasan)


@transaction.atomic
def ajukan_jadwal_ulang(pesanan, oleh, tanggal_baru, sesi_baru, alasan):
    """Usulan diganti, jadwal final dikosongkan, status balik ke Dikonfirmasi. Petugas tetap sama."""
    pesanan = PesananPemeriksaan.objects.select_for_update().get(pk=pesanan.pk)
    if pesanan.status not in STATUS_BISA_JADWAL_ULANG:
        raise ValidationError('Jadwal ulang cuma bisa diminta saat pesanan Dikonfirmasi atau Dijadwalkan.')
    if not alasan.strip():
        raise ValidationError('Alasan jadwal ulang wajib diisi.')
    validasi_tanggal_usulan(tanggal_baru)

    status_lama = pesanan.status
    tanggal_lama = pesanan.tanggal_final or pesanan.tanggal_usulan
    pesanan.tanggal_usulan = tanggal_baru
    pesanan.sesi_usulan = sesi_baru
    pesanan.tanggal_final = None
    pesanan.sesi_final = ''
    pesanan.status = Status.DIKONFIRMASI
    pesanan.save(update_fields=[
        'tanggal_usulan', 'sesi_usulan', 'tanggal_final', 'sesi_final', 'status', 'diperbarui_pada',
    ])
    catat_riwayat(
        pesanan, oleh, jenis=RiwayatPesanan.Jenis.JADWAL_ULANG,
        sebelum=status_lama, sesudah=Status.DIKONFIRMASI, catatan=alasan.strip(),
        tanggal_lama=tanggal_lama, tanggal_baru=tanggal_baru,
    )
    return pesanan
