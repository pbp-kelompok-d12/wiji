from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.vary import vary_on_headers

from lands.models import Lahan
from .forms import HasilMandiriForm, NutrientMeasurementForm, DokumenLaboratoriumForm, ContaminantFindingForm
from .models import HasilPemeriksaan, NutrientMeasurement
import uuid
from django.http import FileResponse, Http404, JsonResponse
from django.db.models.deletion import ProtectedError

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
        {
            "hasil": hasil, 
            "terkunci": hasil.dipakai_dalam_rencana(),
        },
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

    if hasil.dipakai_dalam_rencana():
        messages.error(
            request,
            "Hasil sudah digunakan dalam rencana pengelolaan "
            "sehingga tidak dapat diubah atau dihapus.",
        )
        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

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

    if hasil.dipakai_dalam_rencana():
        messages.error(
            request,
            "Hasil sudah digunakan dalam rencana pengelolaan "
            "sehingga tidak dapat diubah atau dihapus.",
        )
        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

    if request.method == "POST":
        lahan_url = hasil.lahan.get_absolute_url()

        try:
            hasil.delete()
        except ProtectedError:
            messages.error(
                request,
                "Hasil tidak dapat dihapus karena sudah digunakan "
                "dalam rekomendasi atau data terkait.",
            )
            return redirect(
                "soil_results:detail_hasil",
                hasil_id=hasil.pk,
            )

        messages.success(request, "Hasil mandiri berhasil dihapus.")
        return redirect(lahan_url)

    return render(
        request,
        "soil_results/konfirmasi_hapus.html",
        {"hasil": hasil},
    )

@login_required
@require_http_methods(["GET", "POST"])
def tambah_unsur_hara(request, hasil_id):
    if not request.user.is_owner:
        raise PermissionDenied(
            "Hanya pemilik lahan yang dapat menambahkan pengukuran."
        )

    hasil = get_object_or_404(
        HasilPemeriksaan.objects.select_related("lahan"),
        pk=hasil_id,
        lahan__owner=request.user,
        lahan__diarsipkan=False,
        asal=HasilPemeriksaan.Asal.MANDIRI,
    )

    if hasil.dipakai_dalam_rencana():
        messages.error(
            request,
            "Hasil sudah digunakan dalam rencana pengelolaan "
            "sehingga tidak dapat diubah atau dihapus.",
        )
        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

    if request.method == "POST":
        form = NutrientMeasurementForm(request.POST)

        if form.is_valid():
            pengukuran = form.save(commit=False)
            pengukuran.hasil = hasil
            pengukuran.save()

            messages.success(request, "Pengukuran unsur hara ditambahkan.")
            return redirect(
                "soil_results:detail_hasil",
                hasil_id=hasil.pk,
            )
    else:
        form = NutrientMeasurementForm()

    return render(
        request,
        "soil_results/form_unsur_hara.html",
        {"form": form, "hasil": hasil},
    )

