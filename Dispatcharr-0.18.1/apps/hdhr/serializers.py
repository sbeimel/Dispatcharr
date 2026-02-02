from rest_framework import serializers
from .models import HDHRDevice


class HDHRDeviceSerializer(serializers.ModelSerializer):
    """Serializer for HDHomeRun device information"""
    
    class Meta:
        model = HDHRDevice
        fields = ['id', 'friendly_name', 'device_id', 'tuner_count']
