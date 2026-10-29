from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class DashboardAccessTests(TestCase):
    def test_guest_is_sent_to_login(self):
        response = self.client.get(reverse('dashboard:home'))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('dashboard:home')}")

    def test_owner_sees_dashboard(self):
        owner = User.objects.create_user('sari', 'sari@contoh.id', 'tanah12345', first_name='Sari Rahayu')
        self.client.force_login(owner)
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/owner.html')
        self.assertContains(response, 'Selamat datang, ')
        self.assertContains(response, 'Sari!')

    def test_officer_sees_officer_dashboard(self):
        officer = User.objects.create_user('budi', 'budi@contoh.id', 'tanah12345', role=User.Role.OFFICER, first_name='Budi Santoso')
        self.client.force_login(officer)
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/petugas.html')
        self.assertContains(response, 'Halo, ')
        self.assertContains(response, 'Budi!')
        self.assertNotContains(response, 'Lahan saya')

    def test_staff_sees_admin_dashboard_even_though_role_is_owner(self):
        # Akun dari createsuperuser perannya owner, tapi tetap harus dapat dashboard admin
        admin = User.objects.create_user('admin', 'a@contoh.id', 'tanah12345', is_staff=True)
        self.assertTrue(admin.is_owner)
        self.client.force_login(admin)
        response = self.client.get(reverse('dashboard:home'))
        self.assertTemplateUsed(response, 'dashboard/admin.html')
        self.assertTemplateNotUsed(response, 'dashboard/owner.html')
        self.assertContains(response, reverse('inspections:kelola_daftar'))

    def test_staff_with_officer_role_sees_admin_dashboard(self):
        admin = User.objects.create_user('admin', 'a@contoh.id', 'tanah12345', role=User.Role.OFFICER, is_staff=True)
        self.client.force_login(admin)
        response = self.client.get(reverse('dashboard:home'))
        self.assertTemplateUsed(response, 'dashboard/admin.html')


class DashboardContentTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('sari', 'sari@contoh.id', 'tanah12345', first_name='Sari Rahayu')
        self.client.force_login(self.owner)
        self.response = self.client.get(reverse('dashboard:home'))

    def test_shows_main_sections(self):
        for text in ['Lahan saya', 'Rekomendasi terbaik', 'Pesanan aktif', 'Hasil tanah terbaru', 'Catatan dari Wiji']:
            self.assertContains(self.response, text)

    def test_new_owner_sees_empty_states_instead_of_sample_data(self):
        for text in ['Belum ada lahan', 'Belum ada rekomendasi', 'Belum ada pesanan berjalan', 'Belum ada hasil tanah']:
            self.assertContains(self.response, text)
        for sample in ['Kebun Lereng Cibodas', 'Pekarangan Dramaga', 'Akar wangi', 'contoh']:
            self.assertNotContains(self.response, sample)

    def test_without_orders_shows_order_button(self):
        self.assertContains(self.response, reverse('inspections:pesan_pemeriksaan'))
        self.assertNotContains(self.response, 'class="now"')

    def test_summary_cards_are_all_zero_for_new_owner(self):
        self.assertEqual([k['value'] for k in self.response.context['kpis']], [0, 0, 0, 0])

    def test_sidebar_has_active_item_and_logout_form(self):
        self.assertContains(self.response, 'side-link is-active')
        self.assertContains(self.response, reverse('accounts:logout'))
        self.assertContains(self.response, 'SR')  # inisial di avatar

    def test_dashboard_loads_its_script(self):
        self.assertContains(self.response, 'js/dashboard.js')


