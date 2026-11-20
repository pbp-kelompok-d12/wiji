"""API DRF Modul B (pemesanan pemeriksaan) di /api/v1/, buat aplikasi mobile.

Endpoint JSON lama di api.py tetap ada dan tetap dipakai web.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import API_AUTH, IsPemilik

from .models import JenisPemeriksaan, PesananPemeriksaan
from .serializers import (
    JenisPemeriksaanSerializer,
    PesananBaruSerializer,
    PesananDetailSerializer,
    PesananSerializer,
)


def _pesanan_pemilik(request):
    # Pemilik cuma boleh liat pesanan buat lahannya sendiri. Pesanan orang lain jadi 404, bukan 403.
    return PesananPemeriksaan.objects.filter(lahan__owner=request.user).select_related(
        'lahan', 'jenis', 'petugas',
    )


@api_view(['GET'])
@authentication_classes(API_AUTH)
@permission_classes([IsAuthenticated])
def daftar_jenis(request):
    """Pilihan jenis pemeriksaan buat form pesan. Yang nggak aktif nggak ikut."""
    jenis = JenisPemeriksaan.objects.filter(aktif=True)
    return Response(JenisPemeriksaanSerializer(jenis, many=True).data)


@api_view(['GET', 'POST'])
@authentication_classes(API_AUTH)
@permission_classes([IsPemilik])
def daftar_pesanan(request):
    """GET: pesanan milik pemilik (boleh ?status=diajukan). POST: pesan pemeriksaan baru."""
    if request.method == 'GET':
        pesanan = _pesanan_pemilik(request)
        status_dicari = request.query_params.get('status', '').strip()
        if status_dicari:
            pesanan = pesanan.filter(status=status_dicari)
        return Response(PesananSerializer(pesanan, many=True).data)

    serializer = PesananBaruSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    pesanan = serializer.save()
    return Response(PesananDetailSerializer(pesanan).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes(API_AUTH)
@permission_classes([IsPemilik])
def detail_pesanan(request, pk):
    pesanan = get_object_or_404(
        _pesanan_pemilik(request).prefetch_related('riwayat__oleh'), pk=pk,
    )
    return Response(PesananDetailSerializer(pesanan).data)
