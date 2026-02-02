# apps/accounts/signals.py
# Example: automatically create something on user creation

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User


@receiver(post_save, sender=User)
def handle_new_user(sender, instance, created, **kwargs):
    if created:
        # e.g. initialize default avatar config
        if not instance.avatar_config:
            instance.avatar_config = {"style": "circle"}
            instance.save()
