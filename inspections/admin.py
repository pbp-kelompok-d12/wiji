from django.contrib import admin

from .models import JenisPemeriksaan


@admin.register(JenisPemeriksaan)
class JenisPemeriksaanAdmin(admin.ModelAdmin):
    list_display = ('nama', 'tingkat', 'aktif')
    list_filter = ('aktif',)
    prepopulated_fields = {'slug': ('nama',)}

