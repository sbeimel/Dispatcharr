# Generated migration for Dispatcharr v0.19.0 enhancements

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0019_m3uaccount_priority'),  # Adjust based on your latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='m3uaccount',
            name='proxy',
            field=models.CharField(
                blank=True,
                help_text='HTTP proxy URL for streams (e.g., http://proxy:8080)',
                max_length=500,
                null=True
            ),
        ),
    ]
