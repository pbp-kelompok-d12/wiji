from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from inspections.models import PesananPemeriksaan
from inspections.tampilan import langkah_status
from inspections.pemesanan import STATUS_BISA_BATAL, STATUS_BISA_JADWAL_ULANG

# Data di bawah ini cuma contoh. Nanti diganti query ke model lahan (Modul A),
# hasil tanah (Modul C), tanaman (Modul D), dan rekomendasi (Modul E).
# Pesanan aktif sudah dari data asli (Modul B), lihat _pesanan_aktif().
SAMPLE_KPIS = [
    {
        'icon': 'pin', 'label': 'Lahan terdaftar', 'value': 4,
        'chip': {'text': '+1 bulan ini', 'kind': 'up', 'trend': True},
        'segments': [True, True, True, False],
        'caption': '3 dari 4 lahan sudah punya koordinat.',
    },
    {
        'icon': 'flask', 'label': 'Pesanan aktif', 'value': 1,
        'chip': {'text': 'Dijadwalkan', 'kind': 'sky'},
        'caption': 'Satu lahan hanya boleh punya satu pesanan aktif.',
    },
    {
        'icon': 'doc', 'label': 'Hasil tanah', 'value': 3,
        'chip': {'text': '2 dari petugas', 'kind': 'paper'},
        'caption': 'Hasil final yang bisa dipakai buat rekomendasi.',
    },
    {
        'icon': 'sprout', 'label': 'Rencana tanam', 'value': 1,
        'chip': {'text': 'Akar wangi', 'kind': 'up'},
        'caption': 'Rencana pengelolaan yang sudah kamu simpan.',
    },
]

SAMPLE_LANDS = [
    {'name': 'Kebun Lereng Cibodas', 'place': 'Cianjur', 'area': '1.200 m²', 'use': 'Kebun sayur',
     'ph': 'pH 6,2', 'texture': 'Lempung', 'status': 'Pesanan aktif', 'kind': 'sky', 'icon': 'pin', 'warn': False},
    {'name': 'Pekarangan Dramaga', 'place': 'Bogor', 'area': '450 m²', 'use': 'Pekarangan',
     'ph': 'pH 5,8', 'texture': 'Liat', 'status': 'Siap dipesan', 'kind': 'up', 'icon': 'pin', 'warn': False},
    {'name': 'Sawah Tadah Hujan Ciampea', 'place': 'Bogor', 'area': '2.400 m²', 'use': 'Sawah',
     'ph': 'Belum ada', 'texture': 'data tanah', 'status': 'Perlu koordinat', 'kind': 'sand', 'icon': 'alert', 'warn': True},
]

SAMPLE_RECOMMENDATION = {
    'plant': 'Akar wangi', 'latin': 'Chrysopogon zizanioides', 'role': 'Pengendali erosi', 'score': 86,
    'reason': 'Cocok buat Kebun Lereng Cibodas: pH 6,2 pas, tanahnya lempung, dan lerengnya butuh penahan erosi.',
    'tags': ['pH 6,2', 'Lempung', 'Musim hujan'],
}

SAMPLE_CHART = {
    'title': 'Kelembapan tanah 7 hari', 'current': '42%', 'change': '-12% dari minggu lalu',
    'labels': ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'],
    'values': [46, 44, 49, 43, 45, 40, 42],
    'min': 36, 'max': 52, 'unit': '%',
}

SAMPLE_NOTES = [
    {'icon': 'check', 'tone': 'text-moss', 'text': 'pH 6,2 di Kebun Lereng Cibodas masih cocok buat sebagian besar tanaman penutup tanah.'},
    {'icon': 'drop', 'tone': 'text-clay', 'text': 'Kelembapan turun 12% dari minggu lalu. Penutup tanah bisa bantu menahan air.'},
    {'icon': 'shield', 'tone': 'text-sky', 'text': 'Hasil Pekarangan Dramaga dicatat petugas pada 14 Sep, jadi ditandai "hasil Wiji".'},
    {'icon': 'alert', 'tone': 'text-turmeric', 'text': 'Sawah Ciampea belum punya koordinat, lengkapi dulu buat memesan pemeriksaan.'},
]

