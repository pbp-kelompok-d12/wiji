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

@login_required
@require_http_methods(["GET", "POST"])
def ubah_hasil_mandiri(request, hasil_id):
    if not request.user.is_owner:
        raise PermissionDenied(
            "Hanya pemilik lahan yang dapat mengubah hasil mandiri."
        )

    hasil = get_object_or_404(
        HasilPemeriksaan.objects.select_related("lahan"),
        pk=hasil_id,
        lahan__owner=request.user,
        lahan__diarsipkan=False,
        asal=HasilPemeriksaan.Asal.MANDIRI,
    )

    # TODO integrasi Modul E
    # Blokir perubahan jika hasil sudah dipakai dalam rencana.

    if request.method == "POST":
        form = HasilMandiriForm(request.POST, instance=hasil)

        if form.is_valid():
            form.save()
            messages.success(request, "Hasil mandiri berhasil diperbarui.")
            return redirect(
                "soil_results:detail_hasil",
                hasil_id=hasil.pk,
            )
    else:
        form = HasilMandiriForm(instance=hasil)

    return render(
        request,
        "soil_results/form_hasil_mandiri.html",
        {
            "form": form,
            "lahan": hasil.lahan,
            "hasil": hasil,
            "is_edit": True,
        },
    )

@login_required
@require_http_methods(["GET", "POST"])
def hapus_hasil_mandiri(request, hasil_id):
    if not request.user.is_owner:
        raise PermissionDenied(
            "Hanya pemilik lahan yang dapat menghapus hasil mandiri."
        )

    hasil = get_object_or_404(
        HasilPemeriksaan.objects.select_related("lahan"),
        pk=hasil_id,
        lahan__owner=request.user,
        lahan__diarsipkan=False,
        asal=HasilPemeriksaan.Asal.MANDIRI,
    )

    # TODO integrasi Modul E:
    # Blokir penghapusan jika hasil sudah dipakai dalam rencana.

    if request.method == "POST":
        lahan_url = hasil.lahan.get_absolute_url()
        hasil.delete()

        messages.success(request, "Hasil mandiri berhasil dihapus.")
        return redirect(lahan_url)

    return render(
        request,
        "soil_results/konfirmasi_hapus.html",
        {"hasil": hasil},
    )