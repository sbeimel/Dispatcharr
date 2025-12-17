from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class MACPortal(models.Model):
    name = models.CharField(max_length=200)
    url = models.URLField()
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "MAC Portal"
        verbose_name_plural = "MAC Portale"

class MACAddress(models.Model):
    STATUS_CHOICES = [
        ('active', 'Aktiv'),
        ('inactive', 'Inaktiv'),
        ('banned', 'Gesperrt'),
        ('expired', 'Abgelaufen')
    ]
    
    portal = models.ForeignKey(MACPortal, on_delete=models.CASCADE, related_name='mac_addresses')
    address = models.CharField(max_length=17)  # Format: 00:1A:79:XX:XX:XX
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    max_connections = models.PositiveIntegerField(default=1)
    current_connections = models.PositiveIntegerField(default=0)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "MAC Adresse"
        verbose_name_plural = "MAC Adressen"
        unique_together = ('portal', 'address')

    def __str__(self):
        return f"{self.address} ({self.portal.name})"
