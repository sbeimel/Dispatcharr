# Generated migration for buffering_timeout and buffering_speed fields

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0042_add_performance_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='buffering_timeout',
            field=models.IntegerField(
                default=15,
                validators=[
                    django.core.validators.MinValueValidator(5),
                    django.core.validators.MaxValueValidator(300)
                ],
                help_text='Stream below speed for X seconds → failover. 15s=schnell, 30s=normal, 60s=sehr tolerant. Range: 5-300s.'
            ),
        ),
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='buffering_speed',
            field=models.FloatField(
                default=1.0,
                validators=[
                    django.core.validators.MinValueValidator(0.1),
                    django.core.validators.MaxValueValidator(2.0)
                ],
                help_text='Min speed. 1.0=Echtzeit (streng), 0.8=20% langsamer OK, 0.5=sehr tolerant. Niedriger=weniger Failovers. Range: 0.1-2.0.'
            ),
        ),
    ]
