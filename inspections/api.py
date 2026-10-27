"""API JSON buat pesanan pemeriksaan (login lewat sesi, sama seperti halaman web).

Aturan aksesnya sama dengan halaman: pemilik cuma bisa melihat dan mengubah pesanan buat lahannya sendiri.
Kalau belum masuk dibalas 401, kalau bukan pemilik 403 (bukan diarahkan ke halaman login).
"""
import json
from functools import wraps

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from .forms import BatalkanForm, JadwalUlangForm, PesananForm
from .models import PesananPemeriksaan
from .pemesanan import ajukan_jadwal_ulang, batalkan_pesanan, buat_pesanan


def api_pemilik(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'detail': 'Masuk dulu.'}, status=401)
        if not request.user.is_owner:
            return JsonResponse({'detail': 'Cuma pemilik lahan yang bisa mengakses ini.'}, status=403)
        return view(request, *args, **kwargs)
    return wrapper


def _pesanan_pemilik(request):
    return PesananPemeriksaan.objects.filter(lahan__owner=request.user).select_related(
        'lahan', 'jenis', 'petugas',
    )


def _serialisasi(pesanan, dengan_riwayat=False):
    data = {
        'id': pesanan.pk,
        'kode': pesanan.kode,
        'status': pesanan.status,
        'status_label': pesanan.get_status_display(),
        'lahan': {'id': str(pesanan.lahan_id), 'nama': pesanan.lahan.nama},
        'jenis': {'id': pesanan.jenis_id, 'nama': pesanan.jenis.nama},
        'petugas': pesanan.petugas.display_name if pesanan.petugas else None,
        'tanggal_usulan': pesanan.tanggal_usulan.isoformat(),
        'sesi_usulan': pesanan.sesi_usulan,
        'tanggal_final': pesanan.tanggal_final.isoformat() if pesanan.tanggal_final else None,
        'sesi_final': pesanan.sesi_final or None,
        'catatan': pesanan.catatan,
        'dibuat_pada': pesanan.dibuat_pada.isoformat(),
    }
    if dengan_riwayat:
        data['riwayat'] = [
            {
                'jenis': r.jenis,
                'status_sebelum': r.status_sebelum or None,
                'status_sesudah': r.status_sesudah or None,
                'oleh': r.oleh.display_name if r.oleh else None,
                'catatan': r.catatan,
                'tanggal_lama': r.tanggal_lama.isoformat() if r.tanggal_lama else None,
                'tanggal_baru': r.tanggal_baru.isoformat() if r.tanggal_baru else None,
                'dibuat_pada': r.dibuat_pada.isoformat(),
            }
            for r in pesanan.riwayat.select_related('oleh')
        ]
    return data


def _baca_data(request):
    """Terima JSON atau form biasa. Mengembalikan (data, None) atau (None, respons_error)."""
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body or b'{}')
        except json.JSONDecodeError:
            return None, JsonResponse({'detail': 'Isi JSON-nya nggak valid.'}, status=400)
        if not isinstance(data, dict):
            return None, JsonResponse({'detail': 'Isi JSON harus berupa objek.'}, status=400)
        return data, None
    return request.POST, None


def _error_form(form):
    return JsonResponse({'errors': {k: [str(m) for m in v] for k, v in form.errors.items()}}, status=400)


def _error_aturan(e):
    return JsonResponse({'errors': {'__all__': e.messages}}, status=400)


@api_pemilik
def api_pesanan(request):
    """GET: daftar pesanan (boleh ?status=). POST: bikin pesanan baru."""
    if request.method == 'GET':
        daftar = _pesanan_pemilik(request)
        status = request.GET.get('status')
        if status:
            daftar = daftar.filter(status=status)
        return JsonResponse({'hasil': [_serialisasi(p) for p in daftar]})
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method nggak diizinkan.'}, status=405)

    data, galat = _baca_data(request)
    if galat:
        return galat
    form = PesananForm(data, pemilik=request.user)
    if not form.is_valid():
        return _error_form(form)
    try:
        pesanan = buat_pesanan(
            pemilik=request.user, lahan=form.cleaned_data['lahan'], jenis=form.cleaned_data['jenis'],
            tanggal_usulan=form.cleaned_data['tanggal_usulan'], sesi_usulan=form.cleaned_data['sesi_usulan'],
            catatan=form.cleaned_data['catatan'],
        )
    except ValidationError as e:
        return _error_aturan(e)
    return JsonResponse(_serialisasi(pesanan, dengan_riwayat=True), status=201)


@api_pemilik
@require_GET
def api_detail_pesanan(request, pk):
    pesanan = get_object_or_404(_pesanan_pemilik(request), pk=pk)
    return JsonResponse(_serialisasi(pesanan, dengan_riwayat=True))


def _aksi(request, pk, form_class, jalankan):
    pesanan = get_object_or_404(_pesanan_pemilik(request), pk=pk)
    data, galat = _baca_data(request)
    if galat:
        return galat
    form = form_class(data)
    if not form.is_valid():
        return _error_form(form)
    try:
        jalankan(pesanan, request.user, form.cleaned_data)
    except ValidationError as e:
        return _error_aturan(e)
    pesanan = get_object_or_404(_pesanan_pemilik(request), pk=pk)
    return JsonResponse(_serialisasi(pesanan, dengan_riwayat=True))


@api_pemilik
@require_POST
def api_batalkan(request, pk):
    return _aksi(request, pk, BatalkanForm, lambda p, user, d: batalkan_pesanan(p, user, d['alasan']))


@api_pemilik
@require_POST
def api_jadwal_ulang(request, pk):
    return _aksi(
        request, pk, JadwalUlangForm,
        lambda p, user, d: ajukan_jadwal_ulang(p, user, d['tanggal'], d['sesi'], d['alasan']),
    )
