from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('akun/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('', include('core.urls')),
    path('lahan/', include('lands.urls')),
    path('pemeriksaan/', include('inspections.urls')),
    path('hasil-tanah/', include('soil_results.urls')),
    path('rekomendasi/', include('recommendations.urls')),
]

# API DRF buat aplikasi mobile. Semua di bawah /api/v1/, tiap modul ngisi api_urls.py di app-nya
# sendiri biar nggak rebutan file ini. Endpoint JSON lama (misalnya /lahan/api/) tetap jalan.
urlpatterns += [
    path('api/v1/', include('accounts.api_urls')),
    path('api/v1/', include('lands.api_urls')),
    path('api/v1/', include('inspections.api_urls')),
    path('api/v1/', include('soil_results.api_urls')),
    path('api/v1/', include('core.api_urls')),
    path('api/v1/', include('recommendations.api_urls')),
    # Tombol masuk/keluar di halaman Browsable API DRF (sesinya sama dengan login web)
    path('api-auth/', include('rest_framework.urls')),
]

# Foto lahan (media/) disajikan Django sendiri, baik DEBUG nyala atau mati, karena WhiteNoise cuma
# buat file statis. Dokumen laboratorium ada di private_media/ dan nggak lewat sini.
def sajikan_media(request, path):
    # MEDIA_ROOT dibaca pas ada permintaan (bukan pas impor), jadi gampang diganti di tes
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', sajikan_media),
]
