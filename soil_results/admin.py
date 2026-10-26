from django.contrib import admin
from .models import HasilPemeriksaan


@admin.register(HasilPemeriksaan)
class HasilPemeriksaanAdmin(admin.ModelAdmin):
    list_display = (
        "lahan",
        "tanggal_pemeriksaan",
        "ph",
        "kelembapan",
        "dibuat_oleh",
    )
    list_filter = ("tanggal_pemeriksaan",)
    search_fields = ("lahan__nama",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.dibuat_oleh = request.user
        super().save_model(request, obj, form, change)