from django.urls import path

from . import api_views

app_name = "soil_results_api"

urlpatterns = [
    path(
        "hasil/",
        api_views.daftar_hasil,
        name="daftar_hasil",
    ),
    path(
        "hasil/<int:hasil_id>/",
        api_views.detail_hasil,
        name="detail_hasil",
    ),
]