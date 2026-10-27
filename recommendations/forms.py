from django import forms

from .models import ManagementPlan


class ManagementPlanForm(forms.ModelForm):
    class Meta:
        model = ManagementPlan
        fields = (
            "luas_tanam_m2",
            "jumlah_bibit",
            "tanggal_tanam",
            "catatan",
        )
        widgets = {
            "luas_tanam_m2": forms.NumberInput(attrs={
                "class": "field-input",
                "min": "0.01",
                "step": "0.01",
                "placeholder": "Contoh: 100",
            }),
            "jumlah_bibit": forms.NumberInput(attrs={
                "class": "field-input",
                "min": "1",
                "step": "1",
                "placeholder": "Jumlah bibit",
            }),
            "tanggal_tanam": forms.DateInput(attrs={
                "class": "field-input",
                "type": "date",
            }),
            "catatan": forms.Textarea(attrs={
                "class": "field-input",
                "rows": "3",
                "placeholder": "Catatan tambahan (opsional)",
            }),
        }