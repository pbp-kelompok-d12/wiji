"""Kerangka bareng buat aksi pada satu pesanan (ubah usulan, batalkan, tugaskan, dan seterusnya).

Dari halaman detail, formnya muncul sebagai modal lewat HTMX. Kalau JavaScript mati,
alamat yang sama tetap jalan sebagai halaman biasa. Pemilik, admin, dan petugas
memakai kerangka yang sama, yang beda cuma siapa yang boleh dan halaman detailnya.
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render


def jalankan_aksi(request, pesanan, *, form_class, jalankan, judul, deskripsi, label_kirim, pesan_sukses,
                  segarkan, konteks_detail, templat_isi, nama_url_detail, active_nav,
                  awal=None, form_kwargs=None, bahaya=False):
    """Tampilkan form aksi, jalankan kalau valid, lalu perbarui halaman detail.

    segarkan: fungsi yang mengambil ulang pesanan setelah aksi berhasil.
    konteks_detail: fungsi pesanan -> konteks halaman detail.
    templat_isi: isi detail yang diganti lewat HTMX setelah aksi berhasil.
    """
    lewat_htmx = request.headers.get('HX-Request') == 'true'
    data = request.POST if request.method == 'POST' else None
    form = form_class(data, initial=awal(pesanan) if awal else None, **(form_kwargs(pesanan) if form_kwargs else {}))

    if request.method == 'POST' and form.is_valid():
        try:
            jalankan(pesanan, request.user, form.cleaned_data)
        except ValidationError as e:
            form.add_error(None, e)
        else:
            pesanan = segarkan()
            if lewat_htmx:
                # Isi detail diganti, modalnya ditutup lewat elemen "oob"
                return render(request, 'inspections/partials/_hasil_aksi.html', {
                    **konteks_detail(pesanan), 'pesan_sukses': pesan_sukses, 'templat_isi': templat_isi,
                })
            messages.success(request, pesan_sukses)
            return redirect(nama_url_detail, pk=pesanan.pk)

    konteks = {
        'form': form, 'pesanan': pesanan, 'judul': judul, 'deskripsi': deskripsi,
        'label_kirim': label_kirim, 'bahaya': bahaya, 'aksi_url': request.path,
        'url_kembali': nama_url_detail, 'active_nav': active_nav,
    }
    if lewat_htmx:
        respons = render(request, 'inspections/partials/_modal_aksi.html', konteks)
        if request.method == 'POST':
            # Gagal validasi: tampilkan lagi di modal, bukan di tempat isi detail
            respons['HX-Retarget'] = '#modal-slot'
            respons['HX-Reswap'] = 'innerHTML'
        return respons
    return render(request, 'inspections/form_aksi.html', konteks)
