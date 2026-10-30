from django.db import migrations

from core.seed_tanaman import muat_tanaman_awal


def isi_tanaman(apps, schema_editor):
    muat_tanaman_awal(
        apps.get_model('core', 'Tanaman'),
        apps.get_model('core', 'ContaminantType'),
        apps.get_model('core', 'PlantReference'),
        apps.get_model('core', 'PlantContaminantCapability'),
        apps.get_model('lands', 'ManagementGoal'),
    )


class Migration(migrations.Migration):
    """Katalog awal biar ada minimal 50 tanaman begitu aplikasi pertama kali di-deploy."""

    dependencies = [
        ('core', '0002_contaminanttype_tanaman_tujuan_pengelolaan_and_more'),
        ('lands', '0002_seed_management_goal'),
    ]

    operations = [
        # Nggak dibalik: tanaman yang sudah diedit tim nggak boleh ikut terhapus
        migrations.RunPython(isi_tanaman, migrations.RunPython.noop),
    ]
