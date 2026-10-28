from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from accounts.models import User

from .. import akses, services
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_services import buat_petugas


def buat_admin(username='admin'):
    return User.objects.create_user(username, f'{username}@contoh.id', 'tanah12345', is_staff=True)


class PeranTests(TestCase):
    def test_admin_adalah_staf(self):
        self.assertTrue(akses.adalah_admin(buat_admin()))
        self.assertFalse(akses.adalah_admin(buat_pemilik()))
        self.assertFalse(akses.adalah_admin(buat_petugas()))

    def test_petugas_adalah_peran_officer(self):
        self.assertTrue(akses.adalah_petugas(buat_petugas()))
        self.assertFalse(akses.adalah_petugas(buat_pemilik()))

    def test_tamu_bukan_siapa_siapa(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(akses.adalah_admin(AnonymousUser()))
        self.assertFalse(akses.adalah_petugas(AnonymousUser()))


class PembatasTests(TestCase):
    def jalankan(self, pembatas, user):
        request = RequestFactory().get('/')
        request.user = user
        return pembatas(lambda r: HttpResponse('ok'))(request)

    def test_admin_boleh_lewat_pembatas_admin(self):
        self.assertEqual(self.jalankan(akses.admin_required, buat_admin()).content, b'ok')

    def test_bukan_admin_dapat_403(self):
        for user in (buat_pemilik(), buat_petugas()):
            with self.assertRaises(PermissionDenied):
                self.jalankan(akses.admin_required, user)

    def test_petugas_boleh_lewat_pembatas_petugas(self):
        self.assertEqual(self.jalankan(akses.petugas_required, buat_petugas()).content, b'ok')

    def test_bukan_petugas_dapat_403(self):
        for user in (buat_pemilik(), buat_admin()):
            with self.assertRaises(PermissionDenied):
                self.jalankan(akses.petugas_required, user)

    def test_tamu_diarahkan_ke_halaman_masuk(self):
        from django.contrib.auth.models import AnonymousUser
        respons = self.jalankan(akses.admin_required, AnonymousUser())
        self.assertEqual(respons.status_code, 302)


class PesananUntukTests(TestCase):
    def setUp(self):
        self.sari = buat_pemilik('sari')
        self.dewi = buat_pemilik('dewi')
        self.punya_sari = buat_pesanan(buat_lahan(self.sari))
        self.punya_dewi = buat_pesanan(buat_lahan(self.dewi))
        self.bima = buat_petugas('bima')
        self.laras = buat_petugas('laras')
        services.konfirmasi_pesanan(self.punya_sari, self.bima)
        services.konfirmasi_pesanan(self.punya_dewi, self.laras)

    def ids(self, user):
        return set(akses.pesanan_untuk(user).values_list('pk', flat=True))

    def test_admin_lihat_semua(self):
        self.assertEqual(self.ids(buat_admin()), {self.punya_sari.pk, self.punya_dewi.pk})

    def test_petugas_cuma_lihat_tugasnya(self):
        self.assertEqual(self.ids(self.bima), {self.punya_sari.pk})
        self.assertEqual(self.ids(self.laras), {self.punya_dewi.pk})

    def test_pemilik_cuma_lihat_pesanan_lahannya(self):
        self.assertEqual(self.ids(self.sari), {self.punya_sari.pk})

    def test_petugas_baru_tanpa_tugas_nggak_lihat_apa_apa(self):
        self.assertEqual(self.ids(buat_petugas('baru')), set())

    def test_tamu_nggak_lihat_apa_apa(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertEqual(self.ids(AnonymousUser()), set())
