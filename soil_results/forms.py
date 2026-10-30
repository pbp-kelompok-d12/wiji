from django import forms
from .models import HasilPemeriksaan, NutrientMeasurement, ContaminantFinding


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


class DokumenLaboratoriumForm(forms.Form):
    dokumen = forms.FileField(
        label="Dokumen laboratorium",
        widget=forms.FileInput(attrs={"accept": ".pdf"}),
        help_text="PDF, maksimal 5 MB.",
    )

    def clean_dokumen(self):
        dokumen = self.cleaned_data["dokumen"]

        if not dokumen.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Pilih file PDF.")

        if dokumen.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Ukuran maksimal 5 MB.")

        header = dokumen.read(5)
        dokumen.seek(0)

        if header != b"%PDF-":
            raise forms.ValidationError("Isi file tidak dikenali sebagai PDF.")

        return dokumen


class ContaminantFindingForm(forms.ModelForm):
    class Meta:
        model = ContaminantFinding
        fields = [
            "kontaminan",
            "status",
            "nilai",
            "satuan",
            "batas_deteksi",
            "metode",
            "catatan",
        ]
        widgets = {
            "catatan": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, hasil, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.hasil = hasil

        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-xl border border-line "
                "bg-white px-3 py-2"
            )

    def clean_kontaminan(self):
        kontaminan = self.cleaned_data["kontaminan"]

        duplikat = ContaminantFinding.objects.filter(
            hasil=self.instance.hasil,
            kontaminan=kontaminan,
        )

        if self.instance.pk:
            duplikat = duplikat.exclude(pk=self.instance.pk)

        if duplikat.exists():
            raise forms.ValidationError(
                "Kontaminan ini sudah dicatat pada hasil tersebut. "
                "Ubah temuan yang sudah ada."
            )

        return kontaminan


class HasilPetugasForm(HasilMandiriForm):
    class Meta(HasilMandiriForm.Meta):
        fields = [
            "tanggal_pemeriksaan",
            "ph",
            "kelembapan",
            "tekstur",
            "bahan_organik",
            "catatan",
        ]

    def __init__(self, *args, **kwargs):
        # Gunakan inisialisasi ModelForm karena form ini
        # tidak menyertakan field sumber.
        forms.ModelForm.__init__(self, *args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-xl border border-line "
                "bg-white px-3 py-2"
            )


class KoreksiHasilForm(HasilPetugasForm):
    alasan = forms.CharField(
        label="Alasan koreksi",
        min_length=10,
        max_length=2000,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "class": "w-full rounded-xl border border-line p-3",
        }),
        help_text="Jelaskan kesalahan data dan alasan perbaikannya.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for nama in [
            "tanggal_pemeriksaan",
            "ph",
            "kelembapan",
            "tekstur",
            "bahan_organik",
        ]:
            self.fields[nama].required = True