class DashboardActiveOrderTests(TestCase):
    def setUp(self):
        from inspections.tests.helpers import buat_lahan, buat_pesanan
        from inspections import services

        self.owner = User.objects.create_user('sari', 'sari@contoh.id', 'tanah12345', first_name='Sari Rahayu')
        self.order = buat_pesanan(buat_lahan(self.owner, nama='Kebun Cibodas'))
        officer = User.objects.create_user('bima', 'b@contoh.id', 'tanah12345', first_name='Bima', role=User.Role.OFFICER)
        services.konfirmasi_pesanan(self.order, officer)
        self.client.force_login(self.owner)
        self.response = self.client.get(reverse('dashboard:home'))

    def test_shows_real_active_order(self):
        self.assertContains(self.response, self.order.kode)
        self.assertContains(self.response, 'Kebun Cibodas')
        self.assertContains(self.response, 'Petugas: Bima')

    def test_stepper_marks_current_status(self):
        self.assertContains(self.response, 'class="now"', count=1)
        self.assertContains(self.response, 'class="done"', count=1)

    def test_order_card_links_to_detail_and_actions(self):
        self.assertContains(self.response, reverse('inspections:detail_pesanan', args=[self.order.pk]))
        self.assertContains(self.response, reverse('inspections:batalkan_pesanan', args=[self.order.pk]))
        self.assertContains(self.response, reverse('inspections:jadwal_ulang', args=[self.order.pk]))

    def test_summary_card_counts_active_orders(self):
        kpi = self.response.context['kpis'][1]
        self.assertEqual((kpi['label'], kpi['value']), ('Pesanan aktif', 1))
        self.assertEqual(kpi['chip']['text'], 'Dikonfirmasi')

    def test_cancelled_order_is_not_shown_as_active(self):
        from inspections import pemesanan

        pemesanan.batalkan_pesanan(self.order, self.owner, 'Salah lahan')
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'Belum ada pesanan berjalan')
        self.assertEqual(response.context['kpis'][1]['value'], 0)

    def test_other_owners_orders_are_not_shown(self):
        other = User.objects.create_user('dewi', 'd@contoh.id', 'tanah12345')
        self.client.force_login(other)
        response = self.client.get(reverse('dashboard:home'))
        self.assertNotContains(response, self.order.kode)


