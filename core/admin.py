from django.contrib import admin

# Register your models here.
from .models import Tanaman, ContaminantType, PlantReference, PlantContaminantCapability

admin.site.register(Tanaman)
admin.site.register(ContaminantType)
admin.site.register(PlantReference)
admin.site.register(PlantContaminantCapability)