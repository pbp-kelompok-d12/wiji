from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from .. import services
from ..models import PesananPemeriksaan, RiwayatPesanan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan
from .test_akses import buat_admin
from .test_services import buat_petugas

Status = PesananPemeriksaan.Status
HTMX = {'HTTP_HX_REQUEST': 'true'}


def hari(n):
    return date.today() + timedelta(days=n)


class KelolaAksiTestCase(TestCase):
    def setUp(self):
        self.admin = buat_admin()
        self.bima = buat_petugas('bima', first_name='Bima')
        self.laras = buat_petugas('laras', first_name='Laras')
        self.pesanan = buat_pesanan(buat_lahan(buat_pemilik()))
        self.client.force_login(self.admin)

    def url(self, nama):
        return reverse(f'inspections:{nama}', args=[self.pesanan.pk])

    def muat(self):
        self.pesanan.refresh_from_db()
        return self.pesanan

    def jadikan(self, status):
        PesananPemeriksaan.objects.filter(pk=self.pesanan.pk).update(status=status)


class AksesAksiTests(KelolaAksiTestCase):
    AKSI = ('kelola_tugaskan', 'kelola_jadwalkan', 'kelola_ganti_petugas', 'kelola_batalkan')

    def test_cuma_admin_yang_boleh(self):
        for user in (buat_pemilik('dewi'), buat_petugas('dimas')):
            self.client.force_login(user)
            for nama in self.AKSI:
                self.assertEqual(self.client.get(self.url(nama)).status_code, 403, (user, nama))
        self.client.logout()
        for nama in self.AKSI:
            self.assertEqual(self.client.get(self.url(nama)).status_code, 302)

    def test_aksi_di_pesanan_yang_nggak_ada_404(self):
        self.assertEqual(self.client.get(reverse('inspections:kelola_tugaskan', args=[9999])).status_code, 404)


class TugaskanTests(KelolaAksiTestCase):
    def test_tugaskan_mengubah_status_jadi_dikonfirmasi_dan_tercatat(self):
        response = self.client.post(self.url('kelola_tugaskan'), {'petugas': self.bima.pk, 'catatan': 'Dekat rumahnya'})
        self.assertRedirects(response, self.url('kelola_detail'))
        pesanan = self.muat()
        self.assertEqual((pesanan.status, pesanan.petugas), (Status.DIKONFIRMASI, self.bima))
        catatan = pesanan.riwayat.last()
        self.assertEqual((catatan.status_sesudah, catatan.oleh, catatan.catatan), ('dikonfirmasi', self.admin, 'Dekat rumahnya'))

    def test_pilihan_cuma_petugas_aktif(self):
        buat_petugas('nonaktif', is_active=False)
        buat_pemilik('pemilik-lain')
        pilihan = {u.username for u in self.client.get(self.url('kelola_tugaskan')).context['form'].fields['petugas'].queryset}
        self.assertEqual(pilihan, {'bima', 'laras'})

    def test_tanpa_petugas_ditolak(self):
        response = self.client.post(self.url('kelola_tugaskan'), {})
        self.assertEqual(response.status_code, 200)
        self.assertIn('petugas', response.context['form'].errors)
        self.assertEqual(self.muat().status, Status.DIAJUKAN)

    def test_pemilik_bukan_petugas_ditolak(self):
        lain = buat_pemilik('dewi')
        response = self.client.post(self.url('kelola_tugaskan'), {'petugas': lain.pk})
        self.assertIn('petugas', response.context['form'].errors)

    def test_nggak_bisa_tugaskan_ulang_pesanan_yang_sudah_dikonfirmasi(self):
        services.konfirmasi_pesanan(self.pesanan, self.bima)
        response = self.client.post(self.url('kelola_tugaskan'), {'petugas': self.laras.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.muat().petugas, self.bima)

    def test_htmx_buka_modal_lalu_berhasil_ganti_isi_detail(self):
        self.assertContains(self.client.get(self.url('kelola_tugaskan'), **HTMX), 'Tugaskan petugas')
        response = self.client.post(self.url('kelola_tugaskan'), {'petugas': self.bima.pk}, **HTMX)
        self.assertContains(response, 'Petugas sudah ditugaskan')
        self.assertContains(response, 'id="konten-pesanan"')
        self.assertContains(response, 'hx-swap-oob="true"')
        self.assertContains(response, 'Tetapkan jadwal')


class JadwalkanTests(KelolaAksiTestCase):
    def setUp(self):
        super().setUp()
        services.konfirmasi_pesanan(self.pesanan, self.bima)

    def test_tetapkan_jadwal_mengubah_status_jadi_dijadwalkan(self):
        self.client.post(self.url('kelola_jadwalkan'), {'tanggal': hari(5).isoformat(), 'sesi': 'siang'})
        pesanan = self.muat()
        self.assertEqual(pesanan.status, Status.DIJADWALKAN)
        self.assertEqual((pesanan.tanggal_final, pesanan.sesi_final), (hari(5), 'siang'))

    def test_form_terisi_usulan_pemilik(self):
        form = self.client.get(self.url('kelola_jadwalkan')).context['form']
        self.assertEqual(form.initial['tanggal'], self.pesanan.tanggal_usulan)

    def test_hari_ini_boleh_kemarin_ditolak(self):
        self.client.post(self.url('kelola_jadwalkan'), {'tanggal': hari(0).isoformat(), 'sesi': 'pagi'})
        self.assertEqual(self.muat().status, Status.DIJADWALKAN)
        self.jadikan(Status.DIKONFIRMASI)
        response = self.client.post(self.url('kelola_jadwalkan'), {'tanggal': hari(-1).isoformat(), 'sesi': 'pagi'})
        self.assertIn('tanggal', response.context['form'].errors)
        self.assertEqual(self.muat().status, Status.DIKONFIRMASI)

    def test_sesi_dan_tanggal_wajib(self):
        response = self.client.post(self.url('kelola_jadwalkan'), {})
        self.assertEqual(set(response.context['form'].errors), {'tanggal', 'sesi'})

    def test_nggak_bisa_selagi_masih_diajukan(self):
        self.jadikan(Status.DIAJUKAN)
        response = self.client.post(self.url('kelola_jadwalkan'), {'tanggal': hari(5).isoformat(), 'sesi': 'pagi'})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.muat().tanggal_final)

    def test_setelah_jadwal_ulang_pemilik_admin_menetapkan_jadwal_baru(self):
        from .. import pemesanan
        services.jadwalkan_pesanan(self.pesanan, hari(5), 'pagi')
        pemesanan.ajukan_jadwal_ulang(self.pesanan, self.pesanan.pemilik, hari(9), 'siang', 'Ada acara')
        self.assertEqual(self.muat().status, Status.DIKONFIRMASI)
        self.client.post(self.url('kelola_jadwalkan'), {'tanggal': hari(9).isoformat(), 'sesi': 'siang'})
        pesanan = self.muat()
        self.assertEqual((pesanan.status, pesanan.tanggal_final, pesanan.petugas), (Status.DIJADWALKAN, hari(9), self.bima))


