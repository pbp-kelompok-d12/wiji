from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User

from .. import services
from ..models import PesananPemeriksaan, RiwayatPesanan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan

Status = PesananPemeriksaan.Status


def buat_petugas(username='bima', **kwargs):
    return User.objects.create_user(
        username, f'{username}@contoh.id', 'tanah12345', role=User.Role.OFFICER, **kwargs,
    )


class UbahStatusTests(TestCase):
    def setUp(self):
        self.pesanan = buat_pesanan(buat_lahan(buat_pemilik()))
        self.petugas = buat_petugas()
        self.admin = User.objects.create_user('admin', 'a@contoh.id', 'tanah12345', is_staff=True)

    def test_alur_lengkap_sampai_selesai_tercatat_di_riwayat(self):
        besok = date.today() + timedelta(days=1)
        services.konfirmasi_pesanan(self.pesanan, self.petugas, self.admin)
        services.jadwalkan_pesanan(self.pesanan, besok, 'pagi', self.admin)
        for status in (Status.SAMPEL_DIAMBIL, Status.DIPROSES, Status.SELESAI):
            services.ubah_status(self.pesanan, status, self.petugas)

        self.pesanan.refresh_from_db()
        self.assertEqual(self.pesanan.status, Status.SELESAI)
        self.assertEqual(self.pesanan.petugas, self.petugas)
        self.assertEqual(self.pesanan.tanggal_final, besok)
        urutan = list(self.pesanan.riwayat.values_list('status_sesudah', flat=True))
        self.assertEqual(urutan, ['dikonfirmasi', 'dijadwalkan', 'sampel_diambil', 'diproses', 'selesai'])
        self.assertEqual(self.pesanan.riwayat.first().oleh, self.admin)

    def test_lompat_status_ditolak(self):
        with self.assertRaises(ValidationError):
            services.ubah_status(self.pesanan, Status.DIPROSES)
        self.pesanan.refresh_from_db()
        self.assertEqual(self.pesanan.status, Status.DIAJUKAN)
        self.assertFalse(RiwayatPesanan.objects.exists())

    def test_status_akhir_nggak_bisa_diubah_lagi(self):
        services.ubah_status(self.pesanan, Status.DIBATALKAN, catatan='Salah pilih lahan')
        with self.assertRaises(ValidationError):
            services.ubah_status(self.pesanan, Status.DIKONFIRMASI)

    def test_konfirmasi_butuh_petugas(self):
        with self.assertRaises(ValidationError):
            services.ubah_status(self.pesanan, Status.DIKONFIRMASI)

    def test_konfirmasi_menolak_bukan_petugas(self):
        with self.assertRaises(ValidationError):
            services.konfirmasi_pesanan(self.pesanan, self.admin)

    def test_konfirmasi_menolak_petugas_nonaktif(self):
        with self.assertRaises(ValidationError):
            services.konfirmasi_pesanan(self.pesanan, buat_petugas('dimas', is_active=False))

    def test_jadwalkan_butuh_tanggal_dan_sesi(self):
        services.konfirmasi_pesanan(self.pesanan, self.petugas)
        with self.assertRaises(ValidationError):
            services.ubah_status(self.pesanan, Status.DIJADWALKAN)

    def test_batal_butuh_alasan(self):
        with self.assertRaises(ValidationError):
            services.ubah_status(self.pesanan, Status.DIBATALKAN, catatan='   ')

    def test_batal_menyimpan_alasan(self):
        services.ubah_status(self.pesanan, Status.DIBATALKAN, catatan='Salah pilih lahan')
        self.assertEqual(self.pesanan.riwayat.get().catatan, 'Salah pilih lahan')


class GantiPetugasTests(TestCase):
    def setUp(self):
        self.pesanan = buat_pesanan(buat_lahan(buat_pemilik()))
        self.bima = buat_petugas('bima', first_name='Bima')
        self.laras = buat_petugas('laras', first_name='Laras')
        services.konfirmasi_pesanan(self.pesanan, self.bima)

    def test_ganti_petugas_nggak_ubah_status_dan_tercatat(self):
        services.ganti_petugas(self.pesanan, self.laras)
        self.pesanan.refresh_from_db()
        self.assertEqual(self.pesanan.petugas, self.laras)
        self.assertEqual(self.pesanan.status, Status.DIKONFIRMASI)
        catatan = self.pesanan.riwayat.last()
        self.assertEqual(catatan.jenis, RiwayatPesanan.Jenis.GANTI_PETUGAS)
        self.assertIn('Bima → Laras', catatan.catatan)

    def test_nggak_bisa_ganti_setelah_sampel_diambil(self):
        PesananPemeriksaan.objects.filter(pk=self.pesanan.pk).update(
            status=Status.SAMPEL_DIAMBIL,
        )
        with self.assertRaises(ValidationError):
            services.ganti_petugas(self.pesanan, self.laras)

    def test_nggak_bisa_ganti_ke_bukan_petugas(self):
        with self.assertRaises(ValidationError):
            services.ganti_petugas(self.pesanan, buat_pemilik('budi'))
