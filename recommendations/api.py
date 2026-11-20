from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response

from accounts.permissions import API_AUTH, IsPemilik
from lands.models import Lahan, ManagementGoal
from soil_results.models import HasilPemeriksaan

from .models import ManagementPlan
from .serializers import (
    ManagementPlanDetailSerializer,
    ManagementPlanFilterSerializer,
    ManagementPlanListResponseSerializer,
    RecommendationQuerySerializer,
    RecommendationResponseSerializer,
)
from .services import RecommendationInputError, calculate_recommendations


def _invalid(message, details=None):
    payload = {"error": message}
    if details is not None:
        payload["details"] = details
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)


def _not_found(message):
    return Response(
        {"error": message},
        status=status.HTTP_404_NOT_FOUND,
    )


@never_cache
@api_view(["GET"])
@authentication_classes(API_AUTH)
@permission_classes([IsPemilik])
def rekomendasi_lahan(request, lahan_id):
    query = RecommendationQuerySerializer(data=request.query_params)
    if not query.is_valid():
        return _invalid("Parameter hasil dan tujuan wajib valid.", query.errors)

    lahan = Lahan.objects.filter(
        owner=request.user,
        diarsipkan=False,
        pk=lahan_id,
    ).first()
    if lahan is None:
        return _not_found("Lahan tidak ditemukan.")

    hasil = (
        HasilPemeriksaan.objects.select_related("lahan").prefetch_related(
            "nutrient_measurements"
        )
        .filter(
            pk=query.validated_data["hasil"],
            status_hasil=HasilPemeriksaan.StatusHasil.FINAL,
        )
        .first()
    )
    if hasil is None:
        return _not_found("Hasil pemeriksaan tidak ditemukan.")
    if hasil.lahan_id != lahan.pk:
        return _invalid(
            "Hasil pemeriksaan tidak sesuai dengan lahan yang dipilih."
        )

    tujuan = ManagementGoal.objects.filter(
        pk=query.validated_data["tujuan"]
    ).first()
    if tujuan is None:
        return _not_found("Tujuan pengelolaan tidak ditemukan.")
    if not tujuan.aktif:
        return _invalid("Tujuan pengelolaan sudah tidak aktif.")

    try:
        data = calculate_recommendations(
            lahan=lahan,
            hasil_pemeriksaan=hasil,
            tujuan=tujuan,
        )
    except RecommendationInputError as exc:
        return _invalid(str(exc))

    payload = RecommendationResponseSerializer(
        {
            "lahan": lahan,
            "hasil": hasil,
            "tujuan": tujuan,
            **data,
        }
    ).data
    return Response(payload)


@never_cache
@api_view(["GET"])
@authentication_classes(API_AUTH)
@permission_classes([IsPemilik])
def daftar_rencana(request):
    query = ManagementPlanFilterSerializer(data=request.query_params)
    if not query.is_valid():
        return _invalid("Filter status tidak valid.", query.errors)

    plans = ManagementPlan.objects.filter(pemilik=request.user).select_related(
        "lahan",
        "rekomendasi",
        "rekomendasi__tanaman",
        "rekomendasi__tujuan",
    )
    selected_status = query.validated_data.get("status")
    if selected_status:
        plans = plans.filter(status=selected_status)

    payload = ManagementPlanListResponseSerializer({"results": plans}).data
    return Response(payload)


@never_cache
@api_view(["GET"])
@authentication_classes(API_AUTH)
@permission_classes([IsPemilik])
def detail_rencana(request, pk):
    plan = (
        ManagementPlan.objects.select_related(
            "lahan",
            "rekomendasi",
            "rekomendasi__tanaman",
            "rekomendasi__tujuan",
            "rekomendasi__hasil_pemeriksaan",
        )
        .filter(pk=pk, pemilik=request.user)
        .first()
    )
    if plan is None:
        return _not_found("Rencana pengelolaan tidak ditemukan.")
    return Response(ManagementPlanDetailSerializer(plan).data)
