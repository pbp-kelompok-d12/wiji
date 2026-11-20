from django.contrib import admin

from .models import HasilPemeriksaan, RiwayatKoreksiHasil


class ReadOnlyAdmin(admin.ModelAdmin):
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HasilPemeriksaan)
class HasilPemeriksaanAdmin(ReadOnlyAdmin):
    list_display = (
        "lahan",
        "tanggal_pemeriksaan",
        "asal",
        "status_hasil",
        "dibuat_oleh",
    )
    list_filter = (
        "asal",
        "status_hasil",
        "tanggal_pemeriksaan",
    )
    search_fields = ("lahan__nama",)
    exclude = ("dokumen_laboratorium",)


@admin.register(RiwayatKoreksiHasil)
class RiwayatKoreksiHasilAdmin(ReadOnlyAdmin):
    list_display = (
        "hasil",
        "dikoreksi_oleh",
        "dibuat_pada",
    )
    search_fields = (
        "hasil__lahan__nama",
        "dikoreksi_oleh__username",
        "alasan",
    )
    list_filter = ("dibuat_pada",)