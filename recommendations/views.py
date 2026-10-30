from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import render

from lands.models import Lahan, ManagementGoal
from soil_results.models import HasilPemeriksaan

from .services import (
    RecommendationInputError,
    calculate_recommendations,
)

from urllib.parse import urlencode

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import ManagementPlanForm
from .models import ManagementPlan, RecommendationSnapshot

from django.http import JsonResponse
from django.views.decorators.http import require_GET


def _first_by_pk(queryset, value):
    """
    Cari satu objek berdasarkan primary key.
    ID yang kosong atau tidak valid menghasilkan None,
    bukan error server.
    """
    if not value:
        return None

    try:
        return queryset.filter(pk=value).first()
    except (TypeError, ValueError, ValidationError):
        return None


@login_required
def daftar_rekomendasi(request):
    """
    Halaman rekomendasi tanaman untuk pemilik lahan.

    Pengguna hanya dapat memilih lahan dan hasil pemeriksaan
    yang memang berada dalam kepemilikannya.
    """
    # Modul E ini ditujukan untuk pemilik lahan.
    if not request.user.is_owner:
        raise PermissionDenied

    # Hanya tampilkan lahan aktif milik pengguna yang login.
    lahan_list = (
        Lahan.objects.filter(
            owner=request.user,
            diarsipkan=False,
        )
        .order_by("nama")
    )

    # Hanya tujuan pengelolaan yang masih aktif.
    tujuan_list = ManagementGoal.objects.filter(
        aktif=True,
    ).order_by("nama")

    # Batasi hasil pemeriksaan berdasarkan kepemilikan lahan.
    hasil_list = (
        HasilPemeriksaan.objects.filter(
            lahan__owner=request.user,
            lahan__diarsipkan=False,
        )
        .select_related("lahan")
    )

    # Ambil pilihan dari query string.
    lahan_id = request.GET.get("lahan", "").strip()
    hasil_id = request.GET.get("hasil", "").strip()
    tujuan_id = request.GET.get("tujuan", "").strip()

    # 1. Pilih lahan milik pengguna.
    lahan_terpilih = _first_by_pk(lahan_list, lahan_id)

    if lahan_id and lahan_terpilih is None:
        messages.error(
            request,
            "Lahan yang dipilih tidak tersedia atau bukan milikmu.",
        )

    # 2. Hasil pemeriksaan harus berasal dari lahan terpilih.
    if lahan_terpilih:
        hasil_form = hasil_list.filter(lahan=lahan_terpilih)
    else:
        hasil_form = hasil_list.none()

    hasil_terpilih = _first_by_pk(hasil_form, hasil_id)

    if hasil_id and hasil_terpilih is None:
        messages.error(
            request,
            "Hasil pemeriksaan tidak valid untuk lahan yang dipilih.",
        )

    # 3. Pilih tujuan pengelolaan yang aktif.
    tujuan_terpilih = _first_by_pk(tujuan_list, tujuan_id)

    if tujuan_id and tujuan_terpilih is None:
        messages.error(
            request,
            "Tujuan pengelolaan tidak tersedia atau sudah tidak aktif.",
        )

    # Belum ada rekomendasi sebelum ketiga input valid.
    hasil_scoring = None

    if (
        lahan_terpilih is not None
        and hasil_terpilih is not None
        and tujuan_terpilih is not None
    ):
        try:
            hasil_scoring = calculate_recommendations(
                lahan=lahan_terpilih,
                hasil_pemeriksaan=hasil_terpilih,
                tujuan=tujuan_terpilih,
            )
        except RecommendationInputError as exc:
            messages.error(request, str(exc))

    if hasil_scoring and hasil_scoring.get("risiko_tinggi"):
        return render(
            request,
            "recommendations/risiko_tinggi.html",
            {
                "active_nav": "rekomendasi",
                "lahan_terpilih": lahan_terpilih,
                "hasil_terpilih": hasil_terpilih,
                "tujuan_terpilih": tujuan_terpilih,
                "temuan_risiko": hasil_scoring["temuan_risiko"],
            },
        )

    context = {
        "active_nav": "rekomendasi",
        "lahan_list": lahan_list,
        "hasil_list": hasil_form,
        "tujuan_list": tujuan_list,
        "lahan_terpilih": lahan_terpilih,
        "hasil_terpilih": hasil_terpilih,
        "tujuan_terpilih": tujuan_terpilih,
        "hasil_scoring": hasil_scoring,
    }

    return render(
        request,
        "recommendations/daftar_rekomendasi.html",
        context,
    )

