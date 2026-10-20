from django.db import models

# Create your models here.
class Tanaman(models.Model):
    nama = models.CharField(max_length=100)
    deskripsi = models.TextField()
    jenis = models.CharField(max_length=50)
    harga = models.IntegerField()
    stok = models.IntegerField(default=0)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nama