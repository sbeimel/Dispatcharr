from django.db import migrations
import json

def create_default_refresh_tasks(apps, schema_editor):
    """
    Creates a PeriodicTask for each existing EPGSource that doesn't have one.
    """
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    EPGSource = apps.get_model("epg", "EPGSource")

    default_interval, _ = IntervalSchedule.objects.get_or_create(
        every=24,
        period="hours",
    )

    for account in EPGSource.objects.all():
        if account.refresh_task:
            continue

        task_name = f"epg_source-refresh-{account.id}"

        refresh_task = PeriodicTask.objects.create(
            name=task_name,
            interval=default_interval,
            task="apps.epg.tasks.refresh_epg_data",
            kwargs=json.dumps({"account_id": account.id}),
        )

        account.refresh_task = refresh_task
        account.save(update_fields=["refresh_task"])

def reverse_migration(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    EPGSource = apps.get_model("epg", "EPGSource")

    for account in EPGSource.objects.all():
        IntervalSchedule.objects.all().delete()
        PeriodicTask.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("epg", "0006_epgsource_refresh_interval_epgsource_refresh_task"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_default_refresh_tasks, reverse_migration),
    ]
