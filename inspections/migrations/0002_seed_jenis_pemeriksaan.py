from django.db import migrations

# Tiga jenis awal sesuai docs/DOMAIN.md. Bertingkat: tiap jenis memuat data jenis sebelumnya.
JENIS = [
    {
        'slug': 'dasar',
        'nama': 'Dasar',
        'tingkat': 1,
        'deskripsi': 'Mengukur pH, tekstur, kelembapan, dan bahan organik tanah.',
    },
    {
        'slug': 'unsur-hara',
        'nama': 'Unsur Hara',
        'tingkat': 2,
        'deskripsi': 'Semua data Dasar, ditambah pengukuran unsur hara seperti nitrogen, fosfor, dan kalium.',
    },
    {
        'slug': 'kontaminan',
        'nama': 'Kontaminan',
        'tingkat': 3,
        'deskripsi': 'Semua data Dasar, ditambah pemeriksaan kontaminan seperti logam berat.',
    },
]


def isi_jenis(apps, schema_editor):
    JenisPemeriksaan = apps.get_model('inspections', 'JenisPemeriksaan')
    for jenis in JENIS:
        JenisPemeriksaan.objects.update_or_create(
            slug=jenis['slug'],
            defaults={
                'nama': jenis['nama'],
                'tingkat': jenis['tingkat'],
                'deskripsi': jenis['deskripsi'],
                'aktif': True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0001_jenis_pemeriksaan'),
    ]

    operations = [
        # Mundur sengaja nggak ngapa-ngapain, biar data yang sudah diubah admin nggak ikut hilang
        migrations.RunPython(isi_jenis, migrations.RunPython.noop),
    ]
