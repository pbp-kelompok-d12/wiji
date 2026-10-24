from django.urls import path

from . import views

app_name = 'lands'

urlpatterns = [
    path('', views.daftar_lahan, name='daftar_lahan'),
    path('tambah/', views.tambah_lahan, name='tambah_lahan'),
    path('api/cari-lokasi/', views.cari_lokasi, name='cari_lokasi'),
    path('api/reverse-lokasi/', views.reverse_lokasi, name='reverse_lokasi'),
    path('api/', views.api_lahan, name='api_lahan'),
    path('api/<uuid:pk>/', views.api_detail_lahan, name='api_detail_lahan'),
    path('<uuid:pk>/', views.detail_lahan, name='detail_lahan'),
    path('<uuid:pk>/ubah/', views.ubah_lahan, name='ubah_lahan'),
    path('<uuid:pk>/arsip/', views.arsip_lahan, name='arsip_lahan'),
    path('<uuid:pk>/pulihkan/', views.pulihkan_lahan, name='pulihkan_lahan'),
    path('<uuid:pk>/hapus/', views.hapus_lahan, name='hapus_lahan'),
]
