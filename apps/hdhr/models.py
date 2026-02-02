from django.db import models

class HDHRDevice(models.Model):
    friendly_name = models.CharField(max_length=100, default='Dispatcharr HDHomeRun')
    device_id = models.CharField(max_length=32, unique=True)
    tuner_count = models.PositiveIntegerField(default=3)

    def __str__(self):
        return self.friendly_name
