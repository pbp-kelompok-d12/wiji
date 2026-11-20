from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from .. import ringkasan, services
from ..models import PesananPemeriksaan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_akses import buat_admin
from .test_services import buat_petugas

Status = PesananPemeriksaan.Status


def hari(n):
    return date.today() + timedelta(days=n)


def pesanan_baru(nama='Lahan', pemilik=None):
    return buat_pesanan(buat_lahan(pemilik or buat_pemilik(f'p-{nama}'), nama=nama))


class RingkasanAdminTests(TestCase):
    def setUp(self):
        self.bima = buat_petugas('bima', first_name='Bima')
        self.laras = buat_petugas('laras', first_name='Laras')
        self.diajukan = [pesanan_baru('A'), pesanan_baru('B')]
        self.konfirmasi = pesanan_baru('C')
        self.jadwal = pesanan_baru('D')
        self.selesai = pesanan_baru('E')
        services.konfirmasi_pesanan(self.konfirmasi, self.bima)
        services.konfirmasi_pesanan(self.jadwal, self.bima)
        services.jadwalkan_pesanan(self.jadwal, hari(3), 'pagi')
        services.konfirmasi_pesanan(self.selesai, self.laras)
        PesananPemeriksaan.objects.filter(pk=self.selesai.pk).update(status='selesai')

    def test_angka_ringkasan(self):
        data = ringkasan.ringkasan_admin()
        self.assertEqual(data['jumlah_perlu_ditugaskan'], 2)
        self.assertEqual(data['jumlah_perlu_jadwal'], 1)
        self.assertEqual(data['jumlah_berjalan'], 2)
        self.assertEqual(data['jumlah_selesai'], 1)

    def test_yang_paling_lama_menunggu_di_atas(self):
        data = ringkasan.ringkasan_admin()
        self.assertEqual([p.pk for p in data['perlu_ditugaskan']], [p.pk for p in self.diajukan])

    def test_daftar_dibatasi(self):
        for i in range(8):
            pesanan_baru(f'X{i}')
        self.assertEqual(len(ringkasan.ringkasan_admin(batas=3)['perlu_ditugaskan']), 3)

    def test_jadwal_terdekat_cuma_yang_dijadwalkan_dan_belum_lewat(self):
        lewat = pesanan_baru('Lewat')
        services.konfirmasi_pesanan(lewat, self.laras)
        services.jadwalkan_pesanan(lewat, hari(0), 'pagi')
        PesananPemeriksaan.objects.filter(pk=lewat.pk).update(tanggal_final=hari(-2))
        daftar = ringkasan.ringkasan_admin()['jadwal_terdekat']
        self.assertEqual([p.pk for p in daftar], [self.jadwal.pk])

    def test_beban_petugas_dihitung_dari_tugas_berjalan(self):
        beban = {u.username: u.aktif for u in ringkasan.ringkasan_admin()['beban_petugas']}
        self.assertEqual(beban, {'bima': 2, 'laras': 0})  # tugas Laras sudah selesai

    def test_petugas_nonaktif_nggak_ikut_dihitung(self):
        buat_petugas('nonaktif', is_active=False)
        self.assertEqual(len(ringkasan.ringkasan_admin()['beban_petugas']), 2)


class DashboardAdminTests(TestCase):
    def setUp(self):
        self.bima = buat_petugas('bima', first_name='Bima')
        self.pesanan = pesanan_baru('Kebun Cibodas')
        self.client.force_login(buat_admin())
        self.url = reverse('dashboard:home')

    def test_menampilkan_angka_dan_pesanan_yang_perlu_ditugaskan(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Perlu ditugaskan')
        self.assertContains(response, self.pesanan.kode)
        self.assertContains(response, 'Kebun Cibodas')
        self.assertContains(response, reverse('inspections:kelola_detail', args=[self.pesanan.pk]))
        self.assertEqual(response.context['jumlah_perlu_ditugaskan'], 1)

    def test_keadaan_kosong(self):
        PesananPemeriksaan.objects.all().delete()
        response = self.client.get(self.url)
        self.assertContains(response, 'Semua pesanan sudah ditugaskan')
        self.assertContains(response, 'Belum ada jadwal yang akan datang')

    def test_menampilkan_beban_petugas(self):
        services.konfirmasi_pesanan(self.pesanan, self.bima)
        response = self.client.get(self.url)
        self.assertContains(response, 'Bima')
        self.assertContains(response, '1 tugas')

    def test_tanpa_petugas_ada_petunjuk(self):
        self.bima.delete()
        self.assertContains(self.client.get(self.url), 'Belum ada akun petugas')


class DashboardPetugasTests(TestCase):
    def setUp(self):
        self.bima = buat_petugas('bima', first_name='Bima')
        self.laras = buat_petugas('laras')
        self.siap = pesanan_baru('Lahan Siap')
        self.sampel = pesanan_baru('Lahan Sampel')
        self.proses = pesanan_baru('Lahan Proses')
        self.milik_laras = pesanan_baru('Lahan Laras')
        for p in (self.siap, self.sampel, self.proses):
            services.konfirmasi_pesanan(p, self.bima)
            services.jadwalkan_pesanan(p, hari(2), 'pagi')
        PesananPemeriksaan.objects.filter(pk=self.sampel.pk).update(status='sampel_diambil')
        PesananPemeriksaan.objects.filter(pk=self.proses.pk).update(status='diproses')
        services.konfirmasi_pesanan(self.milik_laras, self.laras)
        self.client.force_login(self.bima)

    def test_angka_ringkasan_cuma_dari_tugas_sendiri(self):
        data = ringkasan.ringkasan_petugas(self.bima)
        self.assertEqual(
            (data['jumlah_aktif'], data['jumlah_siap_diambil'], data['jumlah_dikerjakan'], data['jumlah_selesai']),
            (3, 1, 2, 0),
        )

    def test_dashboard_menampilkan_tugas_dan_tindakan(self):
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'Lahan Siap')
        self.assertContains(response, 'Mulai proses')
        self.assertContains(response, 'Menunggu hasil pemeriksaan')
        self.assertContains(response, reverse('inspections:tugas_detail', args=[self.siap.pk]))

    def test_nggak_menampilkan_tugas_petugas_lain(self):
        self.assertNotContains(self.client.get(reverse('dashboard:home')), 'Lahan Laras')

    def test_petugas_tanpa_tugas_melihat_keadaan_kosong(self):
        self.client.force_login(buat_petugas('baru'))
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'Belum ada tugas yang akan datang')
        self.assertContains(response, 'Nggak ada yang menunggu tindakanmu')

    def test_akun_staf_berperan_officer_dapat_dashboard_admin(self):
        self.client.force_login(buat_petugas('staf', is_staff=True))
        self.assertTemplateUsed(self.client.get(reverse('dashboard:home')), 'dashboard/admin.html')
