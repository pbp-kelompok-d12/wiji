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

