# Generated manually to add missing is_adult fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('channels', '0019_auto_20241201_1200'),  # Adjust to your latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='channel',
            name='is_adult',
            field=models.BooleanField(default=False, help_text='Mark channel as adult content'),
        ),
        migrations.AddField(
            model_name='stream',
            name='is_adult',
            field=models.BooleanField(default=False, help_text='Mark stream as adult content'),
        ),
    ]