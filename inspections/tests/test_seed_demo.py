from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import User
from lands.models import Lahan

from ..models import PesananPemeriksaan, RiwayatPesanan


def jalankan(*args):
    keluaran = StringIO()
    call_command('seed_pesanan_demo', *args, stdout=keluaran)
    return keluaran.getvalue()


class SeedPesananDemoTests(TestCase):
    def test_membuat_delapan_pesanan_yang_mencakup_semua_status(self):
        jalankan()
        self.assertEqual(PesananPemeriksaan.objects.count(), 8)
        status = set(PesananPemeriksaan.objects.values_list('status', flat=True))
        self.assertEqual(status, {s.value for s in PesananPemeriksaan.Status})

    def test_ada_petugas_dan_pemilik_demo(self):
        jalankan()
        self.assertEqual(User.objects.filter(role=User.Role.OFFICER).count(), 3)
        pemilik = User.objects.get(username='pemilik.demo')
        self.assertTrue(pemilik.check_password('demo-wiji-123'))
        self.assertEqual(Lahan.objects.filter(owner=pemilik).count(), 8)

    def test_semua_pesanan_punya_riwayat_dan_satu_pesanan_aktif_per_lahan(self):
        jalankan()
        for pesanan in PesananPemeriksaan.objects.all():
            self.assertTrue(pesanan.riwayat.exists(), pesanan.kode)
            self.assertEqual(pesanan.riwayat.first().status_sesudah, 'diajukan')

    def test_pesanan_selesai_riwayatnya_lengkap(self):
        jalankan()
        selesai = PesananPemeriksaan.objects.get(status='selesai')
        urutan = list(selesai.riwayat.values_list('status_sesudah', flat=True))
        self.assertEqual(urutan, ['diajukan', 'dikonfirmasi', 'dijadwalkan', 'sampel_diambil', 'diproses', 'selesai'])

    def test_ada_pesanan_yang_pernah_dijadwal_ulang(self):
        jalankan()
        self.assertTrue(RiwayatPesanan.objects.filter(jenis='jadwal_ulang').exists())

    def test_dijalankan_dua_kali_nggak_menggandakan_data(self):
        jalankan()
        self.assertIn('sudah ada', jalankan())
        self.assertEqual(PesananPemeriksaan.objects.count(), 8)

    def test_ulang_membuat_data_baru_tanpa_menumpuk(self):
        jalankan()
        jalankan('--ulang')
        self.assertEqual(PesananPemeriksaan.objects.count(), 8)
        self.assertEqual(Lahan.objects.filter(owner__username='pemilik.demo').count(), 8)

    def test_ulang_nggak_menyentuh_data_pemilik_lain(self):
        from .helpers import buat_lahan, buat_pemilik, buat_pesanan

        punya_dewi = buat_pesanan(buat_lahan(buat_pemilik('dewi')))
        jalankan()
        jalankan('--ulang')
        self.assertTrue(PesananPemeriksaan.objects.filter(pk=punya_dewi.pk).exists())


class AkunDemoTests(TestCase):
    def test_ada_akun_admin_demo_yang_bisa_masuk_ke_halaman_kelola(self):
        jalankan()
        admin = User.objects.get(username='admin.demo')
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.check_password('demo-wiji-123'))
        self.client.force_login(admin)
        self.assertEqual(self.client.get('/pemeriksaan/kelola/').status_code, 200)

    def test_petugas_demo_punya_tugas_di_halaman_petugas(self):
        jalankan()
        petugas = User.objects.get(username='petugas.bima')
        self.client.force_login(petugas)
        response = self.client.get('/pemeriksaan/tugas/')
        self.assertTrue(len(response.context['pesanan_list']) > 0)

    def test_admin_dibuat_juga_kalau_data_demo_sudah_ada_dari_versi_lama(self):
        jalankan()
        User.objects.filter(username='admin.demo').delete()
        self.assertIn('sudah ada', jalankan())
        self.assertTrue(User.objects.filter(username='admin.demo', is_staff=True).exists())

    def test_ulang_nggak_menggandakan_admin(self):
        jalankan()
        jalankan('--ulang')
        self.assertEqual(User.objects.filter(username='admin.demo').count(), 1)
