from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from lands.models import Lahan

from .lahan import RingkasanLahan


def buat_pemilik(username='sari'):
    return User.objects.create_user(username, f'{username}@contoh.id', 'tanah12345')


def lahan_lengkap(pemilik, nama='Lahan'):
    return Lahan.objects.create(
        owner=pemilik, nama=nama, alamat='Cianjur', latitude='-6.8', longitude='107.0',
        luas_m2=1000, penggunaan='kebun',
    )


def lahan_draf(pemilik, nama='Draf'):
    return Lahan.objects.create(owner=pemilik, nama=nama)


class RingkasanLahanTests(TestCase):
    def setUp(self):
        self.sari = buat_pemilik()

    def test_tiap_angka_cuma_sekali_query(self):
        lahan_lengkap(self.sari)
        r = RingkasanLahan(self.sari)
        with self.assertNumQueries(1):
            r.aktif, r.aktif, r.aktif

    def test_tanpa_lahan_semuanya_nol(self):
        r = RingkasanLahan(self.sari)
        self.assertEqual((r.aktif, r.draf, r.draf_pertama), (0, 0, None))

    def test_membedakan_aktif_draf_dan_arsip(self):
        lahan_lengkap(self.sari, 'A')
        lahan_lengkap(self.sari, 'B')
        lahan_draf(self.sari, 'C')
        arsip = lahan_lengkap(self.sari, 'D')
        arsip.arsipkan()
        lahan_draf(self.sari, 'E').arsipkan()
        r = RingkasanLahan(self.sari)
        self.assertEqual((r.aktif, r.draf), (2, 1))

    def test_lahan_tanpa_koordinat_dihitung_draf(self):
        Lahan.objects.create(owner=self.sari, nama='X', alamat='Y', luas_m2=10, penggunaan='kebun')
        self.assertEqual(RingkasanLahan(self.sari).draf, 1)

    def test_draf_pertama_adalah_yang_terbaru(self):
        lahan_draf(self.sari, 'Lama')
        baru = lahan_draf(self.sari, 'Baru')
        self.assertEqual(RingkasanLahan(self.sari).draf_pertama, baru)

    def test_cuma_menghitung_lahan_sendiri(self):
        lahan_lengkap(buat_pemilik('dewi'))
        self.assertEqual(RingkasanLahan(self.sari).aktif, 0)


class SidebarPemilikTests(TestCase):
    def setUp(self):
        self.sari = buat_pemilik()
        self.client.force_login(self.sari)
        self.url = reverse('lands:daftar_lahan')

    def test_tanpa_lahan_nggak_ada_angka_dan_kartu(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'side-count')
        self.assertNotContains(response, 'lahan belum lengkap')

    def test_angka_lahan_aktif_di_sidebar(self):
        lahan_lengkap(self.sari, 'A')
        lahan_lengkap(self.sari, 'B')
        lahan_draf(self.sari, 'C')
        self.assertContains(self.client.get(self.url), '<span class="side-count">2</span>', html=False)

    def test_kartu_menyebut_jumlah_draf_dan_menuju_lahan_draf(self):
        lahan_draf(self.sari, 'Draf lama')
        terbaru = lahan_draf(self.sari, 'Draf baru')
        response = self.client.get(self.url)
        self.assertContains(response, '2 lahan belum lengkap')
        self.assertContains(response, reverse('lands:ubah_lahan', args=[terbaru.pk]))

    def test_kartu_hilang_kalau_semua_lahan_lengkap(self):
        lahan_lengkap(self.sari)
        self.assertNotContains(self.client.get(self.url), 'lahan belum lengkap')

    def test_lahan_orang_lain_nggak_ikut_dihitung(self):
        lahan_draf(buat_pemilik('dewi'))
        lahan_lengkap(buat_pemilik('budi'))
        response = self.client.get(self.url)
        self.assertNotContains(response, 'side-count')
        self.assertNotContains(response, 'lahan belum lengkap')


class SidebarBukanPemilikTests(TestCase):
    def test_admin_petugas_dan_tamu_nggak_dapat_data_lahan_di_sidebar(self):
        admin = User.objects.create_user('adm', 'a@contoh.id', 'tanah12345', is_staff=True)
        petugas = User.objects.create_user('bima', 'b@contoh.id', 'tanah12345', role=User.Role.OFFICER)
        lahan_draf(buat_pemilik())
        for user in (admin, petugas):
            self.client.force_login(user)
            response = self.client.get(reverse('dashboard:home'))
            self.assertNotIn('sidebar_lahan', response.context)
            self.assertNotContains(response, 'lahan belum lengkap')
