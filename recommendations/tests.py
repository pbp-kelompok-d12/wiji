import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import (
    Tanaman,
    ContaminantType,
    PlantReference,
    PlantContaminantCapability,
)

from soil_results.models import ContaminantFinding

from lands.models import Lahan, ManagementGoal
from soil_results.models import HasilPemeriksaan

from .models import ManagementPlan, RecommendationSnapshot
from .services import (
    RecommendationInputError,
    calculate_recommendations,
)

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from .environment import fetch_environmental_data
from urllib.error import URLError
from django.urls import reverse


User = get_user_model()


class RecommendationSnapshotTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pemilik1",
            password="test-password-123",
        )
        self.goal = ManagementGoal.objects.create(
            nama="Menambah bahan organik",
            slug="menambah-bahan-organik",
        )
        self.land = Lahan.objects.create(
            owner=self.user,
            nama="Lahan Uji",
        )
        self.result = HasilPemeriksaan.objects.create(
            lahan=self.land,
            dibuat_oleh=self.user,
            tanggal_pemeriksaan=date(2026, 10, 20),
            ph=Decimal("6.50"),
            kelembapan =Decimal("45.00"),
            kontaminan="Tidak Terdeteksi",
        )
        self.plant = Tanaman.objects.create(
            nama="Tanaman Uji",
            nama_latin="Planta testus",
        )

    def create_snapshot(self, **overrides):
        data = {
            "lahan": self.land,
            "hasil_pemeriksaan": self.result,
            "tanaman": self.plant,
            "tujuan": self.goal,
            "skor": 85,
            "alasan": ["Sesuai dengan tujuan pengelolaan"],
            "input_snapshot": {"ph": "6.50"},
            "data_lingkungan": {"sumber": "Open-Meteo"},
            "kelengkapan_data": 90,
            "versi_aturan": "v1",
        }
        data.update(overrides)
        return RecommendationSnapshot.objects.create(**data)

    def test_snapshot_stores_score_reasons_and_input(self):
        snapshot = self.create_snapshot()

        self.assertEqual(snapshot.skor, 85)
        self.assertEqual(
            snapshot.alasan,
            ["Sesuai dengan tujuan pengelolaan"],
        )
        self.assertEqual(snapshot.input_snapshot["ph"], "6.50")
        self.assertEqual(snapshot.versi_aturan, "v1")

    def test_result_must_belong_to_selected_land(self):
        other_land = Lahan.objects.create(
            owner=self.user,
            nama="Lahan Lain",
        )
        snapshot = RecommendationSnapshot(
            lahan=other_land,
            hasil_pemeriksaan=self.result,
            tanaman=self.plant,
            tujuan=self.goal,
            skor=80,
            kelengkapan_data=90,
        )

        with self.assertRaises(ValidationError):
            snapshot.full_clean()

    def test_score_must_be_between_zero_and_one_hundred(self):
        snapshot = self.create_snapshot(skor=101)

        with self.assertRaises(ValidationError):
            snapshot.full_clean()

    def test_completeness_must_be_between_zero_and_one_hundred(self):
        snapshot = RecommendationSnapshot(
            lahan=self.land,
            hasil_pemeriksaan=self.result,
            tanaman=self.plant,
            tujuan=self.goal,
            skor=85,
            alasan=["Sesuai dengan tujuan pengelolaan"],
            input_snapshot={"ph": "6.50"},
            kelengkapan_data=-1,
            versi_aturan="v1",
        )

        with self.assertRaises(ValidationError):
            snapshot.full_clean()


class ManagementPlanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pemilik2",
            password="test-password-123",
        )
        self.other_user = User.objects.create_user(
            username="pemilik3",
            password="test-password-123",
        )
        self.goal = ManagementGoal.objects.create(
            nama="Memperbaiki tanah",
            slug="memperbaiki-tanah",
        )
        self.land = Lahan.objects.create(
            owner=self.user,
            nama="Lahan Pemilik",
        )
        self.result = HasilPemeriksaan.objects.create(
            lahan=self.land,
            tanggal_pemeriksaan=date(2026, 10, 20),
            ph=Decimal("6.50"),
        )
        self.plant = Tanaman.objects.create(
            nama="Tanaman Rencana",
            nama_latin="Planta planus",
        )
        self.snapshot = RecommendationSnapshot.objects.create(
            lahan=self.land,
            hasil_pemeriksaan=self.result,
            tanaman=self.plant,
            tujuan=self.goal,
            skor=85,
            alasan=["Alasan uji"],
            input_snapshot={"ph": "6.50"},
            kelengkapan_data=90,
            versi_aturan="v1",
        )

    def create_plan(self, **overrides):
        data = {
            "pemilik": self.user,
            "lahan": self.land,
            "rekomendasi": self.snapshot,
            "luas_tanam_m2": Decimal("100.00"),
            "jumlah_bibit": 50,
            "tanggal_tanam": date(2026, 11, 1),
            "catatan": "Rencana pengujian",
        }
        data.update(overrides)
        plan = ManagementPlan(**data)
        plan.full_clean()
        plan.save()
        return plan

    def test_plan_stores_management_details(self):
        plan = self.create_plan()

        self.assertEqual(plan.luas_tanam_m2, Decimal("100.00"))
        self.assertEqual(plan.jumlah_bibit, 50)
        self.assertEqual(plan.rekomendasi.skor, 85)

    def test_owner_must_own_the_land(self):
        plan = ManagementPlan(
            pemilik=self.other_user,
            lahan=self.land,
            rekomendasi=self.snapshot,
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_plan_land_must_match_snapshot_land(self):
        other_land = Lahan.objects.create(
            owner=self.user,
            nama="Lahan Kedua",
        )
        plan = ManagementPlan(
            pemilik=self.user,
            lahan=other_land,
            rekomendasi=self.snapshot,
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_one_snapshot_cannot_have_two_plans(self):
        self.create_plan()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ManagementPlan.objects.create(
                    pemilik=self.user,
                    lahan=self.land,
                    rekomendasi=self.snapshot,
                )

class RecommendationScoringTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="scoring_user",
            password="test-password-123",
        )
        self.land = Lahan.objects.create(
            owner=self.user,
            nama="Lahan Scoring",
        )
        self.goal = ManagementGoal.objects.create(
            nama="Menambah bahan organik",
            slug="menambah-bahan-organik",
        )
        self.result = HasilPemeriksaan.objects.create(
            lahan=self.land,
            dibuat_oleh=self.user,
            tanggal_pemeriksaan=date(2026, 10, 20),
            ph=Decimal("6.50"),
            kelembapan=Decimal("45.00"),
            kontaminan="Tidak terdeteksi",
        )
        self.environmental_data = {
            "status": "available",
            "source": "Open-Meteo",
            "reason": None,
            "message": "Data cuaca berhasil diambil.",
            "timezone": "Asia/Jakarta",
            "current": {
                "temperature_2m": 30.1,
            },
            "units": {
                "temperature_2m": "°C",
            },
        }

        environment_patcher = patch(
            "recommendations.services.fetch_environmental_data",
            return_value=self.environmental_data,
        )
        self.environment_mock = environment_patcher.start()
        self.addCleanup(environment_patcher.stop)

    def create_plant(self, **overrides):
        data = {
            "nama": "Tanaman Organik",
            "nama_latin": "Planta organica",
            "fungsi": "Menambah bahan organik dan unsur hara",
            "deskripsi": "Mendukung penambahan bahan organik tanah",
            "kondisi_pertumbuhan": "Informasi kondisi pertumbuhan tersedia",
            "tersedia_di_indonesia": True,
            "risiko_penggunaan": "",
        }
        data.update(overrides)
        return Tanaman.objects.create(**data)

    def create_contaminant_finding(self):
        contaminant = ContaminantType.objects.create(
            nama="Timbal",
            deskripsi="Kontaminan logam berat.",
        )

        ContaminantFinding.objects.create(
            hasil=self.result,
            kontaminan=contaminant,
            status=ContaminantFinding.Status.TERDETEKSI,
            nilai=Decimal("380"),
            satuan=ContaminantFinding.Satuan.MG_KG,
        )

        return contaminant

    def test_matching_plant_is_scored(self):
        plant = self.create_plant()

        result = calculate_recommendations(
            self.land,
            self.result,
            self.goal,
        )

        self.assertEqual(len(result["rekomendasi"]), 1)
        candidate = result["rekomendasi"][0]

        self.assertEqual(candidate.tanaman, plant)
        self.assertGreaterEqual(candidate.skor, 0)
        self.assertLessEqual(candidate.skor, 100)
        self.assertTrue(candidate.alasan)
        self.assertEqual(candidate.kelengkapan_data, 50)
        self.assertEqual(candidate.versi_aturan, "v1")
        self.assertEqual(result["data_lingkungan"]["status"],"available",)
        self.assertEqual(candidate.data_lingkungan["current"]["temperature_2m"],30.1,)

    def test_unavailable_plant_is_excluded(self):
        self.create_plant(tersedia_di_indonesia=False)

        result = calculate_recommendations(
            self.land,
            self.result,
            self.goal,
        )

        self.assertEqual(result["rekomendasi"], [])

    def test_high_risk_plant_is_blocked(self):
        plant = self.create_plant(
            risiko_penggunaan="Beracun jika dikonsumsi.",
        )

        result = calculate_recommendations(
            self.land,
            self.result,
            self.goal,
        )

        recommended_plants = [
            item.tanaman for item in result["rekomendasi"]
        ]
        blocked_plants = [
            item["tanaman"] for item in result["diblokir"]
        ]

        self.assertNotIn(plant, recommended_plants)
        self.assertIn(plant, blocked_plants)

    def test_insufficient_data_is_rejected(self):
        self.result.ph = None
        self.result.kelembapan = None
        self.result.save()

        with self.assertRaises(RecommendationInputError):
            calculate_recommendations(
                self.land,
                self.result,
                self.goal,
            )

    def test_result_from_another_land_is_rejected(self):
        other_land = Lahan.objects.create(
            owner=self.user,
            nama="Lahan Lain",
        )

        with self.assertRaises(RecommendationInputError):
            calculate_recommendations(
                other_land,
                self.result,
                self.goal,
            )

    def test_inactive_goal_is_rejected(self):
        self.goal.aktif = False
        self.goal.save()

        with self.assertRaises(RecommendationInputError):
            calculate_recommendations(
                self.land,
                self.result,
                self.goal,
            )

    def test_api_failure_does_not_fabricate_weather_in_recommendations(self):
        self.create_plant()

        unavailable_data = {
            "status": "unavailable",
            "source": "Open-Meteo",
            "reason": "api_unavailable",
            "message": "Data cuaca sementara tidak tersedia.",
            "timezone": None,
            "current": {},
            "units": {},
        }
        self.environment_mock.return_value = unavailable_data

        result = calculate_recommendations(
            self.land,
            self.result,
            self.goal,
        )

        self.assertEqual(
            result["data_lingkungan"]["status"],
            "unavailable",
        )
        self.assertEqual(result["data_lingkungan"]["current"], {})
        self.assertEqual(len(result["rekomendasi"]), 1)
        self.assertEqual(
            result["rekomendasi"][0].data_lingkungan["current"],
            {},
        )

    def test_recorded_contaminant_blocks_recommendations(self):
        self.create_plant()
        self.result.kontaminan = "Pb: 380 mg/kg; batas aman 100 mg/kg."
        self.result.sumber = "Laboratorium uji"
        self.result.save()

        result = calculate_recommendations(
            self.land,
            self.result,
            self.goal,
        )

        self.assertTrue(result["risiko_tinggi"])
        self.assertEqual(result["rekomendasi"], [])
        self.assertEqual(
            result["temuan_risiko"]["temuan"],
            self.result.kontaminan,
        )
        self.environment_mock.assert_not_called()

    def test_missing_contaminant_data_blocks_recommendations(self):
        self.result.kontaminan = ""
        self.result.save()

        result = calculate_recommendations(
            self.land,
            self.result,
            self.goal,
        )

        self.assertTrue(result["risiko_tinggi"])
        self.assertEqual(result["rekomendasi"], [])
        self.assertEqual(
            result["temuan_risiko"]["temuan"],
            "Data kontaminan belum tersedia.",
        )
        self.environment_mock.assert_not_called()

    def test_supported_contaminant_pair_is_recommended(self):
        contaminant = self.create_contaminant_finding()
        plant = self.create_plant()

        PlantContaminantCapability.objects.create(
            tanaman=plant,
            kontaminan=contaminant,
            tingkat_efektivitas="Didukung penelitian",
        )
        PlantReference.objects.create(
            tanaman=plant,
            sumber_literatur="Penelitian tentang fitoremediasi timbal",
            tautan="https://example.com/research",
        )

        self.result.kontaminan = ""
        self.result.save()

        result = calculate_recommendations(
            self.land,
            self.result,
            self.goal,
        )

        self.assertIn(
            plant,
            [item.tanaman for item in result["rekomendasi"]],
        )


    def test_unsupported_contaminant_pair_is_blocked(self):
        self.create_contaminant_finding()
        plant = self.create_plant()

        self.result.kontaminan = ""
        self.result.save()

        result = calculate_recommendations(
            self.land,
            self.result,
            self.goal,
        )

        self.assertNotIn(
            plant,
            [item.tanaman for item in result["rekomendasi"]],
        )


    def test_contaminant_pair_without_reference_is_blocked(self):
        contaminant = self.create_contaminant_finding()
        plant = self.create_plant()

        PlantContaminantCapability.objects.create(
            tanaman=plant,
            kontaminan=contaminant,
            tingkat_efektivitas="Didukung penelitian",
        )

        self.result.kontaminan = ""
        self.result.save()

        result = calculate_recommendations(
            self.land,
            self.result,
            self.goal,
        )

        self.assertNotIn(
            plant,
            [item.tanaman for item in result["rekomendasi"]],
        )
    def test_contaminant_pair_with_unrelated_reference_is_blocked(self):
        contaminant = self.create_contaminant_finding()
        plant = self.create_plant()

        PlantContaminantCapability.objects.create(
            tanaman=plant,
            kontaminan=contaminant,
            tingkat_efektivitas="Didukung penelitian",
        )

        PlantReference.objects.create(
            tanaman=plant,
            sumber_literatur="Penelitian tentang fitoremediasi arsenik",
            tautan="https://example.com/arsenic-research",
        )

        self.result.kontaminan = ""
        self.result.save()

        result = calculate_recommendations(
            self.land,
            self.result,
            self.goal,
        )

        self.assertNotIn(
            plant,
            [item.tanaman for item in result["rekomendasi"]],
        )
    def test_food_crop_without_consumption_safety_is_blocked(self):
        plant = self.create_plant(
            nama="Bayam",
            fungsi=(
                "Tanaman pangan untuk sayuran dan "
                "menambah bahan organik"
            ),
            deskripsi="Tanaman sayuran yang dapat dikonsumsi.",
            risiko_penggunaan="",
        )

        result = calculate_recommendations(
            self.land,
            self.result,
            self.goal,
        )

        self.assertNotIn(
            plant,
            [item.tanaman for item in result["rekomendasi"]],
        )

        blocked_plants = [
            item["tanaman"]
            for item in result["diblokir"]
        ]

        self.assertIn(plant, blocked_plants)

class OpenMeteoEnvironmentTests(TestCase):
    def setUp(self):
        self.land = SimpleNamespace(
            latitude=Decimal("-6.200000"),
            longitude=Decimal("106.800000"),
        )

    def api_payload(self):
        return {
            "timezone": "Asia/Jakarta",
            "current": {
                "time": "2026-10-27T19:00",
                "temperature_2m": 30.1,
                "relative_humidity_2m": 78,
                "precipitation": 0.0,
                "weather_code": 2,
                "wind_speed_10m": 5.2,
            },
            "current_units": {
                "temperature_2m": "°C",
                "relative_humidity_2m": "%",
                "precipitation": "mm",
                "weather_code": "wmo code",
                "wind_speed_10m": "km/h",
            },
        }

    @patch("recommendations.environment.urlopen")
    def test_successful_response_returns_weather(self, mock_urlopen):
        mock_urlopen.return_value = BytesIO(
            json.dumps(self.api_payload()).encode("utf-8")
        )

        result = fetch_environmental_data(self.land)

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["source"], "Open-Meteo")
        self.assertEqual(
            result["current"]["temperature_2m"], 30.1
        )
        self.assertEqual(
            result["current"]["relative_humidity_2m"], 78
        )
        self.assertEqual(result["timezone"], "Asia/Jakarta")

    @patch("recommendations.environment.urlopen")
    def test_request_sends_only_coordinates_and_weather_parameters(
        self, mock_urlopen
    ):
        mock_urlopen.return_value = BytesIO(
            json.dumps(self.api_payload()).encode("utf-8")
        )

        fetch_environmental_data(self.land)

        request = mock_urlopen.call_args.args[0]
        query = parse_qs(urlparse(request.full_url).query)

        self.assertEqual(
            set(query),
            {"latitude", "longitude", "current", "timezone"},
        )
        self.assertEqual(query["latitude"], ["-6.2"])
        self.assertEqual(query["longitude"], ["106.8"])

    @patch("recommendations.environment.urlopen")
    def test_missing_coordinates_do_not_call_api(self, mock_urlopen):
        self.land.latitude = None

        result = fetch_environmental_data(self.land)

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "coordinates_missing")
        self.assertEqual(result["current"], {})
        mock_urlopen.assert_not_called()

    @patch("recommendations.environment.urlopen")
    def test_api_failure_does_not_fabricate_weather(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Connection failed")

        result = fetch_environmental_data(self.land)

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "api_unavailable")
        self.assertEqual(result["current"], {})
        self.assertNotIn("temperature_2m", result["current"])

    @patch("recommendations.environment.urlopen")
    def test_invalid_response_is_not_used(self, mock_urlopen):
        mock_urlopen.return_value = BytesIO(
            b'{"timezone": "Asia/Jakarta", "current": {}}'
        )

        result = fetch_environmental_data(self.land)

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "response_invalid")
        self.assertEqual(result["current"], {})

    @patch("recommendations.environment.urlopen")
    def test_out_of_range_coordinates_do_not_call_api(
        self, mock_urlopen
    ):
        self.land.latitude = Decimal("100")

        result = fetch_environmental_data(self.land)

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "coordinates_invalid")
        mock_urlopen.assert_not_called()

class RecommendationListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="recommendation_page_owner",
            password="test-password-123",
        )
        self.land = Lahan.objects.create(
            owner=self.user,
            nama="Lahan Saya",
        )
        self.result = HasilPemeriksaan.objects.create(
            lahan=self.land,
            dibuat_oleh=self.user,
            tanggal_pemeriksaan=date(2026, 10, 20),
        )
        self.goal = ManagementGoal.objects.create(
            nama="Tujuan Halaman",
            slug="tujuan-halaman",
        )
        self.url = reverse("recommendations:daftar_rekomendasi")

    def test_page_requires_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_owner_can_open_recommendation_page(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "recommendations/daftar_rekomendasi.html",
        )

    def test_only_current_users_lands_are_listed(self):
        other_user = User.objects.create_user(
            username="other_recommendation_owner",
            password="test-password-123",
        )
        Lahan.objects.create(
            owner=other_user,
            nama="Lahan Rahasia Pengguna Lain",
        )

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(
            list(response.context["lahan_list"]),
            [self.land],
        )

    def test_officer_cannot_open_owner_recommendation_page(self):
        officer = User.objects.create_user(
            username="recommendation_officer",
            password="test-password-123",
            role=User.Role.OFFICER,
        )
        self.client.force_login(officer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_invalid_land_id_does_not_crash_page(self):
        self.client.force_login(self.user)

        response = self.client.get(
            self.url,
            {"lahan": "not-a-valid-uuid"},
        )

        self.assertEqual(response.status_code, 200)

    def test_results_are_filtered_by_selected_land(self):
        another_land = Lahan.objects.create(
            owner=self.user,
            nama="Lahan Kedua",
        )
        another_result = HasilPemeriksaan.objects.create(
            lahan=another_land,
            dibuat_oleh=self.user,
            tanggal_pemeriksaan=date(2026, 10, 21),
        )

        self.client.force_login(self.user)
        response = self.client.get(
            self.url,
            {"lahan": str(self.land.pk)},
        )

        self.assertEqual(
            list(response.context["hasil_list"]),
            [self.result],
        )
        self.assertNotIn(
            another_result,
            response.context["hasil_list"],
        )
class ManagementPlanViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="plan_owner",
            password="test-password-123",
        )
        self.other_user = User.objects.create_user(
            username="plan_other_owner",
            password="test-password-123",
        )

        self.land = Lahan.objects.create(
            owner=self.user,
            nama="Lahan Rencana",
        )
        self.goal = ManagementGoal.objects.create(
            nama="Menambah bahan organik",
            slug="tujuan-rencana-organik",
        )
        self.result = HasilPemeriksaan.objects.create(
            lahan=self.land,
            dibuat_oleh=self.user,
            tanggal_pemeriksaan=date(2026, 10, 20),
            ph=Decimal("6.50"),
            kelembapan=Decimal("45.00"),
            kontaminan="Tidak terdeteksi",
        )
        self.plant = Tanaman.objects.create(
            nama="Tanaman Rencana",
            nama_latin="Planta consilii",
            fungsi="Menambah bahan organik dan unsur hara",
            deskripsi="Tanaman untuk mendukung bahan organik tanah",
            kondisi_pertumbuhan="Informasi kondisi pertumbuhan tercatat",
            tersedia_di_indonesia=True,
            risiko_penggunaan="",
        )

        self.environment_data = {
            "status": "unavailable",
            "source": "Open-Meteo",
            "reason": "coordinates_missing",
            "message": "Koordinat lahan belum tersedia.",
            "timezone": None,
            "current": {},
            "units": {},
        }
        environment_patcher = patch(
            "recommendations.services.fetch_environmental_data",
            return_value=self.environment_data,
        )
        self.environment_mock = environment_patcher.start()
        self.addCleanup(environment_patcher.stop)

        self.recommendation_url = reverse(
            "recommendations:daftar_rekomendasi"
        )
        self.list_url = reverse("recommendations:daftar_rencana")

    def create_plan(self, owner=None):
        snapshot = RecommendationSnapshot.objects.create(
            lahan=self.land,
            hasil_pemeriksaan=self.result,
            tanaman=self.plant,
            tujuan=self.goal,
            skor=85,
            alasan=["Cocok dengan kata kunci tujuan."],
            input_snapshot={"ph": "6.50"},
            data_lingkungan=self.environment_data,
            kelengkapan_data=33,
            versi_aturan="v1",
        )
        plan = ManagementPlan(
            pemilik=owner or self.user,
            lahan=self.land,
            rekomendasi=snapshot,
            luas_tanam_m2=Decimal("100.00"),
            jumlah_bibit=50,
            catatan="Rencana uji",
        )
        plan.full_clean()
        plan.save()
        return plan

    def test_plan_list_requires_login(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 302)

    def test_owner_can_open_empty_plan_list(self):
        self.client.force_login(self.user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "recommendations/daftar_rencana.html",
        )

    def test_plan_list_only_shows_current_users_plans(self):
        own_plan = self.create_plan()

        other_land = Lahan.objects.create(
            owner=self.other_user,
            nama="Lahan Pemilik Lain",
        )
        other_result = HasilPemeriksaan.objects.create(
            lahan=other_land,
            dibuat_oleh=self.other_user,
            tanggal_pemeriksaan=date(2026, 10, 21),
        )
        other_goal = ManagementGoal.objects.create(
            nama="Tujuan Pemilik Lain",
            slug="tujuan-pemilik-lain",
        )
        other_snapshot = RecommendationSnapshot.objects.create(
            lahan=other_land,
            hasil_pemeriksaan=other_result,
            tanaman=self.plant,
            tujuan=other_goal,
            skor=70,
            kelengkapan_data=33,
        )
        ManagementPlan.objects.create(
            pemilik=self.other_user,
            lahan=other_land,
            rekomendasi=other_snapshot,
        )

        self.client.force_login(self.user)
        response = self.client.get(self.list_url)

        self.assertEqual(
            list(response.context["rencana_list"]),
            [own_plan],
        )

    def test_owner_can_open_plan_detail(self):
        plan = self.create_plan()
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("recommendations:detail_rencana", args=[plan.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["rencana"], plan)

    def test_other_user_cannot_open_plan_detail(self):
        plan = self.create_plan()
        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse("recommendations:detail_rencana", args=[plan.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_owner_can_create_plan_from_valid_recommendation(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("recommendations:buat_rencana"),
            {
                "lahan": str(self.land.pk),
                "hasil": str(self.result.pk),
                "tujuan": str(self.goal.pk),
                "tanaman": str(self.plant.pk),
                "luas_tanam_m2": "100",
                "jumlah_bibit": "50",
                "tanggal_tanam": "2026-11-01",
                "catatan": "Mulai setelah persiapan lahan.",
            },
        )

        self.assertEqual(ManagementPlan.objects.count(), 1)
        plan = ManagementPlan.objects.select_related(
            "rekomendasi"
        ).get()

        self.assertEqual(plan.pemilik, self.user)
        self.assertEqual(plan.lahan, self.land)
        self.assertEqual(plan.rekomendasi.tanaman, self.plant)
        self.assertEqual(plan.rekomendasi.input_snapshot["ph"], "6.50")
        self.assertEqual(plan.rekomendasi.versi_aturan, "v1")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("recommendations:detail_rencana", args=[plan.pk]),
        )

    def test_high_risk_plant_cannot_be_saved_as_plan(self):
        risky_plant = Tanaman.objects.create(
            nama="Tanaman Berisiko",
            nama_latin="Planta periculosa",
            fungsi="Menambah bahan organik dan unsur hara",
            deskripsi="Tanaman yang perlu penilaian risiko",
            kondisi_pertumbuhan="Informasi kondisi pertumbuhan tersedia",
            tersedia_di_indonesia=True,
            risiko_penggunaan="Beracun jika dikonsumsi.",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("recommendations:buat_rencana"),
            {
                "lahan": str(self.land.pk),
                "hasil": str(self.result.pk),
                "tujuan": str(self.goal.pk),
                "tanaman": str(risky_plant.pk),
                "catatan": "Uji safety",
            },
        )

        self.assertEqual(ManagementPlan.objects.count(), 0)
        self.assertEqual(RecommendationSnapshot.objects.count(), 0)
        self.assertEqual(response.status_code, 302)

    def test_user_cannot_create_plan_for_another_users_land(self):
        other_land = Lahan.objects.create(
            owner=self.other_user,
            nama="Bukan Lahan Saya",
        )
        other_result = HasilPemeriksaan.objects.create(
            lahan=other_land,
            dibuat_oleh=self.other_user,
            tanggal_pemeriksaan=date(2026, 10, 21),
            ph=Decimal("6.50"),
            kelembapan=Decimal("45.00"),
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("recommendations:buat_rencana"),
            {
                "lahan": str(other_land.pk),
                "hasil": str(other_result.pk),
                "tujuan": str(self.goal.pk),
                "tanaman": str(self.plant.pk),
            },
        )

        self.assertEqual(ManagementPlan.objects.count(), 0)
        self.assertEqual(RecommendationSnapshot.objects.count(), 0)
        self.assertEqual(response.status_code, 302)

    def test_owner_can_edit_plan(self):
        plan = self.create_plan()
        snapshot_id = plan.rekomendasi_id
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("recommendations:edit_rencana", args=[plan.pk]),
            {
                "luas_tanam_m2": "125.50",
                "jumlah_bibit": "75",
                "tanggal_tanam": "2026-11-15",
                "catatan": "Detail rencana diperbarui.",
            },
        )

        self.assertRedirects(
            response,
            reverse("recommendations:detail_rencana", args=[plan.pk]),
        )

        plan.refresh_from_db()
        self.assertEqual(plan.luas_tanam_m2, Decimal("125.50"))
        self.assertEqual(plan.jumlah_bibit, 75)
        self.assertEqual(plan.tanggal_tanam, date(2026, 11, 15))
        self.assertEqual(plan.catatan, "Detail rencana diperbarui.")

        # Snapshot rekomendasi tetap dipertahankan.
        self.assertEqual(plan.rekomendasi_id, snapshot_id)
        self.assertEqual(plan.rekomendasi.skor, 85)

    def test_edit_form_is_displayed(self):
        plan = self.create_plan()
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("recommendations:edit_rencana", args=[plan.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "recommendations/edit_rencana.html",
        )

    def test_other_user_cannot_edit_plan(self):
        plan = self.create_plan()
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse("recommendations:edit_rencana", args=[plan.pk]),
            {
                "luas_tanam_m2": "200",
                "jumlah_bibit": "100",
                "catatan": "Percobaan akses.",
            },
        )

        self.assertEqual(response.status_code, 404)
        plan.refresh_from_db()
        self.assertEqual(plan.luas_tanam_m2, Decimal("100.00"))

    def test_delete_confirmation_does_not_delete_plan(self):
        plan = self.create_plan()
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("recommendations:hapus_rencana", args=[plan.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "recommendations/konfirmasi_hapus_rencana.html",
        )
        self.assertTrue(
            ManagementPlan.objects.filter(pk=plan.pk).exists()
        )
        self.assertTrue(
            RecommendationSnapshot.objects.filter(
                pk=plan.rekomendasi_id
            ).exists()
        )

    def test_owner_can_delete_plan_and_its_snapshot(self):
        plan = self.create_plan()
        plan_id = plan.pk
        snapshot_id = plan.rekomendasi_id
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("recommendations:hapus_rencana", args=[plan_id])
        )

        self.assertRedirects(
            response,
            reverse("recommendations:daftar_rencana"),
        )
        self.assertFalse(
            ManagementPlan.objects.filter(pk=plan_id).exists()
        )
        self.assertFalse(
            RecommendationSnapshot.objects.filter(pk=snapshot_id).exists()
        )

    def test_other_user_cannot_delete_plan(self):
        plan = self.create_plan()
        snapshot_id = plan.rekomendasi_id
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse("recommendations:hapus_rencana", args=[plan.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            ManagementPlan.objects.filter(pk=plan.pk).exists()
        )
        self.assertTrue(
            RecommendationSnapshot.objects.filter(pk=snapshot_id).exists()
        )

    def test_contaminated_result_displays_risk_page(self):
        self.result.kontaminan = "Pb: 380 mg/kg; batas aman 100 mg/kg."
        self.result.sumber = "Laboratorium uji"
        self.result.save()
        self.client.force_login(self.user)

        response = self.client.get(
            self.recommendation_url,
            {
                "lahan": str(self.land.pk),
                "hasil": str(self.result.pk),
                "tujuan": str(self.goal.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "recommendations/risiko_tinggi.html",
        )
        self.assertTrue(
            response.context["temuan_risiko"]["risiko_tinggi"]
        )
        self.environment_mock.assert_not_called()

    def test_contaminated_result_cannot_create_plan(self):
        self.result.kontaminan = "Pb: 380 mg/kg; batas aman 100 mg/kg."
        self.result.sumber = "Laboratorium uji"
        self.result.save()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("recommendations:buat_rencana"),
            {
                "lahan": str(self.land.pk),
                "hasil": str(self.result.pk),
                "tujuan": str(self.goal.pk),
                "tanaman": str(self.plant.pk),
                "luas_tanam_m2": "100",
                "jumlah_bibit": "50",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ManagementPlan.objects.count(), 0)
        self.assertEqual(RecommendationSnapshot.objects.count(), 0)


class HasilLahanAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="api_owner",
            password="test-password-123",
        )
        self.other_user = User.objects.create_user(
            username="api_other_owner",
            password="test-password-123",
        )

        self.land = Lahan.objects.create(
            owner=self.user,
            nama="Lahan API",
        )

        self.result = HasilPemeriksaan.objects.create(
            lahan=self.land,
            dibuat_oleh=self.user,
            tanggal_pemeriksaan=date(2026, 10, 20),
            asal=HasilPemeriksaan.Asal.MANDIRI,
            sumber="Laboratorium Uji",
        )

        self.url = reverse(
            "recommendations:api_hasil_lahan",
            kwargs={"lahan_id": self.land.pk},
        )

    def test_owner_can_get_json_results(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/json",
        )
        self.assertEqual(
            response["Cache-Control"],
            "private, no-store",
        )
        self.assertEqual(
            response.json(),
            {
                "results": [
                    {
                        "id": self.result.pk,
                        "tanggal_pemeriksaan": "2026-10-20",
                        "asal": "Hasil Mandiri",
                        "sumber": "Laboratorium Uji",
                    }
                ]
            },
        )

    def test_unauthenticated_user_cannot_access_api(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)

    def test_officer_cannot_access_owner_api(self):
        officer = User.objects.create_user(
            username="api_officer",
            password="test-password-123",
            role=User.Role.OFFICER,
        )
        self.client.force_login(officer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_owner_cannot_access_another_users_land(self):
        other_land = Lahan.objects.create(
            owner=self.other_user,
            nama="Lahan Pengguna Lain",
        )
        self.client.force_login(self.user)

        url = reverse(
            "recommendations:api_hasil_lahan",
            kwargs={"lahan_id": other_land.pk},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_api_only_accepts_get_method(self):
        self.client.force_login(self.user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)