class DashboardRealDataTests(TestCase):
    def setUp(self):
        from datetime import date
        from decimal import Decimal

        from core.models import Tanaman
        from lands.models import Lahan, ManagementGoal
        from recommendations.models import ManagementPlan, RecommendationSnapshot
        from soil_results.models import HasilPemeriksaan

        self.owner = User.objects.create_user('sari', 'sari@contoh.id', 'tanah12345', first_name='Sari Rahayu')
        data = {'alamat': 'Cianjur', 'latitude': '-6.8', 'longitude': '107.0', 'luas_m2': 1200, 'penggunaan': 'kebun'}
        self.siap = Lahan.objects.create(owner=self.owner, nama='Kebun Cibodas', **data)
        self.draf = Lahan.objects.create(owner=self.owner, nama='Lahan Draf')
        self.arsip = Lahan.objects.create(owner=self.owner, nama='Lahan Arsip', **data)
        self.arsip.arsipkan()
        self.milik_lain = Lahan.objects.create(owner=User.objects.create_user('dewi', 'd@contoh.id', 'tanah12345'), nama='Lahan Dewi', **data)

        self.hasil = HasilPemeriksaan.objects.create(
            lahan=self.siap, tanggal_pemeriksaan=date(2026, 10, 20), ph=Decimal('6.40'), tekstur='Lempung',
            asal=HasilPemeriksaan.Asal.WIJI,
        )
        tanaman = Tanaman.objects.create(nama='Kara benguk', nama_latin='Mucuna pruriens', fungsi='Menambah bahan organik', deskripsi='x', kondisi_pertumbuhan='x')
        lain = Tanaman.objects.create(nama='Tanaman Skor Rendah', fungsi='x', deskripsi='x', kondisi_pertumbuhan='x')
        tujuan = ManagementGoal.objects.first()
        buat = lambda t, skor: RecommendationSnapshot.objects.create(
            lahan=self.siap, hasil_pemeriksaan=self.hasil, tanaman=t, tujuan=tujuan, skor=skor,
            alasan=['pH 6,4 masuk rentang tumbuh.'], input_snapshot={'ph': '6.40', 'tekstur': 'Lempung'}, kelengkapan_data=90,
        )
        buat(lain, 40)
        self.terbaik = buat(tanaman, 86)
        ManagementPlan.objects.create(pemilik=self.owner, lahan=self.siap, rekomendasi=self.terbaik)
        self.client.force_login(self.owner)
        self.response = self.client.get(reverse('dashboard:home'))

    def test_summary_cards_count_real_data(self):
        lahan, pesanan, hasil, rencana = self.response.context['kpis']
        self.assertEqual((lahan['value'], lahan['chip']['text']), (2, '1 draf'))
        self.assertEqual(hasil['value'], 1)
        self.assertEqual(hasil['chip']['text'], '1 dari petugas')
        self.assertEqual((rencana['value'], rencana['chip']['text']), (1, 'Kara benguk'))

    def test_land_card_lists_own_unarchived_lands_with_status(self):
        self.assertContains(self.response, 'Kebun Cibodas')
        self.assertContains(self.response, 'Lahan Draf')
        self.assertNotContains(self.response, 'Lahan Arsip')
        self.assertNotContains(self.response, 'Lahan Dewi')
        self.assertContains(self.response, 'Siap dipesan')
        self.assertContains(self.response, 'Perlu dilengkapi')

    def test_land_card_shows_latest_soil_values(self):
        self.assertContains(self.response, 'pH 6,40')
        self.assertContains(self.response, 'Lempung')

    def test_ready_land_has_order_button_with_land_preselected(self):
        self.assertContains(self.response, f"{reverse('inspections:pesan_pemeriksaan')}?lahan={self.siap.pk}")

    def test_draft_land_has_complete_button_instead(self):
        self.assertContains(self.response, reverse('lands:ubah_lahan', args=[self.draf.pk]))

    def test_land_with_active_order_shows_no_order_button(self):
        from inspections.tests.helpers import buat_pesanan
        buat_pesanan(self.siap)
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'Pesanan aktif')
        self.assertNotContains(response, f"{reverse('inspections:pesan_pemeriksaan')}?lahan={self.siap.pk}")

    def test_best_recommendation_is_highest_score(self):
        rekomendasi = self.response.context['rekomendasi']
        self.assertEqual(rekomendasi['snap'], self.terbaik)
        self.assertContains(self.response, 'Kara benguk')
        self.assertContains(self.response, 'Mucuna pruriens')
        self.assertNotContains(self.response, 'Tanaman Skor Rendah')
        self.assertContains(self.response, 'pH 6,4 masuk rentang tumbuh.')

    def test_latest_soil_result_card(self):
        self.assertContains(self.response, 'Hasil tanah terbaru')
        self.assertContains(self.response, reverse('soil_results:detail_hasil', args=[self.hasil.pk]))
        self.assertContains(self.response, 'Hasil Wiji')

    def test_notes_come_from_real_state(self):
        teks = ' '.join(c['text'] for c in self.response.context['catatan'])
        self.assertIn('1 lahan belum lengkap', teks)
        self.assertIn('Kara benguk paling cocok buat Kebun Cibodas (skor 86)', teks)

    def test_recent_activity_mixes_modules_newest_first(self):
        judul = [a['title'] for a in self.response.context['aktivitas']]
        self.assertTrue(any('Lahan ditambahkan' in j for j in judul))
        self.assertTrue(any('Hasil tanah dicatat' in j for j in judul))
        self.assertIn('Rencana disimpan', judul)
        waktu = [a['waktu'] for a in self.response.context['aktivitas']]
        self.assertEqual(waktu, sorted(waktu, reverse=True))

    def test_another_owner_sees_none_of_it(self):
        self.client.force_login(self.milik_lain.owner)
        response = self.client.get(reverse('dashboard:home'))
        for teks in ('Kebun Cibodas', 'Kara benguk', 'Lahan Draf'):
            self.assertNotContains(response, teks)
        self.assertEqual(response.context['kpis'][2]['value'], 0)
