from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from lands.models import Lahan, ManagementGoal
from .models import HasilPemeriksaan, NutrientMeasurement, ContaminantFinding


from datetime import timedelta
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from .forms import HasilMandiriForm, DokumenLaboratoriumForm, ContaminantFindingForm

from core.models import Tanaman, ContaminantType
from recommendations.models import RecommendationSnapshot, ManagementPlan

from unittest.mock import patch


class AksesHasilTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.pemilik = User.objects.create_user(
            username="pemilik_tes",
            password="password-test-123",
            role="owner",
        )
        self.pengguna_lain = User.objects.create_user(
            username="pengguna_lain",
            password="password-test-123",
            role="owner",
        )

        self.lahan = Lahan.objects.create(
            owner=self.pemilik,
            nama="Lahan pengujian",
        )
        self.hasil = HasilPemeriksaan.objects.create(
            lahan=self.lahan,
            dibuat_oleh=self.pemilik,
            tanggal_pemeriksaan=date(2026, 1, 1),
            asal=HasilPemeriksaan.Asal.MANDIRI,
            sumber="Laboratorium pengujian",
            ph="6.50",
        )

    def test_pemilik_bisa_membaca_detail(self):
        self.client.force_login(self.pemilik)

        response = self.client.get(
            reverse(
                "soil_results:detail_hasil",
                args=[self.hasil.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Laboratorium pengujian")

    def test_pengguna_lain_tidak_bisa_membaca_detail(self):
        self.client.force_login(self.pengguna_lain)

        response = self.client.get(
            reverse(
                "soil_results:detail_hasil",
                args=[self.hasil.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_api_tanpa_login_ditolak(self):
        response = self.client.get(
            reverse("soil_results:api_daftar_hasil")
        )

        self.assertEqual(response.status_code, 401)

    def test_api_pengguna_lain_tidak_memuat_hasil(self):
        self.client.force_login(self.pengguna_lain)

        response = self.client.get(
            reverse("soil_results:api_daftar_hasil")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_pengguna_lain_tidak_bisa_mengubah_hasil(self):
        self.client.force_login(self.pengguna_lain)

        response = self.client.post(
            reverse(
                "soil_results:ubah_hasil_mandiri",
                args=[self.hasil.pk],
            ),
            {
                "sumber": "Diubah pengguna lain",
                "tanggal_pemeriksaan": "2026-01-01",
                "ph": "9.00",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.hasil.refresh_from_db()
        self.assertEqual(self.hasil.sumber, "Laboratorium pengujian")

    def test_pengguna_lain_tidak_bisa_menghapus_hasil(self):
        self.client.force_login(self.pengguna_lain)

        response = self.client.post(
            reverse(
                "soil_results:hapus_hasil_mandiri",
                args=[self.hasil.pk],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            HasilPemeriksaan.objects.filter(pk=self.hasil.pk).exists()
        )

    def test_membuka_konfirmasi_tidak_menghapus_data(self):
        self.client.force_login(self.pemilik)

        response = self.client.get(
            reverse(
                "soil_results:hapus_hasil_mandiri",
                args=[self.hasil.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            HasilPemeriksaan.objects.filter(pk=self.hasil.pk).exists()
        )

    def test_pemilik_tidak_bisa_melihat_draf_petugas(self):
        self.hasil.asal = HasilPemeriksaan.Asal.WIJI
        self.hasil.status_hasil = HasilPemeriksaan.StatusHasil.DRAF
        self.hasil.save()

        self.client.force_login(self.pemilik)

        for nama_url in [
            "soil_results:detail_hasil",
            "soil_results:api_detail_hasil",
        ]:
            with self.subTest(url=nama_url):
                response = self.client.get(
                    reverse(nama_url, args=[self.hasil.pk])
                )
                self.assertEqual(response.status_code, 404)

        response = self.client.get(
            reverse("soil_results:api_daftar_hasil")
        )
        self.assertEqual(response.json()["results"], [])

        response = self.client.get(
            reverse("soil_results:daftar_hasil")
        )
        self.assertNotIn(
            self.hasil.pk,
            [hasil.pk for hasil in response.context["hasil_list"]],
        )

class ValidasiFormTests(TestCase):
    def data_hasil(self, **perubahan):
        data = {
            "sumber": "Laboratorium pengujian",
            "tanggal_pemeriksaan": "2026-01-01",
            "ph": "6.50",
            "kelembapan": "40",
            "tekstur": "Lempung",
            "bahan_organik": "3",
            "catatan": "",
        }
        data.update(perubahan)
        return data

    def test_data_valid_diterima(self):
        form = HasilMandiriForm(data=self.data_hasil())
        self.assertTrue(form.is_valid(), form.errors)

    def test_ph_di_luar_batas_ditolak(self):
        form = HasilMandiriForm(data=self.data_hasil(ph="15"))
        self.assertFalse(form.is_valid())
        self.assertIn("ph", form.errors)

    def test_kelembapan_negatif_ditolak(self):
        form = HasilMandiriForm(
            data=self.data_hasil(kelembapan="-1")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("kelembapan", form.errors)

    def test_tanggal_masa_depan_ditolak(self):
        besok = timezone.localdate() + timedelta(days=1)
        form = HasilMandiriForm(
            data=self.data_hasil(
                tanggal_pemeriksaan=besok.isoformat()
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("tanggal_pemeriksaan", form.errors)

    def test_file_bernama_pdf_tapi_isi_bukan_pdf_ditolak(self):
        berkas = SimpleUploadedFile(
            "palsu.pdf",
            b"Ini bukan PDF",
            content_type="application/pdf",
        )
        form = DokumenLaboratoriumForm(
            data={},
            files={"dokumen": berkas},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("dokumen", form.errors)

    def test_file_lebih_dari_5_mb_ditolak(self):
        berkas = SimpleUploadedFile(
            "besar.pdf",
            b"%PDF-" + b"x" * (5 * 1024 * 1024),
            content_type="application/pdf",
        )
        form = DokumenLaboratoriumForm(
            data={},
            files={"dokumen": berkas},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("dokumen", form.errors)


class DokumenPrivatTests(TestCase):
    def setUp(self):
        from .storage import private_document_storage

        self.storage = private_document_storage

        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

        self.pengaturan = override_settings(
            PRIVATE_MEDIA_ROOT=self.folder.name
        )
        self.pengaturan.enable()
        self.addCleanup(self.pengaturan.disable)

        # Storage yang sudah dibuat saat import perlu diarahkan
        # ke folder sementara khusus pengujian.
        self.lokasi_lama = self.storage._location
        self.storage._location = self.folder.name
        self.storage.__dict__.pop("base_location", None)
        self.storage.__dict__.pop("location", None)
        self.addCleanup(self.pulihkan_storage)

        User = get_user_model()
        self.pemilik = User.objects.create_user(
            username="pemilik_dokumen",
            role="owner",
        )
        self.orang_lain = User.objects.create_user(
            username="orang_lain",
            role="owner",
        )
        self.admin = User.objects.create_user(
            username="admin_dokumen",
            is_staff=True,
        )
        lahan = Lahan.objects.create(
            owner=self.pemilik,
            nama="Lahan dokumen",
        )
        self.hasil = HasilPemeriksaan.objects.create(
            lahan=lahan,
            dibuat_oleh=self.pemilik,
            tanggal_pemeriksaan=date(2026, 1, 1),
            sumber="Lab pengujian",
        )
        self.isi_file = b"%PDF-1.4\nDokumen sintetis untuk tes akses\n"
        self.hasil.dokumen_laboratorium.save(
            "uji-akses.pdf",
            SimpleUploadedFile("uji-akses.pdf", self.isi_file),
        )
        self.url = reverse(
            "soil_results:unduh_dokumen",
            args=[self.hasil.pk],
        )

    def pulihkan_storage(self):
        self.storage._location = self.lokasi_lama
        self.storage.__dict__.pop("base_location", None)
        self.storage.__dict__.pop("location", None)

    def test_pemilik_bisa_mengunduh(self):
        self.client.force_login(self.pemilik)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            b"".join(response.streaming_content),
            self.isi_file,
        )
        response.close()

    def test_admin_bisa_mengunduh(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        response.close()

    def test_pengguna_lain_ditolak(self):
        self.client.force_login(self.orang_lain)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_tanpa_login_diarahkan_ke_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("next=", response.url)


class PenguncianRencanaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.pemilik = User.objects.create_user(
            username="pemilik_rencana",
            role="owner",
        )
        self.client.force_login(self.pemilik)

        self.lahan = Lahan.objects.create(
            owner=self.pemilik,
            nama="Lahan integrasi",
        )
        self.hasil = HasilPemeriksaan.objects.create(
            lahan=self.lahan,
            dibuat_oleh=self.pemilik,
            tanggal_pemeriksaan=date(2026, 1, 1),
            sumber="Lab awal",
            asal=HasilPemeriksaan.Asal.MANDIRI,
        )
        tanaman = Tanaman.objects.create(
            nama="Tanaman uji",
            fungsi="Pengujian",
            deskripsi="Data sintetis",
            kondisi_pertumbuhan="Data pengujian",
        )
        tujuan = ManagementGoal.objects.create(
            nama="Tujuan uji",
            slug="tujuan-uji",
        )
        self.rekomendasi = RecommendationSnapshot.objects.create(
            lahan=self.lahan,
            hasil_pemeriksaan=self.hasil,
            tanaman=tanaman,
            tujuan=tujuan,
            skor=80,
            kelengkapan_data=100,
        )

    def buat_rencana(self):
        return ManagementPlan.objects.create(
            pemilik=self.pemilik,
            lahan=self.lahan,
            rekomendasi=self.rekomendasi,
        )

    def test_snapshot_saja_belum_dianggap_rencana(self):
        self.assertFalse(self.hasil.dipakai_dalam_rencana())

    def test_hasil_dengan_rencana_terdeteksi(self):
        self.buat_rencana()
        self.assertTrue(self.hasil.dipakai_dalam_rencana())

    def test_edit_hasil_dengan_rencana_ditolak(self):
        self.buat_rencana()

        response = self.client.post(
            reverse(
                "soil_results:ubah_hasil_mandiri",
                args=[self.hasil.pk],
            ),
            {
                "sumber": "Sumber baru",
                "tanggal_pemeriksaan": "2026-01-01",
                "ph": "6.5",
            },
        )

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        self.hasil.refresh_from_db()
        self.assertEqual(self.hasil.sumber, "Lab awal")

    def test_hapus_hasil_dengan_rencana_ditolak(self):
        self.buat_rencana()

        response = self.client.post(
            reverse(
                "soil_results:hapus_hasil_mandiri",
                args=[self.hasil.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        self.assertTrue(
            HasilPemeriksaan.objects.filter(pk=self.hasil.pk).exists()
        )

    def test_hapus_hasil_dengan_snapshot_tidak_error_server(self):
        response = self.client.post(
            reverse(
                "soil_results:hapus_hasil_mandiri",
                args=[self.hasil.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        self.assertTrue(
            HasilPemeriksaan.objects.filter(pk=self.hasil.pk).exists()
        )

    def test_tambah_unsur_hara_saat_terkunci_ditolak(self):
        self.buat_rencana()
        jumlah_awal = self.hasil.nutrient_measurements.count()

        response = self.client.post(
            reverse(
                "soil_results:tambah_unsur_hara",
                args=[self.hasil.pk],
            ),
            {
                "nama_unsur": "Nitrogen",
                "nilai": "0.2",
                "satuan": "%",
                "metode": "Metode uji",
            },
        )

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        self.assertEqual(
            self.hasil.nutrient_measurements.count(),
            jumlah_awal,
        )

    def test_ubah_unsur_hara_saat_terkunci_ditolak(self):
        pengukuran = NutrientMeasurement.objects.create(
            hasil=self.hasil,
            nama_unsur="Nitrogen",
            nilai="0.2",
            satuan="%",
        )
        self.buat_rencana()

        response = self.client.post(
            reverse(
                "soil_results:ubah_unsur_hara",
                args=[pengukuran.pk],
            ),
            {
                "nama_unsur": "Nama diubah",
                "nilai": "0.5",
                "satuan": "%",
                "metode": "",
            },
        )

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        pengukuran.refresh_from_db()
        self.assertEqual(pengukuran.nama_unsur, "Nitrogen")
        self.assertEqual(str(pengukuran.nilai), "0.2000")

    def test_hapus_unsur_hara_saat_terkunci_ditolak(self):
        pengukuran = NutrientMeasurement.objects.create(
            hasil=self.hasil,
            nama_unsur="Nitrogen",
            nilai="0.2",
            satuan="%",
        )
        self.buat_rencana()

        response = self.client.post(
            reverse(
                "soil_results:hapus_unsur_hara",
                args=[pengukuran.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        self.assertTrue(
            NutrientMeasurement.objects.filter(
                pk=pengukuran.pk,
            ).exists()
        )

    def test_unggah_dokumen_saat_terkunci_ditolak(self):
        self.buat_rencana()
        nama_awal = self.hasil.dokumen_laboratorium.name

        dokumen = SimpleUploadedFile(
            "uji.pdf",
            b"%PDF-1.4\nDokumen sintetis\n",
            content_type="application/pdf",
        )

        storage = self.hasil.dokumen_laboratorium.storage

        with patch.object(storage, "save") as simpan_file:
            response = self.client.post(
                reverse(
                    "soil_results:unggah_dokumen",
                    args=[self.hasil.pk],
                ),
                {"dokumen": dokumen},
            )

            simpan_file.assert_not_called()

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        self.hasil.refresh_from_db()
        self.assertEqual(
            self.hasil.dokumen_laboratorium.name,
            nama_awal,
        )

    def test_detail_terkunci_menyembunyikan_tombol_ubah(self):
        self.buat_rencana()

        response = self.client.get(
            reverse(
                "soil_results:detail_hasil",
                args=[self.hasil.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Hasil digunakan dalam rencana pengelolaan",
        )
        self.assertNotContains(
            response,
            reverse(
                "soil_results:ubah_hasil_mandiri",
                args=[self.hasil.pk],
            ),
        )
        self.assertNotContains(
            response,
            reverse(
                "soil_results:unggah_dokumen",
                args=[self.hasil.pk],
            ),
        )

    def test_perubahan_kontaminan_saat_terkunci_ditolak(self):
        jenis = ContaminantType.objects.create(nama="Jenis terkunci")
        jenis_baru = ContaminantType.objects.create(nama="Jenis tambahan")

        temuan = ContaminantFinding.objects.create(
            hasil=self.hasil,
            kontaminan=jenis,
            status="terdeteksi",
            nilai="2",
            satuan="mg/kg",
        )
        self.buat_rencana()

        kasus = [
            (
                "soil_results:tambah_kontaminan",
                self.hasil.pk,
                jenis_baru.pk,
            ),
            (
                "soil_results:ubah_kontaminan",
                temuan.pk,
                jenis.pk,
            ),
            (
                "soil_results:hapus_kontaminan",
                temuan.pk,
                jenis.pk,
            ),
        ]


class KontaminanTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.pemilik = User.objects.create_user(
            username="pemilik_kontaminan",
            role="owner",
        )
        self.orang_lain = User.objects.create_user(
            username="orang_lain_kontaminan",
            role="owner",
        )
        self.client.force_login(self.pemilik)

        self.lahan = Lahan.objects.create(
            owner=self.pemilik,
            nama="Lahan kontaminan",
        )
        self.hasil = HasilPemeriksaan.objects.create(
            lahan=self.lahan,
            dibuat_oleh=self.pemilik,
            tanggal_pemeriksaan=date(2026, 1, 1),
            asal=HasilPemeriksaan.Asal.MANDIRI,
            sumber="Lab pengujian",
        )
        self.jenis = ContaminantType.objects.create(
            nama="Kontaminan uji",
        )

    def data_form(self, **perubahan):
        data = {
            "kontaminan": str(self.jenis.pk),
            "status": "terdeteksi",
            "nilai": "2",
            "satuan": "mg/kg",
            "batas_deteksi": "",
            "metode": "Metode uji",
            "catatan": "",
        }
        data.update(perubahan)
        return data

    def buat_temuan(self):
        return ContaminantFinding.objects.create(
            hasil=self.hasil,
            kontaminan=self.jenis,
            status="terdeteksi",
            nilai="2",
            satuan="mg/kg",
        )

    def test_tambah_temuan_valid(self):
        response = self.client.post(
            reverse(
                "soil_results:tambah_kontaminan",
                args=[self.hasil.pk],
            ),
            self.data_form(),
        )

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        self.assertEqual(self.hasil.contaminant_findings.count(), 1)

    def test_terdeteksi_tanpa_nilai_ditolak(self):
        form = ContaminantFindingForm(
            data=self.data_form(nilai=""),
            hasil=self.hasil,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("nilai", form.errors)

    def test_tidak_terdeteksi_tanpa_nilai_valid(self):
        form = ContaminantFindingForm(
            data=self.data_form(
                status="tidak_terdeteksi",
                nilai="",
                satuan="",
            ),
            hasil=self.hasil,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_tidak_terdeteksi_dengan_nilai_ditolak(self):
        form = ContaminantFindingForm(
            data=self.data_form(status="tidak_terdeteksi"),
            hasil=self.hasil,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("nilai", form.errors)

    def test_nilai_negatif_ditolak(self):
        form = ContaminantFindingForm(
            data=self.data_form(nilai="-1"),
            hasil=self.hasil,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("nilai", form.errors)

    def test_batas_deteksi_memerlukan_satuan(self):
        form = ContaminantFindingForm(
            data=self.data_form(
                status="tidak_terdeteksi",
                nilai="",
                satuan="",
                batas_deteksi="0.1",
            ),
            hasil=self.hasil,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("satuan", form.errors)

    def test_duplikat_ditolak(self):
        self.buat_temuan()

        form = ContaminantFindingForm(
            data=self.data_form(),
            hasil=self.hasil,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("kontaminan", form.errors)

    def test_edit_temuan_sendiri_bukan_duplikat(self):
        temuan = self.buat_temuan()

        response = self.client.post(
            reverse(
                "soil_results:ubah_kontaminan",
                args=[temuan.pk],
            ),
            self.data_form(nilai="3"),
        )

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        temuan.refresh_from_db()
        self.assertEqual(temuan.nilai, 3)
        self.assertEqual(self.hasil.contaminant_findings.count(), 1)

    def test_pengguna_lain_tidak_bisa_mengubah_atau_menghapus(self):
        temuan = self.buat_temuan()
        self.client.force_login(self.orang_lain)

        for nama_url in [
            "soil_results:ubah_kontaminan",
            "soil_results:hapus_kontaminan",
        ]:
            with self.subTest(nama_url=nama_url):
                response = self.client.post(
                    reverse(nama_url, args=[temuan.pk]),
                    self.data_form(nilai="9"),
                )
                self.assertEqual(response.status_code, 404)

        temuan.refresh_from_db()
        self.assertEqual(temuan.nilai, 2)

    def test_konfirmasi_hapus_belum_menghapus(self):
        temuan = self.buat_temuan()

        response = self.client.get(
            reverse(
                "soil_results:hapus_kontaminan",
                args=[temuan.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ContaminantFinding.objects.filter(pk=temuan.pk).exists()
        )

    def test_hapus_temuan_tidak_menghapus_hasil(self):
        temuan = self.buat_temuan()

        response = self.client.post(
            reverse(
                "soil_results:hapus_kontaminan",
                args=[temuan.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        self.assertFalse(
            ContaminantFinding.objects.filter(pk=temuan.pk).exists()
        )
        self.assertTrue(
            HasilPemeriksaan.objects.filter(pk=self.hasil.pk).exists()
        )

    def test_json_memuat_kontaminan(self):
        temuan = self.buat_temuan()

        response = self.client.get(
            reverse(
                "soil_results:api_detail_hasil",
                args=[self.hasil.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["temuan_kontaminan"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], temuan.pk)
        self.assertEqual(data[0]["kontaminan"]["nama"], self.jenis.nama)



class KontaminanTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.pemilik = User.objects.create_user(
            username="pemilik_kontaminan",
            role="owner",
        )
        self.orang_lain = User.objects.create_user(
            username="pengguna_lain_kontaminan",
            role="owner",
        )
        self.client.force_login(self.pemilik)

        self.lahan = Lahan.objects.create(
            owner=self.pemilik,
            nama="Lahan kontaminan",
        )
        self.hasil = HasilPemeriksaan.objects.create(
            lahan=self.lahan,
            dibuat_oleh=self.pemilik,
            asal=HasilPemeriksaan.Asal.MANDIRI,
            tanggal_pemeriksaan=date(2026, 1, 1),
            sumber="Laboratorium pengujian",
        )
        self.jenis = ContaminantType.objects.create(
            nama="Kontaminan uji",
        )

    def data_form(self, **perubahan):
        data = {
            "kontaminan": str(self.jenis.pk),
            "status": "terdeteksi",
            "nilai": "1.5",
            "satuan": "mg/kg",
            "batas_deteksi": "",
            "metode": "Metode uji",
            "catatan": "",
        }
        data.update(perubahan)
        return data

    def buat_temuan(self):
        return ContaminantFinding.objects.create(
            hasil=self.hasil,
            kontaminan=self.jenis,
            status="terdeteksi",
            nilai="1.5",
            satuan="mg/kg",
        )

    def test_terdeteksi_wajib_nilai_dan_satuan(self):
        form = ContaminantFindingForm(
            data=self.data_form(nilai="", satuan=""),
            hasil=self.hasil,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("nilai", form.errors)
        self.assertIn("satuan", form.errors)

    def test_tidak_terdeteksi_tanpa_nilai_valid(self):
        form = ContaminantFindingForm(
            data=self.data_form(
                status="tidak_terdeteksi",
                nilai="",
                satuan="",
            ),
            hasil=self.hasil,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_tidak_terdeteksi_tidak_boleh_diisi_nol(self):
        form = ContaminantFindingForm(
            data=self.data_form(
                status="tidak_terdeteksi",
                nilai="0",
            ),
            hasil=self.hasil,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("nilai", form.errors)

    def test_nilai_negatif_ditolak(self):
        form = ContaminantFindingForm(
            data=self.data_form(nilai="-1"),
            hasil=self.hasil,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("nilai", form.errors)

    def test_batas_deteksi_memerlukan_satuan(self):
        form = ContaminantFindingForm(
            data=self.data_form(
                status="tidak_terdeteksi",
                nilai="",
                satuan="",
                batas_deteksi="0.1",
            ),
            hasil=self.hasil,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("satuan", form.errors)

    def test_jenis_duplikat_ditolak(self):
        self.buat_temuan()

        form = ContaminantFindingForm(
            data=self.data_form(),
            hasil=self.hasil,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("kontaminan", form.errors)

    def test_edit_temuan_sendiri_bukan_duplikat(self):
        temuan = self.buat_temuan()

        form = ContaminantFindingForm(
            data=self.data_form(nilai="2"),
            hasil=self.hasil,
            instance=temuan,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_pemilik_bisa_menambah_temuan(self):
        response = self.client.post(
            reverse(
                "soil_results:tambah_kontaminan",
                args=[self.hasil.pk],
            ),
            self.data_form(),
        )

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        self.assertEqual(self.hasil.contaminant_findings.count(), 1)

    def test_orang_lain_tidak_bisa_menghapus_temuan(self):
        temuan = self.buat_temuan()
        self.client.force_login(self.orang_lain)

        response = self.client.post(
            reverse(
                "soil_results:hapus_kontaminan",
                args=[temuan.pk],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            ContaminantFinding.objects.filter(pk=temuan.pk).exists()
        )

    def test_get_konfirmasi_tidak_menghapus_temuan(self):
        temuan = self.buat_temuan()

        response = self.client.get(
            reverse(
                "soil_results:hapus_kontaminan",
                args=[temuan.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ContaminantFinding.objects.filter(pk=temuan.pk).exists()
        )

    def test_hapus_temuan_tidak_menghapus_hasil(self):
        temuan = self.buat_temuan()

        response = self.client.post(
            reverse(
                "soil_results:hapus_kontaminan",
                args=[temuan.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("soil_results:detail_hasil", args=[self.hasil.pk]),
        )
        self.assertFalse(
            ContaminantFinding.objects.filter(pk=temuan.pk).exists()
        )
        self.assertTrue(
            HasilPemeriksaan.objects.filter(pk=self.hasil.pk).exists()
        )

    def test_hasil_terkunci_menolak_perubahan_kontaminan(self):
        temuan = self.buat_temuan()

        aksi = [
            ("soil_results:tambah_kontaminan", self.hasil.pk),
            ("soil_results:ubah_kontaminan", temuan.pk),
            ("soil_results:hapus_kontaminan", temuan.pk),
        ]

        with patch.object(
            HasilPemeriksaan,
            "dipakai_dalam_rencana",
            return_value=True,
        ):
            for nama_url, objek_id in aksi:
                with self.subTest(aksi=nama_url):
                    response = self.client.post(
                        reverse(nama_url, args=[objek_id]),
                        self.data_form(nilai="9"),
                    )
                    self.assertRedirects(
                        response,
                        reverse(
                            "soil_results:detail_hasil",
                            args=[self.hasil.pk],
                        ),
                    )

        self.assertEqual(self.hasil.contaminant_findings.count(), 1)
        temuan.refresh_from_db()
        self.assertEqual(str(temuan.nilai), "1.500000")

    def test_json_memuat_temuan(self):
        temuan = self.buat_temuan()

        response = self.client.get(
            reverse(
                "soil_results:api_detail_hasil",
                args=[self.hasil.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()["temuan_kontaminan"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], temuan.pk)
        self.assertEqual(
            data[0]["kontaminan"]["nama"],
            self.jenis.nama,
        )