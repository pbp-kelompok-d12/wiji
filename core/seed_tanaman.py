"""Pemuat data awal tanaman. Dipakai migrasi (model historis) dan perintah `seed_tanaman` (model asli)."""
from .data_tanaman import KONTAMINAN, TANAMAN


def muat_tanaman_awal(Tanaman, ContaminantType, PlantReference, PlantContaminantCapability, ManagementGoal):
    """Isi atau perbarui tanaman awal berdasarkan nama. Aman dijalankan berulang kali."""
    jenis = {}
    for nama, deskripsi in KONTAMINAN.items():
        jenis[nama], _ = ContaminantType.objects.update_or_create(nama=nama, defaults={'deskripsi': deskripsi})

    tujuan = {g.slug: g for g in ManagementGoal.objects.all()}

    for data in TANAMAN:
        tanaman, _ = Tanaman.objects.update_or_create(
            nama=data['nama'],
            defaults={
                'nama_latin': data['nama_latin'],
                'fungsi': data['fungsi'],
                'deskripsi': data['deskripsi'],
                'kondisi_pertumbuhan': data['kondisi_pertumbuhan'],
                'kontaminan_ditangani': (
                    ', '.join(k[0] for k in data['kontaminan']) if data['kontaminan'] else None
                ),
                'tersedia_di_indonesia': True,
                'risiko_penggunaan': data['risiko'] or None,
                'sumber_penelitian': '; '.join(r[0] for r in data['refs']) + (
                    f". Catatan: {data['catatan']}" if data['catatan'] else ''
                ),
            },
        )
        tanaman.tujuan_pengelolaan.set([tujuan[slug] for slug in data['tujuan'] if slug in tujuan])

        # Referensi dan kemampuan dibuat ulang supaya nggak dobel kalau dijalankan lagi
        tanaman.referensi.all().delete()
        for sumber, tautan in data['refs']:
            PlantReference.objects.create(tanaman=tanaman, sumber_literatur=sumber, tautan=tautan)
        tanaman.kemampuan_kontaminan.all().delete()
        for nama, efektivitas, catatan in data['kontaminan']:
            PlantContaminantCapability.objects.create(
                tanaman=tanaman, kontaminan=jenis[nama], tingkat_efektivitas=efektivitas, catatan_khusus=catatan,
            )
    return len(TANAMAN)
