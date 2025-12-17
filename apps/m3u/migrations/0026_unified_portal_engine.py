# Generated migration for Unified Portal Engine

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0025_extended_features'),
    ]

    operations = [
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='portal_engine',
            field=models.CharField(
                choices=[
                    ('auto', 'Auto-Detect (Recommended)'),
                    ('unified', 'Unified (All Strategies)'),
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