class GantiPetugasTests(KelolaAksiTestCase):
    def setUp(self):
        super().setUp()
        services.konfirmasi_pesanan(self.pesanan, self.bima)

    def test_ganti_petugas_nggak_ubah_status_dan_tercatat(self):
        self.client.post(self.url('kelola_ganti_petugas'), {'petugas': self.laras.pk, 'catatan': 'Bima sakit'})
        pesanan = self.muat()
        self.assertEqual((pesanan.petugas, pesanan.status), (self.laras, Status.DIKONFIRMASI))
        catatan = pesanan.riwayat.last()
        self.assertEqual((catatan.jenis, catatan.oleh), (RiwayatPesanan.Jenis.GANTI_PETUGAS, self.admin))
        self.assertIn('Bima → Laras', catatan.catatan)
        self.assertIn('Bima sakit', catatan.catatan)

    def test_petugas_sekarang_nggak_ada_di_pilihan(self):
        pilihan = {u.username for u in self.client.get(self.url('kelola_ganti_petugas')).context['form'].fields['petugas'].queryset}
        self.assertEqual(pilihan, {'laras'})

    def test_nggak_bisa_setelah_sampel_diambil(self):
        self.jadikan(Status.SAMPEL_DIAMBIL)
        response = self.client.post(self.url('kelola_ganti_petugas'), {'petugas': self.laras.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.muat().petugas, self.bima)


class BatalkanAdminTests(KelolaAksiTestCase):
    def test_admin_membatalkan_dengan_alasan_dan_pelaku_tercatat(self):
        self.client.post(self.url('kelola_batalkan'), {'alasan': 'Lahan sedang dipakai'})
        pesanan = self.muat()
        self.assertEqual(pesanan.status, Status.DIBATALKAN)
        catatan = pesanan.riwayat.last()
        self.assertEqual((catatan.oleh, catatan.catatan), (self.admin, 'Lahan sedang dipakai'))
        self.assertTrue(catatan.dibuat_pada)

    def test_alasan_wajib(self):
        response = self.client.post(self.url('kelola_batalkan'), {'alasan': ''})
        self.assertIn('alasan', response.context['form'].errors)
        self.assertEqual(self.muat().status, Status.DIAJUKAN)

    def test_nggak_bisa_setelah_sampel_diambil(self):
        self.jadikan(Status.SAMPEL_DIAMBIL)
        response = self.client.post(self.url('kelola_batalkan'), {'alasan': 'Terlambat'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.muat().status, Status.SAMPEL_DIAMBIL)

    def test_pemilik_melihat_pembatalan_oleh_admin_di_riwayatnya(self):
        self.client.post(self.url('kelola_batalkan'), {'alasan': 'Lahan sedang dipakai'})
        self.client.force_login(self.pesanan.pemilik)
        response = self.client.get(reverse('inspections:detail_pesanan', args=[self.pesanan.pk]))
        self.assertContains(response, 'Lahan sedang dipakai')


class TombolDetailAdminTests(KelolaAksiTestCase):
    def tombol(self):
        isi = self.client.get(self.url('kelola_detail')).content.decode()
        return [self.url(n) in isi for n in ('kelola_tugaskan', 'kelola_jadwalkan', 'kelola_ganti_petugas', 'kelola_batalkan')]

    def test_tombol_sesuai_status(self):
        harapan = {
            Status.DIAJUKAN: [True, False, False, True],
            Status.DIKONFIRMASI: [False, True, True, True],
            Status.DIJADWALKAN: [False, False, True, True],
            Status.SAMPEL_DIAMBIL: [False, False, False, False],
            Status.DIPROSES: [False, False, False, False],
            Status.SELESAI: [False, False, False, False],
            Status.DIBATALKAN: [False, False, False, False],
        }
        for status, tombol in harapan.items():
            with self.subTest(status=status):
                self.jadikan(status)
                self.assertEqual(self.tombol(), tombol)
