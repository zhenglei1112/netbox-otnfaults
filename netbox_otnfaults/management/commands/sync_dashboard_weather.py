from typing import Any
from django.core.management.base import BaseCommand
from ...services.dashboard_weather import sync_weather


class Command(BaseCommand):
    help = 'Sync free MET Norway and HKO data for Dashboard V2 (run every 10 minutes).'

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(str(sync_weather()))
