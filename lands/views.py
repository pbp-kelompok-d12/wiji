from functools import wraps
from urllib.error import HTTPError, URLError

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import forms
from . import models
from .environment import fetch_environmental_data
from .nasa_power import fetch_climate_data
from .services import nominatim

LahanForm = forms.LahanForm
LandForm = getattr(forms, 'LandForm', forms.LahanForm)


def owner_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_owner:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


def _lahan_owner(request):
    Land = getattr(models, 'Land', None) or getattr(models, 'Lahan')
    return Land.objects.filter(owner=request.user)


def _draf_filter():
    Land = getattr(models, 'Land', None) or getattr(models, 'Lahan')
    draf_filter = Q()
    for field_name in Land.REQUIRED_FIELDS:
        field = Land._meta.get_field(field_name)
        kosong = Q(**{f'{field_name}__isnull': True})
        if field.get_internal_type() in ('CharField', 'TextField'):
            kosong |= Q(**{field_name: ''})
        draf_filter |= kosong
    return draf_filter


@owner_required
def daftar_lahan(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status')
    if status not in ('all', 'active', 'draft', 'archived'):
        status = 'archived' if request.GET.get('arsip') == '1' else 'all'

    semua_lahan = _lahan_owner(request)
    draf_filter = _draf_filter()
    lahan_list = semua_lahan
    if status == 'active':
        lahan_list = lahan_list.filter(diarsipkan=False).exclude(draf_filter)
    elif status == 'draft':
        lahan_list = lahan_list.filter(diarsipkan=False).filter(draf_filter)
    elif status == 'archived':
        lahan_list = lahan_list.filter(diarsipkan=True)

    if q:
        lahan_list = lahan_list.filter(Q(nama__icontains=q) | Q(alamat__icontains=q))
    lahan_list = lahan_list.prefetch_related('tujuan')

    context = {
        'active_nav': 'lahan',
        'lahan_list': lahan_list,
        'q': q,
        'status_filter': status,
        'jumlah_semua': semua_lahan.count(),
        'jumlah_aktif': (
            semua_lahan.filter(diarsipkan=False).exclude(draf_filter).count()
        ),
        'jumlah_draf': (
            semua_lahan.filter(diarsipkan=False).filter(draf_filter).count()
        ),
        'jumlah_arsip': semua_lahan.filter(diarsipkan=True).count(),
    }

    if request.headers.get('HX-Request') == 'true':
        return render(request, 'lands/partials/_daftar_lahan.html', context)
    return render(request, 'lands/daftar_lahan.html', context)


@owner_required
def tambah_lahan(request):
    form = LahanForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        lahan = form.save(commit=False)
        lahan.owner = request.user
        lahan.save()
        form.save_m2m()
        if lahan.adalah_draf:
            messages.info(
                request,
                f'Draft lahan {lahan.nama or "tanpa nama"} berhasil disimpan.',
            )
            return redirect(f'{reverse("lands:daftar_lahan")}?status=draft')
        messages.success(request, f'Lahan {lahan.nama} berhasil ditambahkan.')
        return redirect('lands:detail_lahan', pk=lahan.pk)

    return render(request, 'lands/form_lahan.html', {
        'active_nav': 'lahan',
        'form': form,
        'title': 'Tambah Lahan',
        'tombol': 'Simpan Lahan',
    })


@owner_required
def detail_lahan(request, pk):
    lahan = get_object_or_404(
        _lahan_owner(request).prefetch_related('tujuan'),
        pk=pk,
    )
    punya_pesanan_aktif = lahan.punya_pesanan_aktif()
    return render(request, 'lands/detail_lahan.html', {
        'active_nav': 'lahan',
        'lahan': lahan,
        'hasil_final': list(lahan.hasil_final()),
        'punya_pesanan_aktif': punya_pesanan_aktif,
        'dapat_diarsipkan': not lahan.diarsipkan and not punya_pesanan_aktif,
        'data_lingkungan': fetch_environmental_data(lahan),
        'iklim_historis': fetch_climate_data(lahan),
    })


@owner_required
def ubah_lahan(request, pk):
    lahan = get_object_or_404(_lahan_owner(request), pk=pk)
    form = LahanForm(
        request.POST or None,
        request.FILES or None,
        instance=lahan,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        if lahan.adalah_draf:
            messages.info(
                request,
                f'Draft lahan {lahan.nama or "tanpa nama"} berhasil diperbarui.',
            )
            return redirect(f'{reverse("lands:daftar_lahan")}?status=draft')
        messages.success(request, f'Lahan {lahan.nama} berhasil diperbarui.')
        return redirect('lands:detail_lahan', pk=lahan.pk)

    return render(request, 'lands/form_lahan.html', {
        'active_nav': 'lahan',
        'form': form,
        'lahan': lahan,
        'title': 'Ubah Lahan',
        'tombol': 'Simpan Perubahan',
    })


@owner_required
@require_http_methods(['GET', 'POST'])
def arsip_lahan(request, pk):
    lahan = get_object_or_404(_lahan_owner(request), pk=pk)
    if lahan.diarsipkan:
        messages.info(request, 'Lahan ini sudah diarsipkan.')
        return redirect('lands:detail_lahan', pk=lahan.pk)

    if lahan.adalah_draf:
        messages.error(request, 'Lengkapi data wajib sebelum mengarsipkan lahan.')
        return redirect('lands:ubah_lahan', pk=lahan.pk)

    if lahan.punya_pesanan_aktif():
        if request.method != 'POST':
            return render(request, 'lands/konfirmasi_arsip.html', {
                'active_nav': 'lahan',
                'lahan': lahan,
                'blocked': True,
            })
        messages.error(
            request,
            'Lahan ini masih punya pesanan aktif. Batalkan pesanannya dulu.',
        )
        return redirect('lands:detail_lahan', pk=lahan.pk)

    if request.method == 'POST':
        lahan.arsipkan()
        messages.success(request, f'Lahan {lahan.nama} diarsipkan.')
        return redirect('lands:daftar_lahan')

    return render(request, 'lands/konfirmasi_arsip.html', {
        'active_nav': 'lahan',
        'lahan': lahan,
    })


@owner_required
@require_POST
def pulihkan_lahan(request, pk):
    lahan = get_object_or_404(_lahan_owner(request), pk=pk)
    if request.method == 'POST':
        lahan.pulihkan()
        messages.success(request, f'Lahan {lahan.nama} dipulihkan.')
    return redirect('lands:detail_lahan', pk=lahan.pk)


@owner_required
def hapus_lahan(request, pk):
    lahan = get_object_or_404(_lahan_owner(request), pk=pk)

    if not lahan.adalah_draf:
        messages.error(
            request,
            'Lahan aktif tidak dapat dihapus permanen; gunakan Hapus untuk mengarsipkannya.',
        )
        return redirect('lands:detail_lahan', pk=lahan.pk)

    if not lahan.dapat_dihapus:
        messages.error(request, 'Lahan draft ini punya riwayat, jadi tidak dapat dihapus.')
        return redirect('lands:detail_lahan', pk=lahan.pk)

    if request.method == 'POST':
        nama = lahan.nama
        lahan.delete()
        messages.success(request, f'Lahan {nama} dihapus.')
        return redirect('lands:daftar_lahan')

    return render(request, 'lands/konfirmasi_hapus.html', {
        'active_nav': 'lahan',
        'lahan': lahan,
    })


def _serialisasi_lahan(lahan):
    return {
        'id': str(lahan.id),
        'nama': lahan.nama,
        'alamat': lahan.alamat,
        'latitude': float(lahan.latitude) if lahan.latitude is not None else None,
        'longitude': float(lahan.longitude) if lahan.longitude is not None else None,
        'luas_m2': float(lahan.luas_m2) if lahan.luas_m2 is not None else None,
        'penggunaan': lahan.penggunaan,
        'penggunaan_label': lahan.get_penggunaan_display(),
        'kondisi': lahan.kondisi,
        'foto': lahan.foto.url if lahan.foto else None,
        'tujuan': [tujuan.nama for tujuan in lahan.tujuan.all()],
        'punya_koordinat': lahan.punya_koordinat,
        'diarsipkan': lahan.diarsipkan,
        'status': (
            'archived'
            if lahan.diarsipkan
            else 'draft' if lahan.adalah_draf else 'active'
        ),
        'dibuat_pada': lahan.dibuat_pada.isoformat(),
        'diperbarui_pada': lahan.diperbarui_pada.isoformat(),
    }


@owner_required
@require_GET
def api_lahan(request):
    lahan_list = _lahan_owner(request).prefetch_related('tujuan')
    if request.GET.get('arsip') != '1':
        lahan_list = lahan_list.filter(diarsipkan=False)
    return JsonResponse(
        [_serialisasi_lahan(lahan) for lahan in lahan_list],
        safe=False,
    )


@owner_required
@require_GET
def api_detail_lahan(request, pk):
    lahan = get_object_or_404(
        _lahan_owner(request).prefetch_related('tujuan'),
        pk=pk,
    )
    return JsonResponse(_serialisasi_lahan(lahan))


@login_required
@require_GET
def cari_lokasi(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 3:
        return JsonResponse({'error': 'Kata kunci minimal 3 karakter.'}, status=400)

    try:
        data = nominatim('search', {
            'q': q,
            'addressdetails': 1,
            'limit': 5,
            'countrycodes': 'id',
        })
    except (HTTPError, URLError, TimeoutError):
        return JsonResponse(
            {'error': 'Layanan pencarian lokasi sedang tidak tersedia.'},
            status=502,
        )

    hasil = [
        {
            'display_name': item.get('display_name', ''),
            'lat': item.get('lat'),
            'lon': item.get('lon'),
            'type': item.get('type', ''),
        }
        for item in data
    ]
    return JsonResponse(hasil, safe=False)


@login_required
@require_GET
def reverse_lokasi(request):
    try:
        lat = float(request.GET.get('lat', ''))
        lon = float(request.GET.get('lon', ''))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Koordinat tidak valid.'}, status=400)

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return JsonResponse({'error': 'Koordinat di luar jangkauan.'}, status=400)

    try:
        data = nominatim('reverse', {
            'lat': lat,
            'lon': lon,
            'zoom': 18,
        })
    except (HTTPError, URLError, TimeoutError):
        return JsonResponse(
            {'error': 'Layanan alamat sedang tidak tersedia.'},
            status=502,
        )

    return JsonResponse({
        'display_name': data.get('display_name', ''),
        'lat': data.get('lat', lat),
        'lon': data.get('lon', lon),
    })
