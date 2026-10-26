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
]