from django.test import TestCase
from django.urls import reverse

from .. import services
from ..models import PesananPemeriksaan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_akses import buat_admin
from .test_services import buat_petugas

HTMX = {'HTTP_HX_REQUEST': 'true'}


class AksesKelolaTests(TestCase):
    def setUp(self):
        self.pesanan = buat_pesanan(buat_lahan(buat_pemilik()))
        self.urls = [reverse('inspections:kelola_daftar'), reverse('inspections:kelola_detail', args=[self.pesanan.pk])]

    def test_tamu_diarahkan_ke_login(self):
        for url in self.urls:
            self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}")

    def test_pemilik_dan_petugas_dapat_403(self):
        for user in (buat_pemilik('dewi'), buat_petugas()):
            self.client.force_login(user)
            for url in self.urls:
                self.assertEqual(self.client.get(url).status_code, 403, (user, url))

    def test_admin_boleh(self):
        self.client.force_login(buat_admin())
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 200)


class DaftarKelolaTests(TestCase):
    def setUp(self):
        self.sari = buat_pemilik('sari')
        self.dewi = buat_pemilik('dewi')
        self.baru = buat_pesanan(buat_lahan(self.sari, nama='Kebun Cibodas'))
        self.jalan = buat_pesanan(buat_lahan(self.dewi, nama='Pekarangan Dramaga'))
        services.konfirmasi_pesanan(self.jalan, buat_petugas())
        self.selesai = buat_pesanan(buat_lahan(self.sari, nama='Sawah Ciampea'))
        PesananPemeriksaan.objects.filter(pk=self.selesai.pk).update(status='selesai')
        self.url = reverse('inspections:kelola_daftar')
        self.client.force_login(buat_admin())

    def nama_lahan(self, **param):
        return {p.lahan.nama for p in self.client.get(self.url, param).context['pesanan_list']}

    def test_menampilkan_pesanan_dari_semua_pemilik(self):
        self.assertEqual(self.nama_lahan(), {'Kebun Cibodas', 'Pekarangan Dramaga', 'Sawah Ciampea'})

    def test_filter_perlu_ditugaskan_cuma_yang_diajukan(self):
        self.assertEqual(self.nama_lahan(status='perlu'), {'Kebun Cibodas'})

    def test_filter_berjalan_selesai_dan_dibatalkan(self):
        self.assertEqual(self.nama_lahan(status='berjalan'), {'Pekarangan Dramaga'})
        self.assertEqual(self.nama_lahan(status='selesai'), {'Sawah Ciampea'})
        self.assertEqual(self.nama_lahan(status='dibatalkan'), set())

    def test_filter_ngawur_dianggap_semua(self):
        self.assertEqual(len(self.nama_lahan(status='ngawur')), 3)

    def test_jumlah_di_tiap_filter(self):
        jumlah = {f['kunci']: f['jumlah'] for f in self.client.get(self.url).context['filter_list']}
        self.assertEqual(jumlah, {'semua': 3, 'perlu': 1, 'berjalan': 1, 'selesai': 1, 'dibatalkan': 0})

    def test_cari_lewat_nama_lahan_nama_pemilik_dan_kode(self):
        self.assertEqual(self.nama_lahan(q='cibodas'), {'Kebun Cibodas'})
        self.assertEqual(self.nama_lahan(q='dewi'), {'Pekarangan Dramaga'})
        self.assertEqual(self.nama_lahan(q=self.jalan.kode), {'Pekarangan Dramaga'})
        self.assertEqual(self.nama_lahan(q=self.jalan.kode.lower()), {'Pekarangan Dramaga'})

    def test_cari_dan_filter_bisa_digabung(self):
        self.assertEqual(self.nama_lahan(q='sari', status='selesai'), {'Sawah Ciampea'})
        self.assertEqual(self.nama_lahan(q='dewi', status='selesai'), set())

    def test_tombol_di_daftar_menyesuaikan_status(self):
        isi = self.client.get(self.url).content.decode()
        self.assertIn('>Tugaskan<', isi)
        self.assertIn('>Kelola<', isi)

    def test_htmx_cuma_mengirim_bagian_daftar(self):
        response = self.client.get(self.url, {'status': 'selesai'}, **HTMX)
        self.assertContains(response, 'Sawah Ciampea')
        self.assertNotContains(response, 'Kebun Cibodas')
        self.assertNotContains(response, '<html')
        self.assertTemplateUsed(response, 'inspections/kelola/partials/_daftar.html')

    def test_halaman_penuh_memuat_layout_dan_penunjuk(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<html')
        self.assertContains(response, 'Kelola pesanan')

    def test_kosong_menampilkan_pesan_ramah(self):
        response = self.client.get(self.url, {'q': 'tidak-ada-lahan-ini'})
        self.assertContains(response, 'Nggak ada pesanan yang cocok')


class DetailKelolaTests(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik('sari')
        self.pemilik.first_name = 'Sari Rahayu'
        self.pemilik.save()
        self.pesanan = buat_pesanan(buat_lahan(self.pemilik, nama='Kebun Cibodas'))
        self.client.force_login(buat_admin())

    def test_admin_melihat_pemilik_email_dan_lokasi_lahan(self):
        response = self.client.get(reverse('inspections:kelola_detail', args=[self.pesanan.pk]))
        self.assertContains(response, 'Sari Rahayu')
        self.assertContains(response, 'sari@contoh.id')
        self.assertContains(response, 'Cianjur')
        self.assertContains(response, '-6.8')

    def test_detail_menampilkan_riwayat(self):
        services.konfirmasi_pesanan(self.pesanan, buat_petugas(first_name='Bima'))
        response = self.client.get(reverse('inspections:kelola_detail', args=[self.pesanan.pk]))
        self.assertContains(response, 'Dikonfirmasi')
        self.assertContains(response, 'Bima')

    def test_pesanan_nggak_ada_404(self):
        self.assertEqual(self.client.get(reverse('inspections:kelola_detail', args=[9999])).status_code, 404)

    def test_halaman_pemilik_tetap_nggak_menampilkan_email_dan_pemilik(self):
        self.client.force_login(self.pemilik)
        response = self.client.get(reverse('inspections:detail_pesanan', args=[self.pesanan.pk]))
        self.assertNotContains(response, 'sari@contoh.id')
        self.assertNotContains(response, 'Email pemilik')


class MenuSidebarTests(TestCase):
    def test_admin_dapat_menu_admin_bukan_menu_pemilik(self):
        self.client.force_login(buat_admin())
        response = self.client.get(reverse('inspections:kelola_daftar'))
        self.assertContains(response, reverse('inspections:kelola_daftar'))
        self.assertContains(response, reverse('admin:index'))
        self.assertNotContains(response, reverse('recommendations:daftar_rencana'))

    def test_pemilik_nggak_melihat_menu_kelola(self):
        pemilik = buat_pemilik()
        self.client.force_login(pemilik)
        response = self.client.get(reverse('inspections:daftar_pesanan'))
        self.assertNotContains(response, reverse('inspections:kelola_daftar'))
        self.assertContains(response, reverse('recommendations:daftar_rencana'))
