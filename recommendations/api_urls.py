from django.urls import path

from . import api

app_name = "recommendations_api"

urlpatterns = [
    path(
        "lahan/<uuid:lahan_id>/rekomendasi/",
        api.rekomendasi_lahan,
        name="rekomendasi_lahan",
    ),
    path("rencana/", api.daftar_rencana, name="daftar_rencana"),
    path("rencana/<int:pk>/", api.detail_rencana, name="detail_rencana"),
]
