# Generated migration for ChannelGroup group_type and custom_properties fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('channels', '0030_alter_stream_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='channelgroup',
            name='group_type',
            field=models.CharField(
                choices=[
                    ('live', 'Live TV'),
                    ('vod_movie', 'VOD Movies'),
                    ('vod_series', 'VOD Series'),
                    ('other', 'Other')
                ],
                db_index=True,
                default='live',
                help_text='Type of content in this group (live TV, VOD movies, VOD series)',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='channelgroup',
            name='custom_properties',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Custom properties for this group (portal_category_id, etc.)',
                null=True
            ),
        ),
    ]
