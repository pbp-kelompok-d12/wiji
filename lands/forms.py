from django import forms
from django.core.exceptions import ValidationError

from . import models
from .models import ManagementGoal

INPUT_CLASS = 'field-input'


class LahanForm(forms.ModelForm):
    class Meta:
        model = models.Lahan
        fields = (
            'nama',
            'alamat',
            'latitude',
            'longitude',
            'luas_m2',
            'penggunaan',
            'kondisi',
            'foto',
            'tujuan',
        )
        labels = {
            'nama': 'Nama lahan',
            'alamat': 'Alamat',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'luas_m2': 'Luas (m²)',
            'penggunaan': 'Penggunaan',
            'kondisi': 'Kondisi umum',
            'foto': 'Foto lahan',
            'tujuan': 'Tujuan pengelolaan',
        }
        widgets = {
            'nama': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'alamat': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Terisi dari peta, bisa diubah',
            }),
            'latitude': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.000001',
                'placeholder': '-6.740000',
            }),
            'longitude': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.000001',
                'placeholder': '107.000000',
            }),
            'luas_m2': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
                'min': '0',
            }),
            'penggunaan': forms.Select(attrs={'class': INPUT_CLASS}),
            'kondisi': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Contoh: Tanah subur',
            }),
            'foto': forms.ClearableFileInput(attrs={
                'class': 'block w-full rounded-xl border border-line bg-paper px-3 py-2 text-sm',
                'accept': 'image/*',
                'aria-label': 'Foto lahan',
            }),
            'tujuan': forms.CheckboxSelectMultiple(attrs={
                'class': 'mt-0.5 size-4 shrink-0 rounded border-line text-moss focus:ring-moss',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tujuan'].queryset = ManagementGoal.objects.filter(aktif=True)
        self.fields['tujuan'].required = False
        self.fields['foto'].required = False
        self.fields['kondisi'].required = False
        for name in models.Lahan.REQUIRED_FIELDS:
            self.fields[name].required = False
        self.fields['latitude'].help_text = 'Terisi otomatis dari peta.'
        self.fields['longitude'].help_text = 'Terisi otomatis dari peta.'

        for name in ('latitude', 'longitude', 'luas_m2'):
            self.fields[name].localize = False

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if not foto:
            return foto
        if getattr(foto, '_committed', False):
            return foto
        if foto.size > 5 * 1024 * 1024:
            raise ValidationError('Ukuran foto maksimal 5 MB.')
        content_type = getattr(foto, 'content_type', None)
        if content_type and not content_type.startswith('image/'):
            raise ValidationError('File harus berupa gambar.')
        return foto


LandForm = LahanForm
try:
    from .models import Land
    LandForm = LahanForm
except Exception:
    pass
