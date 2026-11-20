"""Bantuan buat nampilin pesanan di template."""
from .models import PesananPemeriksaan

Status = PesananPemeriksaan.Status

# Urutan normal pesanan, dipakai buat garis status
URUTAN_STATUS = [
    Status.DIAJUKAN,
    Status.DIKONFIRMASI,
    Status.DIJADWALKAN,
    Status.SAMPEL_DIAMBIL,
    Status.DIPROSES,
    Status.SELESAI,
]


def langkah_status(pesanan):
    """Daftar langkah buat garis status: done = sudah lewat, now = lagi di sini.

    Pesanan yang dibatalkan nggak punya garis status (None), tampilannya beda.
    """
    if pesanan.status == Status.DIBATALKAN:
        return None
    sekarang = URUTAN_STATUS.index(pesanan.status)
    langkah = []
    for i, status in enumerate(URUTAN_STATUS):
        if i < sekarang or pesanan.status == Status.SELESAI:
            keadaan = 'done'
        elif i == sekarang:
            keadaan = 'now'
        else:
            keadaan = ''
        langkah.append({'label': status.label, 'keadaan': keadaan})
    return langkah
