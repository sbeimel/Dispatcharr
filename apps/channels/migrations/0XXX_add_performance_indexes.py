# Generated manually for performance optimization
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('channels', '0XXX_previous_migration'),  # Replace with actual previous migration
    ]

    operations = [
        # Add indexes to Stream for faster queries
        migrations.AddIndex(
            model_name='stream',
            index=models.Index(fields=['m3u_account'], name='stream_account_idx'),
        ),
        migrations.AddIndex(
            model_name='stream',
            index=models.Index(fields=['stream_hash'], name='stream_hash_idx'),
        ),
        migrations.AddIndex(
            model_name='stream',
            index=models.Index(fields=['last_seen'], name='stream_last_seen_idx'),
        ),
    ]
