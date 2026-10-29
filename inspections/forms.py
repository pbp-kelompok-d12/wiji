from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.forms import INPUT_CLASS, InvalidFieldMixin
from accounts.models import User
from lands.models import Lahan

from .models import JenisPemeriksaan, PesananPemeriksaan
from .pemesanan import MAKS_HARI_KE_DEPAN, validasi_tanggal_usulan


def lahan_bisa_dipesan(pemilik):
    """Lahan milik pemilik yang boleh dipesankan: aktif (bukan draf, bukan arsip) dan belum punya pesanan berjalan."""
    lahan = Lahan.objects.filter(owner=pemilik, diarsipkan=False)
    ids = [l.pk for l in lahan if not l.adalah_draf and not l.punya_pesanan_aktif()]
    return Lahan.objects.filter(pk__in=ids).order_by('nama')


def atur_batas_tanggal(field):
    """Bantuan di kolom tanggal: paling cepat besok, paling lambat 30 hari lagi.
    Yang menentukan tetap validasi di server."""
    hari_ini = timezone.localdate()
    field.widget.attrs.update({
        'min': (hari_ini + timedelta(days=1)).isoformat(),
        'max': (hari_ini + timedelta(days=MAKS_HARI_KE_DEPAN)).isoformat(),
    })


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
        atur_batas_tanggal(self.fields['tanggal_usulan'])

    def clean_tanggal_usulan(self):
        tanggal = self.cleaned_data['tanggal_usulan']
        try:
            validasi_tanggal_usulan(tanggal)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return tanggal


def _validasi_tanggal(form):
    tanggal = form.cleaned_data['tanggal']
    try:
        validasi_tanggal_usulan(tanggal)
    except ValidationError as e:
        raise forms.ValidationError(e.messages)
    return tanggal


class BatalkanForm(InvalidFieldMixin, forms.Form):
    alasan = forms.CharField(
        label='Alasan pembatalan',
        widget=forms.Textarea(attrs={'class': INPUT_CLASS + ' !h-auto py-3', 'rows': 3}),
        error_messages={'required': 'Alasan pembatalan wajib diisi.'},
    )


class JadwalUlangForm(InvalidFieldMixin, forms.Form):
    tanggal = forms.DateField(
        label='Tanggal usulan baru',
        widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}),
        error_messages={'required': 'Isi tanggal usulan baru.', 'invalid': 'Format tanggal belum benar.'},
    )
    sesi = forms.ChoiceField(
        label='Sesi',
        choices=PesananPemeriksaan.Sesi.choices,
        widget=forms.RadioSelect,
        error_messages={'required': 'Pilih sesi pagi atau siang.'},
    )
    alasan = forms.CharField(
        label='Alasan',
        widget=forms.Textarea(attrs={'class': INPUT_CLASS + ' !h-auto py-3', 'rows': 3}),
        error_messages={'required': 'Alasan jadwal ulang wajib diisi.'},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        atur_batas_tanggal(self.fields['tanggal'])

    def clean_tanggal(self):
        return _validasi_tanggal(self)


class UbahUsulanForm(InvalidFieldMixin, forms.Form):
    tanggal = forms.DateField(
        label='Tanggal usulan',
        widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}, format='%Y-%m-%d'),
        error_messages={'required': 'Isi tanggal usulan.', 'invalid': 'Format tanggal belum benar.'},
    )
    sesi = forms.ChoiceField(
        label='Sesi',
        choices=PesananPemeriksaan.Sesi.choices,
        widget=forms.RadioSelect,
        error_messages={'required': 'Pilih sesi pagi atau siang.'},
    )
    catatan = forms.CharField(
        label='Catatan untuk petugas',
        required=False,
        widget=forms.Textarea(attrs={'class': INPUT_CLASS + ' !h-auto py-3', 'rows': 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        atur_batas_tanggal(self.fields['tanggal'])

    def clean_tanggal(self):
        return _validasi_tanggal(self)


def petugas_aktif():
    """Petugas pemeriksa yang masih aktif, buat pilihan di form admin."""
    return User.objects.filter(role=User.Role.OFFICER, is_active=True).order_by('first_name', 'username')


class _PilihPetugasField(forms.ModelChoiceField):
    def label_from_instance(self, user):
        return user.display_name


class TugaskanForm(InvalidFieldMixin, forms.Form):
    petugas = _PilihPetugasField(
        queryset=User.objects.none(),
        label='Petugas',
        empty_label='Pilih petugas',
        widget=forms.Select(attrs={'class': INPUT_CLASS}),
        error_messages={'required': 'Pilih petugas yang bertugas.', 'invalid_choice': 'Petugas ini nggak tersedia.'},
    )
    catatan = forms.CharField(
        label='Catatan (boleh kosong)', required=False,
        widget=forms.Textarea(attrs={'class': INPUT_CLASS + ' !h-auto py-3', 'rows': 2}),
    )

    def __init__(self, *args, pesanan=None, **kwargs):
        super().__init__(*args, **kwargs)
        daftar = petugas_aktif()
        # Waktu ganti petugas, petugas yang sekarang nggak perlu muncul lagi
        if pesanan is not None and pesanan.petugas_id:
            daftar = daftar.exclude(pk=pesanan.petugas_id)
        self.fields['petugas'].queryset = daftar


class JadwalFinalForm(InvalidFieldMixin, forms.Form):
    tanggal = forms.DateField(
        label='Tanggal pemeriksaan',
        widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}, format='%Y-%m-%d'),
        error_messages={'required': 'Isi tanggal pemeriksaan.', 'invalid': 'Format tanggal belum benar.'},
    )
    sesi = forms.ChoiceField(
        label='Sesi',
        choices=PesananPemeriksaan.Sesi.choices,
        widget=forms.RadioSelect,
        error_messages={'required': 'Pilih sesi pagi atau siang.'},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tanggal'].widget.attrs['min'] = timezone.localdate().isoformat()

    def clean_tanggal(self):
        tanggal = self.cleaned_data['tanggal']
        # Jadwal final cuma dilarang di masa lalu. Hari ini masih boleh
        if tanggal < timezone.localdate():
            raise forms.ValidationError('Tanggal pemeriksaan nggak boleh di masa lalu.')
        return tanggal
