# your_app/management/commands/update_column.py

from django.core.management.base import BaseCommand
from core.models import CoreSettings, NETWORK_ACCESS


class Command(BaseCommand):
    help = "Reset network access settings"

    def handle(self, *args, **options):
        setting = CoreSettings.objects.get(key=NETWORK_ACCESS)
        setting.value = "{}"
        setting.save()
