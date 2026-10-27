from django.urls import path

from . import api, views

app_name = 'inspections'

urlpatterns = [
    # API JSON (didaftarkan dulu supaya nggak ketabrak pola lain)
    path('api/pesanan/', api.api_pesanan, name='api_pesanan'),
    path('api/pesanan/<int:pk>/', api.api_detail_pesanan, name='api_detail_pesanan'),
    path('api/pesanan/<int:pk>/batalkan/', api.api_batalkan, name='api_batalkan'),
    path('api/pesanan/<int:pk>/jadwal-ulang/', api.api_jadwal_ulang, name='api_jadwal_ulang'),

    path('', views.daftar_pesanan, name='daftar_pesanan'),
    path('pesan/', views.pesan_pemeriksaan, name='pesan_pemeriksaan'),
    path('<int:pk>/', views.detail_pesanan, name='detail_pesanan'),
    path('<int:pk>/ubah/', views.ubah_usulan_pesanan, name='ubah_usulan'),
    path('<int:pk>/batalkan/', views.batalkan_pesanan_view, name='batalkan_pesanan'),
    path('<int:pk>/jadwal-ulang/', views.jadwal_ulang_pesanan, name='jadwal_ulang'),
]