@login_required
def daftar_rencana(request):
    if not request.user.is_owner:
        raise PermissionDenied

    rencana_list = (
        ManagementPlan.objects.filter(pemilik=request.user)
        .select_related(
            "lahan",
            "rekomendasi",
            "rekomendasi__tanaman",
            "rekomendasi__tujuan",
        )
        .order_by("-dibuat_pada")
    )

    return render(
        request,
        "recommendations/daftar_rencana.html",
        {
            "active_nav": "rencana",
            "rencana_list": rencana_list,
        },
    )


@login_required
def detail_rencana(request, pk):
    if not request.user.is_owner:
        raise PermissionDenied

    rencana = get_object_or_404(
        ManagementPlan.objects.select_related(
            "lahan",
            "rekomendasi",
            "rekomendasi__tanaman",
            "rekomendasi__tujuan",
            "rekomendasi__hasil_pemeriksaan",
        ),
        pk=pk,
        pemilik=request.user,
    )

    return render(
        request,
        "recommendations/detail_rencana.html",
        {
            "active_nav": "rencana",
            "rencana": rencana,
        },
    )


@login_required
def buat_rencana(request):
    if not request.user.is_owner:
        raise PermissionDenied

    # Form ini hanya boleh dikirim melalui POST.
    if request.method != "POST":
        return redirect("recommendations:daftar_rekomendasi")

    lahan_id = request.POST.get("lahan", "").strip()
    hasil_id = request.POST.get("hasil", "").strip()
    tujuan_id = request.POST.get("tujuan", "").strip()
    tanaman_id = request.POST.get("tanaman", "").strip()

    # Kalau input tidak valid, kembalikan pengguna ke halaman
    # rekomendasi dengan filter yang sama.
    params = {
        "lahan": lahan_id,
        "hasil": hasil_id,
        "tujuan": tujuan_id,
    }
    params = {key: value for key, value in params.items() if value}
    target_rekomendasi = reverse("recommendations:daftar_rekomendasi")
    if params:
        target_rekomendasi += "?" + urlencode(params)

    form = ManagementPlanForm(request.POST)

    lahan = _first_by_pk(
        Lahan.objects.filter(
            owner=request.user,
            diarsipkan=False,
        ),
        lahan_id,
    )

    if lahan is None:
        messages.error(
            request,
            "Lahan tidak valid atau bukan milikmu.",
        )
        return redirect(target_rekomendasi)

    hasil_pemeriksaan = _first_by_pk(
        HasilPemeriksaan.objects.filter(lahan=lahan),
        hasil_id,
    )

    if hasil_pemeriksaan is None:
        messages.error(
            request,
            "Pilih hasil pemeriksaan yang berasal dari lahan tersebut.",
        )
        return redirect(target_rekomendasi)

    tujuan = _first_by_pk(
        ManagementGoal.objects.filter(aktif=True),
        tujuan_id,
    )

    if tujuan is None:
        messages.error(
            request,
            "Tujuan pengelolaan tidak valid atau sudah tidak aktif.",
        )
        return redirect(target_rekomendasi)

    if not form.is_valid():
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
        return redirect(target_rekomendasi)

    try:
        hasil_scoring = calculate_recommendations(
            lahan=lahan,
            hasil_pemeriksaan=hasil_pemeriksaan,
            tujuan=tujuan,
        )
    except RecommendationInputError as exc:
        messages.error(request, str(exc))
        return redirect(target_rekomendasi)

    if hasil_scoring.get("risiko_tinggi"):
        messages.error(
            request,
            "Pembuatan rencana otomatis dihentikan karena hasil "
            "pemeriksaan memerlukan penilaian ahli.",
        )
        return redirect(target_rekomendasi)
    
    # Hanya tanaman yang lolos filter scoring yang boleh disimpan.
    # Tanaman berisiko tinggi yang masuk daftar diblokir tidak bisa
    # dipaksakan menjadi rencana hanya dengan mengubah POST.
    kandidat = next(
        (
            item
            for item in hasil_scoring["rekomendasi"]
            if str(item.tanaman.pk) == tanaman_id
        ),
        None,
    )

    if kandidat is None:
        messages.error(
            request,
            "Tanaman tersebut tidak tersedia sebagai rekomendasi "
            "yang aman untuk input saat ini.",
        )
        return redirect(target_rekomendasi)

    try:
        with transaction.atomic():
            snapshot = RecommendationSnapshot(
                lahan=lahan,
                hasil_pemeriksaan=hasil_pemeriksaan,
                tanaman=kandidat.tanaman,
                tujuan=tujuan,
                skor=kandidat.skor,
                alasan=kandidat.alasan,
                input_snapshot=kandidat.input_snapshot,
                data_lingkungan=kandidat.data_lingkungan,
                kelengkapan_data=kandidat.kelengkapan_data,
                versi_aturan=kandidat.versi_aturan,
            )
            snapshot.full_clean()
            snapshot.save()

            rencana = ManagementPlan(
                pemilik=request.user,
                lahan=lahan,
                rekomendasi=snapshot,
                **form.cleaned_data,
            )
            rencana.full_clean()
            rencana.save()

    except ValidationError:
        messages.error(
            request,
            "Rencana tidak dapat disimpan karena datanya tidak valid.",
        )
        return redirect(target_rekomendasi)

    messages.success(request, "Rencana pengelolaan berhasil dibuat.")
    return redirect(
        "recommendations:detail_rencana",
        pk=rencana.pk,
    )

