from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from lands.models import ManagementGoal

from .forms import TanamanForm
from .models import Tanaman


def landing(request):
    return render(request, 'core/landing.html')


def _tanaman_terlihat(request):
    """Pengunjung cuma melihat tanaman yang aktif. Staf boleh melihat yang diarsipkan lewat ?arsip=1."""
    semua = Tanaman.objects.prefetch_related('tujuan_pengelolaan')
    if request.user.is_staff and request.GET.get('arsip') == '1':
        return semua.filter(diarsipkan=True)
    return semua.filter(diarsipkan=False)


def _saring(request, queryset):
    """Pencarian (nama, nama ilmiah, fungsi) dan filter tujuan, jenis, serta ketersediaan."""
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(nama__icontains=q) | Q(nama_latin__icontains=q) | Q(fungsi__icontains=q)
        )
    tujuan = request.GET.get('tujuan', '').strip()
    if tujuan:
        queryset = queryset.filter(tujuan_pengelolaan__slug=tujuan)
    jenis = request.GET.get('jenis', '')
    if jenis == 'fitoremediasi':
        queryset = queryset.exclude(Q(kontaminan_ditangani__isnull=True) | Q(kontaminan_ditangani=''))
    elif jenis == 'umum':
        queryset = queryset.filter(Q(kontaminan_ditangani__isnull=True) | Q(kontaminan_ditangani=''))
    if request.GET.get('lokal') == '1':
        queryset = queryset.filter(tersedia_di_indonesia=True)
    return queryset.distinct()


def daftar_tanaman(request):
    tanaman_list = _saring(request, _tanaman_terlihat(request))
    konteks = {
        'tanaman_list': tanaman_list,
        'tujuan_list': ManagementGoal.objects.filter(aktif=True),
        'q': request.GET.get('q', '').strip(),
        'tujuan_dipilih': request.GET.get('tujuan', ''),
        'jenis_dipilih': request.GET.get('jenis', ''),
        'hanya_lokal': request.GET.get('lokal') == '1',
        'lihat_arsip': request.user.is_staff and request.GET.get('arsip') == '1',
    }
    # Pencarian lewat HTMX cuma mengganti daftar kartunya
    if request.headers.get('HX-Request') == 'true':
        return render(request, 'core/partials/_daftar_kartu.html', konteks)
    return render(request, 'core/daftar_tanaman.html', konteks)


def _ambil_tanaman(request, pk):
    tanaman = get_object_or_404(Tanaman, pk=pk)
    if tanaman.diarsipkan and not request.user.is_staff:
        raise Http404
    return tanaman


# READ: Melihat detail tanaman
def detail_tanaman(request, pk):
    tanaman = _ambil_tanaman(request, pk)
    return render(request, 'core/detail_tanaman.html', {
        'tanaman': tanaman,
        'referensi_list': tanaman.referensi.all(),
        'kemampuan_list': tanaman.kemampuan_kontaminan.select_related('kontaminan'),
        'tujuan_list': tanaman.tujuan_pengelolaan.all(),
    })


# CREATE: Menambah tanaman baru
@staff_member_required
def tambah_tanaman(request):
    if request.method == 'POST':
        form = TanamanForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tanaman berhasil ditambahkan.')
            return redirect('core:daftar_tanaman')
    else:
        form = TanamanForm()
    return render(request, 'core/form_tanaman.html', {'form': form, 'title': 'Tambah Tanaman'})


# UPDATE: Mengubah informasi tanaman
@staff_member_required
def ubah_tanaman(request, pk):
    tanaman = get_object_or_404(Tanaman, pk=pk)
    if request.method == 'POST':
        form = TanamanForm(request.POST, instance=tanaman)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perubahan tanaman disimpan.')
            return redirect('core:detail_tanaman', pk=tanaman.pk)
    else:
        form = TanamanForm(instance=tanaman)
    return render(request, 'core/form_tanaman.html', {'form': form, 'title': 'Ubah Tanaman'})


