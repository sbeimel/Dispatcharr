from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import StreamProfile

@receiver(pre_delete, sender=StreamProfile)
def prevent_deletion_if_locked(sender, instance, **kwargs):
    if instance.locked:
        raise ValidationError("This profile is locked and cannot be deleted.")
