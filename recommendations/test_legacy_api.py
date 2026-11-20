from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.models import ContaminantType, Tanaman
from lands.models import Lahan, ManagementGoal
from soil_results.models import ContaminantFinding, HasilPemeriksaan

from .models import ManagementPlan, RecommendationSnapshot

CUACA = {'status': 'unavailable', 'source': 'Open-Meteo', 'reason': 'tes', 'message': '', 'timezone': None,
         'current': {}, 'units': {}}


class ApiRekomendasiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pemilik = User.objects.create_user('pemilik.api', password='api-12345')
        cls.lain = User.objects.create_user('pemilik.lain.api', password='api-12345')
        cls.petugas = User.objects.create_user('petugas.api', password='api-12345', role=User.Role.OFFICER)
        cls.tujuan = ManagementGoal.objects.get(slug='pencegahan-erosi')
        cls.lahan = Lahan.objects.create(owner=cls.pemilik, nama='Lahan API', latitude='-6.5', longitude='106.7',
                                         luas_m2=500, alamat='Bogor')
        cls.hasil = HasilPemeriksaan.objects.create(
            lahan=cls.lahan, asal='mandiri', sumber='Lab uji', tanggal_pemeriksaan=date(2026, 10, 1),
            ph=Decimal('6.2'), kelembapan=Decimal('30'), tekstur='lempung', bahan_organik=Decimal('2.5'),
        )
        for nama in ('Timbal (Pb)', 'Kadmium (Cd)'):
            jenis, _ = ContaminantType.objects.get_or_create(nama=nama)
            ContaminantFinding.objects.create(hasil=cls.hasil, kontaminan=jenis, status='tidak_terdeteksi')
        tanaman = Tanaman.objects.get(nama='Akar wangi')
        snapshot = RecommendationSnapshot.objects.create(
            lahan=cls.lahan, hasil_pemeriksaan=cls.hasil, tanaman=tanaman, tujuan=cls.tujuan, skor=90,
            alasan=['Cocok.'], kelengkapan_data=80,
        )
        cls.rencana = ManagementPlan.objects.create(
            pemilik=cls.pemilik, lahan=cls.lahan, rekomendasi=snapshot, luas_tanam_m2=Decimal('120'),
            jumlah_bibit=60, tanggal_tanam=date(2026, 11, 5), status='berjalan', catatan='Rahasia pemilik.',
        )

    # --- rencana ---
    def test_daftar_rencana_butuh_login(self):
        self.assertEqual(self.client.get(reverse('recommendations:api_daftar_rencana')).status_code, 401)

    def test_petugas_ditolak_403(self):
        self.client.force_login(self.petugas)
        self.assertEqual(self.client.get(reverse('recommendations:api_daftar_rencana')).status_code, 403)

    def test_pemilik_melihat_rencananya_sendiri(self):
        self.client.force_login(self.pemilik)
        r = self.client.get(reverse('recommendations:api_daftar_rencana'))
        self.assertEqual(r.status_code, 200)
        data = r.json()['results']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['tanaman']['nama'], 'Akar wangi')
        self.assertEqual(data[0]['status'], 'berjalan')
        self.assertEqual(data[0]['luas_tanam_m2'], '120.00')
        self.assertEqual(r['Cache-Control'], 'private, no-store')

    def test_filter_status(self):
        self.client.force_login(self.pemilik)
        r = self.client.get(reverse('recommendations:api_daftar_rencana'), {'status': 'selesai'})
        self.assertEqual(r.json()['results'], [])

    def test_pemilik_lain_tidak_melihat_rencana_orang(self):
        self.client.force_login(self.lain)
        self.assertEqual(self.client.get(reverse('recommendations:api_daftar_rencana')).json()['results'], [])
        self.assertEqual(
            self.client.get(reverse('recommendations:api_detail_rencana', args=[self.rencana.pk])).status_code, 404)

    def test_detail_rencana_lengkap(self):
        self.client.force_login(self.pemilik)
        data = self.client.get(reverse('recommendations:api_detail_rencana', args=[self.rencana.pk])).json()
        self.assertEqual(data['alasan'], ['Cocok.'])
        self.assertEqual(data['catatan'], 'Rahasia pemilik.')
        self.assertEqual(data['tujuan']['slug'], 'pencegahan-erosi')

    def test_api_hanya_baca(self):
        self.client.force_login(self.pemilik)
        self.assertEqual(self.client.post(reverse('recommendations:api_daftar_rencana')).status_code, 405)
        self.assertEqual(
            self.client.delete(reverse('recommendations:api_detail_rencana', args=[self.rencana.pk])).status_code, 405)

    # --- rekomendasi ---
    def url_rek(self, lahan=None):
        return reverse('recommendations:api_rekomendasi_lahan', args=[(lahan or self.lahan).pk])

    def minta(self, **params):
        with patch('recommendations.services.fetch_environmental_data', return_value=dict(CUACA)):
            return self.client.get(self.url_rek(), params)

    def test_rekomendasi_butuh_login(self):
        self.assertEqual(self.client.get(self.url_rek()).status_code, 401)

    def test_rekomendasi_menghitung_tanpa_menyimpan(self):
        self.client.force_login(self.pemilik)
        sebelum = RecommendationSnapshot.objects.count()
        r = self.minta(hasil=self.hasil.pk, tujuan=self.tujuan.pk)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertFalse(data['risiko_tinggi'])
        self.assertIn('Akar wangi', [k['tanaman']['nama'] for k in data['rekomendasi']])
        self.assertTrue(all('alasan' in k and 'skor' in k for k in data['rekomendasi']))
        self.assertEqual(RecommendationSnapshot.objects.count(), sebelum)

    def test_tanaman_pangan_belum_terverifikasi_muncul_di_diblokir(self):
        goal = ManagementGoal.objects.get(slug='pangan-keluarga')
        self.client.force_login(self.pemilik)
        data = self.minta(hasil=self.hasil.pk, tujuan=goal.pk).json()
        self.assertTrue(data['diblokir'])
        self.assertTrue(all(d['alasan'] for d in data['diblokir']))

    def test_kontaminan_terdeteksi_menghentikan_rekomendasi(self):
        timbal = ContaminantType.objects.get(nama='Timbal (Pb)')
        ContaminantFinding.objects.filter(hasil=self.hasil, kontaminan=timbal).update(
            status='terdeteksi', nilai=Decimal('380'), satuan='mg/kg')
        self.client.force_login(self.pemilik)
        data = self.minta(hasil=self.hasil.pk, tujuan=self.tujuan.pk).json()
        self.assertTrue(data['risiko_tinggi'])
        self.assertEqual(data['rekomendasi'], [])

    def test_lahan_orang_lain_404(self):
        self.client.force_login(self.lain)
        self.assertEqual(self.minta(hasil=self.hasil.pk, tujuan=self.tujuan.pk).status_code, 404)

    def test_hasil_dari_lahan_lain_404(self):
        punya_lain = Lahan.objects.create(owner=self.lain, nama='Lahan Lain', latitude='-6.5', longitude='106.7',
                                          luas_m2=100, alamat='Bogor')
        hasil_lain = HasilPemeriksaan.objects.create(
            lahan=punya_lain, asal='mandiri', sumber='Lab', tanggal_pemeriksaan=date(2026, 10, 1), ph=Decimal('6'))
        self.client.force_login(self.pemilik)
        self.assertEqual(self.minta(hasil=hasil_lain.pk, tujuan=self.tujuan.pk).status_code, 404)

    def test_parameter_salah_404_bukan_500(self):
        self.client.force_login(self.pemilik)
        self.assertEqual(self.minta().status_code, 404)
        self.assertEqual(self.minta(hasil='abc', tujuan='xyz').status_code, 404)

    def test_hasil_draf_tidak_dipakai(self):
        HasilPemeriksaan.objects.filter(pk=self.hasil.pk).update(status_hasil='draf')
        self.client.force_login(self.pemilik)
        self.assertEqual(self.minta(hasil=self.hasil.pk, tujuan=self.tujuan.pk).status_code, 404)
