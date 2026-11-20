from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.response import Response

from accounts.permissions import (
    API_AUTH,
    IsAdminWiji,
    IsPemilik,
    IsPetugas,
)
from .models import HasilPemeriksaan
from .serializers import (
    DetailHasilPemeriksaanSerializer,
    HasilPemeriksaanSerializer,
)
from .views import hasil_yang_bisa_dibaca


class FilterHasilSerializer(serializers.Serializer):
    lahan = serializers.UUIDField(required=False)
    asal = serializers.ChoiceField(
        choices=HasilPemeriksaan.Asal.choices,
        required=False,
    )


@api_view(["GET"])
@authentication_classes(API_AUTH)
@permission_classes([IsPemilik | IsPetugas | IsAdminWiji])
def daftar_hasil(request):
    filter_form = FilterHasilSerializer(data=request.query_params)
    filter_form.is_valid(raise_exception=True)

    # Pakai aturan akses yang sama dengan halaman web.
    hasil_list = hasil_yang_bisa_dibaca(request.user)

    lahan_id = filter_form.validated_data.get("lahan")
    asal = filter_form.validated_data.get("asal")

    if lahan_id is not None:
        hasil_list = hasil_list.filter(lahan_id=lahan_id)

    if asal is not None:
        hasil_list = hasil_list.filter(asal=asal)

    serializer = HasilPemeriksaanSerializer(
        hasil_list,
        many=True,
    )
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes(API_AUTH)
@permission_classes([IsPemilik | IsPetugas | IsAdminWiji])
def detail_hasil(request, hasil_id):
    queryset = hasil_yang_bisa_dibaca(
        request.user,
    ).prefetch_related(
        "nutrient_measurements",
        "contaminant_findings__kontaminan",
    )

    hasil = get_object_or_404(queryset, pk=hasil_id)

    serializer = DetailHasilPemeriksaanSerializer(hasil)
    return Response(serializer.data)