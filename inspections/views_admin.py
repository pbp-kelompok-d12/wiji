"""Halaman admin buat ngelola semua pesanan pemeriksaan (bukan Django Admin)."""
import re

from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .aksi import jalankan_aksi
from .akses import admin_required, pesanan_untuk
from .forms import BatalkanForm, JadwalFinalForm, TugaskanForm
from .models import PesananPemeriksaan
from .pemesanan import STATUS_BISA_BATAL, batalkan_pesanan
from .services import STATUS_BISA_GANTI_PETUGAS, ganti_petugas, jadwalkan_pesanan, konfirmasi_pesanan
from .tampilan import langkah_status

Status = PesananPemeriksaan.Status

# Pilihan filter: kunci -> (label, daftar status). None = semua status.
FILTER_KELOLA = {
    'semua': ('Semua', None),
    'perlu': ('Perlu ditugaskan', [Status.DIAJUKAN]),
    'berjalan': ('Berjalan', [s for s in Status.values if s not in ('diajukan', 'selesai', 'dibatalkan')]),
    'selesai': ('Selesai', [Status.SELESAI]),
    'dibatalkan': ('Dibatalkan', [Status.DIBATALKAN]),
}


def _cari(queryset, q):
    """Cari lewat kode pesanan (WJ-0012), nama lahan, atau nama pemilik."""
    q = q.strip()
    if not q:
        return queryset
    kode = re.fullmatch(r'(?i)wj-?0*(\d+)', q)
    if kode:
        return queryset.filter(pk=int(kode.group(1)))
    return queryset.filter(
        Q(lahan__nama__icontains=q)
        | Q(lahan__owner__username__icontains=q)
        | Q(lahan__owner__first_name__icontains=q)
    )


@admin_required
def kelola_daftar(request):
    q = request.GET.get('q', '')
    dasar = _cari(pesanan_untuk(request.user), q)
    kunci = request.GET.get('status', 'semua')
    if kunci not in FILTER_KELOLA:
        kunci = 'semua'
    daftar_status = FILTER_KELOLA[kunci][1]

    konteks = {
        'pesanan_list': dasar.filter(status__in=daftar_status) if daftar_status else dasar,
        'filter_aktif': kunci,
        'filter_list': [
            {'kunci': k, 'label': label, 'jumlah': dasar.filter(status__in=st).count() if st else dasar.count()}
            for k, (label, st) in FILTER_KELOLA.items()
        ],
        'q': q,
        'active_nav': 'kelola',
    }
    # Dari filter atau kotak cari (HTMX), cukup kirim bagian daftarnya saja
    if request.headers.get('HX-Request') == 'true':
        return render(request, 'inspections/kelola/partials/_daftar.html', konteks)
    return render(request, 'inspections/kelola/daftar.html', konteks)


def konteks_detail_admin(pesanan):
    return {
        'pesanan': pesanan,
        'peran': 'admin',
        'langkah': langkah_status(pesanan),
        # Linimasa: yang terbaru di atas
        'riwayat': pesanan.riwayat.select_related('oleh').order_by('-dibuat_pada', '-id'),
        # Tombol aksi cuma muncul kalau statusnya masih mengizinkan
        'bisa_tugaskan': pesanan.status == Status.DIAJUKAN,
        'bisa_jadwalkan': pesanan.status == Status.DIKONFIRMASI,
        'bisa_ganti_petugas': pesanan.status in STATUS_BISA_GANTI_PETUGAS,
        'bisa_batal': pesanan.status in STATUS_BISA_BATAL,
        'active_nav': 'kelola',
    }


@admin_required
def kelola_detail(request, pk):
    pesanan = get_object_or_404(pesanan_untuk(request.user), pk=pk)
    return render(request, 'inspections/kelola/detail.html', konteks_detail_admin(pesanan))


def _jalankan_aksi_admin(request, pk, **kwargs):
    pesanan = get_object_or_404(pesanan_untuk(request.user), pk=pk)
    return jalankan_aksi(
        request, pesanan, segarkan=lambda: get_object_or_404(pesanan_untuk(request.user), pk=pk),
        konteks_detail=konteks_detail_admin, templat_isi='inspections/kelola/partials/_isi_detail.html',
        nama_url_detail='inspections:kelola_detail', active_nav='kelola', **kwargs,
    )


@admin_required
def kelola_tugaskan(request, pk):
    return _jalankan_aksi_admin(
        request, pk, form_class=TugaskanForm, form_kwargs=lambda p: {'pesanan': p},
        jalankan=lambda p, user, d: konfirmasi_pesanan(p, d['petugas'], user, d['catatan']),
        judul='Tugaskan petugas',
        deskripsi='Pesanan jadi Dikonfirmasi. Setelah itu kamu tetapkan jadwal finalnya.',
        label_kirim='Tugaskan', pesan_sukses='Petugas sudah ditugaskan, pesanan jadi Dikonfirmasi.',
    )


@admin_required
def kelola_jadwalkan(request, pk):
    return _jalankan_aksi_admin(
        request, pk, form_class=JadwalFinalForm,
        awal=lambda p: {'tanggal': p.tanggal_usulan, 'sesi': p.sesi_usulan},
        jalankan=lambda p, user, d: jadwalkan_pesanan(p, d['tanggal'], d['sesi'], user),
        judul='Tetapkan jadwal final',
        deskripsi='Jadwal usulan pemilik sudah terisi. Ubah kalau perlu, lalu pesanan jadi Dijadwalkan.',
        label_kirim='Tetapkan jadwal', pesan_sukses='Jadwal final ditetapkan, pesanan jadi Dijadwalkan.',
    )


@admin_required
def kelola_ganti_petugas(request, pk):
    return _jalankan_aksi_admin(
        request, pk, form_class=TugaskanForm, form_kwargs=lambda p: {'pesanan': p},
        jalankan=lambda p, user, d: ganti_petugas(p, d['petugas'], user, d['catatan']),
        judul='Ganti petugas',
        deskripsi='Status pesanan nggak berubah. Pergantiannya tercatat di riwayat.',
        label_kirim='Ganti petugas', pesan_sukses='Petugas sudah diganti.',
    )


@admin_required
def kelola_batalkan(request, pk):
    return _jalankan_aksi_admin(
        request, pk, form_class=BatalkanForm,
        jalankan=lambda p, user, d: batalkan_pesanan(p, user, d['alasan']),
        judul='Batalkan pesanan?',
        deskripsi='Pesanan tetap tersimpan di riwayat dan nggak bisa dibuka lagi. Alasannya dicatat.',
        label_kirim='Batalkan pesanan', pesan_sukses='Pesanan dibatalkan.', bahaya=True,
    )
