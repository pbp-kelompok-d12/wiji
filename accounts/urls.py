from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('masuk/', views.WijiLoginView.as_view(), name='login'),
    path('keluar/', views.WijiLogoutView.as_view(), name='logout'),
    path('daftar/', views.register, name='register'),
    path('daftar/cek-username/', views.check_username, name='check_username'),
]
