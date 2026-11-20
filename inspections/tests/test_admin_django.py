from django.contrib import admin
from django.test import TestCase

from ..models import PesananPemeriksaan
from .helpers import buat_lahan, buat_pemilik, buat_pesanan


class PesananAdminDjangoTests(TestCase):
    def test_kolom_alur_cuma_bisa_dibaca(self):
        pesanan = buat_pesanan(buat_lahan(buat_pemilik()))
        model_admin = admin.site._registry[PesananPemeriksaan]
        readonly = model_admin.get_readonly_fields(None, pesanan)
        for kolom in ('status', 'petugas', 'tanggal_final', 'sesi_final'):
            self.assertIn(kolom, readonly)
