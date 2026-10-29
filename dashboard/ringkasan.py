"""Angka dan daftar asli buat dashboard pemilik (menggantikan data contoh)."""
from inspections.models import PesananPemeriksaan, RiwayatPesanan
from inspections.pemesanan import STATUS_BISA_BATAL, STATUS_BISA_JADWAL_ULANG
from inspections.tampilan import langkah_status
from lands.models import Lahan
from recommendations.models import ManagementPlan, RecommendationSnapshot
from soil_results.models import HasilPemeriksaan

# Label garis status dipendekkan biar muat di kartu dashboard
LABEL_SINGKAT = {
    'Diajukan': 'Diajukan', 'Dikonfirmasi': 'Konfirmasi', 'Dijadwalkan': 'Jadwal',
    'Sampel diambil': 'Sampel', 'Diproses': 'Proses', 'Selesai': 'Selesai',
}

# Warna chip di kartu angka, mengikuti status pesanan terbaru
KIND_STATUS = {
    'diajukan': 'sand', 'dikonfirmasi': 'paper', 'dijadwalkan': 'sky',
    'sampel_diambil': 'sky', 'diproses': 'paper',
}


def pesanan_aktif(pemilik):
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
        'steps': [{'label': LABEL_SINGKAT[l['label']], 'state': l['keadaan']} for l in langkah_status(pesanan)],
        'bisa_jadwal_ulang': pesanan.status in STATUS_BISA_JADWAL_ULANG,
        'bisa_batal': pesanan.status in STATUS_BISA_BATAL,
    }


def _kpi_lahan(lahan_list):
    total = len(lahan_list)
    lengkap = sum(1 for l in lahan_list if not l.adalah_draf)
    draf = total - lengkap
    return {
        'icon': 'pin', 'label': 'Lahan terdaftar', 'value': total,
        'chip': {'text': f'{draf} draf' if draf else ('Semua lengkap' if total else 'Belum ada'),
                 'kind': 'sand' if draf else ('up' if total else 'paper')},
        'segments': [not l.adalah_draf for l in lahan_list[:6]] or None,
        'caption': f'{lengkap} dari {total} lahan sudah lengkap.' if total else 'Tambahkan lahan pertamamu.',
    }


def _kpi_pesanan(pemilik, aktif):
    jumlah = PesananPemeriksaan.objects.filter(lahan__owner=pemilik).exclude(
        status__in=PesananPemeriksaan.STATUS_AKHIR,
    ).count()
    chip = (
        {'text': aktif['pesanan'].get_status_display(), 'kind': KIND_STATUS.get(aktif['pesanan'].status, 'paper')}
        if aktif else {'text': 'Belum ada', 'kind': 'paper'}
    )
    return {
        'icon': 'flask', 'label': 'Pesanan aktif', 'value': jumlah, 'chip': chip,
        'caption': 'Satu lahan hanya boleh punya satu pesanan aktif.',
    }


def _kpi_hasil(hasil_qs):
    jumlah = hasil_qs.count()
    dari_petugas = hasil_qs.filter(asal=HasilPemeriksaan.Asal.WIJI).count()
    return {
        'icon': 'doc', 'label': 'Hasil tanah', 'value': jumlah,
        'chip': {'text': f'{dari_petugas} dari petugas' if jumlah else 'Belum ada', 'kind': 'paper'},
        'caption': 'Hasil pemeriksaan buat lahanmu, dari petugas atau yang kamu masukkan.',
    }


def _kpi_rencana(rencana_qs):
    jumlah = rencana_qs.count()
    terbaru = rencana_qs.select_related('rekomendasi__tanaman').first()
    return {
        'icon': 'sprout', 'label': 'Rencana tanam', 'value': jumlah,
        'chip': {'text': terbaru.rekomendasi.tanaman.nama, 'kind': 'up'} if terbaru else {'text': 'Belum ada', 'kind': 'paper'},
        'caption': 'Rencana pengelolaan yang sudah kamu simpan.',
    }


def _kartu_lahan(lahan):
    hasil = lahan.soil_results.order_by('-tanggal_pemeriksaan', '-dibuat_pada').first()
    if lahan.adalah_draf:
        status, kind, siap = 'Perlu dilengkapi', 'sand', False
    elif lahan.punya_pesanan_aktif():
        status, kind, siap = 'Pesanan aktif', 'sky', False
    else:
        status, kind, siap = 'Siap dipesan', 'up', True
    return {
        'lahan': lahan, 'status': status, 'kind': kind, 'bisa_pesan': siap,
        'ph': f'pH {hasil.ph}'.replace('.', ',') if hasil and hasil.ph is not None else 'Belum ada',
        'tekstur': (hasil.tekstur or 'data tanah') if hasil else 'data tanah',
    }


