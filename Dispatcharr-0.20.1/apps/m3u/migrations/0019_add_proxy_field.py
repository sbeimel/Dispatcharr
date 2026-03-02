# Generated migration for proxy field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0018_add_profile_custom_properties'),
    ]

    operations = [
        migrations.AddField(
            model_name='m3uaccount',
            name='proxy',
            field=models.CharField(
                blank=True,
                help_text='HTTP Proxy URL (e.g., http://proxy:port)',
                max_length=500,
                null=True
            ),
        ),
    ]
