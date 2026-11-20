from django.test import TestCase
from django.urls import reverse


from .. import services
from ..models import PesananPemeriksaan
from ..tampilan import langkah_status
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_services import buat_petugas

Status = PesananPemeriksaan.Status


class DaftarDanDetailTests(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.lahan = buat_lahan(self.pemilik, nama='Kebun Cibodas')
        self.pesanan = buat_pesanan(self.lahan)
        self.lain = buat_pemilik('dewi')
        self.pesanan_lain = buat_pesanan(buat_lahan(self.lain, nama='Lahan Dewi'))

    def test_tamu_diarahkan_ke_login(self):
        for nama, args in (('daftar_pesanan', []), ('detail_pesanan', [self.pesanan.pk])):
            url = reverse(f'inspections:{nama}', args=args)
            self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}")

    def test_petugas_dapat_403(self):
        self.client.force_login(buat_petugas())
        self.assertEqual(self.client.get(reverse('inspections:daftar_pesanan')).status_code, 403)

    def test_daftar_cuma_menampilkan_pesanan_sendiri(self):
        self.client.force_login(self.pemilik)
        response = self.client.get(reverse('inspections:daftar_pesanan'))
        self.assertContains(response, self.pesanan.kode)
        self.assertContains(response, 'Kebun Cibodas')
        self.assertNotContains(response, 'Lahan Dewi')

    def test_daftar_kosong_menampilkan_pesan_ramah(self):
        self.client.force_login(buat_pemilik('baru'))
        self.assertContains(self.client.get(reverse('inspections:daftar_pesanan')), 'Belum ada pesanan')

    def test_detail_menampilkan_rincian_dan_riwayat(self):
        services.konfirmasi_pesanan(self.pesanan, buat_petugas(first_name='Bima'))
        self.client.force_login(self.pemilik)
        response = self.client.get(reverse('inspections:detail_pesanan', args=[self.pesanan.pk]))
        self.assertContains(response, 'Dikonfirmasi')
        self.assertContains(response, 'Bima')
        self.assertContains(response, 'Belum ditetapkan admin')

    def test_detail_pesanan_orang_lain_404(self):
        self.client.force_login(self.pemilik)
        response = self.client.get(reverse('inspections:detail_pesanan', args=[self.pesanan_lain.pk]))
        self.assertEqual(response.status_code, 404)

    def test_pesanan_dibatalkan_tampil_pesan_batal_tanpa_garis_status(self):
        services.ubah_status(self.pesanan, Status.DIBATALKAN, catatan='Salah lahan')
        self.client.force_login(self.pemilik)
        response = self.client.get(reverse('inspections:detail_pesanan', args=[self.pesanan.pk]))
        self.assertContains(response, 'Pesanan ini dibatalkan')
        self.assertContains(response, 'Salah lahan')
        self.assertNotContains(response, 'class="stepper')


class LangkahStatusTests(TestCase):
    def test_langkah_menandai_yang_sudah_lewat_dan_yang_sekarang(self):
        pesanan = buat_pesanan(buat_lahan(buat_pemilik()))
        pesanan.status = Status.DIJADWALKAN
        keadaan = [l['keadaan'] for l in langkah_status(pesanan)]
        self.assertEqual(keadaan, ['done', 'done', 'now', '', '', ''])

    def test_pesanan_selesai_semua_langkah_done(self):
        pesanan = buat_pesanan(buat_lahan(buat_pemilik()))
        pesanan.status = Status.SELESAI
        self.assertTrue(all(l['keadaan'] == 'done' for l in langkah_status(pesanan)))

    def test_pesanan_dibatalkan_tanpa_langkah(self):
        pesanan = buat_pesanan(buat_lahan(buat_pemilik()))
        pesanan.status = Status.DIBATALKAN
        self.assertIsNone(langkah_status(pesanan))
