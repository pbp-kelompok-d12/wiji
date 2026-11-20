"""Siapa boleh lihat dan ngapain di modul pemeriksaan.

- Admin = akun staf (is_staff). Lihat dan kelola semua pesanan.
- Petugas = akun dengan peran officer. Cuma lihat pesanan yang ditugaskan ke dia.
- Pemilik = akun dengan peran owner. Cuma lihat pesanan buat lahannya sendiri.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import PesananPemeriksaan


def adalah_admin(user):
    return user.is_authenticated and user.is_staff


def adalah_petugas(user):
    return user.is_authenticated and user.role == 'officer'


def _wajib(cek):
    """Bikin pembatas halaman: belum masuk -> ke halaman masuk, peran salah -> 403."""
    def pembatas(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not cek(request.user):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return pembatas


admin_required = _wajib(adalah_admin)
petugas_required = _wajib(adalah_petugas)


def pesanan_untuk(user):
    """Pesanan yang boleh diakses pengguna ini. Satu pintu supaya halaman dan API selalu sepakat."""
    semua = PesananPemeriksaan.objects.select_related('lahan', 'lahan__owner', 'jenis', 'petugas')
    if adalah_admin(user):
        return semua
    if adalah_petugas(user):
        return semua.filter(petugas=user)
    if user.is_authenticated:
        return semua.filter(lahan__owner=user)
    return semua.none()
