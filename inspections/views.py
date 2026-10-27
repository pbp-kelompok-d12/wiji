from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from lands.views import owner_required

from .forms import PesananForm, lahan_bisa_dipesan
from .models import PesananPemeriksaan
from .pemesanan import buat_pesanan
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


@owner_required
def pesan_pemeriksaan(request):
    # Dari halaman lahan, lahannya sudah terpilih lewat ?lahan=<id>
    awal = {'lahan': request.GET.get('lahan')} if request.method == 'GET' else None
    # Pakai cek method, bukan 'request.POST or None': form kosong yang dikirim juga harus kena validasi
    data = request.POST if request.method == 'POST' else None
    form = PesananForm(data, initial=awal, pemilik=request.user)

    if request.method == 'POST' and form.is_valid():
        try:
            pesanan = buat_pesanan(
                pemilik=request.user,
                lahan=form.cleaned_data['lahan'],
                jenis=form.cleaned_data['jenis'],
                tanggal_usulan=form.cleaned_data['tanggal_usulan'],
                sesi_usulan=form.cleaned_data['sesi_usulan'],
                catatan=form.cleaned_data['catatan'],
            )
        except ValidationError as e:
            form.add_error(None, e)
        else:
            messages.success(request, f'Pesanan {pesanan.kode} sudah diajukan. Admin akan menugaskan petugas.')
            return redirect('inspections:detail_pesanan', pk=pesanan.pk)

    return render(request, 'inspections/form_pesanan.html', {
        'form': form,
        'ada_lahan': lahan_bisa_dipesan(request.user).exists(),
        'active_nav': 'pesanan',
    })
