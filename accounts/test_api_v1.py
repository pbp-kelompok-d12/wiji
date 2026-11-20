"""Test fondasi API DRF: permission bareng, rute /api/v1/, sama izin CORS buat Flutter web."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.authentication import SessionAuthentication
from rest_framework.test import APIRequestFactory

from accounts.permissions import API_AUTH, IsAdminWiji, IsAdminWijiOrReadOnly, IsPemilik, IsPetugas

User = get_user_model()


class PermissionBarengTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pemilik = User.objects.create_user('pemilik', password='rahasia-123')
        cls.petugas = User.objects.create_user('petugas', password='rahasia-123', role='officer')
        cls.admin = User.objects.create_user('admin', password='rahasia-123', is_staff=True)

    def boleh(self, permission, user, method='get'):
        request = getattr(APIRequestFactory(), method)('/api/v1/contoh/')
        request.user = user
        return permission().has_permission(request, None)

    def test_api_pakai_sesi_login_web(self):
        self.assertIn(SessionAuthentication, API_AUTH)

    def test_is_pemilik(self):
        self.assertTrue(self.boleh(IsPemilik, self.pemilik))
        self.assertFalse(self.boleh(IsPemilik, self.petugas))
        self.assertFalse(self.boleh(IsPemilik, AnonymousUser()))

    def test_is_petugas(self):
        self.assertTrue(self.boleh(IsPetugas, self.petugas))
        self.assertFalse(self.boleh(IsPetugas, self.pemilik))
        self.assertFalse(self.boleh(IsPetugas, AnonymousUser()))

    def test_is_admin_wiji(self):
        self.assertTrue(self.boleh(IsAdminWiji, self.admin))
        self.assertFalse(self.boleh(IsAdminWiji, self.pemilik))
        self.assertFalse(self.boleh(IsAdminWiji, self.petugas))
        self.assertFalse(self.boleh(IsAdminWiji, AnonymousUser()))

    def test_is_admin_wiji_or_read_only(self):
        self.assertTrue(self.boleh(IsAdminWijiOrReadOnly, AnonymousUser(), 'get'))
        self.assertFalse(self.boleh(IsAdminWijiOrReadOnly, AnonymousUser(), 'post'))
        self.assertFalse(self.boleh(IsAdminWijiOrReadOnly, self.pemilik, 'patch'))
        self.assertTrue(self.boleh(IsAdminWijiOrReadOnly, self.admin, 'delete'))


class RuteApiTests(TestCase):
    def test_halaman_masuk_browsable_api_kebuka(self):
        self.assertEqual(self.client.get('/api-auth/login/').status_code, 200)

    def test_rute_lama_tetap_jalan(self):
        self.assertEqual(self.client.get('/katalog/api/').status_code, 200)


class CorsTests(TestCase):
    """Flutter web jalan di localhost dengan port acak, jadi yang diizinin cuma localhost dan cuma /api/."""

    def preflight(self, path, origin):
        return self.client.options(
            path,
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
        )

    def test_flutter_web_di_localhost_diizinin(self):
        for origin in ('http://localhost:51234', 'http://127.0.0.1:8080'):
            response = self.preflight('/api/v1/tanaman/', origin)
            self.assertEqual(response.headers.get('access-control-allow-origin'), origin)

    def test_header_authorization_boleh_dikirim(self):
        response = self.client.options(
            '/api/v1/tanaman/',
            HTTP_ORIGIN='http://localhost:51234',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization, content-type',
        )
        self.assertIn('authorization', response.headers.get('access-control-allow-headers', ''))

    def test_situs_lain_nggak_diizinin(self):
        response = self.preflight('/api/v1/tanaman/', 'https://situs-lain.example')
        self.assertNotIn('access-control-allow-origin', response.headers)

    def test_halaman_web_biasa_nggak_kena_cors(self):
        response = self.preflight('/lahan/', 'http://localhost:51234')
        self.assertNotIn('access-control-allow-origin', response.headers)
