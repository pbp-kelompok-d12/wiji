from django.test import TestCase
from django.urls import reverse

from .helpers import buat_lahan, buat_pemilik, buat_pesanan


class TombolPesanDiHalamanLahanTests(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.client.force_login(self.pemilik)

    def detail(self, lahan):
        return self.client.get(reverse('lands:detail_lahan', args=[lahan.pk]))

    def test_lahan_siap_dapat_tautan_pesan_dengan_lahan_terpilih(self):
        lahan = buat_lahan(self.pemilik)
        url_pesan = f"{reverse('inspections:pesan_pemeriksaan')}?lahan={lahan.pk}"
        self.assertContains(self.detail(lahan), f'href="{url_pesan}"')

    def test_lahan_dengan_pesanan_berjalan_tombolnya_mati_dan_ada_tautan_pesanan(self):
        lahan = buat_lahan(self.pemilik)
        buat_pesanan(lahan)
        response = self.detail(lahan)
        self.assertNotContains(response, reverse('inspections:pesan_pemeriksaan'))
        self.assertContains(response, reverse('inspections:daftar_pesanan'))

    def test_lahan_draf_nggak_bisa_dipesan(self):
        lahan = buat_lahan(self.pemilik, penggunaan=None)
        self.assertNotContains(self.detail(lahan), reverse('inspections:pesan_pemeriksaan'))

    def test_lahan_diarsipkan_nggak_bisa_dipesan(self):
        lahan = buat_lahan(self.pemilik)
        lahan.arsipkan()
        self.assertNotContains(self.detail(lahan), reverse('inspections:pesan_pemeriksaan'))
