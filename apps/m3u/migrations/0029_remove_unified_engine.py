# Generated migration to remove 'unified' engine option
# 'unified' was identical to 'auto' and has been removed

from django.db import migrations, models


def convert_unified_to_auto(apps, schema_editor):
    """Convert any 'unified' portal_engine values to 'auto'."""
    MACPortalGlobalSettings = apps.get_model('m3u', 'MACPortalGlobalSettings')
    
    # Update any settings that have 'unified' to 'auto'
    updated = MACPortalGlobalSettings.objects.filter(portal_engine='unified').update(portal_engine='auto')
    if updated:
        print(f"  Converted {updated} MACPortalGlobalSettings from 'unified' to 'auto'")


def reverse_migration(apps, schema_editor):
    """Reverse migration - no action needed."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0028_fix_invalid_account_types'),
    ]

    operations = [
        migrations.RunPython(convert_unified_to_auto, reverse_migration),
        migrations.AlterField(
            model_name='macportalglobalsettings',
            name='portal_engine',
            field=models.CharField(
                choices=[
                    ('auto', 'Auto-Detect (Recommended)'),
                    ('allinone', 'AllinOne Best-of-All (Empfohlen)'),
                    ('macreplay', 'MacReplayXC (Standard)'),
                    ('estalker', 'EStalker (Enigma2 Style)'),
                    ('boxpirate', 'BoxPirate (Dreambox Style)'),
                    ('ob2_2025', 'OB2_2025 (Extended Metrics)'),
                ],
                default='auto',
                help_text='Portal authentication engine to use',
                max_length=20,
            ),
        ),
    ]
