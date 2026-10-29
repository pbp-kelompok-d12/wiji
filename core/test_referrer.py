from django.test import TestCase
from django.urls import reverse


class ReferrerPolicyTests(TestCase):
    """Peta lahan memuat gambar dari OpenStreetMap, yang menolak permintaan tanpa Referer."""

    def test_halaman_mengirim_referrer_policy_yang_cukup_buat_peta(self):
        response = self.client.get(reverse('core:landing'))
        self.assertEqual(response['Referrer-Policy'], 'strict-origin-when-cross-origin')

    def test_alamat_halaman_lengkap_nggak_bocor_ke_situs_lain(self):
        # Bukan 'unsafe-url' dan bukan 'origin-when-cross-origin' tanpa strict
        self.assertNotIn(self.client.get(reverse('core:landing'))['Referrer-Policy'], ('unsafe-url', 'no-referrer'))