SAMPLE_ACTIVITY = [
    {'icon': 'cal', 'title': 'Pesanan dijadwalkan', 'when': 'Hari ini, 09.30'},
    {'icon': 'doc', 'title': 'Hasil mandiri dimasukkan', 'when': 'Kemarin, 16.10'},
    {'icon': 'sprout', 'title': 'Rekomendasi dihitung', 'when': 'Kemarin, 16.12'},
    {'icon': 'check', 'title': 'Rencana disimpan', 'when': '12 Okt, 10.05'},
    {'icon': 'pin', 'title': 'Lahan ditambahkan', 'when': '9 Okt, 14.40'},
]


# Label garis status dipendekkan biar muat di kartu dashboard
LABEL_SINGKAT = {
    'Diajukan': 'Diajukan', 'Dikonfirmasi': 'Konfirmasi', 'Dijadwalkan': 'Jadwal',
    'Sampel diambil': 'Sampel', 'Diproses': 'Proses', 'Selesai': 'Selesai',
}


def _pesanan_aktif(pemilik):
    """Pesanan berjalan paling baru milik pemilik, lengkap dengan garis statusnya. None kalau nggak ada."""
    pesanan = (
        PesananPemeriksaan.objects.filter(lahan__owner=pemilik)
        .exclude(status__in=PesananPemeriksaan.STATUS_AKHIR)
        .select_related('lahan', 'jenis', 'petugas')
        .first()
    )
    if pesanan is None:
        return None
    return {
        'pesanan': pesanan,
        'steps': [
            {'label': LABEL_SINGKAT[l['label']], 'state': l['keadaan']} for l in langkah_status(pesanan)
        ],
        'bisa_jadwal_ulang': pesanan.status in STATUS_BISA_JADWAL_ULANG,
        'bisa_batal': pesanan.status in STATUS_BISA_BATAL,
    }


# Warna chip di kartu angka, mengikuti status pesanan terbaru
KIND_STATUS = {
    'diajukan': 'sand', 'dikonfirmasi': 'paper', 'dijadwalkan': 'sky',
    'sampel_diambil': 'sky', 'diproses': 'paper',
}


def _kpi_pesanan(pemilik, pesanan_aktif):
    """Kartu angka 'Pesanan aktif' dari data asli."""
    jumlah = PesananPemeriksaan.objects.filter(lahan__owner=pemilik).exclude(
        status__in=PesananPemeriksaan.STATUS_AKHIR,
    ).count()
    kartu = dict(SAMPLE_KPIS[1], value=jumlah)
    if pesanan_aktif:
        pesanan = pesanan_aktif['pesanan']
        kartu['chip'] = {'text': pesanan.get_status_display(), 'kind': KIND_STATUS.get(pesanan.status, 'paper')}
    else:
        kartu['chip'] = {'text': 'Belum ada', 'kind': 'paper'}
    return kartu


@login_required
def home(request):
    # Petugas dan admin punya dashboard sendiri nanti (lihat docs/WORK-PLAN.md, issue 07)
    if not request.user.is_owner:
        return render(request, 'dashboard/pending.html', {'active_nav': 'dashboard'})

    pesanan_aktif = _pesanan_aktif(request.user)
    kpis = list(SAMPLE_KPIS)
    kpis[1] = _kpi_pesanan(request.user, pesanan_aktif)

    context = {
        'active_nav': 'dashboard',
        'greeting_name': request.user.first_name.split()[0] if request.user.first_name else request.user.username,
        'kpis': kpis,
        'lands': SAMPLE_LANDS,
        'recommendation': SAMPLE_RECOMMENDATION,
        'order': pesanan_aktif,
        'chart': SAMPLE_CHART,
        'notes': SAMPLE_NOTES,
        'activity': SAMPLE_ACTIVITY,
    }
    return render(request, 'dashboard/owner.html', context)