def _rekomendasi_terbaik(pemilik):
    snap = (
        RecommendationSnapshot.objects.filter(lahan__owner=pemilik)
        .select_related('tanaman', 'lahan').order_by('-skor', '-dibuat_pada').first()
    )
    if snap is None:
        return None
    ph, tekstur = snap.input_snapshot.get('ph'), snap.input_snapshot.get('tekstur')
    return {
        'snap': snap,
        'alasan': (snap.alasan or [''])[0],
        'tags': [t for t in (f'pH {ph}'.replace('.', ',') if ph else '', tekstur) if t],
    }


def _catatan(pemilik, lahan_list, aktif, rekomendasi):
    """Catatan singkat dari kondisi data pemilik sendiri."""
    catatan = []
    draf = [l for l in lahan_list if l.adalah_draf]
    if draf:
        catatan.append({'icon': 'alert', 'tone': 'text-turmeric',
                        'text': f'{len(draf)} lahan belum lengkap. Lengkapi datanya (termasuk koordinat) supaya bisa dipesankan pemeriksaan.'})
    if aktif:
        p = aktif['pesanan']
        catatan.append({'icon': 'cal', 'tone': 'text-sky',
                        'text': f'Pesanan {p.kode} untuk {p.lahan.nama or "lahanmu"} berstatus {p.get_status_display()}.'})
    if rekomendasi:
        s = rekomendasi['snap']
        catatan.append({'icon': 'check', 'tone': 'text-moss',
                        'text': f'{s.tanaman.nama} paling cocok buat {s.lahan.nama or "lahanmu"} (skor {s.skor}).'})
    siap = [l for l in lahan_list if not l.adalah_draf and not l.punya_pesanan_aktif()]
    if siap and not aktif:
        catatan.append({'icon': 'flask', 'tone': 'text-moss',
                        'text': f'{siap[0].nama or "Lahanmu"} siap dipesankan pemeriksaan tanah.'})
    return catatan


def _aktivitas(pemilik, batas=5):
    """Kejadian terbaru dari semua modul, digabung dan diurutkan dari yang paling baru."""
    kejadian = []
    for r in RiwayatPesanan.objects.filter(pesanan__lahan__owner=pemilik).select_related('pesanan').order_by('-dibuat_pada')[:batas]:
        judul = r.get_status_sesudah_display() if r.jenis == 'status' else r.get_jenis_display()
        kejadian.append({'icon': 'cal', 'title': f'{r.pesanan.kode}: {judul}', 'waktu': r.dibuat_pada})
    for l in Lahan.objects.filter(owner=pemilik, diarsipkan=False).order_by('-dibuat_pada')[:batas]:
        kejadian.append({'icon': 'pin', 'title': f'Lahan ditambahkan: {l.nama or "tanpa nama"}', 'waktu': l.dibuat_pada})
    for h in HasilPemeriksaan.objects.filter(lahan__owner=pemilik).select_related('lahan').order_by('-dibuat_pada')[:batas]:
        kejadian.append({'icon': 'doc', 'title': f'Hasil tanah dicatat: {h.lahan.nama or "lahan"}', 'waktu': h.dibuat_pada})
    for p in ManagementPlan.objects.filter(pemilik=pemilik).order_by('-dibuat_pada')[:batas]:
        kejadian.append({'icon': 'check', 'title': 'Rencana disimpan', 'waktu': p.dibuat_pada})
    return sorted(kejadian, key=lambda k: k['waktu'], reverse=True)[:batas]


def ringkasan_pemilik(pemilik):
    """Semua bahan dashboard pemilik dari data asli."""
    lahan_list = list(Lahan.objects.filter(owner=pemilik, diarsipkan=False).order_by('-dibuat_pada'))
    hasil_qs = HasilPemeriksaan.objects.filter(lahan__owner=pemilik)
    rencana_qs = ManagementPlan.objects.filter(pemilik=pemilik).order_by('-dibuat_pada')
    aktif = pesanan_aktif(pemilik)
    rekomendasi = _rekomendasi_terbaik(pemilik)
    return {
        'kpis': [_kpi_lahan(lahan_list), _kpi_pesanan(pemilik, aktif), _kpi_hasil(hasil_qs), _kpi_rencana(rencana_qs)],
        'lahan_kartu': [_kartu_lahan(l) for l in lahan_list[:3]],
        'rekomendasi': rekomendasi,
        'order': aktif,
        'hasil_terbaru': hasil_qs.select_related('lahan').order_by('-tanggal_pemeriksaan', '-dibuat_pada')[:3],
        'catatan': _catatan(pemilik, lahan_list, aktif, rekomendasi),
        'aktivitas': _aktivitas(pemilik),
    }
