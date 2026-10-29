from django.test import TestCase
from django.urls import reverse

from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_akses import buat_admin
from .test_services import buat_petugas


class LayoutStafTests(TestCase):
    """Akun admin (staf) bawaan perannya owner. Tampilannya tetap harus tampilan admin."""

    def setUp(self):
        self.admin = buat_admin()
        self.pesanan = buat_pesanan(buat_lahan(buat_pemilik('sari')))

    def test_admin_bawaan_perannya_owner_tapi_labelnya_admin(self):
        self.assertTrue(self.admin.is_owner)
        self.assertEqual(self.admin.role_label, 'Admin')

    def test_label_peran_lain_tetap(self):
        self.assertEqual(buat_pemilik('dewi').role_label, 'Pemilik Lahan')
        self.assertEqual(buat_petugas().role_label, 'Petugas Pemeriksa')

    def test_admin_nggak_melihat_tombol_dan_kartu_khusus_pemilik(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('inspections:kelola_daftar'))
        self.assertNotContains(response, reverse('lands:tambah_lahan'))
        self.assertNotContains(response, 'Satu lahan belum lengkap')
        self.assertNotContains(response, 'Pemilik Lahan</p>')

    def test_pemilik_tetap_melihatnya(self):
        self.client.force_login(self.pesanan.pemilik)
        response = self.client.get(reverse('inspections:daftar_pesanan'))
        self.assertContains(response, reverse('lands:tambah_lahan'))
        self.assertContains(response, 'Satu lahan belum lengkap')

    def test_catatan_khusus_pemilik_nggak_muncul_di_halaman_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('inspections:kelola_detail', args=[self.pesanan.pk]))
        self.assertNotContains(response, 'masih bisa sampai petugas menandai sampel diambil')
        self.client.force_login(self.pesanan.pemilik)
        response = self.client.get(reverse('inspections:detail_pesanan', args=[self.pesanan.pk]))
        self.assertContains(response, 'masih bisa sampai petugas menandai sampel diambil')
