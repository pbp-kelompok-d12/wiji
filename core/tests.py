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

    def test_catalog_preview_lists_plants(self):
        response = self.client.get(reverse('core:landing'))
        self.assertContains(response, 'Akar wangi')
        self.assertContains(response, 'Chrysopogon zizanioides')
