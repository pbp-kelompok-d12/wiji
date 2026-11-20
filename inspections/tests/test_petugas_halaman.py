from django.test import TestCase
from django.urls import reverse

from .. import services
from ..models import PesananPemeriksaan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_akses import buat_admin
from .test_services import buat_petugas

from datetime import date, timedelta

HTMX = {'HTTP_HX_REQUEST': 'true'}


def hari(n):
    return date.today() + timedelta(days=n)


class AksesTugasTests(TestCase):
    def setUp(self):
        self.bima = buat_petugas('bima')
        self.pesanan = buat_pesanan(buat_lahan(buat_pemilik()))
        services.konfirmasi_pesanan(self.pesanan, self.bima)
        self.urls = [reverse('inspections:tugas_daftar'), reverse('inspections:tugas_detail', args=[self.pesanan.pk])]

    def test_tamu_diarahkan_ke_login(self):
        for url in self.urls:
            self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}")

    def test_pemilik_dan_admin_dapat_403(self):
        for user in (buat_pemilik('dewi'), buat_admin()):
            self.client.force_login(user)
            for url in self.urls:
                self.assertEqual(self.client.get(url).status_code, 403, (user, url))

    def test_petugas_boleh(self):
        self.client.force_login(self.bima)
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_petugas_lain_nggak_bisa_membuka_tugas_orang(self):
        self.client.force_login(buat_petugas('laras'))
        self.assertEqual(self.client.get(self.urls[1]).status_code, 404)

    def test_akun_staf_berperan_officer_tetap_cuma_melihat_tugasnya(self):
        staf = buat_petugas('staf-petugas', is_staff=True)
        buat_pesanan(buat_lahan(buat_pemilik('lain'), nama='Lahan Lain'))
        self.client.force_login(staf)
        self.assertEqual(list(self.client.get(self.urls[0]).context['pesanan_list']), [])
        self.assertEqual(self.client.get(self.urls[1]).status_code, 404)


class DaftarTugasTests(TestCase):
    def setUp(self):
        self.bima = buat_petugas('bima')
        self.laras = buat_petugas('laras')
        pemilik = buat_pemilik()
        self.konfirmasi = buat_pesanan(buat_lahan(pemilik, nama='Lahan Konfirmasi'))
        self.jadwal = buat_pesanan(buat_lahan(pemilik, nama='Lahan Jadwal'))
        self.kerja = buat_pesanan(buat_lahan(pemilik, nama='Lahan Kerja'))
        self.selesai = buat_pesanan(buat_lahan(pemilik, nama='Lahan Selesai'))
        self.punya_laras = buat_pesanan(buat_lahan(pemilik, nama='Lahan Laras'))
        self.belum = buat_pesanan(buat_lahan(pemilik, nama='Lahan Belum Ditugaskan'))
        for p in (self.konfirmasi, self.jadwal, self.kerja, self.selesai):
            services.konfirmasi_pesanan(p, self.bima)
        services.konfirmasi_pesanan(self.punya_laras, self.laras)
        services.jadwalkan_pesanan(self.jadwal, hari(6), 'pagi')
        services.jadwalkan_pesanan(self.kerja, hari(3), 'siang')
        PesananPemeriksaan.objects.filter(pk=self.kerja.pk).update(status='diproses')
        services.jadwalkan_pesanan(self.selesai, hari(1), 'pagi')
        PesananPemeriksaan.objects.filter(pk=self.selesai.pk).update(status='selesai')
        self.url = reverse('inspections:tugas_daftar')
        self.client.force_login(self.bima)

    def nama_lahan(self, **param):
        return [p.lahan.nama for p in self.client.get(self.url, param).context['pesanan_list']]

    def test_cuma_tugas_sendiri(self):
        semua = self.nama_lahan()
        self.assertEqual(set(semua), {'Lahan Konfirmasi', 'Lahan Jadwal', 'Lahan Kerja', 'Lahan Selesai'})
        self.assertNotIn('Lahan Laras', semua)
        self.assertNotIn('Lahan Belum Ditugaskan', semua)

    def test_jadwal_terdekat_di_atas_dan_tanpa_jadwal_di_bawah(self):
        self.assertEqual(
            self.nama_lahan(),
            ['Lahan Selesai', 'Lahan Kerja', 'Lahan Jadwal', 'Lahan Konfirmasi'],
        )

    def test_filter_kelompok_status(self):
        self.assertEqual(set(self.nama_lahan(status='terjadwal')), {'Lahan Konfirmasi', 'Lahan Jadwal'})
        self.assertEqual(self.nama_lahan(status='dikerjakan'), ['Lahan Kerja'])
        self.assertEqual(self.nama_lahan(status='selesai'), ['Lahan Selesai'])
        self.assertEqual(self.nama_lahan(status='dibatalkan'), [])

    def test_filter_ngawur_dianggap_semua(self):
        self.assertEqual(len(self.nama_lahan(status='ngawur')), 4)

    def test_jumlah_di_tiap_filter(self):
        jumlah = {f['kunci']: f['jumlah'] for f in self.client.get(self.url).context['filter_list']}
        self.assertEqual(jumlah, {'semua': 4, 'terjadwal': 2, 'dikerjakan': 1, 'selesai': 1, 'dibatalkan': 0})

    def test_htmx_cuma_mengirim_bagian_daftar(self):
        response = self.client.get(self.url, {'status': 'selesai'}, **HTMX)
        self.assertContains(response, 'Lahan Selesai')
        self.assertNotContains(response, 'Lahan Kerja')
        self.assertNotContains(response, '<html')

    def test_petugas_tanpa_tugas_melihat_pesan_ramah(self):
        self.client.force_login(buat_petugas('baru'))
        self.assertContains(self.client.get(self.url), 'Belum ada tugas')


