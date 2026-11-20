"""Isi data demo lengkap buat semua modul dengan satu perintah.

Urutannya: akun, lahan, dan pesanan (seed_pesanan_demo), lalu hasil pemeriksaan, rekomendasi, dan rencana tanam.
Katalog tanaman sudah terisi otomatis lewat migrasi.

Pakai: python manage.py seed_demo [--ulang]
Akun demo dipakai buat percobaan, jangan dipakai di server asli.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from core.models import ContaminantType
from inspections.management.commands.seed_pesanan_demo import PASSWORD_DEMO, PEMILIK
from lands.models import Lahan, ManagementGoal
from recommendations import services as rekomendasi
from recommendations.models import ManagementPlan, RecommendationSnapshot
from soil_results.models import ContaminantFinding, HasilPemeriksaan, NutrientMeasurement

# Cuaca nggak diambil dari internet buat data demo, supaya hasilnya sama di mana pun dijalankan
CUACA_DEMO = {
    'status': 'unavailable',
    'source': 'Open-Meteo',
    'reason': 'data_demo',
    'message': 'Data cuaca tidak diambil untuk data demo.',
    'timezone': None,
    'current': {},
    'units': {},
}

# lahan -> tujuan pengelolaan
TUJUAN_LAHAN = {
    'Pekarangan Dramaga': ['peningkatan-kesuburan', 'konservasi-air'],
    'Kebun Lereng Cibodas': ['pencegahan-erosi'],
    'Kebun Salak Tenjolaya': ['konservasi-air'],
    'Kebun Kopi Sukamakmur': ['pemulihan-tanah-tercemar'],
}


def hari(n):
    return date.today() + timedelta(days=n)


class Command(BaseCommand):
    help = 'Isi data demo semua modul: akun, lahan, pesanan, hasil pemeriksaan, rekomendasi, dan rencana tanam.'

    def add_arguments(self, parser):
        parser.add_argument('--ulang', action='store_true', help='Hapus data demo lama, lalu bikin lagi.')

    @transaction.atomic
    def handle(self, *args, **opsi):
        if opsi['ulang']:
            self._hapus_turunan()

        call_command('seed_pesanan_demo', ulang=opsi['ulang'], stdout=self.stdout)

        pemilik = User.objects.get(username=PEMILIK['username'])
        lahan = {l.nama: l for l in Lahan.objects.filter(owner=pemilik)}
        if HasilPemeriksaan.objects.filter(lahan__owner=pemilik).exists():
            self.stdout.write('Hasil dan rencana demo sudah ada. Pakai --ulang kalau mau dibuat ulang.')
            return

        for nama, slugs in TUJUAN_LAHAN.items():
            lahan[nama].tujuan.set(ManagementGoal.objects.filter(slug__in=slugs))

        # Hasil Wiji yang sudah final, dari pesanan yang Selesai
        dramaga = self._hasil_wiji_final(lahan['Pekarangan Dramaga'])
        # Hasil Wiji yang masih draf, dari pesanan yang Diproses (petugas bisa "lanjutkan draf")
        self._hasil_wiji_draf(lahan['Kebun Salak Tenjolaya'])
        # Hasil mandiri (dari lab sendiri), bersih dari kontaminan
        cibodas = self._hasil_mandiri(lahan['Kebun Lereng Cibodas'])
        # Hasil mandiri dengan timbal tinggi: rekomendasi otomatis berhenti dan diarahkan ke ahli
        self._hasil_tercemar(lahan['Kebun Kopi Sukamakmur'])

        rencana = [
            self._rencana(pemilik, dramaga, 'peningkatan-kesuburan', ManagementPlan.Status.BERJALAN, 120, 80, hari(-3)),
            self._rencana(pemilik, cibodas, 'pencegahan-erosi', ManagementPlan.Status.DIRENCANAKAN, 300, 150, hari(14)),
        ]

        self.stdout.write(self.style.SUCCESS(
            f'Data demo lengkap. {HasilPemeriksaan.objects.filter(lahan__owner=pemilik).count()} hasil pemeriksaan, '
            f'{len(rencana)} rencana tanam.\n'
            f'  Masuk sebagai {PEMILIK["username"]} / {PASSWORD_DEMO}'
        ))

    def _hapus_turunan(self):
        """Hasil, rekomendasi, dan rencana nyangkut (PROTECT) ke lahan dan pesanan, jadi dihapus duluan."""
        pemilik = User.objects.filter(username=PEMILIK['username']).first()
        if not pemilik:
            return
        ManagementPlan.objects.filter(pemilik=pemilik).delete()
        RecommendationSnapshot.objects.filter(lahan__owner=pemilik).delete()
        HasilPemeriksaan.objects.filter(lahan__owner=pemilik).delete()

    def _hasil_wiji_final(self, lahan):
        pesanan = lahan.inspection_orders.get()
        hasil = HasilPemeriksaan.objects.create(
            lahan=lahan, pesanan=pesanan, asal=HasilPemeriksaan.Asal.WIJI, sumber='Pemeriksaan Wiji',
            dibuat_oleh=pesanan.petugas, tanggal_pemeriksaan=hari(-8),
            ph=Decimal('6.4'), kelembapan=Decimal('31'), tekstur='lempung berpasir', bahan_organik=Decimal('3.1'),
            catatan='Tanah gembur, sedikit batu kecil di bagian timur.',
            status_hasil=HasilPemeriksaan.StatusHasil.FINAL,
        )
        HasilPemeriksaan.objects.filter(pk=hasil.pk).update(difinalkan_pada=hasil.dibuat_pada)
        for nama, nilai, satuan in [('Nitrogen total', '0.21', '%'), ('Fosfor tersedia', '14.5', 'mg/kg'),
                                    ('Kalium', '0.42', 'cmol(+)/kg')]:
            NutrientMeasurement.objects.create(hasil=hasil, nama_unsur=nama, nilai=Decimal(nilai), satuan=satuan)
        self._tanpa_kontaminan(hasil)
        return hasil

    def _hasil_wiji_draf(self, lahan):
        pesanan = lahan.inspection_orders.get()
        HasilPemeriksaan.objects.create(
            lahan=lahan, pesanan=pesanan, asal=HasilPemeriksaan.Asal.WIJI, sumber='Pemeriksaan Wiji',
            dibuat_oleh=pesanan.petugas, tanggal_pemeriksaan=date.today(), ph=Decimal('5.8'),
            status_hasil=HasilPemeriksaan.StatusHasil.DRAF, catatan='Baru pH yang terukur, sisanya menyusul.',
        )

    def _hasil_mandiri(self, lahan):
        hasil = HasilPemeriksaan.objects.create(
            lahan=lahan, asal=HasilPemeriksaan.Asal.MANDIRI, sumber='Laboratorium Tanah mitra (hasil milik pemilik)',
            dibuat_oleh=lahan.owner, tanggal_pemeriksaan=hari(-20),
            ph=Decimal('5.9'), kelembapan=Decimal('35'), tekstur='lempung berliat', bahan_organik=Decimal('2.4'),
            catatan='Lereng agak curam, tanah terbuka di bagian bawah.',
        )
        NutrientMeasurement.objects.create(hasil=hasil, nama_unsur='Nitrogen total', nilai=Decimal('0.15'), satuan='%')
        self._tanpa_kontaminan(hasil)
        return hasil

    def _tanpa_kontaminan(self, hasil):
        """Mesin rekomendasi cuma lanjut kalau 'tidak terdeteksi' dicatat eksplisit. Data kosong dianggap belum diketahui."""
        for nama in ('Timbal (Pb)', 'Kadmium (Cd)'):
            jenis, _ = ContaminantType.objects.get_or_create(nama=nama)
            ContaminantFinding.objects.create(
                hasil=hasil, kontaminan=jenis, status=ContaminantFinding.Status.TIDAK_TERDETEKSI,
            )

    def _hasil_tercemar(self, lahan):
        hasil = HasilPemeriksaan.objects.create(
            lahan=lahan, asal=HasilPemeriksaan.Asal.MANDIRI, sumber='Laboratorium Lingkungan mitra',
            dibuat_oleh=lahan.owner, tanggal_pemeriksaan=hari(-12),
            ph=Decimal('6.1'), kelembapan=Decimal('29'), tekstur='lempung', bahan_organik=Decimal('2.0'),
        )
        timbal, _ = ContaminantType.objects.get_or_create(nama='Timbal (Pb)')
        ContaminantFinding.objects.create(
            hasil=hasil, kontaminan=timbal, status=ContaminantFinding.Status.TERDETEKSI, nilai=Decimal('380'),
            satuan='mg/kg', catatan='Kadar jauh di atas ambang. Dinilai risiko tinggi, perlu penilaian ahli.',
        )
        return hasil

    def _rencana(self, pemilik, hasil, slug_tujuan, status, luas, bibit, tanggal):
        """Hitung rekomendasi lewat mesin yang sama dengan aplikasi, ambil yang skornya tertinggi, simpan jadi rencana."""
        tujuan = ManagementGoal.objects.get(slug=slug_tujuan)
        asli = rekomendasi.fetch_environmental_data
        rekomendasi.fetch_environmental_data = lambda lahan: dict(CUACA_DEMO)
        try:
            hitungan = rekomendasi.calculate_recommendations(hasil.lahan, hasil, tujuan)
        finally:
            rekomendasi.fetch_environmental_data = asli
        if not hitungan['rekomendasi']:
            self.stdout.write(self.style.WARNING(f'Nggak ada tanaman yang lolos buat tujuan {slug_tujuan}, rencana dilewati.'))
            return None
        k = hitungan['rekomendasi'][0]
        snapshot = RecommendationSnapshot(
            lahan=hasil.lahan, hasil_pemeriksaan=hasil, tanaman=k.tanaman, tujuan=tujuan, skor=k.skor,
            alasan=k.alasan, input_snapshot=k.input_snapshot, data_lingkungan=k.data_lingkungan,
            kelengkapan_data=k.kelengkapan_data, versi_aturan=k.versi_aturan,
        )
        snapshot.full_clean()
        snapshot.save()
        plan = ManagementPlan(
            pemilik=pemilik, lahan=hasil.lahan, rekomendasi=snapshot, luas_tanam_m2=Decimal(luas), jumlah_bibit=bibit,
            tanggal_tanam=tanggal, status=status, catatan='Data demo.',
        )
        plan.full_clean()
        plan.save()
        return plan
