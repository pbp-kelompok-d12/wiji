from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.models import Tanaman


class LandingTests(TestCase):
    def test_landing_is_public(self):
        response = self.client.get(reverse('core:landing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kenali tanahmu.')

    def test_guest_sees_login_and_register(self):
        response = self.client.get(reverse('core:landing'))
        self.assertContains(response, reverse('accounts:login'))
        self.assertContains(response, reverse('accounts:register'))

    def test_logged_in_user_sees_logout_instead(self):
        user = User.objects.create_user('sari', 'sari@contoh.id', 'tanah12345', first_name='Sari')
        self.client.force_login(user)
        response = self.client.get(reverse('core:landing'))
        self.assertContains(response, 'Keluar')
        self.assertContains(response, 'Sari')
        self.assertNotContains(response, reverse('accounts:login'))

    def test_has_all_sections_in_order(self):
        html = self.client.get(reverse('core:landing')).content.decode()
        ids = ['id="cara-kerja"', 'id="peran"', 'id="langkah"', 'id="tanya"']
        positions = [html.index(i) for i in ids]
        self.assertEqual(positions, sorted(positions))

    def test_steps_list_has_four_steps(self):
        response = self.client.get(reverse('core:landing'))
        self.assertContains(response, 'class="lp-langkah__n"', count=4)

    def test_navbar_is_overlay_and_links_to_sections(self):
        response = self.client.get(reverse('core:landing'))
        self.assertContains(response, 'site-header--overlay')
        self.assertContains(response, '#langkah')
        self.assertContains(response, '#tanya')
        self.assertContains(response, reverse('core:daftar_tanaman'))
        self.assertContains(response, 'logo-wordmark.svg')

    def test_landing_loads_its_own_assets(self):
        response = self.client.get(reverse('core:landing'))
        self.assertContains(response, 'css/landing.css')
        self.assertContains(response, 'js/landing.js')

    def test_logged_in_user_gets_dashboard_button(self):
        user = User.objects.create_user('sari', 'sari@contoh.id', 'tanah12345')
        self.client.force_login(user)
        response = self.client.get(reverse('core:landing'))
        self.assertContains(response, 'Buka dashboard')
        self.assertNotContains(response, reverse('accounts:register'))

    def test_photo_credits_are_shown(self):
        response = self.client.get(reverse('core:landing'))
        self.assertContains(response, 'Foto: USDA')
        self.assertContains(response, 'Ksheera Piraati, CC BY 4.0')


class HalamanErrorTests(TestCase):
    def test_404_page_is_styled_and_has_links_out(self):
        response = self.client.get('/halaman-yang-tidak-ada/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'nggak ketemu.', status_code=404)
        self.assertContains(response, 'href="%s"' % reverse('core:landing'), status_code=404)
        self.assertContains(response, reverse('core:daftar_tanaman'), status_code=404)
        self.assertContains(response, 'css/errors.css', status_code=404)

    def test_403_page_for_logged_in_owner_offers_dashboard_and_logout(self):
        owner = User.objects.create_user('sari', 'sari@contoh.id', 'tanah12345')
        self.client.force_login(owner)
        # Halaman kelola pesanan cuma buat admin, jadi pemilik kena 403
        response = self.client.get(reverse('inspections:kelola_daftar'))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'bukan milikmu.', status_code=403)
        self.assertContains(response, reverse('dashboard:home'), status_code=403)
        self.assertContains(response, reverse('accounts:logout'), status_code=403)
        self.assertContains(response, 'er--dark', status_code=403)

    def test_500_page_renders_without_a_request(self):
        # Halaman 500 dirender tanpa request/context, jadi tes lewat view bawaan Django
        from django.test import RequestFactory
        from django.views.defaults import server_error

        response = server_error(RequestFactory().get('/'))
        self.assertEqual(response.status_code, 500)
        body = response.content.decode()
        self.assertIn('sisi kami.', body)
        self.assertIn('Muat ulang', body)
        self.assertIn(reverse('core:landing'), body)


class KatalogAwalTests(TestCase):
    """Data awal dari migrasi: syarat tugas minimal 50 tanaman saat deploy."""

    def test_katalog_punya_minimal_50_tanaman_dan_nama_unik(self):
        from core.models import Tanaman
        self.assertGreaterEqual(Tanaman.objects.count(), 50)
        nama = list(Tanaman.objects.values_list('nama', flat=True))
        self.assertEqual(len(nama), len(set(nama)))

    def test_semua_tanaman_punya_sumber_dan_kondisi_tumbuh(self):
        from core.models import Tanaman
        for tanaman in Tanaman.objects.all():
            self.assertTrue(tanaman.sumber_penelitian, tanaman.nama)
            self.assertTrue(tanaman.kondisi_pertumbuhan.startswith('pH tanah'), tanaman.nama)
            self.assertTrue(tanaman.referensi.exists(), tanaman.nama)
            self.assertTrue(tanaman.tujuan_pengelolaan.exists(), tanaman.nama)

    def test_setiap_tujuan_lahan_punya_tanaman_yang_cocok(self):
        from core.models import Tanaman
        from lands.models import ManagementGoal
        from recommendations.services import _goal_matches_plant
        for tujuan in ManagementGoal.objects.filter(aktif=True):
            cocok = [t for t in Tanaman.objects.all() if _goal_matches_plant(tujuan, t)]
            self.assertTrue(cocok, tujuan.slug)

    def test_tanaman_fitoremediasi_punya_kemampuan_kontaminan_bersumber(self):
        from core.models import PlantContaminantCapability, Tanaman
        remediasi = Tanaman.objects.exclude(kontaminan_ditangani__isnull=True)
        self.assertGreaterEqual(remediasi.count(), 4)
        for tanaman in remediasi:
            self.assertTrue(tanaman.kemampuan_kontaminan.exists(), tanaman.nama)
            self.assertTrue(tanaman.referensi.exists(), tanaman.nama)
        # Nggak ada klaim persentase keberhasilan
        for kemampuan in PlantContaminantCapability.objects.all():
            self.assertNotIn('%', kemampuan.tingkat_efektivitas)

    def test_tanaman_yang_berisiko_diblokir_dari_rekomendasi_otomatis(self):
        from core.models import Tanaman
        from recommendations.services import _is_high_risk
        for nama in ('Lamtoro', 'Bunga matahari', 'Sawi india', 'Pakis arsenik'):
            self.assertTrue(_is_high_risk(Tanaman.objects.get(nama=nama)), nama)
        self.assertFalse(_is_high_risk(Tanaman.objects.get(nama='Akar wangi')))

    def test_perintah_seed_aman_dijalankan_berulang(self):
        from django.core.management import call_command
        from core.models import PlantReference, Tanaman
        sebelum = (Tanaman.objects.count(), PlantReference.objects.count())
        call_command('seed_tanaman', stdout=__import__('io').StringIO())
        self.assertEqual((Tanaman.objects.count(), PlantReference.objects.count()), sebelum)


class KatalogPublikTests(TestCase):
    """Katalog dibaca publik, dikelola staf, dan bisa dicari, diarsipkan, serta dibaca lewat JSON."""

    @classmethod
    def setUpTestData(cls):
        cls.staf = User.objects.create_user('staf.katalog', password='katalog-12345', is_staff=True)
        cls.pemilik = User.objects.create_user('pemilik.katalog', password='katalog-12345')
        cls.aktif = Tanaman.objects.get(nama='Kangkung darat')
        cls.fito = Tanaman.objects.get(nama='Akar wangi')

    def test_pengunjung_bisa_baca_daftar_dan_detail(self):
        self.assertEqual(self.client.get(reverse('core:daftar_tanaman')).status_code, 200)
        r = self.client.get(reverse('core:detail_tanaman', args=[self.fito.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Truong')

    def test_pengunjung_dan_pemilik_tidak_bisa_mengelola(self):
        urls = [reverse('core:tambah_tanaman'), reverse('core:ubah_tanaman', args=[self.aktif.pk]),
                reverse('core:hapus_tanaman', args=[self.aktif.pk])]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.pemilik)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(self.client.post(reverse('core:arsip_tanaman', args=[self.aktif.pk])).status_code, 302)
        self.aktif.refresh_from_db()
        self.assertFalse(self.aktif.diarsipkan)

    def test_pencarian_menyaring_nama(self):
        r = self.client.get(reverse('core:daftar_tanaman'), {'q': 'kangkung'})
        self.assertContains(r, 'Kangkung')
        self.assertNotContains(r, 'Akar wangi')

    def test_filter_tujuan_dan_jenis(self):
        r = self.client.get(reverse('core:daftar_tanaman'), {'jenis': 'fitoremediasi'})
        self.assertContains(r, 'Akar wangi')
        self.assertNotContains(r, 'Kangkung')
        r = self.client.get(reverse('core:daftar_tanaman'), {'tujuan': 'pemulihan-tanah-tercemar'})
        self.assertContains(r, 'Akar wangi')
        self.assertNotContains(r, 'Kangkung')

    def test_htmx_hanya_membalas_daftar_kartu(self):
        r = self.client.get(reverse('core:daftar_tanaman'), {'q': 'kangkung'}, headers={'HX-Request': 'true'})
        self.assertContains(r, 'Kangkung')
        self.assertNotContains(r, '<html')

    def test_arsip_menyembunyikan_dari_publik_tapi_tidak_dari_staf(self):
        self.client.force_login(self.staf)
        self.client.post(reverse('core:arsip_tanaman', args=[self.aktif.pk]))
        self.aktif.refresh_from_db()
        self.assertTrue(self.aktif.diarsipkan)
        self.assertEqual(self.client.get(reverse('core:detail_tanaman', args=[self.aktif.pk])).status_code, 200)
        self.assertContains(self.client.get(reverse('core:daftar_tanaman'), {'arsip': '1'}), 'Kangkung')
        self.client.logout()
        self.assertEqual(self.client.get(reverse('core:detail_tanaman', args=[self.aktif.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('core:daftar_tanaman')), 'Kangkung')
        self.assertEqual(self.client.get(reverse('core:api_detail_tanaman', args=[self.aktif.pk])).status_code, 404)
        self.client.force_login(self.staf)
        self.client.post(reverse('core:pulihkan_tanaman', args=[self.aktif.pk]))
        self.aktif.refresh_from_db()
        self.assertFalse(self.aktif.diarsipkan)

    def test_pengunjung_tidak_bisa_lihat_arsip_lewat_parameter(self):
        self.aktif.diarsipkan = True
        self.aktif.save()
        self.assertNotContains(self.client.get(reverse('core:daftar_tanaman'), {'arsip': '1'}), 'Kangkung')

    def test_arsip_hanya_lewat_post(self):
        self.client.force_login(self.staf)
        self.assertEqual(self.client.get(reverse('core:arsip_tanaman', args=[self.aktif.pk])).status_code, 405)

    def test_staf_bisa_tambah_ubah_dan_hapus_yang_belum_dipakai(self):
        self.client.force_login(self.staf)
        data = {'nama': 'Tanaman uji', 'fungsi': 'Uji', 'deskripsi': 'Deskripsi uji', 'kondisi_pertumbuhan': 'pH 6'}
        self.assertEqual(self.client.post(reverse('core:tambah_tanaman'), data).status_code, 302)
        baru = Tanaman.objects.get(nama='Tanaman uji')
        data['nama'] = 'Tanaman uji ubah'
        self.client.post(reverse('core:ubah_tanaman', args=[baru.pk]), data)
        baru.refresh_from_db()
        self.assertEqual(baru.nama, 'Tanaman uji ubah')
        self.client.post(reverse('core:hapus_tanaman', args=[baru.pk]))
        self.assertFalse(Tanaman.objects.filter(pk=baru.pk).exists())

    def test_tanaman_yang_sudah_dipakai_rekomendasi_tidak_bisa_dihapus(self):
        from unittest import mock
        self.client.force_login(self.staf)
        with mock.patch.object(Tanaman, 'sudah_dipakai', new_callable=mock.PropertyMock, return_value=True):
            r = self.client.post(reverse('core:hapus_tanaman', args=[self.aktif.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Tanaman.objects.filter(pk=self.aktif.pk).exists())

    def test_json_daftar_dan_detail_bisa_dibaca_publik(self):
        r = self.client.get(reverse('core:api_tanaman'), {'q': 'akar wangi'})
        self.assertEqual(r.status_code, 200)
        hasil = r.json()['hasil']
        self.assertEqual([t['nama'] for t in hasil], ['Akar wangi'])
        detail = self.client.get(reverse('core:api_detail_tanaman', args=[self.fito.pk])).json()
        self.assertTrue(detail['referensi'])
        self.assertTrue(detail['kemampuan_kontaminan'])
        self.assertIn('pemulihan-tanah-tercemar', detail['tujuan'])

    def test_json_tidak_menerima_perubahan(self):
        self.assertEqual(self.client.post(reverse('core:api_tanaman')).status_code, 405)


class SeedDemoTests(TestCase):
    """Satu perintah isi data demo semua modul, aman dijalankan berulang."""

    def jalankan(self, **opsi):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_demo', stdout=StringIO(), **opsi)

    def test_mengisi_semua_modul(self):
        from inspections.models import PesananPemeriksaan
        from recommendations.models import ManagementPlan
        from soil_results.models import HasilPemeriksaan
        self.jalankan()
        self.assertEqual(PesananPemeriksaan.objects.count(), 8)
        self.assertEqual(HasilPemeriksaan.objects.count(), 4)
        self.assertEqual(ManagementPlan.objects.count(), 2)
        self.assertTrue(User.objects.filter(username='pemilik.demo').exists())

    def test_pesanan_selesai_punya_hasil_final(self):
        from soil_results.models import HasilPemeriksaan
        self.jalankan()
        hasil = HasilPemeriksaan.objects.get(pesanan__status='selesai')
        self.assertEqual(hasil.status_hasil, 'final')
        self.assertEqual(hasil.asal, 'wiji')

    def test_pesanan_diproses_punya_draf_buat_dilanjutkan(self):
        from soil_results.models import HasilPemeriksaan
        self.jalankan()
        self.assertEqual(HasilPemeriksaan.objects.get(pesanan__status='diproses').status_hasil, 'draf')

    def test_lahan_bertimbal_tinggi_menghentikan_rekomendasi_otomatis(self):
        from recommendations.services import assess_soil_risk
        from soil_results.models import HasilPemeriksaan
        self.jalankan()
        hasil = HasilPemeriksaan.objects.get(lahan__nama='Kebun Kopi Sukamakmur')
        self.assertTrue(assess_soil_risk(hasil)['risiko_tinggi'])

    def test_rencana_memakai_tanaman_dari_katalog(self):
        from recommendations.models import ManagementPlan
        self.jalankan()
        for rencana in ManagementPlan.objects.select_related('rekomendasi__tanaman'):
            self.assertTrue(Tanaman.objects.filter(pk=rencana.rekomendasi.tanaman_id).exists())
            self.assertEqual(rencana.pemilik.username, 'pemilik.demo')

    def test_dijalankan_berulang_tidak_menggandakan_data(self):
        from soil_results.models import HasilPemeriksaan
        self.jalankan()
        self.jalankan()
        self.assertEqual(HasilPemeriksaan.objects.count(), 4)

    def test_ulang_membuat_data_dari_awal(self):
        from recommendations.models import ManagementPlan
        from soil_results.models import HasilPemeriksaan
        self.jalankan()
        self.jalankan(ulang=True)
        self.assertEqual(HasilPemeriksaan.objects.count(), 4)
        self.assertEqual(ManagementPlan.objects.count(), 2)
