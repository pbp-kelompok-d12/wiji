from django.shortcuts import render, redirect, get_object_or_404
from .models import Tanaman
from .forms import TanamanForm
from django.contrib.admin.views.decorators import staff_member_required

def landing(request):
    return render(request, 'core/landing.html')


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