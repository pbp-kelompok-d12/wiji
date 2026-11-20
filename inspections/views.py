from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from lands.views import owner_required

from .aksi import jalankan_aksi
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


# Pilihan filter di daftar: kunci -> (label, daftar status). None = semua status.
FILTER_STATUS = {
    'semua': ('Semua', None),
    'berjalan': ('Berjalan', [s for s in PesananPemeriksaan.Status.values if s not in ('selesai', 'dibatalkan')]),
    'selesai': ('Selesai', ['selesai']),
    'dibatalkan': ('Dibatalkan', ['dibatalkan']),
}


@owner_required
def daftar_pesanan(request):
    semua = _pesanan_pemilik(request)
    kunci = request.GET.get('status', 'semua')
    if kunci not in FILTER_STATUS:
        kunci = 'semua'
    daftar_status = FILTER_STATUS[kunci][1]
    pesanan_list = semua.filter(status__in=daftar_status) if daftar_status else semua

    konteks = {
        'pesanan_list': pesanan_list,
        'filter_aktif': kunci,
        'filter_list': [
            {'kunci': k, 'label': label, 'jumlah': semua.filter(status__in=st).count() if st else semua.count()}
            for k, (label, st) in FILTER_STATUS.items()
        ],
        'active_nav': 'pesanan',
    }
    # Dari filter HTMX, cukup kirim bagian daftarnya saja
    if request.headers.get('HX-Request') == 'true':
        return render(request, 'inspections/partials/_daftar.html', konteks)
    return render(request, 'inspections/daftar_pesanan.html', konteks)


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


def _jalankan_aksi(request, pk, **kwargs):
    """Aksi pemilik. Kerangka form dan HTMX-nya ada di aksi.py."""
    pesanan = get_object_or_404(_pesanan_pemilik(request), pk=pk)
    return jalankan_aksi(
        request, pesanan, segarkan=lambda: get_object_or_404(_pesanan_pemilik(request), pk=pk),
        konteks_detail=_konteks_detail, templat_isi='inspections/partials/_isi_detail.html',
        nama_url_detail='inspections:detail_pesanan', active_nav='pesanan', **kwargs,
    )


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
