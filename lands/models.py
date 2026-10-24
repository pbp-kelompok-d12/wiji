import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


class ManagementGoal(models.Model):
    nama = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    deskripsi = models.TextField(blank=True)
    aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ['nama']
        verbose_name = 'Tujuan pengelolaan'
        verbose_name_plural = 'Tujuan pengelolaan'

    def __str__(self):
        return self.nama


class Lahan(models.Model):
    REQUIRED_FIELDS = (
        'nama',
        'alamat',
        'latitude',
        'longitude',
        'luas_m2',
        'penggunaan',
    )

    class Penggunaan(models.TextChoices):
        SAWAH = 'sawah', 'Sawah'
        KEBUN = 'kebun', 'Kebun'
        PEKARANGAN = 'pekarangan', 'Pekarangan'
        LADANG = 'ladang', 'Ladang'
        TAMBAK = 'tambak', 'Tambak'
        LAINNYA = 'lainnya', 'Lainnya'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lands',
    )
    nama = models.CharField(max_length=120, null=True, blank=True)
    alamat = models.TextField(null=True, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    luas_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Luas lahan dalam meter persegi.',
    )
    penggunaan = models.CharField(
        max_length=20,
        choices=Penggunaan.choices,
        null=True,
        blank=True,
    )
    kondisi = models.TextField(blank=True)
    foto = models.ImageField(upload_to='lahan/%Y/%m/', blank=True, null=True)
    tujuan = models.ManyToManyField(
        ManagementGoal,
        related_name='lahan',
        blank=True,
    )
    diarsipkan = models.BooleanField(default=False)
    diarsipkan_pada = models.DateTimeField(null=True, blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-dibuat_pada']
        indexes = [models.Index(fields=['owner', 'diarsipkan'])]
        verbose_name = 'Lahan'
        verbose_name_plural = 'Lahan'

    def __str__(self):
        return self.nama or 'Lahan tanpa nama'

    def get_absolute_url(self):
        return reverse('lands:detail_lahan', args=[self.pk])

    @property
    def punya_koordinat(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def adalah_draf(self):
        return any(
            getattr(self, field_name) in (None, '')
            for field_name in self.REQUIRED_FIELDS
        )

    def clean(self):
        super().clean()
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError(
                'Latitude dan longitude harus diisi berdua atau dikosongkan berdua.'
            )
        if self.luas_m2 is not None and self.luas_m2 <= 0:
            raise ValidationError({'luas_m2': 'Luas lahan harus lebih dari 0.'})

    def punya_riwayat(self):
        for name in (
            'orders',
            'inspection_orders',
            'soil_results',
            'recommendation_snapshots',
            'management_plans',
        ):
            manager = getattr(self, name, None)
            if manager is not None and manager.exists():
                return True
        return False

    def punya_pesanan_aktif(self):
        status_akhir = Q(status__iexact='selesai') | Q(status__iexact='dibatalkan')

        for name in ('orders', 'inspection_orders'):
            manager = getattr(self, name, None)
            if manager is not None and manager.exclude(status_akhir).exists():
                return True
        return False

    @property
    def dapat_dihapus(self):
        return not self.punya_riwayat()

    @property
    def dapat_diarsipkan(self):
        return not self.diarsipkan and not self.punya_pesanan_aktif()

    def arsipkan(self):
        self.diarsipkan = True
        self.diarsipkan_pada = timezone.now()
        self.save(update_fields=['diarsipkan', 'diarsipkan_pada', 'diperbarui_pada'])

    def pulihkan(self):
        self.diarsipkan = False
        self.diarsipkan_pada = None
        self.save(update_fields=['diarsipkan', 'diarsipkan_pada', 'diperbarui_pada'])


Land = Lahan