# DELETE: Menghapus tanaman dari katalog (yang sudah dipakai rekomendasi cuma bisa diarsipkan)
@staff_member_required
def hapus_tanaman(request, pk):
    tanaman = get_object_or_404(Tanaman, pk=pk)
    if tanaman.sudah_dipakai:
        messages.error(request, f'{tanaman.nama} sudah dipakai di rekomendasi, jadi nggak bisa dihapus. Arsipkan saja.')
        return redirect('core:detail_tanaman', pk=tanaman.pk)
    if request.method == 'POST':
        tanaman.delete()
        messages.success(request, 'Tanaman dihapus dari katalog.')
        return redirect('core:daftar_tanaman')
    return render(request, 'core/konfirmasi_hapus.html', {'tanaman': tanaman})


@staff_member_required
@require_POST
def arsip_tanaman(request, pk):
    tanaman = get_object_or_404(Tanaman, pk=pk)
    tanaman.diarsipkan = True
    tanaman.diarsipkan_pada = timezone.now()
    tanaman.save(update_fields=['diarsipkan', 'diarsipkan_pada'])
    messages.success(request, f'{tanaman.nama} diarsipkan. Pengunjung nggak lagi melihatnya dan rekomendasi baru nggak memakainya.')
    return redirect('core:detail_tanaman', pk=tanaman.pk)


@staff_member_required
@require_POST
def pulihkan_tanaman(request, pk):
    tanaman = get_object_or_404(Tanaman, pk=pk)
    tanaman.diarsipkan = False
    tanaman.diarsipkan_pada = None
    tanaman.save(update_fields=['diarsipkan', 'diarsipkan_pada'])
    messages.success(request, f'{tanaman.nama} dikembalikan ke katalog.')
    return redirect('core:detail_tanaman', pk=tanaman.pk)


# ---- API JSON (publik, hanya baca) ----

def _serialisasi(tanaman, lengkap=False):
    data = {
        'id': tanaman.pk,
        'nama': tanaman.nama,
        'nama_latin': tanaman.nama_latin,
        'fungsi': tanaman.fungsi,
        'tersedia_di_indonesia': tanaman.tersedia_di_indonesia,
        'fitoremediasi': bool(tanaman.kontaminan_ditangani),
        'tujuan': [g.slug for g in tanaman.tujuan_pengelolaan.all()],
    }
    if lengkap:
        data.update({
            'deskripsi': tanaman.deskripsi,
            'kondisi_pertumbuhan': tanaman.kondisi_pertumbuhan,
            'risiko_penggunaan': tanaman.risiko_penggunaan,
            'sumber_penelitian': tanaman.sumber_penelitian,
            'kontaminan_ditangani': tanaman.kontaminan_ditangani,
            'referensi': [
                {'sumber': r.sumber_literatur, 'tautan': r.tautan} for r in tanaman.referensi.all()
            ],
            'kemampuan_kontaminan': [
                {'kontaminan': k.kontaminan.nama, 'tingkat_efektivitas': k.tingkat_efektivitas, 'catatan': k.catatan_khusus}
                for k in tanaman.kemampuan_kontaminan.select_related('kontaminan')
            ],
        })
    return data


@require_GET
def api_tanaman(request):
    """Daftar tanaman aktif. Parameter sama seperti halaman: q, tujuan, jenis, lokal."""
    queryset = _saring(request, Tanaman.objects.filter(diarsipkan=False).prefetch_related('tujuan_pengelolaan'))
    return JsonResponse({'hasil': [_serialisasi(t) for t in queryset]})


@require_GET
def api_detail_tanaman(request, pk):
    tanaman = get_object_or_404(Tanaman.objects.filter(diarsipkan=False), pk=pk)
    return JsonResponse(_serialisasi(tanaman, lengkap=True))
