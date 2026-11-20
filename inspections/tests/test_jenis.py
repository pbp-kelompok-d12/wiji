from django.db import IntegrityError, transaction
from django.test import TestCase

from ..models import JenisPemeriksaan


class JenisPemeriksaanTests(TestCase):
    def test_tiga_jenis_awal_tersedia_dan_berurutan(self):
        nama = list(JenisPemeriksaan.objects.values_list('nama', flat=True))
        self.assertEqual(nama, ['Dasar', 'Unsur Hara', 'Kontaminan'])

    def test_jenis_awal_aktif(self):
        self.assertFalse(JenisPemeriksaan.objects.filter(aktif=False).exists())

    def test_nama_harus_unik(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            JenisPemeriksaan.objects.create(nama='Dasar', slug='dasar-lain')

    def test_str_pakai_nama(self):
        self.assertEqual(str(JenisPemeriksaan.objects.get(slug='dasar')), 'Dasar')
