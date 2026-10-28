from datetime import date, timedelta

from accounts.models import User
from lands.models import Lahan

from ..models import JenisPemeriksaan, PesananPemeriksaan


def buat_pemilik(username='sari'):
    return User.objects.create_user(username, f'{username}@contoh.id', 'tanah12345')


def buat_lahan(pemilik, **kwargs):
    data = {
        'nama': 'Kebun Cibodas', 'alamat': 'Cianjur', 'latitude': '-6.8', 'longitude': '107.0',
        'luas_m2': 1200, 'penggunaan': Lahan.Penggunaan.KEBUN, **kwargs,
    }
    return Lahan.objects.create(owner=pemilik, **data)


def buat_pesanan(lahan, **kwargs):
    data = {
        'jenis': JenisPemeriksaan.objects.get(slug='dasar'),
        'tanggal_usulan': date.today() + timedelta(days=3),
        'sesi_usulan': PesananPemeriksaan.Sesi.PAGI,
        **kwargs,
    }
    return PesananPemeriksaan.objects.create(lahan=lahan, **data)
