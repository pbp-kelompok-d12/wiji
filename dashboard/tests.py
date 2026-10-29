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
        for text in ['Lahan saya', 'Rekomendasi terbaik', 'Pesanan aktif', 'Catatan dari Wiji', 'Kebun Lereng Cibodas']:
            self.assertContains(self.response, text)

    def test_without_orders_shows_empty_state_with_order_button(self):
        self.assertContains(self.response, 'Belum ada pesanan berjalan')
        self.assertContains(self.response, reverse('inspections:pesan_pemeriksaan'))
        self.assertNotContains(self.response, 'class="now"')

    def test_chart_data_is_embedded_as_json(self):
        self.assertContains(self.response, 'id="chart-data"')
        self.assertEqual(self.response.context['chart']['values'], [46, 44, 49, 43, 45, 40, 42])

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
