from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from .. import services
from ..models import PesananPemeriksaan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_akses import buat_admin
from .test_services import buat_petugas

Status = PesananPemeriksaan.Status
HTMX = {'HTTP_HX_REQUEST': 'true'}


class LanjutTestCase(TestCase):
    def setUp(self):
        self.bima = buat_petugas('bima')
        self.pesanan = buat_pesanan(buat_lahan(buat_pemilik()))
        services.konfirmasi_pesanan(self.pesanan, self.bima)
        services.jadwalkan_pesanan(self.pesanan, date.today() + timedelta(days=2), 'pagi')
        self.url = reverse('inspections:tugas_lanjut', args=[self.pesanan.pk])
        self.detail = reverse('inspections:tugas_detail', args=[self.pesanan.pk])
        self.client.force_login(self.bima)

    def muat(self):
        self.pesanan.refresh_from_db()
        return self.pesanan

    def jadikan(self, status):
        PesananPemeriksaan.objects.filter(pk=self.pesanan.pk).update(status=status)


class LanjutStatusTests(LanjutTestCase):
    def test_dua_langkah_sampai_diproses_dan_tercatat(self):
        self.assertRedirects(self.client.post(self.url, {'ke': 'sampel_diambil'}), self.detail)
        self.assertEqual(self.muat().status, Status.SAMPEL_DIAMBIL)
        self.client.post(self.url, {'ke': 'diproses'})
        self.assertEqual(self.muat().status, Status.DIPROSES)
        terakhir = self.pesanan.riwayat.order_by('id').last()
        self.assertEqual((terakhir.status_sebelum, terakhir.status_sesudah, terakhir.oleh), ('sampel_diambil', 'diproses', self.bima))

    def test_petugas_nggak_bisa_menyelesaikan_pesanan(self):
        self.jadikan(Status.DIPROSES)
        self.client.post(self.url, {'ke': 'selesai'})
        self.assertEqual(self.muat().status, Status.DIPROSES)

    def test_nggak_bisa_melompati_langkah(self):
        self.client.post(self.url, {'ke': 'diproses'})
        self.assertEqual(self.muat().status, Status.DIJADWALKAN)

    def test_klik_dobel_nggak_memajukan_dua_langkah(self):
        self.client.post(self.url, {'ke': 'sampel_diambil'})
        response = self.client.post(self.url, {'ke': 'sampel_diambil'}, follow=True)
        self.assertEqual(self.muat().status, Status.SAMPEL_DIAMBIL)
        self.assertContains(response, 'Status pesanan sudah berubah')

    def test_tanpa_tujuan_ditolak(self):
        self.client.post(self.url, {})
        self.assertEqual(self.muat().status, Status.DIJADWALKAN)

    def test_belum_dijadwalkan_nggak_bisa_diambil_sampelnya(self):
        self.jadikan(Status.DIKONFIRMASI)
        self.client.post(self.url, {'ke': 'sampel_diambil'})
        self.assertEqual(self.muat().status, Status.DIKONFIRMASI)

    def test_cuma_lewat_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class LanjutAksesTests(LanjutTestCase):
    def test_petugas_lain_dapat_404_dan_status_nggak_berubah(self):
        self.client.force_login(buat_petugas('laras'))
        self.assertEqual(self.client.post(self.url, {'ke': 'sampel_diambil'}).status_code, 404)
        self.assertEqual(self.muat().status, Status.DIJADWALKAN)

    def test_pemilik_dan_admin_dapat_403(self):
        for user in (self.pesanan.pemilik, buat_admin()):
            self.client.force_login(user)
            self.assertEqual(self.client.post(self.url, {'ke': 'sampel_diambil'}).status_code, 403)
        self.assertEqual(self.muat().status, Status.DIJADWALKAN)

    def test_tamu_diarahkan_ke_login(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {'ke': 'sampel_diambil'}).status_code, 302)
        self.assertEqual(self.muat().status, Status.DIJADWALKAN)


class LanjutHtmxTests(LanjutTestCase):
    def test_berhasil_mengganti_isi_detail(self):
        response = self.client.post(self.url, {'ke': 'sampel_diambil'}, **HTMX)
        self.assertContains(response, 'id="konten-pesanan"')
        self.assertContains(response, 'Sampel ditandai sudah diambil.')
        self.assertContains(response, 'Mulai proses')
        self.assertNotContains(response, '<html')

    def test_status_basi_menampilkan_pesan_tanpa_mengubah_apa_apa(self):
        self.jadikan(Status.SAMPEL_DIAMBIL)
        response = self.client.post(self.url, {'ke': 'sampel_diambil'}, **HTMX)
        self.assertContains(response, 'Status pesanan sudah berubah')
        self.assertEqual(self.muat().status, Status.SAMPEL_DIAMBIL)


class TombolDetailPetugasTests(LanjutTestCase):
    def teks_tombol(self):
        isi = self.client.get(self.detail).content.decode()
        return [t for t in ('Tandai sampel diambil', 'Mulai proses') if t in isi]

    def test_tombol_sesuai_status(self):
        harapan = {
            Status.DIKONFIRMASI: [],
            Status.DIJADWALKAN: ['Tandai sampel diambil'],
            Status.SAMPEL_DIAMBIL: ['Mulai proses'],
            Status.DIPROSES: [],
            Status.SELESAI: [],
            Status.DIBATALKAN: [],
        }
        for status, tombol in harapan.items():
            with self.subTest(status=status):
                self.jadikan(status)
                self.assertEqual(self.teks_tombol(), tombol)

    def test_petunjuk_saat_menunggu_jadwal_dan_saat_diproses(self):
        self.jadikan(Status.DIKONFIRMASI)
        self.assertContains(self.client.get(self.detail), 'Menunggu admin menetapkan jadwal')
        self.jadikan(Status.DIPROSES)
        self.assertContains(self.client.get(self.detail), 'modul hasil pemeriksaan')

    def test_pemilik_melihat_perubahan_dari_petugas_di_riwayatnya(self):
        self.client.post(self.url, {'ke': 'sampel_diambil'})
        self.client.force_login(self.pesanan.pemilik)
        response = self.client.get(reverse('inspections:detail_pesanan', args=[self.pesanan.pk]))
        self.assertContains(response, 'Sampel diambil')
