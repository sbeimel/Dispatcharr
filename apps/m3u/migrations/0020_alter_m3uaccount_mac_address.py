from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m3u", "0019_m3uaccountmac"),
    ]

    operations = [
        migrations.AlterField(
            model_name="m3uaccount",
            name="mac_address",
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                help_text=(
                    "One or more MAC addresses (comma/semicolon/whitespace separated) "
                    "for MAC/STB accounts"
                ),
            ),
        ),
    ]
