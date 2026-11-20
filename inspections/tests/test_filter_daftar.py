from django.test import TestCase
from django.urls import reverse

from .. import pemesanan
from ..models import PesananPemeriksaan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan

Status = PesananPemeriksaan.Status
HTMX = {'HTTP_HX_REQUEST': 'true'}


class FilterDaftarTests(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.url = reverse('inspections:daftar_pesanan')
        self.jalan = buat_pesanan(buat_lahan(self.pemilik, nama='Lahan Berjalan'))
        self.selesai = buat_pesanan(buat_lahan(self.pemilik, nama='Lahan Selesai'))
        PesananPemeriksaan.objects.filter(pk=self.selesai.pk).update(status=Status.SELESAI)
        self.batal = buat_pesanan(buat_lahan(self.pemilik, nama='Lahan Batal'))
        pemesanan.batalkan_pesanan(self.batal, self.pemilik, 'Salah lahan')
        self.client.force_login(self.pemilik)

    def nama_lahan(self, **param):
        response = self.client.get(self.url, param)
        return {p.lahan.nama for p in response.context['pesanan_list']}

    def test_tanpa_filter_menampilkan_semua(self):
        self.assertEqual(self.nama_lahan(), {'Lahan Berjalan', 'Lahan Selesai', 'Lahan Batal'})

    def test_filter_per_kelompok_status(self):
        self.assertEqual(self.nama_lahan(status='berjalan'), {'Lahan Berjalan'})
        self.assertEqual(self.nama_lahan(status='selesai'), {'Lahan Selesai'})
        self.assertEqual(self.nama_lahan(status='dibatalkan'), {'Lahan Batal'})

    def test_filter_ngawur_dianggap_semua(self):
        self.assertEqual(len(self.nama_lahan(status='ngawur')), 3)

    def test_jumlah_di_tiap_filter(self):
        response = self.client.get(self.url)
        jumlah = {f['kunci']: f['jumlah'] for f in response.context['filter_list']}
        self.assertEqual(jumlah, {'semua': 3, 'berjalan': 1, 'selesai': 1, 'dibatalkan': 1})

    def test_filter_cuma_menghitung_pesanan_sendiri(self):
        buat_pesanan(buat_lahan(buat_pemilik('dewi'), nama='Lahan Dewi'))
        self.assertNotIn('Lahan Dewi', self.nama_lahan())

    def test_htmx_cuma_mengirim_bagian_daftar(self):
        response = self.client.get(self.url, {'status': 'selesai'}, **HTMX)
        self.assertContains(response, 'Lahan Selesai')
        self.assertNotContains(response, 'Lahan Berjalan')
        self.assertNotContains(response, '<html')
        self.assertTemplateUsed(response, 'inspections/partials/_daftar.html')

    def test_halaman_penuh_memuat_layout(self):
        self.assertContains(self.client.get(self.url), '<html')

    def test_filter_kosong_menampilkan_pesan_filter(self):
        PesananPemeriksaan.objects.filter(pk=self.selesai.pk).delete()
        response = self.client.get(self.url, {'status': 'selesai'})
        self.assertContains(response, 'Nggak ada pesanan di filter ini')
