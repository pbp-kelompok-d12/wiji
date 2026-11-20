"""Isi data demo buat modul pemesanan: satu admin, petugas sintetis, satu pemilik demo dengan lahan, dan 8 pesanan.

Delapan pesanan itu mencakup ketujuh status (plus satu pesanan yang pernah dijadwal ulang),
lengkap dengan riwayatnya, lewat fungsi yang sama dengan aplikasi aslinya.

Pakai: python manage.py seed_pesanan_demo [--ulang]
Data bisa dibuat ulang kapan saja. Akun demo dipakai buat percobaan, jangan dipakai di server asli.
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from inspections import services
from inspections.models import JenisPemeriksaan, PesananPemeriksaan
from inspections.pemesanan import ajukan_jadwal_ulang, batalkan_pesanan
from lands.models import Lahan

Status = PesananPemeriksaan.Status

PASSWORD_DEMO = 'demo-wiji-123'
PEMILIK = {'username': 'pemilik.demo', 'first_name': 'Sari Rahayu'}
ADMIN = {'username': 'admin.demo', 'first_name': 'Admin Wiji'}
PETUGAS = [
    {'username': 'petugas.bima', 'first_name': 'Bima Pratama'},
    {'username': 'petugas.laras', 'first_name': 'Laras Wulandari'},
    {'username': 'petugas.dimas', 'first_name': 'Dimas Aryo'},
]
# nama lahan, kota, jenis, status akhir yang dituju
LAHAN_DAN_PESANAN = [
    ('Kebun Lereng Cibodas', 'Cianjur', 'dasar', 'dijadwalkan'),
    ('Kebun Kopi Sukamakmur', 'Bogor', 'kontaminan', 'diajukan'),
    ('Kebun Cempaka', 'Bogor', 'dasar', 'dikonfirmasi'),
    ('Ladang Cisarua', 'Bogor', 'unsur-hara', 'sampel_diambil'),
    ('Kebun Salak Tenjolaya', 'Bogor', 'unsur-hara', 'diproses'),
    ('Pekarangan Dramaga', 'Bogor', 'unsur-hara', 'selesai'),
    ('Sawah Tadah Hujan Ciampea', 'Bogor', 'dasar', 'dibatalkan'),
    ('Ladang Jagung Ciawi', 'Bogor', 'dasar', 'jadwal_ulang'),
]


def hari(n):
    return date.today() + timedelta(days=n)


class Command(BaseCommand):
    help = 'Isi data demo pemesanan pemeriksaan (petugas, lahan, dan 8 pesanan dengan riwayat).'

    def add_arguments(self, parser):
        parser.add_argument('--ulang', action='store_true', help='Hapus data demo lama, lalu bikin lagi.')

    @transaction.atomic
    def handle(self, *args, **opsi):
        if opsi['ulang']:
            self._hapus_demo()

        # Akun admin dibuat dulu dan selalu dicek, jadi data demo lama pun dapat akun admin-nya
        self._akun(ADMIN, role=User.Role.OWNER, is_staff=True)
        pemilik, baru = self._akun(PEMILIK, role=User.Role.OWNER)
        if not baru and PesananPemeriksaan.objects.filter(lahan__owner=pemilik).exists():
            self.stdout.write('Data demo sudah ada. Pakai --ulang kalau mau dibuat ulang.')
            return

        petugas = [self._akun(p, role=User.Role.OFFICER)[0] for p in PETUGAS]
        for i, (nama, kota, slug, tujuan) in enumerate(LAHAN_DAN_PESANAN):
            lahan = Lahan.objects.create(
                owner=pemilik, nama=nama, alamat=f'{kota}, Jawa Barat',
                latitude=f'-6.{600 + i * 13}', longitude=f'106.{800 + i * 9}',
                luas_m2=400 + i * 250, penggunaan=Lahan.Penggunaan.KEBUN,
            )
            self._pesanan(lahan, JenisPemeriksaan.objects.get(slug=slug), tujuan, petugas[i % len(petugas)], pemilik)

        self.stdout.write(self.style.SUCCESS(
            f'Selesai: {len(LAHAN_DAN_PESANAN)} pesanan demo. Password semua akun demo: {PASSWORD_DEMO}\n'
            f'  pemilik : {PEMILIK["username"]}\n'
            f'  admin   : {ADMIN["username"]}\n'
            f'  petugas : {", ".join(p["username"] for p in PETUGAS)}'
        ))

    def _akun(self, data, role, **tambahan):
        user, baru = User.objects.get_or_create(
            username=data['username'], defaults={'first_name': data['first_name'], 'role': role, **tambahan},
        )
        if baru:
            user.set_password(PASSWORD_DEMO)
            user.save(update_fields=['password'])
        return user, baru

    def _hapus_demo(self):
        pemilik = User.objects.filter(username=PEMILIK['username']).first()
        if pemilik:
            PesananPemeriksaan.objects.filter(lahan__owner=pemilik).delete()
            Lahan.objects.filter(owner=pemilik).delete()

    def _pesanan(self, lahan, jenis, tujuan, petugas, pemilik):
        """Bikin satu pesanan lalu majukan statusnya lewat services, jadi riwayatnya ikut tercatat."""
        selesai = tujuan == 'selesai'
        # Pesanan yang sudah selesai tanggalnya di masa lalu, sisanya di depan
        pesanan = PesananPemeriksaan.objects.create(
            lahan=lahan, jenis=jenis, sesi_usulan='pagi',
            tanggal_usulan=hari(-10) if selesai else hari(5), catatan='Parkir motor di warung depan.',
        )
        services.catat_riwayat(pesanan, pemilik, sesudah=Status.DIAJUKAN)
        admin = None  # penugasan dan jadwal dari admin, nggak diisi nama pelaku di data demo

        if tujuan == 'diajukan':
            return
        if tujuan == 'dibatalkan':
            batalkan_pesanan(pesanan, pemilik, 'Salah pilih lahan, nanti dipesan ulang.')
            return

        services.konfirmasi_pesanan(pesanan, petugas, admin)
        if tujuan == 'dikonfirmasi':
            return

        services.jadwalkan_pesanan(pesanan, hari(-8) if selesai else hari(6), 'pagi', admin)
        if tujuan == 'jadwal_ulang':
            ajukan_jadwal_ulang(pesanan, pemilik, hari(12), 'siang', 'Ada acara keluarga di hari itu.')
            return
        for status in (Status.SAMPEL_DIAMBIL, Status.DIPROSES, Status.SELESAI):
            if tujuan == 'dijadwalkan':
                break
            services.ubah_status(pesanan, status, petugas)
            if status.value == tujuan:
                break
