from django.urls import path

from . import views

app_name = "recommendations"

urlpatterns = [
    path("", views.daftar_rekomendasi, name="daftar_rekomendasi"),
]