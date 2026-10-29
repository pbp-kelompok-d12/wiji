from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from inspections.ringkasan import ringkasan_admin, ringkasan_petugas

from .ringkasan import ringkasan_pemilik


def _nama_sapaan(user):
    return user.first_name.split()[0] if user.first_name else user.username


@login_required
def home(request):
    konteks = {'active_nav': 'dashboard', 'greeting_name': _nama_sapaan(request.user)}

    # Admin dicek duluan: akun staf bawaan (createsuperuser) perannya owner
    if request.user.is_staff:
        return render(request, 'dashboard/admin.html', {**konteks, **ringkasan_admin()})
    if request.user.is_officer:
        return render(request, 'dashboard/petugas.html', {**konteks, **ringkasan_petugas(request.user)})
    return render(request, 'dashboard/owner.html', {**konteks, **ringkasan_pemilik(request.user)})
