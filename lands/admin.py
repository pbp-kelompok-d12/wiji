from django.contrib import admin

from .models import Lahan, ManagementGoal


@admin.register(ManagementGoal)
class ManagementGoalAdmin(admin.ModelAdmin):
    list_display = ('nama', 'slug', 'aktif')
    list_filter = ('aktif',)
    search_fields = ('nama', 'deskripsi')
    prepopulated_fields = {'slug': ('nama',)}


@admin.register(Lahan)
class LahanAdmin(admin.ModelAdmin):
    list_display = (
        'nama',
        'owner',
        'penggunaan',
        'luas_m2',
        'punya_koordinat',
        'diarsipkan',
        'dibuat_pada',
    )
    list_filter = ('diarsipkan', 'penggunaan', 'tujuan')
    search_fields = ('nama', 'alamat', 'owner__username', 'owner__email')
    readonly_fields = ('dibuat_pada', 'diperbarui_pada', 'diarsipkan_pada')
    filter_horizontal = ('tujuan',)
    list_select_related = ('owner',)
