from django.apps import AppConfig
from . import ssdp

class HdhrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hdhr'
    verbose_name = "HDHomeRun Emulation"
    def ready(self):
        # Start SSDP services when the app is ready
        ssdp.start_ssdp()
