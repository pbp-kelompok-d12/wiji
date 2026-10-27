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