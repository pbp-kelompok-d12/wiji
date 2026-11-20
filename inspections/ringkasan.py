"""Angka dan daftar buat dashboard admin dan petugas."""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import User

from .models import PesananPemeriksaan
from .views_petugas import tugas_petugas

Status = PesananPemeriksaan.Status

STATUS_BERJALAN = (Status.DIKONFIRMASI, Status.DIJADWALKAN, Status.SAMPEL_DIAMBIL, Status.DIPROSES)


def _semua():
    return PesananPemeriksaan.objects.select_related('lahan', 'lahan__owner', 'jenis', 'petugas')


def ringkasan_admin(batas=5):
    """Yang perlu admin kerjakan: pesanan yang belum ditugaskan, jadwal terdekat, dan beban tiap petugas."""
    semua = _semua()
    hari_ini = timezone.localdate()
    return {
        'jumlah_perlu_ditugaskan': semua.filter(status=Status.DIAJUKAN).count(),
        'jumlah_perlu_jadwal': semua.filter(status=Status.DIKONFIRMASI).count(),
        'jumlah_berjalan': semua.filter(status__in=STATUS_BERJALAN).count(),
        'jumlah_selesai': semua.filter(status=Status.SELESAI).count(),
        # Yang paling lama menunggu di atas
        'perlu_ditugaskan': semua.filter(status=Status.DIAJUKAN).order_by('dibuat_pada', 'id')[:batas],
        'perlu_jadwal': semua.filter(status=Status.DIKONFIRMASI).order_by('dibuat_pada', 'id')[:batas],
        'jadwal_terdekat': semua.filter(status=Status.DIJADWALKAN, tanggal_final__gte=hari_ini).order_by('tanggal_final', 'id')[:batas],
        'beban_petugas': list(
            User.objects.filter(role=User.Role.OFFICER, is_active=True)
            .annotate(aktif=Count('tugas_pemeriksaan', filter=Q(tugas_pemeriksaan__status__in=STATUS_BERJALAN)))
            .order_by('-aktif', 'first_name', 'username')
        ),
    }


def ringkasan_petugas(petugas, batas=5):
    """Tugas milik petugas: yang perlu tindakan sekarang dan yang akan datang."""
    tugas = tugas_petugas(petugas)
    return {
        'jumlah_aktif': tugas.filter(status__in=STATUS_BERJALAN).count(),
        'jumlah_siap_diambil': tugas.filter(status=Status.DIJADWALKAN).count(),
        'jumlah_dikerjakan': tugas.filter(status__in=(Status.SAMPEL_DIAMBIL, Status.DIPROSES)).count(),
        'jumlah_selesai': tugas.filter(status=Status.SELESAI).count(),
        # Sampel sudah diambil, tinggal mulai diproses
        'perlu_diproses': tugas.filter(status=Status.SAMPEL_DIAMBIL).order_by('tanggal_final', 'id')[:batas],
        'mendatang': tugas.filter(status__in=(Status.DIKONFIRMASI, Status.DIJADWALKAN)).order_by('tanggal_final', 'id')[:batas],
        'menunggu_hasil': tugas.filter(status=Status.DIPROSES).order_by('tanggal_final', 'id')[:batas],
    }
