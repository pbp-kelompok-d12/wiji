from django.urls import path

from . import api, views, views_admin

app_name = 'inspections'

urlpatterns = [
    # API JSON (didaftarkan dulu supaya nggak ketabrak pola lain)
    path('api/pesanan/', api.api_pesanan, name='api_pesanan'),
    path('api/pesanan/<int:pk>/', api.api_detail_pesanan, name='api_detail_pesanan'),
    path('api/pesanan/<int:pk>/batalkan/', api.api_batalkan, name='api_batalkan'),
    path('api/pesanan/<int:pk>/jadwal-ulang/', api.api_jadwal_ulang, name='api_jadwal_ulang'),

    # Halaman admin (didaftarkan sebelum pola <int:pk> milik pemilik)
    path('kelola/', views_admin.kelola_daftar, name='kelola_daftar'),
    path('kelola/<int:pk>/', views_admin.kelola_detail, name='kelola_detail'),
    path('kelola/<int:pk>/tugaskan/', views_admin.kelola_tugaskan, name='kelola_tugaskan'),
    path('kelola/<int:pk>/jadwalkan/', views_admin.kelola_jadwalkan, name='kelola_jadwalkan'),
    path('kelola/<int:pk>/ganti-petugas/', views_admin.kelola_ganti_petugas, name='kelola_ganti_petugas'),
    path('kelola/<int:pk>/batalkan/', views_admin.kelola_batalkan, name='kelola_batalkan'),

    path('', views.daftar_pesanan, name='daftar_pesanan'),
    path('pesan/', views.pesan_pemeriksaan, name='pesan_pemeriksaan'),
    path('<int:pk>/', views.detail_pesanan, name='detail_pesanan'),
    path('<int:pk>/ubah/', views.ubah_usulan_pesanan, name='ubah_usulan'),
    path('<int:pk>/batalkan/', views.batalkan_pesanan_view, name='batalkan_pesanan'),
    path('<int:pk>/jadwal-ulang/', views.jadwal_ulang_pesanan, name='jadwal_ulang'),
]
