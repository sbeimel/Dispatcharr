# Generated manually to add missing is_adult field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('m3u', '0019_m3uaccount_proxy'),
    ]

    operations = [
        migrations.AddField(
            model_name='m3uaccount',
            name='is_adult',
            field=models.BooleanField(default=False, help_text='Mark M3U account as containing adult content'),
        ),
    ]