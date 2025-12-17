# Generated migration for CoreSettings value TextField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_alter_systemevent_event_type"),
    ]

    operations = [
        # Alter the value field from CharField to TextField
        # This allows storing larger JSON configurations
        migrations.AlterField(
            model_name='coresettings',
            name='value',
            field=models.TextField(help_text='Setting value. Can store JSON for complex settings.'),
        ),
    ]
