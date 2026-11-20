import json
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from .. import services
from ..models import JenisPemeriksaan, PesananPemeriksaan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_services import buat_petugas


def hari(n):
    return (date.today() + timedelta(days=n)).isoformat()


class ApiPesananTestCase(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.lahan = buat_lahan(self.pemilik, nama='Kebun Cibodas')
        self.client.force_login(self.pemilik)

    def kirim(self, nama, data, args=None):
        return self.client.post(
            reverse(f'inspections:{nama}', args=args or []), json.dumps(data), content_type='application/json',
        )


class AksesApiTests(ApiPesananTestCase):
    def test_tamu_dapat_401_json(self):
        self.client.logout()
        response = self.client.get(reverse('inspections:api_pesanan'))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_petugas_dapat_403(self):
        self.client.force_login(buat_petugas())
        self.assertEqual(self.client.get(reverse('inspections:api_pesanan')).status_code, 403)

    def test_method_lain_ditolak(self):
        self.assertEqual(self.client.delete(reverse('inspections:api_pesanan')).status_code, 405)


class DaftarDanDetailApiTests(ApiPesananTestCase):
    def test_daftar_cuma_berisi_pesanan_sendiri(self):
        milik = buat_pesanan(self.lahan)
        buat_pesanan(buat_lahan(buat_pemilik('dewi'), nama='Lahan Dewi'))
        hasil = self.client.get(reverse('inspections:api_pesanan')).json()['hasil']
        self.assertEqual([p['id'] for p in hasil], [milik.pk])
        self.assertEqual(hasil[0]['lahan']['nama'], 'Kebun Cibodas')
        self.assertEqual(hasil[0]['status'], 'diajukan')

    def test_daftar_bisa_difilter_status(self):
        buat_pesanan(self.lahan)
        response = self.client.get(reverse('inspections:api_pesanan'), {'status': 'selesai'})
        self.assertEqual(response.json()['hasil'], [])

    def test_detail_memuat_riwayat(self):
        pesanan = buat_pesanan(self.lahan)
        services.konfirmasi_pesanan(pesanan, buat_petugas(first_name='Bima'))
        data = self.client.get(reverse('inspections:api_detail_pesanan', args=[pesanan.pk])).json()
        self.assertEqual(data['status'], 'dikonfirmasi')
        self.assertEqual(data['petugas'], 'Bima')
        self.assertEqual([r['status_sesudah'] for r in data['riwayat']], ['dikonfirmasi'])

    def test_detail_pesanan_orang_lain_404_tanpa_bocor(self):
        lain = buat_pesanan(buat_lahan(buat_pemilik('dewi'), nama='Lahan Dewi'))
        response = self.client.get(reverse('inspections:api_detail_pesanan', args=[lain.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('Dewi', response.content.decode())


class BuatPesananApiTests(ApiPesananTestCase):
    def data(self, **ubah):
        return {
            'lahan': str(self.lahan.pk), 'jenis': JenisPemeriksaan.objects.get(slug='dasar').pk,
            'tanggal_usulan': hari(3), 'sesi_usulan': 'pagi', 'catatan': 'Parkir di warung', **ubah,
        }

    def test_buat_lewat_json(self):
        response = self.kirim('api_pesanan', self.data())
        self.assertEqual(response.status_code, 201)
        pesanan = PesananPemeriksaan.objects.get()
        self.assertEqual(response.json()['id'], pesanan.pk)
        self.assertEqual(pesanan.status, 'diajukan')

    def test_buat_lewat_form_biasa(self):
        response = self.client.post(reverse('inspections:api_pesanan'), self.data())
        self.assertEqual(response.status_code, 201)

    def test_data_salah_dibalas_400_per_kolom(self):
        response = self.kirim('api_pesanan', self.data(tanggal_usulan=hari(0), sesi_usulan='malam'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()['errors']), {'tanggal_usulan', 'sesi_usulan'})
        self.assertFalse(PesananPemeriksaan.objects.exists())

    def test_lahan_orang_lain_ditolak(self):
        punya_dewi = buat_lahan(buat_pemilik('dewi'))
        response = self.kirim('api_pesanan', self.data(lahan=str(punya_dewi.pk)))
        self.assertEqual(response.status_code, 400)
        self.assertIn('lahan', response.json()['errors'])

    def test_pesanan_aktif_ganda_ditolak(self):
        self.kirim('api_pesanan', self.data())
        response = self.kirim('api_pesanan', self.data())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PesananPemeriksaan.objects.count(), 1)

    def test_json_rusak_dibalas_400(self):
        response = self.client.post(reverse('inspections:api_pesanan'), '{rusak', content_type='application/json')
        self.assertEqual(response.status_code, 400)


class AksiApiTests(ApiPesananTestCase):
    def setUp(self):
        super().setUp()
        self.pesanan = buat_pesanan(self.lahan)

    def test_batalkan(self):
        response = self.kirim('api_batalkan', {'alasan': 'Salah lahan'}, [self.pesanan.pk])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'dibatalkan')

    def test_batalkan_tanpa_alasan_400(self):
        response = self.kirim('api_batalkan', {}, [self.pesanan.pk])
        self.assertEqual(response.status_code, 400)
        self.assertIn('alasan', response.json()['errors'])

    def test_batalkan_setelah_sampel_diambil_400(self):
        PesananPemeriksaan.objects.filter(pk=self.pesanan.pk).update(status='sampel_diambil')
        response = self.kirim('api_batalkan', {'alasan': 'Terlambat'}, [self.pesanan.pk])
        self.assertEqual(response.status_code, 400)
        self.assertIn('__all__', response.json()['errors'])

    def test_jadwal_ulang(self):
        services.konfirmasi_pesanan(self.pesanan, buat_petugas())
        data = {'tanggal': hari(10), 'sesi': 'siang', 'alasan': 'Ada acara'}
        response = self.kirim('api_jadwal_ulang', data, [self.pesanan.pk])
        self.assertEqual(response.status_code, 200)
        hasil = response.json()
        self.assertEqual((hasil['status'], hasil['tanggal_usulan'], hasil['sesi_usulan']), ('dikonfirmasi', hari(10), 'siang'))
        self.assertIsNone(hasil['tanggal_final'])

    def test_aksi_cuma_lewat_post(self):
        response = self.client.get(reverse('inspections:api_batalkan', args=[self.pesanan.pk]))
        self.assertEqual(response.status_code, 405)

    def test_aksi_di_pesanan_orang_lain_404(self):
        lain = buat_pesanan(buat_lahan(buat_pemilik('dewi')))
        response = self.kirim('api_batalkan', {'alasan': 'Iseng'}, [lain.pk])
        self.assertEqual(response.status_code, 404)
        lain.refresh_from_db()
        self.assertEqual(lain.status, 'diajukan')
