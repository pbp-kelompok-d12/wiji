from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from .. import services
from ..models import PesananPemeriksaan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_services import buat_petugas

Status = PesananPemeriksaan.Status
HTMX = {'HTTP_HX_REQUEST': 'true'}


def hari(n):
    return date.today() + timedelta(days=n)


class AksiPemilikTestCase(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.pesanan = buat_pesanan(buat_lahan(self.pemilik))
        self.client.force_login(self.pemilik)

    def url(self, nama, pesanan=None):
        return reverse(f'inspections:{nama}', args=[(pesanan or self.pesanan).pk])

    def muat(self):
        self.pesanan.refresh_from_db()
        return self.pesanan

    def jadikan(self, status):
        PesananPemeriksaan.objects.filter(pk=self.pesanan.pk).update(status=status)


class AkunDanKepemilikanTests(AksiPemilikTestCase):
    def test_tamu_diarahkan_ke_login(self):
        self.client.logout()
        for nama in ('ubah_usulan', 'batalkan_pesanan', 'jadwal_ulang'):
            self.assertEqual(self.client.get(self.url(nama)).status_code, 302)

    def test_petugas_dapat_403(self):
        self.client.force_login(buat_petugas())
        for nama in ('ubah_usulan', 'batalkan_pesanan', 'jadwal_ulang'):
            self.assertEqual(self.client.get(self.url(nama)).status_code, 403)

    def test_pesanan_orang_lain_404_dan_nggak_berubah(self):
        lain = buat_pesanan(buat_lahan(buat_pemilik('dewi')))
        for nama in ('ubah_usulan', 'batalkan_pesanan', 'jadwal_ulang'):
            self.assertEqual(self.client.get(self.url(nama, lain)).status_code, 404)
        response = self.client.post(self.url('batalkan_pesanan', lain), {'alasan': 'Iseng'})
        self.assertEqual(response.status_code, 404)
        lain.refresh_from_db()
        self.assertEqual(lain.status, Status.DIAJUKAN)


class BatalkanTests(AksiPemilikTestCase):
    def test_halaman_biasa_batal_berhasil_lalu_ke_detail(self):
        response = self.client.post(self.url('batalkan_pesanan'), {'alasan': 'Salah lahan'})
        self.assertRedirects(response, self.url('detail_pesanan'))
        self.assertEqual(self.muat().status, Status.DIBATALKAN)
        self.assertEqual(self.pesanan.riwayat.last().catatan, 'Salah lahan')

    def test_alasan_kosong_ditolak(self):
        response = self.client.post(self.url('batalkan_pesanan'), {'alasan': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn('alasan', response.context['form'].errors)
        self.assertEqual(self.muat().status, Status.DIAJUKAN)

    def test_setelah_sampel_diambil_ditolak(self):
        self.jadikan(Status.SAMPEL_DIAMBIL)
        response = self.client.post(self.url('batalkan_pesanan'), {'alasan': 'Terlambat'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.muat().status, Status.SAMPEL_DIAMBIL)
        self.assertContains(response, 'nggak bisa dibatalkan')

    def test_htmx_buka_modal_tanpa_layout(self):
        response = self.client.get(self.url('batalkan_pesanan'), **HTMX)
        self.assertContains(response, 'Batalkan pesanan?')
        self.assertContains(response, 'class="modal is-open"')
        self.assertNotContains(response, '<html')

    def test_htmx_berhasil_ganti_isi_detail_dan_tutup_modal(self):
        response = self.client.post(self.url('batalkan_pesanan'), {'alasan': 'Salah lahan'}, **HTMX)
        self.assertContains(response, 'id="konten-pesanan"')
        self.assertContains(response, 'Pesanan dibatalkan.')
        self.assertContains(response, 'hx-swap-oob="true"')
        self.assertEqual(self.muat().status, Status.DIBATALKAN)

    def test_htmx_gagal_validasi_tampil_lagi_di_modal(self):
        response = self.client.post(self.url('batalkan_pesanan'), {'alasan': ''}, **HTMX)
        self.assertEqual(response['HX-Retarget'], '#modal-slot')
        self.assertContains(response, 'Alasan pembatalan wajib diisi.')
        self.assertEqual(self.muat().status, Status.DIAJUKAN)


class JadwalUlangViewTests(AksiPemilikTestCase):
    def setUp(self):
        super().setUp()
        services.konfirmasi_pesanan(self.pesanan, buat_petugas())
        services.jadwalkan_pesanan(self.pesanan, hari(4), 'pagi')
        self.data = {'tanggal': hari(10).isoformat(), 'sesi': 'siang', 'alasan': 'Ada acara'}

    def test_jadwal_ulang_berhasil(self):
        response = self.client.post(self.url('jadwal_ulang'), self.data)
        self.assertRedirects(response, self.url('detail_pesanan'))
        pesanan = self.muat()
        self.assertEqual(pesanan.status, Status.DIKONFIRMASI)
        self.assertEqual((pesanan.tanggal_usulan, pesanan.sesi_usulan), (hari(10), 'siang'))
        self.assertIsNone(pesanan.tanggal_final)

    def test_tanggal_di_luar_rentang_dan_alasan_kosong_ditolak(self):
        for ubah in ({'tanggal': hari(0).isoformat()}, {'tanggal': hari(31).isoformat()}, {'alasan': ''}):
            with self.subTest(ubah=ubah):
                response = self.client.post(self.url('jadwal_ulang'), {**self.data, **ubah})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
        self.assertEqual(self.muat().status, Status.DIJADWALKAN)

    def test_saat_masih_diajukan_ditolak(self):
        self.jadikan(Status.DIAJUKAN)
        response = self.client.post(self.url('jadwal_ulang'), self.data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dikonfirmasi atau Dijadwalkan')

    def test_htmx_berhasil_menampilkan_riwayat_terbaru(self):
        response = self.client.post(self.url('jadwal_ulang'), self.data, **HTMX)
        self.assertContains(response, 'Permintaan jadwal ulang terkirim')
        self.assertContains(response, 'Ada acara')


class UbahUsulanViewTests(AksiPemilikTestCase):
    def test_form_terisi_data_sekarang(self):
        response = self.client.get(self.url('ubah_usulan'))
        self.assertEqual(response.context['form'].initial['tanggal'], self.pesanan.tanggal_usulan)

    def test_ubah_berhasil_selama_diajukan(self):
        data = {'tanggal': hari(7).isoformat(), 'sesi': 'siang', 'catatan': 'Pindah ke siang'}
        self.client.post(self.url('ubah_usulan'), data)
        pesanan = self.muat()
        self.assertEqual((pesanan.tanggal_usulan, pesanan.sesi_usulan, pesanan.catatan), (hari(7), 'siang', 'Pindah ke siang'))

    def test_ditolak_setelah_dikonfirmasi(self):
        services.konfirmasi_pesanan(self.pesanan, buat_petugas())
        data = {'tanggal': hari(7).isoformat(), 'sesi': 'siang', 'catatan': ''}
        response = self.client.post(self.url('ubah_usulan'), data)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(self.muat().tanggal_usulan, hari(7))


class TombolDiDetailTests(AksiPemilikTestCase):
    def tombol(self):
        response = self.client.get(self.url('detail_pesanan'))
        isi = response.content.decode()
        return {nama: self.url(nama) in isi for nama in ('ubah_usulan', 'jadwal_ulang', 'batalkan_pesanan')}

    def test_tombol_sesuai_status(self):
        harapan = {
            Status.DIAJUKAN: (True, False, True),
            Status.DIKONFIRMASI: (False, True, True),
            Status.DIJADWALKAN: (False, True, True),
            Status.SAMPEL_DIAMBIL: (False, False, False),
            Status.DIPROSES: (False, False, False),
            Status.SELESAI: (False, False, False),
            Status.DIBATALKAN: (False, False, False),
        }
        for status, (ubah, ulang, batal) in harapan.items():
            with self.subTest(status=status):
                self.jadikan(status)
                self.assertEqual(
                    list(self.tombol().values()), [ubah, ulang, batal],
                )
