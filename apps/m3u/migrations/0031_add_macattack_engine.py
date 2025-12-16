# Generated migration for adding MacAttack engine option

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0030_add_istb_engine'),
    ]

    operations = [
        # Update PORTAL_ENGINE_CHOICES to include 'macattack'
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
                    ('macattack', 'MacAttack (X-Random, api_sig 262)'),
                ],
                default='auto',
                help_text='Portal authentication engine to use',
                max_length=20,
            ),
        ),
    ]
