from django.core.management.base import BaseCommand

from core.models import ContaminantType, PlantContaminantCapability, PlantReference, Tanaman
from core.seed_tanaman import muat_tanaman_awal
from lands.models import ManagementGoal


class Command(BaseCommand):
    help = 'Isi atau perbarui katalog tanaman awal (53 tanaman). Aman dijalankan berulang kali.'

    def handle(self, *args, **options):
        jumlah = muat_tanaman_awal(Tanaman, ContaminantType, PlantReference, PlantContaminantCapability, ManagementGoal)
        self.stdout.write(self.style.SUCCESS(f'{jumlah} tanaman awal sudah dimuat. Total di katalog: {Tanaman.objects.count()}.'))
