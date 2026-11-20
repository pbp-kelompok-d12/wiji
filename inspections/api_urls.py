"""Endpoint DRF Modul B (pemesanan pemeriksaan) di bawah /api/v1/.

Daftar endpoint lengkapnya ada di docs/WORK-PLAN.md repo wiji-mobile.
Batal, jadwal ulang, sama tugas petugas nyusul setelah Checkpoint 1.
"""
from django.urls import path

from . import api_views

app_name = 'inspections_api'

urlpatterns = [
    path('jenis-pemeriksaan/', api_views.daftar_jenis, name='jenis'),
    path('pesanan/', api_views.daftar_pesanan, name='pesanan'),
    path('pesanan/<int:pk>/', api_views.detail_pesanan, name='detail_pesanan'),
]
