from django.test import TestCase
from django.urls import reverse

from accounts.models import User


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
