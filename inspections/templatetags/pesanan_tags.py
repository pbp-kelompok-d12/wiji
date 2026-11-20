from django import template

register = template.Library()

KELAS_STATUS = {
    'diajukan': 'chip-sand',
    'dikonfirmasi': 'chip-paper',
    'dijadwalkan': 'chip-sky',
    'sampel_diambil': 'chip-sky',
    'diproses': 'chip-paper',
    'selesai': 'chip-up',
    'dibatalkan': 'chip-down',
}


@register.filter
def kelas_status(status):
    """Kelas warna chip buat status pesanan."""
    return KELAS_STATUS.get(status, 'chip-paper')
