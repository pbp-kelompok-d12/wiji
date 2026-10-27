from django.shortcuts import get_object_or_404, render

from lands.views import owner_required

from .models import PesananPemeriksaan
from .tampilan import langkah_status


def _pesanan_pemilik(request):
    """Cuma pesanan buat lahan milik pengguna yang lagi masuk."""
    return PesananPemeriksaan.objects.filter(lahan__owner=request.user).select_related(
        'lahan', 'jenis', 'petugas',
    )


@owner_required
def daftar_pesanan(request):
    return render(request, 'inspections/daftar_pesanan.html', {
        'pesanan_list': _pesanan_pemilik(request),
        'active_nav': 'pesanan',
    })


@owner_required
def detail_pesanan(request, pk):
    pesanan = get_object_or_404(_pesanan_pemilik(request), pk=pk)
    return render(request, 'inspections/detail_pesanan.html', {
        'pesanan': pesanan,
        'langkah': langkah_status(pesanan),
        # Linimasa: yang terbaru di atas
        'riwayat': pesanan.riwayat.select_related('oleh').order_by('-dibuat_pada', '-id'),
        'active_nav': 'pesanan',
    })
