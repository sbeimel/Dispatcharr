# Generated migration to add 'istb' engine option

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0029_remove_unified_engine'),
    ]

    operations = [
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
                    ('istb', 'iSTB (iOS Emulator Style)'),
                ],
                default='auto',
                help_text='Portal authentication engine to use',
                max_length=20,
            ),
        ),
    ]
