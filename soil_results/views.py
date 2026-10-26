from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from lands.models import Lahan
from .forms import HasilMandiriForm
from .models import HasilPemeriksaan


@login_required
@require_http_methods(["GET", "POST"])
def tambah_hasil_mandiri(request, lahan_id):
    if not request.user.is_owner:
        raise PermissionDenied(
            "Hanya pemilik lahan yang dapat memasukkan hasil mandiri."
        )

    lahan = get_object_or_404(
        Lahan,
        pk=lahan_id,
        owner=request.user,
        diarsipkan=False,
    )

    if request.method == "POST":
        form = HasilMandiriForm(request.POST)

        if form.is_valid():
            hasil = form.save(commit=False)
            hasil.lahan = lahan
            hasil.dibuat_oleh = request.user
            hasil.asal = HasilPemeriksaan.Asal.MANDIRI
            hasil.save()

            messages.success(request, "Hasil mandiri berhasil disimpan.")
            return redirect("soil_results:detail_hasil", hasil_id=hasil.pk)
    else:
        form = HasilMandiriForm()

    return render(
        request,
        "soil_results/form_hasil_mandiri.html",
        {"form": form, "lahan": lahan},
    )

@login_required
@require_http_methods(["GET"])
def detail_hasil(request, hasil_id):
    hasil = get_object_or_404(
        HasilPemeriksaan.objects.select_related("lahan"),
        pk=hasil_id,
        lahan__owner=request.user,
    )

    return render(
        request,
        "soil_results/detail_hasil.html",
        {"hasil": hasil},
    )