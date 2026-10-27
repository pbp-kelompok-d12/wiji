from django import forms
from .models import HasilPemeriksaan, NutrientMeasurement


class HasilMandiriForm(forms.ModelForm):
    class Meta:
        model = HasilPemeriksaan
        fields = [
            "sumber",
            "tanggal_pemeriksaan",
            "ph",
            "kelembapan",
            "tekstur",
            "bahan_organik",
            "catatan",
        ]
        widgets = {
            "tanggal_pemeriksaan": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "catatan": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "sumber": "Laboratorium / sumber hasil",
            "ph": "pH",
            "kelembapan": "Kelembapan (%)",
            "bahan_organik": "Bahan organik (%)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["sumber"].required = True

        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-xl border border-line "
                "bg-white px-3 py-2"
            )

class NutrientMeasurementForm(forms.ModelForm):
    class Meta:
        model = NutrientMeasurement
        fields = ["nama_unsur", "nilai", "satuan", "metode"]
        labels = {
            "nama_unsur": "Nama unsur / parameter",
            "nilai": "Nilai pengukuran",
            "satuan": "Satuan",
            "metode": "Metode pemeriksaan",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-xl border border-line "
                "bg-white px-3 py-2"
            )