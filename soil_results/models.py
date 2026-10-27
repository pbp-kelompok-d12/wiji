from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


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