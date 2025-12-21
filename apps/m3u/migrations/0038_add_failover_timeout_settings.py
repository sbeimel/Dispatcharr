# Generated migration for failover timeout settings

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0037_add_stream_performance_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='failover_total_timeout',
            field=models.IntegerField(
                default=60,
                help_text='Maximum time in seconds to find a working stream before giving up (10-300)',
                validators=[
                    django.core.validators.MinValueValidator(10),
                    django.core.validators.MaxValueValidator(300)
                ]
            ),
        ),
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='failover_timeout_action',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('stop', 'Stop - Give up and show error'),
                    ('loop', 'Loop - Keep trying indefinitely'),
                ],
                default='stop',
                help_text='What to do when failover timeout is reached'
            ),
        ),
        migrations.AddField(
            model_name='macportalglobalsettings',
            name='max_failover_attempts',
            field=models.IntegerField(
                default=10,
                help_text='Maximum number of stream switch attempts (1-50)',
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(50)
                ]
            ),
        ),
    ]
