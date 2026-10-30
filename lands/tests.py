import json
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .environment import fetch_environmental_data
from .forms import LandForm, LahanForm
from .nasa_power import fetch_climate_data

from .models import Land, Lahan, ManagementGoal


class LandModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username='owner',
            password='rahasia123',
            role='owner',
        )

    def buat_lahan(self, **kwargs):
        data = {
            'owner': self.owner,
            'nama': 'Kebun Uji',
            'alamat': 'Dramaga, Bogor',
            'luas_m2': Decimal('120.50'),
            'penggunaan': Land.Penggunaan.KEBUN,
        }
        data.update(kwargs)
        return Land(**data)

    def test_lahan_lengkap_tanpa_koordinat_masih_draf(self):
        lahan = self.buat_lahan()
        self.assertTrue(lahan.adalah_draf)
        self.assertFalse(lahan.punya_koordinat)

    def test_lahan_draf_saat_field_wajib_kosong(self):
        lahan = self.buat_lahan(luas_m2=None)
        self.assertTrue(lahan.adalah_draf)

    def test_lahan_lengkap_saat_koordinat_terisi(self):
        lahan = self.buat_lahan(
            latitude=Decimal('-6.550000'),
            longitude=Decimal('106.750000'),
        )
        self.assertFalse(lahan.adalah_draf)
        self.assertTrue(lahan.punya_koordinat)

    def test_koordinat_harus_berpasangan(self):
        lahan = self.buat_lahan(latitude=Decimal('-6.55'))
        with self.assertRaises(ValidationError):
            lahan.full_clean()

    def test_luas_harus_positif(self):
        lahan = self.buat_lahan(luas_m2=Decimal('0'))
        with self.assertRaises(ValidationError):
            lahan.full_clean()

    def test_lahan_baru_bisa_dihapus(self):
        lahan = self.buat_lahan()
        self.assertTrue(lahan.dapat_dihapus)


class LandFormTests(TestCase):
    def test_hanya_tujuan_aktif_yang_tampil(self):
        aktif = ManagementGoal.objects.create(nama='Aktif', slug='aktif', aktif=True)
        ManagementGoal.objects.create(nama='Nonaktif', slug='nonaktif', aktif=False)

        form = LandForm()

        self.assertIn(aktif, form.fields['tujuan'].queryset)
        self.assertNotIn(
            ManagementGoal.objects.get(slug='nonaktif'),
            form.fields['tujuan'].queryset,
        )


class LandViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username='owner',
            password='rahasia123',
            role='owner',
        )
        cls.other_owner = User.objects.create_user(
            username='other',
            password='rahasia123',
            role='owner',
        )
        cls.officer = User.objects.create_user(
            username='officer',
            password='rahasia123',
            role='officer',
        )
        cls.goal = ManagementGoal.objects.create(
            nama='Pemulihan tanah',
            slug='pemulihan-tanah',
        )
        cls.lahan = Land.objects.create(
            owner=cls.owner,
            nama='Kebun Cibodas',
            alamat='Cibodas, Bogor',
            latitude=Decimal('-6.550000'),
            longitude=Decimal('106.750000'),
            luas_m2=Decimal('250.00'),
            penggunaan=Land.Penggunaan.KEBUN,
        )
        cls.lahan.tujuan.add(cls.goal)
        cls.lahan_lain = Land.objects.create(
            owner=cls.other_owner,
            nama='Sawah Lain',
            alamat='Ciampea, Bogor',
            luas_m2=Decimal('800.00'),
            penggunaan=Land.Penggunaan.SAWAH,
        )

    def setUp(self):
        environment_patcher = patch('lands.views.fetch_environmental_data')
        self.environment_mock = environment_patcher.start()
        self.environment_mock.return_value = {
            'status': 'unavailable',
            'source': 'Open-Meteo',
            'reason': 'coordinates_missing',
            'message': 'Koordinat lahan belum tersedia.',
            'timezone': None,
            'current': {},
            'units': {},
            'weather_description': None,
        }
        self.addCleanup(environment_patcher.stop)

        climate_patcher = patch('lands.views.fetch_climate_data')
        self.climate_mock = climate_patcher.start()
        self.climate_mock.return_value = {
            'status': 'unavailable',
            'source': 'NASA POWER',
            'reason': 'coordinates_missing',
            'message': 'Koordinat lahan belum tersedia.',
            'rainfall_30d': None,
            'rainfall_annual': None,
            'units': {
                'rainfall_30d': 'mm',
                'rainfall_annual': 'mm',
            },
            'period': None,
            'latest_data_date': None,
        }
        self.addCleanup(climate_patcher.stop)

    def test_halaman_lahan_wajib_login(self):
        response = self.client.get(reverse('lands:daftar_lahan'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_hanya_pemilik_yang_boleh_masuk(self):
        self.client.force_login(self.officer)
        response = self.client.get(reverse('lands:daftar_lahan'))
        self.assertEqual(response.status_code, 403)

    def test_daftar_hanya_menampilkan_lahan_milik_sendiri(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('lands:daftar_lahan'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kebun Cibodas')
        self.assertContains(response, '-6.550000')
        self.assertNotContains(response, 'Sawah Lain')

    def test_daftar_semua_status_dan_filter_masing_masing(self):
        draft = Land.objects.create(
            owner=self.owner,
            nama='Draft Sawah',
        )
        archived = Land.objects.create(
            owner=self.owner,
            nama='Arsip Kebun',
            alamat='Bogor',
            luas_m2=Decimal('100.00'),
            penggunaan=Land.Penggunaan.KEBUN,
        )
        archived.arsipkan()
        self.client.force_login(self.owner)

        semua = self.client.get(reverse('lands:daftar_lahan'))
        aktif = self.client.get(reverse('lands:daftar_lahan'), {'status': 'active'})
        draf = self.client.get(reverse('lands:daftar_lahan'), {'status': 'draft'})
        arsip = self.client.get(reverse('lands:daftar_lahan'), {'status': 'archived'})

        self.assertContains(semua, 'Kebun Cibodas')
        self.assertContains(semua, 'Draft Sawah')
        self.assertContains(semua, 'Arsip Kebun')
        self.assertContains(aktif, 'Kebun Cibodas')
        self.assertNotContains(aktif, 'Draft Sawah')
        self.assertNotContains(aktif, 'Arsip Kebun')
        self.assertContains(draf, 'Draft Sawah')
        self.assertNotContains(draf, 'Kebun Cibodas')
        self.assertContains(arsip, 'Arsip Kebun')
        self.assertNotContains(arsip, 'Kebun Cibodas')
        self.assertContains(draf, 'Lengkapi data lahan')
        self.assertContains(draf, reverse('lands:hapus_lahan', args=[draft.pk]))
        self.assertContains(aktif, reverse('lands:ubah_lahan', args=[self.lahan.pk]))
        self.assertContains(aktif, reverse('lands:arsip_lahan', args=[self.lahan.pk]))
        self.assertContains(arsip, 'Pulihkan')
        self.assertTrue(draft.adalah_draf)

    def test_pencarian_lahan(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('lands:daftar_lahan'), {'q': 'Cibodas'})

        self.assertContains(response, 'Kebun Cibodas')
        self.assertEqual(response.context['q'], 'Cibodas')

    def test_htmx_mengembalikan_partial(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse('lands:daftar_lahan'),
            HTTP_HX_REQUEST='true',
        )

        self.assertContains(response, 'Kebun Cibodas')
        self.assertNotContains(response, '<!DOCTYPE html>')

    def test_detail_lahan_sendiri_menampilkan_peta(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse('lands:detail_lahan', args=[self.lahan.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-lat="-6.550000"')
        self.assertContains(response, 'relative z-0 isolate h-[246px]')
        self.assertContains(response, 'Kebun Cibodas')
        self.assertEqual(response.context['hasil_final'], [])
        self.assertFalse(response.context['punya_pesanan_aktif'])

    def test_detail_lahan_menampilkan_data_cuaca_terkini(self):
        self.environment_mock.return_value = {
            'status': 'available',
            'source': 'Open-Meteo',
            'reason': None,
            'message': 'Data cuaca berhasil diambil.',
            'timezone': 'Asia/Jakarta',
            'current': {
                'time': '2026-10-30T10:00',
                'temperature_2m': 27.5,
                'relative_humidity_2m': 80,
                'precipitation': 0.0,
                'weather_code': 2,
                'wind_speed_10m': 5.2,
            },
            'units': {
                'temperature_2m': '°C',
                'relative_humidity_2m': '%',
                'precipitation': 'mm',
                'weather_code': 'wmo code',
                'wind_speed_10m': 'km/h',
            },
            'weather_description': 'Berawan',
        }
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('lands:detail_lahan', args=[self.lahan.pk])
        )

        self.assertContains(response, '27,5')
        self.assertContains(response, 'Berawan')
        self.assertContains(response, 'Data lingkungan · Open-Meteo')
        self.environment_mock.assert_called_once_with(self.lahan)

    def test_detail_lahan_menampilkan_pesan_saat_cuaca_tidak_tersedia(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('lands:detail_lahan', args=[self.lahan.pk])
        )

        self.assertContains(response, 'Koordinat lahan belum tersedia.')
        self.assertNotContains(response, 'Hujan 30 hr')

    def test_detail_lahan_menampilkan_iklim_nasa_power(self):
        self.climate_mock.return_value = {
            'status': 'available',
            'source': 'NASA POWER',
            'reason': None,
            'message': 'Data iklim berhasil diambil.',
            'rainfall_30d': 123.4,
            'rainfall_annual': 2500.6,
            'units': {
                'rainfall_30d': 'mm',
                'rainfall_annual': 'mm',
            },
            'period': {
                'start': '2025-10-22',
                'end': '2026-10-21',
            },
            'latest_data_date': '2026-10-21',
        }
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('lands:detail_lahan', args=[self.lahan.pk])
        )

        self.assertContains(response, '123,4')
        self.assertContains(response, 'Iklim historis · NASA POWER')
        self.assertContains(response, 'Hujan 30 hari')
        self.assertContains(response, '2025-10-22')
        self.assertContains(response, '2026-10-21')
        self.climate_mock.assert_called_once_with(self.lahan)

    def test_form_ubah_memakai_titik_desimal(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse('lands:ubah_lahan', args=[self.lahan.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lengkapi')
        self.assertNotContains(response, 'Simpan sebagai draft')
        self.assertContains(response, 'value="-6.550000"')
        self.assertContains(response, 'value="106.750000"')

    def test_detail_lahan_lain_404(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse('lands:detail_lahan', args=[self.lahan_lain.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_pesan_pemeriksaan_menampilkan_alasan_saat_lahan_tidak_tersedia(self):
        self.client.force_login(self.owner)
        self.lahan.arsipkan()

        response = self.client.get(
            reverse('lands:detail_lahan', args=[self.lahan.pk])
        )

        self.assertContains(
            response,
            'Pulihkan lahan terlebih dahulu untuk memesan pemeriksaan.',
        )
        self.assertNotContains(response, '<button type="button" class="btn btn-ghost')

    def test_pesan_pemeriksaan_menjelaskan_pesanan_aktif(self):
        self.client.force_login(self.owner)
        with patch.object(Land, 'punya_pesanan_aktif', return_value=True):
            response = self.client.get(
                reverse('lands:detail_lahan', args=[self.lahan.pk])
            )

        self.assertContains(
            response,
            'Lahan ini masih memiliki pesanan yang berjalan.',
        )

    def test_tambah_lahan_menetapkan_owner(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('lands:tambah_lahan'), {
            'nama': 'Sawah Baru',
            'alamat': 'Dramaga, Bogor',
            'latitude': '-6.550000',
            'longitude': '106.750000',
            'luas_m2': '500.00',
            'penggunaan': Land.Penggunaan.SAWAH,
            'kondisi': 'Tanah masih gembur.',
            'tujuan': [self.goal.pk],
        })

        lahan = Land.objects.get(nama='Sawah Baru')
        self.assertRedirects(
            response,
            reverse('lands:detail_lahan', args=[lahan.pk]),
        )
        self.assertEqual(lahan.owner, self.owner)
        self.assertFalse(lahan.adalah_draf)
        self.assertIn(self.goal, lahan.tujuan.all())

    def test_tambah_lahan_tidak_lengkap_disimpan_sebagai_draf(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('lands:tambah_lahan'), {
            'nama': 'Draft Kebun',
            'alamat': '',
            'latitude': '',
            'longitude': '',
            'luas_m2': '',
            'penggunaan': '',
        })

        lahan = Land.objects.get(nama='Draft Kebun')
        self.assertRedirects(
            response,
            f"{reverse('lands:daftar_lahan')}?status=draft",
        )
        self.assertEqual(lahan.owner, self.owner)
        self.assertTrue(lahan.adalah_draf)

    def test_lahan_tanpa_koordinat_disimpan_sebagai_draf(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('lands:tambah_lahan'), {
            'nama': 'Kebun Belakang',
            'alamat': 'Cibinong, Bogor',
            'latitude': '',
            'longitude': '',
            'luas_m2': '210.00',
            'penggunaan': Land.Penggunaan.KEBUN,
        })

        lahan = Land.objects.get(nama='Kebun Belakang')
        self.assertRedirects(
            response,
            f"{reverse('lands:daftar_lahan')}?status=draft",
        )
        self.assertTrue(lahan.adalah_draf)

    def test_draft_bisa_dilengkapi_menjadi_lahan_aktif(self):
        draft = Land.objects.create(owner=self.owner, nama='Draft Kebun')
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('lands:ubah_lahan', args=[draft.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Draft Kebun"')
        self.assertContains(response, 'Simpan sebagai draft')

        response = self.client.post(
            reverse('lands:ubah_lahan', args=[draft.pk]),
            {
                'nama': 'Kebun Selesai',
                'alamat': 'Dramaga, Bogor',
                'latitude': '-6.550000',
                'longitude': '106.750000',
                'luas_m2': '100.00',
                'penggunaan': Land.Penggunaan.KEBUN,
                'kondisi': '',
                'tujuan': [],
            },
        )

        self.assertRedirects(
            response,
            reverse('lands:detail_lahan', args=[draft.pk]),
        )
        draft.refresh_from_db()
        self.assertFalse(draft.adalah_draf)
        self.assertEqual(draft.nama, 'Kebun Selesai')

    def test_tambah_lahan_tidak_valid_tetap_di_form(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('lands:tambah_lahan'), {
            'nama': 'Land Rusak',
            'alamat': '',
            'latitude': '-6.55',
            'longitude': '',
            'luas_m2': '-1',
            'penggunaan': Land.Penggunaan.KEBUN,
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Land.objects.filter(nama='Land Rusak').exists())
        self.assertTrue(response.context['form'].errors)

    def test_ubah_lahan(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('lands:ubah_lahan', args=[self.lahan.pk]),
            {
                'nama': 'Kebun Cibodas Baru',
                'alamat': self.lahan.alamat,
                'latitude': '-6.550000',
                'longitude': '106.750000',
                'luas_m2': '300.00',
                'penggunaan': Land.Penggunaan.KEBUN,
                'kondisi': 'Subur.',
                'tujuan': [self.goal.pk],
            },
        )

        self.assertRedirects(
            response,
            reverse('lands:detail_lahan', args=[self.lahan.pk]),
        )
        self.lahan.refresh_from_db()
        self.assertEqual(self.lahan.nama, 'Kebun Cibodas Baru')
        self.assertEqual(self.lahan.luas_m2, Decimal('300.00'))

    def test_arsip_dan_pulihkan_lahan(self):
        self.client.force_login(self.owner)
        confirmation = self.client.get(
            reverse('lands:arsip_lahan', args=[self.lahan.pk])
        )
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, 'role="alertdialog"')
        self.assertContains(confirmation, 'Arsipkan Kebun Cibodas?')
        self.assertContains(confirmation, 'Ya, arsipkan')

        response = self.client.post(
            reverse('lands:arsip_lahan', args=[self.lahan.pk])
        )
        self.assertRedirects(response, reverse('lands:daftar_lahan'))

        self.lahan.refresh_from_db()
        self.assertTrue(self.lahan.diarsipkan)
        self.assertIsNotNone(self.lahan.diarsipkan_pada)

        response = self.client.post(
            reverse('lands:pulihkan_lahan', args=[self.lahan.pk])
        )
        self.assertRedirects(
            response,
            reverse('lands:detail_lahan', args=[self.lahan.pk]),
        )

        self.lahan.refresh_from_db()
        self.assertFalse(self.lahan.diarsipkan)
        self.assertIsNone(self.lahan.diarsipkan_pada)

    def test_endpoint_arsip_membatasi_metode_dan_pemilik(self):
        url = reverse('lands:arsip_lahan', args=[self.lahan.pk])
        self.client.force_login(self.owner)
        self.assertEqual(self.client.put(url).status_code, 405)

        self.client.force_login(self.officer)
        self.assertEqual(self.client.post(url).status_code, 403)

        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.post(
                reverse('lands:arsip_lahan', args=[self.lahan_lain.pk])
            ).status_code,
            404,
        )

    def test_endpoint_pulihkan_hanya_menerima_post(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse('lands:pulihkan_lahan', args=[self.lahan.pk])
        )

        self.assertEqual(response.status_code, 405)

    def test_arsip_ditolak_saat_ada_pesanan_aktif(self):
        self.client.force_login(self.owner)
        with patch.object(Land, 'punya_pesanan_aktif', return_value=True):
            confirmation = self.client.get(
                reverse('lands:arsip_lahan', args=[self.lahan.pk])
            )
            self.assertEqual(confirmation.status_code, 200)
            self.assertContains(confirmation, 'role="alertdialog"')
            self.assertContains(confirmation, 'Belum bisa mengarsipkan')
            self.assertContains(confirmation, 'Mengerti')

            response = self.client.post(
                reverse('lands:arsip_lahan', args=[self.lahan.pk])
            )

        self.assertRedirects(
            response,
            reverse('lands:detail_lahan', args=[self.lahan.pk]),
        )
        self.lahan.refresh_from_db()
        self.assertFalse(self.lahan.diarsipkan)

    def test_hapus_lahan(self):
        lahan = Land.objects.create(
            owner=self.owner,
            nama='Draft Sementara',
        )
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse('lands:hapus_lahan', args=[lahan.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'role="alertdialog"')
        self.assertContains(response, 'Hapus Draft Sementara?')
        self.assertContains(response, 'Ya, hapus')

        response = self.client.post(
            reverse('lands:hapus_lahan', args=[lahan.pk])
        )
        self.assertRedirects(response, reverse('lands:daftar_lahan'))
        self.assertFalse(Land.objects.filter(pk=lahan.pk).exists())

    def test_hapus_permanen_lahan_aktif_ditolak(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('lands:hapus_lahan', args=[self.lahan.pk])
        )

        self.assertRedirects(
            response,
            reverse('lands:detail_lahan', args=[self.lahan.pk]),
        )
        self.assertTrue(Land.objects.filter(pk=self.lahan.pk).exists())

    def test_api_lahan_hanya_milik_sendiri(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('lands:api_lahan'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], str(self.lahan.pk))
        self.assertEqual(data[0]['nama'], 'Kebun Cibodas')
        self.assertTrue(data[0]['punya_koordinat'])
        self.assertEqual(data[0]['tujuan'], ['Pemulihan tanah'])

    def test_api_detail_lahan_lain_404(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse('lands:api_detail_lahan', args=[self.lahan_lain.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_api_lahan_menyertakan_arsip_saat_diminta(self):
        self.lahan.diarsipkan = True
        self.lahan.save(update_fields=['diarsipkan'])
        self.client.force_login(self.owner)

        aktif = self.client.get(reverse('lands:api_lahan')).json()
        arsip = self.client.get(reverse('lands:api_lahan'), {'arsip': '1'}).json()

        self.assertEqual(aktif, [])
        self.assertEqual(len(arsip), 1)
        self.assertTrue(arsip[0]['diarsipkan'])

    def test_api_lahan_draft_mendukung_field_wajib_kosong(self):
        draft = Land.objects.create(
            owner=self.owner,
            nama='Draft API',
        )
        self.client.force_login(self.owner)

        response = self.client.get(reverse('lands:api_lahan'))
        data = next(item for item in response.json() if item['id'] == str(draft.pk))

        self.assertEqual(data['status'], 'draft')
        self.assertIsNone(data['luas_m2'])
        self.assertIsNone(data['penggunaan'])

    def test_api_wajib_login(self):
        response = self.client.get(reverse('lands:api_lahan'))
        self.assertEqual(response.status_code, 302)


class NominatimViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username='owner',
            password='rahasia123',
            role='owner',
        )

    def setUp(self):
        self.client.force_login(self.owner)

    def test_kata_kunci_terlalu_pendek(self):
        response = self.client.get(reverse('lands:cari_lokasi'), {'q': 'bo'})
        self.assertEqual(response.status_code, 400)

    @patch('lands.views.nominatim')
    def test_cari_lokasi_sukses(self, nominatim_mock):
        nominatim_mock.return_value = [
            {
                'display_name': 'Dramaga, Bogor, Jawa Barat',
                'lat': '-6.550000',
                'lon': '106.750000',
                'type': 'village',
            }
        ]

        response = self.client.get(reverse('lands:cari_lokasi'), {'q': 'Dramaga'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['display_name'], 'Dramaga, Bogor, Jawa Barat')
        nominatim_mock.assert_called_once()
        self.assertEqual(nominatim_mock.call_args.args[0], 'search')
        self.assertEqual(nominatim_mock.call_args.args[1]['countrycodes'], 'id')

    @patch('lands.views.nominatim', side_effect=URLError('offline'))
    def test_cari_lokasi_gagal(self, nominatim_mock):
        response = self.client.get(reverse('lands:cari_lokasi'), {'q': 'Dramaga'})
        self.assertEqual(response.status_code, 502)

    @patch('lands.views.nominatim')
    def test_reverse_lokasi_sukses(self, nominatim_mock):
        nominatim_mock.return_value = {
            'display_name': 'Dramaga, Bogor',
            'lat': '-6.55',
            'lon': '106.75',
        }

        response = self.client.get(
            reverse('lands:reverse_lokasi'),
            {'lat': '-6.55', 'lon': '106.75'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['display_name'], 'Dramaga, Bogor')

    def test_reverse_lokasi_tidak_valid(self):
        response = self.client.get(
            reverse('lands:reverse_lokasi'),
            {'lat': 'abc', 'lon': '106.75'},
        )
        self.assertEqual(response.status_code, 400)

    def test_reverse_lokasi_di_luar_jangkauan(self):
        response = self.client.get(
            reverse('lands:reverse_lokasi'),
            {'lat': '91', 'lon': '106.75'},
        )
        self.assertEqual(response.status_code, 400)


class OpenMeteoEnvironmentTests(TestCase):
    def setUp(self):
        cache.clear()
        self.lahan = SimpleNamespace(
            latitude=Decimal('-6.200000'),
            longitude=Decimal('106.800000'),
        )

    def api_payload(self):
        return {
            'timezone': 'Asia/Jakarta',
            'current': {
                'time': '2026-10-30T10:00',
                'temperature_2m': 30.1,
                'relative_humidity_2m': 78,
                'precipitation': 0.0,
                'weather_code': 2,
                'wind_speed_10m': 5.2,
            },
            'current_units': {
                'temperature_2m': '°C',
                'relative_humidity_2m': '%',
                'precipitation': 'mm',
                'weather_code': 'wmo code',
                'wind_speed_10m': 'km/h',
            },
        }

    @patch('lands.environment.urlopen')
    def test_respons_sukses_mengembalikan_cuaca(self, mock_urlopen):
        mock_urlopen.return_value = BytesIO(
            json.dumps(self.api_payload()).encode('utf-8')
        )

        result = fetch_environmental_data(self.lahan)

        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['source'], 'Open-Meteo')
        self.assertEqual(result['current']['temperature_2m'], 30.1)
        self.assertEqual(result['current']['relative_humidity_2m'], 78)
        self.assertEqual(result['weather_description'], 'Berawan')
        self.assertEqual(result['timezone'], 'Asia/Jakarta')

    @patch('lands.environment.urlopen')
    def test_permintaan_hanya_mengirim_koordinat_dan_parameter_cuaca(
        self, mock_urlopen
    ):
        mock_urlopen.return_value = BytesIO(
            json.dumps(self.api_payload()).encode('utf-8')
        )

        fetch_environmental_data(self.lahan)

        request = mock_urlopen.call_args.args[0]
        query = parse_qs(urlparse(request.full_url).query)

        self.assertEqual(
            set(query),
            {'latitude', 'longitude', 'current', 'timezone'},
        )
        self.assertEqual(query['latitude'], ['-6.2'])
        self.assertEqual(query['longitude'], ['106.8'])

    @patch('lands.environment.urlopen')
    def test_hasil_sukses_disimpan_di_cache(self, mock_urlopen):
        mock_urlopen.return_value = BytesIO(
            json.dumps(self.api_payload()).encode('utf-8')
        )

        pertama = fetch_environmental_data(self.lahan)
        kedua = fetch_environmental_data(self.lahan)

        mock_urlopen.assert_called_once()
        self.assertEqual(pertama, kedua)

    @patch('lands.environment.urlopen')
    def test_koordinat_kosong_tidak_memanggil_api(self, mock_urlopen):
        self.lahan.latitude = None

        result = fetch_environmental_data(self.lahan)

        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['reason'], 'coordinates_missing')
        self.assertEqual(result['current'], {})
        mock_urlopen.assert_not_called()

    @patch('lands.environment.urlopen')
    def test_kegagalan_api_tidak_mengarang_cuaca(self, mock_urlopen):
        mock_urlopen.side_effect = URLError('Connection failed')

        result = fetch_environmental_data(self.lahan)

        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['reason'], 'api_unavailable')
        self.assertEqual(result['current'], {})

    @patch('lands.environment.urlopen')
    def test_respons_tidak_valid_tidak_dipakai(self, mock_urlopen):
        mock_urlopen.return_value = BytesIO(
            b'{"timezone": "Asia/Jakarta", "current": {}}'
        )

        result = fetch_environmental_data(self.lahan)

        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['reason'], 'response_invalid')
        self.assertEqual(result['current'], {})

    @patch('lands.environment.urlopen')
    def test_koordinat_di_luar_jangkauan_tidak_memanggil_api(
        self, mock_urlopen
    ):
        self.lahan.latitude = Decimal('100')

        result = fetch_environmental_data(self.lahan)

        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['reason'], 'coordinates_invalid')
        mock_urlopen.assert_not_called()


class NasaPowerClimateTests(TestCase):
    def setUp(self):
        cache.clear()
        self.lahan = SimpleNamespace(
            latitude=Decimal('-6.200000'),
            longitude=Decimal('106.800000'),
        )
        self.today = date(2026, 10, 30)

    def api_payload(self, days=380, value=1.0, end=None):
        end = end or self.today
        start = end - timedelta(days=days - 1)
        series = {
            (start + timedelta(days=offset)).strftime('%Y%m%d'): value
            for offset in range(days)
        }
        return {
            'properties': {
                'parameter': {
                    'PRECTOTCORR': series,
                },
            },
        }

    @patch('lands.nasa_power.urlopen')
    def test_respons_sukses_menghitung_hujan_30_hari_dan_setahun(
        self, mock_urlopen
    ):
        mock_urlopen.return_value = BytesIO(
            json.dumps(self.api_payload()).encode('utf-8')
        )

        result = fetch_climate_data(self.lahan, today=self.today)

        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['source'], 'NASA POWER')
        self.assertEqual(result['rainfall_30d'], 30.0)
        self.assertEqual(result['rainfall_annual'], 365.0)
        self.assertEqual(result['period']['end'], '2026-10-30')
        self.assertEqual(result['latest_data_date'], '2026-10-30')

    @patch('lands.nasa_power.urlopen')
    def test_permintaan_hanya_mengirim_koordinat_dan_parameter_iklim(
        self, mock_urlopen
    ):
        mock_urlopen.return_value = BytesIO(
            json.dumps(self.api_payload()).encode('utf-8')
        )

        fetch_climate_data(self.lahan, today=self.today)

        request = mock_urlopen.call_args.args[0]
        query = parse_qs(urlparse(request.full_url).query)

        self.assertEqual(
            set(query),
            {
                'parameters',
                'community',
                'latitude',
                'longitude',
                'start',
                'end',
                'format',
            },
        )
        self.assertEqual(query['parameters'], ['PRECTOTCORR'])
        self.assertEqual(query['community'], ['AG'])
        self.assertEqual(query['latitude'], ['-6.2'])
        self.assertEqual(query['longitude'], ['106.8'])
        self.assertEqual(query['start'], ['20251016'])
        self.assertEqual(query['end'], ['20261030'])

    @patch('lands.nasa_power.urlopen')
    def test_hasil_sukses_disimpan_di_cache(self, mock_urlopen):
        mock_urlopen.return_value = BytesIO(
            json.dumps(self.api_payload()).encode('utf-8')
        )

        pertama = fetch_climate_data(self.lahan, today=self.today)
        kedua = fetch_climate_data(self.lahan, today=self.today)

        mock_urlopen.assert_called_once()
        self.assertEqual(pertama, kedua)

    @patch('lands.nasa_power.urlopen')
    def test_nilai_fill_tidak_dihitung_sebagai_hujan(self, mock_urlopen):
        payload = self.api_payload()
        series = payload['properties']['parameter']['PRECTOTCORR']
        for offset in range(0, 9):
            hari = self.today - timedelta(days=offset)
            series[hari.strftime('%Y%m%d')] = -999.0

        mock_urlopen.return_value = BytesIO(
            json.dumps(payload).encode('utf-8')
        )

        result = fetch_climate_data(self.lahan, today=self.today)

        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['latest_data_date'], '2026-10-21')
        self.assertEqual(result['rainfall_annual'], 365.0)

    @patch('lands.nasa_power.urlopen')
    def test_koordinat_kosong_tidak_memanggil_api(self, mock_urlopen):
        self.lahan.latitude = None

        result = fetch_climate_data(self.lahan, today=self.today)

        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['reason'], 'coordinates_missing')
        self.assertIsNone(result['rainfall_30d'])
        mock_urlopen.assert_not_called()

    @patch('lands.nasa_power.urlopen')
    def test_koordinat_di_luar_jangkauan_tidak_memanggil_api(
        self, mock_urlopen
    ):
        self.lahan.latitude = Decimal('100')

        result = fetch_climate_data(self.lahan, today=self.today)

        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['reason'], 'coordinates_invalid')
        mock_urlopen.assert_not_called()

    @patch('lands.nasa_power.urlopen')
    def test_kegagalan_api_tidak_mengarang_data_iklim(self, mock_urlopen):
        mock_urlopen.side_effect = URLError('Connection failed')

        result = fetch_climate_data(self.lahan, today=self.today)

        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['reason'], 'api_unavailable')
        self.assertIsNone(result['rainfall_annual'])

    @patch('lands.nasa_power.urlopen')
    def test_respons_tidak_valid_tidak_dipakai(self, mock_urlopen):
        mock_urlopen.return_value = BytesIO(b'{"properties": {}}')

        result = fetch_climate_data(self.lahan, today=self.today)

        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['reason'], 'response_invalid')

    @patch('lands.nasa_power.urlopen')
    def test_data_kurang_dari_setahun_ditolak(self, mock_urlopen):
        mock_urlopen.return_value = BytesIO(
            json.dumps(self.api_payload(days=100)).encode('utf-8')
        )

        result = fetch_climate_data(self.lahan, today=self.today)

        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['reason'], 'data_incomplete')
