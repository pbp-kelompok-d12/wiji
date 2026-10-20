from django import forms
from .models import Tanaman

class TanamanForm(forms.ModelForm):
    class Meta:
        model = Tanaman
        fields = ['nama', 'deskripsi', 'jenis', 'harga', 'stok']