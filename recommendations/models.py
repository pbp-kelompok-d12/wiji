from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class RecommendationSnapshot(models.Model):
    """
    Rekaman rekomendasi pada saat rekomendasi dihitung.
    Data snapshot tidak dimaksudkan untuk berubah saat rencana diedit.
    """

    lahan = models.ForeignKey(
        "lands.Lahan",
        on_delete=models.PROTECT,
        related_name="recommendation_snapshots",
    )
    hasil_pemeriksaan = models.ForeignKey(
        "soil_results.HasilPemeriksaan",
        on_delete=models.PROTECT,
        related_name="recommendation_snapshots",
    )
    tanaman = models.ForeignKey(
        "core.Tanaman",
        on_delete=models.PROTECT,
        related_name="recommendation_snapshots",
    )
    tujuan = models.ForeignKey(
        "lands.ManagementGoal",
        on_delete=models.PROTECT,
        related_name="recommendation_snapshots",
    )

    skor = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    alasan = models.JSONField(default=list)
    input_snapshot = models.JSONField(default=dict)
    data_lingkungan = models.JSONField(default=dict, blank=True)
    kelengkapan_data = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    versi_aturan = models.CharField(max_length=50, default="v1")

    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dibuat_pada"]
        verbose_name = "Snapshot rekomendasi"
        verbose_name_plural = "Snapshot rekomendasi"

    def __str__(self):
        return (
            f"Rekomendasi {self.tanaman} "
            f"({self.skor}/100)"
        )

    def clean(self):
        super().clean()

        if (
            self.lahan_id
            and self.hasil_pemeriksaan_id
            and self.hasil_pemeriksaan.lahan_id != self.lahan_id
        ):
            raise ValidationError({
                "hasil_pemeriksaan":
                    "Hasil pemeriksaan harus berasal dari lahan yang dipilih."
            })


class ManagementPlan(models.Model):
    """
    Rencana pengelolaan milik seorang pengguna.
    Tanaman, skor, dan alasan rekomendasi bersumber dari snapshot.
    """

    class Status(models.TextChoices):
        DIRENCANAKAN = "direncanakan", "Direncanakan"
        BERJALAN = "berjalan", "Sedang berjalan"
        SELESAI = "selesai", "Selesai"

    pemilik = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="management_plans",
    )
    lahan = models.ForeignKey(
        "lands.Lahan",
        on_delete=models.PROTECT,
        related_name="management_plans",
    )
    rekomendasi = models.OneToOneField(
        RecommendationSnapshot,
        on_delete=models.PROTECT,
        related_name="management_plan",
    )

    luas_tanam_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.01)],
    )
    jumlah_bibit = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    tanggal_tanam = models.DateField(null=True, blank=True)
    catatan = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DIRENCANAKAN,
    )

    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-dibuat_pada"]
        verbose_name = "Rencana pengelolaan"
        verbose_name_plural = "Rencana pengelolaan"

    def __str__(self):
        return f"Rencana {self.lahan} - {self.rekomendasi.tanaman}"

    def clean(self):
        super().clean()

        errors = {}

        if self.lahan_id and self.rekomendasi_id:
            if self.rekomendasi.lahan_id != self.lahan_id:
                errors["rekomendasi"] = (
                    "Rekomendasi harus berasal dari lahan yang dipilih."
                )

        if self.pemilik_id and self.lahan_id:
            if self.lahan.owner_id != self.pemilik_id:
                errors["pemilik"] = (
                    "Pemilik rencana harus merupakan pemilik lahan."
                )

        if errors:
            raise ValidationError(errors)
