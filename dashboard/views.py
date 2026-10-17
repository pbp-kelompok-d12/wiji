from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# Semua data di bawah ini cuma contoh. Nanti diganti query ke model lahan (Modul A),
# pesanan (Modul B), hasil tanah (Modul C), tanaman (Modul D), dan rekomendasi (Modul E).
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

# Urutan status pesanan sesuai docs/DOMAIN.md. state: done, now, atau kosong
SAMPLE_ORDER = {
    'code': 'WJ-0012', 'type': 'Pemeriksaan dasar', 'land': 'Kebun Lereng Cibodas',
    'schedule': '3 Okt, Pagi', 'officer': 'Budi S.',
    'steps': [
        {'label': 'Diajukan', 'state': 'done'}, {'label': 'Konfirmasi', 'state': 'done'},
        {'label': 'Jadwal', 'state': 'now'}, {'label': 'Sampel', 'state': ''},
        {'label': 'Proses', 'state': ''}, {'label': 'Selesai', 'state': ''},
    ],
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


@login_required
def home(request):
    # Petugas dan admin punya dashboard sendiri nanti (lihat docs/WORK-PLAN.md, issue 07)
    if not request.user.is_owner:
        return render(request, 'dashboard/pending.html', {'active_nav': 'dashboard'})

    context = {
        'active_nav': 'dashboard',
        'greeting_name': request.user.first_name.split()[0] if request.user.first_name else request.user.username,
        'kpis': SAMPLE_KPIS,
        'lands': SAMPLE_LANDS,
        'recommendation': SAMPLE_RECOMMENDATION,
        'order': SAMPLE_ORDER,
        'chart': SAMPLE_CHART,
        'notes': SAMPLE_NOTES,
        'activity': SAMPLE_ACTIVITY,
    }
    return render(request, 'dashboard/owner.html', context)