@login_required
def edit_rencana(request, pk):
    if not request.user.is_owner:
        raise PermissionDenied

    rencana = get_object_or_404(
        ManagementPlan.objects.select_related(
            "lahan",
            "rekomendasi",
            "rekomendasi__tanaman",
        ),
        pk=pk,
        pemilik=request.user,
    )

    if request.method == "POST":
        form = ManagementPlanForm(request.POST, instance=rencana)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Rencana pengelolaan berhasil diperbarui.",
            )
            return redirect(
                "recommendations:detail_rencana",
                pk=rencana.pk,
            )
    else:
        form = ManagementPlanForm(instance=rencana)

    return render(
        request,
        "recommendations/edit_rencana.html",
        {
            "active_nav": "rencana",
            "rencana": rencana,
            "form": form,
        },
    )


@login_required
def hapus_rencana(request, pk):
    if not request.user.is_owner:
        raise PermissionDenied

    rencana = get_object_or_404(
        ManagementPlan.objects.select_related(
            "lahan",
            "rekomendasi",
            "rekomendasi__tanaman",
        ),
        pk=pk,
        pemilik=request.user,
    )

    if request.method == "POST":
        snapshot = rencana.rekomendasi

        with transaction.atomic():
            rencana.delete()
            snapshot.delete()

        messages.success(
            request,
            "Rencana pengelolaan berhasil dihapus.",
        )
        return redirect("recommendations:daftar_rencana")

    if request.method != "GET":
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["GET", "POST"])

    return render(
        request,
        "recommendations/konfirmasi_hapus_rencana.html",
        {
            "active_nav": "rencana",
            "rencana": rencana,
        },
    )

@require_GET
def api_hasil_lahan(request, lahan_id):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "Silakan login terlebih dahulu."},
            status=401,
        )

    if not request.user.is_owner:
        return JsonResponse(
            {"error": "Akses hanya untuk pemilik lahan."},
            status=403,
        )

    lahan = get_object_or_404(
        Lahan.objects.filter(
            owner=request.user,
            diarsipkan=False,
        ),
        pk=lahan_id,
    )

    hasil_list = HasilPemeriksaan.objects.filter(
        lahan=lahan,
    ).order_by("-tanggal_pemeriksaan", "-dibuat_pada")

    response = JsonResponse({
        "results": [
            {
                "id": hasil.pk,
                "tanggal_pemeriksaan": (
                    hasil.tanggal_pemeriksaan.isoformat()
                ),
                "asal": hasil.get_asal_display(),
                "sumber": hasil.sumber,
            }
            for hasil in hasil_list
        ],
    })

    response["Cache-Control"] = "private, no-store"
    return response