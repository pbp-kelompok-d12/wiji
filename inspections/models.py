from django.conf import settings
from django.db import models


class JenisPemeriksaan(models.Model):
    """Layanan yang dipilih pemilik pas memesan. Dikelola admin.

    Jenisnya bertingkat: makin tinggi tingkatnya, makin banyak data wajib
    yang harus diisi petugas sebelum hasil difinalkan (lihat docs/DOMAIN.md).
    """

    nama = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    deskripsi = models.TextField(blank=True)
    tingkat = models.PositiveSmallIntegerField(
        default=1,
        help_text='Urutan jenis. 1 = paling dasar.',
    )
    aktif = models.BooleanField(
        default=True,
        help_text='Jenis yang nggak aktif nggak muncul di form pesanan.',
    )

    class Meta:
        ordering = ['tingkat', 'nama']
        verbose_name = 'Jenis pemeriksaan'
        verbose_name_plural = 'Jenis pemeriksaan'

    def __str__(self):
        return self.nama


class PesananPemeriksaan(models.Model):
    """Satu permintaan pemeriksaan tanah untuk satu lahan.

    Pemilik pesanan dibaca dari lahan.owner, jadi nggak disimpan lagi di sini.
    Kolom petugas = petugas yang ditugaskan admin.
    """

    class Status(models.TextChoices):
        DIAJUKAN = 'diajukan', 'Diajukan'
        DIKONFIRMASI = 'dikonfirmasi', 'Dikonfirmasi'
        DIJADWALKAN = 'dijadwalkan', 'Dijadwalkan'
        SAMPEL_DIAMBIL = 'sampel_diambil', 'Sampel diambil'
        DIPROSES = 'diproses', 'Diproses'
        SELESAI = 'selesai', 'Selesai'
        DIBATALKAN = 'dibatalkan', 'Dibatalkan'

    class Sesi(models.TextChoices):
        PAGI = 'pagi', 'Pagi'
        SIANG = 'siang', 'Siang'

    # Pesanan dianggap aktif selama belum masuk salah satu status akhir ini.
    # Nilainya sengaja huruf kecil, karena lands.Lahan membacanya begitu.
    STATUS_AKHIR = (Status.SELESAI, Status.DIBATALKAN)

    lahan = models.ForeignKey(
        'lands.Lahan',
        on_delete=models.PROTECT,
        related_name='inspection_orders',
    )
    jenis = models.ForeignKey(
        JenisPemeriksaan,
        on_delete=models.PROTECT,
        related_name='pesanan',
    )
    petugas = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'officer'},
        related_name='tugas_pemeriksaan',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DIAJUKAN,
    )
    # Jadwal usulan dari pemilik
    tanggal_usulan = models.DateField()
    sesi_usulan = models.CharField(max_length=10, choices=Sesi.choices)
    # Jadwal final dari admin, kosong sampai status Dijadwalkan
    tanggal_final = models.DateField(null=True, blank=True)
    sesi_final = models.CharField(max_length=10, choices=Sesi.choices, blank=True)
    catatan = models.TextField(blank=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-dibuat_pada', '-id']
        verbose_name = 'Pesanan pemeriksaan'
        verbose_name_plural = 'Pesanan pemeriksaan'
        constraints = [
            # Satu lahan cuma boleh punya satu pesanan aktif
            models.UniqueConstraint(
                fields=['lahan'],
                condition=~models.Q(status__in=['selesai', 'dibatalkan']),
                name='satu_pesanan_aktif_per_lahan',
            ),
        ]

    def __str__(self):
        return f'{self.kode} · {self.lahan}'

    @property
    def kode(self):
        return f'WJ-{self.pk:04d}' if self.pk else 'WJ-baru'

    @property
    def pemilik(self):
        return self.lahan.owner

    @property
    def aktif(self):
        return self.status not in self.STATUS_AKHIR


class RiwayatPesanan(models.Model):
    """Catatan tiap perubahan penting pada pesanan. Jadi isi linimasa di halaman detail."""

    class Jenis(models.TextChoices):
        STATUS = 'status', 'Perubahan status'
        JADWAL_ULANG = 'jadwal_ulang', 'Jadwal ulang'
        GANTI_PETUGAS = 'ganti_petugas', 'Ganti petugas'

    pesanan = models.ForeignKey(
        PesananPemeriksaan,
        on_delete=models.CASCADE,
        related_name='riwayat',
    )
    jenis = models.CharField(max_length=20, choices=Jenis.choices, default=Jenis.STATUS)
    oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='riwayat_pesanan',
    )
    status_sebelum = models.CharField(
        max_length=20, choices=PesananPemeriksaan.Status.choices, blank=True,
    )
    status_sesudah = models.CharField(
        max_length=20, choices=PesananPemeriksaan.Status.choices, blank=True,
    )
    # Cuma diisi pas jadwal ulang
    tanggal_lama = models.DateField(null=True, blank=True)
    tanggal_baru = models.DateField(null=True, blank=True)
    catatan = models.TextField(blank=True, help_text='Catatan atau alasan perubahan.')
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['dibuat_pada', 'id']
        verbose_name = 'Riwayat pesanan'
        verbose_name_plural = 'Riwayat pesanan'

    def __str__(self):
        return f'{self.pesanan.kode} · {self.get_jenis_display()}'
