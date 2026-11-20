"""API JSON buat rencana tanam dan rekomendasi (hanya baca, login lewat sesi seperti halaman web).

Aturannya sama dengan halaman: pemilik cuma bisa membaca data lahan dan rencananya sendiri.
Belum masuk dibalas 401, bukan pemilik 403, dan data milik orang lain dibalas 404 (bukan 403)
supaya keberadaannya nggak ketahuan.
"""
from functools import wraps

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from lands.models import Lahan, ManagementGoal
from soil_results.models import HasilPemeriksaan

from .models import ManagementPlan
from .services import RecommendationInputError, calculate_recommendations


def api_pemilik(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Silakan login terlebih dahulu.'}, status=401)
        if not request.user.is_owner:
            return JsonResponse({'error': 'Akses hanya untuk pemilik lahan.'}, status=403)
        response = view(request, *args, **kwargs)
        response['Cache-Control'] = 'private, no-store'
        return response
    return wrapper


def _rencana_pemilik(request):
    return ManagementPlan.objects.filter(pemilik=request.user).select_related(
        'lahan', 'rekomendasi', 'rekomendasi__tanaman', 'rekomendasi__tujuan',
    )


def _serialisasi_rencana(rencana, lengkap=False):
    rek = rencana.rekomendasi
    data = {
        'id': rencana.pk,
        'lahan': {'id': str(rencana.lahan_id), 'nama': rencana.lahan.nama},
        'tanaman': {'id': rek.tanaman_id, 'nama': rek.tanaman.nama, 'nama_latin': rek.tanaman.nama_latin},
        'tujuan': {'slug': rek.tujuan.slug, 'nama': rek.tujuan.nama},
        'skor': rek.skor,
        'status': rencana.status,
        'luas_tanam_m2': str(rencana.luas_tanam_m2) if rencana.luas_tanam_m2 is not None else None,
        'jumlah_bibit': rencana.jumlah_bibit,
        'tanggal_tanam': rencana.tanggal_tanam.isoformat() if rencana.tanggal_tanam else None,
    }
    if lengkap:
        data.update({
            'catatan': rencana.catatan,
            'alasan': rek.alasan,
            'kelengkapan_data': rek.kelengkapan_data,
            'versi_aturan': rek.versi_aturan,
            'hasil_pemeriksaan_id': rek.hasil_pemeriksaan_id,
            'dibuat_pada': rencana.dibuat_pada.isoformat(),
            'diperbarui_pada': rencana.diperbarui_pada.isoformat(),
        })
    return data


@require_GET
@api_pemilik
def api_daftar_rencana(request):
    rencana = _rencana_pemilik(request)
    status = request.GET.get('status', '').strip()
    if status:
        rencana = rencana.filter(status=status)
    return JsonResponse({'results': [_serialisasi_rencana(r) for r in rencana]})


@require_GET
@api_pemilik
def api_detail_rencana(request, pk):
    rencana = get_object_or_404(_rencana_pemilik(request), pk=pk)
    return JsonResponse(_serialisasi_rencana(rencana, lengkap=True))


@require_GET
@api_pemilik
def api_rekomendasi_lahan(request, lahan_id):
    """Hitung rekomendasi buat satu lahan. Wajib: ?hasil=<id hasil final>&tujuan=<id tujuan>.

    Cuma menghitung dan menampilkan, nggak menyimpan apa pun (rencana dibuat lewat halaman).
    """
    lahan = get_object_or_404(Lahan.objects.filter(owner=request.user, diarsipkan=False), pk=lahan_id)
    hasil = get_object_or_404(
        HasilPemeriksaan.objects.filter(lahan=lahan, status_hasil=HasilPemeriksaan.StatusHasil.FINAL),
        pk=_angka(request.GET.get('hasil')),
    )
    tujuan = get_object_or_404(ManagementGoal.objects.filter(aktif=True), pk=_angka(request.GET.get('tujuan')))

    try:
        hitungan = calculate_recommendations(lahan=lahan, hasil_pemeriksaan=hasil, tujuan=tujuan)
    except RecommendationInputError as e:
        return JsonResponse({'error': str(e)}, status=400)

    if hitungan.get('risiko_tinggi'):
        return JsonResponse({
            'risiko_tinggi': True,
            'temuan_risiko': hitungan['temuan_risiko'],
            'rekomendasi': [],
            'diblokir': [],
        })
    return JsonResponse({
        'risiko_tinggi': False,
        'tujuan': {'slug': tujuan.slug, 'nama': tujuan.nama},
        'kelengkapan_data': hitungan['kelengkapan_data'],
        'versi_aturan': hitungan['versi_aturan'],
        'rekomendasi': [
            {'tanaman': {'id': k.tanaman.pk, 'nama': k.tanaman.nama}, 'skor': k.skor, 'alasan': k.alasan}
            for k in hitungan['rekomendasi']
        ],
        'diblokir': [
            {'tanaman': {'id': d['tanaman'].pk, 'nama': d['tanaman'].nama}, 'alasan': d['alasan']}
            for d in hitungan['diblokir']
        ],
    })


def _angka(nilai):
    """Parameter yang bukan angka dianggap nggak ada (jadi 404, bukan error server)."""
    try:
        return int(nilai)
    except (TypeError, ValueError):
        return 0
