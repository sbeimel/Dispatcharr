# apps/m3u/apps.py
from django.apps import AppConfig

class M3UConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.m3u'
    verbose_name = "M3U Management"

    def ready(self):
        import apps.m3u.signals  # ensures M3U signals get registered
