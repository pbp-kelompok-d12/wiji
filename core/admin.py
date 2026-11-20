from django.contrib import admin

from .models import ContaminantType, PlantContaminantCapability, PlantReference, Tanaman


class PlantReferenceInline(admin.TabularInline):
    model = PlantReference
    extra = 1


class PlantContaminantCapabilityInline(admin.TabularInline):
    model = PlantContaminantCapability
    extra = 0


@admin.register(Tanaman)
class TanamanAdmin(admin.ModelAdmin):
    list_display = ('nama', 'nama_latin', 'fungsi', 'tersedia_di_indonesia', 'diarsipkan')
    list_filter = ('diarsipkan', 'tersedia_di_indonesia', 'tujuan_pengelolaan')
    search_fields = ('nama', 'nama_latin', 'fungsi')
    filter_horizontal = ('tujuan_pengelolaan',)
    inlines = [PlantReferenceInline, PlantContaminantCapabilityInline]


admin.site.register(ContaminantType)
admin.site.register(PlantReference)
admin.site.register(PlantContaminantCapability)
