import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import User
from .models import Lahan


def png_kecil():
    buf = BytesIO()
    Image.new('RGB', (4, 4), (60, 120, 70)).save(buf, 'PNG')
    return buf.getvalue()


class FotoLahanTests(TestCase):
    """Foto lahan bisa diunggah dan tetap tampil saat DEBUG mati (seperti di PWS)."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.pengaturan = override_settings(MEDIA_ROOT=self.folder)
        self.pengaturan.enable()
        self.owner = User.objects.create_user('pemilik.foto', password='foto-12345')
        self.client.force_login(self.owner)

    def tearDown(self):
        self.pengaturan.disable()
        shutil.rmtree(self.folder, ignore_errors=True)

    def _unggah(self, berkas):
        return self.client.post(reverse('lands:tambah_lahan'), {
            'nama': 'Lahan Foto', 'alamat': 'Bogor', 'latitude': '-6.55', 'longitude': '106.75',
            'luas_m2': '300', 'penggunaan': Lahan.Penggunaan.SAWAH, 'kondisi': 'Gembur.', 'foto': berkas,
        })

    def test_foto_lahan_bisa_diunggah_dan_disimpan(self):
        self._unggah(SimpleUploadedFile('sawah.png', png_kecil(), content_type='image/png'))
        lahan = Lahan.objects.get(nama='Lahan Foto')
        self.assertTrue(lahan.foto)
        self.assertTrue(lahan.foto.name.startswith('lahan/'))

    def test_foto_tampil_lewat_media_walau_debug_mati(self):
        self._unggah(SimpleUploadedFile('sawah.png', png_kecil(), content_type='image/png'))
        lahan = Lahan.objects.get(nama='Lahan Foto')
        with override_settings(DEBUG=False):
            r = self.client.get(lahan.foto.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), png_kecil())

    def test_berkas_bukan_gambar_ditolak(self):
        self._unggah(SimpleUploadedFile('virus.txt', b'bukan gambar', content_type='text/plain'))
        self.assertFalse(Lahan.objects.filter(nama='Lahan Foto', foto__gt='').exists())

    def test_foto_lebih_dari_5mb_ditolak(self):
        besar = SimpleUploadedFile('besar.png', png_kecil() + b'0' * (5 * 1024 * 1024 + 1), content_type='image/png')
        self._unggah(besar)
        self.assertFalse(Lahan.objects.filter(nama='Lahan Foto', foto__gt='').exists())

    def test_dokumen_privat_tidak_punya_alamat_media(self):
        r = self.client.get('/media/hasil_pemeriksaan/2026/10/apa-saja.pdf')
        self.assertEqual(r.status_code, 404)
