from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class WijiUserAdmin(UserAdmin):
    # Akun petugas dibuat admin lewat sini
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (('Peran Wiji', {'fields': ('role',)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Peran Wiji', {'fields': ('email', 'role')}),
    )
