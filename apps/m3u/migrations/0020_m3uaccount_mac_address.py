from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration to add mac_address field to M3UAccount model.
    This field stores space-separated MAC addresses for MAC/STB-Portal accounts.
    """

    dependencies = [
        ("m3u", "0019_m3uaccountmac"),
    ]

    operations = [
        migrations.AddField(
            model_name="m3uaccount",
            name="mac_address",
            field=models.CharField(
                max_length=255,
                blank=True,
                null=True,
                help_text="Space-separated MAC addresses for STB-Portal accounts",
            ),
        ),
    ]
