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

    def test_officer_sees_pending_page(self):
        officer = User.objects.create_user('budi', 'budi@contoh.id', 'tanah12345', role=User.Role.OFFICER)
        self.client.force_login(officer)
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/pending.html')
        self.assertNotContains(response, 'Lahan saya')

    def test_staff_gets_admin_link_on_pending_page(self):
        admin = User.objects.create_user('admin', 'a@contoh.id', 'tanah12345', role=User.Role.OFFICER, is_staff=True)
        self.client.force_login(admin)
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, reverse('admin:index'))


class DashboardContentTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('sari', 'sari@contoh.id', 'tanah12345', first_name='Sari Rahayu')
        self.client.force_login(self.owner)
        self.response = self.client.get(reverse('dashboard:home'))

    def test_shows_main_sections(self):
        for text in ['Lahan saya', 'Rekomendasi terbaik', 'Pesanan aktif', 'Catatan dari Wiji', 'Kebun Lereng Cibodas']:
            self.assertContains(self.response, text)

    def test_order_stepper_has_six_statuses_with_one_current(self):
        self.assertContains(self.response, 'class="now"', count=1)
        self.assertContains(self.response, 'class="done"', count=2)

    def test_chart_data_is_embedded_as_json(self):
        self.assertContains(self.response, 'id="chart-data"')
        self.assertEqual(self.response.context['chart']['values'], [46, 44, 49, 43, 45, 40, 42])

    def test_sidebar_has_active_item_and_logout_form(self):
        self.assertContains(self.response, 'side-link is-active')
        self.assertContains(self.response, reverse('accounts:logout'))
        self.assertContains(self.response, 'SR')  # inisial di avatar

    def test_dashboard_loads_its_script(self):
        self.assertContains(self.response, 'js/dashboard.js')
