from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m3u", "0018_add_profile_custom_properties"),
    ]

    operations = [
        migrations.AddField(
            model_name="m3uaccount",
            name="mac_address",
            field=models.CharField(
                max_length=32,
                blank=True,
                default="",
                help_text="MAC address for Stalker/portal accounts (optional).",
            ),
        ),
    ]
