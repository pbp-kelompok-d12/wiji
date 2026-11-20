from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from core.models import ContaminantType
from inspections.models import JenisPemeriksaan, PesananPemeriksaan
from lands.models import Lahan
from .models import (
    ContaminantFinding,
    HasilPemeriksaan,
    NutrientMeasurement,
)


class HasilAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.pemilik = User.objects.create_user(
            username="pemilik_api", role="owner",
        )
        cls.orang_lain = User.objects.create_user(
            username="lain_api", role="owner",
        )
        cls.petugas = User.objects.create_user(
            username="petugas_api", role="officer",
        )
        cls.petugas_lain = User.objects.create_user(
            username="petugas_lain_api", role="officer",
        )
        cls.admin = User.objects.create_user(
            username="admin_api", is_staff=True,
        )

        cls.lahan = Lahan.objects.create(
            owner=cls.pemilik, nama="Kebun API",
        )
        cls.lahan_lain = Lahan.objects.create(
            owner=cls.orang_lain, nama="Kebun orang lain",
        )

        cls.mandiri = HasilPemeriksaan.objects.create(
            lahan=cls.lahan,
            dibuat_oleh=cls.pemilik,
            tanggal_pemeriksaan=date(2026, 1, 1),
            asal="mandiri",
            status_hasil="final",
            ph="6.50",
        )
        cls.hasil_lain = HasilPemeriksaan.objects.create(
            lahan=cls.lahan_lain,
            tanggal_pemeriksaan=date(2026, 1, 1),
            asal="mandiri",
            status_hasil="final",
        )

        jenis = JenisPemeriksaan.objects.create(
            nama="Dasar API", slug="dasar-api", tingkat=1,
        )
        pesanan = PesananPemeriksaan.objects.create(
            lahan=cls.lahan,
            jenis=jenis,
            petugas=cls.petugas,
            status="diproses",
            tanggal_usulan=date(2026, 1, 1),
            sesi_usulan="pagi",
        )
        cls.draf = HasilPemeriksaan.objects.create(
            lahan=cls.lahan,
            dibuat_oleh=cls.petugas,
            pesanan=pesanan,
            tanggal_pemeriksaan=date(2026, 1, 2),
            asal="wiji",
            status_hasil="draf",
        )

        NutrientMeasurement.objects.create(
            hasil=cls.mandiri,
            nama_unsur="Nitrogen",
            nilai="1.25",
            satuan="%",
        )
        kontaminan = ContaminantType.objects.create(nama="Timbal API")
        ContaminantFinding.objects.create(
            hasil=cls.mandiri,
            kontaminan=kontaminan,
            status="tidak_terdeteksi",
            satuan="mg/kg",
            batas_deteksi="0.01",
        )

    def setUp(self):
        self.url_daftar = reverse("soil_results_api:daftar_hasil")

    def url_detail(self, hasil):
        return reverse(
            "soil_results_api:detail_hasil",
            args=[hasil.pk],
        )

    def test_tanpa_login_ditolak(self):
        # SessionAuthentication saat ini mengembalikan 403.
        for url in [self.url_daftar, self.url_detail(self.mandiri)]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_pemilik_hanya_melihat_hasil_final_miliknya(self):
        self.client.force_login(self.pemilik)

        response = self.client.get(self.url_daftar)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()],
            [self.mandiri.pk],
        )

    def test_detail_orang_lain_dan_draf_ditolak(self):
        self.client.force_login(self.pemilik)

        for hasil in [self.hasil_lain, self.draf]:
            with self.subTest(hasil=hasil.pk):
                response = self.client.get(self.url_detail(hasil))
                self.assertEqual(response.status_code, 404)

    def test_petugas_bisa_melihat_draf_tugasnya(self):
        self.client.force_login(self.petugas)

        response = self.client.get(self.url_daftar)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()],
            [self.draf.pk],
        )

        response = self.client.get(self.url_detail(self.draf))
        self.assertEqual(response.status_code, 200)

    def test_petugas_lain_tidak_bisa_melihat_draf(self):
        self.client.force_login(self.petugas_lain)

        response = self.client.get(self.url_daftar)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        response = self.client.get(self.url_detail(self.draf))
        self.assertEqual(response.status_code, 404)

    def test_admin_bisa_melihat_semua_hasil(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.url_daftar)
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            [item["id"] for item in response.json()],
            [self.mandiri.pk, self.hasil_lain.pk, self.draf.pk],
        )

        response = self.client.get(self.url_detail(self.draf))
        self.assertEqual(response.status_code, 200)

    def test_detail_memuat_pengukuran_dan_kontaminan(self):
        self.client.force_login(self.pemilik)

        response = self.client.get(self.url_detail(self.mandiri))
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["ph"], "6.50")
        self.assertEqual(
            data["nutrient_measurements"][0]["nama_unsur"],
            "Nitrogen",
        )
        self.assertEqual(
            data["contaminant_findings"][0]["kontaminan_nama"],
            "Timbal API",
        )
        self.assertIsNone(data["contaminant_findings"][0]["nilai"])
        self.assertFalse(data["ada_dokumen"])
        self.assertNotIn("dokumen_laboratorium", data)

    def test_filter_asal(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.url_daftar, {"asal": "wiji"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()],
            [self.draf.pk],
        )

    def test_filter_lahan_dan_asal(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            self.url_daftar,
            {"lahan": str(self.lahan.pk), "asal": "mandiri"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()],
            [self.mandiri.pk],
        )

    def test_filter_tidak_membuka_data_orang_lain(self):
        self.client.force_login(self.pemilik)

        response = self.client.get(
            self.url_daftar,
            {"lahan": str(self.lahan_lain.pk)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_filter_invalid_ditolak(self):
        self.client.force_login(self.pemilik)

        for parameter in [
            {"lahan": "bukan-uuid"},
            {"asal": "asal-sembarang"},
        ]:
            with self.subTest(parameter=parameter):
                response = self.client.get(self.url_daftar, parameter)
                self.assertEqual(response.status_code, 400)

    def test_endpoint_baca_menolak_perubahan(self):
        self.client.force_login(self.pemilik)

        for url in [self.url_daftar, self.url_detail(self.mandiri)]:
            for method in ["post", "put", "patch", "delete"]:
                with self.subTest(url=url, method=method):
                    response = getattr(self.client, method)(
                        url, {}, format="json",
                    )
                    self.assertEqual(response.status_code, 405)