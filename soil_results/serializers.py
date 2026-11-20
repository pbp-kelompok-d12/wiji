from rest_framework import serializers

from .models import (
    ContaminantFinding,
    HasilPemeriksaan,
    NutrientMeasurement,
)


class NutrientMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutrientMeasurement
        fields = [
            "id",
            "nama_unsur",
            "nilai",
            "satuan",
            "metode",
        ]
        read_only_fields = fields


class ContaminantFindingSerializer(serializers.ModelSerializer):
    kontaminan_nama = serializers.CharField(
        source="kontaminan.nama",
        read_only=True,
    )
    status_label = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = ContaminantFinding
        fields = [
            "id",
            "kontaminan",
            "kontaminan_nama",
            "status",
            "status_label",
            "nilai",
            "satuan",
            "batas_deteksi",
            "metode",
            "catatan",
        ]
        read_only_fields = fields


class HasilPemeriksaanSerializer(serializers.ModelSerializer):
    lahan_nama = serializers.CharField(
        source="lahan.nama",
        read_only=True,
    )
    asal_label = serializers.CharField(
        source="get_asal_display",
        read_only=True,
    )
    status_hasil_label = serializers.CharField(
        source="get_status_hasil_display",
        read_only=True,
    )

    class Meta:
        model = HasilPemeriksaan
        fields = [
            "id",
            "lahan",
            "lahan_nama",
            "asal",
            "asal_label",
            "status_hasil",
            "status_hasil_label",
            "tanggal_pemeriksaan",
            "ph",
            "sumber",
        ]
        read_only_fields = fields


class DetailHasilPemeriksaanSerializer(HasilPemeriksaanSerializer):
    nutrient_measurements = NutrientMeasurementSerializer(
        many=True,
        read_only=True,
    )
    contaminant_findings = ContaminantFindingSerializer(
        many=True,
        read_only=True,
    )
    ada_dokumen = serializers.SerializerMethodField()

    def get_ada_dokumen(self, obj):
        return bool(obj.dokumen_laboratorium)

    class Meta(HasilPemeriksaanSerializer.Meta):
        fields = HasilPemeriksaanSerializer.Meta.fields + [
            "kelembapan",
            "tekstur",
            "bahan_organik",
            "unsur_hara",
            "kontaminan",
            "catatan",
            "pesanan",
            "difinalkan_pada",
            "dibuat_pada",
            "diperbarui_pada",
            "nutrient_measurements",
            "contaminant_findings",
            "ada_dokumen",
        ]
        read_only_fields = fields