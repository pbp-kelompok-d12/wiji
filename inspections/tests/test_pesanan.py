from django.db import IntegrityError, transaction
from django.test import TestCase

from ..models import PesananPemeriksaan, RiwayatPesanan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan


class PesananPemeriksaanTests(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.lahan = buat_lahan(self.pemilik)

    def test_status_awal_diajukan(self):
        self.assertEqual(buat_pesanan(self.lahan).status, PesananPemeriksaan.Status.DIAJUKAN)

    def test_kode_pakai_nomor_pesanan(self):
        pesanan = buat_pesanan(self.lahan)
        self.assertEqual(pesanan.kode, f'WJ-{pesanan.pk:04d}')

    def test_pemilik_dibaca_dari_lahan(self):
        self.assertEqual(buat_pesanan(self.lahan).pemilik, self.pemilik)

    def test_pesanan_selesai_dan_batal_nggak_aktif(self):
        pesanan = buat_pesanan(self.lahan)
        self.assertTrue(pesanan.aktif)
        for status in ('selesai', 'dibatalkan'):
            pesanan.status = status
            self.assertFalse(pesanan.aktif)

    def test_satu_lahan_cuma_boleh_satu_pesanan_aktif(self):
        buat_pesanan(self.lahan)
        with self.assertRaises(IntegrityError), transaction.atomic():
            buat_pesanan(self.lahan)

    def test_lahan_boleh_dipesan_lagi_setelah_pesanan_selesai_atau_batal(self):
        lama = buat_pesanan(self.lahan)
        lama.status = PesananPemeriksaan.Status.DIBATALKAN
        lama.save()
        buat_pesanan(self.lahan)
        self.assertEqual(self.lahan.inspection_orders.count(), 2)

    def test_lahan_lain_boleh_punya_pesanan_aktif_sendiri(self):
        buat_pesanan(self.lahan)
        buat_pesanan(buat_lahan(self.pemilik, nama='Pekarangan'))

    def test_aturan_arsip_lahan_membaca_pesanan(self):
        # lands.Lahan membaca relasi inspection_orders buat nentuin boleh arsip/hapus atau nggak
        self.assertTrue(self.lahan.dapat_diarsipkan)
        pesanan = buat_pesanan(self.lahan)
        self.assertFalse(self.lahan.dapat_diarsipkan)
        self.assertFalse(self.lahan.dapat_dihapus)
        pesanan.status = PesananPemeriksaan.Status.SELESAI
        pesanan.save()
        self.assertTrue(self.lahan.dapat_diarsipkan)
        self.assertFalse(self.lahan.dapat_dihapus)


class RiwayatPesananTests(TestCase):
    def test_riwayat_berurutan_dari_yang_paling_lama(self):
        pesanan = buat_pesanan(buat_lahan(buat_pemilik()))
        pertama = RiwayatPesanan.objects.create(pesanan=pesanan, status_sesudah='diajukan')
        kedua = RiwayatPesanan.objects.create(
            pesanan=pesanan, status_sebelum='diajukan', status_sesudah='dikonfirmasi',
        )
        self.assertEqual(list(pesanan.riwayat.all()), [pertama, kedua])
