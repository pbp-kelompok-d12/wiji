"""Hitungan lahan milik pemilik, dipakai sidebar dan dashboard."""
from functools import cached_property

from django.db.models import Q

from lands.models import Lahan


def filter_draf():
    """Lahan draf = ada data wajib yang masih kosong. Sama dengan aturan di daftar lahan."""
    draf = Q()
    for nama in Lahan.REQUIRED_FIELDS:
        kosong = Q(**{f'{nama}__isnull': True})
        if Lahan._meta.get_field(nama).get_internal_type() in ('CharField', 'TextField'):
            kosong |= Q(**{nama: ''})
        draf |= kosong
    return draf


class RingkasanLahan:
    """Hitungan lahan milik satu pemilik. Query baru jalan kalau angkanya dipakai."""

    def __init__(self, pemilik):
        self._semua = Lahan.objects.filter(owner=pemilik, diarsipkan=False)
        self._draf = self._semua.filter(filter_draf())

    @cached_property
    def aktif(self):
        return self._semua.exclude(filter_draf()).count()

    @cached_property
    def draf(self):
        return self._draf.count()

    @cached_property
    def draf_pertama(self):
        return self._draf.order_by('-dibuat_pada').first()
