from django.contrib import admin
from .models import MACPortal, MACAddress

@admin.register(MACPortal)
class MACPortalAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'url', 'username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Allgemein', {
            'fields': ('name', 'url', 'is_active')
        }),
        ('Zugangsdaten', {
            'fields': ('username', 'password'),
            'classes': ('collapse',)
        }),
        ('Zeitstempel', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(MACAddress)
class MACAddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'portal', 'status', 'current_connections', 'max_connections', 'last_seen')
    list_filter = ('status', 'portal', 'last_seen')
    search_fields = ('address', 'portal__name')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('portal',)
    
    fieldsets = (
        ('Allgemein', {
            'fields': ('portal', 'address', 'status')
        }),
        ('Verbindungen', {
            'fields': ('current_connections', 'max_connections')
        }),
        ('Zeitstempel', {
            'fields': ('last_seen', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # Deaktiviert das Hinzufügen von MAC-Adressen über die Admin-Oberfläche
        return False
