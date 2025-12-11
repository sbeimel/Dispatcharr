from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Migration to add mac_address field to M3UAccount model.
    This field stores space-separated MAC addresses for MAC/STB-Portal accounts.
    Also adds the MAC account type to the Types choices.
    """

    dependencies = [
        ("m3u", "0024_m3uaccountmac"),
    ]

    operations = [
        # Add mac_address field to M3UAccount
        migrations.AddField(
            model_name="m3uaccount",
            name="mac_address",
            field=models.CharField(
                max_length=255,
                blank=True,
                null=True,
                help_text="Space-separated MAC addresses for STB-Portal accounts (e.g., '00:1A:79:12:34:56 00:1A:79:12:34:57')",
            ),
        ),
    ]
