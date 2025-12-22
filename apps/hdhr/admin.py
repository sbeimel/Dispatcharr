from django.contrib import admin
from .models import HDHRDevice

@admin.register(HDHRDevice)
class HDHRDeviceAdmin(admin.ModelAdmin):
    list_display = ('friendly_name', 'device_id', 'tuner_count')
