from django.urls import path

from . import views

app_name = 'inspections'

urlpatterns = [
    path('', views.daftar_pesanan, name='daftar_pesanan'),
    path('<int:pk>/', views.detail_pesanan, name='detail_pesanan'),
]
