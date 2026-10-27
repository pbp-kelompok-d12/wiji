from django.urls import path

from . import views

app_name = "recommendations"

urlpatterns = [
    path("", views.daftar_rekomendasi, name="daftar_rekomendasi"),
    path("rencana/", views.daftar_rencana, name="daftar_rencana"),
    path("rencana/buat/", views.buat_rencana, name="buat_rencana"),
    path("rencana/<int:pk>/", views.detail_rencana, name="detail_rencana"),
    path("rencana/<int:pk>/edit/", views.edit_rencana, name="edit_rencana"),
    path("rencana/<int:pk>/hapus/", views.hapus_rencana, name="hapus_rencana"),
]