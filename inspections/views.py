from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from lands.views import owner_required

from .forms import BatalkanForm, JadwalUlangForm, PesananForm, UbahUsulanForm, lahan_bisa_dipesan
from .models import PesananPemeriksaan
from .pemesanan import (
    STATUS_BISA_BATAL, STATUS_BISA_JADWAL_ULANG, ajukan_jadwal_ulang, batalkan_pesanan,
    buat_pesanan, ubah_usulan,
)
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


def _konteks_detail(pesanan):
    """Bahan buat halaman detail. Tombol aksi cuma muncul kalau statusnya masih mengizinkan."""
    return {
        'pesanan': pesanan,
        'langkah': langkah_status(pesanan),
        # Linimasa: yang terbaru di atas
        'riwayat': pesanan.riwayat.select_related('oleh').order_by('-dibuat_pada', '-id'),
        'bisa_ubah': pesanan.status == PesananPemeriksaan.Status.DIAJUKAN,
        'bisa_batal': pesanan.status in STATUS_BISA_BATAL,
        'bisa_jadwal_ulang': pesanan.status in STATUS_BISA_JADWAL_ULANG,
        'active_nav': 'pesanan',
    }


@owner_required
def detail_pesanan(request, pk):
    pesanan = get_object_or_404(_pesanan_pemilik(request), pk=pk)
    return render(request, 'inspections/detail_pesanan.html', _konteks_detail(pesanan))


def _jalankan_aksi(request, pk, *, form_class, jalankan, judul, deskripsi, label_kirim,
                   pesan_sukses, awal=None, bahaya=False):
    """Kerangka bareng buat aksi pemilik (ubah usulan, batalkan, jadwal ulang).

    Dari halaman detail, formnya muncul sebagai modal lewat HTMX. Kalau JavaScript mati,
    alamat yang sama tetap jalan sebagai halaman biasa.
    """
    pesanan = get_object_or_404(_pesanan_pemilik(request), pk=pk)
    lewat_htmx = request.headers.get('HX-Request') == 'true'
    data = request.POST if request.method == 'POST' else None
    form = form_class(data, initial=awal(pesanan) if awal else None)

    if request.method == 'POST' and form.is_valid():
        try:
            jalankan(pesanan, request.user, form.cleaned_data)
        except ValidationError as e:
            form.add_error(None, e)
        else:
            pesanan = get_object_or_404(_pesanan_pemilik(request), pk=pk)
            if lewat_htmx:
                # Isi detail diganti, modalnya ditutup lewat elemen "oob"
                return render(request, 'inspections/partials/_hasil_aksi.html', {
                    **_konteks_detail(pesanan), 'pesan_sukses': pesan_sukses,
                })
            messages.success(request, pesan_sukses)
            return redirect('inspections:detail_pesanan', pk=pesanan.pk)

    konteks = {
        'form': form, 'pesanan': pesanan, 'judul': judul, 'deskripsi': deskripsi,
        'label_kirim': label_kirim, 'bahaya': bahaya, 'aksi_url': request.path,
        'active_nav': 'pesanan',
    }
    if lewat_htmx:
        respons = render(request, 'inspections/partials/_modal_aksi.html', konteks)
        if request.method == 'POST':
            # Gagal validasi: tampilkan lagi di modal, bukan di tempat isi detail
            respons['HX-Retarget'] = '#modal-slot'
            respons['HX-Reswap'] = 'innerHTML'
        return respons
    return render(request, 'inspections/form_aksi.html', konteks)


@owner_required
def ubah_usulan_pesanan(request, pk):
    return _jalankan_aksi(
        request, pk, form_class=UbahUsulanForm,
        jalankan=lambda p, user, d: ubah_usulan(p, d['tanggal'], d['sesi'], d['catatan']),
        awal=lambda p: {'tanggal': p.tanggal_usulan, 'sesi': p.sesi_usulan, 'catatan': p.catatan},
        judul='Ubah usulan',
        deskripsi='Tanggal, sesi, dan catatan masih bisa diubah selama pesanan Diajukan.',
        label_kirim='Simpan perubahan', pesan_sukses='Usulan pesanan sudah diperbarui.',
    )


@owner_required
def batalkan_pesanan_view(request, pk):
    return _jalankan_aksi(
        request, pk, form_class=BatalkanForm,
        jalankan=lambda p, user, d: batalkan_pesanan(p, user, d['alasan']),
        judul='Batalkan pesanan?',
        deskripsi='Pesanan tetap tersimpan di riwayat dan nggak bisa dibuka lagi.',
        label_kirim='Batalkan pesanan', pesan_sukses='Pesanan dibatalkan.', bahaya=True,
    )


@owner_required
def jadwal_ulang_pesanan(request, pk):
    return _jalankan_aksi(
        request, pk, form_class=JadwalUlangForm,
        jalankan=lambda p, user, d: ajukan_jadwal_ulang(p, user, d['tanggal'], d['sesi'], d['alasan']),
        judul='Minta jadwal ulang',
        deskripsi='Petugas tetap sama. Jadwal final dikosongkan dan admin menetapkan jadwal barunya.',
        label_kirim='Kirim permintaan',
        pesan_sukses='Permintaan jadwal ulang terkirim. Admin akan menetapkan jadwal baru.',
    )


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
