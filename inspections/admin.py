from django.contrib import admin

from .models import JenisPemeriksaan, PesananPemeriksaan, RiwayatPesanan


@admin.register(JenisPemeriksaan)
class JenisPemeriksaanAdmin(admin.ModelAdmin):
    list_display = ('nama', 'tingkat', 'aktif')
    list_filter = ('aktif',)
    prepopulated_fields = {'slug': ('nama',)}


class RiwayatInline(admin.TabularInline):
    model = RiwayatPesanan
    extra = 0
    can_delete = False
    # Riwayat cuma boleh dicatat lewat alur resmi, jangan diubah dari admin
    readonly_fields = [f.name for f in RiwayatPesanan._meta.fields if f.name != 'id']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PesananPemeriksaan)
class PesananPemeriksaanAdmin(admin.ModelAdmin):
    list_display = ('kode', 'lahan', 'jenis', 'status', 'petugas', 'tanggal_usulan')
    list_filter = ('status', 'jenis')
    search_fields = ('lahan__nama', 'lahan__owner__username')
    # Status, petugas, dan jadwal final nggak boleh diubah langsung dari admin, supaya
    # nggak lolos dari riwayat. Semuanya lewat halaman kelola atau fungsi transisi.
    readonly_fields = ('status', 'petugas', 'tanggal_final', 'sesi_final')
    inlines = [RiwayatInline]
