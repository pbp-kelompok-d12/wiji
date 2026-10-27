from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.forms import INPUT_CLASS, InvalidFieldMixin
from lands.models import Lahan

from .models import JenisPemeriksaan, PesananPemeriksaan
from .pemesanan import MAKS_HARI_KE_DEPAN, validasi_tanggal_usulan


def lahan_bisa_dipesan(pemilik):
    """Lahan milik pemilik yang boleh dipesankan: aktif (bukan draf, bukan arsip) dan belum punya pesanan berjalan."""
    lahan = Lahan.objects.filter(owner=pemilik, diarsipkan=False)
    ids = [l.pk for l in lahan if not l.adalah_draf and not l.punya_pesanan_aktif()]
    return Lahan.objects.filter(pk__in=ids).order_by('nama')


class PesananForm(InvalidFieldMixin, forms.Form):
    lahan = forms.ModelChoiceField(
        queryset=Lahan.objects.none(),
        label='Lahan',
        empty_label='Pilih lahan',
        widget=forms.Select(attrs={'class': INPUT_CLASS}),
        error_messages={'required': 'Pilih lahan yang mau diperiksa.', 'invalid_choice': 'Lahan ini nggak bisa dipesankan pemeriksaan.'},
    )
    jenis = forms.ModelChoiceField(
        queryset=JenisPemeriksaan.objects.filter(aktif=True),
        label='Jenis pemeriksaan',
        empty_label=None,
        widget=forms.RadioSelect,
        error_messages={'required': 'Pilih jenis pemeriksaan.'},
    )
    tanggal_usulan = forms.DateField(
        label='Tanggal usulan',
        widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}),
        error_messages={'required': 'Isi tanggal usulan.', 'invalid': 'Format tanggal belum benar.'},
    )
    sesi_usulan = forms.ChoiceField(
        label='Sesi',
        choices=PesananPemeriksaan.Sesi.choices,
        widget=forms.RadioSelect,
        error_messages={'required': 'Pilih sesi pagi atau siang.'},
    )
    catatan = forms.CharField(
        label='Catatan untuk petugas',
        required=False,
        widget=forms.Textarea(attrs={'class': INPUT_CLASS + ' !h-auto py-3', 'rows': 3}),
        help_text='Misalnya patokan lokasi atau tempat parkir. Boleh dikosongkan.',
    )

    def __init__(self, *args, pemilik, **kwargs):
        super().__init__(*args, **kwargs)
        self.pemilik = pemilik
        self.fields['lahan'].queryset = lahan_bisa_dipesan(pemilik)
        hari_ini = timezone.localdate()
        # Batas ini cuma bantuan di kolom tanggal. Yang menentukan tetap validasi di server.
        self.fields['tanggal_usulan'].widget.attrs.update({
            'min': (hari_ini + timedelta(days=1)).isoformat(),
            'max': (hari_ini + timedelta(days=MAKS_HARI_KE_DEPAN)).isoformat(),
        })

    def clean_tanggal_usulan(self):
        tanggal = self.cleaned_data['tanggal_usulan']
        try:
            validasi_tanggal_usulan(tanggal)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return tanggal
