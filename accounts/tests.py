from django.test import TestCase
from django.urls import reverse

from .models import User

VALID_FORM = {
    'first_name': 'Sari Rahayu',
    'username': 'sari.rahayu',
    'email': 'sari@contoh.id',
    'password1': 'tanah12345',
    'password2': 'tanah12345',
}


class RegisterTests(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)

    def test_register_creates_owner_and_logs_in(self):
        response = self.client.post(reverse('accounts:register'), VALID_FORM)
        self.assertRedirects(response, reverse('core:landing'))
        user = User.objects.get(username='sari.rahayu')
        self.assertEqual(user.role, User.Role.OWNER)
        self.assertFalse(user.is_staff)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_register_cannot_choose_role(self):
        self.client.post(reverse('accounts:register'), {**VALID_FORM, 'role': 'officer', 'is_staff': 'on'})
        user = User.objects.get(username='sari.rahayu')
        self.assertEqual(user.role, User.Role.OWNER)
        self.assertFalse(user.is_staff)

    def test_password_mismatch(self):
        response = self.client.post(reverse('accounts:register'), {**VALID_FORM, 'password2': 'beda12345'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kata sandi tidak sama.')
        self.assertFalse(User.objects.exists())

    def test_password_needs_letters_and_digits(self):
        response = self.client.post(
            reverse('accounts:register'), {**VALID_FORM, 'password1': 'hurufsajalah', 'password2': 'hurufsajalah'}
        )
        self.assertContains(response, 'huruf dan angka')
        self.assertFalse(User.objects.exists())

    def test_password_too_short(self):
        response = self.client.post(
            reverse('accounts:register'), {**VALID_FORM, 'password1': 'a1b2', 'password2': 'a1b2'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_duplicate_username_and_email(self):
        User.objects.create_user('sari.rahayu', 'sari@contoh.id', 'tanah12345')
        response = self.client.post(reverse('accounts:register'), VALID_FORM)
        self.assertContains(response, 'Nama pengguna ini sudah dipakai.')
        self.assertContains(response, 'Email ini sudah terdaftar.')
        self.assertEqual(User.objects.count(), 1)

    def test_logged_in_user_is_redirected_from_register(self):
        user = User.objects.create_user('sari', 'sari@contoh.id', 'tanah12345')
        self.client.force_login(user)
        response = self.client.get(reverse('accounts:register'))
        self.assertRedirects(response, reverse('core:landing'))


class UsernameCheckTests(TestCase):
    def test_available_taken_and_empty(self):
        User.objects.create_user('sari', 'sari@contoh.id', 'tanah12345')
        url = reverse('accounts:check_username')
        self.assertContains(self.client.get(url, {'username': 'baru'}), 'tersedia')
        self.assertContains(self.client.get(url, {'username': 'SARI'}), 'sudah dipakai')
        self.assertNotContains(self.client.get(url, {'username': ''}), 'field-')


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('sari', 'sari@contoh.id', 'tanah12345')

    def test_login_page_loads(self):
        self.assertEqual(self.client.get(reverse('accounts:login')).status_code, 200)

    def test_login_success_goes_to_landing(self):
        response = self.client.post(reverse('accounts:login'), {'username': 'sari', 'password': 'tanah12345'})
        self.assertRedirects(response, reverse('core:landing'))

    def test_login_wrong_password_shows_error(self):
        response = self.client.post(reverse('accounts:login'), {'username': 'sari', 'password': 'salah'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nama pengguna atau kata sandi salah.')

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_logout_post_logs_out(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('core:landing'))
        self.assertNotIn('_auth_user_id', self.client.session)


class UserModelTests(TestCase):
    def test_display_name_falls_back_to_username(self):
        self.assertEqual(User(username='sari').display_name, 'sari')
        self.assertEqual(User(username='sari', first_name='Sari Rahayu').display_name, 'Sari Rahayu')

    def test_role_helpers(self):
        self.assertTrue(User(role=User.Role.OWNER).is_owner)
        self.assertTrue(User(role=User.Role.OFFICER).is_officer)
