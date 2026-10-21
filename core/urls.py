from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing, name='landing'),

    #CRUD 4 (Katalog Tanaman)
    path('katalog/', views.daftar_tanaman, name='daftar_tanaman'),
    path('katalog/tambah/', views.tambah_tanaman, name='tambah_tanaman'),
    path('katalog/<int:pk>/', views.detail_tanaman, name='detail_tanaman'),
    path('katalog/<int:pk>/ubah/', views.ubah_tanaman, name='ubah_tanaman'),
    path('katalog/<int:pk>/hapus/', views.hapus_tanaman, name='hapus_tanaman'),
]
