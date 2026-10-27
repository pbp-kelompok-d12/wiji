from django.urls import path
from . import views

app_name = "soil_results"

urlpatterns = [
    path(
        "lahan/<uuid:lahan_id>/mandiri/tambah/",
        views.tambah_hasil_mandiri,
        name="tambah_hasil_mandiri",
    ),
    path(
        "<int:hasil_id>/",
        views.detail_hasil,
        name="detail_hasil",
    ),
    path(
        "<int:hasil_id>/ubah/",
        views.ubah_hasil_mandiri,
        name="ubah_hasil_mandiri",
    ),
    path(
        "<int:hasil_id>/hapus/",
        views.hapus_hasil_mandiri,
        name="hapus_hasil_mandiri",
    ),
    path(
        "<int:hasil_id>/unsur-hara/tambah/",
        views.tambah_unsur_hara,
        name="tambah_unsur_hara",
    ),
    path(
        "unsur-hara/<int:pengukuran_id>/ubah/",
        views.ubah_unsur_hara,
        name="ubah_unsur_hara",
    ),
    path(
        "unsur-hara/<int:pengukuran_id>/hapus/",
        views.hapus_unsur_hara,
        name="hapus_unsur_hara",
    ),
    path(
        "<int:hasil_id>/dokumen/unggah/",
        views.unggah_dokumen,
        name="unggah_dokumen",
    ),
    path(
        "<int:hasil_id>/dokumen/unduh/",
        views.unduh_dokumen,
        name="unduh_dokumen",
    ),
]