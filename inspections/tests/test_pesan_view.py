from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from ..forms import lahan_bisa_dipesan
from ..models import JenisPemeriksaan, PesananPemeriksaan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_services import buat_petugas


def hari(n):
    return (date.today() + timedelta(days=n)).isoformat()


class PesanPemeriksaanTests(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.lahan = buat_lahan(self.pemilik, nama='Kebun Cibodas')
        self.jenis = JenisPemeriksaan.objects.get(slug='unsur-hara')
        self.url = reverse('inspections:pesan_pemeriksaan')
        self.data = {
            'lahan': str(self.lahan.pk), 'jenis': self.jenis.pk,
            'tanggal_usulan': hari(3), 'sesi_usulan': 'siang', 'catatan': 'Parkir di warung',
        }
        self.client.force_login(self.pemilik)

    def test_tamu_diarahkan_ke_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), f"{reverse('accounts:login')}?next={self.url}")

    def test_petugas_dapat_403(self):
        self.client.force_login(buat_petugas())
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_form_tampil_dengan_lahan_dan_tiga_jenis(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Kebun Cibodas')
        for nama in ('Dasar', 'Unsur Hara', 'Kontaminan'):
            self.assertContains(response, nama)

    def test_lahan_dari_query_langsung_terpilih(self):
        response = self.client.get(f'{self.url}?lahan={self.lahan.pk}')
        self.assertEqual(response.context['form'].initial['lahan'], str(self.lahan.pk))

    def test_pesan_berhasil_membuat_pesanan_diajukan_lalu_ke_detail(self):
        response = self.client.post(self.url, self.data)
        pesanan = PesananPemeriksaan.objects.get()
        self.assertRedirects(response, reverse('inspections:detail_pesanan', args=[pesanan.pk]))
        self.assertEqual(pesanan.status, 'diajukan')
        self.assertEqual((pesanan.jenis, pesanan.sesi_usulan, pesanan.catatan), (self.jenis, 'siang', 'Parkir di warung'))
        self.assertEqual(pesanan.lahan, self.lahan)

    def test_tanggal_kemarin_dan_lewat_30_hari_ditolak(self):
        for n in (0, -2, 31):
            with self.subTest(n=n):
                response = self.client.post(self.url, {**self.data, 'tanggal_usulan': hari(n)})
                self.assertEqual(response.status_code, 200)
                self.assertIn('tanggal_usulan', response.context['form'].errors)
        self.assertFalse(PesananPemeriksaan.objects.exists())

    def test_data_kosong_menampilkan_error_per_kolom(self):
        response = self.client.post(self.url, {})
        self.assertEqual(
            set(response.context['form'].errors), {'lahan', 'jenis', 'tanggal_usulan', 'sesi_usulan'},
        )

    def test_lahan_orang_lain_nggak_ada_di_pilihan(self):
        punya_dewi = buat_lahan(buat_pemilik('dewi'), nama='Lahan Dewi')
        self.assertNotContains(self.client.get(self.url), 'Lahan Dewi')
        response = self.client.post(self.url, {**self.data, 'lahan': str(punya_dewi.pk)})
        self.assertIn('lahan', response.context['form'].errors)
        self.assertFalse(PesananPemeriksaan.objects.exists())

    def test_jenis_nonaktif_ditolak(self):
        self.jenis.aktif = False
        self.jenis.save()
        self.assertNotContains(self.client.get(self.url), 'Unsur Hara')
        response = self.client.post(self.url, self.data)
        self.assertIn('jenis', response.context['form'].errors)

    def test_pemesanan_kedua_di_lahan_yang_sama_ditolak(self):
        self.client.post(self.url, self.data)
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('lahan', response.context['form'].errors)
        self.assertEqual(PesananPemeriksaan.objects.count(), 1)

    def test_tanpa_lahan_yang_bisa_dipesan_tampil_penjelasan(self):
        self.lahan.arsipkan()
        response = self.client.get(self.url)
        self.assertContains(response, 'Belum ada lahan yang bisa dipesan')


class LahanBisaDipesanTests(TestCase):
    def test_hanya_lahan_aktif_lengkap_tanpa_pesanan_berjalan(self):
        pemilik = buat_pemilik()
        siap = buat_lahan(pemilik, nama='Siap')
        buat_lahan(pemilik, nama='Draf', penggunaan=None)
        buat_lahan(pemilik, nama='Tanpa koordinat', latitude=None, longitude=None)
        buat_lahan(pemilik, nama='Arsip').arsipkan()
        buat_pesanan(buat_lahan(pemilik, nama='Sedang dipesan'))
        self.assertEqual(list(lahan_bisa_dipesan(pemilik)), [siap])
