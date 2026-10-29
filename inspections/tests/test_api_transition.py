import json
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from .. import services
from ..models import PesananPemeriksaan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_akses import buat_admin
from .test_services import buat_petugas

Status = PesananPemeriksaan.Status


def hari(n):
    return (date.today() + timedelta(days=n)).isoformat()


class TransitionTestCase(TestCase):
    def setUp(self):
        self.admin = buat_admin()
        self.bima = buat_petugas('bima', first_name='Bima')
        self.laras = buat_petugas('laras', first_name='Laras')
        self.pemilik = buat_pemilik()
        self.pesanan = buat_pesanan(buat_lahan(self.pemilik))
        self.url = reverse('inspections:api_transition', args=[self.pesanan.pk])

    def kirim(self, data, user=None, url=None):
        if user is not None:
            self.client.force_login(user)
        return self.client.post(url or self.url, json.dumps(data), content_type='application/json')

    def muat(self):
        self.pesanan.refresh_from_db()
        return self.pesanan

    def jadikan(self, status):
        PesananPemeriksaan.objects.filter(pk=self.pesanan.pk).update(status=status)


class AksesTransitionTests(TransitionTestCase):
    def test_tamu_dapat_401_json(self):
        response = self.kirim({'ke': 'dikonfirmasi'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_pemilik_dapat_403(self):
        self.assertEqual(self.kirim({'ke': 'dibatalkan', 'alasan': 'Iseng'}, self.pemilik).status_code, 403)
        self.assertEqual(self.muat().status, Status.DIAJUKAN)

    def test_cuma_lewat_post(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_pesanan_nggak_ada_404(self):
        url = reverse('inspections:api_transition', args=[9999])
        self.assertEqual(self.kirim({'ke': 'dibatalkan'}, self.admin, url).status_code, 404)

    def test_json_rusak_400(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, '{rusak', content_type='application/json')
        self.assertEqual(response.status_code, 400)


class TransitionAdminTests(TransitionTestCase):
    def test_tugaskan_lalu_jadwalkan_lalu_batalkan(self):
        r = self.kirim({'ke': 'dikonfirmasi', 'petugas': self.bima.pk, 'catatan': 'Dekat'}, self.admin)
        self.assertEqual((r.status_code, r.json()['status'], r.json()['petugas']), (200, 'dikonfirmasi', 'Bima'))
        r = self.kirim({'ke': 'dijadwalkan', 'tanggal': hari(4), 'sesi': 'siang'})
        self.assertEqual((r.status_code, r.json()['status'], r.json()['tanggal_final']), (200, 'dijadwalkan', hari(4)))
        r = self.kirim({'ke': 'dibatalkan', 'alasan': 'Lahan dipakai'})
        self.assertEqual((r.status_code, r.json()['status']), (200, 'dibatalkan'))
        riwayat = r.json()['riwayat']
        self.assertEqual([x['status_sesudah'] for x in riwayat], ['dikonfirmasi', 'dijadwalkan', 'dibatalkan'])
        self.assertEqual(riwayat[-1]['oleh'], self.admin.display_name)

    def test_isian_kurang_dibalas_400_per_kolom(self):
        r = self.kirim({'ke': 'dikonfirmasi'}, self.admin)
        self.assertEqual((r.status_code, set(r.json()['errors'])), (400, {'petugas'}))
        r = self.kirim({'ke': 'dibatalkan'})
        self.assertEqual(set(r.json()['errors']), {'alasan'})
        self.assertEqual(self.muat().status, Status.DIAJUKAN)

    def test_tujuan_nggak_dikenal_ditolak(self):
        for ke in ('', 'selesai', 'diproses', 'sampel_diambil', 'ngawur'):
            with self.subTest(ke=ke):
                r = self.kirim({'ke': ke}, self.admin)
                self.assertEqual(r.status_code, 400)
                self.assertIn('ke', r.json()['errors'])
        self.assertEqual(self.muat().status, Status.DIAJUKAN)

    def test_lompat_status_ditolak_oleh_aturan(self):
        r = self.kirim({'ke': 'dijadwalkan', 'tanggal': hari(4), 'sesi': 'pagi'}, self.admin)
        self.assertEqual(r.status_code, 400)
        self.assertIn('__all__', r.json()['errors'])
        self.assertEqual(self.muat().status, Status.DIAJUKAN)

    def test_pemilik_bukan_petugas_ditolak(self):
        r = self.kirim({'ke': 'dikonfirmasi', 'petugas': self.pemilik.pk}, self.admin)
        self.assertEqual(set(r.json()['errors']), {'petugas'})

    def test_respons_nggak_membocorkan_email_pemilik(self):
        r = self.kirim({'ke': 'dikonfirmasi', 'petugas': self.bima.pk}, self.admin)
        self.assertNotIn(self.pemilik.email, r.content.decode())


class TransitionPetugasTests(TransitionTestCase):
    def setUp(self):
        super().setUp()
        services.konfirmasi_pesanan(self.pesanan, self.bima)
        services.jadwalkan_pesanan(self.pesanan, date.today() + timedelta(days=2), 'pagi')

    def test_dua_langkah_sampai_diproses(self):
        r = self.kirim({'ke': 'sampel_diambil'}, self.bima)
        self.assertEqual((r.status_code, r.json()['status']), (200, 'sampel_diambil'))
        r = self.kirim({'ke': 'diproses'})
        self.assertEqual((r.status_code, r.json()['status']), (200, 'diproses'))
        self.assertEqual(r.json()['riwayat'][-1]['oleh'], 'Bima')

    def test_nggak_bisa_melompati_atau_menyelesaikan(self):
        for ke in ('diproses', 'selesai', 'dibatalkan', 'dikonfirmasi', ''):
            with self.subTest(ke=ke):
                self.assertEqual(self.kirim({'ke': ke}, self.bima).status_code, 400)
        self.assertEqual(self.muat().status, Status.DIJADWALKAN)

    def test_petugas_nggak_bisa_melakukan_transisi_admin(self):
        r = self.kirim({'ke': 'dibatalkan', 'alasan': 'Iseng'}, self.bima)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.muat().status, Status.DIJADWALKAN)

    def test_petugas_lain_dapat_404(self):
        self.assertEqual(self.kirim({'ke': 'sampel_diambil'}, self.laras).status_code, 404)
        self.assertEqual(self.muat().status, Status.DIJADWALKAN)

    def test_admin_nggak_bisa_melakukan_langkah_petugas(self):
        self.assertEqual(self.kirim({'ke': 'sampel_diambil'}, self.admin).status_code, 400)
        self.assertEqual(self.muat().status, Status.DIJADWALKAN)

    def test_klik_dobel_nggak_memajukan_dua_langkah(self):
        self.kirim({'ke': 'sampel_diambil'}, self.bima)
        self.assertEqual(self.kirim({'ke': 'sampel_diambil'}).status_code, 400)
        self.assertEqual(self.muat().status, Status.SAMPEL_DIAMBIL)


class SelesaiLewatModulHasilTests(TransitionTestCase):
    def test_modul_hasil_bisa_menyelesaikan_pesanan_lewat_fungsi_transisi(self):
        services.konfirmasi_pesanan(self.pesanan, self.bima)
        services.jadwalkan_pesanan(self.pesanan, date.today(), 'pagi')
        self.kirim({'ke': 'sampel_diambil'}, self.bima)
        self.kirim({'ke': 'diproses'})
        services.ubah_status(self.pesanan, Status.SELESAI, oleh=self.bima)
        self.assertEqual(self.muat().status, Status.SELESAI)
        self.assertEqual(self.pesanan.riwayat.order_by('id').last().status_sesudah, 'selesai')
