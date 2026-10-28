from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from .. import pemesanan, services
from ..models import JenisPemeriksaan, PesananPemeriksaan, RiwayatPesanan
from .helpers import buat_lahan, buat_pemilik
from .test_services import buat_petugas

Status = PesananPemeriksaan.Status


def hari(n):
    return date.today() + timedelta(days=n)


class BuatPesananTests(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.lahan = buat_lahan(self.pemilik)
        self.jenis = JenisPemeriksaan.objects.get(slug='dasar')

    def buat(self, **kwargs):
        data = {
            'pemilik': self.pemilik, 'lahan': self.lahan, 'jenis': self.jenis,
            'tanggal_usulan': hari(3), 'sesi_usulan': 'pagi', **kwargs,
        }
        return pemesanan.buat_pesanan(**data)

    def test_pesanan_baru_berstatus_diajukan_dan_tercatat(self):
        pesanan = self.buat(catatan='  Parkir di warung  ')
        self.assertEqual(pesanan.status, Status.DIAJUKAN)
        self.assertEqual(pesanan.catatan, 'Parkir di warung')
        riwayat = pesanan.riwayat.get()
        self.assertEqual((riwayat.status_sesudah, riwayat.oleh), ('diajukan', self.pemilik))

    def test_tanggal_besok_dan_30_hari_lagi_boleh(self):
        self.buat(tanggal_usulan=hari(1))
        PesananPemeriksaan.objects.all().delete()
        self.buat(tanggal_usulan=hari(30))

    def test_tanggal_hari_ini_kemarin_dan_lebih_dari_30_hari_ditolak(self):
        for n in (0, -1, 31):
            with self.subTest(n=n), self.assertRaises(ValidationError):
                self.buat(tanggal_usulan=hari(n))
        self.assertFalse(PesananPemeriksaan.objects.exists())

    def test_lahan_orang_lain_ditolak(self):
        with self.assertRaises(ValidationError):
            self.buat(pemilik=buat_pemilik('dewi'))

    def test_lahan_diarsipkan_ditolak(self):
        self.lahan.arsipkan()
        with self.assertRaises(ValidationError):
            self.buat()

    def test_lahan_tanpa_koordinat_ditolak(self):
        lahan = buat_lahan(self.pemilik, nama='Tanpa koordinat', latitude=None, longitude=None)
        with self.assertRaises(ValidationError):
            self.buat(lahan=lahan)

    def test_lahan_draf_ditolak(self):
        lahan = buat_lahan(self.pemilik, nama='Draf', penggunaan=None)
        with self.assertRaises(ValidationError):
            self.buat(lahan=lahan)

    def test_jenis_nonaktif_ditolak(self):
        self.jenis.aktif = False
        self.jenis.save()
        with self.assertRaises(ValidationError):
            self.buat()

    def test_pesanan_aktif_ganda_ditolak(self):
        self.buat()
        with self.assertRaises(ValidationError):
            self.buat()
        self.assertEqual(PesananPemeriksaan.objects.count(), 1)

    def test_boleh_pesan_lagi_setelah_dibatalkan(self):
        pesanan = self.buat()
        pemesanan.batalkan_pesanan(pesanan, self.pemilik, 'Salah jadwal')
        self.buat()


class UbahUsulanTests(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.pesanan = pemesanan.buat_pesanan(
            self.pemilik, buat_lahan(self.pemilik), JenisPemeriksaan.objects.get(slug='dasar'), hari(3), 'pagi',
        )

    def test_ubah_usulan_selagi_diajukan(self):
        pemesanan.ubah_usulan(self.pesanan, hari(5), 'siang', 'Pindah ke siang')
        self.pesanan.refresh_from_db()
        self.assertEqual((self.pesanan.tanggal_usulan, self.pesanan.sesi_usulan), (hari(5), 'siang'))
        self.assertEqual(self.pesanan.catatan, 'Pindah ke siang')

    def test_usulan_nggak_bisa_diubah_setelah_dikonfirmasi(self):
        services.konfirmasi_pesanan(self.pesanan, buat_petugas())
        with self.assertRaises(ValidationError):
            pemesanan.ubah_usulan(self.pesanan, hari(5), 'siang')

    def test_tanggal_baru_tetap_divalidasi(self):
        with self.assertRaises(ValidationError):
            pemesanan.ubah_usulan(self.pesanan, hari(0), 'siang')


class BatalkanTests(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.pesanan = pemesanan.buat_pesanan(
            self.pemilik, buat_lahan(self.pemilik), JenisPemeriksaan.objects.get(slug='dasar'), hari(3), 'pagi',
        )
        self.petugas = buat_petugas()

    def test_batal_di_status_diajukan_dikonfirmasi_dan_dijadwalkan(self):
        for status in (Status.DIAJUKAN, Status.DIKONFIRMASI, Status.DIJADWALKAN):
            with self.subTest(status=status):
                PesananPemeriksaan.objects.filter(pk=self.pesanan.pk).update(status=status)
                pemesanan.batalkan_pesanan(self.pesanan, self.pemilik, 'Berubah pikiran')
                self.pesanan.refresh_from_db()
                self.assertEqual(self.pesanan.status, Status.DIBATALKAN)

    def test_batal_wajib_pakai_alasan(self):
        with self.assertRaises(ValidationError):
            pemesanan.batalkan_pesanan(self.pesanan, self.pemilik, '')

    def test_nggak_bisa_batal_setelah_sampel_diambil(self):
        PesananPemeriksaan.objects.filter(pk=self.pesanan.pk).update(status=Status.SAMPEL_DIAMBIL)
        with self.assertRaises(ValidationError):
            pemesanan.batalkan_pesanan(self.pesanan, self.pemilik, 'Terlambat')

    def test_pesanan_batal_tetap_tersimpan(self):
        pemesanan.batalkan_pesanan(self.pesanan, self.pemilik, 'Salah lahan')
        self.assertTrue(PesananPemeriksaan.objects.filter(pk=self.pesanan.pk).exists())


class JadwalUlangTests(TestCase):
    def setUp(self):
        self.pemilik = buat_pemilik()
        self.petugas = buat_petugas()
        self.pesanan = pemesanan.buat_pesanan(
            self.pemilik, buat_lahan(self.pemilik), JenisPemeriksaan.objects.get(slug='dasar'), hari(3), 'pagi',
        )
        services.konfirmasi_pesanan(self.pesanan, self.petugas)
        services.jadwalkan_pesanan(self.pesanan, hari(4), 'siang')

    def test_jadwal_ulang_ganti_usulan_kosongkan_final_dan_petugas_tetap(self):
        pemesanan.ajukan_jadwal_ulang(self.pesanan, self.pemilik, hari(10), 'pagi', 'Ada acara keluarga')
        self.pesanan.refresh_from_db()
        self.assertEqual(self.pesanan.status, Status.DIKONFIRMASI)
        self.assertEqual((self.pesanan.tanggal_usulan, self.pesanan.sesi_usulan), (hari(10), 'pagi'))
        self.assertIsNone(self.pesanan.tanggal_final)
        self.assertEqual(self.pesanan.sesi_final, '')
        self.assertEqual(self.pesanan.petugas, self.petugas)

    def test_riwayat_menyimpan_tanggal_lama_dan_baru(self):
        pemesanan.ajukan_jadwal_ulang(self.pesanan, self.pemilik, hari(10), 'pagi', 'Ada acara keluarga')
        catatan = self.pesanan.riwayat.last()
        self.assertEqual(catatan.jenis, RiwayatPesanan.Jenis.JADWAL_ULANG)
        self.assertEqual((catatan.tanggal_lama, catatan.tanggal_baru), (hari(4), hari(10)))
        self.assertEqual(catatan.catatan, 'Ada acara keluarga')

    def test_boleh_berkali_kali(self):
        for n in (10, 11, 12):
            pemesanan.ajukan_jadwal_ulang(self.pesanan, self.pemilik, hari(n), 'pagi', f'Alasan {n}')
        self.assertEqual(self.pesanan.riwayat.filter(jenis='jadwal_ulang').count(), 3)

    def test_alasan_wajib(self):
        with self.assertRaises(ValidationError):
            pemesanan.ajukan_jadwal_ulang(self.pesanan, self.pemilik, hari(10), 'pagi', ' ')

    def test_nggak_bisa_saat_masih_diajukan_atau_sudah_sampel_diambil(self):
        for status in (Status.DIAJUKAN, Status.SAMPEL_DIAMBIL):
            PesananPemeriksaan.objects.filter(pk=self.pesanan.pk).update(status=status)
            with self.subTest(status=status), self.assertRaises(ValidationError):
                pemesanan.ajukan_jadwal_ulang(self.pesanan, self.pemilik, hari(10), 'pagi', 'Alasan')
