from django.test import TestCase
from django.urls import reverse

from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_services import buat_petugas


class LayoutAplikasiTests(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.pesanan = buat_pesanan(buat_lahan(self.pemilik))
        self.client.force_login(self.pemilik)

    def test_halaman_bisa_mengganti_penunjuk_halaman_di_bar_atas(self):
        response = self.client.get(reverse('inspections:detail_pesanan', args=[self.pesanan.pk]))
        self.assertContains(response, f'Pemeriksaan / {self.pesanan.kode}')

    def test_dashboard_tetap_menampilkan_penunjuk_dashboard(self):
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'ic"><use href="#i-home"/></svg>Dashboard')

    def test_tombol_tambah_lahan_di_bar_atas_mengarah_ke_form_lahan(self):
        response = self.client.get(reverse('inspections:daftar_pesanan'))
        self.assertContains(response, f'href="{reverse("lands:tambah_lahan")}"')

    def test_petugas_nggak_melihat_tombol_tambah_lahan(self):
        self.client.force_login(buat_petugas())
        response = self.client.get(reverse('dashboard:home'))
        self.assertNotContains(response, reverse('lands:tambah_lahan'))

    def test_ikon_kembali_tersedia(self):
        response = self.client.get(reverse('inspections:detail_pesanan', args=[self.pesanan.pk]))
        self.assertContains(response, 'id="i-back"')
