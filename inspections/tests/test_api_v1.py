"""Test API DRF Modul B (/api/v1/jenis-pemeriksaan/, /api/v1/pesanan/) buat aplikasi mobile."""
from datetime import date, timedelta

from rest_framework.test import APIClient, APITestCase

from ..models import JenisPemeriksaan, PesananPemeriksaan, RiwayatPesanan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_services import buat_petugas

URL_JENIS = '/api/v1/jenis-pemeriksaan/'
URL_PESANAN = '/api/v1/pesanan/'


def hari(n):
    return (date.today() + timedelta(days=n)).isoformat()


class ApiV1TestCase(APITestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.lahan = buat_lahan(self.pemilik, nama='Kebun Cibodas')
        self.jenis = JenisPemeriksaan.objects.get(slug='dasar')
        self.client.force_authenticate(self.pemilik)

    def data_pesanan(self, **ubah):
        return {
            'lahan': str(self.lahan.pk), 'jenis': self.jenis.pk,
            'tanggal_usulan': hari(3), 'sesi_usulan': 'pagi', 'catatan': 'Parkir di balai desa',
            **ubah,
        }


class AksesTests(ApiV1TestCase):
    def test_tamu_ditolak(self):
        self.client.force_authenticate(None)
        for url in (URL_JENIS, URL_PESANAN):
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_petugas_nggak_boleh_liat_pesanan_pemilik(self):
        self.client.force_authenticate(buat_petugas())
        self.assertEqual(self.client.get(URL_PESANAN).status_code, 403)
        self.assertEqual(self.client.post(URL_PESANAN, self.data_pesanan(), format='json').status_code, 403)

    def test_method_yang_nggak_ada_ditolak(self):
        self.assertEqual(self.client.delete(URL_PESANAN).status_code, 405)
        pesanan = buat_pesanan(self.lahan)
        self.assertEqual(self.client.post(f'{URL_PESANAN}{pesanan.pk}/').status_code, 405)

    def test_post_lewat_sesi_tanpa_csrf_ditolak(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.pemilik)
        response = client.post(URL_PESANAN, self.data_pesanan(), format='json')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(PesananPemeriksaan.objects.exists())


class JenisTests(ApiV1TestCase):
    def test_cuma_jenis_aktif(self):
        JenisPemeriksaan.objects.filter(slug='kontaminan').update(aktif=False)
        response = self.client.get(URL_JENIS)
        self.assertEqual(response.status_code, 200)
        slugs = [j['slug'] for j in response.data]
        self.assertIn('dasar', slugs)
        self.assertNotIn('kontaminan', slugs)
        self.assertEqual(set(response.data[0]), {'id', 'nama', 'slug', 'deskripsi', 'tingkat'})


class DaftarDanDetailTests(ApiV1TestCase):
    def test_daftar_cuma_pesanan_sendiri(self):
        milik = buat_pesanan(self.lahan)
        buat_pesanan(buat_lahan(buat_pemilik('dewi'), nama='Lahan Dewi'))

        response = self.client.get(URL_PESANAN)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([p['id'] for p in response.data], [milik.pk])
        pesanan = response.data[0]
        self.assertEqual(pesanan['kode'], milik.kode)
        self.assertEqual(pesanan['status_label'], 'Diajukan')
        self.assertEqual(pesanan['lahan'], {'id': str(self.lahan.pk), 'nama': 'Kebun Cibodas'})
        self.assertEqual(pesanan['jenis']['slug'], 'dasar')
        self.assertIsNone(pesanan['petugas'])
        self.assertNotIn('riwayat', pesanan)

    def test_daftar_bisa_difilter_status(self):
        buat_pesanan(self.lahan)
        self.assertEqual(len(self.client.get(URL_PESANAN, {'status': 'diajukan'}).data), 1)
        self.assertEqual(self.client.get(URL_PESANAN, {'status': 'selesai'}).data, [])

    def test_detail_ada_riwayatnya(self):
        pesanan = self.client.post(URL_PESANAN, self.data_pesanan(), format='json').data

        response = self.client.get(f"{URL_PESANAN}{pesanan['id']}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['riwayat']), 1)
        self.assertEqual(response.data['riwayat'][0]['status_sesudah'], 'diajukan')
        self.assertEqual(response.data['riwayat'][0]['oleh'], self.pemilik.display_name)

    def test_detail_pesanan_orang_lain_404(self):
        punya_dewi = buat_pesanan(buat_lahan(buat_pemilik('dewi'), nama='Lahan Dewi'))
        self.assertEqual(self.client.get(f'{URL_PESANAN}{punya_dewi.pk}/').status_code, 404)
        self.assertEqual(self.client.get(f'{URL_PESANAN}9999/').status_code, 404)


class PesanTests(ApiV1TestCase):
    def test_pesan_berhasil(self):
        response = self.client.post(URL_PESANAN, self.data_pesanan(), format='json')

        self.assertEqual(response.status_code, 201)
        pesanan = PesananPemeriksaan.objects.get()
        self.assertEqual(response.data['kode'], pesanan.kode)
        self.assertEqual(pesanan.lahan, self.lahan)
        self.assertEqual(pesanan.status, 'diajukan')
        self.assertEqual(pesanan.catatan, 'Parkir di balai desa')
        self.assertEqual(RiwayatPesanan.objects.filter(pesanan=pesanan).count(), 1)

    def test_field_yang_dijaga_server_nggak_bisa_diisi(self):
        petugas = buat_petugas()
        response = self.client.post(
            URL_PESANAN,
            self.data_pesanan(status='selesai', petugas=petugas.pk, tanggal_final=hari(4)),
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        pesanan = PesananPemeriksaan.objects.get()
        self.assertEqual(pesanan.status, 'diajukan')
        self.assertIsNone(pesanan.petugas)
        self.assertIsNone(pesanan.tanggal_final)

    def test_input_salah_ditolak_per_field(self):
        lahan_dewi = buat_lahan(buat_pemilik('dewi'), nama='Lahan Dewi')
        JenisPemeriksaan.objects.filter(slug='kontaminan').update(aktif=False)
        kontaminan = JenisPemeriksaan.objects.get(slug='kontaminan')

        kasus = [
            ({'lahan': str(lahan_dewi.pk)}, 'lahan'),
            ({'jenis': kontaminan.pk}, 'jenis'),
            ({'tanggal_usulan': hari(0)}, 'tanggal_usulan'),
            ({'tanggal_usulan': hari(31)}, 'tanggal_usulan'),
            ({'sesi_usulan': 'malam'}, 'sesi_usulan'),
        ]
        for ubah, field in kasus:
            with self.subTest(field=field, ubah=ubah):
                response = self.client.post(URL_PESANAN, self.data_pesanan(**ubah), format='json')
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)
        self.assertFalse(PesananPemeriksaan.objects.exists())

    def test_satu_lahan_cuma_boleh_satu_pesanan_aktif(self):
        buat_pesanan(self.lahan)

        response = self.client.post(URL_PESANAN, self.data_pesanan(), format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['lahan'], ['Lahan ini masih punya pesanan yang berjalan.'])
        self.assertEqual(PesananPemeriksaan.objects.count(), 1)

    def test_lahan_arsip_atau_tanpa_koordinat_ditolak(self):
        diarsip = buat_lahan(self.pemilik, nama='Lahan Lama', diarsipkan=True)
        tanpa_titik = buat_lahan(self.pemilik, nama='Lahan Baru', latitude=None, longitude=None)

        for lahan in (diarsip, tanpa_titik):
            with self.subTest(lahan=lahan.nama):
                response = self.client.post(
                    URL_PESANAN, self.data_pesanan(lahan=str(lahan.pk)), format='json',
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn('lahan', response.data)