class DetailTugasTests(TestCase):
    def setUp(self):
        self.bima = buat_petugas('bima', first_name='Bima')
        pemilik = buat_pemilik('sari')
        pemilik.first_name = 'Sari Rahayu'
        pemilik.save()
        self.pesanan = buat_pesanan(buat_lahan(pemilik, nama='Kebun Cibodas'), catatan='Parkir motor di warung')
        services.konfirmasi_pesanan(self.pesanan, self.bima)
        services.jadwalkan_pesanan(self.pesanan, hari(4), 'pagi')
        self.client.force_login(self.bima)
        self.response = self.client.get(reverse('inspections:tugas_detail', args=[self.pesanan.pk]))

    def test_menampilkan_info_yang_dibutuhkan_petugas(self):
        for teks in ('Kebun Cibodas', 'Sari Rahayu', 'Cianjur', '-6.8', 'Parkir motor di warung', 'Dijadwalkan'):
            self.assertContains(self.response, teks)

    def test_email_pemilik_nggak_bocor(self):
        self.assertNotContains(self.response, 'sari@contoh.id')
        self.assertNotContains(self.response, 'Email pemilik')

    def test_catatan_khusus_pemilik_nggak_muncul(self):
        self.assertNotContains(self.response, 'masih bisa sampai petugas menandai sampel diambil')

    def test_menampilkan_riwayat(self):
        self.assertContains(self.response, 'Dikonfirmasi')
        self.assertContains(self.response, 'Dijadwalkan')


class MenuPetugasTests(TestCase):
    def test_petugas_dapat_menu_petugas_bukan_menu_pemilik(self):
        self.client.force_login(buat_petugas())
        response = self.client.get(reverse('inspections:tugas_daftar'))
        self.assertContains(response, reverse('inspections:tugas_daftar'))
        self.assertNotContains(response, reverse('recommendations:daftar_rencana'))
        self.assertNotContains(response, reverse('inspections:kelola_daftar'))
        self.assertContains(response, 'Petugas Pemeriksa')
