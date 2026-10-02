from django.shortcuts import render

# Data sementara buat preview katalog. Nanti ganti pakai model Plant kalau Modul D udah jadi.
FEATURED_PLANTS = [
    {'name': 'Akar wangi', 'latin': 'Chrysopogon zizanioides', 'role': 'Pengendali erosi'},
    {'name': 'Kalopo', 'latin': 'Calopogonium mucunoides', 'role': 'Penutup tanah'},
    {'name': 'Gamal', 'latin': 'Gliricidia sepium', 'role': 'Penambah nitrogen'},
    {'name': 'Kara benguk', 'latin': 'Mucuna pruriens', 'role': 'Bahan organik'},
]

OWNER_STEPS = [
    'Cari lokasi lahan langsung di peta.',
    'Pesan pemeriksaan dan pantau statusnya.',
    'Bandingkan tanaman dengan skor dan alasan.',
    'Simpan pilihan sebagai rencana tanam.',
]

# Contoh isi dashboard di landing page, bukan data asli
SAMPLE_ORDERS = [
    {'land': 'Kebun Lereng Cibodas', 'note': 'WJ-0012 · 3 Okt, Pagi', 'status': 'Dijadwalkan', 'badge': 'badge-sky'},
    {'land': 'Pekarangan Dramaga', 'note': 'WJ-0009 · hasil final 14 Sep', 'status': 'Selesai', 'badge': 'badge-leaf'},
    {'land': 'Sawah Tadah Hujan Ciampea', 'note': 'Belum ada data tanah', 'status': 'Pesan pemeriksaan', 'badge': 'badge-paper'},
]


def landing(request):
    context = {
        'featured_plants': FEATURED_PLANTS,
        'owner_steps': OWNER_STEPS,
        'sample_orders': SAMPLE_ORDERS,
    }
    return render(request, 'core/landing.html', context)
