"""Autentikasi sama permission bareng buat semua API DRF di /api/v1/.

Semua modul pakai yang di sini biar aturan aksesnya sama, dan kalau cara login HP berubah
cukup diganti di satu tempat. Contoh di api_views.py:

    @api_view(['GET'])
    @authentication_classes(API_AUTH)
    @permission_classes([IsPemilik])
    def daftar_lahan(request):
        ...

Peran sama kayak di web: pemilik dan petugas dibedain lewat kolom `role`, admin itu akun staf.
Permission di sini cuma ngecek peran. Ngecek "ini data punya dia bukan" tetap tugas view
(filter queryset pakai request.user, data orang lain dibalas 404).
"""
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import SAFE_METHODS, BasePermission

# Sementara cuma sesi login web, kayak Tutorial 07, jadi endpoint bisa dicoba lewat Browsable API
# setelah login di web. Login dari HP (issue 14) nanti nambahin caranya di daftar ini.
API_AUTH = [SessionAuthentication]


def _login(request):
    return bool(request.user and request.user.is_authenticated)


class IsPemilik(BasePermission):
    message = 'Cuma pemilik lahan yang bisa mengakses ini.'

    def has_permission(self, request, view):
        return _login(request) and request.user.is_owner


class IsPetugas(BasePermission):
    message = 'Cuma petugas pemeriksa yang bisa mengakses ini.'

    def has_permission(self, request, view):
        return _login(request) and request.user.is_officer


class IsAdminWiji(BasePermission):
    """Admin Wiji itu akun staf (is_staff), bukan superuser."""

    message = 'Cuma admin yang bisa mengakses ini.'

    def has_permission(self, request, view):
        return _login(request) and request.user.is_staff


class IsAdminWijiOrReadOnly(BasePermission):
    """Semua orang boleh baca (GET), yang boleh ngubah cuma admin. Misalnya katalog tanaman."""

    message = 'Cuma admin yang bisa mengubah data ini.'

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or (_login(request) and request.user.is_staff)
