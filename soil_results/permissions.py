from django.core.exceptions import PermissionDenied

from .models import HasilPemeriksaan


def boleh_mengelola_hasil(user, hasil):
    if not user.is_authenticated or hasil.lahan.diarsipkan:
        return False

    if hasil.dipakai_dalam_rencana():
        return False

    if hasil.asal == HasilPemeriksaan.Asal.MANDIRI:
        return user.is_owner and hasil.lahan.owner_id == user.pk

    if hasil.asal == HasilPemeriksaan.Asal.WIJI:
        return (
            user.is_officer
            and hasil.status_hasil == HasilPemeriksaan.StatusHasil.DRAF
            and hasil.pesanan_id is not None
            and hasil.pesanan.petugas_id == user.pk
            and hasil.pesanan.status == "diproses"
        )

    return False


def pastikan_boleh_mengelola(user, hasil):
    if not boleh_mengelola_hasil(user, hasil):
        raise PermissionDenied(
            "Hasil tidak dapat diubah: akses tidak sesuai, "
            "hasil sudah terkunci, atau pesanan tidak sedang diproses."
        )