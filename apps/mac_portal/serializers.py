from rest_framework import serializers
from django.db import models
from .models import MACPortal, MACAddress

class MACAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = MACAddress
        fields = ['id', 'address', 'status', 'max_connections', 
                 'current_connections', 'last_seen', 'created_at']
        read_only_fields = ['created_at', 'last_seen']

class MACPortalSerializer(serializers.ModelSerializer):
    mac_addresses = MACAddressSerializer(many=True, read_only=True)
    online_macs = serializers.SerializerMethodField()
    total_macs = serializers.SerializerMethodField()
    available_macs = serializers.SerializerMethodField()
    in_use_macs = serializers.SerializerMethodField()
    
    class Meta:
        model = MACPortal
        fields = [
            'id', 'name', 'url', 'is_active', 'created_at', 
            'updated_at', 'mac_addresses', 'online_macs', 
            'total_macs', 'available_macs', 'in_use_macs'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_online_macs(self, obj):
        return obj.mac_addresses.filter(status='active').count()
    
    def get_total_macs(self, obj):
        return obj.mac_addresses.count()
    
    def get_available_macs(self, obj):
        return obj.mac_addresses.filter(
            status='active', 
            current_connections__lt=models.F('max_connections')
        ).count()
    
    def get_in_use_macs(self, obj):
        return obj.mac_addresses.filter(current_connections__gt=0).count()
