from django.db import migrations

TUJUAN = [
    {
        'slug': 'pemulihan-tanah-tercemar',
        'nama': 'Pemulihan tanah tercemar',
        'deskripsi': 'Memulihkan tanah yang tercemar logam berat atau polutan lain.',
    },
    {
        'slug': 'pencegahan-erosi',
        'nama': 'Pencegahan erosi',
        'deskripsi': 'Menjaga lapisan tanah agar tidak terkikis air atau angin.',
    },
    {
        'slug': 'peningkatan-kesuburan',
        'nama': 'Peningkatan kesuburan',
        'deskripsi': 'Memperbaiki kandungan hara dan bahan organik tanah.',
    },
    {
        'slug': 'konservasi-air',
        'nama': 'Konservasi air',
        'deskripsi': 'Meningkatkan kemampuan tanah menyimpan dan mengatur air.',
    },
    {
        'slug': 'pangan-keluarga',
        'nama': 'Pangan keluarga',
        'deskripsi': 'Memanfaatkan lahan untuk memenuhi kebutuhan pangan sehari-hari.',
    },
]


def seed_tujuan(apps, schema_editor):
    ManagementGoal = apps.get_model('lands', 'ManagementGoal')
    for tujuan in TUJUAN:
        ManagementGoal.objects.update_or_create(
            slug=tujuan['slug'],
            defaults={
                'nama': tujuan['nama'],
                'deskripsi': tujuan['deskripsi'],
                'aktif': True,
            },
        )


def hapus_tujuan(apps, schema_editor):
    ManagementGoal = apps.get_model('lands', 'ManagementGoal')
    ManagementGoal.objects.filter(
        slug__in=[tujuan['slug'] for tujuan in TUJUAN]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('lands', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_tujuan, hapus_tujuan),
    ]
