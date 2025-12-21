# Migration to convert 'fastest' engine to 'auto'

from django.db import migrations


def convert_fastest_to_auto(apps, schema_editor):
    """Convert all 'fastest' portal_engine values to 'auto'"""
    MACPortalGlobalSettings = apps.get_model('m3u', 'MACPortalGlobalSettings')
    
    try:
        settings = MACPortalGlobalSettings.objects.get(pk=1)
        if settings.portal_engine == 'fastest':
            settings.portal_engine = 'auto'
            settings.save(update_fields=['portal_engine'])
            print("Converted global portal_engine from 'fastest' to 'auto'")
    except MACPortalGlobalSettings.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0040_add_engine_cache'),
    ]

    operations = [
        migrations.RunPython(convert_fastest_to_auto, migrations.RunPython.noop),
    ]