@login_required
@require_http_methods(["GET", "POST"])
def ubah_unsur_hara(request, pengukuran_id):
    if not request.user.is_owner:
        raise PermissionDenied(
            "Hanya pemilik lahan yang dapat mengubah pengukuran."
        )

    pengukuran = get_object_or_404(
        NutrientMeasurement.objects.select_related("hasil__lahan"),
        pk=pengukuran_id,
        hasil__lahan__owner=request.user,
        hasil__lahan__diarsipkan=False,
        hasil__asal=HasilPemeriksaan.Asal.MANDIRI,
    )
    hasil = pengukuran.hasil

    if hasil.dipakai_dalam_rencana():
        messages.error(
            request,
            "Hasil sudah digunakan dalam rencana pengelolaan "
            "sehingga tidak dapat diubah atau dihapus.",
        )
        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

    if request.method == "POST":
        form = NutrientMeasurementForm(
            request.POST,
            instance=pengukuran,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Pengukuran berhasil diperbarui.")
            return redirect(
                "soil_results:detail_hasil",
                hasil_id=hasil.pk,
            )
    else:
        form = NutrientMeasurementForm(instance=pengukuran)

    return render(
        request,
        "soil_results/form_unsur_hara.html",
        {
            "form": form,
            "hasil": hasil,
            "is_edit": True,
        },
    )

@login_required
@require_http_methods(["GET", "POST"])
def hapus_unsur_hara(request, pengukuran_id):
    if not request.user.is_owner:
        raise PermissionDenied(
            "Hanya pemilik lahan yang dapat menghapus pengukuran."
        )

    pengukuran = get_object_or_404(
        NutrientMeasurement.objects.select_related("hasil__lahan"),
        pk=pengukuran_id,
        hasil__lahan__owner=request.user,
        hasil__lahan__diarsipkan=False,
        hasil__asal=HasilPemeriksaan.Asal.MANDIRI,
    )
    hasil = pengukuran.hasil

    if hasil.dipakai_dalam_rencana():
        messages.error(
            request,
            "Hasil sudah digunakan dalam rencana pengelolaan "
            "sehingga tidak dapat diubah atau dihapus.",
        )
        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

    if request.method == "POST":
        pengukuran.delete()
        messages.success(request, "Pengukuran berhasil dihapus.")
        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

    return render(
        request,
        "soil_results/konfirmasi_hapus_unsur_hara.html",
        {"pengukuran": pengukuran, "hasil": hasil},
    )


@login_required
@require_http_methods(["GET", "POST"])
def unggah_dokumen(request, hasil_id):
    if not request.user.is_owner:
        raise PermissionDenied("Hanya pemilik yang dapat mengunggah dokumen.")

    hasil = get_object_or_404(
        HasilPemeriksaan,
        pk=hasil_id,
        lahan__owner=request.user,
        lahan__diarsipkan=False,
        asal=HasilPemeriksaan.Asal.MANDIRI,
    )

    if hasil.dipakai_dalam_rencana():
        messages.error(
            request,
            "Hasil sudah digunakan dalam rencana pengelolaan "
            "sehingga tidak dapat diubah atau dihapus.",
        )
        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

    if request.method == "POST":
        form = DokumenLaboratoriumForm(request.POST, request.FILES)

        if form.is_valid():
            nama_lama = hasil.dokumen_laboratorium.name
            storage = hasil.dokumen_laboratorium.storage

            hasil.dokumen_laboratorium.save(
                f"{uuid.uuid4().hex}.pdf",
                form.cleaned_data["dokumen"],
                save=False,
            )
            hasil.save()

            if nama_lama and nama_lama != hasil.dokumen_laboratorium.name:
                storage.delete(nama_lama)

            messages.success(request, "Dokumen berhasil diunggah.")
            return redirect("soil_results:detail_hasil", hasil_id=hasil.pk)
    else:
        form = DokumenLaboratoriumForm()

    return render(
        request,
        "soil_results/form_dokumen.html",
        {"form": form, "hasil": hasil},
    )


@login_required
@require_http_methods(["GET"])
def unduh_dokumen(request, hasil_id):
    queryset = HasilPemeriksaan.objects.all()

    if not request.user.is_staff:
        queryset = queryset.filter(lahan__owner=request.user)

    hasil = get_object_or_404(queryset, pk=hasil_id)

    if not hasil.dokumen_laboratorium:
        raise Http404("Dokumen belum tersedia.")

    try:
        berkas = hasil.dokumen_laboratorium.open("rb")
    except FileNotFoundError:
        raise Http404("File dokumen tidak ditemukan.")

    response = FileResponse(
        berkas,
        as_attachment=True,
        filename=f"hasil-pemeriksaan-{hasil.pk}.pdf",
        content_type="application/pdf",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@require_http_methods(["GET"])
def daftar_hasil(request):
    hasil_list = (
        HasilPemeriksaan.objects
        .filter(lahan__owner=request.user)
        .select_related("lahan")
    )

    pencarian = request.GET.get("q", "").strip()
    asal = request.GET.get("asal", "")

    if pencarian:
        hasil_list = hasil_list.filter(lahan__nama__icontains=pencarian)

    if asal in HasilPemeriksaan.Asal.values:
        hasil_list = hasil_list.filter(asal=asal)

    return render(
        request,
        "soil_results/daftar_hasil.html",
        {
            "hasil_list": hasil_list,
            "pencarian": pencarian,
            "asal": asal,
        },
    )


@login_required
@require_http_methods(["GET"])
@vary_on_headers("HX-Request")
def daftar_hasil(request):
    hasil_list = (
        HasilPemeriksaan.objects
        .filter(lahan__owner=request.user)
        .select_related("lahan")
    )

    pencarian = request.GET.get("q", "").strip()
    asal = request.GET.get("asal", "")

    if pencarian:
        hasil_list = hasil_list.filter(
            lahan__nama__icontains=pencarian,
        )

    if asal in HasilPemeriksaan.Asal.values:
        hasil_list = hasil_list.filter(asal=asal)

    context = {
        "hasil_list": hasil_list,
        "pencarian": pencarian,
        "asal": asal,
    }

    if request.headers.get("HX-Request") == "true":
        template = "soil_results/partials/daftar_hasil_items.html"
    else:
        template = "soil_results/daftar_hasil.html"

    return render(request, template, context)


def hasil_ke_dict(hasil):
    return {
        "id": hasil.pk,
        "lahan": {
            "id": str(hasil.lahan_id),
            "nama": hasil.lahan.nama,
        },
        "asal": hasil.asal,
        "sumber": hasil.sumber,
        "tanggal_pemeriksaan": hasil.tanggal_pemeriksaan.isoformat(),
        "ph": hasil.ph,
        "kelembapan": hasil.kelembapan,
        "tekstur": hasil.tekstur,
        "bahan_organik": hasil.bahan_organik,
        "catatan": hasil.catatan,
        "ada_dokumen": bool(hasil.dokumen_laboratorium),
        "pengukuran_unsur_hara": [
            {
                "id": item.pk,
                "nama_unsur": item.nama_unsur,
                "nilai": item.nilai,
                "satuan": item.satuan,
                "metode": item.metode,
            }
            for item in hasil.nutrient_measurements.all()
        ],
    }


@require_http_methods(["GET"])
def api_daftar_hasil(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "Silakan login terlebih dahulu."},
            status=401,
        )

    hasil_list = (
        HasilPemeriksaan.objects
        .filter(lahan__owner=request.user)
        .select_related("lahan")
        .prefetch_related("nutrient_measurements")
    )

    pencarian = request.GET.get("q", "").strip()
    asal = request.GET.get("asal", "")

    if pencarian:
        hasil_list = hasil_list.filter(lahan__nama__icontains=pencarian)

    if asal in HasilPemeriksaan.Asal.values:
        hasil_list = hasil_list.filter(asal=asal)

    response = JsonResponse({
        "results": [hasil_ke_dict(hasil) for hasil in hasil_list],
    })
    response["Cache-Control"] = "private, no-store"
    return response


@require_http_methods(["GET"])
def api_detail_hasil(request, hasil_id):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "Silakan login terlebih dahulu."},
            status=401,
        )

    hasil = (
        HasilPemeriksaan.objects
        .filter(pk=hasil_id, lahan__owner=request.user)
        .select_related("lahan")
        .prefetch_related("nutrient_measurements")
        .first()
    )

    if hasil is None:
        return JsonResponse(
            {"error": "Hasil tidak ditemukan."},
            status=404,
        )

    response = JsonResponse(hasil_ke_dict(hasil))
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_http_methods(["GET", "POST"])
def tambah_kontaminan(request, hasil_id):
    if not request.user.is_owner:
        raise PermissionDenied(
            "Hanya pemilik lahan yang dapat menambahkan temuan."
        )

    hasil = get_object_or_404(
        HasilPemeriksaan.objects.select_related("lahan"),
        pk=hasil_id,
        lahan__owner=request.user,
        lahan__diarsipkan=False,
        asal=HasilPemeriksaan.Asal.MANDIRI,
    )

    if hasil.dipakai_dalam_rencana():
        messages.error(
            request,
            "Hasil sudah digunakan dalam rencana "
            "sehingga temuan tidak dapat ditambahkan.",
        )
        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

    if request.method == "POST":
        form = ContaminantFindingForm(
            request.POST,
            hasil=hasil,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Temuan kontaminan ditambahkan.")
            return redirect(
                "soil_results:detail_hasil",
                hasil_id=hasil.pk,
            )
    else:
        form = ContaminantFindingForm(hasil=hasil)

    return render(
        request,
        "soil_results/form_kontaminan.html",
        {"form": form, "hasil": hasil},
    )