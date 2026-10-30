from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.vary import vary_on_headers

from lands.models import Lahan
from .forms import HasilMandiriForm, NutrientMeasurementForm, DokumenLaboratoriumForm, ContaminantFindingForm
from .models import HasilPemeriksaan, NutrientMeasurement, ContaminantFinding
import uuid
from django.http import FileResponse, Http404, JsonResponse
from django.db.models.deletion import ProtectedError
from django.db import transaction
from inspections.models import PesananPemeriksaan
from .forms import HasilPetugasForm
from django.db.models import Q
from .permissions import (
    boleh_mengelola_hasil,
    pastikan_boleh_mengelola,
)
from .services import finalkan_hasil_petugas

def hasil_yang_bisa_dibaca(user):
    queryset = HasilPemeriksaan.objects.select_related(
        "lahan",
        "pesanan",
    )

    if user.is_staff:
        return queryset

    akses = Q(
        lahan__owner=user,
        status_hasil=HasilPemeriksaan.StatusHasil.FINAL,
    )

    if user.is_officer:
        akses |= Q(
            asal=HasilPemeriksaan.Asal.WIJI,
            pesanan__petugas=user,
        )

    return queryset.filter(akses)


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
        hasil_yang_bisa_dibaca(request.user),
        pk=hasil_id,
    )

    return render(
        request,
        "soil_results/detail_hasil.html",
        {
            "hasil": hasil, 
            "terkunci": hasil.dipakai_dalam_rencana(),
            "boleh_kelola": boleh_mengelola_hasil(
                request.user,
                hasil,
            ),
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
    hasil = get_object_or_404(
        hasil_yang_bisa_dibaca(request.user),
        pk=hasil_id,
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
    
    pastikan_boleh_mengelola(request.user, hasil)

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
    pengukuran = get_object_or_404(
        NutrientMeasurement.objects.select_related("hasil__lahan", "hasil__pesanan"),
        pk=pengukuran_id,
        hasil__in=hasil_yang_bisa_dibaca(request.user),
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

    pastikan_boleh_mengelola(request.user, hasil)

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
    pengukuran = get_object_or_404(
        NutrientMeasurement.objects.select_related("hasil__lahan", "hasil__pesanan",),
        pk=pengukuran_id,
        hasil__in=hasil_yang_bisa_dibaca(request.user),
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

    pastikan_boleh_mengelola(request.user, hasil)

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
    hasil = get_object_or_404(
        hasil_yang_bisa_dibaca(request.user),
        pk=hasil_id,
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

    pastikan_boleh_mengelola(request.user, hasil)

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
    hasil = get_object_or_404(
        hasil_yang_bisa_dibaca(request.user),
        pk=hasil_id,
    )

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
@vary_on_headers("HX-Request")
def daftar_hasil(request):
    hasil_list = (
        HasilPemeriksaan.objects
        .filter(lahan__owner=request.user,
                status_hasil=HasilPemeriksaan.StatusHasil.FINAL,    )
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
        "status_hasil": hasil.status_hasil,
        "pesanan_id": hasil.pesanan_id,
        "difinalkan_pada": (
            hasil.difinalkan_pada.isoformat()
            if hasil.difinalkan_pada
            else None
        ),
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
                "temuan_kontaminan": [
            {
                "id": temuan.pk,
                "kontaminan": {
                    "id": temuan.kontaminan_id,
                    "nama": temuan.kontaminan.nama,
                },
                "status": temuan.status,
                "nilai": temuan.nilai,
                "satuan": temuan.satuan,
                "batas_deteksi": temuan.batas_deteksi,
                "metode": temuan.metode,
                "catatan": temuan.catatan,
            }
            for temuan in hasil.contaminant_findings.all()
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
        hasil_yang_bisa_dibaca(request.user)
        .prefetch_related(
            "nutrient_measurements",
            "contaminant_findings__kontaminan",
        )
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
        hasil_yang_bisa_dibaca(request.user)
        .filter(pk=hasil_id)
        .prefetch_related(
            "nutrient_measurements",
            "contaminant_findings__kontaminan",
        )
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
    hasil = get_object_or_404(
        hasil_yang_bisa_dibaca(request.user),
        pk=hasil_id,
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

    pastikan_boleh_mengelola(request.user, hasil)

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


@login_required
@require_http_methods(["GET", "POST"])
def ubah_kontaminan(request, temuan_id):
    temuan = get_object_or_404(
        ContaminantFinding.objects.select_related(
            "hasil__lahan",
            "hasil__pesanan",
            "kontaminan",
        ),
        pk=temuan_id,
        hasil__in=hasil_yang_bisa_dibaca(request.user),
    )
    hasil = temuan.hasil

    if hasil.dipakai_dalam_rencana():
        messages.error(
            request,
            "Hasil sudah digunakan dalam rencana "
            "sehingga temuan tidak dapat diubah.",
        )
        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

    pastikan_boleh_mengelola(request.user, hasil)

    if request.method == "POST":
        form = ContaminantFindingForm(
            request.POST,
            hasil=hasil,
            instance=temuan,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Temuan kontaminan diperbarui.")
            return redirect(
                "soil_results:detail_hasil",
                hasil_id=hasil.pk,
            )
    else:
        form = ContaminantFindingForm(
            hasil=hasil,
            instance=temuan,
        )

    return render(
        request,
        "soil_results/form_kontaminan.html",
        {
            "form": form,
            "hasil": hasil,
            "is_edit": True,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def hapus_kontaminan(request, temuan_id):
    temuan = get_object_or_404(
        ContaminantFinding.objects.select_related(
            "hasil__lahan",
            "hasil__pesanan",
            "kontaminan",
        ),
        pk=temuan_id,
        hasil__in=hasil_yang_bisa_dibaca(request.user),
    )
    hasil = temuan.hasil

    if hasil.dipakai_dalam_rencana():
        messages.error(
            request,
            "Hasil sudah digunakan dalam rencana "
            "sehingga temuan tidak dapat dihapus.",
        )
        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

    pastikan_boleh_mengelola(request.user, hasil)

    if request.method == "POST":
        temuan.delete()
        messages.success(request, "Temuan kontaminan berhasil dihapus.")
        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

    return render(
        request,
        "soil_results/konfirmasi_hapus_kontaminan.html",
        {"temuan": temuan, "hasil": hasil},
    )


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def isi_hasil_petugas(request, pesanan_id):
    if not request.user.is_officer:
        raise PermissionDenied(
            "Halaman ini hanya untuk petugas pemeriksa."
        )

    pesanan = get_object_or_404(
        PesananPemeriksaan.objects.select_for_update(),
        pk=pesanan_id,
        petugas=request.user,
        status=PesananPemeriksaan.Status.DIPROSES,
    )

    hasil = HasilPemeriksaan.objects.filter(
        pesanan=pesanan,
    ).first()

    if hasil is not None and (
        hasil.status_hasil != HasilPemeriksaan.StatusHasil.DRAF
        or hasil.asal != HasilPemeriksaan.Asal.WIJI
    ):
        raise PermissionDenied(
            "Hasil ini tidak dapat diubah melalui pengisian draf."
        )

    if hasil is None:
        hasil = HasilPemeriksaan(
            pesanan=pesanan,
            lahan=pesanan.lahan,
            dibuat_oleh=request.user,
            asal=HasilPemeriksaan.Asal.WIJI,
            status_hasil=HasilPemeriksaan.StatusHasil.DRAF,
            sumber="Pemeriksaan Wiji",
        )

    if request.method == "POST":
        form = HasilPetugasForm(request.POST, instance=hasil)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Draf berhasil disimpan. Hasil belum ditampilkan kepada pemilik.",
            )
            return redirect(
                "soil_results:detail_hasil",
                hasil_id=hasil.pk,
            )
    else:
        form = HasilPetugasForm(instance=hasil)

    return render(
        request,
        "soil_results/form_hasil_petugas.html",
        {
            "form": form,
            "hasil": hasil,
            "pesanan": pesanan,
        },
    )

@login_required
@require_http_methods(["GET", "POST"])
def finalisasi_hasil(request, hasil_id):
    hasil = get_object_or_404(
        hasil_yang_bisa_dibaca(request.user),
        pk=hasil_id,
        asal=HasilPemeriksaan.Asal.WIJI,
    )
    pastikan_boleh_mengelola(request.user, hasil)

    if request.method == "POST":
        try:
            hasil = finalkan_hasil_petugas(
                hasil_id=hasil.pk,
                user=request.user,
            )
        except ValidationError as exc:
            for pesan in exc.messages:
                messages.error(request, pesan)
        else:
            messages.success(
                request,
                "Hasil berhasil difinalkan. Pesanan telah selesai.",
            )

        return redirect(
            "soil_results:detail_hasil",
            hasil_id=hasil.pk,
        )

    return render(
        request,
        "soil_results/konfirmasi_finalisasi.html",
        {"hasil": hasil},
    )