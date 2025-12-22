# Generated migration for proxy field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dispatcharr_m3u', '0015_m3uaccount_priority'),
    ]

    operations = [
        migrations.AddField(
            model_name='m3uaccount',
            name='proxy',
            field=models.CharField(
                blank=True,
                help_text='HTTP proxy URL for FFmpeg streams (e.g., http://proxy:8080)',
                max_length=500,
                null=True,
            ),
        ),
    ]
