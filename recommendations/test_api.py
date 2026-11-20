from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from core.models import ContaminantType, Tanaman
from lands.models import Lahan, ManagementGoal
from soil_results.models import ContaminantFinding, HasilPemeriksaan

from .models import ManagementPlan, RecommendationSnapshot


User = get_user_model()


class ModuleEAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="api_owner",
            password="owner-password-123",
            role=User.Role.OWNER,
        )
        self.other_owner = User.objects.create_user(
            username="api_other_owner",
            password="other-password-123",
            role=User.Role.OWNER,
        )
        self.officer = User.objects.create_user(
            username="api_officer",
            password="officer-password-123",
            role=User.Role.OFFICER,
        )
        self.lahan = Lahan.objects.create(
            owner=self.owner,
            nama="Kebun API",
        )
        self.tujuan = ManagementGoal.objects.create(
            nama="Menambah bahan organik",
            slug="api-tambah-bahan-organik",
        )
        self.hasil = HasilPemeriksaan.objects.create(
            lahan=self.lahan,
            dibuat_oleh=self.owner,
            tanggal_pemeriksaan=date(2026, 1, 5),
            ph=Decimal("6.50"),
            kelembapan=Decimal("45.00"),
        )
        kontaminan, _ = ContaminantType.objects.get_or_create(
            nama="Timbal (Pb)"
        )
        ContaminantFinding.objects.create(
            hasil=self.hasil,
            kontaminan=kontaminan,
            status="tidak_terdeteksi",
        )
        self.tanaman = self.create_plant("Tanaman Organik")
        self.environment_data = {
            "status": "unavailable",
            "source": "Open-Meteo",
            "reason": "coordinates_missing",
            "message": "Koordinat lahan belum tersedia.",
            "timezone": None,
            "current": {},
            "units": {},
        }
        environmental_patch = patch(
            "recommendations.services.fetch_environmental_data",
            return_value=self.environment_data,
        )
        self.environment_mock = environmental_patch.start()
        self.addCleanup(environmental_patch.stop)

        self.recommendation_url = reverse(
            "recommendations_api:rekomendasi_lahan",
            kwargs={"lahan_id": self.lahan.pk},
        )
        self.plan_list_url = reverse(
            "recommendations_api:daftar_rencana"
        )

    def create_plant(self, name, risk=""):
        return Tanaman.objects.create(
            nama=name,
            nama_latin="Planta API",
            fungsi="Menambah bahan organik dan unsur hara",
            deskripsi="Mendukung bahan organik tanah.",
            kondisi_pertumbuhan="Informasi kondisi tumbuh tersedia.",
            tersedia_di_indonesia=True,
            risiko_penggunaan=risk,
        )

    def authenticate_as(self, user=None):
        self.client.force_authenticate(user=user)

    def recommendation_params(self, **overrides):
        params = {"hasil": self.hasil.pk, "tujuan": self.tujuan.pk}
        params.update(overrides)
        return params

    def create_plan(self, owner=None, status=ManagementPlan.Status.DIRENCANAKAN):
        owner = owner or self.owner
        if owner == self.owner:
            lahan = self.lahan
            hasil = self.hasil
            tujuan = self.tujuan
        else:
            lahan = Lahan.objects.create(
                owner=owner,
                nama="Kebun Pemilik Lain",
            )
            hasil = HasilPemeriksaan.objects.create(
                lahan=lahan,
                dibuat_oleh=owner,
                tanggal_pemeriksaan=date(2026, 1, 6),
            )
            tujuan = ManagementGoal.objects.create(
                nama="Tujuan Pemilik Lain",
                slug="tujuan-pemilik-lain-api",
            )

        snapshot = RecommendationSnapshot.objects.create(
            lahan=lahan,
            hasil_pemeriksaan=hasil,
            tanaman=self.tanaman,
            tujuan=tujuan,
            skor=82,
            alasan=["Sesuai dengan tujuan pengelolaan."],
            input_snapshot={"ph": "6.50"},
            data_lingkungan=self.environment_data,
            kelengkapan_data=33,
            versi_aturan="v1",
        )
        return ManagementPlan.objects.create(
            pemilik=owner,
            lahan=lahan,
            rekomendasi=snapshot,
            luas_tanam_m2=Decimal("100.00"),
            jumlah_bibit=40,
            catatan="Catatan untuk aplikasi mobile.",
            status=status,
        )

    def test_recommendation_requires_authentication(self):
        response = self.client.get(
            self.recommendation_url,
            self.recommendation_params(),
        )

        self.assertEqual(response.status_code, 403)

    def test_recommendation_rejects_non_owner(self):
        self.authenticate_as(self.officer)

        response = self.client.get(
            self.recommendation_url,
            self.recommendation_params(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("pemilik lahan", response.json()["detail"].lower())

    def test_owner_gets_recommendations_without_writing_records(self):
        self.authenticate_as(self.owner)
        before = (
            RecommendationSnapshot.objects.count(),
            ManagementPlan.objects.count(),
        )

        response = self.client.get(
            self.recommendation_url,
            self.recommendation_params(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["lahan"]["id"], str(self.lahan.pk))
        self.assertEqual(payload["hasil"]["id"], self.hasil.pk)
        self.assertEqual(payload["tujuan"]["id"], self.tujuan.pk)
        own_plant = next(
            item
            for item in payload["rekomendasi"]
            if item["tanaman"]["id"] == self.tanaman.pk
        )
        self.assertEqual(own_plant["skor"], 90)
        self.assertEqual(
            (
                RecommendationSnapshot.objects.count(),
                ManagementPlan.objects.count(),
            ),
            before,
        )
        self.environment_mock.assert_called_once_with(self.lahan)
        self.assert_private_no_store(response)

    def test_recommendation_rejects_missing_and_invalid_query_parameters(self):
        self.authenticate_as(self.owner)

        missing = self.client.get(self.recommendation_url)
        invalid = self.client.get(
            self.recommendation_url,
            {"hasil": "abc", "tujuan": "-3"},
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("details", missing.json())
        self.assertIn("error", invalid.json())

    def test_owner_cannot_request_recommendations_for_another_land(self):
        other_land = Lahan.objects.create(
            owner=self.other_owner,
            nama="Lahan lain",
        )
        url = reverse(
            "recommendations_api:rekomendasi_lahan",
            kwargs={"lahan_id": other_land.pk},
        )
        self.authenticate_as(self.owner)

        response = self.client.get(
            url,
            self.recommendation_params(),
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "Lahan tidak ditemukan.")

    def test_result_must_belong_to_requested_land(self):
        other_land = Lahan.objects.create(
            owner=self.owner,
            nama="Lahan hasil berbeda",
        )
        other_result = HasilPemeriksaan.objects.create(
            lahan=other_land,
            dibuat_oleh=self.owner,
            tanggal_pemeriksaan=date(2026, 1, 7),
            ph=Decimal("6.00"),
            kelembapan=Decimal("30.00"),
        )
        self.authenticate_as(self.owner)

        response = self.client.get(
            self.recommendation_url,
            self.recommendation_params(hasil=other_result.pk),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("tidak sesuai", response.json()["error"])

    def test_missing_result_is_not_found(self):
        self.authenticate_as(self.owner)

        response = self.client.get(
            self.recommendation_url,
            self.recommendation_params(hasil=999999),
        )

        self.assertEqual(response.status_code, 404)

    def test_draft_result_is_not_found(self):
        draft = HasilPemeriksaan.objects.create(
            lahan=self.lahan,
            dibuat_oleh=self.owner,
            tanggal_pemeriksaan=date(2026, 1, 9),
            status_hasil=HasilPemeriksaan.StatusHasil.DRAF,
        )
        self.authenticate_as(self.owner)

        response = self.client.get(
            self.recommendation_url,
            self.recommendation_params(hasil=draft.pk),
        )

        self.assertEqual(response.status_code, 404)

    def test_inactive_or_unknown_goal_is_rejected(self):
        self.authenticate_as(self.owner)
        self.tujuan.aktif = False
        self.tujuan.save(update_fields=["aktif"])

        inactive = self.client.get(
            self.recommendation_url,
            self.recommendation_params(),
        )
        unknown = self.client.get(
            self.recommendation_url,
            self.recommendation_params(tujuan=999999),
        )

        self.assertEqual(inactive.status_code, 400)
        self.assertEqual(unknown.status_code, 404)
        self.assertIn("tidak aktif", inactive.json()["error"])

    def test_incomplete_soil_data_returns_service_error(self):
        incomplete = HasilPemeriksaan.objects.create(
            lahan=self.lahan,
            dibuat_oleh=self.owner,
            tanggal_pemeriksaan=date(2026, 1, 8),
        )
        kontaminan = ContaminantType.objects.get(nama="Timbal (Pb)")
        ContaminantFinding.objects.create(
            hasil=incomplete,
            kontaminan=kontaminan,
            status="tidak_terdeteksi",
        )
        self.authenticate_as(self.owner)

        response = self.client.get(
            self.recommendation_url,
            self.recommendation_params(hasil=incomplete.pk),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("belum mencukupi", response.json()["error"])
        self.environment_mock.assert_not_called()

    def test_contamination_risk_stops_environment_fetch_and_recommendations(self):
        self.hasil.kontaminan = "Arsenik terdeteksi"
        self.hasil.save(update_fields=["kontaminan"])
        self.authenticate_as(self.owner)

        response = self.client.get(
            self.recommendation_url,
            self.recommendation_params(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["risiko_tinggi"])
        self.assertEqual(payload["rekomendasi"], [])
        self.assertTrue(payload["temuan_risiko"]["risiko_tinggi"])
        self.environment_mock.assert_not_called()

    def test_high_risk_plants_remain_blocked(self):
        risky_plant = self.create_plant(
            "Tanaman Beracun",
            risk="Beracun jika dikonsumsi.",
        )
        self.authenticate_as(self.owner)

        response = self.client.get(
            self.recommendation_url,
            self.recommendation_params(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(
            any(item["tanaman"]["id"] == self.tanaman.pk
                for item in payload["rekomendasi"])
        )
        self.assertTrue(
            any(item["tanaman"]["id"] == risky_plant.pk
                for item in payload["diblokir"])
        )

    def test_recommendation_only_allows_get(self):
        self.authenticate_as(self.owner)

        response = self.client.post(
            self.recommendation_url,
            self.recommendation_params(),
            format="json",
        )

        self.assertEqual(response.status_code, 405)

    def test_plan_list_requires_authentication_and_owner_role(self):
        unauthenticated = self.client.get(self.plan_list_url)
        self.authenticate_as(self.officer)
        officer = self.client.get(self.plan_list_url)

        self.assertEqual(unauthenticated.status_code, 403)
        self.assertEqual(officer.status_code, 403)

    def test_plan_list_is_owner_scoped_and_supports_status_filter(self):
        planned = self.create_plan()
        ongoing = self.create_plan(status=ManagementPlan.Status.BERJALAN)
        other_plan = self.create_plan(owner=self.other_owner)
        self.authenticate_as(self.owner)

        all_response = self.client.get(self.plan_list_url)
        filtered_response = self.client.get(
            self.plan_list_url,
            {"status": ManagementPlan.Status.BERJALAN},
        )
        invalid_filter = self.client.get(
            self.plan_list_url,
            {"status": "unknown"},
        )

        self.assertEqual(all_response.status_code, 200)
        all_ids = {item["id"] for item in all_response.json()["results"]}
        self.assertEqual(all_ids, {planned.pk, ongoing.pk})
        self.assertNotIn(other_plan.pk, all_ids)
        self.assertEqual(
            [item["id"] for item in filtered_response.json()["results"]],
            [ongoing.pk],
        )
        self.assertEqual(invalid_filter.status_code, 400)
        self.assert_private_no_store(all_response)

    def test_plan_list_only_allows_get(self):
        self.authenticate_as(self.owner)

        response = self.client.post(self.plan_list_url, {}, format="json")

        self.assertEqual(response.status_code, 405)

    def test_owner_can_retrieve_plan_details_and_related_information(self):
        plan = self.create_plan()
        self.authenticate_as(self.owner)
        url = reverse(
            "recommendations_api:detail_rencana",
            kwargs={"pk": plan.pk},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], plan.pk)
        self.assertEqual(payload["lahan"]["id"], str(self.lahan.pk))
        self.assertEqual(payload["rekomendasi"]["tanaman"]["id"], self.tanaman.pk)
        self.assertEqual(payload["rekomendasi"]["tujuan"]["id"], self.tujuan.pk)
        self.assertEqual(
            payload["rekomendasi"]["input_snapshot"]["ph"],
            "6.50",
        )
        self.assertEqual(payload["status_label"], "Direncanakan")
        self.assertNotIn("pemilik", payload)
        self.assert_private_no_store(response)

    def test_another_owners_or_missing_plan_returns_404(self):
        other_plan = self.create_plan(owner=self.other_owner)
        self.authenticate_as(self.owner)
        other_url = reverse(
            "recommendations_api:detail_rencana",
            kwargs={"pk": other_plan.pk},
        )
        missing_url = reverse(
            "recommendations_api:detail_rencana",
            kwargs={"pk": 999999},
        )

        other_response = self.client.get(other_url)
        missing_response = self.client.get(missing_url)

        self.assertEqual(other_response.status_code, 404)
        self.assertEqual(missing_response.status_code, 404)

    def test_plan_detail_requires_authentication_and_owner_role(self):
        plan = self.create_plan()
        url = reverse(
            "recommendations_api:detail_rencana",
            kwargs={"pk": plan.pk},
        )
        unauthenticated = self.client.get(url)
        self.authenticate_as(self.officer)

        officer = self.client.get(url)

        self.assertEqual(unauthenticated.status_code, 403)
        self.assertEqual(officer.status_code, 403)

    def test_plan_detail_only_allows_get(self):
        plan = self.create_plan()
        self.authenticate_as(self.owner)
        url = reverse(
            "recommendations_api:detail_rencana",
            kwargs={"pk": plan.pk},
        )

        patch_response = self.client.patch(url, {"catatan": "Ubah"}, format="json")
        delete_response = self.client.delete(url)

        self.assertEqual(patch_response.status_code, 405)
        self.assertEqual(delete_response.status_code, 405)

    def assert_private_no_store(self, response):
        self.assertIn("private", response["Cache-Control"])
        self.assertIn("no-store", response["Cache-Control"])
