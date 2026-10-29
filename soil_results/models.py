from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from .storage import private_document_storage


class HasilPemeriksaan(models.Model):
    lahan = models.ForeignKey(
        "lands.Lahan",
        on_delete=models.PROTECT,
        related_name="soil_results",
    )
    dibuat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hasil_pemeriksaan",
    )
    tanggal_pemeriksaan = models.DateField()
    ph = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(14)],
        null=True,
        blank=True,
    )
    kelembapan = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Kelembapan dalam persen (0–100).",
        null=True,
        blank=True,
    )
    tekstur = models.CharField(max_length=100, blank=True)
    unsur_hara = models.TextField(
        blank=True,
        help_text="Tuliskan unsur, nilai hasil pemeriksaan, dan satuannya.",
    )
    kontaminan = models.TextField(
        blank=True,
        help_text="Tuliskan hasil pemeriksaan kontaminan beserta satuannya.",
    )
    dokumen_laboratorium = models.FileField(
        storage=private_document_storage,
        upload_to="hasil_pemeriksaan/%Y/%m/",
        blank=True,
    )
    catatan = models.TextField(blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Asal(models.TextChoices):
        MANDIRI = "mandiri", "Hasil Mandiri"
        WIJI = "wiji", "Hasil Wiji"

    asal = models.CharField(
        max_length=10,
        choices=Asal.choices,
        default=Asal.MANDIRI,
    )
    sumber = models.CharField(
        max_length=200,
        blank=True,
        help_text="Nama laboratorium atau pihak yang melakukan pemeriksaan.",
    )
    bahan_organik = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Kadar bahan organik dalam persen (0–100).",
    )

    class Meta:
        ordering = ["-tanggal_pemeriksaan", "-dibuat_pada"]
        verbose_name = "Hasil pemeriksaan"
        verbose_name_plural = "Hasil pemeriksaan"

    def __str__(self):
        return f"{self.lahan} — {self.tanggal_pemeriksaan}"

    def clean(self):
        super().clean()

        if (
            self.tanggal_pemeriksaan
            and self.tanggal_pemeriksaan > timezone.localdate()
        ):
            raise ValidationError({
                "tanggal_pemeriksaan":
                    "Tanggal pemeriksaan tidak boleh di masa depan."
            })

    def dipakai_dalam_rencana(self):
        return self.recommendation_snapshots.filter(
            management_plan__isnull=False,
        ).exists()


class NutrientMeasurement(models.Model):
    class Satuan(models.TextChoices):
        PERSEN = "%", "%"
        MG_KG = "mg/kg", "mg/kg"
        CMOL_KG = "cmol(+)/kg", "cmol(+)/kg"

    hasil = models.ForeignKey(
        HasilPemeriksaan,
        on_delete=models.CASCADE,
        related_name="nutrient_measurements",
    )
    nama_unsur = models.CharField(
        max_length=100,
        help_text="Nama unsur atau parameter sesuai laporan laboratorium.",
    )
    nilai = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )
    satuan = models.CharField(
        max_length=20,
        choices=Satuan.choices,
    )
    metode = models.CharField(
        max_length=200,
        blank=True,
        help_text="Metode pemeriksaan, jika tercantum dalam laporan.",
    )

    class Meta:
        ordering = ["nama_unsur", "pk"]
        verbose_name = "Pengukuran unsur hara"
        verbose_name_plural = "Pengukuran unsur hara"

    def __str__(self):
        return f"{self.nama_unsur}: {self.nilai} {self.satuan}"


class ContaminantFinding(models.Model):
    class Status(models.TextChoices):
        TERDETEKSI = "terdeteksi", "Terdeteksi"
        TIDAK_TERDETEKSI = "tidak_terdeteksi", "Tidak terdeteksi"

    class Satuan(models.TextChoices):
        MG_KG = "mg/kg", "mg/kg"
        UG_KG = "ug/kg", "µg/kg"

    hasil = models.ForeignKey(
        HasilPemeriksaan,
        on_delete=models.CASCADE,
        related_name="contaminant_findings",
    )
    kontaminan = models.ForeignKey(
        "core.ContaminantType",
        on_delete=models.PROTECT,
        related_name="soil_findings",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
    )
    nilai = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    satuan = models.CharField(
        max_length=10,
        choices=Satuan.choices,
        blank=True,
    )
    batas_deteksi = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Isi jika tercantum di laporan, dengan satuan yang sama.",
    )
    metode = models.CharField(max_length=200, blank=True)
    catatan = models.TextField(blank=True)

    class Meta:
        ordering = ["kontaminan__nama", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["hasil", "kontaminan"],
                name="unique_contaminant_per_soil_result",
            )
        ]
        verbose_name = "Temuan kontaminan"
        verbose_name_plural = "Temuan kontaminan"

    def clean(self):
        super().clean()
        errors = {}

        if self.status == self.Status.TERDETEKSI:
            if self.nilai is None:
                errors["nilai"] = (
                    "Isi nilai pengukuran untuk kontaminan terdeteksi."
                )
            if not self.satuan:
                errors["satuan"] = "Pilih satuan pengukuran."

        elif self.status == self.Status.TIDAK_TERDETEKSI:
            if self.nilai is not None:
                errors["nilai"] = (
                    "Kosongkan nilai jika kontaminan tidak terdeteksi. "
                    "Gunakan kolom batas deteksi jika tersedia."
                )

        if self.batas_deteksi is not None and not self.satuan:
            errors["satuan"] = (
                "Pilih satuan untuk batas deteksi."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.kontaminan} — {self.get_status_display()}"
