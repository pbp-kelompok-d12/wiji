from django import forms
from .models import Tanaman

class TanamanForm(forms.ModelForm):
    class Meta:
        model = Tanaman
        fields = [
            'nama', 'nama_latin', 'fungsi', 'deskripsi', 
            'kondisi_pertumbuhan', 'kontaminan_ditangani', 
            'tersedia_di_indonesia', 'risiko_penggunaan', 'sumber_penelitian'
        ]
        widgets = {
            'nama': forms.TextInput(attrs={'class': 'w-full rounded-xl border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-forest'}),
            'nama_latin': forms.TextInput(attrs={'class': 'w-full rounded-xl border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-forest italic'}),
            'fungsi': forms.TextInput(attrs={'class': 'w-full rounded-xl border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-forest'}),
            'deskripsi': forms.Textarea(attrs={'class': 'w-full rounded-xl border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-forest', 'rows': 3}),
            'kondisi_pertumbuhan': forms.Textarea(attrs={'class': 'w-full rounded-xl border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-forest', 'rows': 2}),
            'kontaminan_ditangani': forms.Textarea(attrs={'class': 'w-full rounded-xl border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-forest', 'rows': 2}),
            'risiko_penggunaan': forms.Textarea(attrs={'class': 'w-full rounded-xl border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-forest', 'rows': 2}),
            'sumber_penelitian': forms.TextInput(attrs={'class': 'w-full rounded-xl border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-forest'}),
            'tersedia_di_indonesia': forms.CheckboxInput(attrs={'class': 'size-4 rounded border-line text-forest focus:ring-forest'}),
        }