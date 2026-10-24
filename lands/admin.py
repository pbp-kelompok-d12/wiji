from django.contrib import admin

from .models import ManagementGoal


@admin.register(ManagementGoal)
class ManagementGoalAdmin(admin.ModelAdmin):
    list_display = ('nama', 'slug', 'aktif')
    list_filter = ('aktif',)
    search_fields = ('nama', 'deskripsi')
    prepopulated_fields = {'slug': ('nama',)}


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


try:
    from . import models
    if hasattr(models, 'Lahan') and not admin.site.is_registered(models.Lahan):
        admin.site.register(models.Lahan, LahanAdmin)
    if hasattr(models, 'Land') and models.Land is not models.Lahan and not admin.site.is_registered(models.Land):
        admin.site.register(models.Land, LahanAdmin)
except Exception:
    pass
