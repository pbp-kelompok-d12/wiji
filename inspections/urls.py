from django.urls import path

from . import views

app_name = 'inspections'

urlpatterns = [
    path('', views.daftar_pesanan, name='daftar_pesanan'),
    path('pesan/', views.pesan_pemeriksaan, name='pesan_pemeriksaan'),
    path('<int:pk>/', views.detail_pesanan, name='detail_pesanan'),
    path('<int:pk>/ubah/', views.ubah_usulan_pesanan, name='ubah_usulan'),
    path('<int:pk>/batalkan/', views.batalkan_pesanan_view, name='batalkan_pesanan'),
    path('<int:pk>/jadwal-ulang/', views.jadwal_ulang_pesanan, name='jadwal_ulang'),
]
