from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("m3u", "0019_m3uaccountmac"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE m3u_m3uaccount "
                "ALTER COLUMN mac_address TYPE varchar(255);"
            ),
            reverse_sql=(
                "ALTER TABLE m3u_m3uaccount "
                "ALTER COLUMN mac_address TYPE varchar(17);"
            ),
        ),
    ]
