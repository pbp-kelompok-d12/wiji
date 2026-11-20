from decimal import Decimal

from rest_framework import serializers

from core.models import Tanaman
from lands.models import Lahan, ManagementGoal
from soil_results.models import HasilPemeriksaan

from .models import ManagementPlan, RecommendationSnapshot


class RecommendationQuerySerializer(serializers.Serializer):
    hasil = serializers.IntegerField(min_value=1)
    tujuan = serializers.IntegerField(min_value=1)


class ManagementPlanFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=ManagementPlan.Status.choices,
        required=False,
    )


class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tanaman
        fields = (
            "id",
            "nama",
            "nama_latin",
            "fungsi",
            "deskripsi",
            "kondisi_pertumbuhan",
            "kontaminan_ditangani",
            "tersedia_di_indonesia",
            "risiko_penggunaan",
            "sumber_penelitian",
        )


class LandSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Lahan
        fields = ("id", "nama")


class GoalSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagementGoal
        fields = ("id", "nama", "slug", "deskripsi")


class SoilResultSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = HasilPemeriksaan
        fields = ("id", "tanggal_pemeriksaan", "asal", "sumber")


class RecommendationCandidateSerializer(serializers.Serializer):
    tanaman = PlantSerializer(read_only=True)
    skor = serializers.IntegerField()
    alasan = serializers.ListField(child=serializers.CharField())
    kelengkapan_data = serializers.IntegerField()
    input_snapshot = serializers.JSONField()
    data_lingkungan = serializers.JSONField()
    versi_aturan = serializers.CharField()


class BlockedRecommendationSerializer(serializers.Serializer):
    tanaman = PlantSerializer(read_only=True)
    alasan = serializers.CharField()


class RecommendationResponseSerializer(serializers.Serializer):
    lahan = LandSummarySerializer(read_only=True)
    hasil = SoilResultSummarySerializer(read_only=True)
    tujuan = GoalSummarySerializer(read_only=True)
    rekomendasi = RecommendationCandidateSerializer(many=True)
    diblokir = BlockedRecommendationSerializer(many=True)
    kelengkapan_data = serializers.IntegerField()
    input_snapshot = serializers.JSONField()
    data_lingkungan = serializers.JSONField()
    versi_aturan = serializers.CharField()
    risiko_tinggi = serializers.BooleanField()
    temuan_risiko = serializers.JSONField(allow_null=True)


class RecommendationPlanSummarySerializer(serializers.ModelSerializer):
    tanaman = PlantSerializer(read_only=True)
    tujuan = GoalSummarySerializer(read_only=True)

    class Meta:
        model = RecommendationSnapshot
        fields = (
            "id",
            "tanaman",
            "tujuan",
            "skor",
            "alasan",
            "kelengkapan_data",
            "versi_aturan",
        )


class RecommendationSnapshotDetailSerializer(serializers.ModelSerializer):
    tanaman = PlantSerializer(read_only=True)
    tujuan = GoalSummarySerializer(read_only=True)
    hasil_pemeriksaan = SoilResultSummarySerializer(read_only=True)

    class Meta:
        model = RecommendationSnapshot
        fields = (
            "id",
            "tanaman",
            "tujuan",
            "hasil_pemeriksaan",
            "skor",
            "alasan",
            "input_snapshot",
            "data_lingkungan",
            "kelengkapan_data",
            "versi_aturan",
            "dibuat_pada",
        )


class ManagementPlanListSerializer(serializers.ModelSerializer):
    lahan = LandSummarySerializer(read_only=True)
    rekomendasi = RecommendationPlanSummarySerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    luas_tanam_m2 = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = ManagementPlan
        fields = (
            "id",
            "lahan",
            "rekomendasi",
            "luas_tanam_m2",
            "jumlah_bibit",
            "tanggal_tanam",
            "catatan",
            "status",
            "status_label",
            "dibuat_pada",
            "diperbarui_pada",
        )


class ManagementPlanListResponseSerializer(serializers.Serializer):
    results = ManagementPlanListSerializer(many=True)


class ManagementPlanDetailSerializer(serializers.ModelSerializer):
    lahan = LandSummarySerializer(read_only=True)
    rekomendasi = RecommendationSnapshotDetailSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    luas_tanam_m2 = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = ManagementPlan
        fields = (
            "id",
            "lahan",
            "rekomendasi",
            "luas_tanam_m2",
            "jumlah_bibit",
            "tanggal_tanam",
            "catatan",
            "status",
            "status_label",
            "dibuat_pada",
            "diperbarui_pada",
        )
