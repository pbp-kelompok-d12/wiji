from django.shortcuts import render, redirect, get_object_or_404
from .models import Tanaman
from .forms import TanamanForm
from django.contrib.admin.views.decorators import staff_member_required

# Data sementara buat preview katalog. Nanti ganti pakai model Plant kalau Modul D udah jadi.
FEATURED_PLANTS = [
    {'name': 'Akar wangi', 'latin': 'Chrysopogon zizanioides', 'role': 'Pengendali erosi'},
    {'name': 'Kalopo', 'latin': 'Calopogonium mucunoides', 'role': 'Penutup tanah'},
    {'name': 'Gamal', 'latin': 'Gliricidia sepium', 'role': 'Penambah nitrogen'},
    {'name': 'Kara benguk', 'latin': 'Mucuna pruriens', 'role': 'Bahan organik'},
]

OWNER_STEPS = [
    'Cari lokasi lahan langsung di peta.',
    'Pesan pemeriksaan dan pantau statusnya.',
    'Bandingkan tanaman dengan skor dan alasan.',
    'Simpan pilihan sebagai rencana tanam.',
]

# Contoh isi dashboard di landing page, bukan data asli
SAMPLE_ORDERS = [
    {'land': 'Kebun Lereng Cibodas', 'note': 'WJ-0012 · 3 Okt, Pagi', 'status': 'Dijadwalkan', 'badge': 'badge-sky'},
    {'land': 'Pekarangan Dramaga', 'note': 'WJ-0009 · hasil final 14 Sep', 'status': 'Selesai', 'badge': 'badge-leaf'},
    {'land': 'Sawah Tadah Hujan Ciampea', 'note': 'Belum ada data tanah', 'status': 'Pesan pemeriksaan', 'badge': 'badge-paper'},
]


def landing(request):
    context = {
        'featured_plants': FEATURED_PLANTS,
        'owner_steps': OWNER_STEPS,
        'sample_orders': SAMPLE_ORDERS,
    }
    return render(request, 'core/landing.html', context)

def daftar_tanaman(request):
    tanaman_list = Tanaman.objects.all()
    return render(request, 'core/daftar_tanaman.html', {'tanaman_list': tanaman_list})

# READ: Melihat detail tanaman
def detail_tanaman(request, pk):
    tanaman = get_object_or_404(Tanaman, pk=pk)
    return render(request, 'core/detail_tanaman.html', {'tanaman': tanaman})

# CREATE: Menambah tanaman baru
@staff_member_required
def tambah_tanaman(request):
    if request.method == 'POST':
        form = TanamanForm(request.POST)
        if form.is_valid():
            form.save()
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
            return redirect('core:detail_tanaman', pk=tanaman.pk)
    else:
        form = TanamanForm(instance=tanaman)
    return render(request, 'core/form_tanaman.html', {'form': form, 'title': 'Ubah Tanaman'})

# DELETE: Menghapus tanaman dari katalog
@staff_member_required
def hapus_tanaman(request, pk):
    tanaman = get_object_or_404(Tanaman, pk=pk)
    if request.method == 'POST':
        tanaman.delete()
        return redirect('core:daftar_tanaman')
    return render(request, 'core/konfirmasi_hapus.html', {'tanaman': tanaman})