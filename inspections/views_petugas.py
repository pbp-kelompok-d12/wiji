"""Halaman petugas: tugas yang ditugaskan ke dia dan langkah pemeriksaannya."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .akses import petugas_required
from .models import PesananPemeriksaan
from .services import ubah_status
from .tampilan import langkah_status

Status = PesananPemeriksaan.Status

# Pilihan filter: kunci -> (label, daftar status). None = semua status.
FILTER_TUGAS = {
    'semua': ('Semua', None),
    'terjadwal': ('Terjadwal', [Status.DIKONFIRMASI, Status.DIJADWALKAN]),
    'dikerjakan': ('Dikerjakan', [Status.SAMPEL_DIAMBIL, Status.DIPROSES]),
    'selesai': ('Selesai', [Status.SELESAI]),
    'dibatalkan': ('Dibatalkan', [Status.DIBATALKAN]),
}


def tugas_petugas(user):
    """Cuma pesanan yang ditugaskan ke petugas ini. Sengaja bukan pesanan_untuk(): akun staf
    yang kebetulan berperan officer nggak boleh melihat semua pesanan lewat halaman petugas."""
    return PesananPemeriksaan.objects.filter(petugas=user).select_related(
        'lahan', 'lahan__owner', 'jenis', 'petugas',
    )


@petugas_required
def tugas_daftar(request):
    dasar = tugas_petugas(request.user)
    kunci = request.GET.get('status', 'semua')
    if kunci not in FILTER_TUGAS:
        kunci = 'semua'
    daftar_status = FILTER_TUGAS[kunci][1]
    tugas = dasar.filter(status__in=daftar_status) if daftar_status else dasar

    konteks = {
        # Jadwal terdekat di atas, yang belum punya jadwal di bawah
        'pesanan_list': tugas.order_by(F('tanggal_final').asc(nulls_last=True), '-dibuat_pada'),
        'filter_aktif': kunci,
        'filter_list': [
            {'kunci': k, 'label': label, 'jumlah': dasar.filter(status__in=st).count() if st else dasar.count()}
            for k, (label, st) in FILTER_TUGAS.items()
        ],
        'active_nav': 'tugas',
    }
    if request.headers.get('HX-Request') == 'true':
        return render(request, 'inspections/petugas/partials/_daftar.html', konteks)
    return render(request, 'inspections/petugas/daftar.html', konteks)


# Langkah yang boleh diambil petugas: status sekarang -> (status berikutnya, tulisan tombol, pesan sukses).
# Berhenti di Diproses. Mengisi dan memfinalkan hasil (jadi Selesai) dikerjakan lewat modul hasil pemeriksaan.
LANGKAH_BERIKUTNYA = {
    Status.DIJADWALKAN: (Status.SAMPEL_DIAMBIL, 'Tandai sampel diambil', 'Sampel ditandai sudah diambil.'),
    Status.SAMPEL_DIAMBIL: (Status.DIPROSES, 'Mulai proses', 'Pesanan masuk tahap proses.'),
}


def konteks_detail_petugas(pesanan):
    berikut = LANGKAH_BERIKUTNYA.get(pesanan.status)
    return {
        'langkah_berikut': {'ke': berikut[0].value, 'label': berikut[1]} if berikut else None,
        'pesanan': pesanan,
        'peran': 'petugas',
        'langkah': langkah_status(pesanan),
        # Linimasa: yang terbaru di atas
        'riwayat': pesanan.riwayat.select_related('oleh').order_by('-dibuat_pada', '-id'),
        'active_nav': 'tugas',
    }


@petugas_required
def tugas_detail(request, pk):
    pesanan = get_object_or_404(tugas_petugas(request.user), pk=pk)
    return render(request, 'inspections/petugas/detail.html', konteks_detail_petugas(pesanan))


@petugas_required
@require_POST
def tugas_lanjut(request, pk):
    """Majukan status ke langkah berikutnya. Tombolnya mengirim status tujuan (ke), jadi klik dobel
    atau halaman yang sudah basi nggak bisa melompati langkah."""
    pesanan = get_object_or_404(tugas_petugas(request.user), pk=pk)
    lewat_htmx = request.headers.get('HX-Request') == 'true'
    berikut = LANGKAH_BERIKUTNYA.get(pesanan.status)
    pesan_sukses = pesan_error = None

    if berikut is None or request.POST.get('ke') != berikut[0].value:
        pesan_error = 'Status pesanan sudah berubah. Muat ulang halaman, lalu coba lagi.'
    else:
        try:
            ubah_status(pesanan, berikut[0], oleh=request.user)
        except ValidationError as e:
            pesan_error = ' '.join(e.messages)
        else:
            pesan_sukses = berikut[2]
        pesanan = get_object_or_404(tugas_petugas(request.user), pk=pk)

    if lewat_htmx:
        return render(request, 'inspections/petugas/partials/_isi_detail.html', {
            **konteks_detail_petugas(pesanan), 'pesan_sukses': pesan_sukses, 'pesan_error': pesan_error,
        })
    (messages.success if pesan_sukses else messages.error)(request, pesan_sukses or pesan_error)
    return redirect('inspections:tugas_detail', pk=pesanan.pk)
