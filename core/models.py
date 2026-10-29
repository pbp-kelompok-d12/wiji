from django.db import models

# Create your models here.
class Tanaman(models.Model):
    nama = models.CharField(max_length=100)
    nama_latin = models.CharField(max_length=150, blank=True, null=True)
    
    # Fungsi utama: Mencegah erosi, Menyerap kontaminan, Menambah unsur hara, dll.
    fungsi = models.CharField(max_length=150)
    deskripsi = models.TextField()
    
    # Parameter Ekologis
    kondisi_pertumbuhan = models.TextField(help_text="Syarat pH, tekstur tanah, kelembapan, dan cuaca.")
    kontaminan_ditangani = models.TextField(blank=True, null=True, help_text="Kosongkan jika untuk tanah sehat. Isi jika untuk fitoremediasi.")
    
    # Status & Risiko
    tersedia_di_indonesia = models.BooleanField(default=True, help_text="Centang jika tanaman ini mudah ditemukan/dibudidayakan di Indonesia.")
    risiko_penggunaan = models.TextField(blank=True, null=True, help_text="Contoh: Tanaman invasif, atau beracun jika dikonsumsi setelah menyerap kontaminan.")
    sumber_penelitian = models.TextField(blank=True, null=True)
    
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    #Relasi ke Modul A (lahan)
    tujuan_pengelolaan = models.ManyToManyField('lands.ManagementGoal', blank=True, related_name='tanaman_didukung')

    def __str__(self):
        return self.nama

class ContaminantType(models.Model):
    nama = models.CharField(max_length=100, unique=True)
    deskripsi = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.nama

class PlantReference(models.Model):
    tanaman = models.ForeignKey(Tanaman, on_delete=models.CASCADE, related_name='referensi')
    sumber_literatur = models.CharField(max_length=255)
    tautan = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Referensi untuk {self.tanaman.nama}"

class PlantContaminantCapability(models.Model):
    tanaman = models.ForeignKey(Tanaman, on_delete=models.CASCADE, related_name='kemampuan_kontaminan')
    kontaminan = models.ForeignKey(ContaminantType, on_delete=models.CASCADE)
    tingkat_efektivitas = models.CharField(max_length=50, blank=True)
    catatan_khusus = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.tanaman.nama} menangani {self.kontaminan.nama}"