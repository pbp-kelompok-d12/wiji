"""Bentuk JSON Modul B buat API DRF (/api/v1/), dipakai aplikasi mobile.

Validasi pesanan baru sengaja manggil aturan yang sama dengan web (pemesanan.py),
jadi pesanan dari HP dan dari web dicek dengan cara yang persis sama.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from lands.models import Lahan

from .models import JenisPemeriksaan, PesananPemeriksaan, RiwayatPesanan
from .pemesanan import buat_pesanan, validasi_lahan_bisa_dipesan, validasi_tanggal_usulan


def _pesan_django(error):
    """Aturan di pemesanan.py ngelempar ValidationError Django, DRF butuh versinya sendiri."""
    return serializers.ValidationError(error.messages)


class JenisPemeriksaanSerializer(serializers.ModelSerializer):
    class Meta:
        model = JenisPemeriksaan
        fields = ['id', 'nama', 'slug', 'deskripsi', 'tingkat']


class LahanRingkasSerializer(serializers.ModelSerializer):
    """Cuma id sama nama. Detail lahan lengkap ada di API Modul A."""

    class Meta:
        model = Lahan
        fields = ['id', 'nama']


class RiwayatPesananSerializer(serializers.ModelSerializer):
    jenis_label = serializers.CharField(source='get_jenis_display', read_only=True)
    oleh = serializers.SerializerMethodField()

    class Meta:
        model = RiwayatPesanan
        fields = [
            'jenis', 'jenis_label', 'status_sebelum', 'status_sesudah', 'oleh',
            'catatan', 'tanggal_lama', 'tanggal_baru', 'dibuat_pada',
        ]

    def get_oleh(self, riwayat):
        # Nama yang tampil aja, akun lengkapnya nggak dikirim
        return riwayat.oleh.display_name if riwayat.oleh else None


class PesananSerializer(serializers.ModelSerializer):
    """Buat daftar pesanan. Semua field cuma dibaca."""

    kode = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    lahan = LahanRingkasSerializer(read_only=True)
    jenis = JenisPemeriksaanSerializer(read_only=True)
    petugas = serializers.SerializerMethodField()

    class Meta:
        model = PesananPemeriksaan
        fields = [
            'id', 'kode', 'status', 'status_label', 'lahan', 'jenis', 'petugas',
            'tanggal_usulan', 'sesi_usulan', 'tanggal_final', 'sesi_final', 'catatan',
            'dibuat_pada', 'diperbarui_pada',
        ]
        read_only_fields = fields

    def get_petugas(self, pesanan):
        return pesanan.petugas.display_name if pesanan.petugas else None


class PesananDetailSerializer(PesananSerializer):
    """Sama kayak daftar, plus riwayat perubahan buat linimasa di halaman detail."""

    riwayat = RiwayatPesananSerializer(many=True, read_only=True)

    class Meta(PesananSerializer.Meta):
        fields = PesananSerializer.Meta.fields + ['riwayat']
        read_only_fields = fields


class PesananBaruSerializer(serializers.Serializer):
    """Isian pas pemilik mesen pemeriksaan dari HP.

    Status, petugas, sama jadwal final sengaja nggak ada di sini, jadi nggak bisa diisi dari luar.
    """

    lahan = serializers.PrimaryKeyRelatedField(
        queryset=Lahan.objects.none(),
        error_messages={'does_not_exist': 'Lahan nggak ketemu atau bukan milikmu.'},
    )
    jenis = serializers.PrimaryKeyRelatedField(
        queryset=JenisPemeriksaan.objects.filter(aktif=True),
        error_messages={'does_not_exist': 'Jenis pemeriksaan ini nggak tersedia.'},
    )
    tanggal_usulan = serializers.DateField()
    sesi_usulan = serializers.ChoiceField(choices=PesananPemeriksaan.Sesi.choices)
    catatan = serializers.CharField(required=False, allow_blank=True, default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pilihan lahan cuma lahan milik yang login. Lahan orang lain dianggap nggak ada.
        self.fields['lahan'].queryset = Lahan.objects.filter(owner=self.context['request'].user)

    def validate_lahan(self, lahan):
        try:
            validasi_lahan_bisa_dipesan(lahan)
        except DjangoValidationError as e:
            raise _pesan_django(e)
        return lahan

    def validate_tanggal_usulan(self, tanggal):
        try:
            validasi_tanggal_usulan(tanggal)
        except DjangoValidationError as e:
            raise _pesan_django(e)
        return tanggal

    def create(self, validated_data):
        try:
            return buat_pesanan(pemilik=self.context['request'].user, **validated_data)
        except DjangoValidationError as e:
            # Misalnya dua request barengan buat lahan yang sama, dan salah satunya kalah duluan
            raise _pesan_django(e)
