from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing, name='landing'),

    #CRUD 4 (Katalog Tanaman)
    path('katalog/', views.daftar_tanaman, name='daftar_tanaman'),
    path('katalog/api/', views.api_tanaman, name='api_tanaman'),
    path('katalog/api/<int:pk>/', views.api_detail_tanaman, name='api_detail_tanaman'),
    path('katalog/tambah/', views.tambah_tanaman, name='tambah_tanaman'),
    path('katalog/<int:pk>/', views.detail_tanaman, name='detail_tanaman'),
    path('katalog/<int:pk>/ubah/', views.ubah_tanaman, name='ubah_tanaman'),
    path('katalog/<int:pk>/arsip/', views.arsip_tanaman, name='arsip_tanaman'),
    path('katalog/<int:pk>/pulihkan/', views.pulihkan_tanaman, name='pulihkan_tanaman'),
    path('katalog/<int:pk>/hapus/', views.hapus_tanaman, name='hapus_tanaman'),
]
