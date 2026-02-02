from django.db import migrations
import json

def create_default_refresh_tasks(apps, schema_editor):
    """
    Creates a PeriodicTask for each existing M3UAccount that doesn't have one.
    """
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    M3UAccount = apps.get_model("m3u", "M3UAccount")

    default_interval, _ = IntervalSchedule.objects.get_or_create(
        every=24,
        period="hours",
    )

    for account in M3UAccount.objects.all():
        if account.refresh_task:
            continue

        task_name = f"m3u_account-refresh-{account.id}"

        refresh_task = PeriodicTask.objects.create(
            name=task_name,
            interval=default_interval,
            task="apps.m3u.tasks.refresh_single_m3u_account",
            kwargs=json.dumps({"account_id": account.id}),
        )

        account.refresh_task = refresh_task
        account.save(update_fields=["refresh_task"])

def reverse_migration(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    M3UAccount = apps.get_model("m3u", "M3UAccount")

    for account in M3UAccount.objects.all():
        IntervalSchedule.objects.filter(name=f"m3u_account-refresh-interval-{account.id}").delete()
        PeriodicTask.objects.filter(name=f"m3u_account-refresh-{account.id}").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("m3u", "0005_m3uaccount_custom_properties_and_more"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_default_refresh_tasks, reverse_migration),
    ]
